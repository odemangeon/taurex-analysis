"""Load versioned runs or historical HD149026b results without modifying them."""
import json
from pathlib import Path
from taurex_analysis.config import resolve
from .io import load_posterior
from .provenance import verify


def legacy_config(source, provenance, summary):
    source = Path(source)
    args = provenance['arguments']
    # Prefer the original physical input location recorded in provenance.
    candidates = [Path(p).parent for p in provenance['sha256'] if Path(p).name == 'stellar_spectrum.npz']
    if not candidates:
        raise ValueError('Legacy provenance does not identify the stellar inputs')
    inputs = candidates[0]
    system = summary.get('system', provenance.get('system', provenance.get('input_manifest', {}).get('system')))
    config = dict(schema_version=1, inputs=str(inputs), measurements=str(inputs/'measurements.csv'),
        selection=[r['band'] for r in summary['selected_measurements']],
        seed=int(args.get('seed', 149026)), sampler=dict(backend='nestle', settings={}))
    if (source/'config.json').exists():
        settings = json.loads((source/'config.json').read_text())
        config['model'] = dict(family='atmosphere', settings=settings)
        bounds = settings['fit']
        config['seed'] = settings['seed']
        config['opacity_stride'] = provenance.get('opacity_stride', 1)
        config['sampler']['settings'] = dict(nlive=settings['nlive'], tol=settings['tolerance'], method='multi')
    else:
        config['model'] = dict(family='blackbody')
        bounds = {'T_day': args['temperature_bounds']}
        if not args.get('fix_radius', False):
            bounds['radius_ratio'] = [.04, .07]
        config['sampler']['settings'] = dict(nlive=args.get('nlive',600), tol=args.get('tol',.1), method='multi')
    config['priors'] = {name: (dict(type='gaussian', mean=system['radius_ratio_mean'], sigma=system['radius_ratio_sigma'])
        if name == 'radius_ratio' else dict(type='uniform', bounds=value)) for name,value in bounds.items()}
    config['smoke'] = bool(args.get('smoke',False)) or (source/'NOT_SCIENTIFIC_RESULTS.txt').exists()
    return resolve(config, source.parent)


def load_run(source, *, verify_inputs=True):
    source = Path(source).resolve()
    provenance = json.loads((source/'provenance.json').read_text())
    if (source/'experiment.json').exists():
        config = resolve(json.loads((source/'experiment.json').read_text()), source)
        rows = json.loads((source/'observations.json').read_text())
        if verify_inputs:
            verify(provenance['physical_inputs'])
        verify({str(source/Path(p).name): h for p,h in provenance.get('artifacts', {}).items()})
    else:
        summary = json.loads((source/'summary.json').read_text())
        rows = summary['selected_measurements']
        physical = {p:h for p,h in provenance['sha256'].items()
            if Path(p).suffix in ('.h5','.hdf5','.cia','.dat') or Path(p).parent.name == 'filters'
            or Path(p).name in ('system.json','manifest.json','stellar_spectrum.npz','measurements.csv')}
        if verify_inputs:
            verify(physical)
        config = legacy_config(source, provenance, summary)
    posterior = load_posterior(source)
    if set(posterior['names']) != set(config['priors']):
        raise ValueError('Saved parameter names differ from configured priors')
    # Preserve the sampler's saved column order.
    config['priors'] = {str(n): config['priors'][str(n)] for n in posterior['names']}
    evidence = json.loads((source/'evidence.json').read_text()) if (source/'evidence.json').exists() else None
    return config, rows, posterior, provenance, evidence
