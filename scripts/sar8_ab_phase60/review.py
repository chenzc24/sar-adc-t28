"""Small local A/B comparison and figures after managed streaming recovery."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/sar8_ab_phase60'
def load(label):return json.loads((OUT/label/'result.json').read_text())
def main():
    a,b=load('a'),load('b');assert a['context']['expected_codes']==b['context']['expected_codes']
    assert a['effective_settings']==b['effective_settings'],'Solver settings differ; do not label equal settings'
    comparisons=[]
    for x,y in zip(a['frames'],b['frames']):
        d=dict(frame=x['frame'],expected=x['expected_code'],A_code=x['code_98'],B_code=y['code_98'],
            A_timing_pass=x['timing_pass'],B_timing_pass=y['timing_pass'],A_counts=x['counts'],B_counts=y['counts'])
        for key in ['sample_int_close_s','seq_sample_close_s','external_close_s']:
            d[key+'_delta_ps']=(y[key][0]-x[key][0])*1e12 if len(x[key])==len(y[key])==1 else None
        for key in ['preclose_error_source_v','preclose_error_pin_v','hold_200ps_error_v','conversion_ns']:
            d['A_'+key]=x.get(key);d['B_'+key]=y.get(key)
        comparisons.append(d)
    verdict=dict(analysis_complete=True,comparison= comparisons,A_startup_code_pass=a['startup_code_pass'],B_startup_code_pass=b['startup_code_pass'],A_startup_timing_pass=a['startup_timing_pass'],B_startup_timing_pass=b['startup_timing_pass'],A_steady_code_pass=a['steady_code_pass'],
        B_steady_code_pass=b['steady_code_pass'],A_steady_timing_pass=a['steady_timing_pass'],B_steady_timing_pass=b['steady_timing_pass'],
        same_effective_settings=True,electrical_verdict='deferred_not_qualified',plots_visually_reviewed=False,
        aperture_shift_tolerance='No numerical specification assigned; measured differences reported')
    (OUT/'comparison.json').write_text(json.dumps(verdict,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(3,1,figsize=(12,8),layout='constrained')
    for label,data,color in [('A',a,'#2166ac'),('B',b,'#d6604d')]:
        xs=[r['frame'] for r in data['frames']]
        axs[0].plot(xs,[r['code_98'] for r in data['frames']],'.-',label=label,color=color)
        axs[1].plot(xs,[r.get('preclose_error_source_v',float('nan'))*1e3 for r in data['frames']],'.-',label=label,color=color)
        axs[2].plot(xs,[r.get('conversion_ns',float('nan')) for r in data['frames']],'.-',label=label,color=color)
    axs[0].plot(xs,a['context']['expected_codes'],'kx',label='Expected')
    for ax,title,y in zip(axs,['Output codes (frame 0: startup)','Acquisition error just before SEQ_SAMPLE falling edge','Last update relative to SEQ_SAMPLE falling edge'],['Code','Error (mV)','Time (ns)']):
        ax.set_title(title);ax.set_ylabel(y);ax.grid(alpha=.25);ax.legend()
    axs[-1].set_xlabel('Frame');fig.savefig(OUT/'codes_settling.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(4,1,figsize=(12,10),layout='constrained')
    for label,color in [('a','#2166ac'),('b','#d6604d')]:
        rows=list(csv.DictReader((OUT/label/'timeline.csv').open()))
        for ax,key in zip(axs,['seq_sample','cmp','write','update']):
            ax.plot([float(r['time_s'])*1e9 for r in rows],[float(r[key]) for r in rows],label=label.upper(),color=color,alpha=.8)
            ax.set_ylabel(key+' (V)');ax.grid(alpha=.25);ax.legend()
    axs[0].set_title('TT A/B interface timeline (plot decimated; metrics use native points)')
    axs[-1].set_xlabel('Time (ns)');fig.savefig(OUT/'handshake.png',dpi=150);plt.close(fig)
    lines=['# Low-first startup Mmain2/L90 A/B TT result','',
        'A: historical custom logic. B: isolated native standard-cell migration. Same 0.9V/27C/10MS/s stimulus and loads.',
        'Stress deferred; not electrical qualification. Frame0 is first valid sample after 60ns initial low; it must pass. DC initialized, no supply ramp qualification. No FFT/PVT/MC conclusions.','',
        '|Frame|Expected|A code|B code|A timing|B timing|SEQ close B-A ps|',
        '|---|---|---|---|---|---|---|']
    for r in comparisons:
        d=r['seq_sample_close_s_delta_ps'];s='unknown' if d is None else '%.3f'%d
        lines.append('|%d|%d|%d|%d|%s|%s|%s|'%(r['frame'],r['expected'],r['A_code'],r['B_code'],r['A_timing_pass'],r['B_timing_pass'],s))
    lines+=['','![Codes and acquisition](codes_settling.png)','![Handshake](handshake.png)','',
        'Full native edge lists and measured-reference DAC tail margins are in a/result.json and b/result.json. Tail metrics are not ideal DAC accuracy. Bootstrap VGS0.45V crossings are diagnostics, not physical turnoff thresholds.',
        'Actual settings: `'+json.dumps(a['effective_settings'])+'`.','',
        'Figures generated; visual review pending. No candidate adoption or circuit change.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(verdict))
if __name__=='__main__':main()
