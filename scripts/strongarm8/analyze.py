"""Deterministic and statistical analysis; no synthesized circuit outcomes."""
from __future__ import annotations
import argparse
import bisect
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

from run import OUT, ROOT, config, dump


def load(path):
    return json.loads(path.read_text())


def interp(t, y, at):
    j=bisect.bisect_left(t,at)
    assert 0 < j < len(t),(at,t[0],t[-1])
    a=(at-t[j-1])/(t[j]-t[j-1])
    return y[j-1]+a*(y[j]-y[j-1])


def cross(t,y,threshold,start,stop):
    for k in range(max(1,bisect.bisect_left(t,start)),len(t)):
        if t[k-1]>stop:break
        if y[k-1]<threshold<=y[k]:
            at=t[k-1]+(threshold-y[k-1])*(t[k]-t[k-1])/(y[k]-y[k-1])
            if start<=at<=stop:return at
    return None


def waves(name):
    r=load(OUT/"results"/(name+".json"));assert r["ok"],r["errors"]
    c=load(OUT/"cases"/(name+".json"))
    w=load(OUT/"waves"/(name+".json"))
    w.pop("units",None)
    assert len(w["time"])>1 and all(math.isfinite(x) for x in w["time"])
    assert all(a<b for a,b in zip(w["time"],w["time"][1:]))
    for key,value in w.items():
        assert len(value)==len(w["time"]),(name,key)
        assert all(math.isfinite(x) for x in value),(name,key)
    return r,c,w


def logtext(result):
    return (Path(result["metadata"]["output_dir"]).parent/"spectre.out").read_text(errors="replace")


def stress(result):
    log=logtext(result)
    return {"cmi_printed":len(re.findall(r"WARNING \(CMI-",log)),
            "suppressed":sum(map(int,re.findall(r"(\d+) warnings suppressed",log))),
            "devices":sorted(set(re.findall(r"WARNING \(CMI-\d+\): ([^:]+):",log)))}


def deterministic():
    rows=[]
    for path in sorted((OUT/"results").glob("det_*.json")):
        if not load(path).get("ok"):continue
        r,c,w=waves(path.stem);t=w["time"];sup=c["supply_v"];sgn=1 if c["differential_v"]>0 else -1
        signed=[sgn*(p-n) for p,n in zip(w["outp"],w["outn"])];delays=[];levels=[];resets=[]
        for k in range(3):
            edge=cross(t,w["clk"],sup/2,(4.9+5*k)*1e-9,(5.2+5*k)*1e-9)
            assert edge is not None
            decision=cross(t,signed,sup/2,edge,edge+1.5e-9)
            delays.append(None if decision is None else (decision-edge)*1e12)
            levels.append(interp(t,signed,edge+1.5e-9))
            resets.append(min(interp(t,w["outp"],(4.9+5*k)*1e-9),interp(t,w["outn"],(4.9+5*k)*1e-9)))
        power=0.0;clockenergy=0.0
        for k in range(1,len(t)):
            if 5.01e-9<=t[k-1] and t[k]<=10.01e-9:
                dt=t[k]-t[k-1]
                power+=-.5*sup*(w["vvdd:p"][k-1]+w["vvdd:p"][k])*dt
                clockenergy+=-.5*(w["clk"][k-1]*w["vclk:p"][k-1]+w["clk"][k]*w["vclk:p"][k])*dt
        rows.append({"name":path.stem,**c,"delay_ps":delays,"output_at_deadline_v":levels,
            "reset_min_v":min(resets),"timing_pass":all(x is not None for x in delays) and min(resets)>=.9*sup,
            "supply_cycle_energy_fj":power*1e15,"clock_cycle_energy_fj":clockenergy*1e15,"stress":stress(r)})
    dump("summary/deterministic.json",rows)
    print("DETERMINISTIC",len(rows),"pass",sum(r["timing_pass"] for r in rows),
          "CMI",sum(r["stress"]["cmi_printed"]>0 for r in rows))
    return rows


def decisions(w,cycles,continuous=False):
    t=w["time"];diff=[p-n for p,n in zip(w["outp"],w["outn"])]
    out=[]
    for k in range(cycles):
        at=6.51e-9+k*5e-9
        value=interp(t,diff,at)
        if not continuous:
            j=min(range(max(0,bisect.bisect_left(t,at)-1),min(len(t),bisect.bisect_left(t,at)+2)),key=lambda j:abs(t[j]-at))
            assert abs(t[j]-at)<1e-15,(at,t[j])
        out.append(1 if value>.45 else -1 if value<-.45 else 0)
    return out


def cdf_fit(rows):
    norm=statistics.NormalDist()
    def loss(mu,ls):
        sigma=math.exp(ls);s=0.
        for r in rows:
            p=max(1e-12,min(1-1e-12,norm.cdf((r["differential_v"]-mu)/sigma)))
            n=r["cycles"]-r["unresolved"];k=r["positive"]
            s-=k*math.log(p)+(n-k)*math.log1p(-p)
        return s
    mu,ls=0.,math.log(.0007);dm,ds=.0003,.4
    for _ in range(120):
        trials=[(loss(mu+i*dm,ls+j*ds),mu+i*dm,ls+j*ds) for i in (-1,0,1) for j in (-1,0,1)]
        _,newmu,newls=min(trials)
        if newmu==mu and newls==ls:dm*=.6;ds*=.6
        else:mu,ls=newmu,newls
        if dm<1e-10 and ds<1e-7:break
    return {"threshold_v":mu,"sigma_v":math.exp(ls),"negative_log_likelihood":loss(mu,ls),
            "scope":"Gaussian-CDF effective input noise; correlated cycles not independent yield evidence"}


def noise():
    rows=[];pilots=[]
    for path in sorted((OUT/"results").glob("noise_*.json")):
        if not load(path).get("ok"):continue
        r,c,w=waves(path.stem)
        out=decisions(w,c["cycles"],not c["strobe_only"])
        row={**c,"positive":out.count(1),"negative":out.count(-1),"unresolved":out.count(0),
             "outcomes":out,"stress":stress(r)}
        (pilots if not c["strobe_only"] else rows).append(row)
    fits={}
    for bandwidth in sorted(set(r["fmax_hz"] for r in rows)):
        subset=[r for r in rows if r["fmax_hz"]==bandwidth]
        if len(set(r["differential_v"] for r in subset))<3:continue
        fits[str(bandwidth)]={"pooled":cdf_fit(subset),"seeds":{str(seed):cdf_fit([r for r in subset if r["seed"]==seed]) for seed in sorted(set(r["seed"] for r in subset))}}
    result={"rows":rows,"fits":fits,"pilot_seed_decisions_differ":len(pilots)==2 and pilots[0]["outcomes"]!=pilots[1]["outcomes"],"pilots":pilots}
    dump("summary/noise.json",result);print("NOISE",len(rows),fits)
    return result


def offset(name):
    from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
    result=load(OUT/"results"/(name+".json"));assert result["ok"],result["errors"]
    cfg=load(OUT/"cases"/(name+".json"));raw=Path(result["metadata"]["output_dir"])
    files=sorted(p for p in raw.rglob("*") if p.is_file() and "tran" in p.name and not p.name.startswith("log"))
    n=len(cfg.get("input_sequence_v",[]));half=n//2;rows=[];stats=[]
    for file in files:
        parsed=parse_spectre_psf_ascii(file)
        if parsed.errors or "time" not in parsed.data:continue
        w={k.lower():v for k,v in parsed.data.items() if isinstance(v,list)}
        if cfg.get("category")=="mismatch_binary":
            if "search_done" not in w:continue
            assert w["time"][-1]>=53e-9
            assert w["search_done"][-1]>.99 and w["search_bad"][-1]<.01,(name,str(file),w["search_bad"][-1])
            lo,hi=w["search_lo"][-1],w["search_hi"][-1]
            assert hi>lo and abs(hi-lo-cfg["threshold_resolution_v"])<1e-8
            bound={"low_v":lo,"high_v":hi,"midpoint_v":(lo+hi)/2,"nonmonotonic":None,"unresolved":0}
            rows.append({"file":str(file.relative_to(raw)),"ascending":bound,"descending":dict(bound),
                         "method":"binary; direction-history measured separately by dense pilot"})
            continue
        if "outp" not in w or w["time"][-1]<(n*5+1.4)*1e-9:continue
        out=decisions(w,n)
        bounds=[]
        for a,b in ((0,half),(half,n)):
            pairs=sorted(zip(cfg["input_sequence_v"][a:b],out[a:b]))
            neg=[v for v,d in pairs if d==-1];pos=[v for v,d in pairs if d==1]
            nonmono=any(pairs[i][1]>pairs[i+1][1] for i in range(len(pairs)-1))
            lo=max(neg) if neg else None;hi=min(pos) if pos else None
            bounds.append({"low_v":lo,"high_v":hi,"midpoint_v":(lo+hi)/2 if lo is not None and hi is not None else None,
                           "nonmonotonic":nonmono,"unresolved":sum(d==0 for _,d in pairs)})
        rows.append({"file":str(file.relative_to(raw)),"ascending":bounds[0],"descending":bounds[1]})
    assert len(rows)==cfg["draws"],(name,len(rows),cfg["draws"],[str(x) for x in files[:8]])
    mids=[r["ascending"]["midpoint_v"] for r in rows if r["ascending"]["midpoint_v"] is not None]
    for f in raw.rglob("*mismatch*params*"):
        if f.is_file():stats.append({"file":str(f.relative_to(raw)),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size})
    limit=config()["targets"]["systematic_offset_abs_v"]
    inside=sum(r["ascending"]["low_v"] is not None and r["ascending"]["high_v"] is not None and
               r["ascending"]["low_v"]>=-limit and r["ascending"]["high_v"]<=limit for r in rows)
    log=logtext(result);rv=re.search(r"Number of random variables:\s*(\d+)",log)
    summary={"name":name,"draws":len(rows),"resolution_v":cfg["threshold_resolution_v"],"rows":rows,
             "midpoint_mean_v":statistics.mean(mids),"midpoint_sigma_v":statistics.stdev(mids),
             "midpoint_min_v":min(mids),"midpoint_max_v":max(mids),"uncensored":len(mids),
             "fully_inside_pm_budget":inside,"random_variables":int(rv[1]) if rv else None,
             "sampled_statistics_files":stats,"history_max_midpoint_difference_v":max(abs(r["ascending"]["midpoint_v"]-r["descending"]["midpoint_v"]) for r in rows if r["ascending"]["midpoint_v"] is not None and r["descending"]["midpoint_v"] is not None),
             "nonmonotonic_draws":sum(bool(r["ascending"]["nonmonotonic"] or r["descending"]["nonmonotonic"]) for r in rows),
             "stress":stress(result)}
    if cfg.get("category")=="mismatch_binary":
        summary["history_max_midpoint_difference_v"]=None
        summary["nonmonotonic_draws"]=None
        summary["history_scope"]="not measured by binary; see independent dense pilot"
    dump(f"summary/{name}.json",summary)
    print("OFFSET",{k:v for k,v in summary.items() if k not in ("rows","sampled_statistics_files")})
    return summary


def held():
    rows=[]
    for f in (OUT/"results").glob("held_*.json"):
        if not load(f).get("ok"):continue
        r,c,w=waves(f.stem);t=w["time"];d=[p-n for p,n in zip(w["vinp"],w["vinn"])];baseline=interp(t,d,4.9e-9)
        take=[i for i,x in enumerate(t) if 5e-9<=x<=6.51e-9]
        rows.append({**c,"pre_edge_diff_v":baseline,"fixture_valid":abs(baseline-c["differential_v"])<max(1e-6,.01*abs(c["differential_v"])),
                     "peak_diff_kickback_v":max(abs(d[i]-baseline) for i in take),"deadline_input_shift_v":interp(t,d,6.51e-9)-baseline,"stress":stress(r)})
    dump("summary/held.json",rows);print("HELD",rows);return rows


def cdac():
    rows=[]
    for f in (OUT/"results").glob("cdac_*_on.json"):
        if not load(f).get("ok"):continue
        r,c,w=waves(f.stem);offname=f.stem[:-2]+"off"
        if not (OUT/"waves"/(offname+".json")).exists():continue
        ro,co,wo=waves(offname);t=w["time"]
        differential=[p-n for p,n in zip(w["topp"],w["topn"])];offdiff=[p-n for p,n in zip(wo["topp"],wo["topn"])]
        cm=[(p+n)/2 for p,n in zip(w["topp"],w["topn"])];offcm=[(p+n)/2 for p,n in zip(wo["topp"],wo["topn"])]
        delta=[v-interp(wo["time"],offdiff,x) for x,v in zip(t,differential) if wo["time"][0]<x<wo["time"][-1]]
        cmdelta=[v-interp(wo["time"],offcm,x) for x,v in zip(t,cm) if 46e-9<=x<=82.6e-9]
        samples=[]
        for k in range(8):
            edge=cross(t,w["cmp_test"],.45,(45.9+5*k)*1e-9,(46.2+5*k)*1e-9)
            assert edge is not None
            at=edge+1.5e-9
            signed=[(1 if c["differential_v"]>=0 else -1)*(p-n) for p,n in zip(w["comp_p"],w["comp_n"])]
            decision=cross(t,signed,.45,edge,at) if c["differential_v"] else None
            samples.append({"edge_ns":edge*1e9,"deadline_diff_v":interp(t,differential,at),
                            "deadline_on_minus_off_v":interp(t,differential,at)-interp(wo["time"],offdiff,at),
                            "decision_delay_ps":None if decision is None else (decision-edge)*1e12,
                            "decision_on_minus_off_v":None if decision is None else interp(t,differential,decision)-interp(wo["time"],offdiff,decision),
                            "decision_cm_on_minus_off_v":None if decision is None else interp(t,cm,decision)-interp(wo["time"],offcm,decision),
                            "output_diff_v":interp(t,w["comp_p"],at)-interp(t,w["comp_n"],at)})
        rows.append({**c,"peak_on_minus_off_v":max(abs(x) for x in delta),"samples":samples,
                     "peak_cm_on_minus_off_v":max(abs(x) for x in cmdelta),
                     "pre_first_compare_diff_v":interp(t,differential,45.9e-9),"stress":stress(r),"off_stress":stress(ro),
                     "common_mode_min_v":min((p+n)/2 for x,p,n in zip(t,w["topp"],w["topn"]) if 45.9e-9<=x<=82.6e-9),
                     "common_mode_max_v":max((p+n)/2 for x,p,n in zip(t,w["topp"],w["topn"]) if 45.9e-9<=x<=82.6e-9)})
    dump("summary/cdac.json",rows);print("CDAC",rows);return rows


def audit():
    """Check every accepted deck and the two independent offset search methods."""
    from run import dut_block, sha, source
    expected=sha(dut_block(source()));accepted=[]
    for f in sorted((OUT/"results").glob("*.json")):
        r=load(f)
        if not r.get("ok"):continue
        c=load(OUT/"cases"/(f.stem+".json"));s=(OUT/"decks"/(f.stem+".scs")).read_text()
        assert sha(s)==r["deck_sha256"]==c["deck_sha256"]
        assert sha(dut_block(s))==expected==c["dut_sha256"]
        if "stimulus_sha256" in c:
            assert sha((ROOT/"scripts/strongarm8/offset_search.va").read_text())==c["stimulus_sha256"]
        accepted.append(f.stem)
    dense=load(OUT/"summary/mc_offset_4_phase.json")
    pilot=load(OUT/"summary/mc_binary_4.json")
    full=load(OUT/"summary/mc_binary_128.json")
    for a,b,c in zip(dense["rows"],pilot["rows"],full["rows"]):
        for direction in ("ascending","descending"):
            for key in ("low_v","high_v"):
                assert abs(a[direction][key]-b["ascending"][key])<1e-12
                assert abs(b["ascending"][key]-c["ascending"][key])<1e-12
    def sampled_lines(name):
        r=load(OUT/"results"/(name+".json"));raw=Path(r["metadata"]["output_dir"])
        lines=(raw/"mc.mismatch.mcdata").read_text().splitlines()
        return [line for line in lines if line.strip() and not line.lstrip().startswith(("#",";"))]
    a,b,c=map(sampled_lines,("mc_offset_4_phase","mc_binary_4","mc_binary_128"))
    assert len(a)==len(b)>0 and len(a)%4==0 and len(c)==len(a)*32,(len(a),len(b),len(c))
    assert a==b==c[:len(a)],"MC sampled variables changed between search methods"
    result={"accepted_decks":len(accepted),"dut_sha256":expected,
            "all_accepted_dut_and_deck_hashes_match":True,
            "dense_binary_pilot_and_full_first_four_thresholds_match":True,
            "first_four_mc_sample_rows_identical":True,
            "mc_sample_lines_per_draw":len(a)//4,
            "first_four_mc_sample_sha256":hashlib.sha256("\n".join(a).encode()).hexdigest(),
            "final_oa_readback":"deferred: CIW unresponsive, user requested other conditions first; no OA mutations"}
    dump("summary/audit.json",result);print("AUDIT",result);return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=["deterministic","noise","offset","held","cdac","audit","all"]);p.add_argument("--name",default="mc_offset_4_phase");args=p.parse_args()
    if args.stage=="all":
        deterministic();noise();held();cdac()
    elif args.stage=="offset":offset(args.name)
    else:globals()[args.stage]()
