from taurex_analysis.plotting.common import plt
from taurex_analysis.plotting.spectra import plot_surface_seds
from taurex_analysis.plotting.spectra import plot_eclipse_sed as _plot
from taurex_analysis.plotting.atmosphere import plot_contribution_functions_and_tp
from taurex_analysis.postprocess.posterior import quantiles
from .models import shared
INPUTS=shared.INPUTS
FIGURE_NOTE=''

def plot_eclipse_sed(wl,sed_q,rows,band_names,band_q,output,inputs=INPUTS,photometry=None):
    if photometry is None:
        from taurex_analysis.data.photometry import PhotometryContext
        photometry=PhotometryContext(rows,inputs)
    return _plot(wl,sed_q,rows,band_names,band_q,output,model_responses=photometry.responses,note=FIGURE_NOTE)
