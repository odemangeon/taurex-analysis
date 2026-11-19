import numpy as np
from .common import plt

def plot_contribution_functions_and_tp(pressure, contributions, bands, temperature,
                                       output, tp_quantiles=None, initial=False,
                                       smoke=False):
    """Compare flux-origin pressures and temperatures on one shared pressure axis."""
    fig, (cf_ax, tp_ax) = plt.subplots(1, 2, sharey=True, figsize=(11, 6),
                                     layout='constrained')
    for i, band in enumerate(bands):
        cf_ax.plot(contributions[:, i], pressure, label=band)
    cf_ax.set(xlabel='Fraction of band thermal flux per dex in pressure',
              ylabel='Pressure (bar)', yscale='log',
              title='Contribution functions: '+('initial model' if initial else 'best posterior sample'))
    cf_ax.invert_yaxis()
    cf_ax.legend(fontsize=9)
    if tp_quantiles is not None:
        low, median, high = tp_quantiles
        tp_ax.fill_betweenx(pressure, low, high, color='tab:blue', alpha=.25,
                            label='68% credible interval')
        tp_ax.plot(median, pressure, color='tab:blue', label='Posterior median')
    tp_ax.plot(temperature, pressure, color='black', linestyle='--',
               label='Initial model' if initial else 'Best posterior sample')
    tp_ax.set(xlabel='Temperature (K)',
              title='Initial T–P profile (not retrieved)' if initial else 'Retrieved T–P profile')
    tp_ax.legend(fontsize=9)
    for ax in (cf_ax, tp_ax):
        ax.grid(axis='y', alpha=.15)
    if smoke:
        fig.suptitle('SOFTWARE SMOKE TEST — not scientific results')
    fig.savefig(output, dpi=180)
    plt.close(fig)
