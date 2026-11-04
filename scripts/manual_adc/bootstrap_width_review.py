"""Review fixed-start single-variable M0 sweep, including unchanged failed criteria."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parents[2]
OUT = R/'verification/manual_adc/bootstrap_width_v1'
FIG = OUT/'figures'
LSB = 1.8/256
FREQ = 10e6*461/1024
AMP = .9*10**(-1/20)


def load(run):
    p = R/'output/managed_execution/runs'/run/'collected/derived/result.json'
    result = json.loads(p.read_text())
    assert result['native_state']['native_exit']==0 and result['native_state']['zero_error_footer']
    result['run_id']=run
    result['result_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def fit(rows):
    t=np.array([x['sample_close_s'] for x in rows])
    y=np.array([x['held_diff_V'] for x in rows])
    m=np.column_stack([np.ones(len(t)),np.sin(2*np.pi*FREQ*t),np.cos(2*np.pi*FREQ*t)])
    b=np.linalg.lstsq(m,y,rcond=None)[0];e=y-m@b
    return {'effective_lag_ps':float(-np.arctan2(b[2],b[1])/(2*np.pi*FREQ)*1e12),
            'gain_error_percent':float((np.hypot(b[1],b[2])/AMP-1)*100),
            'offset_uV':float(b[0]*1e6),'residual_peak_uV':float(max(abs(e))*1e6),
            'residual_rms_uV':float(np.sqrt(np.mean(e**2))*1e6),'residual_uV':(e*1e6).tolist()}


def worst_terminal(r):
    key,z=max(r['terminal_pairs'].items(),key=lambda x:x[1]['peak_V'])
    return dict(z,devices=[{'path':dev,'pair':pair} for dev,m in r['device_pairs'].items() for pair,k in m.items() if k==key])


def wave(run):
    p=R/'output/managed_execution/runs'/run/'collected/derived/wave.csv.gz'
    with gzip.open(p,'rt') as stream:
        reader=csv.reader(stream);header=next(reader);a=np.array(list(reader),float)
    return {n:a[:,i] for i,n in enumerate(header)}


def finish(fig,name,title):
    fig.suptitle(title+'\nTT | 0.9 V | 27 C | 10 MS/s | Bootstrap MOS; other blocks behavioral',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.92))
    fig.savefig(FIG/(name+'.png'),dpi=170)
    fig.savefig(FIG/(name+'.svg'))
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    before=load('manual8-bootshort-startup-v1')
    after=load('manual8-bootwidth-startup-m4-v1')
    widths=[];raw={}
    for w in [4,6,8]:
        dc=load('manual8-bootwidth-dc-m%d-v1'%w);si=load('manual8-bootwidth-sine-m%d-v1'%w)
        raw[w]=(dc,si);rows=dc['frames'];sr=si['frames'];f=fit(sr)
        for result in [dc,si,after]:
            rising=[e[0] for e in result['edges']['clks'] if e[1]==1]
            assert all(abs(t-(110.025e-9+i*100e-9))<1e-14 for i,t in enumerate(rising))
        widths.append({'M0_total_width_um':w,'dc_run':dc['run_id'],'sine_run':si['run_id'],
            'dc_result_sha256':dc['result_sha256'],'sine_result_sha256':si['result_sha256'],
            'dc_checks':dc['checks'],'sine_checks':dict(si['checks'],sine_fit_residual=f['residual_peak_uV']<=.25*LSB*1e6),
            'first_precharge_min_V':min(rows[0]['precharge_P_V'],rows[0]['precharge_N_V']),
            'static_held_peak_mV':max(abs(x['held_diff_error_V']) for x in rows)*1e3,
            'static_single_end_step_range_mV':[min(x[k]*1e3 for x in rows for k in ['turnoff_P_change_V','turnoff_N_change_V']),max(x[k]*1e3 for x in rows for k in ['turnoff_P_change_V','turnoff_N_change_V'])],
            'static_diff_step_peak_mV':max(abs(x['turnoff_diff_change_V']) for x in rows)*1e3,
            'sine_raw_error_peak_mV':max(abs(x['held_diff_error_V']) for x in sr)*1e3,
            'sine_code_delta_peak':max(abs(x['code_delta']) for x in sr),
            'sine_fit':f,'sine_fit_excluding_first':fit(sr[1:]),
            'terminal_dc':worst_terminal(dc),'terminal_sine':worst_terminal(si),
            'native_dc':dc['native_state'],'native_sine':si['native_state'],
            'sine_VDD_clock_uW':(si['power_W']['vdd']+si['power_W']['clock'])*1e6,
            'sine_input_uW':si['power_W']['input']*1e6})
    result={'startup':{'before_first':before['frames'][0],'after_first':after['frames'][0],
                       'after_checks':after['checks'],'native':after['native_state'],
                       'before_run':before['run_id'],'after_run':after['run_id']},
            'widths':widths,'lsb_V':LSB,'clock_start_ns':110,'clock_close_ns':149.975,
            'scope':'Only nominal short tests; turnoff steps combine injection/feedthrough; sinusoidal fitted lag is single-frequency effective lag, not proven pure delay; no new baseline or OA changes.'}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

    # Startup precharge in absolute time; acquisition aligned to first opening.
    fig,ax=plt.subplots(3,1,figsize=(11,9))
    for rr,start,color,label in [(before,10,'#b65c43','Original start: 10 ns'),(after,110,'#287e90','Delayed start: 110 ns')]:
        z=wave(rr['run_id']);t=z['time']*1e9
        cb=z['xadc.xp.xs.net2']-z['xadc.xp.xs.net3']
        m=t<=start+.025
        ax[0].plot(t[m],cb[m],color=color,label=label,lw=2)
        ax[0].plot(start-.075,rr['frames'][0]['precharge_P_V'],'o',color=color)
        rel=t-(start+.025);m=(rel>=-1)&(rel<=44)
        ax[1].plot(rel[m],(z['xadc.xp.xs.net1']-z['inp'])[m],color=color,label=label)
        err=z['xadc.topp']-z['xadc.topn']-(z['vinp']-z['vinn'])
        ax[2].plot(rel[m],err[m]*1e3,color=color,label=label)
    ax[0].axhline(.855,color='#777777',ls='--',label='95% VDD')
    ax[0].set(xlabel='Time after power ramp begins (ns)',ylabel='Cboot P voltage (V)')
    ax[0].legend(fontsize=9)
    ax[1].set(ylabel='Main switch P VGS (V)',xlabel='Time from first opening 50% (ns)')
    ax[2].set(ylabel='Differential error (mV)',xlabel='Time from first opening 50% (ns)',ylim=(-1,12))
    ax[2].axhline(.25*LSB*1e3,color='#777777',ls='--')
    ax[2].text(.02,.92,'Early acquisition errors above 12 mV are clipped.',transform=ax[2].transAxes,fontsize=9)
    for a in ax[1:]:a.axvline(39.95,color='#777777',ls=':')
    for a in ax:a.grid(alpha=.2)
    finish(fig,'01_startup_delay','One extra low-clock period before first sampling; sample-window length unchanged')

    fig,ax=plt.subplots(2,2,figsize=(11,8));xs=[x['M0_total_width_um'] for x in widths]
    metrics=[('effective_lag_ps','Effective lag (ps)'),('residual_peak_uV','Fit residual peak (uV)')]
    for a,(key,label) in zip(ax[0],metrics):
        ys=[x['sine_fit'][key] for x in widths];a.plot(xs,ys,'o-',color='#287e90');a.set(ylabel=label)
        for x,y in zip(xs,ys):a.annotate('%.2f'%y,(x,y),xytext=(0,8),textcoords='offset points',ha='center')
        a.margins(y=.25)
    ys=[x['static_diff_step_peak_mV'] for x in widths]
    ax[1,0].plot(xs,ys,'o-',color='#b65c43');ax[1,0].set(ylabel='Static differential turnoff step (mV)')
    ax[1,0].axhline(.25*LSB*1e3,color='#777777',ls='--',label='0.25 LSB budget');ax[1,0].legend(fontsize=9)
    for x,y in zip(xs,ys):ax[1,0].annotate('%.3f'%y,(x,y),xytext=(0,8),textcoords='offset points',ha='center')
    ax[1,1].plot(xs,[x['terminal_dc']['peak_V'] for x in widths],'o-',label='DC steps')
    ax[1,1].plot(xs,[x['terminal_sine']['peak_V'] for x in widths],'s-',label='Sine')
    ax[1,1].axhline(1.98,color='#777777',ls='--',label='1.98 V project screen')
    ax[1,1].set(ylabel='Maximum absolute MOS terminal pair (V)');ax[1,1].legend(fontsize=9)
    for a in ax.flat:a.set(xlabel='M0 total width (um)',xticks=xs);a.margins(x=.13);a.grid(alpha=.2)
    finish(fig,'02_width_tradeoff','M0 4 / 6 / 8 um: same delayed startup, external timing, load and other devices')

    fig,ax=plt.subplots(3,1,figsize=(11,9))
    for width,color in [(4,'#287e90'),(6,'#b97728'),(8,'#8b5288')]:
        dc,si=raw[width];rows=dc['frames'];s=fit(si['frames'])
        ax[0].plot(range(8),[x['turnoff_P_change_V']*1e3 for x in rows],'o-',color=color,label='%d um P'%width)
        ax[0].plot(range(8),[x['turnoff_N_change_V']*1e3 for x in rows],'x--',color=color,label='%d um N'%width)
        ax[1].plot(range(8),[x['turnoff_diff_change_V']*1e3 for x in rows],'o-',color=color,label='%d um'%width)
        ax[2].plot(range(16),s['residual_uV'],'o-',color=color,label='%d um'%width)
    ax[0].set(ylabel='Single-end turnoff step (mV)',xlabel='Static frame index')
    ax[0].legend(ncol=3,fontsize=9)
    ax[1].set(ylabel='Differential turnoff step (mV)',xlabel='Static frame index');ax[1].legend(ncol=3,fontsize=9)
    ax[2].set(ylabel='Sine fit residual (uV)',xlabel='Sine sample index (16 samples, not FFT/ENOB)');ax[2].legend(ncol=3,fontsize=9)
    for a in ax:a.grid(alpha=.2)
    finish(fig,'03_injection_residual','Turnoff measured with static inputs; high-frequency input motion is not called injection')
    validations=[]
    for rr in [after]+[r for pair in raw.values() for r in pair]:
        z=wave(rr['run_id'])
        errs=[]
        for row in rr['frames']:
            held=np.interp(row['sample_close_s']+1e-9,z['time'],z['xadc.topp']-z['xadc.topn'])
            errs.append(abs(held-row['held_diff_V']))
        assert max(errs)<1e-7
        falls=[e[0] for e in rr['edges']['clks'] if e[1]==0]
        assert len(falls)==len(rr['frames'])
        assert all(abs(t-(149.975e-9+i*100e-9))<1e-14 for i,t in enumerate(falls))
        validations.append({'run_id':rr['run_id'],'native_points':rr['native_points'],
                            'exported_wave_vs_native_held_max_error_V':max(errs),
                            'all_close_edges_match':True})
    manifest=json.loads((OUT/'manifest.json').read_text())
    for run in manifest['runs']:
        for name,digest in run['source_sha256'].items():
            assert hashlib.sha256((R/run['directory']/name).read_bytes()).hexdigest()==digest
    (OUT/'result_validation.json').write_text(json.dumps({'runs':validations,'frozen_case_inputs_unchanged':True},indent=2)+'\n')
    print(json.dumps({'startup':result['startup'],'widths':widths},indent=2))


if __name__=='__main__':main()
