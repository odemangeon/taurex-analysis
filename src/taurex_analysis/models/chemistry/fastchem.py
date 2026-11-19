import numpy as np
from taurex_fastchem import FastChem
from taurex.core import fitparam
from taurex.exceptions import InvalidModelException

class CheckedFastChem(FastChem):
    @fitparam(param_name='log10_metallicity', param_latex=r'\log_{10}(Z/Z_\odot)',
              default_fit=False, default_bounds=[-1., 3.])
    def logMetallicity(self):
        return np.log10(self.metallicity)

    @logMetallicity.setter
    def logMetallicity(self, value):
        self.metallicity = 10.**value

    def initialize_chemistry(self, *args, **kwargs):
        super().initialize_chemistry(*args, **kwargs)
        if np.any(np.asarray(self._fc_output_data.fastchem_flag) != 0):
            raise InvalidModelException('FastChem failed to converge; refusing this model')
        if not np.all(np.isfinite(self.mixProfile)) or np.any(self.mixProfile < 0):
            raise InvalidModelException('Invalid equilibrium mixing ratios')
