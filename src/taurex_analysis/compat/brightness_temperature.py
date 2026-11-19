"""Brightness-temperature diagnostics for thermal eclipse retrievals."""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
from scipy.constants import h, c, k
from scipy.optimize import brentq


from taurex_analysis.physics.brightness import brightness_temperature


from taurex_analysis.physics.brightness import band_brightness_temperature


def write_brightness_temperature(wavelength, temperature_quantiles, output,
                                 rows=(), photometry=None, note='',
                                 band_names=(), band_quantiles=None, band_note=''):
    """Write IR/visible panels, band responses, measurements and predictions."""
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/hd149026b-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    q = np.asarray(temperature_quantiles)
    np.savetxt(output/'brightness_temperature.csv', np.c_[wavelength, q.T],
               delimiter=',', comments='',
               header='wavelength_um,Tb_p16_K,Tb_median_K,Tb_p84_K')
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), layout='constrained')
    for ax in axes:
        ax.fill_between(wavelength, q[0], q[2], alpha=.3, color='tab:blue',
                        label='68% credible interval')
        ax.plot(wavelength, q[1], color='tab:blue', lw=1,
                label='Median thermal brightness temperature')
        ax.set(xlabel='Wavelength (µm)', ylabel='Brightness temperature (K)')
        ax.grid(alpha=.15)
    infrared_min = min(2.5, min((r['wavelength_um']*.95 for r in rows), default=2.5))
    axes[0].set(xscale='log', xlim=(infrared_min, 22))
    axes[1].set(xlim=(.3, 1.2), title='Visible extrapolation: thermal emission only')
    responses = {}
    if photometry is not None:
        for name in dict.fromkeys([r['band'] for r in rows]+['CHEOPS', 'TESS']):
            wave, response = photometry.responses[name]
            responses[name] = wave, response/response.max()
        for ax, names, colors in (
                (axes[0], [r['band'] for r in rows],
                 [plt.get_cmap('tab10')(i) for i in range(len(rows))]),
                (axes[1], ['CHEOPS', 'TESS'], ['tab:purple', 'tab:orange'])):
            response_ax = ax.twinx()
            response_ax.set_zorder(0)
            ax.set_zorder(1)
            ax.patch.set_visible(False)
            response_ax.set(ylim=(0, 1.25), yticks=[0, .5, 1])
            response_ax.set_ylabel('Normalized bandpass response', color='0.5')
            response_ax.tick_params(axis='y', colors='0.5', labelsize=8)
            for name, color in zip(names, colors):
                wave, response = responses[name]
                response_ax.fill_between(wave, response, color=color, alpha=.10)
                response_ax.plot(wave, response, color=color, alpha=.30, lw=1)
                center = np.trapezoid(wave*response, wave)/np.trapezoid(response, wave)
                if len(names) <= 10:
                    response_ax.text(center, 1.04, name, color=color, ha='center', fontsize=8)
    ax = axes[0]
    if photometry is not None and rows:
        radius = photometry.system['radius_ratio_mean']
        measurements = []
        for row in rows:
            depths = np.array([row['depth_ppm']-row['sigma_ppm'], row['depth_ppm'],
                               row['depth_ppm']+row['sigma_ppm']])*1e-6
            values = [band_brightness_temperature(d, radius, photometry.filters[row['band']])
                      for d in depths]
            measurements.append([row['wavelength_um'], *values])
            low, middle, high = values
            # Do not invent a temperature for a nonpositive measurement/error bound.
            if np.all(np.isfinite(values)):
                ax.errorbar(row['wavelength_um'], middle,
                            yerr=[[middle-low], [high-middle]], fmt='ko', capsize=3)
            elif np.isfinite(middle):
                ax.plot(row['wavelength_um'], middle, 'ko')
        ax.plot([], [], 'ko', label=f'Band-inverted data (1σ; Rp/R★ = {radius:g} fixed)')
        np.savetxt(output/'brightness_temperature_measurements.csv', measurements,
                   delimiter=',', comments='',
                   header='wavelength_um,Tb_minus_1sigma_K,Tb_K,Tb_plus_1sigma_K')
        if any(not np.all(np.isfinite(row[1:])) for row in measurements):
            ax.text(.01, .02, 'Nonphysical depths: undefined temperatures/errors omitted (see CSV)',
                    transform=ax.transAxes, fontsize=8)
    if band_quantiles is not None:
        band_quantiles = np.asarray(band_quantiles)
        with open(output/'brightness_temperature_bands.csv', 'w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['band', 'Tb_p16_K', 'Tb_median_K', 'Tb_p84_K'])
            writer.writerows((name, *values) for name, values in zip(band_names, band_quantiles.T))
        for i, name in enumerate(band_names):
            low, median, high = band_quantiles[:, i]
            visible = name in ('CHEOPS', 'TESS')
            ax = axes[int(visible)]
            color = {'CHEOPS': 'tab:purple', 'TESS': 'tab:orange'}.get(name, 'red')
            if visible:
                wave, response = responses[name]
                center = np.trapezoid(wave*response, wave)/np.trapezoid(response, wave)
                label = f'{name}: band-integrated prediction (68%)'
            else:
                center = next(r['wavelength_um'] for r in rows if r['band'] == name)
                label = 'Band-integrated model (68%)' if name == band_names[0] else None
            ax.errorbar(center, median, yerr=[[median-low], [high-median]],
                        fmt='s', mfc='none', mec=color, ecolor=color, capsize=4,
                        elinewidth=1.5, mew=1.5, zorder=6, label=label)
    for ax in axes:
        ax.legend(fontsize=8, loc='lower right')
    if band_note:
        axes[0].set_title(band_note, fontsize=9)
    if note:
        fig.suptitle(note)
    fig.savefig(output/'brightness_temperature.png', dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='Plot saved surface-flux percentiles without rerunning a retrieval.')
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    data = np.genfromtxt(args.results/'sed.csv', delimiter=',', names=True)
    wl = data['wavelength_um']
    flux = np.array([data['planet_surface_flux_W_m2_um_'+suffix]
                     for suffix in ('p16', 'median', 'p84')])
    summary = json.loads((args.results/'summary.json').read_text())
    provenance = json.loads((args.results/'provenance.json').read_text())
    from taurex_analysis.compat.paths import INPUTS as inputs
    # Replot with the original stellar spectrum/responses, never silently use changed inputs.
    for name, expected in provenance['sha256'].items():
        original = Path(name)
        if original.name == 'stellar_spectrum.npz' or original.parent.name == 'filters':
            path = inputs/'filters'/original.name if original.parent.name == 'filters' else inputs/original.name
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Input differs from saved retrieval: {path}')
    from taurex_analysis.compat import models as module
    rows = summary['selected_measurements']
    photometry = module.ThermalModel(rows, inputs)
    original_system = summary.get('system', provenance.get('system'))
    if original_system is not None and original_system != photometry.system:
        raise ValueError('Current system parameters differ from saved retrieval')
    bands = [r['band'] for r in rows]+['CHEOPS', 'TESS']
    band_file = args.results/'brightness_temperature_bands.csv'
    band_note = ''
    if band_file.exists():
        with open(band_file, newline='') as handle:
            saved = {r['band']: [float(r[key]) for key in ('Tb_p16_K', 'Tb_median_K', 'Tb_p84_K')]
                     for r in csv.DictReader(handle)}
        band_q = np.array([saved[b] for b in bands]).T
    elif 'T_day' in summary['parameters']:
        # A blackbody's band brightness temperature equals T_day in every band.
        band_q = np.repeat([[summary['parameters']['T_day'][key]]
                            for key in ('p16', 'median', 'p84')], len(bands), axis=1)
    else:
        parser.error('Saved atmospheric results lack band brightness temperatures; run guillot_baseopacity_fullSpitzer/postprocess_brightness.py RESULTS to evaluate the saved posterior without nested sampling.')
    smoke = (args.results/'NOT_SCIENTIFIC_RESULTS.txt').exists()
    write_brightness_temperature(wl, brightness_temperature(wl, flux), args.results,
        rows, photometry, band_names=bands, band_quantiles=band_q, band_note=band_note,
        note='SOFTWARE SMOKE TEST — not scientific results' if smoke else '')


if __name__ == '__main__':
    main()
