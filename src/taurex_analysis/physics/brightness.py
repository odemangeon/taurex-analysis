import numpy as np
from scipy.constants import h, c, k
from scipy.optimize import brentq

def brightness_temperature(wavelength_um, surface_flux):
    """Invert pi B_lambda; flux is W m^-2 micron^-1, output is kelvin.

    Zero flux has the limiting temperature zero. Negative/nonfinite flux has
    no physical brightness temperature and is returned as NaN.
    """
    wl, flux = np.broadcast_arrays(np.asarray(wavelength_um)*1e-6,
                                    np.asarray(surface_flux, dtype=float))
    if np.any(~np.isfinite(wl) | (wl <= 0)):
        raise ValueError('Wavelengths must be finite and positive')
    result = np.full(flux.shape, np.nan)
    result[flux == 0] = 0.
    valid = np.isfinite(flux) & (flux > 0)
    # logaddexp avoids overflow in the Wien tail.
    log_ratio = np.log(2*np.pi*h*c*c*1e-6) - 5*np.log(wl[valid]) - np.log(flux[valid])
    result[valid] = h*c/(wl[valid]*k*np.logaddexp(0., log_ratio))
    return result

def band_brightness_temperature(depth, radius_ratio, band):
    """Invert a dimensionless band eclipse depth using existing detector weights."""
    if not np.isfinite(radius_ratio) or radius_ratio <= 0:
        raise ValueError('Radius ratio must be finite and positive')
    if not np.isfinite(depth) or depth < 0:
        return np.nan
    if depth == 0:
        return 0.
    wavelength, weight, stellar_integral = band
    wl = wavelength*1e-6
    target = depth*stellar_integral/radius_ratio**2

    def residual(temperature):
        with np.errstate(over='ignore'):
            flux = 2*np.pi*h*c*c/wl**5/np.expm1(h*c/(wl*k*temperature))*1e-6
        return np.trapezoid(flux*weight, wavelength)-target

    upper = 4000.
    while residual(upper) < 0:
        upper *= 2
    return brentq(residual, .01, upper)
