"""Specific compact_v2 short/long review; read only collected compact evidence."""
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import builder as b
import review_stream

HERE=Path(__file__).resolve().parent
OUT=HERE/'result_review'
SOURCE=HERE/'stream_package/common/mapping.json'


def read_case(case):
    run='sar8audit-sample-v2-'+case
    folder=b.ROOT/'output/managed_execution/runs'/run/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text())
    # Parent and preceding local bounded reads already verified every SHA.
    # This review checks frozen sizes/metadata and does not reread raw PSF.
    total=0
    for item in receipt['files']:
        assert (folder/item['name']).stat().st_size==item['bytes']
        total+=item['bytes']
    assert total<32*1024**2
    status=receipt['status']
    assert status['simulation']['status']==status['analysis']['status']=='complete'
    assert status['simulation']['exit_code']==status['analysis']['exit_code']==0
    derived=folder/'derived'
    meta=json.loads((derived/'wave.meta.json').read_text())
    stress=json.loads((derived/'result.json').read_text())
    columns=(derived/'wave.columns').read_text().splitlines()
    matrix=np.memmap(derived/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],len(columns)))
    assert (derived/'wave.bin').stat().st_size==matrix.nbytes
    indices={n:i for i,n in enumerate(columns)}
    t=matrix[:,indices['time']]
    assert t[0]==0 and np.all(np.diff(t)>0) and abs(t[-1]-160e-9)<1e-15
    names=json.loads(SOURCE.read_text())['signal_map']
    at=lambda name,x:float(np.interp(x,t,matrix[:,indices[name]]))
    events={}
    for line in (derived/'wave.events.tsv').read_text().splitlines():
        name,up,time=line.split();events.setdefault(name,[]).append((float(time),int(up)))
    result=review_stream.summarize(events,at,names)
    opening=result['actual_open_ns']*1e-9
    close=result['actual_close_ns']*1e-9
    prior=[x for x,up in events[names['seq_sample']] if not up and x<opening]
    precharge=prior[-1] if prior else None
    result.update(run_id=run,source=folder.relative_to(b.ROOT).as_posix(),
        collected_bytes=total,wave_bytes=matrix.nbytes,native_points=meta['native_points'],
        compact_points=meta['points'],stress_failed_pairs=stress['failing_pairs'],
        stress_checked_pairs=stress['all_MOS_pairs'],
        precharge_low_start_ns=None if precharge is None else precharge*1e9,
        observed_low_interval_ns=None if precharge is None else (opening-precharge)*1e9,
        initial_low_state=at(names['seq_sample'],0)<.081,
        supply_v_at_held=at('vdd!',141.8e-9),
        simulation_peak_rss_mib=status['simulation']['peak_rss_bytes']/1024**2,
        analysis_peak_rss_mib=status['analysis'].get('peak_rss_bytes',0)/1024**2,
        receipt_sha256=hashlib.sha256((folder/'collection_receipt.json').read_bytes()).hexdigest(),
        original_input_SHA_verified_before_review=True)
    inst=json.loads((HERE/'compact_v2/boundary_loads.json').read_text())['device_mapping_without_geometry']
    imap={row['instance']:row['label'].lower() for row in inst}
    sample_times={'DC':0,'before_open':opening-.01e-9,'at110ns':110e-9,
                  'preclose':close-.2e-9,'held':141.8e-9}
    snapshots={}
    for label,x in sample_times.items():
        sides={}
        for side in ['p','n']:
            stem='xf.xdut__xboot'+side+'__'
            values={n:at(stem+n,x) for n in ['g','btop','bbot','ctrl','greset','clksb']}
            values.update(vin_v=at(names['vin_'+side],x),top_v=at(names['top_'+side],x))
            values['cboot_v']=values['btop']-values['bbot']
            values['main_g_minus_input_v']=values['g']-values['vin_v']
            values['M4C_gate_minus_BBOT_v']=at(names['seq_sample'],x)-values['bbot']
            for device in ['Mmain','Mmain_U1','M8','M2','M4','Msin']:
                native='xf.'+imap['XDUT.XBOOT'+side.upper()+'.'+device]
                for port,terminal in [(1,'drain'),(2,'gate')]:
                    values[device+'_'+terminal+'_ua']=at(native+':'+str(port),x)*1e6
            sides[side]=values
        snapshots[label]=dict(time_ns=x*1e9,**sides)
    result['snapshots']=snapshots
    # Independent preset targets, not inferred from observed gate voltages.
    errors=[]
    for side in ['p','n']:
        for bit in range(8):
            target=.9 if ((side=='p')!=(bit==7)) else 0
            node='xf.xdut__xcdac__b'+side+str(bit)
            errors.append(abs(at(node,141.8e-9)-target))
    result['held_bottom_max_preset_error_mv']=max(errors)*1000
    result['actual_settings']=status['simulation']['native']['effective_settings']
    result['global_warning']='SFE-2453 global VDD!/0 also declared as subckt terminals; actual ports are wired to the corresponding global nodes'
    return result,dict(t=t,matrix=matrix,indices=indices,at=at,names=names)


def plot(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'short':'#c34c3c','long':'#227b87'}
    fig,axes=plt.subplots(4,2,figsize=(12,10.5),sharex='col',layout='constrained')
    for case,(result,w) in cases.items():
        x=w['t']*1e9;sel=(x>=99.8)&(x<=143)
        def trace(name):return w['matrix'][:,w['indices'][name]][sel]
        xx=x[sel];color=colors[case];label='Short-low history' if case=='short' else'Long-low history'
        axes[0,0].plot(xx,trace(w['names']['seq_sample']),color=color,label=label)
        axes[0,1].plot(xx,trace('vinp'),color=color,ls=':',lw=1)
        axes[0,1].plot(xx,trace(w['names']['top_p']),color=color,label=label+' TOPP')
        axes[1,0].plot(xx,trace(w['names']['boot_p_btop'])-trace(w['names']['boot_p_bbot']),color=color,label=label)
        axes[1,1].plot(xx,trace(w['names']['boot_p_g'])-trace('vinp'),color=color,label=label)
        axes[2,0].plot(xx,trace(w['names']['boot_p_bbot']),color=color,label=label+' BBOT')
        axes[2,0].plot(xx,trace(w['names']['boot_p_ctrl']),color=color,ls='--',label=label+' CTRL')
        imap=json.loads((HERE/'compact_v2/boundary_loads.json').read_text())['device_mapping_without_geometry']
        ids={r['instance']:r['label'].lower() for r in imap}
        current=sum(trace('xf.'+ids['XDUT.XBOOTP.'+n]+':1') for n in ['Mmain','Mmain_U1'])*1e6
        axes[2,1].plot(xx,current,color=color,label=label)
        axes[3,0].plot(xx,(trace(w['names']['top_p'])-trace(w['names']['top_n'])+.81)*1000,color=color,label=label)
        axes[3,1].plot(xx,trace(w['names']['top_n']),color=color,label=label+' TOPN')
        for ax in axes.flat:
            ax.axvline(result['actual_open_ns'],color=color,ls=':',lw=.8)
            ax.axvline(result['actual_close_ns'],color=color,ls=':',lw=.8)
    axes[0,0].set_ylabel('SEQ_SAMPLE (V)')
    axes[0,1].set_ylabel('P side top / input (V)')
    axes[0,1].axhline(.045,color='#555',ls='--',lw=.8,label='P target .045 V')
    axes[1,0].set_ylabel('P Cboot voltage (V)')
    axes[1,0].axhline(.81,color='#555',ls='--',lw=.8,label='VDD .81 V')
    axes[1,1].set_ylabel('P main G - VIN (V)')
    axes[1,1].axhline(0,color='#555',lw=.8)
    axes[2,0].set_ylabel('P BBOT / CTRL (V)')
    axes[2,1].set_ylabel('P main drain current (uA)')
    axes[2,1].axhline(0,color='#555',lw=.8)
    axes[3,0].set_ylabel('Top differential error (mV)')
    axes[3,0].set_yscale('symlog',linthresh=1)
    axes[3,0].axhspan(-1.7578125,1.7578125,color='#8ab888',alpha=.2,label='Historical +/- .25 LSB screen')
    axes[3,1].set_ylabel('N side top (V)')
    axes[3,1].axhline(.855,color='#555',ls='--',lw=.8,label='N target .855 V')
    for ax in axes.flat:
        ax.set_xlim(99.8,143);ax.grid(alpha=.2);ax.legend(fontsize=7,loc='best')
    for ax in axes[-1]:ax.set_xlabel('Absolute time (ns)')
    fig.suptitle('SS / 0.81 V / 125 C | compact sampling fixture | N4 held in reset\n'
        'Same devices, inputs and reference preset; only SAMPLE prehistory differs\n'
        '20 ps compact voltage/current estimates; dotted lines = native SEQ opening/closing',fontsize=11)
    fig.savefig(OUT/'short_long_diagnosis.png',dpi=170)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    cases={case:read_case(case) for case in ['short','long']}
    total=sum(v[0]['collected_bytes'] for v in cases.values())
    assert total<32*1024**2
    report=dict(scope='specific compact_v2 SS-hot startup-history experiment',
        combined_collected_bytes=total,cases={k:v[0] for k,v in cases.items()},
        verdict='short prehistory leaves P Bootstrap acquisition disabled; long low succeeds in this bounded fixture; no common extraction fault demonstrated',
        caution='different initial histories also change initial stored top voltage; not a sweep of minimum safe precharge duration or a real POR test')
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    plot(cases)
    for case,(r,_) in cases.items():
        print(case,json.dumps({k:r[k] for k in ['actual_open_ns','actual_close_ns','observed_low_interval_ns',
            'preclose_error_mv','raw_held_source_error_mv','raw_held_diff_mv','stress_failed_pairs',
            'held_bottom_max_preset_error_mv']},indent=2))


if __name__=='__main__':main()
