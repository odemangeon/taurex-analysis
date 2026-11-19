"""Prepare shared inputs from cached official response files and PHOENIX."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import numpy as np
from .nircam import prepare_nircam
from astropy.io import fits
from astropy.io.votable import parse_single_table

FILTERS = {f"IRAC{i}": f"Spitzer/IRAC.ch{i}.080924.subarray" for i in range(1, 5)}
FILTERS.update({
           "IRS16": "Spitzer/IRS.Blue.PeakUp.2V", "CHEOPS": "ESA/CHEOPS.band",
           "TESS": "NASA/TESS.v2.0"})
TESS_URL = 'https://heasarc.gsfc.nasa.gov/docs/tess/data/tess-response-function-v2.0.csv'
CHEOPS_URL = 'https://www.cosmos.esa.int/documents/10651/6260921/CHEOPS_bandpass.csv/'
IRAC_URL = 'https://irsa.ipac.caltech.edu/data/SPITZER/docs/irac/calibrationfiles/spectralresponse/'
IRS16_URL = 'https://irsa.ipac.caltech.edu/data/SPITZER/docs/files/spitzer/bluePUtrans.txt'


def prepare_irs16(path, files, root):
    """Clip negatives and truncate at 20 microns, as authorized by the owner."""
    source = path.parent / 'source_files' / 'IRS16_Blue_PeakUp_FilterTransmissionCurve copy.csv'
    # This user-supplied CSV is reformatted from the official plain-text table;
    # do not replace it with a download in a different format if it is missing.
    files[str(source.relative_to(root))] = {
        'url': IRS16_URL, 'format': 'user-supplied CSV',
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    data = np.loadtxt(source, delimiter=',')
    if not np.all(np.isfinite(data)):
        raise ValueError('Invalid IRS16 source: nonfinite values')
    negative_count = int(np.count_nonzero(data[:, 1] < 0))
    data[:, 1] = np.maximum(data[:, 1], 0)
    # Explicit approximation: ignore the long-wavelength tail. A zero endpoint
    # closes the response without interpolating across the discarded tail.
    data = np.vstack((data[data[:, 0] < 20.0], [20.0, 0.0]))
    write_photon_response(path, files, source, IRS16_URL, 'IRS16', data,
        'Locally generated from the supplied IRS Blue Peak-Up CSV, nominal 2.0 V. '
        'Source wavelengths are in microns; response is RQE times transmission '
        '(electrons per photon), including photoconductive gain. '
        f'{negative_count} negative response values set to zero with project-owner approval; '
        'Response assumed zero at and above 20 microns with project-owner approval: '
        'samples below 20 microns retained and a zero endpoint inserted at 20 microns; '
        'longer-wavelength samples omitted. This discards a nonzero tail as an approximation. '
        'No normalization applied. '
        'Original source file unchanged. Apply lambda once when integrating F_lambda. '
        'No SVO calibration metadata is carried over.', wavelength_to_angstrom=1e4, root=root)
    files[str(path.relative_to(root))].update({
        'negative_response_policy': 'clip_to_zero',
        'negative_values_clipped': negative_count,
        'long_wavelength_cutoff_um': 20.0,
        'long_wavelength_policy': 'zero_at_and_above_cutoff; truncate_with_zero_endpoint'})


def prepare_irac(path, files, band, root):
    """Use the supplied subarray response in electrons per incident photon."""
    filename = f'080924ch{band[-1]}trans_sub.txt'
    source = path.parent / 'source_files' / f'Spitzer_{filename}'
    url = IRAC_URL + filename
    files[str(source.relative_to(root))] = download(url, source)
    data = np.loadtxt(source)
    write_photon_response(path, files, source, url, band, data,
        'Locally generated from the official Spitzer IRAC 080924 subarray response. '
        'Source wavelengths are in microns; response is electrons per photon. '
        'Response values preserved without normalization or wavelength weighting. '
        'Apply lambda once when integrating F_lambda. '
        'No SVO calibration metadata is carried over.', wavelength_to_angstrom=1e4, root=root)


def prepare_tess(path, files, root):
    """Wrap NASA's photon response in a local VOTable, without lambda weighting."""
    source = path.parent / 'source_files' / 'tess-response-function-v2.0.csv'
    files[str(source.relative_to(root))] = download(TESS_URL, source)
    data = np.loadtxt([line for line in source.read_text().splitlines() if line.strip()],
                      delimiter=',')
    write_photon_response(path, files, source, TESS_URL, 'TESS', data,
        'Locally generated from the NASA TESS v2.0 CSV. Photon-counting response; '
        'apply lambda once when integrating F_lambda. Convention confirmed with '
        'the NASA TESS team by the project owner; the original CSV column label '
        'is ambiguous. No SVO calibration metadata is carried over.', root=root)


def prepare_cheops(path, files, root):
    """Use the complete ESA PASSBAND (QE times throughput), with wavelengths in nm."""
    source = path.parent / 'source_files' / 'CHEOPS_bandpass.csv'
    files[str(source.relative_to(root))] = download(CHEOPS_URL, source)
    data = np.genfromtxt(source, delimiter=',', names=True)
    response = np.column_stack((data['WAVELENGTH'], data['PASSBAND']))
    write_photon_response(path, files, source, CHEOPS_URL, 'CHEOPS', response,
        'Locally generated from the official ESA CHEOPS_bandpass.csv. '
        'WAVELENGTH in nm converted to Angstrom; PASSBAND values preserved. '
        'PASSBAND includes quantum efficiency and optical throughput. '
        'Photon-counting response: apply lambda once when integrating F_lambda. '
        'No SVO calibration metadata is carried over.', root=root)


def write_photon_response(path, files, source, url, band, data, description,
                          wavelength_to_angstrom=10, *, root):
    """Write an unweighted photon response; input wavelengths default to nm."""
    if Path(path).is_symlink():
        raise ValueError('Cannot overwrite a linked shared response; prepare a new local version')
    wl, response = data.T
    if (len(wl) < 3 or not np.all(np.isfinite(data)) or np.any(np.diff(wl) <= 0)
            or np.any(wl <= 0) or np.any(response < 0) or not np.any(response > 0)):
        raise ValueError(f'Invalid {band} response')
    xml_root = ET.Element('VOTABLE', version='1.1')
    table = ET.SubElement(ET.SubElement(xml_root, 'RESOURCE', type='results'), 'TABLE')
    ET.SubElement(table, 'DESCRIPTION').text = description
    for name, value in [('filterID', FILTERS[band]), ('WavelengthUnit', 'Angstrom'),
                        ('DetectorType', '1'), ('ProfileReference', url),
                        ('Instrument', 'IRAC' if band.startswith('IRAC') else
                         'IRS' if band == 'IRS16' else band),
                        ('Facility', 'Spitzer' if band.startswith('IRAC') or band == 'IRS16' else band)]:
        param = ET.SubElement(table, 'PARAM', name=name, value=value,
                              datatype='char', arraysize='*')
        if name == 'DetectorType':
            ET.SubElement(param, 'DESCRIPTION').text = '0:Energy counter, 1:Photon counter.'
    ET.SubElement(table, 'FIELD', name='Wavelength', unit='Angstrom', datatype='double')
    ET.SubElement(table, 'FIELD', name='Transmission', datatype='double')
    rows = ET.SubElement(ET.SubElement(table, 'DATA'), 'TABLEDATA')
    for wavelength, transmission in data:
        row = ET.SubElement(rows, 'TR')
        ET.SubElement(row, 'TD').text = format(wavelength * wavelength_to_angstrom, '.17g')
        ET.SubElement(row, 'TD').text = format(transmission, '.17g')
    ET.indent(xml_root, space='  ')
    ET.ElementTree(xml_root).write(path, encoding='utf-8', xml_declaration=True)
    files[str(path.relative_to(root))] = {
        'url': url, 'derived_from': str(source.relative_to(root)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def download(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {url}", flush=True)
        with urlopen(url, timeout=90) as response:
            data = response.read()
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_bytes(data)
        temp.replace(path)
    return {"url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def prepare(root, nircam_literature=None):
    from .filter_library import refuse_linked_outputs
    refuse_linked_outputs(Path(root)/'filters')
    root = Path(root)
    config = json.loads((root / 'system.json').read_text())
    manifest = {"system": config, "files": {}, "filters": {}}
    for name, identifier in FILTERS.items():
        path = root / 'filters' / f'{name}.xml'
        path.parent.mkdir(exist_ok=True)
        if name.startswith('IRAC'):
            prepare_irac(path, manifest['files'], name, root)
        elif name == 'TESS':
            prepare_tess(path, manifest['files'], root)
        elif name == 'CHEOPS':
            prepare_cheops(path, manifest['files'], root)
        elif name == 'IRS16':
            prepare_irs16(path, manifest['files'], root)
        else:
            raise ValueError(f'No source preparation defined for {name}')
        table = parse_single_table(path).to_table()
        params = {p.attrib['name']: p.attrib.get('value') for p in ET.parse(path).iter('PARAM')}
        detector = int(params['DetectorType'])
        if detector not in (0, 1):
            raise ValueError(f'Unknown detector type: {name}')
        wl = np.asarray(table['Wavelength'], float) * 1e-4  # Angstrom -> micron
        response = np.asarray(table['Transmission'], float)
        if len(wl) < 3 or np.any(response < 0) or not np.any(response > 0):
            raise ValueError(f'Invalid filter {name}')
        order = np.argsort(wl)
        np.savetxt(path.with_suffix('.csv'), np.c_[wl[order], response[order]],
                   delimiter=',', header='wavelength_um,response', comments='')
        manifest['filters'][name] = {'id': identifier, 'detector_type': detector,
                                     'weighting': 'photon' if detector else 'energy'}
    if nircam_literature is not None:
        prepare_nircam(manifest, root, nircam_literature)
    # Use validated +0.3 dex grid, close to the measured +0.36 dex.
    # Several older +0.5 / 6100 K files fail bolometric validation; never use them.
    t, g = (config[k] for k in ('stellar_teff_K', 'stellar_logg_cgs'))
    if not (6000 <= t <= 6200 and 4.0 <= g <= 4.5 and config['phoenix_grid_metallicity_dex'] == 0.3):
        raise ValueError('Supported grid: Teff 6000–6200, logg 4–4.5, metallicity +0.3; extend validated brackets for other choices.')
    flux = None
    wavelength = None
    manifest['phoenix_interpolation'] = {'temperature_bracket_K': [6000, 6200],
        'logg_bracket': [4.0, 4.5], 'metallicity_dex': 0.3, 'bolometric_ratios': {}}
    from scipy.constants import Stefan_Boltzmann
    for temp in (6000, 6200):
        wt = (6200-t)/200 if temp == 6000 else (t-6000)/200
        filename = f'phoenixp03_{temp}.fits'
        path = root / 'phoenix' / filename
        path.parent.mkdir(exist_ok=True)
        url = f'https://ssb.stsci.edu/trds/grid/phoenix/phoenixp03/{filename}'
        manifest['files'][str(path.relative_to(root))] = download(url, path)
        with fits.open(path) as hdus:
            data = hdus[1].data
            wl = np.asarray(data['WAVELENGTH'], float) * 1e-4
            for column in ('g40', 'g45'):
                ratio = float(np.trapezoid(data[column]*10, wl)/(Stefan_Boltzmann*temp**4))
                manifest['phoenix_interpolation']['bolometric_ratios'][filename+':'+column] = ratio
                if not .92 < ratio < 1.08:
                    raise ValueError(f'PHOENIX flux validation failed: {filename} {column}: {ratio}')
            # FLAM erg/s/cm^2/Angstrom -> W/m^2/micron: factor 10.
            f = ((4.5-g)/0.5 * data['g40'] + (g-4.0)/0.5 * data['g45']) * 10
        if wavelength is None:
            wavelength = wl
            flux = np.zeros_like(wl)
        if wl[0] > wavelength[0] or wl[-1] < wavelength[-1]:
            raise ValueError('PHOENIX grids have incompatible coverage')
        flux += wt * np.interp(wavelength, wl, f)
    if np.any(flux <= 0) or np.any(np.diff(wavelength) <= 0):
        raise ValueError('Invalid PHOENIX spectrum')
    np.savez(root / 'stellar_spectrum.npz', wavelength_um=wavelength,
             surface_flux_W_m2_um=flux)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Shared inputs ready.')

