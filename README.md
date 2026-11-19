# Thermal eclipse retrieval and analysis

Read the [documentation](docs/index.md), including the
[parameter reference](docs/parameters.md) and
[GitHub Pages publishing guide](docs/publishing.md).

The reusable code is in `src/taurex_analysis`. Planet inputs and experiment JSON
files are separate from model implementations. Sampling, posterior prediction,
and plotting are independently runnable stages.

For external opacity setup and repository data layout, see
[external data](docs/external-data.md).

## Run the three stages

Use the existing TauREx/FastChem environment. From this repository:

```bash
source /home/olivier/Softwares/taurex/taurex-fastchem-env/bin/activate
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

python -m taurex_analysis retrieve \
  planets/HD149026b/experiments/blackbody_fullSpitzer.json \
  --output runs/HD149026b/blackbody_fullSpitzer/run01

python -m taurex_analysis postprocess \
  runs/HD149026b/blackbody_fullSpitzer/run01 \
  --config planets/HD149026b/analyses/default.json \
  --output analyses/HD149026b/blackbody_fullSpitzer/v01

python -m taurex_analysis plot \
  analyses/HD149026b/blackbody_fullSpitzer/v01
```

Alternatively, install the package into your chosen environment with
`python -m pip install --no-deps -e .`, then use `taurex-analysis` in place of
`python -m taurex_analysis`. The package's optional dependency groups are
`retrieval`, `plotting`, `preparation`, and `test`. Atmospheric retrievals also
need the existing compatible FastChem installation and opacity tables; the
reorganization does not change those dependencies.

`retrieve --check` evaluates the initial forward model without sampling and
checks atmospheric contribution closure. `retrieve --smoke` uses deliberately
coarse settings for software testing and marks all downstream figures accordingly.
Neither command represents a convergence assessment.

Retrieval and analysis directories must be empty. Replotting replaces figures
in the analysis's `figures/` directory; `plot --output PATH` selects another
figure directory. Sampling never imports plotting. Plotting saved predictions
never loads TauREx, FastChem, opacity tables, or the original planet inputs.

## Where code lives

| Package | Responsibility |
|---|---|
| `data` | Measurements, selections, stellar/response integration context, input preparation |
| `physics` | Planck flux and brightness-temperature inversion |
| `models` | Blackbody and atmospheric TauREx forward models, TP/emission components, chemistry adapters |
| `retrieval` | Sampler-independent likelihood/prior problem, sampler adapters, run orchestration |
| `results` | Versioned output, provenance verification, legacy-result loading |
| `postprocess` | Weighted statistics, saved-posterior predictions, optical/predictive/Tint analyses |
| `plotting` | Figures from computed arrays and summaries |
| `compat` | Historical command arguments and HD149026b defaults |

`planets/HD149026b/experiments/` contains a JSON configuration for every existing
retrieval setup. `planets/HD149026b/inputs` contains the small runtime inputs; historical inputs
remain available at their original paths. Original result
folders and their provenance have not been moved or rewritten. Existing tests
remain alongside their original workflows; package architecture tests are in
`tests/`.

## Configuration and another planet

Experiment JSON contains:

- `filters_path`: the shared, versioned response directory (supports `~`);

- `schema_version: 1`, `inputs`, `measurements` (optional), and `selection`;
- `model.family`: `blackbody` or `atmosphere`;
- atmospheric `model.settings`: pressure grid, temperature profile, opacity
  paths/species, planetary mass/radius, and chemistry backend/settings;
- `priors`: ordered fitted parameter names and uniform bounds or Gaussian
  mean/sigma, in the actual fitted coordinates (including log10 coordinates);
- `sampler.backend`, backend-specific `sampler.settings`, and `seed`.

Paths are resolved relative to the experiment JSON, not the current directory.
The saved `experiment.json` contains the resolved configuration. Blackbody
`model.fixed` can set fixed values through model parameter names. Atmospheric
fixed parameters are supplied in the component settings. If atmospheric
`model.settings.planet` is absent, `system.json` must supply a `planet` object
with the TauREx planetary mass/radius parameters.

For another planet, add an inputs directory containing `system.json`, a
measurement catalog, `stellar_spectrum.npz`, bin definitions and `manifest.json`;
then create experiment JSON files pointing to it and to a shared `filters_path`. No shared Python code needs
planet-name edits. Stellar flux units are W m⁻² µm⁻¹, measurement depths/errors
are ppm, and detector weighting is defined in the input manifest. The exact
band integration and NIRCam bin-edge conventions are preserved.

Instrument responses now live in
`resources/filters/responses-ba0a74ab22aaad5d/`. All 16 experiment
configurations explicitly select this bundle. It contains response CSV/XML files,
original sources, and `library.json` with detector conventions, preparation
metadata and SHA256 hashes. Loading verifies the bundle and checks its detector
metadata against the planet manifest. New run provenance hashes the actual shared
files, their sources, and the library metadata.

`inputs/NIRCAM_bins.csv` remains observation-specific. Old paths beneath
`inputs/filters/` are compatibility symlinks, not duplicate response data; the
old bin path also links to the planet-local table. Existing input manifests and
historical result provenance are unchanged, and their hashes still verify through
these links. The NIRCam parent curves retain their original prepared coverage
(2.35–4.01 and 3.89–5.03 µm); other observations must stay within that coverage
or use a newly prepared version.

To change responses, prepare a private copy and publish a new version. Preparation
refuses to overwrite shared data through compatibility symlinks. For example:

```bash
# -L copies the linked files as independent files. Choose a fresh staging path.
cp -RL planets/HD149026b/inputs /tmp/new-planet-inputs
rm /tmp/new-planet-inputs/filters/library.json
python -m taurex_analysis prepare /tmp/new-planet-inputs \
  --nircam-literature data_litterature_HD149026.csv
python -m taurex_analysis publish-filters /tmp/new-planet-inputs \
  --library resources/filters
```

Use the printed version directory as `filters_path` for new runs, and adopt the
corresponding prepared input manifest/bin definitions. Existing versions are
verified and reused, never overwritten by publication. The publisher excludes
bin definitions and stellar/planet inputs. For old input layouts, omitting
`filters_path` still uses `inputs/filters/`.

Preparation can download missing source files. The existing PHOENIX downloader
still supports only its previously validated 6000–6200 K, logg 4.0–4.5,
[M/H]=+0.3 grid. For other stellar parameters, supply an appropriately prepared
stellar spectrum and manifest or extend and validate that preparation code.
NIRCam preparation takes the complete observation-specific literature catalog
explicitly; it never derives bin boundaries from a selected measurement subset.

Analysis settings are separate: `bands` adds prediction bands to fitted bands,
`posterior_draws: 0` uses every positive-weight sample, and a positive count
requests seeded systematic resampling. `wavelength_um: [min, max, count]`
controls the blackbody spectral grid; atmospheric predictions retain the native
grid. The supplied HD149026b analysis config adds CHEOPS and TESS; the package
does not require those bands for other planets. Resampling may poorly resolve
extreme tails. Brightness temperatures are transformed per sample before
weighted intervals are calculated.

## Saved products and historical results

Retrieval writes `posterior.npz`/CSV (samples, normalized weights, parameter
names, log-likelihoods), `evidence.json`, `sampler_diagnostics.json`,
`experiment.json`, `observations.json`, `selection.txt`, `summary.json`, and
`provenance.json`. Provenance records physical-input hashes, package code hashes,
dependency versions, and hashes of the saved experiment/observation snapshots.

Post-processing writes `posterior_predictions.npz`, spectral/band/brightness
CSVs, band posterior draws, summary and analysis metadata, and its own provenance.
Atmospheric analyses additionally save TP profiles, contribution functions and
best-sample chemistry. The prediction archive includes stellar fluxes, response
curves, measurement temperatures and posterior samples needed for standalone
plotting. It does not alter the retrieval directory.

The same `postprocess` command accepts an existing historical result directory:

```bash
python -m taurex_analysis postprocess HD149026b/blackbody_IRAC2/results \
  --config planets/HD149026b/analyses/default.json \
  --output analyses/HD149026b/legacy_IRAC2/v01
```

Physical inputs are checked against saved provenance. Missing legacy evidence
is reported as unavailable, never reconstructed from normalized weights.
Legacy files without log-likelihoods may require additional model evaluations
to identify the best sample. New analysis provenance records the current code
and dependency versions alongside the original retrieval provenance.

Historical `run.py` commands remain callable with their original options and
now delegate to the package. They run all three stages: raw results go to the
chosen directory, derived products to `analysis/`, and figures to
`analysis/figures/`. Point comparison configurations at that **analysis**
directory for newly generated runs. Old standalone postprocessing commands
remain compatibility tools; prefer the separate-output package command above.

## Comparisons

```bash
python -m taurex_analysis predictive RUN_DIRECTORY \
  --bands TESS CHEOPS --prior-draws 5000 --output PREDICTIVE_DIRECTORY
python -m taurex_analysis predictive --output PREDICTIVE_DIRECTORY --replot

python -m taurex_analysis compare-optical \
  --plot-config MODEL_LIST.json --constraints CONSTRAINTS.csv \
  --geometry GEOMETRY.json --output COMPARISON_DIRECTORY

python -m taurex_analysis compare-tint \
  --results RUN_DIRECTORY_1 RUN_DIRECTORY_2 \
  --tint 500 --output TINT_DIRECTORY
```

Predictive comparisons use the saved priors and weighted posterior through the
same model. Tint comparisons retain the original paired, fixed-100-K baseline
interpretation. The original optical/Tint scientific assumptions and conditional
failure reporting are unchanged; see the existing HD149026b analysis notes.
Historical script names supply their existing HD149026b defaults.

## Adding a sampler or chemistry solver

Nestle and FastChem are the implemented backends. Dynesty and other chemistry
codes are extension points, not claimed as implemented or validated.

A sampler implements `run(problem, settings, seed) -> SamplingResult`.
`problem` exposes `names`, `prior_transform(unit_cube)`, and
`log_likelihood(parameters)`. The likelihood is normalized in dimensionless
flux-ratio units; invalid physical models return negative infinity. The Nestle
adapter alone translates rejection to its finite sentinel. It uses the original
`multi` method by default. Backend-specific options are saved explicitly.
`SamplingResult` holds weighted samples, log-likelihoods, ln(Z), its uncertainty,
and backend diagnostics. Register in Python with
`taurex_analysis.retrieval.samplers.register(name, run)` or expose an installed
entry point in the `taurex_analysis.samplers` group to select it from JSON/CLI.

A chemistry factory accepts its backend's settings and returns a TauREx
`Chemistry` implementation. It supplies gas names, number mixing ratios,
molecular weights, profile initialization and fitted-parameter getters/setters.
Pressure is Pa and temperature K. Each adapter must document its elemental
reference abundances, metallicity/C/O semantics, ion support, and convergence
failure handling. Register with `models.chemistry.register(name, factory)` or
an installed entry point in `taurex_analysis.chemistry`. The atmospheric model
constructs chemistry through this factory, not directly through FastChem.

## Validation

```bash
python -m pytest -q
```

The suite includes the original scientific checks plus likelihood agreement
with TauREx, seeded Nestle result agreement, alternative sampler/chemistry
registration, another-planet input handling, provenance checks, historical
loading, and a subprocess that forbids model/sampler imports while plotting.

### Explicit temperature profiles

New atmospheric experiments select the temperature profile explicitly:

```json
"temperature": {
  "profile": "guillot2010",
  "parameterization": "tied_gamma",
  "parameters": {
    "T_irr": 1800,
    "T_int": 100,
    "kappa_irr": 0.001,
    "log10_gamma": -0.3010299956639812
  }
}
```

Supported profiles are `guillot2010` and `isothermal`. Guillot supports
`standard` (independent visible opacities) and `tied_gamma` (equal visible
opacities derived from infrared opacity and gamma). Isothermal supports
`standard`, with `parameters: {"T": 1800}`.

**Only entries in `priors` are free.** Independent parameters absent from
`priors` retain their configured values. Parameterization does not select fixed
versus free parameters. In tied_gamma, `kappa_v1`, `kappa_v2`, and `alpha` must
be omitted; the first two are derived and the latter has no effect.

Initialization retains TauREx names: `kappa_irr` and `T_int`. Their fitting names
are `kappa_irr` (standard) or `log10_kappa_ir` (tied_gamma), and
`T_int_guillot`, respectively. `T_irr` and `log10_gamma` use the same names in
priors. Isothermal temperature uses `T` in both places. Flat temperature
specifications remain readable for historical results. Other profile families
are not yet implemented by this package.
