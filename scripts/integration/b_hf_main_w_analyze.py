"""Frequency-aware analog held-error diagnostics, not a full-ADC ENOB test."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import re
import shutil

import numpy as np

import b_hf_main_w as run
import b_sine_decompose as oldmath
from r3_anomaly_analyze import edges,monitor,reported_parameters

ROOT,OUT = run.ROOT,run.OUT
Q = 1.8/256
stats = oldmath.stats


class SineModel:
    def __init__(self,hz):
        self.hz = hz
        self.omega = 2*np.pi*hz*1e-9

    def basis(self,ns,order=1):
        theta = (np.asarray(ns)-400)*self.omega
        return np.column_stack([np.ones_like(theta)]+
            [fn(k*theta) for k in range(1,order+1) for fn in (np.sin,np.cos)])

    def fit(self,ns,values):
        matrix = self.basis(ns)
        c,_,rank,_ = np.linalg.lstsq(matrix,values,rcond=None)
        assert rank == 3
        fitted = matrix@c
        remaining = np.asarray(values)-fitted
        assert np.max(abs(matrix.T@remaining)) < 1e-10
        return c,fitted,remaining,dict(dc_v=float(c[0]),sin_v=float(c[1]),cos_v=float(c[2]),
            amplitude_v=float(np.hypot(*c[1:])),phase_rad=float(np.arctan2(c[2],c[1])),
            residual=stats(remaining),design_condition=float(np.linalg.cond(matrix)))

    def transfer(self,output,source):
        phase = output["phase_rad"]-source["phase_rad"]
        phase = np.arctan2(np.sin(phase),np.cos(phase))
        gain = output["amplitude_v"]/source["amplitude_v"]
        return dict(gain=float(gain),gain_error_percent=float((gain-1)*100),
            gain_error_ppm=float((gain-1)*1e6),equivalent_lag_ns=float(-phase/self.omega),
            phase_degrees=float(phase*180/np.pi),
            offset_uv=float((output["dc_v"]-gain*source["dc_v"])*1e6))


def self_check():
    ns = 441.05+100*np.arange(20)
    for hz in (500000,4500000):
        m = SineModel(hz)
        source = .8*np.sin((ns-400)*m.omega)
        nonlinear = 13e-6*np.sin(3*(ns-400)*m.omega)+9e-6*np.cos(2*(ns-400)*m.omega)
        value = 123e-6+.9997*.8*np.sin((ns-400-1.73)*m.omega)+nonlinear
        _,_,_,si = m.fit(ns,source)
        _,_,res,hi = m.fit(ns,value)
        tr = m.transfer(hi,si)
        assert abs(tr["gain"]-.9997)<1e-12 and abs(tr["equivalent_lag_ns"]-1.73)<1e-8
        assert abs(tr["offset_uv"]-123)<1e-6 and np.max(abs(res-nonlinear))<1e-12
    prior = run.read(ROOT/"verification/integration/b_sine_main_w_results.json")
    for case in prior["cases"]:
        ns = np.array([f["sample_ns"] for f in case["frames"]])
        source = np.array([f["source_v"] for f in case["frames"]])
        held = np.array([f["held_v"] for f in case["frames"]])
        m = SineModel(500000)
        _,_,_,si = m.fit(ns,source);_,_,res,hi = m.fit(ns,held)
        tr = m.transfer(hi,si)
        for key in ("gain","equivalent_lag_ns","offset_uv"):
            assert abs(tr[key]-case["held_transfer"][key])<1e-9
        assert abs(stats(res)["peak_abs_uv"]-case["held_remainder"]["peak_abs_uv"])<1e-6
    print("HF_FREQUENCY_AWARE_SYNTHETIC_AND_500KHZ_EQUIVALENCE_PASS",flush=True)


def extract(w):
    ctx = run.read(OUT/"context.json");cfg = ctx["config"]
    case = OUT/f"w{w}"
    result = run.read(case/"result.json");receipt = run.read(case/"waveform_receipt.json")
    assert result["ok"] and run.sha(case/"waveform.pickle")==receipt["sha256"]
    with (case/"waveform.pickle").open("rb") as f:
        wave = {k:np.asarray(v) for k,v in pickle.load(f).items()}
    t = wave["time"]*1e9
    assert len(wave)==45 and np.all(np.diff(t)>0) and t[0]==0 and abs(t[-1]-2400)<1e-6
    at = lambda name,ns: np.interp(ns,t,wave[name])
    diff = lambda p,n,ns: at(p,ns)-at(n,ns)
    samples = edges(t,.9-wave["sample"])
    assert len(samples)==24 and np.max(abs(samples-(41.05+100*np.arange(24))))<1e-5
    ns = samples[4:]
    source_all = diff("vinp_src","vinn_src",samples)
    held_all = diff("topp","topn",samples+.6)
    source,held = source_all[4:],held_all[4:]
    expected = ctx["input_differential_peak_v"]*np.sin(2*np.pi*cfg["input_frequency_hz"]*samples*1e-9+
                                                    np.deg2rad(cfg["source_phase_degrees"][0]))
    assert np.max(abs(source_all-expected))<1e-7
    assert np.max(abs(at("vinp_src",samples)+at("vinn_src",samples)-.9))<1e-7
    log_path = case/"spectre/spectre.out"
    log = log_path.read_text(errors="replace")
    records = monitor(log)
    assert len(records)==24 and [r["frame"] for r in records]==list(range(24))
    probes = re.findall(r"BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)",log)
    assert len(probes)==24
    for i,row in enumerate(probes):
        assert int(row[0])==i
        assert max(abs(a-float(b)) for a,b in zip((source_all[i],held_all[i],held_all[i]-source_all[i]),row[1:]))<1e-7
    params = reported_parameters(log)
    baseline = run.read(ROOT/"verification/integration/b_sine_period_results.json")["reported_solver_parameters"]
    changes = {k:dict(baseline=v,current=params.get(k)) for k,v in baseline.items() if params.get(k)!=v}
    assert not changes,changes
    counts = {}
    for name in ("cmp_clk","xdut.xctrl.phi_w","xdut.xctrl.phi_u"):
        times = edges(t,wave[name])
        counts[name] = [int(np.count_nonzero((times>=100*f)&(times<100*(f+1)))) for f in range(24)]
    model = SineModel(cfg["input_frequency_hz"])
    sc,sf,sr,si = model.fit(ns,source)
    _,_,remaining,hi = model.fit(ns,held)
    tr = model.transfer(hi,si)
    delayed = model.basis(ns-tr["equivalent_lag_ns"])@sc
    phase = delayed-sf
    gain = (tr["gain"]-1)*delayed
    dc = tr["offset_uv"]*1e-6
    assert np.max(abs(phase+gain+dc+remaining-sr-(held-source)))<1e-12
    phase_only = held-delayed

    def prediction(window=5.,degree=3,signal=None):
        rel = np.arange(-window,-.15+.0025,.01)
        assert np.max(abs(at("sample",ns[:,None]+rel)-.9))<1e-9
        matrix = np.polynomial.polynomial.polyvander(rel/window,degree)
        value = diff("topp","topn",ns[:,None]+rel) if signal is None else at(signal,ns[:,None]+rel)
        return np.linalg.lstsq(matrix,value.T,rcond=None)[0][0]
    tracking = prediction()
    _,_,track_remaining,ti = model.fit(ns,tracking)
    off = held-tracking
    _,_,off_remaining,oi = model.fit(ns,off)
    assert np.max(abs(remaining-track_remaining-off_remaining))<1e-12
    sensitivity = [dict(window_ns=window,degree=degree,
        difference_peak_uv=float(np.max(abs(prediction(window,degree)-tracking))*1e6))
        for window in (3.,5.,8.) for degree in (2,3,4,5)]
    common = (at("topp",ns+.6)-prediction(signal="topp")+at("topn",ns+.6)-prediction(signal="topn"))/2
    main_peaks,comp_peaks = [],[]
    for side in "pn":
        g,vin,top = wave[f"xdut.xboot{side}.g"],wave[f"vin{side}"],wave[f"top{side}"]
        for name,val in (("VGS",g-vin),("VGD",g-top),("VDS",top-vin)):
            k = int(np.argmax(abs(val)))
            main_peaks.append(dict(side=side,terminal=name,max_abs_v=float(abs(val[k])),time_ns=float(t[k])))
        drain = wave["xdut.xcomp.y" if side=="p" else "xdut.xcomp.x"]
        tail = wave["xdut.xcomp.tail"]
        for name,val in (("VGS",top-tail),("VGD",top-drain),("VDS",drain-tail)):
            k = int(np.argmax(abs(val)))
            comp_peaks.append(dict(side=side,terminal=name,max_abs_v=float(abs(val[k])),time_ns=float(t[k])))
    rows = []
    for i,f in enumerate(range(4,24)):
        quant = lambda v:int(np.clip(np.floor((v+.9)/Q),0,255))
        code = records[f]["code"]
        rows.append(dict(frame=f,sample_ns=float(ns[i]),source_v=float(source[i]),held_v=float(held[i]),
            raw_error_uv=float((held[i]-source[i])*1e6),phase_only_error_uv=float(phase_only[i]*1e6),
            held_remainder_uv=float(remaining[i]*1e6),turnoff_increment_uv=float(off[i]*1e6),
            turnoff_remainder_uv=float(off_remaining[i]*1e6),tracking_remainder_uv=float(track_remaining[i]*1e6),
            turnoff_common_mode_uv=float(common[i]*1e6),output_code=code,
            code_error_vs_nominal=code-quant(source[i]),code_error_vs_held=code-quant(held[i])))
    warning_events = []
    for value,unit,message in re.findall(r"Warning from spectre at time = ([\d.eE+-]+) (\w+) [^\n]*\n\s*WARNING \(SPECTRE-16780\): ([^\n]+)",log):
        value_ns = float(value)*dict(s=1e9,ms=1e6,us=1e3,ns=1,ps=1e-3)[unit]
        f = int(value_ns//100)
        warning_events.append(dict(code="SPECTRE-16780",reported_time_ns=value_ns,frame=f,message=message,
            after_held_read_ns=float(value_ns-samples[f]-.6) if 0<=f<24 else None))
    summary = dict(width_multiplier=w,main_width_um=w,reused_native_run=False,native_result_ok=True,
        input_deck_sha256=ctx["cases"][str(w)]["deck_sha256"],waveform=receipt,
        native_log_sha256=run.sha(log_path),native_timings_s=result["metadata"].get("timings"),
        parse_seconds=result.get("parse_seconds"),complete_frames=24,event_counts=counts,
        all24_8compare_write_update=all(v==[8]*24 for v in counts.values()),
        all24_final_codes_stable=all(r["valid"] for r in records),solver_parameters=params,solver_parameter_differences=changes,
        held_transfer=tr,held_fit=hi,raw_held_error=stats(held-source),phase_only_error=stats(phase_only),
        held_remainder=stats(remaining),held_remainder_peak_lsb=float(np.max(abs(remaining))/Q),
        held_remainder_rms_lsb=float(np.sqrt(np.mean(remaining**2))/Q),tracking_transfer=model.transfer(ti,si),
        phase_only_peak_lsb=float(np.max(abs(phase_only))/Q),
        gain_term_at_fullscale_endpoint_lsb=128*abs(tr["gain"]-1),
        nonfund_rms_fraction_of_015LSB_budget=float(np.sqrt(np.mean(remaining**2))/(.15*Q)),
        tracking_remainder=stats(track_remaining),turnoff_increment=stats(off),turnoff_remainder=stats(off_remaining),
        turnoff_fit=oi,turnoff_common_mode_increment=stats(common),preedge_window_sensitivity=sensitivity,
        measured_held_within_original_budget=bool(np.all(abs(held-source)<Q*.25)),
        original_budget_exceedance_count=int(np.count_nonzero(abs(held-source)>=Q*.25)),
        max_code_error_vs_nominal=max(abs(f["code_error_vs_nominal"]) for f in rows),
        max_code_error_vs_held=max(abs(f["code_error_vs_held"]) for f in rows),
        main_terminal_peaks=main_peaks,comparator_input_pair_terminal_peaks=comp_peaks,
        comparator_input_pair_within_099V_screen=all(v["max_abs_v"]<=.99 for v in comp_peaks),
        has_CMI="CMI-2754" in log,has_LTE_relaxation="SPECTRE-16780" in log,numerical_warning_events=warning_events,
        warnings=[line.strip() for line in log.splitlines() if "WARNING (" in line],
        opposite_phase_held_sum_peak_uv=float(np.max(abs(held[:10]+held[10:]))*1e6),
        source_samples_v=source_all.tolist(),sample_times_ns=samples.tolist(),frames=rows)
    relative = np.arange(-.3,.8001,.002)
    e = ns[0]
    edge = dict(time_ns=relative.tolist(),
        gate_minus_input=((at("xdut.xbootp.g",e+relative)-at("vinp",e+relative)+
                           at("xdut.xbootn.g",e+relative)-at("vinn",e+relative))/2).tolist(),
        tracking_increment_uv=((diff("topp","topn",e+relative)-tracking[0])*1e6).tolist(),
        raw_error_mv=((diff("topp","topn",e+relative)-source[0])*1e3).tolist())
    # Bounded plot samples only; raw continuous waveform remains unchanged.
    view_t = np.arange(400.,1000.0001,.05)
    code_times = 100*np.arange(4,10)+98
    view = dict(time_ns=view_t.tolist(),input_v=diff("vinp_src","vinn_src",view_t).tolist(),
        sample_ns=ns[:6].tolist(),source_v=source[:6].tolist(),held_v=held[:6].tolist(),
        read_ns=code_times.tolist(),decoded_v=[-.9+(records[f]["code"]+.5)*Q for f in range(4,10)],
        ideal_decoded_v=[-.9+(int(np.clip(np.floor((s+.9)/Q),0,255))+.5)*Q for s in source[:6]])
    run.dump(case/"analysis.json",summary);run.dump(case/"edge.json",edge);run.dump(case/"view.json",view)
    print("EXTRACTED_HF",w,tr,stats(remaining),flush=True)
    return summary,edge,view


def plot(results,edge_data,views):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    target = OUT/"figures";target.mkdir(parents=True,exist_ok=True)
    fig,ax = plt.subplots(2,2,figsize=(11.5,7.5))
    x=[1,2,3]
    ax[0,0].plot(x,[r["held_transfer"]["equivalent_lag_ns"] for r in results],"o-")
    ax[0,0].set_ylabel("Equivalent lag (ns)")
    ax[0,1].plot(x,[r["held_transfer"]["gain_error_percent"] for r in results],"o-")
    ax[0,1].set_ylabel("Gain error (%)")
    for k,label in (("peak_abs_uv","Peak"),("rms_uv","RMS")):
        ax[1,0].plot(x,[r["held_remainder"][k]/(Q*1e6) for r in results],"o-",label=label)
    ax[1,0].set_ylabel("Nonfundamental remainder (LSB)");ax[1,0].legend()
    ax[1,1].plot(x,[r["raw_held_error"]["peak_abs_uv"]/1000 for r in results],"o-",label="Raw")
    ax[1,1].plot(x,[r["phase_only_error"]["peak_abs_uv"]/1000 for r in results],"s--",label="Phase aligned; gain retained")
    ax[1,1].axhline(Q*.25*1000,color="#777777",ls=":",label="Original raw budget")
    ax[1,1].set_ylabel("Error peak (mV)");ax[1,1].legend(fontsize=8)
    for a in ax.flat:
        a.set_xticks(x,["1x","2x","3x"]);a.set_xlabel("Main sampling width");a.grid(alpha=.22)
    fig.tight_layout();fig.savefig(target/"comparison.png",dpi=170);plt.close(fig)
    fig,ax = plt.subplots(3,1,figsize=(11.5,8),sharex=True)
    for r in results:
        tx=[(f["sample_ns"]-400)/1000 for f in r["frames"]]
        for a,key,scale in zip(ax,("raw_error_uv","phase_only_error_uv","held_remainder_uv"),(1000,1000,Q*1e6)):
            a.plot(tx,[f[key]/scale for f in r["frames"]],"o-",ms=3,label=f"{r['width_multiplier']}x")
    ax[0].axhspan(-Q*.25*1000,Q*.25*1000,color="#e1eee3",label="Original raw +/-0.25 LSB budget")
    ax[0].set_ylabel("Raw error (mV)");ax[1].set_ylabel("Phase aligned error (mV)")
    ax[2].set_ylabel("Nonfundamental remainder (LSB)");ax[2].set_xlabel("Nominal sample time from 400 ns (us)")
    for a in ax:
        a.axhline(0,color="#777777",lw=.8);a.grid(alpha=.22);a.legend(fontsize=8)
    fig.tight_layout();fig.savefig(target/"sample_errors.png",dpi=170);plt.close(fig)
    fig,ax = plt.subplots(3,1,figsize=(11.5,8),sharex=True)
    for r,v,a in zip(results,views,ax):
        a.plot(np.array(v["time_ns"])-400,v["input_v"],color="#888888",label="Continuous source")
        a.plot(np.array(v["sample_ns"])-400,v["source_v"],"kx",label="Ideal nominal samples")
        a.plot(np.array(v["sample_ns"])+.6-400,v["held_v"],"o",ms=4,label="Held read at SAMPLE fall +0.6 ns")
        a.step(np.array(v["read_ns"])-400,v["decoded_v"],where="post",label="Decoded code; read at frame +98 ns")
        a.step(np.array(v["read_ns"])-400,v["ideal_decoded_v"],where="post",color="#333333",ls="--",
               label="Ideal nominal code; same read times")
        a.set_ylabel(f"{r['width_multiplier']}x differential (V)");a.grid(alpha=.22)
    handles,labels=ax[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper center",ncol=2,fontsize=8)
    ax[-1].set_xlabel("Time from 400 ns (ns)")
    fig.tight_layout(rect=[0,0,1,.90]);fig.savefig(target/"short_waveforms.png",dpi=170);plt.close(fig)
    fig,ax = plt.subplots(3,1,figsize=(11.5,8),sharex=True)
    for r,e in zip(results,edge_data):
        for a,key in zip(ax,("gate_minus_input","tracking_increment_uv","raw_error_mv")):
            a.plot(e["time_ns"],e[key],label=f"{r['width_multiplier']}x")
    ax[0].set_ylabel("Mean gate - input (V)");ax[1].set_ylabel("From pre-edge prediction (uV)")
    ax[2].set_ylabel("From ideal sample (mV)");ax[2].set_xlabel("Time from SAMPLE 50% fall, frame 5 (ns)")
    for a in ax:
        a.axvspan(-.05,.05,color="#dddddd",alpha=.4);a.axvline(0,color="#777777",ls=":")
        a.axvline(.6,color="#777777",ls=":");a.grid(alpha=.22);a.legend(fontsize=8)
    ax[1].axhline(0,color="#777777",ls="--",label="Pre-edge prediction at sample")
    ax[2].axhline(0,color="#777777",ls="--",label="Ideal nominal sample")
    ax[2].axhspan(-Q*.25*1000,Q*.25*1000,color="#e1eee3",label="Original raw budget")
    ax[1].legend(fontsize=8);ax[2].legend(fontsize=8)
    ax[0].text(0,.98,"SAMPLE 50% fall",transform=ax[0].get_xaxis_transform(),ha="left",va="top",fontsize=8)
    ax[0].text(.6,.98,"Held read",transform=ax[0].get_xaxis_transform(),ha="left",va="top",fontsize=8)
    fig.tight_layout();fig.savefig(target/"turnoff_edges.png",dpi=170);plt.close(fig)


def analyze():
    run.check();self_check()
    results,edges_out,views = [],[],[]
    for w in (1,2,3):
        r,e,v = extract(w);results.append(r);edges_out.append(e);views.append(v)
    for r in results[1:]:
        assert np.max(abs(np.array(r["sample_times_ns"])-results[0]["sample_times_ns"]))<1e-5
        assert np.max(abs(np.array(r["source_samples_v"])-results[0]["source_samples_v"]))<1e-7
    plot(results,edges_out,views)
    low = run.read(ROOT/"verification/integration/b_sine_main_w_results.json")
    comparison = dict(config=run.read(OUT/"context.json")["config"],cases=results,
        input_differential_peak_v=run.read(OUT/"context.json")["input_differential_peak_v"],
        input_context_sha256=run.sha(OUT/"context.json"),all_native_runs_new=True,no_OA_adoption=True,
        qualified_full_ADC=False,selected_width=None,
        limits="20 samples/9 cycles, single TT amplitude; phase/gain separation is diagnostic, not a new raw acceptance gate or ENOB.",
        low_frequency_conditions=dict(input_frequency_hz=500000,input_differential_peak_v=.8,
            input_level_dbfs=float(20*np.log10(.8/.9)),
            result_sha256=run.sha(ROOT/"verification/integration/b_sine_main_w_results.json")),
        low_frequency_comparison=[dict(width_multiplier=c["width_multiplier"],held_transfer=c["held_transfer"],
            held_remainder=c["held_remainder"],raw_held_error=c["raw_held_error"]) for c in low["cases"]],
        analysis_source_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest(),
        runner_source_LF_sha256=hashlib.sha256(Path(run.__file__).read_text(encoding="utf-8").encode()).hexdigest(),
        figure_sha256={p.name:run.sha(p) for p in sorted((OUT/"figures").glob("*.png"))})
    run.dump(OUT/"comparison.json",comparison)


def curate(recommend_width=None):
    r = run.read(OUT/"comparison.json")
    run.check()
    assert run.read(OUT/"flow.json")["stage"]=="awaiting_visual_review"
    assert run.sha(OUT/"context.json")==r["input_context_sha256"]
    assert hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest()==r["analysis_source_LF_sha256"]
    target = ROOT/"docs/figures/b_hf_main_w";target.mkdir(parents=True,exist_ok=True)
    for name,digest in r["figure_sha256"].items():
        assert run.sha(OUT/"figures"/name)==digest
        shutil.copyfile(OUT/"figures"/name,target/name)
    r["figures_visually_reviewed_by_agent"] = True
    r["recommended_width_multiplier"] = recommend_width
    r["recommendation_is_not_OA_adoption_or_raw_budget_pass"] = True
    run.dump(ROOT/"verification/integration/b_hf_main_w_results.json",r)


if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("--self-check",action="store_true");p.add_argument("--curate",action="store_true")
    p.add_argument("--recommend-width",type=int,choices=[1,2,3])
    a=p.parse_args()
    self_check() if a.self_check else (curate(a.recommend_width) if a.curate else analyze())
