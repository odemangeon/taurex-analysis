"""Recompute band intervals from all saved weighted samples, without retrieval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from taurex_analysis.postprocess.bands import write_band_predictions

from taurex_analysis.compat.paths import PLANET as ROOT


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    source = args.results.resolve()
    from taurex_analysis.results.loading import load_run
    from taurex_analysis.retrieval.problem import build
    experiment, rows, saved, provenance, _ = load_run(source)
    model = build(experiment, rows).model
    config = experiment
    atmospheric = experiment['model']['family'] == 'atmosphere'
    checked = provenance.get('physical_inputs', provenance.get('sha256', {}))
    samples, weights, names = saved['samples'], saved['weights'], saved['names'].tolist()
    setters = [model.fitting_parameters()[name][3] for name in names]
    bands = [row['band'] for row in rows]+['CHEOPS', 'TESS']
    keep = weights > 0
    samples, weights = samples[keep], weights[keep]/weights[keep].sum()
    checkpoint = source/'optical_band_checkpoint.npz'
    fingerprint = sha256(source/'posterior.npz')
    model_hashes = {str(p): sha256(p) for p in
                    Path(__file__).parents[1].rglob('*.py')}
    identity = json.dumps(dict(posterior=fingerprint, code=model_hashes, inputs=checked,
                               config=config if atmospheric else None), sort_keys=True)
    depths = []
    if checkpoint.exists():
        with np.load(checkpoint) as saved:
            if str(saved['identity']) != identity:
                raise ValueError(f'Stale checkpoint: {checkpoint}')
            depths = saved['depths_ppm'].tolist()
    completed = len(depths)
    print(f'{source.parent.name}: evaluating {len(samples)} samples; resuming at {completed}', flush=True)
    started = time.time()
    for i in range(completed, len(samples)):
        sample = samples[i]
        for setter, value in zip(setters, sample):
            setter(float(value))
        depths.append([model.band_depth(band)*1e6 for band in bands])
        if (i+1) % 10 == 0 or i == len(samples)-1:
            np.savez_compressed(checkpoint, identity=identity, depths_ppm=depths)
            print(f'{source.parent.name}: {i+1}/{len(samples)} ({time.time()-started:.1f}s)', flush=True)
    write_band_predictions(source, bands, np.array(depths), weights)
    checkpoint.unlink(missing_ok=True)
    report = dict(method='All positive-weight posterior samples; central 68% and 99.7% intervals',
                  nested_sampling_run=False, samples=len(samples),
                  physical_input_sha256=checked, posterior_sha256=sha256(source/'posterior.npz'),
                  code_sha256={str(p): sha256(p) for p in Path(__file__).parents[1].rglob('*.py')})
    (source/'optical_postprocess_provenance.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
