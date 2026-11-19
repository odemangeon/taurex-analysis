"""Sampler-independent prior transform and normalized Gaussian likelihood."""
import numpy as np
from scipy.special import ndtri

class RetrievalProblem:
    def __init__(self, model, rows, priors):
        self.model, self.rows, self.priors = model, rows, priors
        self.names = list(priors)
        available = model.fitting_parameters()
        unknown = set(self.names) - available.keys()
        if unknown:
            raise ValueError(f'Unknown fitted parameters: {sorted(unknown)}')
        self.setters = [available[name][3] for name in self.names]
        self.observed = np.array([r['depth_ppm'] for r in rows])*1e-6
        self.errors = np.array([r['sigma_ppm'] for r in rows])*1e-6
        self.normalization = -np.log(self.errors*np.sqrt(2*np.pi)).sum()

    def update_model(self, parameters):
        if len(parameters) != len(self.names):
            raise ValueError('Parameter vector has incorrect length')
        for setter, value in zip(self.setters, parameters):
            setter(float(value))

    def prior_transform(self, unit):
        result = []
        for u, prior in zip(unit, self.priors.values()):
            if prior['type'] == 'uniform':
                lo, hi = prior['bounds']
                result.append(lo+(hi-lo)*u)
            else:
                result.append(prior['mean']+prior['sigma']*ndtri(u))
        return np.asarray(result)

    def log_likelihood(self, parameters):
        from taurex.exceptions import InvalidModelException
        self.update_model(parameters)
        try:
            prediction = self.model.model()[1]
        except InvalidModelException:
            return -np.inf
        if not np.all(np.isfinite(prediction)):
            return -np.inf
        return float(self.normalization-.5*np.sum(((prediction-self.observed)/self.errors)**2))


def build(config, rows=None):
    from taurex_analysis.data.measurements import read_measurements
    if rows is None:
        rows = read_measurements(config['measurements'], config['selection'])
    spec = config['model']
    if spec['family'] == 'blackbody':
        from taurex_analysis.models.blackbody import ThermalModel
        model = ThermalModel(rows, config['inputs'], filters_path=config.get('filters_path'))
        for name, value in spec.get('fixed', {}).items():
            model.fitting_parameters()[name][3](value)
    else:
        from taurex_analysis.models.atmosphere import AtmosphericPhotometry
        model = AtmosphericPhotometry(rows, spec['settings'], config['inputs'], stride=config.get('opacity_stride', 1), filters_path=config.get('filters_path'))
    return RetrievalProblem(model, rows, config['priors'])
