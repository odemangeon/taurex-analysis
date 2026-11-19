# TauREx Analysis

A configurable workflow for thermal eclipse retrievals and posterior analysis.

The workflow separates three operations:

1. **Retrieve:** fit a forward model and save the weighted posterior and evidence.
2. **Postprocess:** evaluate saved samples to obtain spectra, band predictions,
   brightness temperatures and atmospheric diagnostics.
3. **Plot:** render saved products without loading TauREx, chemistry or opacity data.

Start with [installation and execution](getting-started.md), then consult
[experiment configuration](configuration.md) and the
[parameter reference](parameters.md).

## What is implemented

| Component | Available choices |
| --- | --- |
| Model family | Blackbody, atmospheric thermal emission |
| Temperature profile | Guillot 2010, isothermal |
| Guillot parameterization | Standard, tied gamma |
| Sampler | Nestle; adapter interface for other samplers |
| Equilibrium chemistry | FastChem; factory interface for other solvers |
| Inputs | Photometry and response-integrated spectral bins |

Dynesty and point-based TP profiles are not currently implemented in this package.

## Interpretation

These are thermal-only models. Optical extrapolations do not include reflected
light. Posterior intervals are conditional on the selected stellar spectrum,
response curves, model, measurement uncertainties and priors. The likelihood
assumes independent Gaussian measurement errors. A software smoke test is not a
scientific retrieval or a convergence test.

Use [results and provenance](results.md) to understand saved products and
historical compatibility. See [architecture](architecture.md) to add backends,
and [publishing](publishing.md) to maintain this documentation.
