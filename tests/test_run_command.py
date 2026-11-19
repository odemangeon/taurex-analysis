from pathlib import Path
import json
import pytest
from taurex_analysis.cli import main


def test_run_sequences_stages_with_separate_configs(tmp_path,monkeypatch):
    import taurex_analysis.config as config
    import taurex_analysis.retrieval.runner as retrieval
    import taurex_analysis.postprocess.predictions as post
    import taurex_analysis.plotting.runner as plotting
    calls=[]
    monkeypatch.setattr(config,'load',lambda path:{'model':{'family':'blackbody'},'sampler':{'settings':{}}})
    def retrieve(c,out,check=False):
        calls.append(('retrieve',out,check));return out
    def process(source,out,options):
        calls.append(('process',source,out,options));return out
    monkeypatch.setattr(retrieval,'retrieve',retrieve)
    monkeypatch.setattr(post,'process',process)
    monkeypatch.setattr(plotting,'plot',lambda source,config: calls.append(('plot',source,config)))
    analysis=tmp_path/'analysis.json';analysis.write_text('{"bands":["TESS"]}')
    colors=tmp_path/'plots.json';colors.write_text('{"bandpass_colors":{"TESS":"red"}}')
    out=tmp_path/'run'
    main(['run','experiment.json','--output',str(out),'--analysis-config',str(analysis),'--plot-config',str(colors)])
    assert calls==[('retrieve',out,False),('process',out,out/'analysis',{'bands':['TESS']}),('plot',out/'analysis',{'bandpass_colors':{'TESS':'red'}})]
    calls.clear()
    colors.write_text('{"bandpass_colors":{"TESS":"invalid-color"}}')
    with pytest.raises(ValueError):
        main(['run','experiment.json','--output',str(out),'--plot-config',str(colors)])
    assert calls==[]
