import json
import csv
import numpy as np
from taurex_analysis.postprocess.bands import band_quantiles, COLUMNS

def plot(output, bins=60, log_depth=False):
    from .common import plt
    report = json.loads((output / 'predictive_provenance.json').read_text())
    with np.load(output / 'predictive_samples.npz') as saved:
        bands = saved['bands'].tolist()
        datasets = [(saved['prior_depths_ppm'], np.ones(len(saved['prior_depths_ppm'])),
                     'Prior', '0.65'),
                    (saved['posterior_depths_ppm'], saved['posterior_weights'],
                     'Posterior', '#2166ac')]
    fig, axes = plt.subplots(1, len(bands), figsize=(6 * len(bands), 4.8), squeeze=False)
    rows = []
    for j, (band, ax) in enumerate(zip(bands, axes[0])):
        valid_data = []
        for depths, weights, label, color in datasets:
            valid = np.isfinite(depths).all(axis=1) & (weights > 0)
            if not valid.any():
                raise ValueError(f'No valid {label.lower()} predictions; see saved failure report')
            values, weights = depths[valid, j], weights[valid]
            valid_data.append((values, weights / weights.sum(), label, color))
        all_values = np.concatenate([d[0] for d in valid_data])
        lo, hi = all_values.min(), all_values.max()
        if log_depth and lo <= 0:
            raise ValueError('Log depth requires strictly positive predictions; use the linear axis')
        if hi == lo:
            lo, hi = (lo * .99, hi * 1.01) if lo > 0 else (0, 1)
        edges = np.geomspace(lo, hi, bins + 1) if log_depth else np.linspace(lo, hi, bins + 1)
        for k, (values, weights, label, color) in enumerate(valid_data):
            conditional = report[label.lower()]['invalid_count'] > 0
            ax.hist(values, bins=edges, weights=weights, density=True,
                    histtype='stepfilled' if k == 0 else 'step',
                    alpha=.45 if k == 0 else 1, linewidth=1.8, color=color,
                    label=label + (' (valid subset)' if conditional else ''))
            q = band_quantiles(values[:, None], weights)[:, 0]
            ax.errorbar(q[2], -.12 - k * .09, xerr=[[q[2]-q[1]], [q[3]-q[2]]],
                        fmt='o', color=color, capsize=3, transform=ax.get_xaxis_transform(), clip_on=False)
            rows.append([band, label.lower(), *q])
        if log_depth:
            ax.set_xscale('log')
        # A broad prior can otherwise hide the entire posterior in one bin.
        post, post_weights, _, _ = valid_data[1]
        post_q = band_quantiles(post[:, None], post_weights)[:, 0]
        span = post_q[-1] - post_q[0]
        if not log_depth and 0 < span < (hi - lo) / 5:
            zoom = ax.inset_axes([.39, .38, .57, .40])
            zoom_edges = np.linspace(max(0, post_q[0] - .1 * span), post_q[-1] + .1 * span, bins + 1)
            for values, weights, label, color in valid_data:
                mass, _ = np.histogram(values, bins=zoom_edges, weights=weights)
                zoom.stairs(mass / np.diff(zoom_edges), zoom_edges, color=color,
                            fill=label == 'Prior', alpha=.5 if label == 'Prior' else 1)
            zoom.set_title('Posterior region (ppm)', fontsize=9)
            zoom.tick_params(labelsize=8)
        ax.set(title=band, ylabel='Probability density (ppm⁻¹)', xlabel='Thermal eclipse depth (ppm)')
        ax.xaxis.labelpad = 45
        ax.legend(frameon=False)
    title = report['label']
    if report['smoke']:
        title += ' — SOFTWARE SMOKE TEST ONLY'
    fig.suptitle(title)
    if any(report[key]['invalid_count'] for key in ('prior', 'posterior')):
        fig.text(.5, -.02, 'Distributions conditional on valid evaluations; see provenance for rejected counts and posterior mass.',
                 ha='center', fontsize=9)
    fig.tight_layout()
    for suffix in ('png', 'pdf'):
        fig.savefig(output / f'predictive_comparison.{suffix}', dpi=180, bbox_inches='tight')
    plt.close(fig)
    with (output / 'predictive_intervals.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['band', 'distribution', *COLUMNS])
        writer.writerows(rows)
