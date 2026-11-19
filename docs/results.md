# Results and provenance


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
