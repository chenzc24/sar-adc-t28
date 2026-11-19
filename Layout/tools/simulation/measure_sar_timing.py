"""Observe the distributed write-clock arrivals while running the existing ADC acceptance test."""
from __future__ import print_function
import argparse
import json
import os
import reference_short
from native_stream import samples as native_samples


def analyze(run_dir, out_dir):
    ctx=json.load(open(os.path.join(run_dir,"inputs/context.json")))
    aliases={"xdut.xctrl.phi_w":"xdut.sar_phi_w","xdut.xctrl.xtim.pr":"xdut.sar_pr","xdut.xctrl.xtim.nr":"xdut.sar_nr"}
    taps=["xdut.write_at_d%d"%i for i in range(8)]
    names=taps+["xdut.sar_phi_w","xdut.phi_u","xdut.cmp_clk"]
    latch = ["xdut.latch_q", "xdut.latch_qb"] if "LATCH_QB" in ctx.get("extracted_receiver_map", {}) else []
    names += latch
    frames=[{k:[[],[]] for k in names} for i in range(ctx["frames"])]
    rails = {site: dict(vdd_drop_V=0.0, vss_rise_V=0.0, local_span_loss_V=0.0)
             for site in ctx.get("supply_probe_sites", [])}
    def sampled(path):
        prev=None
        for t,v in native_samples(path):
            if ctx["frame_origin_s"] <= t < ctx["frame_origin_s"] + ctx["frames"] * ctx["period_s"]:
                for site, peaks in rails.items():
                    drop = v["vdd!"] - v["xdut.vdd_at_" + site.lower()]
                    bounce = v["xdut.vss_at_" + site.lower()]
                    for key, value in (("vdd_drop_V", drop), ("vss_rise_V", bounce), ("local_span_loss_V", drop + bounce)):
                        if value > peaks[key]:
                            peaks[key] = value
                            peaks[key + "_time_s"] = t
            for key,mapped in aliases.items():
                v[key]=v[mapped]
            now=[v[k]-v["vdd!"]/2 for k in names]
            if prev:
                t0,old=prev
                for k,a,b in zip(names,old,now):
                    if (a>0)==(b>0) or a==b:
                        continue
                    te=t0-a*(t-t0)/(b-a)
                    frame=int((te-ctx["frame_origin_s"])//ctx["period_s"])
                    if 0<=frame<len(frames):
                        frames[frame][k][0 if b>a else 1].append(te)
            prev=(t,now)
            yield t,v
    reference_short.samples=sampled
    result=reference_short.analyze(run_dir,out_dir)
    if rails:
        result["local_supply_extrema"] = rails
    result["limitations"]=[s.replace("No MC/noise/PEX or supply ramp", "SAR-only xRC; no MC, noise or supply ramp") for s in result.get("limitations",[])]
    for frame,edges in zip(result["frames"],frames):
        w=edges["xdut.sar_phi_w"]; u=edges["xdut.phi_u"][0]; c=edges["xdut.cmp_clk"][0]
        rec={"receiver_write_counts":[len(edges[k][0]) for k in taps]}
        if all(len(edges[k][0])==8 for k in taps) and len(u)==len(c)==len(w[0])==8:
            rec["write_skew_ps"]=[(max(edges[k][0][i] for k in taps)-min(edges[k][0][i] for k in taps))*1e12 for i in range(8)]
            rec["write_rise_to_update_rise_ps"]=[(u[i]-w[0][i])*1e12 for i in range(8)]
            rec["update_to_next_compare_ps"]=[(c[i+1]-u[i])*1e12 for i in range(7)]
            if len(w[1])==8:
                rec["write_fall_to_update_rise_ps"]=[(u[i]-w[1][i])*1e12 for i in range(8)]
        frame["extracted_timing"]=rec
        if latch:
            t0 = ctx["frame_origin_s"] + frame["frame"] * ctx["period_s"]
            for pin in latch:
                active = sorted((t, i == 0) for i in (0,1) for t in edges[pin][i]
                                if t0+40e-9 <= t <= t0+90e-9)
                rec[pin.split(".")[-1]] = dict(rises=sum(r for _,r in active),
                    falls=sum(not r for _,r in active), edges_ns=[[(t-t0)*1e9,r] for t,r in active])
    with open(os.path.join(out_dir,"result.json"),"w") as f:
        json.dump(result,f,indent=2);f.write("\n")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--run-dir",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--source-run-dir")
    a=p.parse_args()
    result=analyze(a.source_run_dir or a.run_dir,a.output_dir)
    print("SAR timing",result["all_code_pass"],result["pass_function_timing"])

