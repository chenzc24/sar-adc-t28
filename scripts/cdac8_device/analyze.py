"""Measurements from accepted PSF, never CDF values substituted for simulation."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import re
import statistics
from common import OUT,load,dump
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

def read_psf(path):
    p=parse_spectre_psf_ascii(path);assert not p.errors,p.errors
    return {str(k).strip('"').replace("\\","").lower():v for k,v in p.data.items()}

def cap_values(w):
    freq=w["freq"]; rows={}
    for key in "abc":
        rows[key]=[abs(complex(w[f"vsrc{key}{i}:p"][0]).imag)/(2*math.pi*freq[0]) for i in range(3)]
    return rows

def units(mc=0,tag="initial"):
    name=("units_mc_"+str(mc) if mc else "units_nominal_ac")+("" if tag=="initial" else "_"+tag)
    r=load(f"units/{name}_result.json");assert r["ok"],r["errors"]
    raw=Path(r["metadata"]["output_dir"])
    if not mc:
        w=read_psf(raw/"ac_unit.ac");caps=cap_values(w)
        row={k:{"capacitance_ff_by_bias":[x*1e15 for x in v],"cside_pf":256*v[1]*1e12,
                "relative_bias_span":(max(v)-min(v))/statistics.mean(v)} for k,v in caps.items()}
    else:
        log=(raw.parent/"spectre.out").read_text(errors="replace")
        m=re.search(r"Number of random variables:\s*(\d+)",log)
        assert m and int(m[1])>=9,"Local capacitor statistics did not activate"
        files=sorted((raw/"mc_cap_separate").glob("mc_cap-*/mc_cap_ac_unit.ac"))
        assert len(files)==mc,[str(p) for p in raw.rglob("*.ac")]
        values=[cap_values(read_psf(p)) for p in files]
        row={"random_variables":int(m[1]),"numruns":mc,"units":{}}
        for key in "abc":
            samples=[x[key][1] for x in values]
            sigma=statistics.stdev(samples)/statistics.mean(samples)
            assert sigma>1e-7,"Random variables exist but C values did not vary"
            row["units"][key]={"cap_mean_ff":statistics.mean(samples)*1e15,"relative_sigma":sigma,
                "samples_ff":[[v*1e15 for v in x[key]] for x in values]}
    dump("units/summary_"+str(mc)+("" if tag=="initial" else "_"+tag)+".json",row)
    public=row if not mc else {**row,"units":{k:{n:v for n,v in x.items() if n!="samples_ff"} for k,x in row["units"].items()}}
    import json;print(json.dumps(public,indent=2))

def banks(mc=0):
    r=load(f"banks/banks_mc_{mc}_result.json");assert r["ok"],r["errors"]
    raw=Path(r["metadata"]["output_dir"])
    paths=sorted((raw/"mc_bank_separate").glob("mc_bank-*/mc_bank_ac_bank.ac")) if mc else [raw/"ac_bank.ac"]
    assert len(paths)==(mc or 1),paths[:3]
    random_count=0
    if mc:
        log=(raw.parent/"spectre.out").read_text(errors="replace")
        random_count=int(re.search(r"Number of random variables:\s*(\d+)",log)[1])
        assert random_count==512,random_count
    rows=[]
    for path in paths:
        w=read_psf(path);f=w["freq"][0]
        caps={s:[abs(complex(w[f"v_sense{s.lower()}{b}:p"][0]).imag)/(2*math.pi*f) for b in range(9)] for s in "PN"}
        weights=[.9*(caps["P"][b]/sum(caps["P"])+caps["N"][b]/sum(caps["N"])) for b in range(8)]
        levels=[-.9+sum(weights[b] for b in range(8) if code&(1<<b)) for code in range(256)]
        widths=[levels[i+1]-levels[i] for i in range(255)]+[.9-levels[255]]
        dnl=max(abs(v/(1.8/256)-1) for v in widths)
        inl=max(abs((levels[i]-(-.9+i*1.8/256))/(1.8/256)) for i in range(256))
        rows.append({"cside_pf":{s:sum(v)*1e12 for s,v in caps.items()},"weights_v":weights,
            "dnl_abs_max_lsb":dnl,"inl_abs_max_lsb":inl,"monotonic":min(widths)>0,
            "internal_pass":dnl<=.5 and inl<=.5})
    summary={"numruns":mc,"random_variables":random_count,"scope":"actual PDK sampled bank weights + charge-conservation static oracle, not full switched MC transient",
             "dnl_worst_lsb":max(x["dnl_abs_max_lsb"] for x in rows),"inl_worst_lsb":max(x["inl_abs_max_lsb"] for x in rows),
             "internal_pass_count":sum(x["internal_pass"] for x in rows),"rows":rows}
    assert all(x["monotonic"] for x in rows)
    if mc:assert statistics.stdev(x["weights_v"][7] for x in rows)>1e-7
    dump(f"banks/summary_{mc}.json",summary)
    import json;print(json.dumps({k:v for k,v in summary.items() if k!="rows"},indent=2))

def switches(tag="initial"):
    rows=[]
    for path in sorted((OUT/"switches").glob("*_case.json")):
        name=path.stem.removesuffix("_case");case=load(f"switches/{path.name}")
        if tag=="initial" and re.fullmatch(r'switch_(tt|ss|ff)_\d+_-?\d+',name) is None:continue
        if tag!="initial" and not name.endswith('_'+tag):continue
        r=load(f"switches/{name}_result.json");assert r["ok"]
        raw=Path(r["metadata"]["output_dir"]);w=read_psf(raw/"dc_leak.dc")
        row={"name":name,**case}
        for x in "hls":
            on=w[f"vprobe{x}on:p"]
            row[x.upper()]={"ron_ohm":.001/abs(float(on[0])),"off_max_na":max(abs(float(v)) for v in w[f"vprobe{x}off:p"])*1e9}
        rows.append(row)
    assert len(rows)==27
    summary={"rows":rows,"worst_ron_ohm":{x:max(r[x]["ron_ohm"] for r in rows) for x in "HLS"},
             "nominal":next(r for r in rows if r["name"]=="switch_tt_900_27"+("" if tag=="initial" else '_'+tag))}
    dump("switches/summary"+("" if tag=="initial" else '_'+tag)+".json",summary)
    import json;print(json.dumps({k:v for k,v in summary.items() if k!="rows"},indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("units","banks","switches"));p.add_argument("--runs",type=int,default=0);p.add_argument("--tag",default="initial");a=p.parse_args()
    if a.stage=="units":units(a.runs,a.tag)
    elif a.stage=="banks":banks(a.runs)
    else:switches(a.tag)
