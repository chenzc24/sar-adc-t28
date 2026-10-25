"""Local analysis of small, verified native stream exports (no remote work)."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import ROOT

def analyze(corner,hybrid=False,long_window=False,native=False):
    run='sar8fix-'+('natlong' if native and long_window else 'natscreen' if native else 'hyblong' if long_window else 'hybscreen' if hybrid else 'ioscreen')+'-'+corner
    folder=ROOT/'output/managed_execution/runs'/run/'collected'
    manifest=json.loads((ROOT/'verification/sar8_physical_repair'/(run+'_manifest.json')).read_text())
    meta=json.loads((folder/'derived/wave.meta.json').read_text())
    names=(folder/'derived/wave.columns').read_text().splitlines()
    data=np.memmap(folder/'derived/wave.bin',dtype='<f8',mode='r').reshape((-1,len(names)))
    assert data.shape[0]==meta['points'] and meta['PSF_END'] and abs(data[-1,0]-(50e-9 if long_window else 20e-9))<1e-15
    def y(n):return data[:,names.index(n.lower())]
    t=data[:,0]*1e9;vdd=float(y('VDD')[-1]);clk=y('CLK')
    def crossing(values,level,start,end,up=True):
        ids=np.flatnonzero((t[:-1]>=start)&(t[1:]<=end)&
            ((values[:-1]<level)&(values[1:]>=level) if up else (values[:-1]>level)&(values[1:]<=level)))
        if not len(ids):return None
        i=ids[0];return float(t[i]+(level-values[i])*(t[i+1]-t[i])/(values[i+1]-values[i]))
    base=22 if long_window else 10;end=28 if long_window else 12
    rise=crossing(clk,vdd/2,base-.1,base+.2)
    fall=crossing(clk,vdd/2,end-.1,end+.2,False)
    results={}
    families=['core','N1','N4','N16'] if native else ['core','18h2','18h4','18h8'] if hybrid else ['core','18','18ud12']
    for family in families:
        tag='F'+family;out=y(tag+'Y')
        down=crossing(out,vdd/2,rise,end,False);up=crossing(out,vdd/2,fall,end+2)
        comp=[]
        for sign,suffix in [(1,'CP'),(-1,'CN')]:
            delta=y(tag+suffix+'OP')-y(tag+suffix+'ON')
            done=crossing(sign*delta,.8*vdd,rise,end-.05)
            final_delta=float(sign*np.interp(end-.1,t,delta))
            passed=done is not None and final_delta>=.8*vdd
            comp.append(dict(input_sign=sign,delay_ns=None if done is None else done-rise,
                             signed_output_before_reset_v=final_delta,
                             pass_window=passed,window_ns=end-.05-rise,
                             pass_1_9ns=passed and done-rise<=1.9))
        switch={}
        for scale in ([] if hybrid or native else [1] if family=='core' else [1,2,4]):
            p=tag+'S'+str(scale);bot=y(p+'B');rp=y(p+'RP')
            d={}
            for pol in ['n','p']:
                d[pol+'_ron_ohm']=float(.01/abs(np.interp(19,t,y(p+pol+'on:1'))))
                d[pol+'_off_A']=float(np.interp(19,t,y(p+pol+'off:1')))
            d['bottom_min_v']=float(bot.min());d['bottom_max_v']=float(bot.max())
            # Final persistent entry to residual band within this high/low interval.
            for label,start,window_end,err in [('low',rise,11.9,bot),('high',fall,13.9,bot-rp)]:
                mask=(t>=start)&(t<=window_end);ids=np.flatnonzero(mask);bad=ids[np.abs(err[ids])>1.7578125e-3]
                settled = len(ids)>0 and abs(err[ids[-1]])<=1.7578125e-3
                entry=(t[bad[-1]+1] if len(bad) else start) if settled else None
                d[label+'_settle_ns']=None if entry is None else float(entry-start)
                d[label+'_end_error_mV']=float(err[ids[-1]]*1000)
            switch[str(scale)]=d
        results[family]=dict(fo4_fall_delay_ps=None if down is None else (down-rise)*1000,
                             fo4_rise_delay_ps=None if up is None else (up-fall)*1000,
                             comparator=comp,reference=switch)
    log=(folder/'spectre.out').read_text(errors='replace')
    assert '0 errors' in log and 'Failed to find' not in log
    mapping=json.loads((ROOT/'output/managed_execution/runs'/run/'inputs/mapping.json').read_text())
    peaks=np.loadtxt(folder/'derived/wave.stress.tsv')
    stress={}
    for label in families:
        grouped={}
        for d in mapping['records']:
            if not d['instance'].startswith('F'+label+'C'):continue
            category='core' if d['model'] in ['nch_mac','pch_mac'] else 'IO'
            peak=peaks[d['pair_index'],1]
            if category not in grouped or peak>grouped[category]['peak_v']:
                grouped[category]=dict(instance=d['instance'],model=d['model'],terminal=d['terminal'],
                    peak_v=float(peak),time_ns=float(peaks[d['pair_index'],2]*1e9),limit_v=d['limit_v'])
        stress[label]=grouped
    result=dict(run_id=run,vdd=vdd,blocks=results,native=json.loads((folder/'derived/result.json').read_text()),
        warning_lines=[l.strip() for l in log.splitlines() if 'WARNING' in l],
        limits='UD12 limit unverified; nominal 1.8V devices use provisional 1.98V screen, not lifetime qualification; no integrated ADC qualification',
        comparator_stress=stress,off_current_bias_abs_vds_v=.01,
        off_current_scope='near-rail leakage only, NOT full off-state VDS=0.9 V leakage',
        comparator_input_diff_mV=1.7578125,comparator_CM_v=.45,
        load='comparator two 4.004 fF MOM units/output, no following logic; reference MSB 128 units to ground',
        fixture='Ideal clocks, ideal comparator input, separate 50 ohm/4pF high-reference per switch variant; no whole-CDAC coupling')
    vf=ROOT/'verification/sar8_physical_repair';(vf/(run+'_analysis.json')).write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    colors=dict(zip(families,['#536878','#dc663e','#168e88','#9b59b6']))
    for family in colors:
        tag='F'+family;c=colors[family]
        if not (hybrid or native) or family in families[:2]:
            axes[0].plot(t,y(tag+'Y'),color=c,label='core' if family=='core' else 'IO FO4 (same for candidates)' if hybrid or native else family)
        axes[1].plot(t,y(tag+'CPOP')-y(tag+'CPON'),color=c,label=family)
        if not (hybrid or native): axes[2].plot(t,y(tag+'S1B'),color=c,label=family+' / reference scale 1')
        else: axes[2].plot(t,y(tag+'CNON')-y(tag+'CNOP'),color=c,label=family+' / negative input')
    axes[0].plot(t,clk,'--',color='black',alpha=.4,label='ideal CLK')
    axes[1].axhline(.8*vdd,ls=':',color='black',lw=1,label='decision threshold')
    for ax in axes:
        ax.set_xlim(base-.2,end+2);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
    axes[0].set_ylabel('FO4 output (V)');axes[1].set_ylabel('Comparator OP-ON (V)');axes[2].set_ylabel('Negative decision (V)' if hybrid or native else 'MSB load node (V)')
    axes[-1].set_xlabel('Time (ns)')
    fig.suptitle(manifest['corner'].upper()+' / '+str(manifest['temp_c'])+' C | VDD='+str(vdd)+' V | native block fixtures, ideal stimulus\nComparator: VCM=0.45 V, differential +1.758 mV, 8 fF/output; NOT integrated ADC',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.98]);figdir=ROOT/'docs/figures/sar8_physical_repair';figdir.mkdir(exist_ok=True)
    fig.savefig(figdir/(run+'.png'),dpi=160);plt.close(fig)
    print(json.dumps(dict(run=run,blocks=results),indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corner');p.add_argument('--hybrid',action='store_true');p.add_argument('--long-window',action='store_true');p.add_argument('--native',action='store_true');a=p.parse_args();analyze(a.corner,a.hybrid,a.long_window,a.native)
