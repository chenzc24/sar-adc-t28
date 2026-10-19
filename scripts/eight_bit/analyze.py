"""Evidence gates for eight-bit flat behavioral, VA, macro and native sampling."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys

import numpy as np

from common import ROOT, OUT, LSB, LIMIT, CU, load, dump, config
sys.path.insert(0,str(ROOT))
from models.behavioral.sar_adc import SarAdcModel
from adctoolbox import analyze_spectrum


def waves(category,stem):
    row=load(f"{category}/{stem}_result.json")
    assert row["ok"],row["errors"]
    # Spectre may include scalar device/model metadata beside signal vectors.
    wave={k:np.asarray(v,dtype=float) for k,v in load(f"{category}/{stem}_waveform.json").items() if isinstance(v,list)}
    t=wave["time"]
    assert len(t)>1 and np.isfinite(t).all() and (np.diff(t)>0).all()
    assert all(len(a)==len(t) and np.isfinite(a).all() for a in wave.values())
    return row,wave


def spectrum(codes):
    x=-.9+np.asarray(codes)*LSB
    m=analyze_spectrum(x-x.mean(),fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
    return {"sndr_db":float(m["sndr_dbc"]),"enob_bits":float(m["enob"]),"sfdr_db":float(m["sfdr_dbc"])}


def va_analysis():
    out={}
    for case in ("timing","static","dynamic","allocated_noise"):
        _,w=waves("veriloga","va8_"+case)
        code=sum((w[f"dout_{b}"]>.45).astype(int)*(1<<b) for b in range(8))
        if case!="timing":
            count=2048 if case=="static" else 16384
            desired=90e-9+np.arange(count)*100e-9
            indices=np.searchsorted(w["time"],desired)
            indices=np.minimum(indices,len(w["time"])-1)
            previous=np.maximum(indices-1,0)
            indices=np.where(abs(w["time"][previous]-desired)<abs(w["time"][indices]-desired),previous,indices)
            assert np.max(abs(w["time"][indices]-desired))<1e-12
            assert (w["valid"][indices]>.45).all() and (w["busy"][indices]<.45).all()
            code=code[indices]
        if case=="timing":
            valid=np.flatnonzero((w["valid"][:-1]<=.45)&(w["valid"][1:]>.45))+1
            sample=np.searchsorted(w["time"],w["time"][valid]+.1e-9)
            assert code[sample].tolist()==[192,64],code[sample]
            rises=np.flatnonzero((w["busy"][:-1]<=.45)&(w["busy"][1:]>.45))+1
            falls=np.flatnonzero((w["busy"][:-1]>.45)&(w["busy"][1:]<=.45))+1
            delay=(w["time"][falls]-w["time"][rises])*1e9
            assert len(delay)==2 and (delay<60).all()
            out[case]={"codes":code[sample].tolist(),"conversion_ns":delay.tolist()}
        elif case=="static":
            expected=np.repeat(np.arange(256),8)
            assert np.array_equal(code,expected),(len(code),code[:20])
            hist=np.bincount(code,minlength=256)
            out[case]={"samples":len(code),"codes":256,"missing_codes":int((hist==0).sum()),"dnl_abs_max_lsb":float(abs(hist/8-1).max())}
        else:
            assert len(code)==16384,len(code)
            sample_time=40.01e-9+np.arange(16384)*100e-9
            vin=.9*10**(-1/20)*np.sin(2*np.pi*(10e6*7373/16384)*sample_time)
            model=SarAdcModel(8,(-.9,.9))
            expected=model.unsigned_codes(model.convert(vin))
            if case=="dynamic":assert np.array_equal(code,expected),np.flatnonzero(code!=expected)[:8]
            metrics=spectrum(code)
            assert metrics["enob_bits"]>=7 and metrics["sndr_db"]>=43.9,metrics
            if case=="allocated_noise":
                assert np.count_nonzero(code!=expected)>0
                partial=math.sqrt((LSB/math.sqrt(12))**2+2*(.18*LSB)**2+(.12*LSB)**2)
                prediction=20*math.log10((.9*10**(-1/20)/math.sqrt(2))/partial)
                assert abs(metrics["sndr_db"]-prediction)<1,metrics
                metrics.update(partial_rss_sndr_db=prediction,changed_codes=int(np.count_nonzero(code!=expected)))
            out[case]={"samples":len(code),**metrics}
    dump("veriloga/summary.json",out)
    return out


def first_order():
    cfg=config(); c=256*CU; k=1.380649e-23; temperature=300.15
    sigma=math.sqrt(2*k*temperature/c)
    envelope={str(t):t*1e-9/(c*math.log(1.8/LIMIT)) for t in (2,3,4)}
    budget=load("behavioral/summary.json")["error_budget"]
    total=cfg["reference"]["resistance_ohm"]+cfg["cdac"]["bottom_ron_ohm"]
    row={"cside_pf":c*1e12,"sigma_ktc_diff_mv":sigma*1e3,"ron_plus_rref_limit_ohm":envelope,
         "allocated_ron_plus_rref_ohm":total,"first_order_residual_3ns_mv":1.8*math.exp(-3e-9/(total*c))*1e3,
         "sampling_budget_mv":budget["sampling_noise_rms_v"]*1e3,
         "comparator_gm_min_us":20e-15/1.5e-9*math.log(.45/LIMIT)*1e6,
         "jitter_absolute_mv":budget["clock_jitter_error_rms_v"]*1e3,
         "acquisition_resistance_limit_ohm":40e-9/(c*math.log(1.8/LIMIT)),
         "scope":"linear allocation only, not transistor characterization"}
    assert sigma<budget["sampling_noise_rms_v"] and total<envelope["3"]
    correlations=[]
    for path in sorted((OUT/"first_order").glob("*_case.json")):
        name=path.stem.removesuffix("_case"); case=load(f"first_order/{path.name}")
        _,w=waves("first_order",name)
        end=(1.0005+case["window_ns"])*1e-9
        measured=2*(.9-float(np.interp(end,w["time"],w["out"])))
        expected=1.8*math.exp(-case["window_ns"]*1e-9/(case["resistance_ohm"]*case["cside_f"]))
        assert abs(measured-expected)<max(expected*.005,1e-8),(name,measured,expected)
        thermal=math.sqrt(2*k*temperature/case["cside_f"])
        correlations.append({"name":name,"expected_mv":expected*1e3,"measured_mv":measured*1e3,
            "settling_pass":measured<=LIMIT,"thermal_mv":thermal*1e3,"thermal_pass":thermal<budget["sampling_noise_rms_v"]})
    assert len(correlations)==4
    assert not next(x for x in correlations if x["name"]=="rc8_slow")["settling_pass"]
    assert not next(x for x in correlations if x["name"]=="rc8_small_cap")["thermal_pass"]
    row["spectre_correlations"]=correlations
    dump("first_order.json",row)
    return row


def macro_analysis():
    cfg=config();rows=[]
    for path in sorted((OUT/"electrical").glob("*_case.json")):
        name=path.stem.removesuffix("_case");case=load(f"electrical/{path.name}");r,w=waves("electrical",name)
        time=w["time"];at=lambda key,ns:float(np.interp(ns*1e-9,time,w[key]))
        code=sum((w[f"dout<{b}>"][-1]>.45)*(1<<b) for b in range(8))
        vin=case["vdiff_v"];trialcode=0;trace=[]
        parasitic=case["parameters"]["CTOPPAR"]
        attenuation=256*CU/(256*CU+parasitic)
        for step,bit in enumerate(range(7,-1,-1)):
            trial=trialcode+(1<<bit)
            # The acquisition switch forces TOP to Vin before opening. A
            # top-to-VCM parasitic attenuates DAC redistribution, not the
            # acquired voltage: Q conservation gives Vin - alpha*VDAC.
            residual=vin-attenuation*(-.9+trial*LSB)
            compare=44+step*5; latch=45.5+step*5
            measured=at("topp",compare-.02)-at("topn",compare-.02)
            comp=at("comp_p",latch)-at("comp_n",latch)
            trace.append({"bit":bit,"trial":trial,"residual_v":residual,"measured_v":measured,
                          "settling_lsb":(measured-residual)/LSB,"latch_comp_v":comp,
                          "resolved":abs(comp)>=.45,"sign_correct":(comp>=0)==(residual>=0)})
            if residual>=0:trialcode=trial
        valid=np.flatnonzero((w["valid"][:-1]<=.45)&(w["valid"][1:]>.45))+1
        row={"name":name,"kind":case["kind"],"input_v":vin,"code":int(code),"oracle_code":trialcode,
             "settling_max_lsb":max(abs(x["settling_lsb"]) for x in trace),
             "all_resolved":all(x["resolved"] for x in trace),"all_signs_correct":all(x["sign_correct"] for x in trace),
             "conversion_ns":float(time[valid[0]]*1e9-41) if len(valid) else None,
             "reference_droop_mv":float(max(abs(w["vrefp"]-.9).max(),abs(w["vrefn"]).max())*1e3),"trace":trace}
        row["pass"]=bool(code==trialcode and row["settling_max_lsb"]<=.25 and row["all_resolved"] and row["all_signs_correct"] and row["conversion_ns"] is not None and row["conversion_ns"]<60)
        if case["kind"]=="nominal":assert row["pass"],row
        rows.append(row)
    assert len([x for x in rows if x["kind"]=="nominal"])==10
    assert next(r for r in rows if r["name"]=="macro8_slow_reference")["pass"] is False
    dump("electrical/summary.json",rows)
    return [{k:v for k,v in x.items() if k!="trace"} for x in rows]


def warning_inventory(record):
    raw=Path(record["metadata"]["output_dir"])
    log=(raw.parent/"spectre.out").read_text(errors="replace")
    return {"cmi_count":len(re.findall(r"WARNING \(CMI-\d+\)",log)),
            "cmi_instances":sorted(set(re.findall(r"WARNING \(CMI-\d+\): ([^:]+):",log))),
            "suppressed":sum(map(int,re.findall(r"(\d+) warnings suppressed",log))),
            "sfe_1131":log.count("SFE-1131")}


def bootstrap_analysis(tag, only_new=False):
    rows=[]
    for vd in config()["validation"]["native_vdiff_v"]:
        if (only_new or tag.endswith("_tight")) and abs(vd)!=.8:continue
        name=f"boot8_{tag}{'_only_new' if only_new else ''}_vd{'m' if vd<0 else 'p'}{abs(round(vd*1000)):03d}"
        r,w=waves("bootstrap",name);t=w["time"];at=lambda k,ns:float(np.interp(ns*1e-9,t,w[k]))
        row={"name":name,"input_v":vd,"warnings":warning_inventory(r)}
        for variant in (("NEW",) if only_new else ("OLD","NEW")):
            diff=lambda ns:at(f"topp_{variant.lower()}",ns)-at(f"topn_{variant.lower()}",ns)
            row[variant]={"acquisition_error_mv":1000*(diff(249.9)-vd),"held_error_mv":1000*(diff(270)-vd),
                          "hold_drift_mv":1000*(diff(280)-diff(260)),"held_common_mode_v":.5*(at(f"topp_{variant.lower()}",270)+at(f"topn_{variant.lower()}",270))}
            row[variant]["pass"]=abs(row[variant]["acquisition_error_mv"])<=LIMIT*1000 and abs(row[variant]["held_error_mv"])<=LIMIT*1000
        rows.append(row)
        # Actual terminal differences, not absolute boosted-node voltage.
        lo,hi=210.8e-9,251e-9
        mask=(t>=lo)&(t<=hi)
        peaks={}
        for side in ("p","n"):
            g=w[f"xnew_{side}.g"][mask];src=w[f"vin{side}_new"][mask];drain=w[f"top{side}_new"][mask]
            peaks[side]={"vgs_abs_max_v":float(abs(g-src).max()),"vgd_abs_max_v":float(abs(g-drain).max()),
                         "vgb_abs_max_v":float(abs(g).max()),"vdiff_abs_max_v":float(abs(src-drain).max())}
        row["new_main_terminal_peaks_210p8_251ns"]=peaks
    dump("bootstrap/summary_"+tag+("_only_new" if only_new else "")+".json",rows)
    return rows


def comparator_analysis(tag="initial"):
    rows=[]
    prefix="comp8_"+("" if tag=="initial" else tag+"_")
    for vd in (-LIMIT,0,LIMIT):
        pair=[]
        for enabled in (False,True):
            name=f"{prefix}{'m' if vd<0 else 'p'}{abs(round(vd*1e6)):04d}_{'on' if enabled else 'off'}"
            r,w=waves("comparator",name);t=w["time"]
            at=lambda k,ns:float(np.interp(ns*1e-9,t,w[k]))
            diff=lambda ns:at("topp",ns)-at("topn",ns)
            od=at("outp",256.5)-at("outn",256.5)
            pair.append(w)
            rows.append({"name":name,"input_v":vd,"clock_enabled":enabled,"preclock_held_error_mv":1000*(diff(254.9)-vd),
                "input_at_compare_v":diff(254.99),"output_diff_1p5ns_v":od,
                "decision_correct":bool((od>0)==(diff(254.99)>0)) if vd and enabled else None,
                "resolved":bool(abs(od)>=.45) if enabled else None,"warnings":warning_inventory(r)})
        off,on=pair;grid=np.linspace(255e-9,256.5e-9,1501)
        d=lambda w:np.interp(grid,w["time"],w["topp"]-w["topn"])
        kick=d(on)-d(off)
        rows[-1]["on_minus_off_peak_diff_kickback_mv"]=float(abs(kick).max()*1e3)
        rows[-1]["on_minus_off_end_diff_kickback_mv"]=float(kick[-1]*1e3)
    assert len(rows)==6
    # Zero differential is a metastability diagnostic, not a pass/fail code.
    assert all(x["decision_correct"] and x["resolved"] for x in rows if x["input_v"] and x["clock_enabled"])
    dump(f"comparator/summary_{tag}.json",rows)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("local","va","macro","bootstrap","candidate-only","comparator"));p.add_argument("--tag",default="initial");a=p.parse_args()
    result={"local":first_order,"va":va_analysis,"macro":macro_analysis,"bootstrap":lambda:bootstrap_analysis(a.tag),
            "candidate-only":lambda:bootstrap_analysis(a.tag,True),"comparator":lambda:comparator_analysis(a.tag)}[a.stage]()
    import json
    print(json.dumps(result,indent=2,default=str))


if __name__=="__main__":main()
