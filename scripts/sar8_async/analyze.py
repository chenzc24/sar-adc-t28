"""Independent measured edge / decoded-word assertions for accepted PSF runs."""
from __future__ import annotations
import argparse
import json
import numpy as np
from oa import OUT,dump


def load(name):
    r=json.loads((OUT/"results"/(name+".json")).read_text(encoding="utf-8"))
    assert r["ok"],r["errors"]
    raw=json.loads((OUT/"waves"/(name+".json")).read_text(encoding="utf-8"))
    w={k.lower():np.asarray(v,dtype=float) for k,v in raw.items()}
    assert all(len(v)==len(w["time"]) and np.isfinite(v).all() for v in w.values())
    return w


def edges(w,net,threshold=.45,rising=True):
    v=w[net.lower()];t=w["time"]
    idx=np.where((v[:-1]<threshold)&(v[1:]>=threshold) if rising else (v[:-1]>threshold)&(v[1:]<=threshold))[0]
    return np.array([t[i]+(threshold-v[i])/(v[i+1]-v[i])*(t[i+1]-t[i]) for i in idx])*1e9


def at(w,net,t_ns):return float(np.interp(t_ns*1e-9,w["time"],w[net.lower()]))


def gates(name,supply=.9):
    w=load(name);rises=edges(w,"a",supply/2);rows={}
    for role in ("dac","valid","capture","reset","advance","publish","bbm"):
        out=edges(w,"y_"+role,supply/2)
        ds=[]
        for t in rises:
            q=out[(out>t)&(out<t+4)]
            if len(q):ds.append(float(q[0]-t))
        assert len(ds)>=3,(role,ds)
        rows[role]=dict(rise_delays_ns=ds,minimum_ns=min(ds),maximum_ns=max(ds))
    # Skip deliberate D/CK coincident edges in this common-source fixture.
    checks=[]
    for t in edges(w,"ck",supply/2):
        if min(abs(t-edges(w,"b",supply/2)))<.1 or min(abs(t-edges(w,"b",supply/2,False)))<.1:continue
        if t+.3>w["time"][-1]*1e9:continue
        want=int(at(w,"b",t-.05)>supply/2);actual=int(at(w,"q",t+.3)>supply/2)
        checks.append(dict(edge_ns=t,want=want,actual=actual));assert want==actual,checks[-1]
    resets=edges(w,"rst",supply/2);reset_checks=[]
    for t in resets:
        if t<2:continue
        ok=at(w,"q",t+.15)<.2*supply
        reset_checks.append(dict(reset_ns=float(t),cleared=ok));assert ok,reset_checks[-1]
    if len(reset_checks)>=2:
        assert at(w,"b",4.9)>.8*supply and at(w,"q",4.9)<.2*supply
        assert at(w,"b",25.7)>.8*supply and at(w,"q",25.7)<.2*supply
    result=dict(delays=rows,dff=checks,async_reset=reset_checks,scope="loaded_5f_native_TT_or_named_corner")
    dump("analysis/"+name+".json",result);print(json.dumps(result,indent=2));return result


def logic(name,expected=None,supply=.9,allow_fault=False):
    w=load(name);rises=edges(w,"valid",supply/2);caps=edges(w,"capture",supply/2)
    advs=edges(w,"advance",supply/2);cmp=edges(w,"cmp_clk",supply/2)
    capfall=edges(w,"capture",supply/2,False);cmpfall=edges(w,"cmp_clk",supply/2,False)
    rows=[]
    for t in rises:
        frame=int(t//100);lo=frame*100+43
        c=caps[(caps>=lo)&(caps<t)];a=advs[(advs>=lo)&(advs<t)];e=cmp[(cmp>=lo)&(cmp<t)]
        code=sum((1<<i)*int(at(w,f"d{i}",t+.1)>supply/2) for i in range(8))
        row=dict(frame=frame,valid_ns=float(t-frame*100),code=code,capture_times_ns=(c-frame*100).tolist(),
                 eval_times_ns=(e-frame*100).tolist(),advance_times_ns=(a-frame*100).tolist(),
                 fault=at(w,"fault",t+.1)>supply/2)
        row["pass"]=bool(len(c)==len(a)==len(e)==8 and np.all(a>c) and not row["fault"] and
                         (expected is None or code==(expected[frame] if isinstance(expected,list) else expected)))
        if len(c)==8:
            widths=[];reset_after_capture=[]
            for ct in c:
                cf=capfall[capfall>ct][0];rf=cmpfall[cmpfall>ct][0]
                widths.append(float(cf-ct));reset_after_capture.append(float(rf-cf))
            row["capture_widths_ns"]=widths;row["cmp_reset_after_capture_fall_ns"]=reset_after_capture
            row["pass"] &= min(reset_after_capture)>=0
            if "xctrl.trial" in w:
                tr=edges(w,"xctrl.trial",supply/2);tr=tr[(tr>=lo)&(tr<t)]
                row["trial_to_eval_ns"]=(e-tr).tolist() if len(tr)==8 else []
                row["pass"] &= bool(len(tr)==8 and min(e-tr)>=3.0)
            if "xctrl.t7" in w:
                row["onehot_capture_stable"]=all(
                    sum(at(w,f"xctrl.t{b}",ct+dt)>supply/2 for b in range(8))==1
                    and at(w,f"xctrl.t{7-j}",ct+dt)>supply/2
                    for j,ct in enumerate(c) for dt in (-.02,.1))
                row["pass"] &= row["onehot_capture_stable"]
        if "sel0_0" in w:
            row["reference_overlap"]=any(np.any((w[f"sel0_{i}"]>supply/2)&(w[f"sel1_{i}"]>supply/2)) for i in range(8))
            row["pass"] &= not row["reference_overlap"]
        rows.append(row)
    result=dict(name=name,rows=rows,valid_count=len(rises),capture_count=len(caps),eval_count=len(cmp),
                maximum_fault_v=float(w["fault"].max()),pass_=bool(rows and all(r["pass"] for r in rows)))
    if allow_fault:result["pass_"]=len(rises)==0 and w["fault"].max()>.8*supply
    dump("analysis/"+name+".json",result);print(json.dumps(result,indent=2));return result


def compare(reference,candidate,tolerance_ns=.02):
    a,b=load(reference),load(candidate);errors={}
    for net in ("cmp_clk","capture","advance","valid"):
        x,y=edges(a,net),edges(b,net);assert len(x)==len(y)>0,(net,len(x),len(y))
        errors[net]=float(np.max(np.abs(x-y)))
    assert max(errors.values())<=tolerance_ns,errors
    result=dict(reference=reference,candidate=candidate,max_edge_difference_ns=errors,tolerance_ns=tolerance_ns,pass_=True)
    dump("analysis/mode_control.json",result);print(json.dumps(result,indent=2));return result


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("kind",choices=["gates","logic","compare"]);ap.add_argument("name")
    ap.add_argument("--candidate")
    ap.add_argument("--expected",type=int);ap.add_argument("--supply",type=float,default=.9);args=ap.parse_args()
    if args.kind=="compare":compare(args.name,args.candidate)
    else:(gates if args.kind=="gates" else lambda n,supply:logic(n,args.expected,supply))(args.name,supply=args.supply)
