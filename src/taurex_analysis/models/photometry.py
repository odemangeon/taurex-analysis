"""Shared photometric forward-model context and fitted radius ratio."""
from taurex.model import ForwardModel
from taurex.core import fitparam
from taurex_analysis.data.photometry import PhotometryContext

class PhotometricModel(ForwardModel, PhotometryContext):
    def __init__(self, rows, inputs, name='Photometry', filters_path=None):
        ForwardModel.__init__(self, name)
        PhotometryContext.__init__(self, rows, inputs, filters_path=filters_path)

    @fitparam(param_name='radius_ratio', param_latex=r'R_p/R_\star', default_fit=True, default_bounds=[0.04, 0.07])
    def size_ratio(self):
        return self.radius_ratio

    @size_ratio.setter
    def size_ratio(self, value):
        self.radius_ratio = value

    def build(self):
        pass

