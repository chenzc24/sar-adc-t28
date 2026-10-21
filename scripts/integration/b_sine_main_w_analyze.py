"""Comparable extraction for the three main-width B native sine cases."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pickle
import re
import shutil

import numpy as np

import b_sine_main_w as run
import b_sine_decompose as mathref
from r3_anomaly_analyze import edges, monitor, reported_parameters

ROOT, OUT, BASE = run.ROOT, run.OUT, run.BASE


def extract(width):
    location = BASE if width == 1 else OUT/f"w{width}"
    result = run.read(location/"result.json")
    receipt = run.read(location/"waveform_receipt.json")
    assert result["ok"] and run.sha(location/"waveform.pickle") == receipt["sha256"]
    with (location/"waveform.pickle").open("rb") as stream:
        wave = {k:np.asarray(v) for k,v in pickle.load(stream).items()}
    t = wave["time"]*1e9
    assert len(wave) == 45 and np.all(np.diff(t) > 0)
    assert t[0] == 0 and abs(t[-1]-2400) < 1e-6
    at = lambda name, ns: np.interp(ns, t, wave[name])
    diff = lambda p,n,ns: at(p,ns)-at(n,ns)
    ns_all = edges(t, .9-wave["sample"])
    assert len(ns_all) == 24
    ns = ns_all[4:]
    source_all = diff("vinp_src", "vinn_src", ns_all)
    source = source_all[4:]
    held_all = diff("topp", "topn", ns_all+.6)
    held = held_all[4:]
    baseline = run.read(ROOT/"verification/integration/b_sine_period_results.json")
    assert np.max(abs(ns_all-np.array([r["sample_ns"] for r in baseline["frames"]]))) < 1e-5
    assert np.max(abs(source_all-np.array([r["source_v"] for r in baseline["frames"]]))) < 1e-7
    log_path = location/"spectre/spectre.out"
    log = log_path.read_text(errors="replace")
    records = monitor(log)
    assert len(records) == 24 and [r["frame"] for r in records] == list(range(24))
    probes = re.findall(r"BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)", log)
    assert len(probes) == 24
    for i, values in enumerate(probes):
        assert int(values[0]) == i
        assert max(abs(a-float(b)) for a,b in zip((source_all[i],held_all[i],held_all[i]-source_all[i]),values[1:])) < 1e-7
    counts = {}
    for name in ("cmp_clk", "xdut.xctrl.phi_w", "xdut.xctrl.phi_u"):
        e = edges(t, wave[name])
        counts[name] = [int(np.count_nonzero((e>=100*f)&(e<100*(f+1)))) for f in range(24)]
    parameters = reported_parameters(log)
    changes = {k:dict(baseline=v,current=parameters.get(k)) for k,v in baseline["reported_solver_parameters"].items()
               if parameters.get(k) != v}
    assert not changes, changes
    source_c, source_fitted, _, si = mathref.fit(ns, source)
    _, held_fitted, remaining, hi = mathref.fit(ns, held)
    transfer = mathref.transfer(hi, si)
    delayed = mathref.basis(ns-transfer["equivalent_lag_ns"]) @ source_c
    phase = delayed-source_fitted
    gain = (transfer["gain"]-1)*delayed
    offset = transfer["offset_uv"]*1e-6
    reconstructed = phase+gain+offset+remaining+(source_fitted-source)
    assert np.max(abs(reconstructed-(held-source))) < 1e-12

    def prediction(window=5., degree=3, step=.01, signal=None):
        relative = np.arange(-window, -.15+step*.25, step)
        assert np.max(abs(at("sample",ns[:,None]+relative)-.9)) < 1e-9
        matrix = np.polynomial.polynomial.polyvander(relative/window, degree)
        values = (diff("topp","topn",ns[:,None]+relative) if signal is None
                  else at(signal,ns[:,None]+relative))
        return np.linalg.lstsq(matrix,values.T,rcond=None)[0][0]
    tracking = prediction()
    _, _, tracking_remaining, ti = mathref.fit(ns,tracking)
    turnoff = held-tracking
    _, turnoff_fitted, turnoff_remaining, oi = mathref.fit(ns,turnoff)
    assert np.max(abs(remaining-tracking_remaining-turnoff_remaining)) < 1e-12
    sensitivity = []
    for window in (3.,5.,8.):
        for degree in (2,3):
            sensitivity.append(dict(window_ns=window,degree=degree,
                prediction_difference_peak_uv=float(np.max(abs(prediction(window,degree)-tracking))*1e6)))
    common_delta = (at("topp",ns+.6)-prediction(signal="topp")+
                    at("topn",ns+.6)-prediction(signal="topn"))/2
    pre_p = at("xdut.xbootp.g",ns-.15)-at("vinp",ns-.15)
    pre_n = at("xdut.xbootn.g",ns-.15)-at("vinn",ns-.15)
    main_stress = []
    comparator_stress = []
    for side in "pn":
        main_g,vin,top = wave[f"xdut.xboot{side}.g"],wave[f"vin{side}"],wave[f"top{side}"]
        for name,v in (("VGS",main_g-vin),("VGD",main_g-top),("VDS",top-vin)):
            index = int(np.argmax(abs(v)))
            main_stress.append(dict(side=side,terminal=name,max_abs_v=float(abs(v[index])),time_ns=float(t[index])))
        drain = "xdut.xcomp.y" if side == "p" else "xdut.xcomp.x"
        for name,v in (("VGS",top-wave["xdut.xcomp.tail"]),
                       ("VGD",top-wave[drain]),("VDS",wave[drain]-wave["xdut.xcomp.tail"])):
            index = int(np.argmax(abs(v)))
            comparator_stress.append(dict(side=side,terminal=name,max_abs_v=float(abs(v[index])),time_ns=float(t[index])))
    def gate_crossing(frame_ns,side,fraction):
        mask = (t>=frame_ns-.05)&(t<=frame_ns+.6)
        x,y = t[mask],wave[f"xdut.xboot{side}.g"][mask]
        threshold = float(at(f"xdut.xboot{side}.g",frame_ns-.15))*fraction
        crossings = np.flatnonzero((y[:-1]>=threshold)&(y[1:]<threshold))
        if not len(crossings):
            return None
        j = crossings[0]
        return float(x[j]+(threshold-y[j])*(x[j+1]-x[j])/(y[j+1]-y[j])-frame_ns)
    rows = []
    for i,f in enumerate(range(4,24)):
        code = records[f]["code"]
        ideal = int(np.clip(np.floor((source[i]+.9)/(1.8/256)),0,255))
        gate_times = {}
        for side in "pn":
            a,b,c = [gate_crossing(ns[i],side,v) for v in (.9,.5,.1)]
            gate_times[side] = dict(fall90_ns=a,fall50_ns=b,fall10_ns=c,
                                   fall90to10_ps=(c-a)*1000 if a is not None and c is not None else None)
        rows.append(dict(frame=f,sample_ns=float(ns[i]),source_v=float(source[i]),held_v=float(held[i]),
            raw_error_uv=float((held[i]-source[i])*1e6),held_remainder_uv=float(remaining[i]*1e6),
            tracking_remainder_uv=float(tracking_remaining[i]*1e6),turnoff_increment_uv=float(turnoff[i]*1e6),
            turnoff_remainder_uv=float(turnoff_remaining[i]*1e6),turnoff_common_mode_uv=float(common_delta[i]*1e6),
            pre_gate_minus_input_p_v=float(pre_p[i]),pre_gate_minus_input_n_v=float(pre_n[i]),
            output_code=code,ideal_code=ideal,code_error=code-ideal,gate_timing=gate_times))
    summary = dict(width_multiplier=width,main_width_um=width,reused_native_run=width == 1,
        native_result_ok=True,waveform=receipt,solver_parameters=parameters,solver_parameter_differences=changes,
        complete_frames=24,all24_8compare_write_update=all(v==[8]*24 for v in counts.values()),
        all24_final_codes_stable=all(r["valid"] for r in records),event_counts=counts,
        maximum_measured_code_error=max(abs(r["code_error"]) for r in rows),
        measured_gross_error_frames=[r["frame"] for r in rows if abs(r["code_error"])>1],
        held_transfer=transfer,held_fit=hi,tracking_transfer=mathref.transfer(ti,si),tracking_fit=ti,
        raw_held_error=mathref.stats(held-source),held_remainder=mathref.stats(remaining),
        turnoff_increment=mathref.stats(turnoff),turnoff_remainder=mathref.stats(turnoff_remaining),
        turnoff_fit=oi,turnoff_common_mode_increment=mathref.stats(common_delta),
        measured_held_within_original_budget=bool(np.all(abs(held-source)<1.7578125e-3)),
        original_budget_exceedance_count=int(np.count_nonzero(abs(held-source)>=1.7578125e-3)),
        preedge_window_sensitivity=sensitivity,main_terminal_peaks=main_stress,
        comparator_input_pair_terminal_peaks=comparator_stress,
        comparator_input_pair_within_099V_screen=all(r["max_abs_v"]<=.99 for r in comparator_stress),
        has_CMI="CMI-2754" in log,has_LTE_relaxation="SPECTRE-16780" in log,
        warnings=[line.strip() for line in log.splitlines() if "WARNING (" in line],
        native_log_sha256=run.sha(log_path),frames=rows)
    if width == 1:
        old = run.read(ROOT/"verification/integration/b_sine_decomposition_results.json")
        for key in ("gain","equivalent_lag_ns","offset_uv"):
            assert abs(summary["held_transfer"][key]-old["held_transfer"][key]) < 1e-9
        assert abs(summary["held_remainder"]["peak_abs_uv"]-old["decomposition"]["remaining"]["peak_abs_uv"])<1e-6
        assert abs(summary["turnoff_remainder"]["peak_abs_uv"]-old["turnoff_fit"]["residual"]["peak_abs_uv"])<1e-6
        summary["reproduces_committed_1x_decomposition"] = True
    # Same input phase: retain frame4 edge, not each variant's best frame.
    relative = np.arange(-.3,.80001,.002)
    edge_sample = ns[0]
    edge = dict(time_ns=relative.tolist(),sample=at("sample",edge_sample+relative).tolist(),
        mean_gate_minus_input=((at("xdut.xbootp.g",edge_sample+relative)-at("vinp",edge_sample+relative)+
                               at("xdut.xbootn.g",edge_sample+relative)-at("vinn",edge_sample+relative))/2).tolist(),
        top_minus_tracking_at_sample_uv=((diff("topp","topn",edge_sample+relative)-tracking[0])*1e6).tolist(),
        top_minus_sampled_source_mv=((diff("topp","topn",edge_sample+relative)-source[0])*1e3).tolist())
    run.dump(OUT/f"w{width}/analysis.json",summary)
    run.dump(OUT/f"w{width}/edge.json",edge)
    return summary,edge


def analyze(baseline_only=False):
    run.check()
    assert mathref.synthetic_check()
    results,edge_data = [],[]
    for width in ((1,) if baseline_only else (1,2,3)):
        r,e = extract(width)
        results.append(r);edge_data.append(e)
        print("EXTRACTED",width,r["held_transfer"],r["held_remainder"],flush=True)
    if baseline_only:
        return
    plot(results,edge_data)
    comparison = dict(config=run.read(OUT/"context.json")["config"],cases=results,
        sole_independent_change="Mmain W; consistent width-derived AD/AS/PD/PS",
        baseline_native_run_reused=True,no_OA_adoption=True,qualified_full_ADC=False,
        limits="Single frequency/amplitude/TT; corrected residual is not raw acceptance or pure charge injection.",
        runner_source_LF_sha256=mathref.hashlib.sha256(Path(run.__file__).read_text().encode()).hexdigest(),
        analysis_source_LF_sha256=mathref.hashlib.sha256(Path(__file__).read_text().encode()).hexdigest(),
        math_reference_source_LF_sha256=mathref.hashlib.sha256(Path(mathref.__file__).read_text().encode()).hexdigest(),
        figure_sha256={p.name:run.sha(p) for p in sorted((OUT/"figures").glob("*.png"))})
    run.dump(OUT/"comparison.json",comparison)


def plot(results,edge_data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    target = OUT/"figures"
    target.mkdir(parents=True,exist_ok=True)
    x = [1,2,3]
    fig,ax = plt.subplots(2,2,figsize=(11.5,7.5))
    ax[0,0].plot(x,[r["held_transfer"]["equivalent_lag_ns"] for r in results],"o-",label="Held")
    ax[0,0].plot(x,[r["tracking_transfer"]["equivalent_lag_ns"] for r in results],"s--",label="Pre-edge tracking")
    ax[0,0].set_ylabel("Equivalent lag (ns)")
    ax[0,1].plot(x,[r["held_transfer"]["gain_error_ppm"] for r in results],"o-",label="Held")
    ax[0,1].plot(x,[r["tracking_transfer"]["gain_error_ppm"] for r in results],"s--",label="Pre-edge tracking")
    ax[0,1].set_ylabel("Gain error (ppm)")
    for key,label in (("held_remainder","Held"),("tracking_fit","Pre-edge tracking"),("turnoff_remainder","Turnoff increment")):
        values=[r[key]["residual"]["peak_abs_uv"] if key=="tracking_fit" else r[key]["peak_abs_uv"] for r in results]
        ax[1,0].plot(x,values,"o-",label=label)
    ax[1,0].set_ylabel("Nonfundamental peak (uV)")
    for key,label in (("peak_abs_uv","Peak"),("rms_uv","RMS")):
        ax[1,1].plot(x,[r["turnoff_increment"][key] for r in results],"o-",label=label)
    ax[1,1].set_ylabel("Turnoff-related increment (uV)")
    for a in ax.flat:
        a.set_xticks(x,["1x","2x","3x"])
        a.set_xlabel("Main sampling width")
        a.grid(alpha=.22);a.legend(fontsize=9)
    fig.tight_layout();fig.savefig(target/"comparison.png",dpi=170);plt.close(fig)
    fig,ax = plt.subplots(2,1,figsize=(11.5,6.8),sharex=True)
    ax[0].axhspan(-1.7578125,1.7578125,color="#e1eee3",label="Original +/-0.25 LSB budget")
    for r in results:
        ns = [(f["sample_ns"]-400)/1000 for f in r["frames"]]
        ax[0].plot(ns,[f["raw_error_uv"]/1000 for f in r["frames"]],"o-",ms=3,label=f"{r['width_multiplier']}x")
        ax[1].plot(ns,[f["held_remainder_uv"] for f in r["frames"]],"o-",ms=3,label=f"{r['width_multiplier']}x")
    ax[0].set_ylabel("Raw held error (mV)");ax[1].set_ylabel("After DC/fundamental fit (uV)")
    ax[1].set_xlabel("Nominal sample time from observed-period start (us)")
    for a in ax:
        a.axhline(0,color="#777777",lw=.8);a.grid(alpha=.22);a.legend(fontsize=9)
    fig.tight_layout();fig.savefig(target/"period_errors.png",dpi=170);plt.close(fig)
    fig,ax = plt.subplots(3,1,figsize=(11.5,8.5),sharex=True)
    for r,e in zip(results,edge_data):
        label=f"{r['width_multiplier']}x"
        ax[0].plot(e["time_ns"],e["mean_gate_minus_input"],label=label)
        ax[1].plot(e["time_ns"],e["top_minus_tracking_at_sample_uv"],label=label)
        ax[2].plot(e["time_ns"],e["top_minus_sampled_source_mv"],label=label)
    ax[0].set_ylabel("Mean main gate - input (V)")
    ax[1].set_ylabel("CDAC - nominal tracking (uV)")
    ax[2].set_ylabel("CDAC - sampled source (mV)")
    ax[2].axhspan(-1.7578125,1.7578125,color="#e1eee3",label="Original budget")
    ax[2].set_xlabel("Time from SAMPLE 50% fall, frame 5 (ns)")
    for a in ax:
        a.axvspan(-.05,.05,color="#dddddd",alpha=.4);a.axvline(0,color="#777777",ls=":")
        a.axvline(.6,color="#777777",ls=":");a.grid(alpha=.22);a.legend(fontsize=9)
    fig.tight_layout();fig.savefig(target/"turnoff_edges.png",dpi=170);plt.close(fig)


def curate():
    result=run.read(OUT/"comparison.json")
    assert run.read(OUT/"flow.json")["stage"] == "awaiting_visual_review"
    target=ROOT/"docs/figures/b_sine_main_w"
    target.mkdir(parents=True,exist_ok=True)
    for name,digest in result["figure_sha256"].items():
        assert run.sha(OUT/"figures"/name)==digest
        shutil.copyfile(OUT/"figures"/name,target/name)
    result["figures_visually_reviewed_by_agent"]=True
    run.dump(ROOT/"verification/integration/b_sine_main_w_results.json",result)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline-only",action="store_true")
    parser.add_argument("--curate",action="store_true")
    args=parser.parse_args()
    curate() if args.curate else analyze(args.baseline_only)
