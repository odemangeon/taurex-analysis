"""Prior/posterior predictions with checkpointed model evaluation."""
from collections import Counter
import json
import numpy as np

def prior_samples(names, count, rng, system, bounds):
    columns, descriptions = [], {}
    for name in names:
        if name == 'radius_ratio':
            mean, sigma = system['radius_ratio_mean'], system['radius_ratio_sigma']
            columns.append(rng.normal(mean, sigma, count))
            descriptions[name] = dict(type='Gaussian', mean=mean, sigma=sigma)
        else:
            lo, hi = bounds[name]
            if not np.isfinite([lo, hi]).all() or lo >= hi:
                raise ValueError(f'Invalid prior bounds for {name}')
            columns.append(rng.uniform(lo, hi, count))
            descriptions[name] = dict(type='Uniform', bounds=[lo, hi])
    return np.column_stack(columns), descriptions

def evaluate(model, samples, names, bands, checkpoint, identity):
    from taurex.exceptions import InvalidModelException
    setters = [model.fitting_parameters()[name][3] for name in names]
    depths = np.full((len(samples), len(bands)), np.nan)
    failures = Counter()
    start = 0
    if checkpoint.exists():
        with np.load(checkpoint) as saved:
            if str(saved['identity']) != identity:
                raise ValueError(f'Stale checkpoint: {checkpoint}; use a new output directory')
            depths[:] = saved['depths']
            start = int(saved['completed'])
            failures.update(json.loads(str(saved['failures'])))
    for i in range(start, len(samples)):
        try:
            for setter, value in zip(setters, samples[i]):
                setter(float(value))
            values = np.array([model.band_depth(b) * 1e6 for b in bands])
            if not np.isfinite(values).all() or np.any(values < 0):
                raise InvalidModelException('Invalid thermal depth')
            depths[i] = values
        except InvalidModelException as exc:
            failures[str(exc) or type(exc).__name__] += 1
        if (i + 1) % 25 == 0 or i + 1 == len(samples):
            temporary = checkpoint.with_suffix('.tmp.npz')
            np.savez_compressed(temporary, depths=depths, completed=i + 1,
                                failures=json.dumps(failures), identity=identity)
            temporary.replace(checkpoint)
            print(f'{checkpoint.stem}: {i + 1}/{len(samples)}; invalid={sum(failures.values())}', flush=True)
    return depths, dict(failures)
