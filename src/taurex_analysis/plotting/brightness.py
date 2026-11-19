"""Render temperatures already computed by post-processing."""
import numpy as np
from .common import plt
from .bandpasses import plot_bandpass_background, create_norm_reponse_and_center_wl

def plot_brightness(wl, sed_q, band_meas_q, band_meas_names, band_predict_q, band_predict_names, output, inputs=None, model_responses=None, note='', bandpass_colors=None):
    fig, axes=plt.subplots(2,1,figsize=(10,9),layout='constrained')
    # Define the bandpass responses functions for plotting.
    responses, centers = create_norm_reponse_and_center_wl(band_predict_names, model_responses, inputs)
    # Select colors for IR and optical bandpasses.
    from .config import resolve_colors
    colors = bandpass_colors if bandpass_colors is not None else resolve_colors(band_predict_names)
    predict_colors = [colors[b] for b in band_meas_names]
    optical_colors = [colors[b] for b in band_predict_names if b not in band_meas_names]
    # Plot the normalized responses on the twin axes of each panel (, and label them).
    plot_bandpass_background(axes[0], responses, band_meas_names, predict_colors)
    plot_bandpass_background(axes[1], responses,[b for b in band_predict_names if b not in band_meas_names], optical_colors)
    # Print the brightness spectra and its uncertainties on both panels
    for ax in axes:
        ax.fill_between(wl, sed_q[0], sed_q[2], color='tab:blue', alpha=.3,
                        label='68% credible interval')
        ax.plot(wl, sed_q[1], color='tab:blue',
                label='Median thermal brightness temperature', lw=1)
        ax.set(xlabel='Wavelength (µm)', ylabel='Brightness temperature (K)')
    # Plot the inverted brightness temperatures measurements and their uncertainties on the upper panel
    for i, band in enumerate(band_meas_names):
        wl,lo,mid,hi=band_meas_q[band_meas_names.index(band),:]
        axes[0].errorbar([centers[band]], [mid], yerr=[[mid-lo],[hi-mid]], fmt='ko',
                          zorder=5)
    axes[0].plot([],[],'ko',label='Band-inverted data (1σ; nominal radius fixed)')
    # Plot the band-integrated brightness temperatures predictions and their uncertainties
    for i, band in enumerate(band_predict_names):
        if band in band_meas_names:
            panel = 0
        else:
            panel = 1
        lo,mid,hi=band_predict_q[:,band_predict_names.tolist().index(band)]
        if np.isfinite([lo,mid,hi]).all():
            axes[panel].errorbar(centers[band],mid,yerr=[[mid-lo],[hi-mid]],fmt='rs',mfc='none',capsize=3,
            label='Band-integrated model (68%)' if i==0 else band if panel else None)
        elif np.isfinite(mid):
            axes[panel].plot(centers[band],mid,'ko')
    # Set the x-axis limits, scales, titles for both panels
    axes[0].set(xscale='log', xlim=(min(2.5,min(band_meas_q[:,0])*.95), 22))
    axes[1].set(xlim=(.3,1.2),title='Visible extrapolation: thermal emission only')
    for ax in axes:
        ax.legend(fontsize=8)
    if note: fig.suptitle(note)
    fig.savefig(output,dpi=180)
    plt.close(fig)
