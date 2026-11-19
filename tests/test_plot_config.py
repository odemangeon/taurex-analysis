import pytest
from taurex_analysis.plotting.config import resolve_colors, validate


def test_color_precedence_and_fallback():
    bands=['NIRCAM-F322W2-2.36','NIRCAM-F444W-4.50','IRAC1','TESS','other']
    rows=[dict(band=bands[0],group='group')]
    config={'bandpass_colors':{bands[0]:'red','group':'green','NIRCAM-F444W':'blue'}}
    colors=resolve_colors(bands,rows,config)
    assert colors[bands[0]]=='red'
    assert colors[bands[1]]=='blue'
    assert colors['TESS']=='tab:orange'
    del config['bandpass_colors'][bands[0]]
    assert resolve_colors(bands,rows,config)[bands[0]]=='green'
    assert len(colors)==len(bands)


def test_bad_color_rejected():
    with pytest.raises(ValueError,match='Invalid bandpass color'):
        validate({'bandpass_colors':{'IRAC1':'not-a-color'}})
    with pytest.raises(ValueError):
        validate({'unknown':True})
