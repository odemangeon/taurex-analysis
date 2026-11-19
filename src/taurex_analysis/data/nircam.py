"""Build NIRCam parent responses and fixed bins from the supplied source tables."""
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import numpy as np



def linear_extrapolate(x, xp, yp):
    """Linear interpolation; outside the table use the nearest two samples."""
    x = np.asarray(x)
    result = np.interp(x, xp, yp)
    for mask, a, b in ((x < xp[0], 0, 1), (x > xp[-1], -2, -1)):
        result[mask] = yp[a] + (x[mask] - xp[a]) * (yp[b] - yp[a]) / (xp[b] - xp[a])
    return result


def validate_curve(data):
    if (data.ndim != 2 or data.shape[1] != 2 or len(data) < 2
            or not np.all(np.isfinite(data)) or np.any(np.diff(data[:, 0]) <= 0)
            or np.any(data[:, 0] <= 0) or np.any(data[:, 1] < 0)
            or not np.any(data[:, 1] > 0)):
        raise ValueError('Invalid NIRCam throughput table')


def prepare_nircam(manifest, root, literature):
    from .filter_library import refuse_linked_outputs
    refuse_linked_outputs(Path(root)/'filters')
    root = Path(root)
    source_dir = root / 'filters' / 'source_files'
    grism_path = source_dir / 'NIRCam_GRISM_TP.csv'
    grism = np.loadtxt(grism_path, delimiter=',', skiprows=2, usecols=(0, 1))
    validate_curve(grism)
    literature = root / literature
    with literature.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    bins = []

    def record(path, **metadata):
        manifest['files'][str(path.relative_to(root))] = {
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **metadata}

    record(grism_path, column='TP_modA_1stOrder', format='user-supplied CSV')
    record(literature)
    for filt in ('F322W2', 'F444W'):
        parent = f'NIRCAM-{filt}'
        # Derive from the complete literature grid, never from a run selection or
        # an edited measurements.csv: omitted bins must not widen their neighbors.
        centers = sorted(Decimal(r['Instrument'].split('-', 2)[2]) for r in rows
                         if r['Instrument'].startswith(parent + '-'))
        if len(centers) < 2 or len(set(centers)) != len(centers):
            raise ValueError(f'Invalid wavelength centers for {parent}')
        edges = ([centers[0] - (centers[1] - centers[0]) / 2]
                 + [(a + b) / 2 for a, b in zip(centers, centers[1:])]
                 + [centers[-1] + (centers[-1] - centers[-2]) / 2])
        for center, lo, hi in zip(centers, edges, edges[1:]):
            bins.append({'band': f'{parent}-{center:f}', 'parent_response': parent,
                         'lower_um': f'{lo:f}', 'upper_um': f'{hi:f}'})
        source = source_dir / f'NRCA5_{filt}_May2024_system_throughput.txt'
        data = np.loadtxt(source, skiprows=1)
        validate_curve(data)
        record(source, format='user-supplied system throughput; microns')
        lo, hi = float(edges[0]), float(edges[-1])
        if lo < data[0, 0] or hi > data[-1, 0]:
            raise ValueError(f'Filter system throughput does not cover {parent} bins')
        # Limit extrapolation to the actual bin coverage. Retain both source
        # grids' breakpoints and every exact bin edge in the combined curve.
        grid = np.unique(np.r_[np.array(edges, dtype=float),
            data[(data[:, 0] > lo) & (data[:, 0] < hi), 0],
            grism[(grism[:, 0] > lo) & (grism[:, 0] < hi), 0]])
        throughput = (np.interp(grid, data[:, 0], data[:, 1])
                      * linear_extrapolate(grid, grism[:, 0], grism[:, 1]))
        combined = np.column_stack((grid, throughput))
        validate_curve(combined)
        path = root / 'filters' / f'{parent}.csv'
        np.savetxt(path, combined, delimiter=',', header='wavelength_um,response', comments='')
        record(path, derived_from=[str(p.relative_to(root)) for p in (source, grism_path)],
               grism_column='TP_modA_1stOrder', interpolation='linear',
               extrapolation='linear using the nearest two grism samples at each end',
               grism_measured_range_um=[float(grism[0, 0]), float(grism[-1, 0])],
               output_range_um=[lo, hi],
               response='filter system throughput times grism; no wavelength weighting or normalization')
        manifest['filters'][parent] = {
            'id': f'JWST/NIRCam.NRCA5.{filt}.grismA.order1',
            'detector_type': 1, 'weighting': 'photon'}

    path = root / 'filters' / 'NIRCAM_bins.csv'
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['band', 'parent_response', 'lower_um', 'upper_um'])
        writer.writeheader()
        writer.writerows(bins)
    record(path, derived_from=str(literature.relative_to(root)),
           boundaries='midpoints within each filter; outer edges use half the adjacent spacing; inferred, not published')
    manifest['spectral_bins'] = 'filters/NIRCAM_bins.csv'


