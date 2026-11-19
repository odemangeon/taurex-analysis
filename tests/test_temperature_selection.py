import numpy as np
import pytest
from taurex_analysis.models.temperature import create_temperature, TiedGuillot2010


def test_explicit_tied_matches_legacy():
    values=dict(T_irr=1800,T_int=100,kappa_irr=.001,log10_gamma=-.3)
    old=create_temperature(values)
    new=create_temperature(dict(profile='guillot2010',parameterization='tied_gamma',parameters=values))
    assert isinstance(new,TiedGuillot2010)
    assert new.kappa_v1==old.kappa_v1==new.kappa_v2
    assert 'log10_gamma' in new.fitting_parameters()


def test_isothermal():
    model=create_temperature(dict(profile='isothermal',parameters={'T':1700}))
    assert model.fitting_parameters()['T'][2]()==1700


def test_redundant_opacity_rejected():
    with pytest.raises(ValueError,match='Derived'):
        create_temperature(dict(profile='guillot2010',parameterization='tied_gamma',parameters=dict(log10_gamma=0,kappa_v1=.1)))


def test_unknown_profile_rejected():
    with pytest.raises(ValueError,match='Unsupported'):
        create_temperature(dict(profile='unknown',parameters={}))
