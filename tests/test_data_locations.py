import json
from pathlib import Path
import shutil
import pytest
from taurex_analysis.config import load
from taurex_analysis.data.locations import resolve_datasets
from taurex_analysis.retrieval.problem import build

ROOT=Path(__file__).resolve().parents[1]


def test_local_paths_are_relative_to_settings_file(tmp_path,monkeypatch):
    p=tmp_path/'local.json'
    p.write_text(json.dumps({'datasets':{'x':{'paths':['tables']},'c':{'path':'cia'}}}))
    monkeypatch.setenv('TAUREX_ANALYSIS_DATA_CONFIG',str(p))
    settings={'opacity_dataset':'x','cia_dataset':'c'}
    resolve_datasets(settings,tmp_path/'elsewhere')
    assert settings['opacity_paths']==[str(tmp_path/'tables')]
    assert settings['cia_path']==str(tmp_path/'cia')
    p.unlink()
    resolve_datasets(settings,tmp_path)  # Saved resolved settings need no local file.


def test_missing_configuration_has_actionable_error(tmp_path,monkeypatch):
    monkeypatch.delenv('TAUREX_ANALYSIS_DATA_CONFIG',raising=False)
    with pytest.raises(ValueError,match='data-paths.example.json'):
        resolve_datasets({'opacity_dataset':'x'},tmp_path)


def test_clone_blackbody_has_no_external_filter_or_historical_dependency(tmp_path,monkeypatch):
    shutil.copytree(ROOT/'planets',tmp_path/'planets',symlinks=True)
    shutil.copytree(ROOT/'resources/filters',tmp_path/'resources/filters')
    monkeypatch.chdir(tmp_path)
    config=load(tmp_path/'planets/HD149026b/experiments/blackbody_IRAC2.json')
    model=build(config).model
    assert model.band_depth('IRAC2')>0
    for p in (tmp_path/'planets').rglob('*'):
        if p.is_symlink():
            assert p.exists()
            assert p.resolve().is_relative_to(tmp_path)
