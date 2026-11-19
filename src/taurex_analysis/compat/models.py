"""Historical folder APIs. New callers must pass inputs explicitly."""
from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
from .paths import INPUTS, PLANET
from taurex_analysis.models.blackbody import ThermalModel as _ThermalModel
from taurex_analysis.data.measurements import read_measurements, read_selection
from taurex_analysis.data.observations import Photometry
from taurex_analysis.physics.blackbody import blackbody

class ThermalModel(_ThermalModel):
    def __init__(self, rows, inputs=INPUTS):
        super().__init__(rows, inputs)

shared = SimpleNamespace(INPUTS=INPUTS,ThermalModel=ThermalModel,Photometry=Photometry,
    read_measurements=read_measurements,read_selection=read_selection,blackbody=blackbody)

# Lazy atmospheric dependencies keep the blackbody workflow independent of FastChem.
def __getattr__(name):
    if name == 'AtmosphericPhotometry':
        from taurex_analysis.models.atmosphere import AtmosphericPhotometry as Base
        class AtmosphericPhotometry(Base):
            def __init__(self, rows, config, stride=1, inputs=INPUTS):
                config=deepcopy(config)
                base=PLANET/'guillot_baseopacity_fullSpitzer'
                config['opacity_paths']=[str((base/p).resolve()) for p in config['opacity_paths']]
                config['cia_path']=str((base/config['cia_path']).resolve())
                super().__init__(rows,config,inputs,stride=stride)
        return AtmosphericPhotometry
    raise AttributeError(name)
