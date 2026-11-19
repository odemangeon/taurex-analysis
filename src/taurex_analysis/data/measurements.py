import csv
from pathlib import Path
import numpy as np

def read_selection(path):
    """One group or measurement ID per line; blank lines and # comments allowed."""
    selectors = [line.split('#', 1)[0].strip() for line in Path(path).read_text().splitlines()]
    selectors = [item for item in selectors if item]
    if not selectors:
        raise ValueError(f'No measurement selectors in {path}')
    return selectors

def read_measurements(path, bands=None):
    with open(path, newline='') as handle:
        rows = list(csv.DictReader(handle))
    names = [r['band'] for r in rows]
    if len(set(names)) != len(names):
        raise ValueError('Each band must appear once; combine repeated measurements explicitly')
    selected_names = set()
    if bands is not None:
        for selector in bands:
            # Explicit group labels allow arbitrary unique IDs for future spectral bins.
            matches = {r['band'] for r in rows
                       if r['band'] == selector or r.get('group', '').strip() == selector}
            if not matches:
                raise ValueError(f'Unknown or empty measurement selector: {selector}')
            selected_names.update(matches)

    selected = []
    for row in rows:
        flag = row.get('enabled', 'true').strip().lower()
        if flag not in ('true', 'false', '1', '0'):
            raise ValueError('enabled must be true/false or 1/0')
        if (bands is not None and row['band'] in selected_names) or (bands is None and flag in ('true', '1')):
            for key in ('wavelength_um', 'depth_ppm', 'sigma_ppm'):
                row[key] = float(row[key])
                if not np.isfinite(row[key]):
                    raise ValueError(f'Nonfinite {key}')
            if row['sigma_ppm'] <= 0 or row['wavelength_um'] <= 0:
                raise ValueError('Uncertainties and wavelengths must be positive')
            selected.append(row)
    if not selected:
        raise ValueError('No measurements selected')
    return sorted(selected, key=lambda row: row['wavelength_um'], reverse=True)
