"""Configuration paths are relative to the JSON file, never the working directory."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np


def load(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text())
    return resolve(config, path.parent)


def resolve(config, base):
    config = deepcopy(config)
    base = Path(base)
    def absolute(value):
        path = Path(value).expanduser()
        return str((base/path).resolve() if not path.is_absolute() else path.resolve())
    if config.get('schema_version') != 1:
        raise ValueError('Expected experiment schema_version 1')
    if config.get('model', {}).get('family') not in ('blackbody', 'atmosphere'):
        raise ValueError('Model family must be blackbody or atmosphere')
    config['inputs'] = absolute(config['inputs'])
    if 'filters_path' in config:
        config['filters_path'] = absolute(config['filters_path'])
    config['measurements'] = absolute(config.get('measurements', str(Path(config['inputs'])/'measurements.csv')))
    if not config.get('selection') or not all(isinstance(s, str) for s in config['selection']):
        raise ValueError('selection must contain measurement IDs or groups')
    model = config['model']
    if model['family'] == 'atmosphere':
        settings = model['settings']
        from .data.locations import resolve_datasets
        resolve_datasets(settings, base)
        settings['opacity_paths'] = [absolute(p) for p in settings['opacity_paths']]
        settings['cia_path'] = absolute(settings['cia_path'])
        if 'planet' not in settings:
            system = json.loads((Path(config['inputs'])/'system.json').read_text())
            settings['planet'] = system['planet']
        settings['fit'] = {name: prior.get('bounds', [.001, 1.]) for name, prior in config['priors'].items()}
    if not config.get('priors'):
        raise ValueError('At least one fitted parameter is required')
    for name, prior in config['priors'].items():
        if prior['type'] == 'uniform':
            lo, hi = prior['bounds']
            if not np.isfinite([lo, hi]).all() or lo >= hi:
                raise ValueError(f'Invalid uniform prior: {name}')
        elif prior['type'] == 'gaussian':
            if not np.isfinite([prior['mean'], prior['sigma']]).all() or prior['sigma'] <= 0:
                raise ValueError(f'Invalid Gaussian prior: {name}')
        else:
            raise ValueError(f'Unsupported prior: {prior}')
    sampler = config.setdefault('sampler', {'backend': 'nestle', 'settings': {}})
    settings = sampler.setdefault('settings', {})
    if int(settings.get('nlive', 600)) < 20 or settings.get('tol', .1) <= 0:
        raise ValueError('Require nlive >=20 and tol >0')
    config.setdefault('seed', 0)
    return config
