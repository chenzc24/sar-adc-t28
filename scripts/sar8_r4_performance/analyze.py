"""Read actual output words and continuous-event observations; calculate ADC metrics."""
import argparse
import json
import re
from pathlib import Path
import numpy as np
from common import OUT, ROOT, LSB, read, dump, sha


def records(log, prefix):
    return [[s.strip() for s in m[1].split(",")] for m in re.finditer(re.escape(prefix)+r",([^\r\n]+)", log)]


def load(name):
    folder=OUT/"cases"/name
    ctx=read(folder/"context.json")
    result_path=folder/"recovered_result.json" if (folder/"recovered_result.json").exists() else folder/"result.json"
    result=read(result_path)
    assert result["ok"], (name,result["errors"])
    assert sha(folder/(name+".scs"))==ctx["deck_sha256"]==result["deck_sha256"]
    assert sha(folder/"wave.npz")==read(folder/"wave_receipt.json")["sha256"]
    w=dict(np.load(folder/"wave.npz"))
    logpath=Path(result["metadata"]["output_dir"]).parent/"spectre.out"
    log=logpath.read_text(encoding="utf-8",errors="replace")
    rows=[]
    fields=["frame","code","compares","writes","updates","captures","early_code","valid",
            "rail_error_v","aperture_time_s","aperture_source_v","held_diff_v","final_top_diff_v","conversion_s"]
    for values in records(log,"R4MEAS"):
        assert len(values)==len(fields),(name,values)
        rows.append(dict(zip(fields,[int(v) if i<8 else float(v) for i,v in enumerate(values)])))
    assert [r["frame"] for r in rows]==list(range(ctx["frames"])), (name,len(rows),ctx["frames"])
    targets=(98+100*np.arange(ctx["frames"]))*1e-9
    idx=np.searchsorted(w["time"],targets).clip(0,len(w["time"])-1)
    prev=np.maximum(idx-1,0)
    idx=np.where(abs(w["time"][prev]-targets)<abs(w["time"][idx]-targets),prev,idx)
    assert np.max(abs(w["time"][idx]-targets))<1e-13
    decoded=sum((w[f"d{b}"][idx]>.45).astype(int)*(1<<b) for b in range(8))
    assert decoded.tolist()==[r["code"] for r in rows]
    assert w["time"][-1]>=ctx["stop_ns"]*1e-9-1e-14
    measured=rows[ctx["warmup"]:] if ctx["kind"]!="pilot" else rows
    bad=[r["frame"] for r in measured if not r["valid"] or r["conversion_s"]>=60e-9]
    warning_codes=sorted(set(re.findall(r"WARNING \(([^)]+)\)",log)))
    numeric_lines=[s.strip() for s in log.splitlines() if re.search(r"LTE.*(?:relax|fail)|convergence failure|relax.*LTE",s,re.I)]
    dc_lines=[s.strip() for s in log.splitlines() if re.search(r"Tolerance relaxation.*DC solution|GminDC|Bad pivoting|homotopy",s,re.I)]
    soa=[];warning_time=None
    for line in log.splitlines():
        m=re.search(r"Warning from spectre at time = (.+?) during",line)
        if m:warning_time=m[1]
        if re.search(r"WARNING \(CMI-\d+\)",line):soa.append(dict(time=warning_time,message=line.strip()))
    settings={}
    for key in ("maxstep","reltol","abstol(V)","abstol(I)","method","errpreset","lteratio","relref"):
        m=re.findall(r"(?m)^\s*"+re.escape(key)+r" = (.+)$",log)
        settings[key]=m[-1].strip() if m else None
    report=dict(name=name,context=ctx,frames=rows,invalid_frames=bad,frame_integrity_pass=not bad,
        warnings=warning_codes,numerical_diagnostics=numeric_lines,initial_DC_diagnostics=dc_lines,SOA_warning_examples=soa,
        CMI=any(s.startswith("CMI-") for s in warning_codes),effective_settings=settings,
        timing=result.get("metadata",{}).get("timings"),elapsed_wall_s=result["elapsed_wall_s"],
        simulator_lines=[s.strip() for s in log.splitlines() if "Version " in s or "spectre completes with" in s or "preset=" in s][:12],
        recovery=result.get("recovery"),result_sha256=sha(result_path),wave_sha256=sha(folder/"wave.npz"),log_sha256=sha(logpath))
    if ctx["kind"]=="static":
        thresholds=[dict(k=int(a),lower_v=float(b),upper_v=float(c),status=int(d)) for a,b,c,d in records(log,"R4THR")]
        assert [t["k"] for t in thresholds]==list(range(ctx["first"],ctx["last"]+1))
        centers=[dict(expected=int(a),input_v=float(b),code=int(c)) for a,b,c in records(log,"R4CENTER")]
        assert [c["expected"] for c in centers]==list(range(ctx["first"]-1,ctx["last"]+1))
        searches=[]
        for a,b,c,d,e in records(log,"R4SEARCH"):
            f=int(a);vin=float(d);code=int(e)
            assert code==rows[f]["code"]
            actual=w["vinp_src"][idx[f]]-w["vinn_src"][idx[f]]
            assert abs(actual-vin)<1e-10,(name,f,actual,vin)
            searches.append(dict(frame=f,k=int(b),phase=int(c),input_v=vin,code=code))
        assert len(searches)==(ctx["last"]-ctx["first"]+1)*(3+ctx["refine"])+1
        report.update(thresholds=thresholds,centers=centers,searches=searches,
            all_brackets_pass=all(t["status"]==0 for t in thresholds))
    elif ctx["kind"]=="sine":
        freq=ctx["frequency_hz"];amp=.9*10**(-1/20)
        for side,sign in (("p",1),("n",-1)):
            assert np.max(abs(w[f"vin{side}_src"]-(.45+sign*amp/2*np.sin(2*np.pi*freq*w["time"]))))<1e-8
        codes=[r["code"] for r in measured]
        assert len(codes)==ctx["samples"]
        report["codes"]=codes
        if len(codes)>=32:report["metrics"]=spectrum(codes,ctx["coherent_bin"])
    dump(folder/"analysis.json",report)
    return report,w


def static_metrics(thresholds, observed_codes):
    assert [r["k"] for r in thresholds]==list(range(1,256))
    lo=np.array([r["lower_v"] for r in thresholds]);hi=np.array([r["upper_v"] for r in thresholds])
    mid=(lo+hi)/2;k=np.arange(1,256);ideal=-.9+k*LSB
    ep_lsb=(mid[-1]-mid[0])/254
    dnl=np.diff(mid)/LSB-1
    raw=(mid-ideal)/LSB;ep=(mid-(mid[0]+(k-1)*ep_lsb))/ep_lsb
    return dict(thresholds_v=mid.tolist(),threshold_lower_v=lo.tolist(),threshold_upper_v=hi.tolist(),
        threshold_max_bracket_width_lsb=float(np.max(hi-lo)/LSB),
        dnl_nominal_lsb=dnl.tolist(),dnl_endpoint_lsb=(np.diff(mid)/ep_lsb-1).tolist(),
        dnl_min_lsb=float(dnl.min()),dnl_max_lsb=float(dnl.max()),
        dnl_lower_bound_lsb=((lo[1:]-hi[:-1])/LSB-1).tolist(),dnl_upper_bound_lsb=((hi[1:]-lo[:-1])/LSB-1).tolist(),
        inl_raw_lsb=raw.tolist(),inl_endpoint_lsb=ep.tolist(),
        inl_raw_abs_max_lsb=float(abs(raw).max()),inl_endpoint_abs_max_lsb=float(abs(ep).max()),
        offset_first_transition_mv=float((mid[0]-ideal[0])*1e3),endpoint_gain_error_percent=float((ep_lsb/LSB-1)*100),
        ordered_disjoint_brackets=bool(np.all(hi[:-1]<lo[1:])),
        all_brackets_pass=all(r["status"]==0 for r in thresholds),
        observed_codes=sorted(set(observed_codes)),unobserved_codes=sorted(set(range(256))-set(observed_codes)),
        saturated_endpoint_code_widths_excluded=[0,255])


def spectrum(codes,bin_number,toolbox=True):
    x=-.9+(np.asarray(codes)+.5)*LSB;n=len(x)
    power=abs(np.fft.rfft(x-x.mean()))**2
    power[1:-1]*=2
    sig=power[bin_number];other=power.copy();other[[0,bin_number]]=0
    sndr=float(10*np.log10(sig/other.sum()));sfdr=float(10*np.log10(sig/other.max()))
    result=dict(samples=n,coherent_bin=bin_number,frequency_hz=10e6*bin_number/n,
        sndr_db=sndr,enob_sndr_bits=(sndr-1.76)/6.02,sfdr_db=sfdr,
        frequency_axis_hz=np.fft.rfftfreq(n,1/10e6).tolist(),spectrum_dbc=(10*np.log10(np.maximum(power/sig,1e-30))).tolist())
    if toolbox:
        import importlib.metadata
        import adctoolbox
        tb=adctoolbox.analyze_spectrum(x-x.mean(),fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
        assert abs(sndr-tb["sndr_dbc"])<1e-7,(sndr,tb)
        result["adctoolbox"]=dict(version=importlib.metadata.version("adctoolbox"),module=adctoolbox.__file__,
            sndr_dbc=float(tb["sndr_dbc"]),direct_fft_delta_db=sndr-float(tb["sndr_dbc"]))
    return result


def pilots(names):
    reports=[load(n)[0] for n in names]
    reference=reports[0]
    comparisons=[]
    for r in reports:
        codes=[f["code"] for f in r["frames"]]
        comparisons.append(dict(name=r["name"],codes=codes,expected_codes=[145,14,241,14],
            output_codes_match=codes==[145,14,241,14],frame_integrity_pass=r["frame_integrity_pass"],
            max_held_delta_v=max(abs(a["held_diff_v"]-b["held_diff_v"]) for a,b in zip(reference["frames"],r["frames"])),
            max_final_residual_delta_v=max(abs(a["final_top_diff_v"]-b["final_top_diff_v"]) for a,b in zip(reference["frames"],r["frames"])),
            elapsed_wall_s=r["elapsed_wall_s"],timing=r["timing"],effective_settings=r["effective_settings"],
            warnings=r["warnings"],numerical_diagnostics=r["numerical_diagnostics"]))
    dump(OUT/"pilot_comparison.json",comparisons)
    print(json.dumps(comparisons,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["case","pilots"]);p.add_argument("names",nargs="+");a=p.parse_args()
    if a.action=="pilots":pilots(a.names)
    else:
        for n in a.names:
            report,_=load(n)
            print(json.dumps({k:v for k,v in report.items() if k in ("name","invalid_frames","all_brackets_pass","effective_settings","metrics","warnings")},indent=2))
