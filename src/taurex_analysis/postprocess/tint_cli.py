"""Paired thermal eclipse sensitivity to T_int, using saved retrieval posteriors."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np


from taurex_analysis.postprocess.posterior import quantiles
from taurex_analysis.plotting.common import plt
from taurex.exceptions import InvalidModelException
from taurex.log import setLogLevel

BANDS = ('CHEOPS', 'TESS')


def temperature_support(source, tint):
    """Check every weighted sample against temperature-table bounds, without RT."""
    import h5py
    from taurex_analysis.models.temperature import create_temperature
    from taurex.planet import Planet
    from taurex.data.profiles.pressure import SimplePressureProfile
    from taurex_analysis.results.loading import load_run
    experiment, _, _, provenance, _ = load_run(source, verify_inputs=False)
    config = experiment['model']['settings']
    paths = provenance.get('opacity_files', {}).values() if 'opacity_files' in provenance else [p for p in provenance['physical_inputs'] if Path(p).suffix in ('.h5', '.hdf5')]
    limits = []
    for path in paths:
        with h5py.File(path) as handle:
            limits.append((float(handle['t'][:].min()), float(handle['t'][:].max())))
    low, high = max(x[0] for x in limits), min(x[1] for x in limits)
    atm = config['atmosphere']
    pressure = SimplePressureProfile(atm['nlayers'], atm['atm_min_pressure'], atm['atm_max_pressure'])
    pressure.compute_pressure_profile()
    tp = create_temperature(config['temperature'])
    tp.initialize_profile(Planet(**config['planet']), pressure.nLayers, pressure.profile)
    tp.internalTemperature = tint
    setters = tp.fitting_parameters()
    with np.load(source/'posterior.npz') as saved:
        weights = saved['weights']/saved['weights'].sum()
        excluded = []
        for sample in saved['samples']:
            for name, value in zip(saved['names'], sample):
                if name in setters:
                    setters[name][3](float(value))
            t = tp.profile
            excluded.append(t.min() < low or t.max() > high)
    return dict(tint_K=tint, table_min_K=low, table_max_K=high,
                excluded_posterior_weight=float(weights[np.asarray(excluded)].sum()),
                note='Exact original weighted posterior mass outside temperature tables; chemistry not checked.')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


from taurex_analysis.postprocess.tint import select_samples


from taurex_analysis.postprocess.tint import summarize


from taurex_analysis.plotting.tint import write_comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', nargs='+', type=Path,
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tint', type=float, default=500.)
    parser.add_argument('--allow-changed-inputs', action='store_true',
                        help='Recompute BOTH temperatures with current physical inputs; record all hash differences')
    parser.add_argument('--posterior-draws', type=int, default=256,
                        help='Systematic posterior resampling; 0 uses every weighted sample')
    args = parser.parse_args(argv)
    if not args.results:
        parser.error('No retrieval output directories found')
    if len({p.resolve().parent.name for p in args.results}) != len(args.results):
        parser.error('Use distinct retrieval folder names for output labels')
    if not np.isfinite(args.tint) or args.tint < 0 or args.posterior_draws < 0:
        parser.error('T_int and posterior-draws must be finite and nonnegative')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output must be empty; choose a new --output directory')
    args.output.mkdir(parents=True, exist_ok=True)
    setLogLevel(40)
    started = time.time()
    checked, reports, summaries = {}, [], []
    for source in args.results:
        source = source.resolve()
        label = source.parent.name.removeprefix('guillot_fullopacity_gamma_kappaIR_metalCO_')
        from taurex_analysis.results.loading import load_run
        from taurex_analysis.retrieval.problem import build
        experiment, rows, saved, provenance, _ = load_run(source, verify_inputs=not args.allow_changed_inputs)
        if experiment['model']['family'] != 'atmosphere':
            raise ValueError('T_int comparison requires an atmospheric run')
        config = experiment['model']['settings']
        config['seed'] = experiment['seed']
        if config['temperature'].get('parameters', config['temperature'])['T_int'] != 100 or 'T_int_guillot' in config['fit']:
            raise ValueError(f'{source}: expected fixed T_int=100 K')
        if experiment.get('opacity_stride', 1) != 1 or experiment.get('smoke', False):
            raise ValueError('Scientific comparison requires full-resolution retrievals')
        print(f'{label}: verifying original physical inputs...', flush=True)
        changed_inputs = {}
        for package, version in provenance['versions'].items():
            if importlib.metadata.version(package) != version:
                raise ValueError(f'Dependency changed: {package}')
        for name, expected in provenance.get('physical_inputs', provenance.get('sha256', {})).items():
            path = Path(name)
            if (path.suffix in ('.h5', '.hdf5', '.cia', '.dat') or path.parent.name == 'filters'
                    or path.name in ('stellar_spectrum.npz', 'system.json', 'manifest.json', 'measurements.csv')):
                if name not in checked:
                    checked[name] = sha256(path)
                if checked[name] != expected:
                    if not args.allow_changed_inputs:
                        raise ValueError(f'Physical input changed since retrieval: {name}. '
                                         'Use --allow-changed-inputs only for a paired comparison with current inputs.')
                    changed_inputs[name] = dict(saved=expected, current=checked[name])
        with np.load(source/'posterior.npz') as saved:
            samples, weights, names = saved['samples'], saved['weights'], saved['names'].tolist()
        if samples.shape != (len(weights), len(names)) or set(names) != set(config['fit']) or not np.all(np.isfinite(samples)):
            raise ValueError('Invalid saved posterior')
        indices, draw_weights = select_samples(weights, args.posterior_draws, config['seed'])
        model = build(experiment, rows).model
        setters = [model.fitting_parameters()[name][3] for name in names]
        model.atmosphere.pressure.compute_pressure_profile()
        model.tp.initialize_profile(model.atmosphere.planet, model.atmosphere.pressure.nLayers,
                                    model.atmosphere.pressure.profile)
        depths = np.full((len(indices), 2, 2), np.nan)
        failures = []
        for i, index in enumerate(indices):
            for setter, value in zip(setters, samples[index]):
                setter(float(value))
            # Test the alternate profile first: unsupported pairs need no costly RT.
            for k, tint in ((1, args.tint), (0, 100.)):
                model.tp.internalTemperature = tint
                model._state = None  # T_int is fixed, so its setter bypasses the wrapper cache.
                try:
                    temperature = model.tp.profile
                    for op in model.opacities:
                        if temperature.min() < op.temperatureGrid.min() or temperature.max() > op.temperatureGrid.max():
                            raise InvalidModelException(f'TP outside {op.moleculeName} temperature table')
                    depths[i, k] = [model.band_depth(b)*1e6 for b in BANDS]
                except InvalidModelException as error:
                    failures.append(dict(draw=i, posterior_index=int(index), tint=tint, reason=str(error)))
                    break
            if i % 10 == 0 or i+1 == len(indices):
                print(f'{label}: {i+1}/{len(indices)} paired samples; {len(failures)} failed evaluations', flush=True)
        np.savez_compressed(args.output/f'{label}_paired.npz', indices=indices, weights=draw_weights,
                            depths_ppm=depths, bands=BANDS, tint_K=[100., args.tint])
        report = dict(model=label, source=str(source), draws=len(indices), failures=failures,
                      changed_inputs=changed_inputs,
                      temperature_support=[temperature_support(source, t) for t in (100., args.tint)],
                      source_sha256={n: sha256(source/n) for n in ('posterior.npz', 'selection.txt', 'provenance.json')})
        reports.append(report)
        (args.output/f'{label}_report.json').write_text(json.dumps(report, indent=2)+'\n')
        summaries.extend(dict(model=label, **r) for r in summarize(depths[:, 0], depths[:, 1], draw_weights))
        del model
    write_comparison(args.output, summaries, args.tint)
    if any(r['changed_inputs'] for r in reports):
        with (args.output/'comparison.md').open('a') as handle:
            handle.write('\nSome saved physical inputs have changed: both temperatures use CURRENT inputs. '
                         'See changed_inputs in the per-run reports; these do not reproduce the original saved predictions.\n')
    (args.output/'provenance.json').write_text(json.dumps(dict(
        tint_K=[100., args.tint], posterior_draws=args.posterior_draws,
        method='Paired systematic resampling with original seed; no refitting/reweighting; valid-pair conditional summaries',
        physical_input_sha256=checked, runs=reports, elapsed_seconds=time.time()-started,
        code_sha256={str(p): sha256(p) for p in Path(__file__).parents[1].rglob('*.py')}), indent=2)+'\n')
    print(f'Wrote {args.output}', flush=True)


if __name__ == '__main__':
    main()
