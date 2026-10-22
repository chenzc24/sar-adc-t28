"""Curate metrics and native candidate definitions without raw/PDK model files."""
import argparse
import numpy as np
from flow import ROOT,OUT,prior,read,dump,sha,cells


def curate(names):
    summaries=[]
    for name in names:
        folder=OUT/name;a=read(folder/'analysis.json');ctx=read(folder/'context.json')
        row={k:v for k,v in a.items() if k!='stress'}
        row['reference_terminal_stress']=[s for s in a['stress'] if s['group']=='reference']
        row['worst_by_group']={g:max((s for s in a['stress'] if s['group']==g),key=lambda s:s['peak_v']) for g in a['groups']}
        row['configuration']={k:ctx[k] for k in ['order','rg_parallel','driver_factor','stepcap','stop_ns','outputstart_ns','spectre_args','frozen_DUT_sha256','DUT_sha256','deck_sha256','monitor_sha256']}
        row['native_result']=read(folder/'result.json')
        previous_A=read(ROOT/'output/sar8_r4_reset/reset_first_c20_late4600/analysis.json')['frames']
        row['versus_A_code_differences']=[dict(frame=f['frame'],A=previous_A[f['frame']]['code'],candidate=f['code'])
            for f in a['frames'] if f['code']!=previous_A[f['frame']]['code']]
        if (folder/'transfer.json').exists():row['transfer_integrity']=read(folder/'transfer.json')
        deck=(folder/'test.scs').read_text()
        row['model_includes']=[line for line in deck.splitlines() if line.startswith('include ')]
        row['test_environment']=dict(supply_v=.9,temperature_c=27,sample_rate_hz=10e6,
            sine_frequency_hz=4501953.125,sine_dbfs=-1,input_resistance_ohm_per_side=50,
            reference_resistance_ohm_per_rail=50,reference_capacitance_f_per_rail=4e-12,
            ideal_external_sources=['supplies','analog input','SAMPLE'],
            transient_noise=False,mismatch=False,post_layout=False,
            simulator='Spectre21.1 X CX',threads=4,profile='t28_io')
        w=np.load(folder/'wave.npz');tn=w['time']*1e9;m=(tn>=500.8)&(tn<=508)
        worst=row['worst_by_group']['reference'];index=int(np.argmin(np.abs(tn-worst['time_ns'])))
        device=next(d for d in ctx['stress_devices'] if d['instance']==worst['instance'])
        row['worst_reference_sample']=dict(instance=device['instance'],time_ns=float(tn[index]),
            nodes=device['nodes'],terminal_voltages_v={key:0.0 if net=='0' else float(w[net.lower()][index]) for key,net in device['nodes'].items()},
            bootstrap_enable_v=float(w['xdut.seq_sample'][index]))
        if m.any():
            ids=np.flatnonzero(m);k=ids[np.argmax(w['xdut.gnn3'][m])]
            row['GNN3_event_500p8_508ns']=dict(peak_v=float(w['xdut.gnn3'][k]),time_ns=float(tn[k]),
                driver_v_at_gate_peak=float(w['xdut.xref.xdrv3.gnndrv'][k]),
                resistor_gate_end_current_ua_at_gate_peak=float(w['xdut.xref.xdrv3.rgnn1_5__dmy0:2'][k]*1e6),
                current_sign='Positive enters resistor terminal2 from GNN3, removing charge from gate.',
                BP6_min_v=float(w['xdut.xcdac.bp6'][m].min()),BN6_max_v=float(w['xdut.xcdac.bn6'][m].max()))
        w.close();summaries.append(row)
    dump(ROOT/'verification/sar8_r4_staged/results.json',summaries)
    # Top block replaces (not supplements) frozen top; appended cells depend on frozen leaves.
    selected=OUT/'msb_600/dut.scs';baseline=cells(prior.FROZEN.read_text());candidate=cells(selected.read_text())
    names_changed=[k for k in candidate if k not in baseline or prior.compact(candidate[k])!=prior.compact(baseline[k])]
    assert set(names_changed)=={'sar_adc8_join_r4','sar8r_delay','sar8r_edge','sar8s_step','sar8s_refword'}
    dest=ROOT/'netlist/sar8_r4_staged';dest.mkdir(parents=True,exist_ok=True)
    text='// Experimental MSB-first reset. Replace frozen top; retain frozen leaf definitions.\n'
    text+='// Not standalone and not an OA export. Reproduce full deck with flow.py prepare --order msb.\n'
    text+='\n\n'.join(candidate[k].rstrip() for k in names_changed)+'\n'
    (dest/'msb_first_cells.scs').write_text(text)
    dump(dest/'provenance.json',dict(frozen_file='netlist/sar8_physical/dut.scs',frozen_sha256=sha(prior.FROZEN),
        candidate_DUT_sha256=sha(selected),curated_sha256=sha(dest/'msb_first_cells.scs'),
        changed_or_added_cells=names_changed,OA_changed=False,baseline_promoted=False,
        generator='scripts/sar8_r4_staged/flow.py',case_manifest=[r['configuration']|{'name':r['name']} for r in summaries]))
    print('Curated',names)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args();curate(a.names)
