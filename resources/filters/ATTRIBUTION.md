# Instrument response sources

The versioned bundle preserves the original source files and derived responses
byte for byte. `library.json` records hashes, source URLs where available,
detector conventions, interpolation, clipping, and wavelength coverage.
These third-party scientific data are not relicensed by the project.

- Spitzer IRAC/IRS: NASA/IPAC IRSA. Public IRSA data generally have no usage
  restrictions; cite the mission/data products and acknowledge IRSA.
  https://irsa.ipac.caltech.edu/data_use_terms.html
  https://irsa.ipac.caltech.edu/ack.html
- NIRCam: supplied NRCA5 system throughput and grism tables; retain the source
  filenames and acknowledge the instrument team and originating archive.
  STScI's general content policy requests NASA/STScI attribution, with exceptions
  for third-party content: https://www.stsci.edu/copyright
- TESS: NASA/HEASARC response table; source URL is retained in `library.json`.
- CHEOPS: ESA CHEOPS passband; source URL is retained in `library.json`.

A blanket redistribution license for the supplied CHEOPS, TESS, and NIRCam
files was not established from their local metadata. This source inventory is
not a claim that all files share the same license. Confirm product-specific
terms with their providers before public distribution if necessary. No remote
repository was published by this migration.
