import numpy as np
from .posterior import quantiles
BANDS=("CHEOPS","TESS")

def select_samples(weights, count, seed):
    weights = np.asarray(weights, dtype=float)
    if not np.all(np.isfinite(weights)) or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError('Invalid posterior weights')
    weights = weights/weights.sum()
    if count == 0 or count >= len(weights):
        return np.arange(len(weights)), weights
    positions = (np.arange(count)+np.random.default_rng(seed).random())/count
    cumulative = np.cumsum(weights)
    cumulative[-1] = 1.
    return np.searchsorted(cumulative, positions), np.full(count, 1/count)

def summarize(base, changed, weights):
    valid = np.all(np.isfinite(base), axis=1) & np.all(np.isfinite(changed), axis=1)
    result = []
    for j, band in enumerate(BANDS):
        row = dict(band=band, valid_weight=float(weights[valid].sum()),
                   failed_weight=float(weights[~valid].sum()), valid_pairs=int(valid.sum()))
        for name, values in [('baseline', base), ('changed', changed),
                             ('difference', changed-base),
                             ('percent_change', 100*(changed-base)/base)]:
            q = quantiles(values[valid, j], weights[valid]) if valid.any() else [np.nan]*3
            row.update({f'{name}_{label}': float(value) for label, value in zip(('p16', 'median', 'p84'), q)})
        result.append(row)
    return result
