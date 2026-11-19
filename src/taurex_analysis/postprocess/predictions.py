"""Derived products from saved posteriors. No sampler or plotting imports."""
import json
import warnings
from pathlib import Path
import numpy as np
from taurex_analysis.physics.brightness import brightness_temperature, band_brightness_temperature
from taurex_analysis.results.io import fresh_directory, write_json
from taurex_analysis.results.loading import load_run
from taurex_analysis.results.provenance import hashes, versions
from .posterior import quantiles
from .bands import write_band_predictions


def process(source, output, options=None):
    from taurex_analysis.retrieval.problem import build
    options = dict(options or {})
    count = options.get('posterior_draws', 0)
    if not isinstance(count, int) or count < 0:
        raise ValueError('posterior_draws must be a nonnegative integer; 0 uses all weighted samples')
    config, rows, saved, provenance, evidence = load_run(source)
    problem = build(config, rows)
    model = problem.model
    atmospheric = config['model']['family'] == 'atmosphere'
    photometry = model.photometry if atmospheric else model
    bands = list(dict.fromkeys([r['band'] for r in rows]+options.get('bands', [])))
    for band in bands:
        if band not in model.filters:
            raise ValueError(f'Unknown prediction band: {band}')
        wave = model.filters[band][0]
        if atmospheric and (wave[0] < model.wavelength[0] or wave[-1] > model.wavelength[-1]):
            raise ValueError(f'Atmospheric coverage insufficient: {band}')
    wl = model.wavelength if atmospheric else np.geomspace(*options.get('wavelength_um', [.3, 25, 2000]))
    samples, weights = saved['samples'], saved['weights']
    # Zero-weight samples must not trigger otherwise irrelevant invalid models.
    indices = np.flatnonzero(weights > 0)
    draw_weights = weights[indices]/weights[indices].sum()
    if count and len(indices) > count:
        warnings.warn('Resampled posterior predictions can poorly resolve extreme tails; use posterior_draws=0 for all weights.')
        positions = (np.arange(count)+np.random.default_rng(options.get('seed',config['seed'])).random())/count
        indices = indices[np.searchsorted(np.cumsum(draw_weights), positions)]
        draw_weights = np.full(count, 1/count)
    output = fresh_directory(output)
    fluxes, spectra, depths, band_temperatures, temperatures = [], [], [], [], []
    for i, index in enumerate(indices):
        problem.update_model(samples[index])
        flux = model.surface_flux(wl)
        fluxes.append(flux)
        spectra.append(model.spectrum(wl)*1e6)
        depths.append([model.band_depth(b)*1e6 for b in bands])
        band_temperatures.append([band_brightness_temperature(d*1e-6, photometry.radius_ratio, model.filters[b]) for b,d in zip(bands,depths[-1])])
        if atmospheric:
            temperatures.append(model.atmosphere.temperatureProfile.copy())
        if i % 100 == 0:
            print(f'Posterior predictions {i+1}/{len(indices)}', flush=True)
    flux_q, sed_q = quantiles(np.array(fluxes),draw_weights), quantiles(np.array(spectra),draw_weights)
    band_q = quantiles(np.array(depths),draw_weights)
    tb_q = quantiles(brightness_temperature(wl,np.array(fluxes)),draw_weights)
    band_tb_q = quantiles(np.array(band_temperatures),draw_weights)
    # Measurement inversion belongs to analysis, not plotting.
    measurement_tb = []
    for row in rows:
        values = [row['depth_ppm']-row['sigma_ppm'],row['depth_ppm'],row['depth_ppm']+row['sigma_ppm']]
        measurement_tb.append([row['wavelength_um'], *[band_brightness_temperature(d*1e-6,model.system['radius_ratio_mean'],model.filters[row['band']]) for d in values]])
    products = dict(wavelength_um=wl, flux_quantiles=flux_q, sed_quantiles=sed_q,
        band_quantiles=band_q, tb_quantiles=tb_q, band_tb_quantiles=band_tb_q,
        bands=bands, star_surface_flux=model.stellar_flux(wl), measurement_tb=measurement_tb,
        samples=samples, weights=weights, names=saved['names'], draw_indices=indices, draw_weights=draw_weights)
    for i, band in enumerate(bands):
        products[f'response_wave_{i}'], products[f'response_value_{i}'] = photometry.responses[band]
    if 'logl' in saved:
        best = int(np.argmax(saved['logl']))
    else:
        # No reliance on Nestle-specific live-point ordering for legacy files.
        best = int(np.argmax([problem.log_likelihood(s) for s in samples]))
    problem.update_model(samples[best])
    if atmospheric:
        model.evaluate()
        pressure = model.atmosphere.pressureProfile/1e5
        tp_q = quantiles(np.array(temperatures),draw_weights)
        fractions,bottom = model.contributions(bands)
        width = abs(np.diff(np.log10(pressure))[0])
        products.update(pressure_bar=pressure,tp_quantiles=tp_q,contributions=fractions/width,
            best_temperature=model.atmosphere.temperatureProfile,lower_boundary_fractions=bottom)
        np.savez_compressed(output/'best_fit_atmosphere.npz', pressure_bar=pressure,
            temperature_K=model.atmosphere.temperatureProfile,species=model.chem.gases,mixing_ratios=model.chem.mixProfile)
        np.savetxt(output/'tp_profile.csv', np.c_[pressure,tp_q.T],delimiter=',',comments='',header='pressure_bar,T_p16_K,T_median_K,T_p84_K')
        np.savetxt(output/'contribution_functions.csv', np.c_[pressure,fractions/width],delimiter=',',comments='',header='pressure_bar,'+','.join(bands))
        write_json(output/'lower_boundary_fractions.json',dict(zip(bands,bottom.tolist())))
    np.savez_compressed(output/'posterior_predictions.npz', **products)
    np.savetxt(output/'sed.csv',np.c_[wl,sed_q.T,flux_q.T,model.stellar_flux(wl)],delimiter=',',comments='',
        header='wavelength_um,ratio_ppm_p16,ratio_ppm_median,ratio_ppm_p84,planet_surface_flux_W_m2_um_p16,planet_surface_flux_W_m2_um_median,planet_surface_flux_W_m2_um_p84,star_surface_flux_W_m2_um')
    write_band_predictions(output,bands,np.array(depths),draw_weights)
    np.savetxt(output/'brightness_temperature.csv',np.c_[wl,tb_q.T],delimiter=',',comments='',header='wavelength_um,Tb_p16_K,Tb_median_K,Tb_p84_K')
    np.savetxt(output/'brightness_temperature_measurements.csv',measurement_tb,delimiter=',',comments='',header='wavelength_um,Tb_minus_1sigma_K,Tb_K,Tb_plus_1sigma_K')
    import csv
    with (output/'brightness_temperature_bands.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['band','Tb_p16_K','Tb_median_K','Tb_p84_K'])
        writer.writerows((b,*q) for b,q in zip(bands,band_tb_q.T))
    params=quantiles(samples,weights)
    summary=dict(evidence=evidence,parameters={n:dict(zip(('p16','median','p84'),q.tolist())) for n,q in zip(saved['names'],params.T)},
        selected_measurements=rows,system=model.system,thermal_only=True,
        software_smoke_test_only=config.get('smoke',False),spectral_posterior_draws=len(indices),
        effective_posterior_samples=float(1/np.sum(weights**2)),
        best_sample_chi2=float(np.sum(((model.model()[1]-problem.observed)/problem.errors)**2)),
        nominal_dof=len(rows)-len(saved['names']),
        band_depths_ppm={b:dict(zip(('p16','median','p84'),q.tolist())) for b,q in zip(bands,band_q.T)})
    write_json(output/'summary.json',summary)
    write_json(output/'analysis.json',dict(schema_version=1,source=str(Path(source).resolve()),options=options,
        model_family=config['model']['family'],rows=rows,system=model.system,smoke=config.get('smoke',False)))
    write_json(output/'provenance.json',dict(source=hashes(Path(source)/name for name in ('posterior.npz','provenance.json')),
        retrieval_provenance=provenance,versions=versions(),code=hashes(Path(__file__).parents[1].rglob('*.py'))))
    return output
