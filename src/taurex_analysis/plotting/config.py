"""Presentation settings and consistent band-color resolution."""
from matplotlib.colors import is_color_like
from .common import plt


def validate(config):
    if not isinstance(config, dict) or set(config) - {'bandpass_colors'}:
        raise ValueError('Plot config accepts only bandpass_colors')
    colors = config.get('bandpass_colors', {})
    if not isinstance(colors, dict):
        raise ValueError('bandpass_colors must map names to colors')
    for name, color in colors.items():
        if not isinstance(name, str) or not is_color_like(color):
            raise ValueError(f'Invalid bandpass color for {name!r}: {color!r}')
    return config


def resolve_colors(bands, rows=(), config=None):
    mapping = validate(config or {}).get('bandpass_colors', {})
    rows = {r['band']: r for r in rows}
    result = {}
    for i, band in enumerate(bands):
        row = rows.get(band, {})
        # NIRCam bin IDs encode their parent response before the last hyphen.
        parent = row.get('parent_response')
        if parent is None and band.startswith('NIRCAM-') and band.count('-') >= 2:
            parent = band.rsplit('-', 1)[0]
        keys = (band, row.get('group'), parent)
        fallback = {'CHEOPS': 'tab:purple', 'TESS': 'tab:orange'}.get(band, plt.get_cmap('tab10')(i % 10))
        result[band] = next((mapping[k] for k in keys if k in mapping), fallback)
    return result
