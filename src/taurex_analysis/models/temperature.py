import numpy as np
from taurex.temperature import Guillot2010
from taurex.core import fitparam

class TiedGuillot2010(Guillot2010):
    """One visible channel, sampled in log10(kappa_visible/kappa_IR)."""
    def __init__(self, log10_gamma, **kwargs):
        super().__init__(**kwargs)
        self.logGamma = log10_gamma

    @fitparam(param_name='log10_gamma', param_latex=r'\log_{10}\gamma',
              default_fit=False, default_bounds=[-1., 1.])
    def logGamma(self):
        return np.log10(self.kappa_v1 / self.kappa_ir)

    @logGamma.setter
    def logGamma(self, value):
        self.kappa_v1 = self.kappa_v2 = self.kappa_ir * 10.**value

    @fitparam(param_name='log10_kappa_ir', param_latex=r'\log_{10}\kappa_{\rm IR}',
              default_fit=False, default_bounds=[-4., 0.])
    def logKappaIR(self):
        return np.log10(self.kappa_ir)

    @logKappaIR.setter
    def logKappaIR(self, value):
        # Preserve gamma regardless of the optimizer's parameter update order.
        gamma = self.logGamma
        self.kappa_ir = 10.**value
        self.logGamma = gamma


def create_temperature(spec):
    """Build a profile; priors, not parameterization, select fitted parameters.

    Flat specifications remain supported for historical saved runs.
    """
    spec = dict(spec)
    if 'profile' not in spec:
        return TiedGuillot2010(**spec) if 'log10_gamma' in spec else Guillot2010(**spec)
    profile = spec.pop('profile')
    parameterization = spec.pop('parameterization', 'standard')
    parameters = dict(spec.pop('parameters', {}))
    if spec:
        raise ValueError(f'Unknown temperature settings: {sorted(spec)}')
    if profile == 'isothermal':
        if parameterization != 'standard':
            raise ValueError('Isothermal supports only standard parameterization')
        from taurex.temperature import Isothermal
        return Isothermal(**parameters)
    if profile != 'guillot2010':
        raise ValueError(f'Unsupported temperature profile: {profile}')
    if parameterization == 'standard':
        if 'log10_gamma' in parameters:
            raise ValueError('log10_gamma requires tied_gamma parameterization')
        return Guillot2010(**parameters)
    if parameterization == 'tied_gamma':
        redundant = {'kappa_v1', 'kappa_v2', 'alpha'} & parameters.keys()
        if redundant:
            raise ValueError(f'Derived or ineffective tied_gamma settings: {sorted(redundant)}')
        if 'log10_gamma' not in parameters:
            raise ValueError('tied_gamma requires an initial log10_gamma')
        return TiedGuillot2010(**parameters)
    raise ValueError(f'Unsupported Guillot parameterization: {parameterization}')
