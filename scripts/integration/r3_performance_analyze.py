"""Whole-ADC transition metrics and uncorrected coherent sampled spectrum."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

import numpy as np
from r3_performance import ROOT,OUT,LSB,r3,dump,baseline


def read_case(name):
    ctx=r3.r1.read_json(OUT/f"cases/{name}.json")
    result=r3.r1.read_json(OUT/f"runs/{name}_result.json")
    assert result["ok"],(name,result["errors"])
    assert r3.r1.sha(OUT/f"decks/{name}.scs")==ctx["deck_sha256"]==result["deck_sha256"]
    w={k:np.asarray(v) for k,v in r3.r1.read_json(OUT/f"runs/{name}_waveform.json").items()}
    assert np.all(np.diff(w["time"])>0) and all(np.isfinite(v).all() for v in w.values())
    assert w["time"][-1]>=ctx["stop_ns"]*1e-9-1e-14
    p=Path(result["metadata"]["output_dir"]).parent/"spectre.out"
    log=p.read_text(encoding="utf-8",errors="replace")
    codes={c:len(re.findall(r'WARNING \('+re.escape(c)+r'\)',log)) for c in set(re.findall(r'WARNING \(([^)]+)\)',log))}
    issues=dict(warning_codes=codes,CMI_count=sum(v for k,v in codes.items() if k.startswith("CMI-")),
        LTE_or_suppressed=[s.strip() for s in log.splitlines() if re.search(r'suppressed|\bLTE\b|convergence failure',s,re.I)],
        initial_DC_diagnostics=[s.strip() for s in log.splitlines() if re.search(r'GminDC|Bad pivoting|homotopy',s)])
    return ctx,result,w,log,issues


def measurement(name):
    ctx,result,w,log,issues=read_case(name)
    rows=[]
    pattern=r'R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([\d.eE+-]+)'
    for m in re.finditer(pattern,log):
        f,code,nc,early,valid=map(int,m.groups()[:5])
        rows.append(dict(frame=f,code=code,compares=nc,early_code=early,valid=bool(valid),rail_error_v=float(m[6])))
    assert len(rows)==ctx["frames"] and [r["frame"] for r in rows]==list(range(ctx["frames"])),(name,len(rows),ctx["frames"])
    targets=(98+100*np.arange(ctx["frames"]))*1e-9
    idx=np.searchsorted(w["time"],targets).clip(0,len(w["time"])-1)
    prev=np.maximum(idx-1,0)
    idx=np.where(abs(w["time"][prev]-targets)<abs(w["time"][idx]-targets),prev,idx)
    assert np.max(abs(w["time"][idx]-targets))<1e-13
    decoded=sum((w[f"d{b}"][idx]>.45).astype(int)*(1<<b) for b in range(8))
    assert decoded.tolist()==[r["code"] for r in rows]
    assert all(r["valid"] and r["compares"]==8 for r in rows[ctx["warmup"]:]),name
    report=dict(name=name,context=ctx,result_ok=True,frame_monitor=rows,issues=issues,
                result_sha256=r3.r1.sha(OUT/f"runs/{name}_result.json"),
                waveform_sha256=r3.r1.sha(OUT/f"runs/{name}_waveform.json"),
                log_sha256=r3.r1.sha(Path(result["metadata"]["output_dir"]).parent/"spectre.out"))
    return report,w,log


def static_case(name):
    row,w,log=measurement(name);ctx=row["context"]
    thresholds=[dict(k=int(m[1]),lower_v=float(m[2]),upper_v=float(m[3]),status=int(m[4]))
        for m in re.finditer(r'R3THR,(\d+),([\d.eE+-]+),([\d.eE+-]+),(\d+)',log)]
    assert [t["k"] for t in thresholds]==list(range(ctx["first_k"],ctx["last_k"]+1))
    searches=[(int(m[1]),int(m[2]),int(m[3]),float(m[4]),int(m[5]))
        for m in re.finditer(r'R3SEARCH,(\d+),(\d+),(\d+),([\d.eE+-]+),(\d+)',log)]
    assert len(searches)==(ctx["last_k"]-ctx["first_k"]+1)*(2+ctx["refine"])
    for f,k,phase,voltage,code in searches:
        assert code==row["frame_monitor"][f]["code"]
        target=(98+100*f)*1e-9;j=int(np.argmin(abs(w["time"]-target)))
        actual=w["vinp_src"][j]-w["vinn_src"][j]
        assert abs(actual-voltage)<1e-10,(name,f,actual,voltage)
    row["thresholds"]=thresholds
    row["all_brackets_pass"]=all(t["status"]==0 for t in thresholds)
    for t in thresholds:
        assert 0<t["upper_v"]-t["lower_v"]<=ctx["threshold_bracket_width_lsb"]*LSB+1e-11
    dump(f"analysis/{name}.json",row)
    assert row["all_brackets_pass"],[(t["k"],t["status"]) for t in thresholds if t["status"]]
    print("STATIC_CASE",name,"brackets",len(thresholds),"PASS",flush=True)
    return row


def static_metrics(thresholds):
    k=np.arange(1,256);lo=np.asarray([t["lower_v"] for t in thresholds]);hi=np.asarray([t["upper_v"] for t in thresholds])
    assert [t["k"] for t in thresholds]==k.tolist() and np.all(hi[:-1]<lo[1:])
    mid=(lo+hi)/2;endpoint_lsb=(mid[-1]-mid[0])/254
    ideal=-.9+k*LSB
    dnl=np.diff(mid)/LSB-1;raw=(mid-ideal)/LSB
    ep=(mid-(mid[0]+(k-1)*endpoint_lsb))/endpoint_lsb
    return dict(transitions=255,threshold_indices=k.tolist(),thresholds_v=mid.tolist(),
        threshold_lower_v=lo.tolist(),threshold_upper_v=hi.tolist(),
        nominal_lsb_v=LSB,endpoint_lsb_v=float(endpoint_lsb),
        code_width_indices=list(range(1,255)),dnl_nominal_lsb=dnl.tolist(),
        dnl_endpoint_lsb=(np.diff(mid)/endpoint_lsb-1).tolist(),
        inl_raw_lsb=raw.tolist(),inl_endpoint_lsb=ep.tolist(),
        dnl_min_lsb=float(dnl.min()),dnl_max_lsb=float(dnl.max()),
        inl_raw_abs_max_lsb=float(abs(raw).max()),inl_endpoint_abs_max_lsb=float(abs(ep).max()),
        threshold_max_bracket_width_lsb=float(np.max(hi-lo)/LSB),
        dnl_lower_bound_lsb=((lo[1:]-hi[:-1])/LSB-1).tolist(),
        dnl_upper_bound_lsb=((hi[1:]-lo[:-1])/LSB-1).tolist(),
        offset_first_transition_mv=float((mid[0]-ideal[0])*1e3),
        endpoint_gain_error_percent=float((endpoint_lsb/LSB-1)*100),
        monotonic_at_measured_bounds=True,all256_codes_observed=True,
        saturated_endpoint_code_widths_excluded=[0,255])


def spectrum_metrics(codes,bin_number):
    x=-.9+(np.asarray(codes)+.5)*LSB;n=len(x)
    power=abs(np.fft.rfft(x-x.mean()))**2
    power[1:-1]*=2
    sig=power[bin_number];denom=power[1:].sum()-sig
    sndr=float(10*np.log10(sig/denom));others=power.copy();others[[0,bin_number]]=0
    from adctoolbox import analyze_spectrum
    toolbox=analyze_spectrum(x-x.mean(),fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
    assert abs(sndr-toolbox["sndr_dbc"])<1e-7
    return dict(samples=n,coherent_bin=bin_number,sndr_db=sndr,enob_sndr_bits=(sndr-1.76)/6.02,
        sfdr_db=float(10*np.log10(sig/others.max())),toolbox_metrics={k:float(v) for k,v in toolbox.items() if np.isscalar(v)},
        spectrum_frequency_hz=np.fft.rfftfreq(n,1/10e6).tolist(),
        spectrum_dbc=(10*np.log10(np.maximum(power/sig,1e-30))).tolist())


def dynamic_case(name):
    row,w,log=measurement(name);ctx=row["context"]
    t=w["time"];a=ctx["differential_amplitude_v"];freq=ctx["frequency_hz"]
    for side,sign in (("p",1),("n",-1)):
        assert np.max(abs(w[f"vin{side}_src"]-(.45+sign*a/2*np.sin(2*np.pi*freq*t))))<1e-8
    codes=[r["code"] for r in row["frame_monitor"]][ctx["warmup"]:]
    assert len(codes)==ctx["samples"]
    row.update(codes=codes,metrics=spectrum_metrics(codes,ctx["coherent_bin"]) if len(codes)>=32 else
        dict(scope="waveform/counting smoke only; too few points for performance"))
    dump(f"analysis/{name}.json",row)
    print("DYNAMIC",name,row["metrics"].get("sndr_db"),row["metrics"].get("enob_sndr_bits"),flush=True)
    return row


def pilot_check():
    import reference_alignment_analyze as timing
    prior=timing.load_wave(ROOT/"output/sar8_join_r3/runs/pfull_waveform.json")
    rows=[]
    for mt in (1,4):
        name=f"pilot_mt{mt}_s0";ctx,result,w,log,issues=read_case(name)
        times=np.array([90,95,98,190,195,198])*1e-9
        codes=sum((np.interp(times,w["time"],w[f"d{b}"])>.45).astype(int)*(1<<b) for b in range(8))
        assert codes.tolist()==[241]*len(times)
        delta=max(float(np.max(abs(np.interp(times,w["time"],w[node])-np.interp(times,prior["time"],prior[node])))) for node in ("topp","topn"))
        assert delta<1e-5
        row=dict(name=name,codes=codes.tolist(),settled_top_delta_v=delta,issues=issues,timings=result["metadata"]["timings"])
        rows.append(row)
    dump("analysis/pilot_check.json",rows)
    return rows


def full():
    static=[static_case(f"static_{lo:03d}_{hi:03d}") for lo,hi in ((1,64),(65,128),(129,192),(193,255))]
    thresholds=[t for r in static for t in r["thresholds"]]
    sm=static_metrics(thresholds);dy=dynamic_case("sine_1024_k461")
    import importlib.metadata
    import adctoolbox
    allcases=static+[dy]
    numerical=[r["name"] for r in allcases if r["issues"]["LTE_or_suppressed"]]
    cmi=[r["name"] for r in allcases if r["issues"]["CMI_count"]]
    result=dict(status="complete_with_warnings" if numerical or cmi else "complete",
        numerical_quality_pass=not numerical,numerical_warning_cases=numerical,CMI_warning_cases=cmi,
        scope="R3 native TT/.9V/27C no transient noise or mismatch",
        parent_R3_manifest_sha256=r3.r1.sha(ROOT/"verification/integration/join_r3_results.json"),
        static=sm,dynamic=dy,static_cases=static,
        adctoolbox=dict(version=importlib.metadata.version("adctoolbox"),module_path=adctoolbox.__file__))
    dump("summary.json",result)
    figures(result)
    sndr=dy["metrics"]["sndr_db"];enob=dy["metrics"]["enob_sndr_bits"]
    caution=(f"Numerical warning cases: {numerical}; CMI warning cases: {cmi}. "
             "Results with LTE relaxation are provisional diagnostics, not numerical signoff.\n\n") if numerical or cmi else ""
    report=(f"# R3 nominal static and dynamic results\n\nNo transient noise or mismatch.\n\n"+caution+
        f"DNL nominal: {sm['dnl_min_lsb']:.6f} to {sm['dnl_max_lsb']:.6f} LSB.\n\n"
        f"INL endpoint max: {sm['inl_endpoint_abs_max_lsb']:.6f} LSB; raw max: {sm['inl_raw_abs_max_lsb']:.6f} LSB.\n\n"
        f"SNDR: {sndr:.4f} dB; ENOB from measured SNDR: {enob:.4f} bits.\n\n"
        "1024-point coherent near-Nyquist sine, -1dBFS; endpoint code widths excluded from DNL.\n\n"
        "Full provenance, code/threshold records and warnings are in summary.json.\n")
    (OUT/"report.md").write_text(report,encoding="utf-8")


def figures(result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dest=OUT/"figures";dest.mkdir(parents=True,exist_ok=True)
    s=result["static"];d=result["dynamic"]["metrics"]
    fig,axes=plt.subplots(2,1,figsize=(10,6))
    axes[0].plot(s["code_width_indices"],s["dnl_nominal_lsb"],label="DNL, nominal LSB")
    axes[1].plot(s["threshold_indices"],s["inl_raw_lsb"],label="Raw transition INL")
    axes[1].plot(s["threshold_indices"],s["inl_endpoint_lsb"],label="Endpoint INL")
    for ax,label in zip(axes,("DNL (LSB)","INL (LSB)")):
        ax.axhline(0,color=".5",lw=.8);ax.set_ylabel(label);ax.set_xlabel("Code / transition index");ax.grid(alpha=.2);ax.legend()
    fig.tight_layout();fig.savefig(dest/"static.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4))
    ax.plot(np.asarray(d["spectrum_frequency_hz"])/1e6,d["spectrum_dbc"])
    ax.set_ylim(-120,3);ax.set_xlabel("Frequency (MHz)");ax.set_ylabel("Power (dBc)");ax.grid(alpha=.2)
    ax.set_title(f"R3 noiseless nominal: SNDR {d['sndr_db']:.2f} dB, ENOB {d['enob_sndr_bits']:.3f} bits")
    fig.tight_layout();fig.savefig(dest/"spectrum.png",dpi=160);plt.close(fig)


def setup_record():
    import hashlib
    paths=[ROOT/"config/sar8_r3_performance.yaml",ROOT/"verification/integration/test_r3_performance.py"]+[
        ROOT/f"scripts/integration/{s}.py" for s in ("r3_performance","r3_performance_analyze","r3_performance_flow")]+[
        ROOT/f"models/veriloga/r3_performance/{s}.va" for s in ("r3_perf_monitor","r3_transition_stim")]
    cases=[r3.r1.read_json(OUT/f"analysis/{s}.json") for s in
           ("static_128_129_smoke_v3","sine_4_k1_smoke_v3")]
    m=dict(status="in_progress_no_full_performance_metrics",remote_OA_changed=False,
        R3_preflight=r3.r1.read_json(OUT/"preflight.json"),
        exact_export_audit=r3.r1.read_json(OUT/"exports/primary/audit.json"),
        source_text_LF_sha256={str(p.relative_to(ROOT)).replace("\\","/"):
            hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() for p in paths},
        pilot=r3.r1.read_json(OUT/"analysis/pilot_check.json"),functional_smoke=cases,
        full_cases={s:r3.r1.read_json(OUT/f"cases/{s}.json") for s in
            ("sine_1024_k461","static_001_064","static_065_128","static_129_192","static_193_255")},
        generated_status_path="output/sar8_r3_performance/flow_status.json",
        generated_report_path="output/sar8_r3_performance/report.md")
    # Window inventory is private operational context, retained only in output/.
    m["R3_preflight"].pop("windows",None)
    p=ROOT/"verification/integration/r3_performance_setup.json"
    p.write_text(json.dumps(m,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["pilot","smoke","full","setup-record"]);a=p.parse_args()
    if a.action=="pilot":pilot_check()
    elif a.action=="smoke":
        static_case("static_128_129_smoke_v3")
        dynamic_case("sine_4_k1_smoke_v3")
    elif a.action=="setup-record":setup_record()
    else:full()
