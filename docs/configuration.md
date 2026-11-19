# Experiment configuration

Experiment JSON contains:

- `filters_path`: the shared, versioned response directory (supports `~`);

- `schema_version: 1`, `inputs`, `measurements` (optional), and `selection`;
- `model.family`: `blackbody` or `atmosphere`;
- atmospheric `model.settings`: pressure grid, temperature profile, opacity
  datasets/species, planetary mass/radius, and chemistry backend/settings;
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


Analysis settings are separate: `bands` adds prediction bands to fitted bands,
`posterior_draws: 0` uses every positive-weight sample, and a positive count
requests seeded systematic resampling. `wavelength_um: [min, max, count]`
controls the blackbody spectral grid; atmospheric predictions retain the native
grid. The supplied HD149026b analysis config adds CHEOPS and TESS; the package
does not require those bands for other planets. Resampling may poorly resolve
extreme tails. Brightness temperatures are transformed per sample before
weighted intervals are calculated.

## Schema version and fitted parameters

`schema_version: 1` describes the JSON format, not the experiment or software
version. Leave it unchanged when editing scientific settings.

Only names present in `priors` are sampled. A Gaussian prior still selects a free
parameter. Parameters absent from priors retain configured values or component
defaults. Do not specify equal uniform bounds to fix a parameter; remove its prior.
At least one fitted parameter is required by the retrieval command.

For blackbody models, `model.fixed` supplies explicit values such as
`{"radius_ratio": 0.0518}`. Remove that name from priors as well: the current
implementation does not reject overlap, and sampling overrides the initial value.
For atmosphere models, component settings supply initial/fixed values.

See [temperature parameters](parameters.md) for profile choices, units and naming.

Configure external datasets using the ignored local file described in
[external data](external-data.md). Resolved paths are saved with each run.
