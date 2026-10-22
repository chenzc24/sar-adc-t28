"""Tracked setup/provenance checkpoint, preserving original and recovery identities."""
from common import ROOT,OUT,read,dump,sha

paths=list((ROOT/"scripts/sar8_r4_performance").glob("*.py"))+list((ROOT/"models/veriloga/sar8_r4_performance").glob("*.va"))
paths += [ROOT/"config/sar8_r4_performance.yaml",ROOT/"verification/sar8_r4_performance/test_metrics.py"]
preflight=read(OUT/"preflight.json")
preflight.pop("resources",None)
state=read(OUT/'flow_status.json')
finished=state['stage'] in ('complete_pending_review','complete_reviewed')
record=dict(status='characterization_complete_stress_not_qualified' if finished else 'production_running_no_final_static_or_dynamic_metrics',DUT="sar_adc8_join_r4",
    preflight=preflight,pilot_comparison=read(OUT/"pilot_comparison.json"),
    smoke_summary=[{k:v for k,v in read(OUT/"cases"/n/"analysis.json").items() if k in
        ("name","invalid_frames","frame_integrity_pass","warnings","numerical_diagnostics","initial_DC_diagnostics","SOA_warning_examples","all_brackets_pass")}
        for n in ("smoke_static_cx","smoke_sine_cx")],
    source_sha256={str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in paths},
    production_cases={p.parent.name:read(p) for p in sorted((OUT/"cases").glob("*/context.json"))
        if p.parent.name.startswith(("static_cx_","sine_cx_1024"))},
    status_path="output/sar8_r4_performance/flow_status.json",
    selected_solver="Spectre X CX 4 threads; default preset effective tolerances, compared against tighter APS/X",
    qualification_note="CMI retained in static and continuous-sine tests; performance is not device-stress qualification or baseline adoption.")
if finished:
    record['results_path']='verification/sar8_r4_performance/results.json'
    record['results_sha256']=sha(ROOT/record['results_path'])
    record['recovery_mapping']=read(OUT/'recovery_20261022_r2.json')['mapping']
dump(ROOT/"verification/sar8_r4_performance/setup.json",record)
print("CHECKPOINT_WRITTEN",len(record["production_cases"]))
