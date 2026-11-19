"""Input and code provenance, separate from scientific products."""
import hashlib
import importlib.metadata
from pathlib import Path

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def hashes(paths):
    return {str(Path(p).resolve()): sha256(p) for p in sorted(set(map(Path, paths)))}

def verify(expected):
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise ValueError(f'Input differs from saved retrieval: {path}')

def versions():
    result = {}
    for package in ('numpy', 'scipy', 'taurex', 'nestle', 'dynesty', 'taurex-fastchem', 'pyfastchem'):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    return result
