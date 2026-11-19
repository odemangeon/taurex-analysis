# Architecture and extensions

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
retrieval setup. `planets/HD149026b/inputs` contains portable runtime inputs. Historical inputs
are retained separately for saved-result compatibility. Original result
folders and their provenance have not been moved or rewritten. Existing tests
remain alongside their original workflows; package architecture tests are in
`tests/`.

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
