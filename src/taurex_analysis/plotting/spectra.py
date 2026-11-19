from pathlib import Path
import numpy as np
from .common import plt
from .bandpasses import plot_bandpass_background, create_norm_reponse_and_center_wl

def plot_surface_seds(wavelength, planet_quantiles, stellar_flux, output, note=''):
    """Compare hemispheric surface fluxes; stellar spectrum is held fixed."""
    fig, ax = plt.subplots(figsize=(8, 4), layout='constrained')
    ax.fill_between(wavelength, planet_quantiles[0], planet_quantiles[2],
                    color='tab:blue', alpha=.3, label='Planet: 68% credible interval')
    ax.plot(wavelength, planet_quantiles[1], color='tab:blue',
            label='Planet: median thermal spectrum')
    ax.plot(wavelength, stellar_flux, color='tab:orange', lw=1,
            label='Star: PHOENIX (fixed)')
    ax.set(xscale='log', yscale='log', xlabel='Wavelength (µm)',
           ylabel='Surface flux (W m⁻² µm⁻¹)')
    ax.legend(fontsize=9)
    if note:
        fig.suptitle(note)
    fig.savefig(output, dpi=180)
    plt.close(fig)

def plot_eclipse_sed(wl, sed_q, rows, band_names, band_meas_q, output, inputs=None,
                     model_responses=None, note='', bandpass_colors=None):
    """Plot eclipse ratios and normalized responses on separate vertical scales."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), layout='constrained')
    # Define the bandpass responses functions for plotting.
    responses, centers = create_norm_reponse_and_center_wl(band_names, model_responses, inputs)
    # Select colors for IR and optical bandpasses.
    from .config import resolve_colors
    colors = bandpass_colors if bandpass_colors is not None else resolve_colors(band_names, rows)
    ir_colors = [colors[r['band']] for r in rows]
    optical_colors = [colors[b] for b in band_names if b not in {r['band'] for r in rows}]
    # Plot the normalized responses on the twin axes of each panel (, and label them).
    plot_bandpass_background(axes[0], responses, [r['band'] for r in rows], ir_colors)
    plot_bandpass_background(axes[1], responses,[b for b in band_names if b not in {r['band'] for r in rows}], optical_colors)
    # Plot the SED eclipse depth model and its uncertainties on both panels
    for ax in axes:
        ax.fill_between(wl, sed_q[0], sed_q[2], color='tab:blue', alpha=.3,
                        label='68% credible interval')
        ax.plot(wl, sed_q[1], color='tab:blue',
                label='Median thermal planet/star spectrum', lw=1)
        ax.set_xlabel('Wavelength (µm)')
        ax.set_ylabel('Planet/star flux ratio (ppm)')
    axes[0].set_xscale('log')
    # Plot the IR eclipse depth measurements and their uncertainties on the upper panel
    axes[0].errorbar([r['wavelength_um'] for r in rows], [r['depth_ppm'] for r in rows],
                     yerr=[r['sigma_ppm'] for r in rows], fmt='ko',
                     label='Eclipse measurements (1σ)', zorder=5)
    selected_q = band_meas_q[:, [band_names.index(r['band']) for r in rows]]
    axes[0].errorbar([r['wavelength_um'] for r in rows], selected_q[1],
                    yerr=[selected_q[1]-selected_q[0], selected_q[2]-selected_q[1]],
                    fmt='rs', mfc='none', capsize=4, elinewidth=1.5,
                    label='Band-integrated model (68%)', zorder=6)
    axes[0].set_xlim(min(2.5, min(r['wavelength_um'] for r in rows)*.95), 22)
    axes[0].legend(fontsize=8, loc='lower right')
    # Plot the optical eclipse depth predictions and their uncertainties on the lower panel
    optical_upper = []
    for name, color in zip([b for b in band_names if b not in {r['band'] for r in rows}], optical_colors):
        wave, response = responses[name]
        center = np.trapezoid(wave*response, wave) / np.trapezoid(response, wave)
        low, median, high = band_meas_q[:, band_names.index(name)]
        optical_upper.append(high)
        axes[1].errorbar(center, median, yerr=[[median-low], [high-median]],
                         fmt='rs', mfc='none', mew=1.5,
                         markersize=7, capsize=4, elinewidth=1.5, zorder=6,
                         label=f'{name}: band-integrated prediction (68%)')
    axes[1].set_xlim(.3, 1.2)
    axes[1].set_ylim(0, max([1e-12, *sed_q[2, (wl >= .3) & (wl <= 1.2)].tolist(), *optical_upper])*1.1)
    axes[1].set_title('Visible extrapolation: thermal emission only')
    axes[1].legend(fontsize=8, loc='upper left')
    if note:
        fig.suptitle(note)
    fig.savefig(output, dpi=180)
    plt.close(fig)
