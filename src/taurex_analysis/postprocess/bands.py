"""Weighted equal-tail thermal eclipse intervals, in ppm."""
import csv
import numpy as np

PROBABILITIES = np.array([.0015, .16, .5, .84, .9985])
COLUMNS = ['p0_15_ppm', 'p16_ppm', 'median_ppm', 'p84_ppm', 'p99_85_ppm']


def band_quantiles(depths, weights):
    depths, weights = np.asarray(depths), np.asarray(weights)
    if (depths.ndim != 2 or weights.shape != (len(depths),)
            or not np.all(np.isfinite(depths)) or np.any(depths < 0)
            or not np.all(np.isfinite(weights)) or np.any(weights < 0)
            or weights.sum() <= 0):
        raise ValueError('Invalid band posterior depths or weights')
    keep = weights > 0
    depths, weights = depths[keep], weights[keep]/weights[keep].sum()
    result = []
    for column in depths.T:
        order = np.argsort(column)
        w = weights[order]
        result.append(np.interp(PROBABILITIES, np.cumsum(w)-.5*w, column[order]))
    return np.array(result).T


def write_band_predictions(output, bands, depths, weights):
    q = band_quantiles(depths, weights)
    with (output/'band_predictions.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['band', *COLUMNS])
        writer.writerows((band, *values) for band, values in zip(bands, q.T))
    np.savez_compressed(output/'band_posterior.npz', bands=bands,
                        depths_ppm=depths, weights=weights,
                        probabilities=PROBABILITIES, quantiles_ppm=q)
    return q
