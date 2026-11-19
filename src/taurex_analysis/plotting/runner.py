"""Figures use only saved arrays: no TauREx, chemistry or opacity access."""
import json
from pathlib import Path
import numpy as np
from .common import plt
from .spectra import plot_eclipse_sed, plot_surface_seds
from .brightness import plot_brightness
from .atmosphere import plot_contribution_functions_and_tp


def plot(source, output=None, config=None):
    from .config import validate, resolve_colors
    config = validate({} if config is None else config)
    source=Path(source)
    output=Path(output) if output else source/'figures'
    output.mkdir(parents=True,exist_ok=True)
    meta=json.loads((source/'analysis.json').read_text())
    with np.load(source/'posterior_predictions.npz',allow_pickle=False) as saved:
        data={k:saved[k] for k in saved.files}
    note='SOFTWARE SMOKE TEST — not scientific results' if meta['smoke'] else ''
    bands=data['bands'].tolist()
    colors=resolve_colors(bands,meta['rows'],config)
    responses={b:(data[f'response_wave_{i}'],data[f'response_value_{i}']) for i,b in enumerate(bands)}
    plot_eclipse_sed(data['wavelength_um'],data['sed_quantiles'],meta['rows'],bands,
        data['band_quantiles'],output/'eclipse_sed.png',model_responses=responses,note=note,bandpass_colors=colors)
    plot_surface_seds(data['wavelength_um'],data['flux_quantiles'],data['star_surface_flux'],output/'planet_star_sed.png',note=note)
    plot_brightness(data['wavelength_um'], data['tb_quantiles'], data['measurement_tb'], data['bands_meas_tb'].tolist(),
        data['band_tb_quantiles'], data['bands'],output/'brightness_temperature.png', model_responses=responses, note=note, bandpass_colors=colors)
    import corner
    fig=corner.corner(data['samples'],weights=data['weights'],labels=data['names'].tolist(),quantiles=[.16,.5,.84],show_titles=True)
    if note: fig.suptitle(note)
    fig.savefig(output/'corner.png',dpi=180,bbox_inches='tight');plt.close(fig)
    if 'tp_quantiles' in data:
        plot_contribution_functions_and_tp(data['pressure_bar'],data['contributions'],bands,
            data['best_temperature'],output/'contribution_functions_and_tp_profile.png',
            tp_quantiles=data['tp_quantiles'],smoke=meta['smoke'])
        fig,ax=plt.subplots(figsize=(5,6),layout='constrained')
        q=data['tp_quantiles'];p=data['pressure_bar']
        ax.fill_betweenx(p,q[0],q[2],alpha=.3);ax.plot(q[1],p)
        ax.set(xlabel='Temperature (K)',ylabel='Pressure (bar)',yscale='log');ax.invert_yaxis()
        if note: fig.suptitle(note)
        fig.savefig(output/'tp_profile.png',dpi=180);plt.close(fig)
    return output
