# Getting started

## Installation and execution

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

For atmospheric runs, first configure [external datasets](external-data.md).
