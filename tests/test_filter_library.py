"""Shared response bundles preserve integration and historical paths."""
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from taurex_analysis.config import resolve
from taurex_analysis.data.filter_library import publish, validate, refuse_linked_outputs
from taurex_analysis.data.measurements import read_measurements
from taurex_analysis.models.blackbody import ThermalModel
from taurex_analysis.retrieval.runner import physical_paths
from taurex_analysis.results.provenance import hashes, verify

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT/'planets/HD149026b/inputs'


def test_shared_library_reproduces_irac_and_nircam_and_tracks_sources(tmp_path):
    directory = publish(INPUTS, tmp_path/'library')
    description = validate(directory)
    assert 'NIRCAM_bins.csv' not in description['files']
    assert 'source_files/NIRCam_GRISM_TP.csv' in description['files']
    assert publish(INPUTS, tmp_path/'library') == directory
    rows = read_measurements(INPUTS/'measurements.csv', ['IRAC', 'NIRCAM-F322W2', 'NIRCAM-F444W'])
    original = ThermalModel(rows, INPUTS)
    shared = ThermalModel(rows, INPUTS, filters_path=directory)
    for band in [r['band'] for r in rows]+['CHEOPS','TESS']:
        assert shared.band_depth(band) == original.band_depth(band)
    config = dict(inputs=str(INPUTS), measurements=str(INPUTS/'measurements.csv'),filters_path=str(directory))
    paths = physical_paths(config, shared)
    assert directory/'library.json' in paths
    assert directory/'IRAC1.csv' in paths
    assert INPUTS/'filters/NIRCAM_bins.csv' in paths
    assert directory/'source_files/NIRCam_GRISM_TP.csv' in paths
    with (directory/'IRAC1.csv').open('a') as handle:
        handle.write('\n')
    with pytest.raises(ValueError,match='content changed'):
        ThermalModel(rows, INPUTS, filters_path=directory)


def test_explicit_external_responses_work_without_local_curves(tmp_path):
    directory = publish(INPUTS, tmp_path/'library')
    inputs = tmp_path/'planet'
    inputs.mkdir()
    for name in ('system.json','manifest.json','stellar_spectrum.npz','measurements.csv'):
        shutil.copyfile(INPUTS/name,inputs/name)
    (inputs/'filters').mkdir()
    shutil.copyfile(INPUTS/'filters/NIRCAM_bins.csv',inputs/'filters/NIRCAM_bins.csv')
    rows = read_measurements(inputs/'measurements.csv',['NIRCAM-F444W'])
    model = ThermalModel(rows,inputs,filters_path=directory)
    assert np.isfinite(model.band_depth(rows[0]['band']))
    assert not (inputs/'filters/IRAC1.csv').exists()


def test_legacy_hashes_follow_aliases_but_detect_changed_bytes(tmp_path):
    old = tmp_path/'old'; old.mkdir()
    response = old/'response.csv';response.write_text('original')
    expected = hashes([response])
    new = tmp_path/'shared.csv';response.rename(new)
    response.symlink_to(new)
    verify(expected)
    with pytest.raises(ValueError,match='linked shared filters'):
        refuse_linked_outputs(old)
    new.write_text('changed')
    with pytest.raises(ValueError,match='Input differs'):
        verify(expected)


def test_filter_path_resolves_relative_to_experiment(tmp_path):
    config = json.loads((ROOT/'planets/HD149026b/experiments/blackbody_IRAC2.json').read_text())
    config['inputs'] = str(INPUTS)
    config['filters_path'] = '../responses'
    assert resolve(config,tmp_path)['filters_path'] == str((tmp_path/'../responses').resolve())
