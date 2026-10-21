"""Curate small measured reports, never raw PDK or waveform files."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output/sar8_physical"
p=argparse.ArgumentParser();p.add_argument("--final",required=True);p.add_argument("--tag",required=True);a=p.parse_args()
read=lambda path:json.loads(path.read_text())
rows=[]
for folder in sorted((OUT/"runs").iterdir()):
    if not (folder/"result.json").exists():continue
    result=read(folder/"result.json");context=read(folder/"context.json")
    row=dict(run=folder.name,result_ok=result["ok"],errors=result["errors"],
             deck_sha256=context["deck_sha256"],export_sha256=context["source_sha256"],
             case=context.get("case","passive"),source_export=context["source"].split("exports")[-1].replace("\\","/"))
    if (folder/"analysis.json").exists():row["analysis"]=read(folder/"analysis.json")
    rows.append(row)
final=next(r for r in rows if r["run"]==a.final);info=final["analysis"]
assert not info["unit"]
functional=all(info.get(key,False) for key in ("all_eight_events","all_codes_exact","all_codes_stable","all_reference_words_match_trial","all_output_rails_valid","all_two_phase_reference_steps_pass"))
electrical=(not info["has_CMI"] and info["LTE_count"]==0 and info["analog_stress_screen_pass"]
            and info["max_precompare_error_lsb"]<=.25 and info["max_held_error_mv"]<=1.7578125
            and not info["gate_conservative_overlap"])
report=dict(candidate="sar_adc8_join_r4",library="SAR_ADC_T28",adopted_as_baseline=False,
            test_scope="bounded TT0.9V27C four-frame transistor/device-level candidate; no performance qualification",
            final_run=a.final,nominal_functional_pass=functional,nominal_electrical_screen_pass=electrical,
            nominal_bounded_pass=functional and electrical,
            interface_sources_still_external=["VDD","reference rails","VINP/VINN","SAMPLE"],
            remaining=["full-code DNL/INL","FFT","PVT","transient noise","mismatch","power-up ramps/arbitrary clock state",
                       "all-logic terminal stress","reference buffer","area/driver optimization","DRC/LVS/PEX"],
            OA=read(OUT/f"postflight/{a.tag}_audit.json"),runs=rows)
deck=(OUT/"runs"/a.final/(a.final+".scs")).read_text()
report["model_sections"]=re.findall(r'(?m)^include "([^"]+)" section=(\w+)',deck)
report["solver_run_line"]=re.findall(r"(?m)^tran_physical tran .*",deck)
report["solver_options"]=re.findall(r"(?ms)^simulatorOptions options .*?(?=\n\S)",deck)
report["stated_conditions"]=dict(corner="TT",supply_v=.9,temperature_c=27,threads=4,
    mode="Spectre21.1 APS",requested_reltol=1e-6,effective_reltol=1e-7,
    maxstep_s=1e-11,vabstol=1e-8,iabstol=1e-13,method="gear2only",transient_noise=False,mismatch=False,
    data_definition="All sampled points for stated selected signals; complete analog67 terminal-pair screen")
report["netlist_provenance"]=read(ROOT/"netlist/sar8_physical/provenance.json")
assert report["OA"]["export_sha256"]==final["export_sha256"]==report["netlist_provenance"]["OA_export_sha256"]
dest=ROOT/"verification/sar8_physical/results.json"
dest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
print("CURATED",dest,"FUNCTIONAL",functional,"ELECTRICAL",electrical)
