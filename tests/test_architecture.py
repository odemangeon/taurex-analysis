"""Regression and dependency-boundary checks for the package workflow."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from taurex_analysis.config import load, resolve
from taurex_analysis.retrieval.problem import build
from taurex_analysis.retrieval.samplers import register
from taurex_analysis.retrieval.samplers.base import SamplingResult
from taurex_analysis.retrieval.runner import retrieve
from taurex_analysis.postprocess.predictions import process
from taurex_analysis.results.loading import load_run

ROOT=Path(__file__).resolve().parents[1]
EXPERIMENT=ROOT/'planets/HD149026b/experiments/blackbody_IRAC2.json'


def test_all_experiment_configs_resolve_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in EXPERIMENT.parent.glob('*.json'):
        config=load(path)
        assert Path(config['inputs']).is_dir()
        assert Path(config['measurements']).is_file()
        if config['model']['family']=='atmosphere':
            assert all(Path(p).is_absolute() for p in config['model']['settings']['opacity_paths'])


def test_likelihood_and_prior_match_taurex():
    from taurex.optimizer.nestle import NestleOptimizer
    from taurex.core.priors import Uniform, Gaussian
    from taurex_analysis.data.observations import Photometry
    config=load(EXPERIMENT);problem=build(config)
    optimizer=NestleOptimizer(model=problem.model,observed=Photometry(problem.rows))
    optimizer.set_prior('T_day',Uniform(bounds=(500,4000)))
    optimizer.set_prior('radius_ratio',Gaussian(mean=.0518,std=.0006))
    optimizer.compile_params()
    point={'T_day':1800.,'radius_ratio':.0518}
    expected=optimizer.log_likelihood([point[n] for n in optimizer.fit_names])
    assert problem.log_likelihood([point[n] for n in problem.names])==pytest.approx(expected,abs=1e-12)
    np.testing.assert_allclose(problem.prior_transform([.5,.5]),[2250,.0518])
    assert problem.prior_transform([.5,1e-10])[1] < .05


def test_nestle_adapter_retains_seed_settings_and_evidence():
    import nestle
    from taurex_analysis.retrieval.samplers.nestle import run
    class Problem:
        names=['x']
        def prior_transform(self,u):return 4*u-2
        def log_likelihood(self,x):return -.5*float(np.sum(x*x))
    problem=Problem()
    result=run(problem,dict(nlive=20,tol=.5),42)
    expected=nestle.sample(problem.log_likelihood,problem.prior_transform,1,npoints=20,dlogz=.5,method='multi',rstate=np.random.RandomState(42))
    np.testing.assert_array_equal(result.samples,expected.samples)
    np.testing.assert_allclose(result.weights,expected.weights)
    assert result.log_evidence==expected.logz
    assert result.log_evidence_error==expected.logzerr


def test_another_planet_uses_explicit_inputs(tmp_path):
    config=load(EXPERIMENT)
    inputs=tmp_path/'other_inputs';shutil.copytree(config['inputs'],inputs)
    system=json.loads((inputs/'system.json').read_text());system['radius_ratio_mean']=.1
    (inputs/'system.json').write_text(json.dumps(system))
    manifest=json.loads((inputs/'manifest.json').read_text());manifest['system']=system
    (inputs/'manifest.json').write_text(json.dumps(manifest))
    original=build(config).model.band_depth('IRAC2')
    config['inputs']=str(inputs);config['measurements']=str(inputs/'measurements.csv')
    other=build(config).model
    assert other.band_depth('IRAC2')==pytest.approx(original*(.1/.0518)**2)


def test_full_pipeline_with_alternate_sampler_and_no_model_imports_for_plot(tmp_path):
    config=load(EXPERIMENT)
    def fake(problem,settings,seed):
        rng=np.random.default_rng(seed)
        samples=np.column_stack((rng.uniform(1600,2000,50),rng.normal(.0518,.0006,50)))
        return SamplingResult(samples,np.arange(1,51,dtype=float),np.array([problem.log_likelihood(s) for s in samples]),problem.names,1.,.1)
    register('test_backend',fake)
    config['sampler']={'backend':'test_backend','settings':{}}
    run=retrieve(config,tmp_path/'run')
    assert not list(run.glob('*.png'))
    assert not (run/'posterior_predictions.npz').exists()
    before={p.name:p.read_bytes() for p in run.iterdir() if p.is_file()}
    analysis=process(run,tmp_path/'analysis',{'bands':['CHEOPS','TESS']})
    assert not list(analysis.glob('*.png'))
    assert before=={p.name:p.read_bytes() for p in run.iterdir() if p.is_file()}
    with np.load(analysis/'posterior_predictions.npz') as data:
        np.testing.assert_allclose(data['tb_quantiles'],np.repeat(data['tb_quantiles'][:,:1],len(data['wavelength_um']),axis=1),rtol=1e-12)
    script='''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('taurex','taurex_fastchem','nestle'):
            raise AssertionError('Plot imported model/sampler dependency: '+fullname)
sys.meta_path.insert(0, Block())
from taurex_analysis.plotting.runner import plot
plot(sys.argv[1])
'''
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
    subprocess.run([sys.executable,'-c',script,str(analysis)],env=env,check=True)
    assert len(list((analysis/'figures').glob('*.png')))==4
    with pytest.raises(ValueError,match='nonempty'):
        retrieve(config,run)
    with pytest.raises(ValueError,match='nonempty'):
        process(run,analysis)


def test_chemistry_factory_boundary():
    from taurex_analysis.models.chemistry import register,create
    marker=object()
    register('test_chemistry',lambda **kwargs:(marker,kwargs))
    result=create({'backend':'test_chemistry','settings':{'metallicity':3}})
    assert result==(marker,{'metallicity':3})
    with pytest.raises(ValueError,match='Unknown chemistry'):
        create({'backend':'unknown'})


def test_invalid_model_rejection_is_sampler_independent():
    from taurex.exceptions import InvalidModelException
    from taurex_analysis.retrieval.problem import RetrievalProblem
    class Model:
        def fitting_parameters(self):return {'x':(None,None,None,lambda value:None)}
        def model(self):raise InvalidModelException('outside opacity grid')
    problem=RetrievalProblem(Model(),[{'depth_ppm':100,'sigma_ppm':10}],{'x':{'type':'uniform','bounds':[0,1]}})
    assert problem.log_likelihood([.5])==-np.inf


def test_blackbody_only_import_does_not_import_chemistry():
    code='from taurex_analysis.models.blackbody import ThermalModel; import sys; assert "taurex_fastchem" not in sys.modules'
    subprocess.run([sys.executable,'-c',code],env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),check=True)


def test_configuration_and_input_provenance_are_verified(tmp_path):
    from taurex_analysis.results.io import save_posterior, write_json
    from taurex_analysis.results.provenance import hashes
    config=load(EXPERIMENT)
    problem=build(config)
    write_json(tmp_path/'experiment.json',config)
    write_json(tmp_path/'observations.json',problem.rows)
    write_json(tmp_path/'provenance.json',{'physical_inputs':{},'artifacts':hashes([tmp_path/'experiment.json',tmp_path/'observations.json'])})
    save_posterior(tmp_path,SamplingResult(np.array([[1800.,.0518]]),np.array([1.]),np.array([0.]),problem.names,0.,.1))
    load_run(tmp_path)
    config['priors']['T_day']['bounds']=[1000,4000]
    write_json(tmp_path/'experiment.json',config)
    with pytest.raises(ValueError,match='Input differs'):
        load_run(tmp_path)


def test_legacy_loader_preserves_prior_coordinates(tmp_path):
    from taurex_analysis.results.loading import legacy_config
    config=load(EXPERIMENT)
    system=json.loads((Path(config['inputs'])/'system.json').read_text())
    provenance={'sha256':{str(Path(config['inputs'])/'stellar_spectrum.npz'):'unused'},
        'arguments':{'temperature_bounds':[500,4000],'fix_radius':False},'input_manifest':{'system':system}}
    result=legacy_config(tmp_path,provenance,{'selected_measurements':[{'band':'IRAC2'}]})
    assert result['priors']['T_day']==dict(type='uniform',bounds=[500,4000])
    assert result['priors']['radius_ratio']['type']=='gaussian'
    assert result['inputs']==config['inputs']
