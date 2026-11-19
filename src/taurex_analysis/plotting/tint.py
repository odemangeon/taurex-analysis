import csv
import numpy as np
from .common import plt
BANDS=("CHEOPS","TESS")

def write_comparison(output, summaries, tint):
    with (output/'comparison.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for j, band in enumerate(BANDS):
        rows = [r for r in summaries if r['band'] == band]
        for i, r in enumerate(rows):
            for key, offset, color in [('baseline', -.12, 'tab:blue'), ('changed', .12, 'tab:orange')]:
                lo, mid, hi = [r[f'{key}_{q}'] for q in ('p16', 'median', 'p84')]
                axes[j, 0].errorbar(i+offset, mid, yerr=[[mid-lo], [hi-mid]], fmt='o', color=color,
                                   label=(f'{100 if key == "baseline" else tint:g} K' if i == 0 else None))
            lo, mid, hi = [r[f'difference_{q}'] for q in ('p16', 'median', 'p84')]
            axes[j, 1].errorbar(i, mid, yerr=[[mid-lo], [hi-mid]], fmt='o', color='black')
        axes[j, 0].set_ylabel(f'{band} thermal depth (ppm)')
        axes[j, 0].legend()
        axes[j, 1].set_ylabel(f'{band} paired change (ppm)')
        axes[j, 1].axhline(0, color='gray', lw=.8)
        for ax in axes[j]:
            ax.set_xticks(range(len(rows)), [r['model'] for r in rows], rotation=15)
            ax.grid(axis='y', alpha=.2)
    conditional = any(r['failed_weight'] > 0 for r in summaries)
    fig.suptitle('T_int sensitivity: medians and 16–84% intervals' + ('\nConditional on valid pairs; see excluded weights in report' if conditional else ''))
    fig.savefig(output/'comparison.png', dpi=180)
    plt.close(fig)
    lines = ['# Internal-temperature sensitivity', '',
             f'Paired predictions at T_int=100 and {tint:g} K using the original 100 K posterior; no refit or likelihood reweighting. Chemistry and radiative transfer are recomputed. Thermal emission only.', '',
             'Intervals are 16th–84th percentiles. If any evaluations fail, ALL tabulated intervals are conditional on valid pairs; excluded probability is reported, not silently discarded. Such results do not establish full-posterior sensitivity.', '',
             '| Retrieval | Band | 100 K ppm [16,84] | Changed ppm [16,84] | Paired change ppm [16,84] | Median paired % change | Excluded weight |',
             '|---|---|---|---|---|---|---|']
    for r in summaries:
        values = [f"{r[k+'_median']:.4g} [{r[k+'_p16']:.4g}, {r[k+'_p84']:.4g}]" for k in ('baseline', 'changed', 'difference')]
        lines.append(f"| {r['model']} | {r['band']} | " + ' | '.join(values) + f" | {r['percent_change_median']:.3g}% | {r['failed_weight']:.2%} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
