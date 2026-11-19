"""Compare thermal prior/posterior predictions without rerunning a retrieval."""
import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np
from taurex_analysis.postprocess.bands import band_quantiles, COLUMNS



def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


from taurex_analysis.postprocess.predictive import prior_samples


from taurex_analysis.postprocess.predictive import evaluate


from taurex_analysis.plotting.predictive import plot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path, nargs='?')
    parser.add_argument('--bands', nargs='+', default=['TESS', 'CHEOPS'])
    parser.add_argument('--prior-draws', type=int, default=5000)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--label')
    parser.add_argument('--bins', type=int, default=60)
    parser.add_argument('--log-depth', action='store_true')
    parser.add_argument('--replot', action='store_true', help='Plot saved predictions without loading a forward model')
    args = parser.parse_args(argv)
    if args.bins < 2 or args.prior_draws < 1:
        parser.error('bins must be >=2 and prior-draws must be positive')
    if args.replot:
        plot(args.output, args.bins, args.log_depth)
        return
    if args.results is None:
        parser.error('results is required unless --replot is used')
    source, output = args.results.resolve(), args.output.resolve()
    if output == source:
        parser.error('Use a separate output directory')
    bands = [b.upper() for b in args.bands]
    if len(set(bands)) != len(bands):
        parser.error('Duplicate bands')
    from taurex_analysis.results.loading import load_run
    from taurex_analysis.retrieval.problem import build
    run_config, rows, saved, provenance, evidence = load_run(source)
    problem = build(run_config, rows)
    model = problem.model
    config = run_config
    samples, weights, names = saved['samples'], saved['weights'], saved['names'].tolist()
    checked = provenance.get('physical_inputs', provenance.get('sha256', {}))
    for band in bands:
        if band not in model.filters:
            raise ValueError(f'Unknown prediction band: {band}')
    keep = weights > 0
    samples, weights = samples[keep], weights[keep] / weights[keep].sum()
    prior = np.array([problem.prior_transform(u) for u in np.random.default_rng(args.seed).random((args.prior_draws, len(names)))])
    priors = problem.priors
    code = list(Path(__file__).parents[1].rglob('*.py'))
    identity = dict(results=str(source), bands=bands, prior_draws=args.prior_draws, seed=args.seed,
                    priors=priors, config=config, physical_inputs=checked,
                    sources={str(p): sha256(p) for p in [source/'posterior.npz', source/'provenance.json', source/'summary.json']},
                    code={str(p): sha256(p) for p in code})
    fingerprint = json.dumps(identity, sort_keys=True)
    output.mkdir(parents=True, exist_ok=True)
    identity_path = output / 'predictive_identity.json'
    if identity_path.exists() and identity_path.read_text() != fingerprint:
        raise ValueError('Output contains a different calculation; choose a new output directory')
    identity_path.write_text(fingerprint)
    prior_depths, prior_failures = evaluate(model, prior, names, bands, output/'prior_checkpoint.npz', fingerprint)
    post_depths, post_failures = evaluate(model, samples, names, bands, output/'posterior_checkpoint.npz', fingerprint)
    np.savez_compressed(output/'predictive_samples.npz', bands=bands, names=names,
                        prior_parameters=prior, posterior_parameters=samples,
                        prior_depths_ppm=prior_depths, posterior_depths_ppm=post_depths, posterior_weights=weights)
    report = dict(identity, label=args.label or source.parent.name,
                  smoke=bool(run_config.get('smoke', False)) or (source/'NOT_SCIENTIFIC_RESULTS.txt').exists(),
                  versions={name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'matplotlib', 'taurex')},
                  interpretation='Thermal depths without measurement noise; intervals conditional on valid evaluations.',
                  prior=dict(count=len(prior), invalid_count=int(np.isnan(prior_depths).any(axis=1).sum()),
                             invalid_fraction=float(np.isnan(prior_depths).any(axis=1).mean()), failures=prior_failures),
                  posterior=dict(count=len(samples), invalid_count=int(np.isnan(post_depths).any(axis=1).sum()),
                                 invalid_weight=float(weights[np.isnan(post_depths).any(axis=1)].sum()), failures=post_failures))
    (output/'predictive_provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    plot(output, args.bins, args.log_depth)
    print(f'Saved comparison to {output}', flush=True)


if __name__ == '__main__':
    main()
