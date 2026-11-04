"""Plot measured transition DNL/INL using ADCtoolbox's native plotter."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from adctoolbox.aout.plot_dnl_inl import plot_dnl_inl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'verification/sar8_campaign/ab_static'
source = OUT/'fullstatic_recovered.json'
data = json.loads(source.read_text())
plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
for col, variant in enumerate('ab'):
    d = data[variant]
    transitions = np.asarray(d['midpoints_v'])
    dnl = np.diff(transitions)/(1.8/256)-1
    endpoint_lsb = (transitions[-1]-transitions[0])/254
    inl = (transitions-np.linspace(transitions[0],transitions[-1],255))/endpoint_lsb
    np.testing.assert_allclose(dnl, d['dnl_nominal_lsb'], atol=1e-12)
    np.testing.assert_allclose(inl, d['inl_endpoint_lsb'], atol=1e-12)
    assert np.all(np.diff(transitions)>0) and len(dnl)==254
    plot_dnl_inl(np.arange(1,255), dnl, inl, inl_code=np.arange(1,256),
                 axes=(axes[0,col],axes[1,col]), show_title=False,
                 color_dnl='b' if variant=='a' else 'r',
                 color_inl='b' if variant=='a' else 'r')
    axes[0,col].set_title(f'{variant.upper()} | DNL [{dnl.min():.5f}, {dnl.max():.5f}] LSB')
    axes[1,col].set_title(f'{variant.upper()} | Endpoint INL [{inl.min():.5f}, {inl.max():.5f}] LSB')
    axes[0,col].set_xlabel('Output code (1 to 254; saturated endpoint widths excluded)')
    axes[1,col].set_xlabel('Transition index k (code k-1 to k)')
    for ax in axes[:,col]:
        ax.set_xlim(0,255)
        ax.set_xticks([0,32,64,96,128,160,192,224,255])
        ax.axhline(0,color='black',linewidth=.6,alpha=.5)
fig.suptitle('Frozen A / B | TT static linearity | 8-bit, 10 MS/s, 0.9 V, 27 C',fontsize=15)
fig.text(.5,.055,'Measured transition brackets: 1/128 nominal LSB (54.93 uV). Curves use bracket midpoints.',ha='center')
fig.text(.5,.028,'DNL: nominal LSB = 1.8 V / 256. INL: endpoint gain/offset removed. Noise / mismatch / PEX disabled.',ha='center')
fig.subplots_adjust(top=.88,bottom=.15,hspace=.46,wspace=.22)
for zoom in [False,True]:
    for ax in axes.flat:
        ax.set_ylim(-.06,.06) if zoom else ax.set_ylim(-1,1)
    name='static_dnl_inl_zoom' if zoom else 'static_dnl_inl_overview'
    for ext in ['png','svg']:
        fig.savefig(OUT/f'{name}.{ext}',dpi=180)
plt.close(fig)
(OUT/'static_plot_metadata.json').write_text(json.dumps(dict(
    source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    plotter='adctoolbox.aout.plot_dnl_inl',estimator='measured transition widths, not histogram',
    dnl_units='nominal LSB',inl_units='endpoint LSB',
    validation='independently recomputed arrays match aggregate within 1e-12'),indent=2)+'\n')
print(OUT/'static_dnl_inl_zoom.png')
