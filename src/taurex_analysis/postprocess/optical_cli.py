"""Compare saved optical thermal predictions and conditional geometric albedos.

See optical_comparison.md for statistical interpretation and input format.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import warnings
from statistics import NormalDist

import numpy as np

BANDS = ('CHEOPS', 'TESS')
COLORS = ('#0072B2', '#D55E00', '#009E73')


def read_models(path, overrides=None):
    """Read an ordered model list; relative paths are relative to this config."""
    config = json.loads(path.read_text())
    entries = config.get('models')
    # Accept the original label-only configuration as well.
    if entries is None and 'model_labels' in config:
        entries = [dict(label=label, results=str(path.resolve().parent.parent/name/'results'))
                   for name, label in config['model_labels'].items()]
    if not isinstance(entries, list) or not entries:
        raise ValueError('Plot config must contain a nonempty models list')
    models = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Each model must be an object with label and results')
        enabled = entry.get('enabled', True)
        if not isinstance(enabled, bool):
            raise ValueError('Model enabled must be true or false')
        if not enabled:
            continue
        label, folder = entry.get('label'), entry.get('results')
        if not isinstance(label, str) or not label.strip():
            raise ValueError('Model label must be a nonempty string')
        if not isinstance(folder, str) or not folder.strip():
            raise ValueError(f'{label}: supply a results folder')
        folder = Path(folder).expanduser()
        if not folder.is_absolute():
            folder = path.resolve().parent/folder
        models.append((folder.resolve(), label))
    if not models:
        raise ValueError('Enable at least one model')
    if len({label for _, label in models}) != len(models):
        raise ValueError('Enabled model labels must be unique')
    if overrides is not None:
        if len(overrides) != len(models):
            raise ValueError('--results must provide one folder per enabled model, in config order')
        models = [(folder.resolve(), label) for folder, (_, label) in zip(overrides, models)]
    return models


from taurex_analysis.postprocess.optical import number


from taurex_analysis.postprocess.optical import read_constraints


from taurex_analysis.postprocess.optical import convert


from taurex_analysis.postprocess.optical import constraint_result


from taurex_analysis.plotting.optical import plot_comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--constraints', type=Path, required=False)
    parser.add_argument('--geometry', type=Path, required=False)
    parser.add_argument('--plot-config', type=Path, required=True,
                        help='JSON ordered list of retrieval results folders and display names')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--thermal-only', action='store_true', help='Plot actual predictions without optical data or geometry')
    parser.add_argument('--results', nargs='+', type=Path, metavar='DIR',
                        help='Override folders for all enabled models, in config order')
    args = parser.parse_args(argv)
    models = read_models(args.plot_config, args.results)
    inputs, predictions = [args.plot_config], {}
    for folder, label in models:
        path = folder/'band_predictions.csv'
        inputs.append(path)
        if not path.is_file():
            raise FileNotFoundError(f'{label}: missing thermal predictions: {path}')
        with path.open() as handle:
            reader = csv.DictReader(handle)
            required = {'band', 'p16_ppm', 'median_ppm', 'p84_ppm'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f'{label}: {path} requires columns {sorted(required)}')
            rows = list(reader)
        for band in BANDS:
            selected = [r for r in rows if r['band'] == band]
            if len(selected) != 1:
                raise ValueError(f'{path}: expected exactly one {band} prediction')
            q = np.array([number(selected[0][key], key) for key in ('p16_ppm', 'median_ppm', 'p84_ppm')])
            if np.any(np.diff(q) < 0) or q[0] < 0:
                raise ValueError(f'{path}: invalid thermal percentiles')
            tail_keys = ('p0_15_ppm', 'p99_85_ppm')
            present = [key in selected[0] and selected[0][key] != '' for key in tail_keys]
            if any(present) and not all(present):
                raise ValueError(f'{path}: supply both 99.7% interval endpoints')
            if all(present):
                tails = [number(selected[0][key], key) for key in tail_keys]
                if not 0 <= tails[0] <= q[0] <= q[2] <= tails[1]:
                    raise ValueError(f'{path}: invalid or non-nested 99.7% thermal interval')
                q = np.r_[q, tails]
            else:
                warnings.warn(f'{label} {band}: missing 99.7% thermal interval; '
                              'regenerate band predictions from the saved posterior', stacklevel=2)
            predictions[label, band] = q
    observations, results = [], []
    geometry = None
    if not args.thermal_only:
        if args.constraints is None or args.geometry is None:
            parser.error('--constraints and --geometry are required unless --thermal-only is used')
        observations = read_constraints(args.constraints)
        geometry = json.loads(args.geometry.read_text())
        inputs.extend([args.constraints, args.geometry])
        for _, label in models:
            for obs in observations:
                band_geometry = geometry.get('bands', {}).get(obs['band'], geometry)
                if 'rp_over_a' in band_geometry:
                    rp_over_a = number(band_geometry['rp_over_a'], 'rp_over_a', positive=True)
                else:
                    rp_over_a = (number(band_geometry['radius_ratio']['value'], 'radius_ratio', positive=True)
                                 / number(band_geometry['a_over_rstar']['value'], 'a_over_rstar', positive=True))
                if rp_over_a >= 1:
                    raise ValueError('rp_over_a must be smaller than one')
                results.append(dict(model=label, **constraint_result(obs, predictions[label, obs['band']], rp_over_a)))
    args.output.mkdir(parents=True, exist_ok=True)
    for paper in (False, True):
        plot_comparison(predictions, observations, results, models, args.output,
                        thermal_only=args.thermal_only, paper=paper)
    with (args.output/'thermal_predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['model', 'band', 'p16_ppm', 'median_ppm', 'p84_ppm', 'p0_15_ppm', 'p99_85_ppm'])
        for (label, band), q in predictions.items():
            writer.writerow([label, band, *q, *(['', ''] if len(q) == 3 else [])])
    if results:
        with (args.output/'albedo_constraints.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
        lines = ['# Conditional geometric albedo constraints', '',
                 'Fixed geometry and median thermal emission; not marginalized albedo posteriors. Negative values are retained. HPD probabilities denote enclosed posterior mass; upper endpoints are not quantiles at those probabilities.', '',
                 '| Model | Band | Constraint | Probability | Best albedo | Albedo interval / upper limit | Upper endpoint sensitivity (thermal p84 to p16) |',
                 '|---|---|---|---|---|---|---|']
        for r in results:
            interval = (f"[{r['ag_lower']:.5f}, {r['ag_upper']:.5f}]" if r['kind'] in ('measurement', 'interval')
                        else f"< {r['ag_upper']:.5f}")
            sensitivity = f"{r['ag_upper_at_thermal_p84']:.5f} to {r['ag_upper_at_thermal_p16']:.5f}"
            center = f"{r['ag_center']:.5f}" if r['ag_center'] != '' else '—'
            lines.append(f"| {r['model']} | {r['band']} | {r['label']} | {r['probability']:.6f} | {center} | {interval} | {sensitivity} |")
        (args.output/'albedo_constraints.md').write_text('\n'.join(lines)+'\n')
    provenance = dict(models=[dict(label=label, results=str(folder)) for folder, label in models],
                      thermal_only=args.thermal_only, geometry=geometry,
                      method='Ag=(observed_ppm-thermal_median_ppm)*1e-6/(Rp/a)^2; conditional summaries only',
                      inputs={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs + [Path(__file__)]})
    (args.output/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'Wrote comparison to {args.output}')


if __name__ == '__main__':
    main()
