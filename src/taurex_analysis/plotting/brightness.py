"""Render temperatures already computed by post-processing."""
import numpy as np
from .common import plt


def plot_brightness(data, rows, output, note=''):
    wl,q=data['wavelength_um'],data['tb_quantiles']
    fig,axes=plt.subplots(2,1,figsize=(10,9),layout='constrained')
    for ax in axes:
        ax.fill_between(wl,q[0],q[2],alpha=.3)
        ax.plot(wl,q[1],label='Median thermal brightness temperature')
        ax.set(xlabel='Wavelength (µm)',ylabel='Brightness temperature (K)')
    axes[0].set(xscale='log',xlim=(min(2.5,min(r['wavelength_um'] for r in rows)*.95),22))
    axes[1].set(xlim=(.3,1.2),title='Visible extrapolation: thermal emission only')
    for wave,lo,mid,hi in data['measurement_tb']:
        if np.isfinite([lo,mid,hi]).all():
            axes[0].errorbar(wave,mid,yerr=[[mid-lo],[hi-mid]],fmt='ko',capsize=3)
        elif np.isfinite(mid):
            axes[0].plot(wave,mid,'ko')
    axes[0].plot([],[],'ko',label='Band-inverted data (1σ; nominal radius fixed)')
    selected={r['band']:r['wavelength_um'] for r in rows}
    backgrounds=[ax.twinx() for ax in axes]
    for ax in backgrounds:
        ax.set(ylim=(0,1.25),ylabel='Normalized bandpass response')
    for i,band in enumerate(data['bands'].tolist()):
        wave,response=data[f'response_wave_{i}'],data[f'response_value_{i}']
        panel=0 if band in selected else 1
        backgrounds[panel].fill_between(wave,response/response.max(),alpha=.08)
        center=selected.get(band,np.trapezoid(wave*response,wave)/np.trapezoid(response,wave))
        lo,mid,hi=data['band_tb_quantiles'][:,i]
        axes[panel].errorbar(center,mid,yerr=[[mid-lo],[hi-mid]],fmt='rs',mfc='none',capsize=3,
            label='Band-integrated model (68%)' if i==0 else band if panel else None)
    for ax in axes:
        ax.legend(fontsize=8)
    if note: fig.suptitle(note)
    fig.savefig(output,dpi=180)
    plt.close(fig)
