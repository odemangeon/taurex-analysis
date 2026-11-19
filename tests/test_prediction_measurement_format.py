"""Measurement names align with brightness rows, independently of plotting."""
import json
from pathlib import Path
import numpy as np
from taurex_analysis.config import load
from taurex_analysis.retrieval.problem import build
from taurex_analysis.results.io import write_json, save_posterior
from taurex_analysis.results.provenance import hashes
from taurex_analysis.retrieval.runner import physical_paths
from taurex_analysis.retrieval.samplers.base import SamplingResult
from taurex_analysis.postprocess.predictions import process


def test_measurement_output_format(tmp_path):
    root=Path(__file__).resolve().parents[1]
    config=load(root/'planets/HD149026b/experiments/blackbody_fullSpitzer.json')
    problem=build(config)
    rows=[dict(row,enabled='true') for row in problem.rows]
    source=tmp_path/'run';source.mkdir()
    write_json(source/'experiment.json',config)
    write_json(source/'observations.json',rows)
    write_json(source/'provenance.json',{'physical_inputs':hashes(physical_paths(config,problem.model))})
    values={'T_day':1800.,'radius_ratio':.0518}
    samples=np.array([[values[n] for n in problem.names]])
    save_posterior(source,SamplingResult(samples,np.ones(1),np.array([problem.log_likelihood(samples[0])]),problem.names,0.,0.))
    output=process(source,tmp_path/'analysis',{'bands':['CHEOPS','TESS']})
    written=json.loads((output/'analysis.json').read_text())['rows']
    assert written==[{k:v for k,v in r.items() if k!='enabled'} for r in rows]
    assert all('sigma_ppm' in r for r in written)
    with np.load(output/'posterior_predictions.npz',allow_pickle=False) as data:
        assert data['bands_meas_tb'].tolist()==[r['band'] for r in rows]
        assert data['measurement_tb'].shape==(len(rows),4)
        np.testing.assert_array_equal(data['measurement_tb'][:,0],[r['wavelength_um'] for r in rows])
        assert 'CHEOPS' in data['bands'] and 'CHEOPS' not in data['bands_meas_tb']
        assert data['bands_meas_tb'].dtype.kind=='U'
    assert json.loads((source/'observations.json').read_text())==rows
