"""Planet-independent stellar and detector integration context (no TauREx)."""
import csv
import json
from pathlib import Path
import numpy as np
from .filter_library import response_directory, validate

class PhotometryContext:
    def __init__(self, rows, inputs, filters_path=None):
        self.inputs = Path(inputs)
        self.system = json.loads((self.inputs / 'system.json').read_text())
        self.radius_ratio = self.system['radius_ratio_mean']
        self.rows = rows
        self.grid = 1e4 / np.array([r['wavelength_um'] for r in rows])
        manifest = json.loads((self.inputs / 'manifest.json').read_text())
        if manifest['system'] != self.system:
            raise ValueError('system.json changed: rerun inputs/prepare.py to rebuild PHOENIX')
        star = np.load(self.inputs / 'stellar_spectrum.npz')
        self.star_wl = star['wavelength_um']
        self.star_flux = star['surface_flux_W_m2_um']
        self.filters_path = response_directory(self.inputs, filters_path)
        library_file = self.filters_path/'library.json'
        if library_file.exists():
            library = validate(self.filters_path)
            for name, meta in manifest['filters'].items():
                if library['filters'].get(name) != meta:
                    raise ValueError(f'Filter metadata differs from input manifest: {name}')
        self.filters = {}
        responses = {}
        for name, meta in manifest['filters'].items():
            wl, response = np.loadtxt(self.filters_path / f'{name}.csv', delimiter=',', skiprows=1).T
            if (not np.all(np.isfinite(wl)) or not np.all(np.isfinite(response))
                    or np.any(np.diff(wl) <= 0) or np.any(response < 0) or not np.any(response > 0)):
                raise ValueError(f'Invalid response: {name}')
            responses[name] = wl, response, meta
        if 'spectral_bins' in manifest:
            with (self.inputs / manifest['spectral_bins']).open(newline='') as handle:
                bins = list(csv.DictReader(handle))
            names = [b['band'] for b in bins]
            if len(set(names)) != len(names) or set(names) & responses.keys():
                raise ValueError('Spectral bin IDs must be unique and distinct from parent responses')
            selected = {row['band']: row for row in rows}
            for b in bins:
                if b['band'] not in selected:
                    continue
                wl, response, meta = responses[b['parent_response']]
                lo, hi = float(b['lower_um']), float(b['upper_um'])
                if not (wl[0] <= lo < hi <= wl[-1]):
                    raise ValueError(f"Invalid or uncovered bin boundaries: {b['band']}")
                if not lo < selected[b['band']]['wavelength_um'] < hi:
                    raise ValueError(f"Measurement wavelength outside bin: {b['band']}")
                grid = np.r_[lo, wl[(wl > lo) & (wl < hi)], hi]
                # Integrate strictly between exact edges; padding with zero would
                # create artificial response ramps outside the bin.
                responses[b['band']] = grid, np.interp(grid, wl, response), meta
        # Keep the unweighted responses for diagnostics, including spectral bins
        # constructed above that deliberately have no individual CSV file.
        self.responses = {name: (wl, response) for name, (wl, response, _) in responses.items()}
        for name, (wl, response, meta) in responses.items():
            if wl[0] < self.star_wl[0] or wl[-1] > self.star_wl[-1]:
                raise ValueError(f'PHOENIX does not cover {name}')
            # Union retains stellar absorption structure AND response breakpoints.
            grid = np.unique(np.r_[wl, self.star_wl[(self.star_wl > wl[0]) & (self.star_wl < wl[-1])]])
            weight = np.interp(grid, wl, response)
            if meta['detector_type'] == 1:
                weight *= grid  # photon counting: lambda/(hc), common constants cancel
            elif meta['detector_type'] != 0:
                raise ValueError('Unsupported detector type')
            denom = np.trapezoid(self.stellar_flux(grid)*weight, grid)
            if not np.isfinite(denom) or denom <= 0:
                raise ValueError('Invalid integrated stellar flux')
            self.filters[name] = grid, weight, denom
        for row in rows:
            if row['band'] not in self.filters:
                raise ValueError(f"Missing response for {row['band']}")

    def stellar_flux(self, wavelength):
        if np.min(wavelength) < self.star_wl[0] or np.max(wavelength) > self.star_wl[-1]:
            raise ValueError('Requested wavelengths exceed PHOENIX coverage')
        return np.interp(wavelength, self.star_wl, self.star_flux)

