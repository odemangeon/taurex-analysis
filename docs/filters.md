# Shared filter library

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

