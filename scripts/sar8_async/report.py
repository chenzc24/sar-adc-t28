"""Curate measured results; keep functional, timing and SOA gates separate."""
from pathlib import Path
import json
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from oa import ROOT,OUT
from analyze import load,edges,at,logic,compare


def read(path):return json.loads(path.read_text(encoding="utf-8"))


def word(w):
    return sum((1<<i)*(w[f"d{i}"]>.45).astype(int) for i in range(8))


def plot_signals(name,filename,title,signals,xlim):
    w=load(name);t=w["time"]*1e9
    fig,axs=plt.subplots(len(signals),1,figsize=(12,1.1*len(signals)+1.1),sharex=True,
                         gridspec_kw={"hspace":.12})
    for ax,(label,nets) in zip(axs,signals):
        if nets==["DOUT"]:
            ax.step(t,word(w),where="post",color="#176b8c",lw=1);ax.set_ylim(-8,265)
        else:
            for net in nets:ax.plot(t,w[net.lower()],lw=1,label=net)
            ax.set_ylim(-.18,1.15)
            if len(nets)>1:ax.legend(loc="upper right",ncol=len(nets),fontsize=8)
        ax.set_ylabel(label,rotation=0,ha="right",va="center",fontsize=9)
        ax.grid(alpha=.2);ax.spines[["right","top"]].set_visible(False)
        ax.set_xlim(*xlim)
    axs[-1].set_xlabel("Time (ns)")
    fig.suptitle(title,fontsize=12,y=.985)
    fig.subplots_adjust(left=.12,right=.98,top=.94,bottom=.08)
    folder=ROOT/"docs/figures/sar8_async_impl";folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/filename,dpi=160);plt.close(fig)


def figures():
    plot_signals("recovery_tight_aps","native_timing.png",
        "Native asynchronous controller | TT 0.9 V 27 C | APS, 5 ps maxstep | ideal ADC plant",
        [("CMP_CLK (V)",["CMP_CLK"]),("CAPTURE (V)",["CAPTURE"]),("ADVANCE (V)",["ADVANCE"]),
         ("Transaction (V)",["BUSY","VALID","FAULT"]),("Reference (V)",["BASE"]),("DOUT (code)",["DOUT"])],(42,92))
    plot_signals("recovery_fault_stuck_aps","fault_recovery.png",
        "Native controller: success / stuck comparator / recovery | functional PASS, SOA OPEN | APS",
        [("SAMPLE (V)",["SAMPLE"]),("CMP_CLK (V)",["CMP_CLK"]),("Status (V)",["VALID","FAULT"]),
         ("Reference (V)",["BASE"]),("DOUT (code)",["DOUT"])],(0,300))
    plot_signals("recovery_strongarm_pos_aps","native_comparator.png",
        "Native controller + unchanged StrongARM | code 145 | ideal sampled DAC | APS, TT",
        [("CMP_CLK (V)",["CMP_CLK"]),("Rails (V)",["COMP_P","COMP_N"]),("CAPTURE (V)",["CAPTURE"]),
         ("ADVANCE (V)",["ADVANCE"]),("VALID (V)",["VALID"])],(42,90))


def main():
    nominal=logic("recovery_tight_aps",145)
    assert nominal["pass_"]
    mode=compare("recovery_tight_aps","recovery_tt_ax")
    strongarm=logic("recovery_strongarm_pos_aps",145);assert strongarm["pass_"]
    w=load("recovery_tight_aps")
    gaps=[]
    for i in range(8):
        for q in (0,1):
            for rise in edges(w,f"sel{q}_{i}"):
                falls=edges(w,f"sel{1-q}_{i}",rising=False)
                before=falls[falls<rise]
                if len(before) and rise>45:gaps.append(float(rise-before[-1]))
    assert gaps and min(gaps)>0
    slow=load("recovery_slow_ax")
    off=edges(slow,"base",rising=False);off=off[(off>89)&(off<90)]
    assert len(off)==1
    hold=dict(base_v_at_89p7ns=at(w,"base",89.7),base_v_at_90p5ns=at(w,"base",90.5),
              deadline_to_base_off_ns=float(off[0]-89.01),
              bbm_min_opposite_select_deadtime_ns=min(gaps))
    assert hold["base_v_at_89p7ns"]>.8 and hold["base_v_at_90p5ns"]<.1
    fault=load("recovery_fault_stuck_aps")
    overshoot=dict(case="recovery_fault_stuck_aps",net="CAPTURE",
                   min_v=float(fault["capture"].min()),max_v=float(fault["capture"].max()),
                   scope="saved_node_extrema_not_all_device_terminal_maximum")
    cases=[]
    names=["recovery_tight_aps","recovery_tight_ax","recovery_tt_ax","recovery_strongarm_pos_aps"]
    names += ["recovery_"+k+"_ax" for k in ("fault_stuck","fault_illegal","abort","system_reset",
               "duplicate_start","slow","ff","ss","strongarm_neg","strongarm_high")]
    names += ["recovery_ss_aps","recovery_fault_stuck_aps","recovery_strongarm_neg_aps"]
    for name in names:
        r=read(OUT/"results"/(name+".json"));a=read(OUT/"analysis"/(name+"_observer.json"))
        assert r["ok"] and r["waveform_validation"]["all_requested_traces_finite"]
        deck=(OUT/"decks"/(name+".scs")).read_text(encoding="utf-8")
        log=(Path(r["metadata"]["output_dir"]).parent/"spectre.out").read_text(errors="replace")
        cases.append(dict(name=name,mode=r["mode"],execution_ok=r["ok"],
                          functional_pass=a["pass_"],soa_clean=a["soa_clean"],rows=a["rows"],
                          printed_cmi_warnings=a["printed_cmi_warnings"],suppressed_warnings=a["suppressed_warnings"],
                          deck_sha256=r["deck_sha256"],model_sha256=r["model_sha256"],
                          model_section=re.search(r"section=((?:tt|ss|ff)macro_mos_moscap)",deck)[1],
                          supply_v=float(re.search(r"\bSUP=([\d.]+)",deck)[1]),
                          temperature_c=float(re.search(r"temp=([\d.-]+) tnom",deck)[1]),
                          simulator_version=re.search(r"(?m)^Version (.+)$",log)[1].strip()))
    units={}
    for name in ("tgdff_gates_tt","tgdff_reset_unit","final_gates_ff_ax","final_gates_ss_ax"):
        r=read(OUT/"results"/(name+".json"))
        assert r["ok"] and r["waveform_validation"]["all_requested_traces_finite"]
        deck=(OUT/"decks"/(name+".scs")).read_text(encoding="utf-8")
        units[name]=dict(measurements=read(OUT/"analysis"/(name+".json")),execution_ok=r["ok"],
                         deck_sha256=r["deck_sha256"],mode=r["mode"],
                         model_section=re.search(r"section=((?:tt|ss|ff)macro_mos_moscap)",deck)[1],
                         supply_v=float(re.search(r"\bSUP=([\d.]+)",deck)[1]),
                         temperature_c=float(re.search(r"temp=([\d.-]+) tnom",deck)[1]))
    summary=dict(qualified=False,model=read(OUT/"model/summary.json"),
                 native_hierarchy=read(OUT/"audit/hierarchy.json"),
                 saved_oa=read(OUT/"audit/final_saved_state.json"),
                 actual_netlist_functional_abstraction=read(OUT/"netlist_logic/summary.json"),
                 nominal_timing=nominal,mode_control=mode,real_comparator_nominal=strongarm,
                 reference_handshake=hold,multi_frame_capture_voltage=overshoot,native_cases=cases,
                 unit_evidence=units,
                 unit_evidence_basis="All primitive definitions unchanged; only sar8a_status changed in recovery revision",
                 native_full_256_spectre=False,
                 open_gates=["SS 0.81V 125C 10MS/s deadline miss","multi-frame controller overvoltage",
                             "FF 0.99V device SOA","negative-input StrongARM SOA",
                             "ideal RC mapping/tolerances","full physical ADC noise/mismatch/layout"])
    target=ROOT/"verification/sar8_async/summary.json"
    target.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    figures()
    print(json.dumps(dict(reference_handshake=hold,native_cases=len(cases),qualified=False),indent=2))


if __name__=="__main__":
    import sys
    (figures if "--plots-only" in sys.argv else main)()
