"""Frozen transient comparison and independent Mmain DC current diagnostic."""
import gzip
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from diagnose import ROOT, OUT, NAMES, DCNAMES, previous

VERIFY=ROOT/'verification/sar8_ss_bootstrap'
FIG=ROOT/'docs/figures/sar8_ss_bootstrap'
COLORS=['#2676b8','#cc493f','#269780']
LABELS=['TT / 0.90 V / 27 C','SS / 0.81 V / -40 C','SS / 0.81 V / 125 C']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def getwaves():
    out=[]
    for name in NAMES:
        p=OUT/(name+'.json.gz')
        assert previous.sha(p)==previous.read(OUT/'receipt.json')['files'][name]
        with gzip.open(p,'rt') as f:r=json.load(f)
        old=previous.read(ROOT/'verification/sar8_pvt_mismatch'/(name+'.json'))
        assert r['native_psf_sha256']==old['native_psf_sha256']
        w={k:np.array(v) for k,v in r['wave'].items()}
        out.append((name,r,old,w,w['time']*1e9))
    return out

def main():
    VERIFY.mkdir(exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    cases=getwaves();metrics=[]
    for name,r,old,w,t in cases:
        def at(k,when):return float(np.interp(when,t,w[k.lower()]))
        f=old['frames'][1];close=f['preclose_time_ns']+.2
        samples=[]
        for ns in [99,105,110,120,130,140,f['preclose_time_ns'],141.8]:
            a=dict(time_ns=ns)
            for side in ['p','n']:
                prefix='xdut.xboot'+side+'.';vin=at('vin'+side,ns)
                a[side]=dict(vin_v=vin,top_v=at('xdut.top'+side,ns),
                    top_error_v=at('xdut.top'+side,ns)-at('vin'+side+'_src',ns),
                    vgs_v=at(prefix+'g',ns)-vin,
                    capacitor_v=at(prefix+'btop',ns)-at(prefix+'bbot',ns),
                    bbot_minus_vin_v=at(prefix+'bbot',ns)-vin,
                    btop_minus_g_v=at(prefix+'btop',ns)-at(prefix+'g',ns),
                    ctrl_minus_bbot_v=at(prefix+'ctrl',ns)-at(prefix+'bbot',ns),
                    net_input_return_ua=(vin-at('vin'+side+'_src',ns))/50*1e6)
            samples.append(a)
        nominal_c=256*4.004e-15
        discharge_ua=nominal_c*(at('xdut.topp',110)-at('xdut.topp',120))/10e-9*1e6
        bmovement={side:float(max(np.ptp(w['xdut.xcdac.b'+side+str(i)][(t>=105)&(t<=140)]) for i in range(8))) for side in ['p','n']}
        gate95={side:float(t[np.flatnonzero((t>101)&(t<110)&((w['xdut.xboot'+side+'.g']-w['vin'+side])>=.95*old['vdd']))[0]]) for side in ['p','n']}
        metrics.append(dict(name=name,native_psf_sha256=r['native_psf_sha256'],native_window_points=len(t),
            samples=samples,acquisition_ns=f['acquisition_ns'],close_ns=close,code=f['code'],
            first_native_sample_vgs95pct_vdd_ns=gate95,
            held_error_mv=f['held_error_v']*1e3,preclose_error_mv=f['preclose_error_v']*1e3,
            topP_nominal_cap_slope_current_110_120_ua=discharge_ua,
            slope_current_assumption='256 x 4.004 fF nominal CDAC only; excludes input parasitic and bottom motion, not direct Mmain current',
            max_bottom_movement_105_140_v=bmovement))
    previous.dump(VERIFY/'transient.json',dict(cases=metrics,source_receipt=previous.read(OUT/'receipt.json'),
        definition='Positive return current = (VIN - ideal source)/50 ohm; includes Mmain and bootstrap branches'))
    environment='Frozen T28 ADC | +0.81 to -0.81 V differential at 100.2-100.3 ns | 10 MS/s\nFixed VREF 0/0.9 V, CM 0.45 V | ideal external sources/SAMPLE | no mismatch, noise or PEX | native CX'
    fig,axs=plt.subplots(5,1,figsize=(11.5,11),sharex=True,layout='constrained')
    fig.suptitle('Acquisition: TT versus cold SS\n'+environment,fontsize=10)
    for j,(name,r,old,w,t) in enumerate(cases[:2]):
        mask=(t>=99)&(t<=142.1);x=t[mask];color=COLORS[j];label=LABELS[j]
        axs[0].plot(x,w['xdut.seq_sample'][mask]/old['vdd'],color=color,label=label)
        for a,side in [(axs[1],'p'),(axs[2],'n')]:a.plot(x,w['xdut.top'+side][mask],color=color,label='TOP'+side.upper()+' '+label)
        axs[3].plot(x,(w['xdut.xbootp.g']-w['vinp'])[mask],color=color,label=label)
        error=(w['xdut.topp']-w['xdut.topn']-w['vinp_src']+w['vinn_src'])*1e3
        axs[4].plot(x,error[mask],color=color,label=label)
        for a in axs:a.axvline(metrics[j]['close_ns'],color=color,ls=':',alpha=.6)
    for a,side in [(axs[1],'p'),(axs[2],'n')]:
        w=cases[0][3];t=cases[0][4];mask=(t>=99)&(t<=142.1)
        a.plot(t[mask],w['vin'+side+'_src'][mask],color='#555',ls='--',label='Input target')
    axs[3].axhline(.81,color=COLORS[1],ls='--',alpha=.5,label='SS VDD = 0.81 V')
    axs[3].axhline(.9,color=COLORS[0],ls='--',alpha=.5,label='TT VDD = 0.90 V')
    axs[4].axhspan(-1.7578125,1.7578125,color='#269780',alpha=.18,label='+/-0.25 LSB')
    axs[4].set_yscale('symlog',linthresh=1.8)
    axs[4].scatter([141.8]*2,[m['held_error_mv'] for m in metrics[:2]],color=COLORS[:2],s=18,zorder=5)
    axs[4].annotate('SS held: +76.56 mV',xy=(141.8,metrics[1]['held_error_mv']),xytext=(126,800),arrowprops=dict(arrowstyle='->',color=COLORS[1]),color=COLORS[1])
    axs[4].annotate('TT held: '+f"{metrics[0]['held_error_mv']:+.3f} mV",xy=(141.8,metrics[0]['held_error_mv']),xytext=(122,-8),arrowprops=dict(arrowstyle='->',color=COLORS[0]),color=COLORS[0])
    for a,label in zip(axs,['Enable / VDD','Discharging P (V)','Charging N (V)','Mmain P VGS (V)','Differential error (mV)']):
        a.set_ylabel(label);a.grid(alpha=.18);a.legend(fontsize=8,loc='best',ncol=2)
    axs[4].legend(fontsize=8,loc='lower left',ncol=1)
    axs[0].set_title('Dotted lines: each corner\'s enable falling edge; 141.8 ns: held value before first comparison',fontsize=9)
    axs[-1].set_xlabel('Time (ns)')
    fig.savefig(FIG/'tt_ss_acquisition.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(4,1,figsize=(11.5,9.5),sharex=True,layout='constrained')
    fig.suptitle('Bootstrap internal nodes: pump or load?\n'+environment,fontsize=10)
    for j,(name,r,old,w,t) in enumerate(cases[:2]):
        mask=(t>=98)&(t<=141);x=t[mask]
        for side,style in [('p','-'),('n','--')]:
            p='xdut.xboot'+side+'.';label=LABELS[j]+' '+side.upper()
            values=[w[p+'btop']-w[p+'bbot'],w[p+'bbot']-w['vin'+side],w[p+'btop']-w[p+'g'],w[p+'ctrl']-w[p+'bbot']]
            for a,y in zip(axs,values):a.plot(x,y[mask],color=COLORS[j],ls=style,label=label)
    for a,label in zip(axs,['Cboot voltage (V)','BBOT - VIN (V)','BTOP - G (V)','CTRL - BBOT (V)']):
        a.set_ylabel(label);a.grid(alpha=.18);a.legend(fontsize=8,loc='best',ncol=2)
    axs[0].set_title('Solid: P side (discharging TOP); dashed: N side (charging TOP)',fontsize=9)
    axs[-1].set_xlabel('Time (ns)');fig.savefig(FIG/'pump_nodes.png',dpi=160);plt.close(fig)
    print('Transient metrics and two figures saved:',VERIFY)

def dc():
    rows=[]
    fig,ax=plt.subplots(figsize=(10,5.3),layout='constrained')
    for j,name in enumerate(DCNAMES):
        p=OUT/name;log=(p/'native/spectre.out').read_text();status=(p/'native/test.raw/logStatus').read_text()
        assert 'spectre completes with 0 errors' in log and re.search(r'dc_iv\s+PASS',status)
        raw=p/'native/test.raw/dc_iv.dc';text=raw.read_text();assert text.rstrip().endswith('END')
        # PSF scalar DC sweep: every swept point is a complete block.
        data=text.split('VALUE')[1].split('END')[0]
        sweep=re.findall(r'^"VGSVAR" (\S+)',data,re.M)
        values={f'VD{i}:p':[-float(v) for v in re.findall(r'^"VD'+str(i)+r':p" (?:"I" )?(\S+)',data,re.M)] for i in range(3)}
        x=np.array(sweep,dtype=float)
        assert len(x)==31 and all(len(v)==len(x) for v in values.values())
        row=dict(name=name,psf_sha256=previous.sha(raw),context=previous.read(p/'context.json'),vgs_v=x.tolist(),id_a=values,
            effective_settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1] for k in ['reltol','abstol(V)','abstol(I)','temp']})
        row['at_vgs']={str(vgs):{k:float(np.interp(vgs,x,v))*1e6 for k,v in values.items()} for vgs in [.797,.8,.81,.893,.9]}
        rows.append(row)
        ax.plot(x,np.array(values['VD1:p'])*1e6,color=COLORS[j],label=LABELS[j].split(' / ')[0]+' / '+str(row['context']['temp_c'])+' C')
        actual=[.893,.797,.797][j]
        ax.scatter(actual,np.interp(actual,x,values['VD1:p'])*1e6,color=COLORS[j],s=35,zorder=5)
    ax.axvline(.8,ls=':',color='#888');ax.axvline(.893,ls=':',color='#888')
    ax.set(xlabel='VGS (V)',ylabel='Drain current (uA)',title='Frozen Mmain: native DC current capability\nT28 nch_18_mac | W/L = 1 um / 150 nm | VS = 0.045 V, VB = 0, VDS = 0.4 V\nDots: representative acquired gate biases (~0.893 V TT; ~0.797 V SS)')
    ax.grid(alpha=.2);ax.legend();fig.savefig(FIG/'main_current.png',dpi=160);plt.close(fig)
    transient=previous.read(VERIFY/'transient.json')['cases'][1];iv=rows[1];comparison=[]
    for s in transient['samples']:
        if s['time_ns'] not in [110,120]:continue
        p=s['p'];vd=p['top_v']-p['vin_v']
        pred=float(np.interp(vd,[.1,.4,.75],[np.interp(p['vgs_v'],iv['vgs_v'],iv['id_a'][f'VD{i}:p'])*1e6 for i in range(3)]))
        comparison.append(dict(time_ns=s['time_ns'],transient_net_return_ua=p['net_input_return_ua'],DC_predicted_ua=pred,
            limitation='Linear interpolation of three VDS curves; DC VS=.045 V, actual VIN slightly higher; net return is not a direct branch-current measurement'))
    previous.dump(VERIFY/'dc_current.json',dict(rows=rows,SS_current_consistency=comparison,
        native_exit=0,all_native_PASS=True,scope='Isolated native DC current, not integrated time-varying Mmain current or validated redesign'))
    print(json.dumps([dict(name=r['name'],at_vgs=r['at_vgs'],settings=r['effective_settings']) for r in rows],indent=2))

if __name__=='__main__':
    import sys
    (dc if sys.argv[1:]==['dc'] else main)()
