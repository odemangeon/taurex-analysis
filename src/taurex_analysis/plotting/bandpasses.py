"""Render instrument bandpases/throughputs"""
from pathlib import Path
import numpy as np

def plot_bandpass_background(ax, responses, names, colors, *, labels=True):
    """
    ax: is the existing spectrum or brightness-temperature axis.
    responses: maps each filter name to its wavelength and response arrays.
    names: selects which filters to draw on that panel.
    colors: controls their appearance.
    """
    response_ax = ax.twinx()
    response_ax.set_zorder(0)
    ax.set_zorder(1)
    ax.patch.set_visible(False)
    response_ax.set_ylim(0, 1.25)
    response_ax.set_yticks([0, .5, 1])
    response_ax.set_ylabel('Normalized bandpass response', color='0.5')
    response_ax.tick_params(axis='y', colors='0.5', labelsize=8)
    for name, color in zip(names, colors):
        wave, response = responses[name]
        response_ax.fill_between(wave, response, color=color, alpha=.10)
        response_ax.plot(wave, response, color=color, alpha=.30, lw=1)
        # Response-weighted mean wavelength is a plotting coordinate only.
        if labels:
            center = np.trapezoid(wave*response, wave) / np.trapezoid(response, wave)
            if len(names) <= 10:
                response_ax.text(center, 1.04, name, color=color, ha='center', fontsize=8)
    return response_ax


def create_norm_reponse_and_center_wl(band_names, model_responses, inputs):
    # Define the bandpass responses functions for plotting.
    responses = {}
    centers = {}
    for name in band_names:
        if model_responses is not None:
            wave, response = model_responses[name]
        else:
            wave, response = np.loadtxt(Path(inputs)/'filters'/f'{name}.csv',
                                        delimiter=',', skiprows=1).T
        responses[name] = wave, response / response.max()
        centers[name] = np.trapezoid(wave*response, wave) / np.trapezoid(response, wave)
    return responses, centers