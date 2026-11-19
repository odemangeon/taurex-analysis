import numpy as np

def quantiles(values, weights):
    values = np.asarray(values)
    if values.ndim == 1:
        order = np.argsort(values)
        w = weights[order] / np.sum(weights)
        return np.interp([.16, .5, .84], np.cumsum(w)-.5*w, values[order])
    return np.array([quantiles(col, weights) for col in values.T]).T
