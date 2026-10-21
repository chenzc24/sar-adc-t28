"""Analyze saved native unit and integrated records without running Spectre."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import pickle
import re

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_physical"
Q = 1.8 / 256


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def edge(t, v, rising=True):
    ix = np.flatnonzero((v[:-1] < .45) & (v[1:] >= .45) if rising
                        else (v[:-1] > .45) & (v[1:] <= .45))
    return t[ix] + (.45-v[ix])*(t[ix+1]-t[ix])/(v[ix+1]-v[ix])


def load(name):
    folder = OUT / "runs" / name
    result = json.loads((folder/"result.json").read_text())
    assert result["ok"], result["errors"]
    receipt = json.loads((folder/"waveform_receipt.json").read_text())
    p = folder/"waveform.pickle"
    assert digest(p) == receipt["sha256"]
    with p.open("rb") as stream:
        wave = pickle.load(stream)
    return folder, result, wave


def measure(name, verbose=True):
    folder, result, w = load(name)
    if not w and (Path(result["metadata"]["output_dir"])/"ac_unit.ac").exists():
        from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
        path=Path(result["metadata"]["output_dir"])/"ac_unit.ac"
        parsed=parse_spectre_psf_ascii(path)
        assert parsed.ok,parsed.errors
        d={k.lower():np.asarray(v).reshape(-1)[0] for k,v in parsed.data.items()}
        admittance=-d["vdc:p"]/d["in"]
        info=dict(result_ok=True,source_file_sha256=digest(path),frequency_hz=float(d["freq"]),
                  resistance_ohm=float(1/admittance.real),capacitance_f=float(admittance.imag/(2*np.pi*d["freq"])))
        (folder/"analysis.json").write_text(json.dumps(info,indent=2)+"\n")
        if verbose:print(json.dumps(info,indent=2))
        return info
    t = w["time"] * 1e9
    at = lambda k, ns: np.interp(ns, t, w[k.lower()])
    unit = "xdut.sample_int" not in w
    word = lambda prefix, ns: sum(int(at(prefix+str(i), ns) > .45) << i for i in range(8))
    rows = []
    if unit:
        for f in range(2):
            rows.append(dict(time_ns=100*f+30, expected=128, actual=word("xref.q", 100*f+30), phase="sampling"))
            for i, target in enumerate([127,128,255,0,170,85,85,65]):
                ns = 100*f+48+5*i
                rows.append(dict(time_ns=ns, expected=target, actual=word("xref.q", ns), phase="update"))
        polarity_bad = []
        overlap = []
        for row in rows:
            for side in "pn":
                for bit in range(8):
                    wanted = .9 * (((row["expected"]>>bit)&1) if side=="p" else 1-((row["expected"]>>bit)&1))
                    for rail in "pn":
                        value = float(at(f"g{side}{rail}{bit}", row["time_ns"]))
                        if abs(value-wanted)>.09:
                            polarity_bad.append(dict(time_ns=row["time_ns"],node=f"g{side}{rail}{bit}",value=value,target=wanted))
                    mask=(t>=2)&(w[f"g{side}p{bit}"]<.45)&(w[f"g{side}n{bit}"]>.45)
                    if np.any(mask):
                        overlap.append(dict(side=side,bit=bit,first_ns=float(t[np.flatnonzero(mask)[0]])))
        info=dict(unit=True,checks=rows,all_words_correct=all(r["expected"]==r["actual"] for r in rows),
                  gate_polarity_failures=polarity_bad,gate_threshold_overlap=overlap)
        conservative_overlap=[]
        for side in "pn":
            for bit in range(8):
                mask=(t>=2)&(w[f"g{side}p{bit}"]<.6)&(w[f"g{side}n{bit}"]>.3)
                if np.any(mask):conservative_overlap.append(dict(side=side,bit=bit,first_ns=float(t[np.flatnonzero(mask)[0]])))
        info["gate_conservative_overlap_after_initialization"]=conservative_overlap
        info["gate_overlap_definition"]="No overlapping GP<0.6V and GN>0.3V after2ns; voltage screen, not a pass-current measurement"
        info["update_width_ps"]=[float((d-u)*1000) for u in edge(t,w["phi_u"])
                                   for d in edge(t,w["phi_u"],False) if 0<d-u<1.5][:16]
        capture=[]
        for f in range(2):
            previous=128
            falls=edge(t,w["phi_u"],False)
            falls=falls[(falls>100*f+40)&(falls<100*f+90)]
            for ft,target in zip(falls,[127,128,255,0,170,85,85,65]):
                after_ns=ft+.3
                capture_ns=None
                if "xref.cap0" in w:
                    clocks=edge(t,w["xref.cap0"])
                    found=clocks[(clocks>ft)&(clocks<ft+2)]
                    assert len(found)==1,(ft,found)
                    capture_ns=float(found[0]);after_ns=capture_ns+.2
                capture.append(dict(fall_ns=float(ft),before_expected=previous,
                                    before_actual=word("xref.q",ft-.04),after_expected=target,
                                    after_actual=word("xref.q",after_ns),LSB_clock_ns=capture_ns,
                                    capture_deadline_pass=capture_ns is None or capture_ns-ft<=1))
                previous=target
        info["fall_capture_checks"]=capture
        info["fall_capture_checks_pass"]=len(capture)==16 and all(
            r["before_expected"]==r["before_actual"] and r["after_expected"]==r["after_actual"]
            and r["capture_deadline_pass"] for r in capture)
        if "xref.cap0" in w:
            info["max_LSB_capture_delay_ns"]=max(r["LSB_clock_ns"]-r["fall_ns"] for r in capture)
            order=[]
            ft=capture[0]["fall_ns"]
            for bit in range(7,-1,-1):
                key="xref.cap_clk" if bit==7 else f"xref.cap{bit}"
                found=edge(t,w[key]);found=found[(found>ft)&(found<ft+1)]
                assert len(found)==1,(key,found)
                order.append(dict(bit=bit,clock_ns=float(found[0])))
            info["capture_clock_order"]=order
            info["weight_first_clock_order_pass"]=all(b["clock_ns"]>a["clock_ns"] for a,b in zip(order,order[1:]))
            info["min_adjacent_clock_separation_ps"]=min((b["clock_ns"]-a["clock_ns"])*1000 for a,b in zip(order,order[1:]))
        slews=[]
        for bit in range(8):
            key=f"gnp{bit}";v=w[key];mask=(t>=44)&(t<46)
            tm=t[mask];vm=v[mask]
            def crossing(level):
                ids=np.flatnonzero((vm[:-1]>level)&(vm[1:]<=level))
                if not len(ids):return None
                i=ids[0];return float(tm[i]+(level-vm[i])*(tm[i+1]-tm[i])/(vm[i+1]-vm[i]))
            t90=crossing(.81);t10=crossing(.09)
            if t90 is not None and t10 is not None:
                slews.append(dict(node=key,fall_90_10_ps=(t10-t90)*1000))
        info["first_update_gate_slew"]=slews
        if "xref.late_clk" in w:
            # Two physical captures per UPDATE: committed D, then next CODE.
            # Legacy one-edge checks above are not the contract of this cell.
            info.pop("fall_capture_checks",None);info.pop("fall_capture_checks_pass",None)
            ck=edge(t,w["xref.cap_clk"])
            rises=edge(t,w["phi_u"])
            checks=[]
            for f in range(2):
                previous=128
                frame_updates=rises[(rises>100*f+40)&(rises<100*f+90)]
                for u,target in zip(frame_updates,[127,128,255,0,170,85,85,65]):
                    clocks=ck[(ck>u)&(ck<u+2)]
                    commit=previous&target
                    row=dict(update_ns=float(u),capture_clock_count=len(clocks),previous_expected=previous,
                             previous_actual=word("xref.q",u-.04),commit_expected=commit,target_expected=target)
                    if len(clocks)==2:
                        row.update(first_clock_ns=float(clocks[0]),late_clock_ns=float(clocks[1]),
                                   late_delay_ns=float(clocks[1]-u),
                                   commit_actual=word("xref.q",(clocks[0]+clocks[1])/2),
                                   target_actual=word("xref.q",clocks[1]+.2))
                    row["pass"]=(len(clocks)==2 and row["previous_actual"]==previous
                                 and row["commit_actual"]==commit and row["target_actual"]==target
                                 and row["late_delay_ns"]<=1.5)
                    checks.append(row);previous=target
            info["two_phase_checks"]=checks
            info["two_phase_checks_pass"]=len(checks)==16 and all(r["pass"] for r in checks)
            info["max_late_capture_delay_ns"]=max((r.get("late_delay_ns",0) for r in checks),default=None)
    else:
        samples=edge(t,w["xdut.sample_int"],False)
        compares=edge(t,w["xdut.cmp_clk"])
        writes=edge(t,w["xdut.xctrl.phi_w"])
        updates=edge(t,w["xdut.phi_u"])
        digital=sum((w[f"d{i}"]>.45).astype(int)*2**i for i in range(8))
        for f, ns in enumerate(samples):
            source=float(at("vinp_src",ns)-at("vinn_src",ns))
            held=float(at("xdut.topp",ns+.6)-at("xdut.topn",ns+.6))
            code=word("d",100*f+98)
            ideal=int(np.clip(np.floor((source+.9)/Q),0,255))
            counts={k:len(a[(a>=100*f)&(a<100*(f+1))]) for k,a in (("compare",compares),("write",writes),("update",updates))}
            cs=compares[(compares>=100*f)&(compares<100*(f+1))]
            errors=[]
            reference_words=[]
            for ct in cs:
                trial=word("xdut.code",ct-.02)
                residual=float(at("xdut.topp",ct-.02)-at("xdut.topn",ct-.02))
                errors.append((residual-(held+.9-trial*Q))/Q)
                reference_words.append(dict(compare_ns=float(ct),trial=trial,physical_word=word("xdut.xref.q",ct-.02)))
            last=updates[(updates>=100*f)&(updates<100*(f+1))]
            stable_mask=(t>=100*f+90)&(t<=100*f+98)
            rails=[abs(float(at(f"d{i}",100*f+read_ns))-(.9 if (code>>i)&1 else 0))
                   for i in range(8) for read_ns in (90,98)]
            rows.append(dict(frame=f,sample_ns=float(ns),source_v=source,held_v=held,
                             raw_held_error_mv=(held-source)*1000,code=code,ideal_code=ideal,
                             code_error=code-ideal,code_stable=bool(np.all(digital[stable_mask]==code)),counts=counts,
                             output_rail_max_error_v=max(rails),output_rail_screen_pass=max(rails)<=.09,
                             conversion_complete_ns=float(last[-1]-ns) if len(last) else None,
                             precompare_error_lsb=errors,reference_words=reference_words))
        info=dict(unit=False,frames=rows,all_eight_events=all(all(v==8 for v in r["counts"].values()) for r in rows),
                  codes=[r["code"] for r in rows],ideal_codes=[r["ideal_code"] for r in rows],
                  all_codes_exact=all(r["code_error"]==0 for r in rows),all_codes_stable=all(r["code_stable"] for r in rows),
                  max_held_error_mv=max(abs(r["raw_held_error_mv"]) for r in rows),
                  max_precompare_error_lsb=max((abs(e) for r in rows for e in r["precompare_error_lsb"]),default=None))
        info["all_reference_words_match_trial"]=all(x["trial"]==x["physical_word"] for r in rows for x in r["reference_words"])
        info["all_output_rails_valid"]=all(r["output_rail_screen_pass"] for r in rows)
        if "xdut.xref.late_clk" in w:
            clocks=edge(t,w["xdut.xref.cap_clk"])
            phases=[]
            for u in updates:
                ck=clocks[(clocks>u)&(clocks<u+2)]
                row=dict(update_ns=float(u),capture_clock_count=len(ck))
                if len(ck)==2:
                    previous=word("xdut.xref.q",u-.04)
                    committed=word("d",ck[0]-.02);trial=word("xdut.code",ck[1]-.02)
                    actual_commit=word("xdut.xref.q",(ck[0]+ck[1])/2)
                    actual_trial=word("xdut.xref.q",ck[1]+.2)
                    row.update(previous=previous,committed=committed,trial=trial,
                               actual_commit=actual_commit,actual_trial=actual_trial,
                               first_clock_ns=float(ck[0]),late_clock_ns=float(ck[1]),
                               phase_gap_ns=float(ck[1]-ck[0]),
                               commit_changed_bits=(previous^committed).bit_count(),
                               trial_changed_bits=(committed^trial).bit_count())
                    row["pass"]=(committed==actual_commit and trial==actual_trial
                                 and row["commit_changed_bits"]<=1 and row["trial_changed_bits"]<=1)
                else:row["pass"]=False
                phases.append(row)
            info["two_phase_reference_steps"]=phases
            info["all_two_phase_reference_steps_pass"]=len(phases)==8*len(rows) and all(r["pass"] for r in phases)
        info["gate_conservative_overlap"]=[]
        for side in "pn":
            for bit in range(8):
                mask=(w[f"xdut.g{side}p{bit}"]<.6)&(w[f"xdut.g{side}n{bit}"]>.3)
                if np.any(mask):info["gate_conservative_overlap"].append(dict(side=side,bit=bit,first_ns=float(t[np.flatnonzero(mask)[0]])))
    log=(Path(result["metadata"]["output_dir"]).parent/"spectre.out").read_text(errors="replace")
    info.update(result_ok=True,waveform_sha256=digest(folder/"waveform.pickle"),
                has_CMI=bool(re.search(r"CMI-27\d+",log)),CMI_codes=sorted(set(re.findall(r"CMI-27\d+",log))),LTE_count=log.count("SPECTRE-16780"),
                warnings=result["warnings"],summary_footer=re.findall(r"spectre completes with [^\n]+",log))
    reference_stress=[]
    for side in "pn":
        for bit in range(8):
            prefix="" if unit else "xdut."
            bottom=w[f"{prefix}xcdac.b{side}{bit}"]
            for kind,rail,source in (("PMOS","p",.9 if unit else w["vrefp"]),
                                      ("NMOS","n",0 if unit else w["vrefn"])):
                gate=w[f"{prefix}g{side}{rail}{bit}"]
                body=.9 if kind=="PMOS" else 0
                values={"D":bottom,"G":gate,"S":np.zeros_like(t)+source,"B":np.zeros_like(t)+body}
                pairs={a+b:values[a]-values[b] for a,b in (("D","G"),("D","S"),("D","B"),("G","S"),("G","B"),("S","B"))}
                pair=max(pairs,key=lambda k:np.max(np.abs(pairs[k])))
                ix=int(np.argmax(abs(pairs[pair])))
                reference_stress.append(dict(side=side,bit=bit,device=kind,terminal_pair=pair,
                                             peak_abs_v=float(abs(pairs[pair][ix])),time_ns=float(t[ix])))
    info["reference_terminal_stress"]=reference_stress
    info["max_reference_terminal_v"]=max(r["peak_abs_v"] for r in reference_stress)
    if not unit:
        analog_stress=reference_stress.copy()
        for side in "pn":
            snap=json.loads((OUT/"baseline/sar_bootstrap_canvas_flat_8b.json").read_text())
            mapping={"CLKS":w["xdut.sample_int"],"Vin":w["vin"+side],"VOUT":w["xdut.top"+side],
                     "VDD!":w["vdd!"],"gnd!":np.zeros_like(t)}
            for inst in snap["instances"]:
                if inst["lib"]!="tsmcN28":continue
                values={term:mapping[net] if net in mapping else w[f"xdut.xboot{side}.{net}".lower()]
                        for term,net in inst["terms"].items()}
                pairs={a+b:values[a]-values[b] for a,b in (("D","G"),("D","S"),("D","B"),("G","S"),("G","B"),("S","B"))}
                pair=max(pairs,key=lambda k:np.max(abs(pairs[k]))); ix=int(np.argmax(abs(pairs[pair])))
                analog_stress.append(dict(block="bootstrap",side=side,device=inst["name"],terminal_pair=pair,
                                          peak_abs_v=float(abs(pairs[pair][ix])),time_ns=float(t[ix]),limit_v=1.98))
        snap=json.loads((OUT/"baseline/sar_strongarm_t28.json").read_text())
        mapping={"CLK":w["xdut.cmp_clk"],"VINP":w["xdut.topp"],"VINN":w["xdut.topn"],
                 "OUTP":w["xdut.comp_p"],"OUTN":w["xdut.comp_n"],"VDD":w["vdd!"],"VSS":np.zeros_like(t)}
        for inst in snap["instances"]:
            values={term:mapping[net] if net in mapping else w[f"xdut.xcomp.{net}".lower()]
                    for term,net in inst["terms"].items()}
            pairs={a+b:values[a]-values[b] for a,b in (("D","G"),("D","S"),("D","B"),("G","S"),("G","B"),("S","B"))}
            pair=max(pairs,key=lambda k:np.max(abs(pairs[k]))); ix=int(np.argmax(abs(pairs[pair])))
            analog_stress.append(dict(block="comparator",device=inst["name"],terminal_pair=pair,
                                      peak_abs_v=float(abs(pairs[pair][ix])),time_ns=float(t[ix]),limit_v=.99))
        for r in analog_stress:
            r.setdefault("block","reference");r.setdefault("limit_v",.99)
            r["screen_pass"]=r["peak_abs_v"]<=r["limit_v"]
        assert len(analog_stress)==67
        info["analog_stress"]=analog_stress
        info["analog_stress_screen_pass"]=all(r["screen_pass"] for r in analog_stress)
        info["stress_coverage"]="67 analog MOS, six terminal pairs each, all saved times; not all internal logic MOS or lifetime signoff"
        info["source_power"]=[]
        for begin,end in ((0,float(t[-1])),(100,float(t[-1]))):
            if end<=begin:continue
            mask=(t>=begin)&(t<=end);times=t[mask]*1e-9
            sources={"VDD":(.9,"vvdd:p"),"REF_HIGH":(.9,"vrefhigh:p"),"REF_LOW":(0,"vreflow:p"),
                     "SAMPLE":(w["sample"],"vsample:p"),"VINP":(w["vinp_src"],"vvinp:p"),
                     "VINN":(w["vinn_src"],"vvinn:p")}
            power={}
            for key,(voltage,current) in sources.items():
                full=-voltage*w[current]
                integrate=lambda values:float(np.trapezoid(values[mask],times))
                net=integrate(full)
                power[key]=dict(net_j=net,delivered_j=integrate(np.maximum(full,0)),
                                returned_j=-integrate(np.minimum(full,0)),net_mw=net/(times[-1]-times[0])*1e3)
            info["source_power"].append(dict(begin_ns=begin,end_ns=end,sources=power))
    (folder/"analysis.json").write_text(json.dumps(info,indent=2)+"\n")
    if verbose:print(json.dumps(info,indent=2))
    return info


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("name");p.add_argument("--brief",action="store_true"); args=p.parse_args()
    info=measure(args.name,not args.brief)
    if args.brief:
        exclude={"checks","frames","warnings","reference_terminal_stress","analog_stress","source_power","fall_capture_checks","two_phase_checks","two_phase_reference_steps"}
        print(json.dumps({k:v for k,v in info.items() if k not in exclude},indent=2))
