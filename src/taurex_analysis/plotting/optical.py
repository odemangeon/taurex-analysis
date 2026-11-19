import numpy as np
from .common import plt
BANDS=('CHEOPS','TESS')
COLORS=('#0072B2','#D55E00','#009E73')

def plot_comparison(predictions, observations, results, models, output, *, thermal_only=False, paper=False):
    """Render identical scientific content with detailed or publication labels."""
    count = len(models)
    colors = [COLORS[i] if i < len(COLORS) else plt.get_cmap('tab20')((i-3) % 20)
              for i in range(count)]
    width = max(7 if thermal_only else 12, (1 if thermal_only else 2)*1.7*count)
    fig, axes = plt.subplots(2, 1 if thermal_only else 2,
                             figsize=(width, 8), squeeze=False)
    for b, band in enumerate(BANDS):
        ax = axes[b, 0]
        outer_labeled = False
        for i, (_, label) in enumerate(models):
            prediction = predictions[label, band]
            lo, mid, hi = prediction[:3]
            if len(prediction) == 5:
                ax.errorbar(i, mid, yerr=[[mid-prediction[3]], [prediction[4]-mid]],
                            fmt='none', ecolor=colors[i], capsize=3,
                            elinewidth=1.8, alpha=.3, zorder=2,
                            label='Thermal 99.7% credible interval' if not outer_labeled else None)
                outer_labeled = True
            ax.errorbar(i, mid, yerr=[[mid-lo], [hi-mid]], fmt='o', color=colors[i],
                        capsize=5, elinewidth=2.2, zorder=3,
                        label='Thermal 68% credible interval' if i == 0 else None)
        obs_band = [r for r in observations if r['band'] == band]
        for j, obs in enumerate(obs_band):
            if obs['kind'] == 'measurement':
                if obs['level'] != 1:
                    continue
                ax.axhspan(obs['depth']-obs['sigma'], obs['depth']+obs['sigma'], color='0.6', alpha=.25,
                           label='Observed ±1σ')
                ax.axhline(obs['depth'], color='0.25', label='Observed depth')
            elif obs['kind'] == 'interval':
                ax.axhspan(obs['lower'], obs['upper'], color='0.5', alpha=.18 if obs['probability'] < .9 else .08,
                           label=f"Observed {100*obs['probability']:g}%" if paper else f"Observed {obs['label']} interval")
                if j == 0:
                    ax.axhline(obs['depth'], color='0.25', label='Observed best value')
                ax.axhline(obs['upper'], color='0.4', linestyle=':', linewidth=.8)
            else:
                limit_label = (obs['label'] if obs['kind'] == 'hpd_upper_endpoint' else
                               f"Upper limit: {obs['label']} ({100*obs['probability']:.3f}%)")
                ax.axhline(obs['depth'], color='0.25', linestyle=('--', ':', '-.')[j % 3],
                           label=f"{100*obs['probability']:g}% upper bound" if paper else limit_label)
                ax.annotate('', xy=(count-.62, obs['depth']-max(abs(obs['depth'])*.08, .2)),
                            xytext=(count-.62, obs['depth']), arrowprops=dict(arrowstyle='->', color='0.25'))
        ax.set_title(f'{band}: eclipse depth' if paper else f'{band}: thermal prediction and observed eclipse')
        ax.set_ylabel('Eclipse depth (ppm)')
        ax.legend(fontsize=8)
        if not thermal_only:
            ag = axes[b, 1]
            for i, (_, label) in enumerate(models):
                selected = [r for r in results if r['model'] == label and r['band'] == band]
                # Draw broad faint intervals first, then narrower opaque ones,
                # and finally a single best-value marker at the shared position.
                intervals = sorted((r for r in selected if r['kind'] in ('measurement', 'interval')),
                                   key=lambda r: r['probability'], reverse=True)
                for j, row in enumerate(intervals):
                    inner = j == len(intervals)-1
                    ag.errorbar(i, row['ag_center'],
                                yerr=[[row['ag_center']-row['ag_lower']], [row['ag_upper']-row['ag_center']]],
                                fmt='none', ecolor=colors[i], capsize=5 if inner else 3,
                                elinewidth=2.2 if inner else 1.8, alpha=1 if inner else .3,
                                zorder=3 if inner else 2)
                if intervals:
                    ag.plot(i, intervals[0]['ag_center'], 'o', color=colors[i], zorder=4)
                limits = [r for r in selected if r['kind'] not in ('measurement', 'interval')]
                for j, row in enumerate(limits):
                    x = i + (j-(len(limits)-1)/2)*.18
                    ag.plot([x, x], [row['ag_upper_at_thermal_p84'], row['ag_upper_at_thermal_p16']],
                            color=colors[i], linewidth=5, alpha=.3)
                    ag.plot(x, row['ag_upper'], marker='v', color=colors[i])
            # Describe intervals once per panel instead of at every model.
            from matplotlib.lines import Line2D
            panel_rows = [r for r in results if r['band'] == band and r['model'] == models[0][1]]
            interval_rows = sorted((r for r in panel_rows if r['kind'] in ('measurement', 'interval')),
                                   key=lambda r: r['probability'])
            handles = [Line2D([0], [0], color='0.2', linewidth=2,
                              alpha=1 if j == 0 else .3,
                              label=f"{100*r['probability']:g}%" if paper else r['label'])
                       for j, r in enumerate(interval_rows)]
            handles += [Line2D([0], [0], color='0.3', marker='v', linestyle='none',
                               label=f"{100*r['probability']:g}% upper bound" if paper else r['label'])
                        for r in panel_rows if r['kind'] not in ('measurement', 'interval')]
            if handles:
                ag.legend(handles=handles, fontsize=8, loc='best')
            ag.axhline(0, color='0.5', linewidth=.8)
            ag.margins(y=.13)
            ag.set_title(f'{band}: geometric albedo' if paper else f'{band}: conditional geometric albedo')
            ag.set_ylabel('Geometric albedo')
        for panel in axes[b]:
            panel.set_xticks(range(count), [label for _, label in models])
            panel.set_xlim(-.5, count-.45)
            panel.grid(axis='y', alpha=.2)
    note = 'Thermal points: median; dark bars: p16–p84 (68%); light bars, where available: p0.15–p99.85 (99.7%).'
    if not thermal_only:
        note += '\nAlbedo intervals: supplied optical coverage, conditional on median thermal emission and band-specific best geometry.\nLimit-marker shading: thermal p16–p84 sensitivity only. Geometry and thermal uncertainty are not marginalized.'
    if paper:
        fig.tight_layout()
    else:
        fig.suptitle('Optical eclipse comparison')
        fig.text(.5, .015, note, ha='center', fontsize=8)
        fig.tight_layout(rect=(0, .065, 1, .96))
    stem = 'optical_comparison_paper' if paper else 'optical_comparison'
    for extension in ('png', 'pdf'):
        fig.savefig(output/f'{stem}.{extension}', dpi=300)
    plt.close(fig)
