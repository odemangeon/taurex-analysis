# Comparisons


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
