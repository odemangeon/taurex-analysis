"""Resolve named external datasets using machine-local configuration."""
import json
import os
from pathlib import Path


def resolve_datasets(settings, base):
    needed = [('opacity_dataset', 'opacity_paths', 'paths'), ('cia_dataset', 'cia_path', 'path')]
    needed = [entry for entry in needed if entry[0] in settings and entry[1] not in settings]
    if not needed:
        return
    explicit = os.environ.get('TAUREX_ANALYSIS_DATA_CONFIG')
    if explicit:
        path = Path(explicit).expanduser().resolve()
    else:
        base = Path(base).resolve()
        path = next((p/'data-paths.local.json' for p in (base,*base.parents)
                     if (p/'data-paths.local.json').is_file()), None)
        if path is None:
            raise ValueError('External datasets require data-paths.local.json; copy data-paths.example.json or set TAUREX_ANALYSIS_DATA_CONFIG')
    data = json.loads(path.read_text())['datasets']
    def absolute(value):
        value = Path(value).expanduser()
        return str((path.parent/value).resolve())
    for dataset_key, path_key, value_key in needed:
        name = settings[dataset_key]
        if name not in data:
            raise ValueError(f'Missing dataset {name!r} in {path}')
        value = data[name][value_key]
        settings[path_key] = [absolute(p) for p in value] if value_key == 'paths' else absolute(value)
