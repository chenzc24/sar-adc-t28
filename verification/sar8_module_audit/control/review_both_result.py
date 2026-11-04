"""Short source/v1/both comparison with native KCL and MP1 total-current charge."""
import hashlib
import json
import os

import numpy as np
import yaml

import prepare_first_event as base
import prepare_sn_load_variants as loads
import review_first_event_v1 as previous

OWN,ROOT=base.OWN,base.ROOT
RUN='sar8audit-ctrl-snload-both-v1'
HASH='66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c'
OUT=OWN/'sn_load_variants_v1/both_results'
P='xdut.xctrl.xtim.'


def read_current_run(run_id=RUN,expected_hash=HASH):
    folder=ROOT/'output/managed_execution/runs'/run_id
    receipt=json.loads((folder/'collected/collection_receipt.json').read_bytes())
    if receipt['skipped']:raise ValueError('Incomplete current collection')
    data={}
    for entry in receipt['files']:
        relative=entry['name']
        if relative.startswith(('/','\\')) or '..' in relative.replace('\\','/').split('/'):
            raise ValueError('Unsafe receipt member')
        path=folder/'collected'/relative
        if not path.exists() or base.digest(path.read_bytes())!=entry['sha256']:
            path=path.with_name(path.stem+'.'+entry['sha256'][:12]+path.suffix)
        blob=path.read_bytes()
        if len(blob)!=entry['bytes'] or base.digest(blob)!=entry['sha256']:
            raise ValueError('Collected SHA/size differs')
        data[relative]=blob
    if sum(len(b) for b in data.values())!=receipt['total_bytes']:raise ValueError('Receipt total differs')
    record=yaml.safe_load((ROOT/'management/runs'/(run_id+'.yaml')).read_text())
    recipe=record['recipe']
    if (record['recipe_hash']!=expected_hash
            or base.digest(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode())!=expected_hash):
        raise ValueError('Current run recipe differs')
    for item in recipe['files']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Registered current-run input changed')
    states={k:json.loads(data[k+'.state.json']) for k in ['simulation','analysis']}
    if any(s['status']!='complete' or s['exit_code']!=0 for s in states.values()):
        raise ValueError('Current run not complete')
    native=states['simulation']['native']
    if not native['native_analysis_pass'] or not native['zero_error_footer']:raise ValueError('Native failure')
    result=json.loads(data['derived/result.json'])
    names=json.loads(data['derived/peak.columns.json'])['names']
    table=np.frombuffer(data['derived/peak.native.bin'],'<f8').reshape((-1,len(names)))
    if (not result['native_PSF_END'] or result['missing_required_signals'] or len(table)!=result['diagnostic_points']
            or not np.isfinite(table).all() or not np.all(np.diff(table[:,0])>0)):
        raise ValueError('Invalid current table/END/signals')
    manifest=(folder/'inputs/measurement.json').read_bytes()
    if base.digest(manifest)!=result['measurement_sha256']:raise ValueError('Measurement hash differs')
    measure=json.loads(manifest)
    for node in measure['critical_kcl_nodes']:
        terms=measure['kcl_terms'][node]
        exact=np.array([sum(row[names.index(term)] for term in terms) for row in table])
        if not np.array_equal(exact,table[:,names.index('kcl:'+node.lower())]):raise ValueError('KCL sum differs')
    proof=dict(run=run_id,recipe_sha256=expected_hash,receipt_files=len(data),receipt_bytes=receipt['total_bytes'],
        required_currents=len(measure['current_saves']),native_points=result['native_points'],
        local_diagnostic_points=len(table),END=result['native_PSF_END'],all_receipt_and_input_hashes_match=True,
        critical_kcl_max_a=max(result['node_kcl'][n.lower()]['max_abs_a'] for n in measure['critical_kcl_nodes']),
        native_warning_codes=native['warning_codes'])
    return table,names,result,measure,proof


def main():
    source,source_names,_=base.collected()
    old,old_names,old_result,old_measure,_,_,_=previous.collect_readonly()
    source_sn,sn_names,_=loads.read_supplement('sar8audit-ctrl-source-sn-v1',loads.SOURCE,loads.SOURCE_SHA)
    old_sn,osn_names,_=loads.read_supplement('sar8audit-ctrl-fixture-sn-v1',loads.FIXTURE,loads.FIXTURE_SHA)
    new,new_names,result,measure,proof=read_current_run()
    datasets={'source':(source,source_names),'v1':(old,old_names),'both':(new,new_names)}
    triples={}
    for signal in [P+'sn',P+'live',P+'x020.n']:
        triples[signal]={}
        for label,(table,names) in datasets.items():
            if signal==P+'sn' and label!='both':
                table,names=(source_sn,sn_names) if label=='source' else (old_sn,osn_names)
            v=table[:,names.index(signal)]
            triples[signal][label]=dict(max_v=float(v.max()),min_v=float(v.min()),
                max_time_s=float(table[int(v.argmax()),0]),
                rise_halfrail_s=base.edge_time(table[:,0],v,.99,True))
    charges={}
    trace=P+'x020.x000.mp1:1'
    for label,table,names,at in [('v1',old,old_names,old_result['peak_snapshot']['time_s']),
                               ('both',new,new_names,result['peak_snapshot']['time_s'])]:
        times,q=previous.integrate_native(table[:,0],table[:,[names.index(trace)]],41.04e-9,at)
        charges[label]=dict(start_s=float(times[0]),stop_s=float(times[-1]),prepeak_net_into_N_c=float(q[-1,0]),
            total_terminal_current_only=True,source_whole_ADC_current_not_directly_measured=True)
    summary=dict(proof=proof,three_way=triples,MP1_charge=charges,
        peak_error_v=result['peak_error_v'],peak_time_error_s=result['peak_time_error_s'],
        max_initial_error_v=result['max_initial_witness_error_v'],
        fidelity_difference_explained='Restoring the four original SN gate loads largely removes the v1 discrepancy; no need to run individual branches now.',
        remaining_fault='Original approximately 88.64mV N overshoot and CMI remain. This correction is to the fixture, not a repaired ADC.',
        full_ADC_qualified=False)
    OUT.mkdir(exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    styles={'source':dict(color='#255d83',lw=1.8),'v1':dict(color='#999999',lw=1.2,ls='--'),
            'both':dict(color='#d16b24',lw=1.3,ls=':')}
    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,7.8),layout='constrained')
    for ax,signal in zip(axes,[P+'sn',P+'live',P+'x020.n']):
        for label,(table,names) in datasets.items():
            if signal==P+'sn' and label!='both':table,names=(source_sn,sn_names) if label=='source' else (old_sn,osn_names)
            ax.plot(table[:,0]*1e9,table[:,names.index(signal)],label=label,**styles[label])
        ax.set(ylabel='Voltage (V)',title=signal.removeprefix(P).upper());ax.grid(alpha=.2)
    axes[0].legend(fontsize=8,ncol=3,loc='center right')
    axes[2].axhline(.99,ls='--',lw=.8,color='#a04848')
    axes[-1].set(xlim=(41.04,41.125),xlabel='Original time (ns); no alignment or fitting')
    fig.suptitle('SN load correction matches the source; N overshoot remains',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | source, isolated v1, four-MOS load correction | before first comparison\n'
                  'External supply/clock ideal; local recorded boundaries; no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'three_way_timing.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(2,1,sharex=True,figsize=(10,6),layout='constrained')
    for label,(table,names) in [('v1',(old,old_names)),('both',(new,new_names))]:
        axes[0].plot(table[:,0]*1e9,table[:,names.index(trace)]*1e6,label=label,**styles[label])
        times,q=previous.integrate_native(table[:,0],table[:,[names.index(trace)]],41.04e-9,41.12e-9)
        axes[1].plot(times*1e9,q[:,0]*1e15,**styles[label])
    axes[0].set(ylabel='MP1 drain current (uA)',title='Positive leaves N; negative injects into N');axes[0].legend(fontsize=8)
    axes[1].set(ylabel='Net charge into N (fC)',xlabel='Original time (ns)',xlim=(41.04,41.12))
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('MP1 total terminal current and native-grid charge',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | original v1 versus corrected local fixture | no component decomposition\n'
                  'Original full-ADC branch current was not directly measured; no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'MP1_charge.png',dpi=165);plt.close(fig)
    print(json.dumps(dict(proof=proof,peak_error_v=result['peak_error_v'],peak_error_s=result['peak_time_error_s'],
        charge=charges,SN_and_LIVE=triples),indent=2))


if __name__=='__main__':main()
