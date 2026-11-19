import numpy as np
from taurex.core import fitparam
from taurex_analysis.physics.blackbody import blackbody
from .photometry import PhotometricModel
from taurex_analysis.data.measurements import read_measurements, read_selection
from taurex_analysis.data.observations import Photometry

class ThermalModel(PhotometricModel):
    def __init__(self, rows, inputs, filters_path=None):
        super().__init__(rows, inputs, 'BlackbodyPhotometry', filters_path=filters_path)
        self.temperature = 1800.

    def surface_flux(self, wavelength):
        return blackbody(wavelength, self.temperature)


    @fitparam(param_name='T_day', param_latex=r'T_\mathrm{day}', default_fit=True, default_bounds=[500, 4000])
    def day_temperature(self):
        return self.temperature

    @day_temperature.setter
    def day_temperature(self, value):
        self.temperature = value

    def band_depth(self, name):
        wl, weight, denominator = self.filters[name]
        return self.radius_ratio**2 * np.trapezoid(blackbody(wl, self.temperature)*weight, wl) / denominator

    def spectrum(self, wavelength):
        return self.radius_ratio**2 * blackbody(wavelength, self.temperature) / self.stellar_flux(wavelength)

    def model(self, wngrid=None, cutoff_grid=True):
        if wngrid is not None and not np.array_equal(wngrid, self.grid):
            raise ValueError('This photometric model returns selected band integrals; use spectrum() for a continuous SED')
        return self.grid, np.array([self.band_depth(r['band']) for r in self.rows]), None, {}