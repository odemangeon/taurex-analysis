import numpy as np
from taurex.model import EmissionModel

class SurfaceEmission(EmissionModel):
    def compute_final_flux(self, flux):
        # Native emission returns pi-integrated surface F_lambda in W/m2/um.
        # Apply the shared PHOENIX denominator and radius ratio outside TauREx.
        return flux

def layer_fluxes(dtau, temperatures, wavenumber, mu, weights):
    """Exact LTE flux contribution per layer plus the black lower boundary.

    Layers ordered bottom to top. Includes Planck source and angular quadrature,
    unlike TauREx's returned tau diagnostic (vertical transmission differences).
    """
    from taurex.util.emission import black_body
    above = np.cumsum(dtau[::-1], axis=0)[::-1] - dtau
    source = np.array([black_body(wavenumber, t) for t in temperatures])
    layer = np.zeros_like(dtau)
    boundary = np.zeros(dtau.shape[1])
    for m, w in zip(mu, weights):
        layer += 2*w*m * source * np.exp(-above/m) * (-np.expm1(-dtau/m))
        boundary += 2*w*m * source[0] * np.exp(-dtau.sum(axis=0)/m)
    return layer, boundary
