# Repository data and external opacity tables

Small response curves, XML metadata and original sources are included in
`resources/filters/responses-ba0a74ab22aaad5d/`. Experiments use a relative
`filters_path`; their byte content and detector conventions are unchanged.
The bundle's `library.json` verifies checksums. See its sibling
`ATTRIBUTION.md` for source acknowledgements and the limits of the redistribution
information established so far.

Planet runtime inputs are real files under `planets/HD149026b/inputs`, not a link
into the ignored historical analysis directory. Compatibility response links
are relative and stay within the repository. NIRCam bins remain planet-specific.
Historical inputs/results and the external filter copy are retained to keep
saved provenance paths working.

## Configure large external datasets

Cross-sections and CIA tables are not included. The experiments select
`opacity_dataset: "exomol-xsec"` and `cia_dataset: "hydrogen-cia"`.

```bash
cp data-paths.example.json data-paths.local.json
```

Edit the local file to point to your downloaded tables:

```json
{
  "datasets": {
    "exomol-xsec": {"paths": ["~/Data/taurex_data/xsec"]},
    "hydrogen-cia": {"path": "~/Data/taurex_data/cia"}
  }
}
```

The local file is ignored by Git. The loader searches from the experiment
folder upwards. Set `TAUREX_ANALYSIS_DATA_CONFIG` to select a different file.
Relative paths inside it are relative to that file, not the working directory.
Blackbody runs need no opacity configuration. Saved runs retain resolved
absolute paths and can be loaded without consulting the local configuration;
legacy explicit opacity/CIA paths remain supported.

## Obtain compatible tables

Obtain cross-sections from ExoMol's opacity catalog and CIA tables from HITRAN's
CIA catalog. Choose TauREx-compatible formats and tables covering your required
species, wavelengths, pressures and temperatures; retain the provider citations.
The experiment's `absorbers` and `cia_pairs` settings select the required species
and pairs. Local dataset names identify directories, not frozen inventories.
`*.h5`, `*.hdf5`, and `*.cia` are ignored by Git.

You can add or replace tables for new retrievals without updating a global
manifest. Each run records its resolved inputs and their hashes in
`provenance.json`. Keep the original files available if you want to reproduce
that run: hashes identify and verify files but cannot recover their contents.
Use a new output directory when running with changed data.

Post-processing an existing run still checks its saved physical-input hashes
and rejects changed inputs. Preserve historical provenance rather than editing
it to accept replacement tables. The versioned filter bundle's `library.json`
is separate from the external opacity inventory and remains in use.
