"""Chemistry factories return TauREx Chemistry implementations.

Adapters expose mixing ratios, molecular weights, gas names and fitting parameters
through TauREx's Chemistry API. Pressures are Pa and temperatures K. A new solver
must explicitly document its reference elemental abundances and metallicity/C/O
conventions; backend-specific settings are preserved in the run configuration.
"""
_FACTORIES = {}

def register(name, factory):
    if name in _FACTORIES or name == 'fastchem':
        raise ValueError(f'Chemistry backend already registered: {name}')
    _FACTORIES[name] = factory

def create(config):
    config = dict(config)
    backend = config.pop('backend', 'fastchem')
    settings = config.pop('settings', config)
    if backend == 'fastchem':
        from .fastchem import CheckedFastChem
        return CheckedFastChem(**settings)
    if backend in _FACTORIES:
        return _FACTORIES[backend](**settings)
    from importlib.metadata import entry_points
    matches = list(entry_points(group='taurex_analysis.chemistry', name=backend))
    if len(matches) != 1:
        raise ValueError(f'Unknown chemistry backend: {backend}')
    return matches[0].load()(**settings)
