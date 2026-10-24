"""Check candidate ownership/invariants and digital-device provenance locally."""
import collections
import re
from prepare import mapping, group, manifest
from control import ROOT, OUT, VERIFY, transport
read,dump,sha=transport.read,transport.dump,transport.sha


def main():
    names=read(VERIFY/'setup.json')['names'];cases=[]
    for name in names:
        folder=OUT/name;ctx=read(folder/'context.json')
        assert sha(folder/'dut.scs')==ctx['DUT_sha256']
        assert sha(folder/'test.scs')==ctx['deck_sha256']
        assert sha(folder/'r4_perf_monitor.va')==ctx['monitor_sha256']
        dut=(folder/'dut.scs').read_text();dev=mapping.mapping(dut)
        assert len(ctx['stress_devices'])==1833
        saves=set(ctx['saved_signals'])
        assert all(n=='0' or n.lower() in saves for d in ctx['stress_devices'] for n in d['nodes'].values())
        assert all(s.lower() in saves for s in ctx['current_signals'])
        assert not re.search(r'\)\s+(?:vsource|isource|bsource|ref_symmetric_diag)\b',dut)
        assert ctx['spectre_args'][-1]=='-preset_override'
        dump(VERIFY/(name+'_setup.json'),manifest(ctx))
        cases.append(dict(name=name,MOS_coverage=1833,terminal_pairs=10998,
                          current_probes=len(ctx['current_signals']),source_hashes=True,
                          ideal_internal_helpers=False,OA_changed=False))
    digital={k:v for k,v in dev.items() if group(k) in ['digital_control','reference_driver']}
    models=dict(collections.Counter(v['model'] for v in digital.values()))
    assert set(models)<=set(['nch_mac','pch_mac','rupolym','cfmom_2t'])
    evidence=dict(standard_cell_library=False,implementation='Project-defined CMOS gate/DFF/async-controller subcircuits using T28 PDK devices',
                  core_primitives=['sar8p_inv','sar8p_nand2','sar8p_dffr'],
                  digital_leaf_models=models,
                  timing_passives='PDK rupolym resistors and cfmom_2t MOM capacitors; not the older ideal RC implementation',
                  source='scripts/sar8_physical/circuit.py',
                  sample_native_DUT_sha256=sha(OUT/names[0]/'dut.scs'),
                  exclusions='Not standard-cell synthesis/STA/physical signoff; no timing/power library qualification inferred')
    dump(VERIFY/'digital_provenance.json',evidence)
    dump(VERIFY/'source_validation.json',dict(ok=True,cases=cases,simulation_results_pending=True))
    print('PASS source hashes/full MOS probes/native-only DUT; digital leaf models:',models)


if __name__=='__main__':main()
