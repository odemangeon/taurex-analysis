"""Immutable, content-addressed instrument response bundles.

Spectral-bin definitions stay with observations. A bundle contains response
curves, source files and their detector conventions, never planetary inputs.
"""
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def describe(inputs):
    inputs = Path(inputs)
    manifest = json.loads((inputs/'manifest.json').read_text())
    directory = inputs/'filters'
    paths = [directory/f'{name}.csv' for name in manifest['filters']]
    paths += [directory/f'{name}.xml' for name in manifest['filters']
              if (directory/f'{name}.xml').exists()]
    paths += [p for p in (directory/'source_files').rglob('*') if p.is_file()]
    files = {str(p.relative_to(directory)): digest(p) for p in sorted(paths)}
    metadata = {name.removeprefix('filters/'): value
                for name, value in manifest.get('files', {}).items()
                if name.removeprefix('filters/') in files}
    return dict(schema_version=1, filters=manifest['filters'], files=files,
                preparation_metadata=metadata)


def publish(inputs, library):
    """Copy a bundle once; an existing version must match byte for byte."""
    inputs, library = Path(inputs), Path(library).expanduser()
    description = describe(inputs)
    identity = hashlib.sha256(json.dumps(description, sort_keys=True).encode()).hexdigest()
    destination = library/f'responses-{identity[:16]}'
    if destination.exists():
        if json.loads((destination/'library.json').read_text()) != description:
            raise ValueError(f'Existing response version differs: {destination}')
        validate(destination)
        return destination
    destination.mkdir(parents=True)
    for name, expected in description['files'].items():
        source = inputs/'filters'/name
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(target) != expected:
            raise ValueError(f'Response changed during publication: {source}')
    (destination/'library.json').write_text(json.dumps(description, indent=2)+'\n')
    validate(destination)
    return destination


def validate(directory):
    """Validate bundle contents before using its metadata or responses."""
    directory = Path(directory)
    description = json.loads((directory/'library.json').read_text())
    if description.get('schema_version') != 1:
        raise ValueError('Unsupported filter library schema')
    for name, expected in description['files'].items():
        if digest(directory/name) != expected:
            raise ValueError(f'Filter library content changed: {directory/name}')
    return description


def response_directory(inputs, filters_path=None):
    """Explicit config wins; local aliases support historical runs unchanged."""
    return Path(filters_path).expanduser() if filters_path is not None else Path(inputs)/'filters'


def refuse_linked_outputs(directory):
    """Preparation must not overwrite the shared snapshots via old aliases."""
    directory = Path(directory)
    if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('Input preparation would overwrite linked shared filters. '
                         'Prepare in a separate inputs directory, then publish a new response version.')
