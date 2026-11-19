import json
from pathlib import Path
import numpy as np


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def fresh_directory(path):
    path = Path(path).resolve()
    if path.exists() and any(path.iterdir()):
        raise ValueError(f'Output directory is nonempty: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_posterior(output, result):
    result.validate()
    np.savez_compressed(output/'posterior.npz', samples=result.samples, weights=result.weights,
                        names=result.names, logl=result.logl)
    np.savetxt(output/'posterior.csv', np.c_[result.samples, result.weights], delimiter=',',
               header=','.join([*result.names, 'weight']), comments='')
    write_json(output/'evidence.json', dict(log_evidence=result.log_evidence,
        log_evidence_error=result.log_evidence_error, log_base='e',
        uncertainty='Backend estimated sampling standard error'))
    write_json(output/'sampler_diagnostics.json', result.diagnostics)


def load_posterior(source):
    with np.load(Path(source)/'posterior.npz', allow_pickle=False) as saved:
        result = {key: saved[key].copy() for key in saved.files}
    samples, weights, names = result['samples'], result['weights'], result['names']
    if (samples.shape != (len(weights), len(names)) or not np.isfinite(samples).all()
            or not np.isfinite(weights).all() or np.any(weights < 0) or weights.sum() <= 0):
        raise ValueError('Invalid saved posterior')
    result['weights'] = weights/weights.sum()
    return result
