"""Sampling persists a reusable result before any analysis is requested."""
from pathlib import Path
import json
from taurex_analysis.results.io import fresh_directory, write_json, save_posterior
from taurex_analysis.results.provenance import hashes, versions
from .problem import build
from .samplers import sample

def physical_paths(config, model):
    inputs = Path(config['inputs'])
    paths = [inputs/name for name in ('system.json', 'manifest.json', 'stellar_spectrum.npz')]
    paths += [Path(config['measurements'])]
    from taurex_analysis.data.filter_library import response_directory
    filters = response_directory(inputs, config.get('filters_path'))
    manifest = json.loads((inputs/'manifest.json').read_text())
    paths += [filters/f'{name}.csv' for name in manifest['filters']]
    if (filters/'library.json').exists():
        paths.append(filters/'library.json')
        library = json.loads((filters/'library.json').read_text())
        paths += [filters/name for name in library['files']]
    if 'spectral_bins' in manifest:
        paths.append(inputs/manifest['spectral_bins'])
    if hasattr(model, 'opacity_files'):
        paths += list(map(Path, model.opacity_files.values()))
        paths += list(Path(config['model']['settings']['cia_path']).glob('*.cia'))
        chemistry = config['model']['settings']['chemistry']
        if chemistry.get('backend', 'fastchem') == 'fastchem':
            import taurex_fastchem
            base = Path(taurex_fastchem.__file__).parent
            paths += list((base/'data').glob('*.dat'))
    return paths

def retrieve(config, output, check=False):
    output = fresh_directory(output)
    problem = build(config)
    write_json(output/'experiment.json', config)
    write_json(output/'observations.json', problem.rows)
    write_json(output/'provenance.json', dict(schema_version=1, versions=versions(),
        physical_inputs=hashes(physical_paths(config, problem.model)),
        artifacts=hashes([output/'experiment.json', output/'observations.json']),
        code=hashes(Path(__file__).parents[1].rglob('*.py')),
        system=problem.model.system, thermal_only=True))
    (output/'selection.txt').write_text('\n'.join(config['selection'])+'\n')
    if config.get('smoke', False):
        (output/'NOT_SCIENTIFIC_RESULTS.txt').write_text('SOFTWARE SMOKE TEST ONLY\n')
    if check:
        report = dict(status='forward_model_passed',
            initial_model_depths_ppm={r['band']: float(problem.model.band_depth(r['band'])*1e6) for r in problem.rows})
        if hasattr(problem.model, 'contributions'):
            _, bottom = problem.model.contributions([r['band'] for r in problem.rows])
            report['lower_boundary_fractions'] = bottom.tolist()
        write_json(output/'validation.json', report)
        return output
    result = sample(problem, config['sampler'], config['seed'])
    save_posterior(output, result)
    from taurex_analysis.postprocess.posterior import quantiles
    q = quantiles(result.samples, result.weights)
    write_json(output/'summary.json', dict(parameters={n: dict(zip(('p16','median','p84'), v.tolist())) for n,v in zip(result.names,q.T)},
        selected_measurements=problem.rows, system=problem.model.system,
        effective_posterior_samples=float(1/(result.weights**2).sum()), thermal_only=True,
        software_smoke_test_only=config.get('smoke', False)))
    return output
