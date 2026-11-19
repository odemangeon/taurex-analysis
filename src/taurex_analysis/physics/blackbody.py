import numpy as np
from scipy.constants import h, c, k

def blackbody(wavelength_um, temperature):
    """Hemispheric surface flux pi B_lambda, W m^-2 micron^-1."""
    wl = np.asarray(wavelength_um) * 1e-6
    if temperature <= 0:
        raise ValueError('Temperature must be positive')
    with np.errstate(over='ignore'):
        return np.pi * 2*h*c*c / wl**5 / np.expm1(h*c/(wl*k*temperature)) * 1e-6
