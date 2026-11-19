import numpy as np
from taurex.spectrum import ArraySpectrum
from taurex.binning import NativeBinner

class Photometry(ArraySpectrum):
    def __init__(self, rows):
        # Explicit dummy widths allow even a single datum. No top-hat binning is used.
        super().__init__(np.array([[r['wavelength_um'], r['depth_ppm']*1e-6,
                                  r['sigma_ppm']*1e-6, 0.01] for r in rows]))

    def create_binner(self):
        return NativeBinner()
