"""Nestle-specific rejection handling and result translation."""
import numpy as np
from .base import SamplingResult

def run(problem, settings, seed):
    import nestle
    options = dict(settings)
    options.setdefault('method', 'multi')
    nlive = options.pop('nlive', 600)
    tolerance = options.pop('tol', .1)
    progress = options.pop('progress', True)
    if not isinstance(progress, bool):
        raise ValueError('Nestle progress must be true or false')
    options.setdefault('callback', nestle.print_progress if progress else None)
    if progress:
        print(f'Starting Nestle with {nlive} live points; initializing live points before iteration updates...', flush=True)
    def likelihood(parameters):
        value = problem.log_likelihood(parameters)
        return -1e100 if value == -np.inf else value
    result = nestle.sample(likelihood, problem.prior_transform, len(problem.names),
                           npoints=nlive, dlogz=tolerance,
                           rstate=np.random.RandomState(seed), **options)
    if progress:
        print(f'\nNestle completed: {result.niter} iterations, {result.ncall} likelihood calls.', flush=True)
    return SamplingResult(result.samples, result.weights, result.logl, problem.names,
                          float(result.logz), float(result.logzerr),
                          {'ncall': int(result.ncall), 'niter': int(result.niter)}).validate()
