"""Review already-collected PVT batch; no remote launch or baseline adoption."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import ROOT
from analyze import load
from loaded_analyze import VERIFY,resolve

CORNERS=['tt','sscold','sshot','ffcold','ffhot']
GROUPS=['bootstrap','reference','comparator','reference_driver','digital_control']

def data(run):
    _,paths,receipt=resolve(run)
    for kind in ['simulation','analysis']:
        s=json.loads(paths[kind+'.state.json'].read_text())
        assert s['status']=='complete' and s['exit_code']==0
    r=json.loads((VERIFY/(run+'_analysis.json')).read_text())
    assert r['frozen_inputs_sha_verified'] and r['stress_all_native_points']
    return r

def main():
    cases=[data('sar8fix-loaded-both-'+c) for c in CORNERS]
    rows=[]
    for r in cases:
        st=r['settling_estimates'];f=r['frames'][1]
        failed=json.loads(resolve(r['run_id'])[1]['derived/failing_pairs.json'].read_text())
        rows.append(dict(run_id=r['run_id'],codes=[x['code'] for x in r['frames']],
            event_counts_pass=r['all_event_counts_pass'],failed_pairs=r['failing_pairs'],
            failed_devices=len({x['instance'] for x in failed}),
            failed_devices_over_1mv=len({x['instance'] for x in failed if x['peak_v']-x['limit_v']>.001}),
            group_peaks={g:r['groups'][g]['peak_v'] for g in GROUPS},
            group_limits={g:r['groups'][g]['limit_v'] for g in GROUPS},
            startup_held_error_mv=r['frames'][0]['monitor_held_error_mv'],
            second_held_error_mv=f['monitor_held_error_mv'],conversion_ns=f['conversion_ns'],
            reset_last_ns=f['last_ref_reset_ns'],power_uw=f['supply_reference_average_uw'],
            max_deadline_error_mv=max(x['deadline_error_mv'] for x in st),
            settling_windows=len(st),all_settling_pass=all(x['settle_after_update_ns'] is not None and
                x['deadline_error_mv']<1.7578125 and not x['illegal_gate_states'] for x in st),
            actual_sample_window_ns=f['sample_window_ns'],actual_close_ns=f['sample_close_ns'],
            sim_peak_rss_mib=r['simulation_peak_rss_mib'],analysis_peak_rss_mib=r['analysis_peak_rss_mib']))
    pair=[]
    for run in ['sar8fix-loaded-comp-sscold','sar8fix-loaded-comp-p4-sscold']:
        r=data(run);_,w,t,_=load(ROOT/'output/managed_execution/runs'/run/'collected/derived')
        q=[x for x in r['comparisons'] if x['frame']==1][-1]
        values={}
        for key,when in [('at_write',q['write_ns']),('at_clock_plus_1p8ns',q['clock_ns']+1.8)]:
            values[key]={p:float(np.interp(when,t,w['xdut.comp_'+p])) for p in ['p','n']}
        pair.append(dict(run_id=run,output_v=values,write_after_clock_ns=q['write_ns']-q['clock_ns'],
            comp_energy_pj=r['frames'][1]['comparator_terminal_absorbed_energy_pj'],
            power_uw=r['frames'][1]['supply_reference_average_uw']))
    result=dict(scope='Five PVT points, two DC-start full-scale frames each; not full-code/sine/qualification',
        rows=rows,pmos_latch_control=pair,overall='NOT_CLOSED',
        next='IO receiving inverter control at TT and SS cold; original PMOS latch2 retained')
    (VERIFY/'loaded_pvt_review.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(3,1,figsize=(10,9),layout='constrained')
    ratio=np.array([[r['groups'][g]['peak_v']/r['groups'][g]['limit_v'] for r in cases] for g in GROUPS])
    ax[0].imshow(ratio,vmin=.4,vmax=1.2,cmap='RdYlGn_r',aspect='auto')
    names=['TT 0.90V 27C','SS 0.81V -40C','SS 0.81V 125C','FF 0.99V -40C','FF 0.99V 125C']
    ax[0].set_xticks(range(5),names,fontsize=8)
    ax[0].set_yticks(range(5),['Bootstrap','Reference IO','N4 comparator','Core ref. driver','Core logic'])
    for i,g in enumerate(GROUPS):
        for j,r in enumerate(cases):
            ax[0].text(j,i,'%.3f / %.2f V'%(r['groups'][g]['peak_v'],r['groups'][g]['limit_v']),ha='center',va='center',fontsize=9)
    ax[0].set_title('Native maximum / device-class screening limit (ratio > 1 fails)',fontsize=10)
    x=np.arange(5)
    for j,r in enumerate(cases):
        f=r['frames'][1];start=f['sample_start_ns'][0]-100;end=f['sample_close_ns'][0]-100
        ax[1].barh(j,end-start,left=start,height=.28,color='#368c85',label='Actual sample' if j==0 else None)
        comp=[q for q in r['comparisons'] if q['frame']==1];start=comp[0]['clock_ns']-100
        end=comp[-1]['write_ns']-100
        ax[1].barh(j,end-start,left=start,height=.28,color='#2864a0',label='First compare to last write' if j==0 else None)
        ax[1].scatter(f['last_ref_reset_ns'][0]-100,j,color='#c85637',marker='D',label='Last ref. reset' if j==0 else None)
    ax[1].axvline(100,color='#777',ls=':',label='Next external frame')
    ax[1].set(xlabel='Time from second frame start (ns)',xlim=(0,105));ax[1].set_yticks(x,names,fontsize=8);ax[1].invert_yaxis()
    ax[1].legend(fontsize=7,ncol=4,loc='upper center',bbox_to_anchor=(.5,1.2))
    power=[r['power_uw'] for r in rows];ax[2].bar(x,power,color='#368c85')
    ax[2].axhline(1000,color='#777',ls=':',label='1 mW target')
    for j,v in enumerate(power):ax[2].text(j,v+20,'%.1f'%v,ha='center',fontsize=9)
    ax[2].set(ylabel='VDD + reference power (uW)',ylim=(0,1120));ax[2].set_xticks(x,names,fontsize=8);ax[2].legend(fontsize=8)
    fig.suptitle('IO reference + N4 comparator | original physical control / BBM / Bootstrap\n'+
        '10 MS/s; differential +0.81 / -0.81 V; 50 ohm sources; 4 pF reference decoupling\n'+
        'Ideal external clock/supplies; no noise, mismatch or PEX; SS-hot startup code242, others243/12',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_pvt_summary.png',dpi=180);plt.close(fig)
    # Locate the newly exposed TT comparator-to-core interface stress.
    r=cases[0];_,w,t,_=load(ROOT/'output/managed_execution/runs'/r['run_id']/'collected/derived')
    peak=r['groups']['digital_control'];center=peak['time_ns'];sel=(t>center-.5)&(t<center+.6)
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout='constrained')
    for n in ['comp_p','comp_n']:ax[0].plot(t[sel],w['xdut.'+n][sel],label=n.upper())
    ax[0].axhline(.9,color='#888',ls=':',label='VDD .90 V');ax[0].axhline(.99,color='#c44',ls='--',label='Core gate-body screen .99 V')
    ax[0].set_ylabel('Raw output / receiver gate (V)')
    ax[1].plot(t[sel],w['xdut.cmp_clk'][sel],label='CMP_CLK');ax[1].set_ylabel('Compare clock (V)')
    ax[2].plot(t[sel],w['xdut.xctrl.phi_w'][sel],label='PHI_W');ax[2].plot(t[sel],w['xdut.phi_u'][sel],label='PHI_U');ax[2].set(ylabel='Write / update (V)',xlabel='Time (ns)')
    for a in ax:a.axvline(center,color='#777',ls=':');a.grid(alpha=.2);a.legend(fontsize=8,loc='best')
    fig.suptitle('TT / 0.90 V / 27 C | N4 output drives original core receiving inverter\n'+
        'Native receiver peak 1.01858 V at %.5f ns; vertical line marks exact peak time\n'%center+
        'Actual full ADC load; 20 ps display; ideal external clock/supplies; no noise/mismatch/PEX',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_receiver_stress.png',dpi=180);plt.close(fig)
    r=cases[2];_,w,t,_=load(ROOT/'output/managed_execution/runs'/r['run_id']/'collected/derived')
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True,layout='constrained')
    for frame,color,label in [(0,'#c85637','Frame1: DC starts with SAMPLE high'),(1,'#2864a0','Frame2: after normal precharge')]:
        start=frame*100+1;ids=(t>=start)&(t<=start+41)
        pin='vinp' if frame==0 else 'vinn';gate='xdut.xbootp.g' if frame==0 else 'xdut.xbootn.g'
        ax[0].plot(t[ids]-start,w[gate][ids]-w[pin][ids],color=color,label=label)
        diff=w['xdut.topp']-w['xdut.topn'];target=.81 if frame==0 else -.81
        ax[1].semilogy(t[ids]-start,np.maximum(np.abs(diff[ids]-target)*1000,.001),color=color,label=label)
        ax[2].plot(t[ids]-start,w['xdut.seq_sample'][ids],color=color,label=label)
    ax[0].axhline(0,color='#777',ls=':');ax[0].set_ylabel('High-input side\nG - VIN (V)')
    ax[1].axhline(1.7578125,color='#777',ls=':',label='0.25 LSB');ax[1].set(ylabel='Absolute top differential\nerror (mV)',ylim=(.001,2500))
    ax[2].set(ylabel='Actual sample gate (V)',xlabel='Time from nominal external sample start (ns)',xlim=(0,41))
    for a in ax:a.grid(alpha=.2);a.legend(fontsize=8,loc='best')
    fig.suptitle('SS / 0.81 V / 125 C | initial-state diagnosis, unchanged full ADC\n'+
        'Frame1 high input = P; frame2 high input = N; input order not controlled in this plot\n'+
        '50 ohm input/reference; ideal DC supplies; no power ramp, noise, mismatch or PEX',fontsize=10)
    fig.savefig(ROOT/'docs/figures/sar8_physical_repair/loaded_startup_diagnosis.png',dpi=180);plt.close(fig)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
