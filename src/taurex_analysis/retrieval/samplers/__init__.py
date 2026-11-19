"""A registered backend implements run(problem, settings, seed)."""
_BACKENDS = {}

def register(name, run):
    if name in _BACKENDS or name == 'nestle':
        raise ValueError(f'Sampler already registered: {name}')
    _BACKENDS[name] = run

def sample(problem, config, seed):
    name = config['backend']
    if name == 'nestle':
        from .nestle import run
    elif name in _BACKENDS:
        run = _BACKENDS[name]
    else:
        from importlib.metadata import entry_points
        matches = list(entry_points(group='taurex_analysis.samplers', name=name))
        if len(matches) != 1:
            raise ValueError(f'Unknown or ambiguous sampler {name!r}; register an adapter before running')
        run = matches[0].load()
    return run(problem, config.get('settings', {}), seed).validate()
