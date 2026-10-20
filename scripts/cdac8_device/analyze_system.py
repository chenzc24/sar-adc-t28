"""Time-domain and ADC metrics, with explicit ideal reference and raw-error reporting."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
import numpy as np
from common import OUT,LSB,LIMIT,load,dump

def waves(name):
    r=load(f"transient/{name}_result.json");assert r["ok"],r["errors"]
    data=load(f"transient/{name}_waveform.json")
    w={k:np.asarray(v,dtype=float) for k,v in data.items() if isinstance(v,list) and (not v or not isinstance(v[0],dict))}
    assert "time" in w and np.isfinite(w['time']).all() and (np.diff(w["time"])>0).all()
    assert all(len(w[k])==len(w['time']) and np.isfinite(w[k]).all() for k in ('topp','topn','valid','busy'))
    return r,w

def warning(r):
    raw=Path(r["metadata"]["output_dir"])
    log=(raw.parent/"spectre.out").read_text(errors="replace")
    return {"cmi_printed":len(re.findall(r"WARNING \(CMI-",log)),
        "suppressed":sum(map(int,re.findall(r"(\d+) warnings suppressed",log))),
        "lte_relaxations_printed":log.count("WARNING (SPECTRE-16780)"),
        "cmi_instances":sorted(set(re.findall(r"WARNING \(CMI-\d+\): ([^:]+):",log)))}

def at(w,key,ns):return float(np.interp(ns*1e-9,w["time"],w[key]))
def diff(w,ns):return at(w,"topp",ns)-at(w,"topn",ns)
def codes(w,supply=.9):return sum((w[f"dout<{b}>"]>supply/2).astype(int)*(1<<b) for b in range(8))

def grid(w,count):
    desired=(490+100*np.arange(count))*1e-9
    i=np.searchsorted(w["time"],desired).clip(0,len(w["time"])-1)
    prev=np.maximum(i-1,0)
    i=np.where(abs(w["time"][prev]-desired)<abs(w["time"][i]-desired),prev,i)
    assert np.max(abs(w["time"][i]-desired))<1e-12
    assert (w["valid"][i]>.45).all() and (w["busy"][i]<.45).all()
    return i

def balanced():
    rows=[];wa={}
    for name in ("balanced_literal","balanced_nominal","balanced_comparator"):
        r,w=waves(name);wa[name]=w
        row={"name":name,"warnings":warning(r),"codes":[int(codes(w)[i]) for i in grid(w,2)],
             "bottom_msb_range_v":[float(min(w['xcdac.bp7'].min(),w['xcdac.bn7'].min())),float(max(w['xcdac.bp7'].max(),w['xcdac.bn7'].max()))]}
        if name!="balanced_comparator":
            row["held_error_mv"]=1000*(diff(w,570)-.8)
            row["acquisition_error_mv"]=1000*(diff(w,540.8)-.8)
            row["hold_pass"]=abs(row["held_error_mv"])<=LIMIT*1000
        rows.append(row)
    a,b=wa['balanced_literal'],wa['balanced_nominal'];g=np.linspace(400e-9,590e-9,10001)
    delta=np.interp(g,a['time'],a['topp']-a['topn'])-np.interp(g,b['time'],b['topp']-b['topn'])
    correlation={"scope":"nominal fixed-code input-step transient, not MC or all-PVT equivalence",
                 "max_common_grid_mv":float(np.max(np.abs(delta))*1000),"held_difference_uv":(diff(a,570)-diff(b,570))*1e6}
    assert correlation["max_common_grid_mv"]<.001
    result={"rows":rows,"correlation":correlation};dump("transient/summary_balanced.json",result);return result

def system(kind,run_name=None):
    name=run_name or ('ideal_dac' if kind=='ideal' else 'final_'+kind)
    r,w=waves(name);count=1024 if kind=="dynamic" else 256;i=grid(w,count)
    code=codes(w)[i];row={"name":name,"simulator_mode":r['mode'],"samples":count,"warnings":warning(r),"codes":code.tolist()}
    if kind=="static":
        error=code-np.arange(256)
        row.update(code_center_max_error_lsb=int(abs(error).max()),code_center_mismatches=int((error!=0).sum()),
            observed_missing_codes=np.flatnonzero(np.bincount(code,minlength=256)==0).tolist(),
            scope="one stimulus at each code center; not a transition/DNL measurement")
    elif kind in ("dac","ideal"):
        # TOPdiff = sampled Vin - VDAC. No fitted offset/gain in raw INL.
        level=-(w["topp"]-w["topn"])[i];ideal=-.9+np.arange(256)*LSB
        dnl=np.diff(level)/LSB-1;inl=(level-ideal)/LSB
        fit=np.polyfit(np.arange(256),level,1);fitted=level-np.polyval(fit,np.arange(256))
        row.update(levels_v=level.tolist(),dnl_lsb=dnl.tolist(),inl_raw_lsb=inl.tolist(),
            dnl_abs_max_lsb=float(abs(dnl).max()),inl_raw_abs_max_lsb=float(abs(inl).max()),
            inl_fit_abs_max_lsb=float(abs(fitted).max()/LSB),offset_mv=float((fit[1]+.9)*1000),
            gain_error_percent=float((fit[0]/LSB-1)*100),monotonic=bool((np.diff(level)>0).all()))
    else:
        from adctoolbox import analyze_spectrum
        x=-.9+(code+.5)*LSB
        m=analyze_spectrum(x-x.mean(),fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
        # Separate measured SNDR from full-scale-normalized toolbox ENOB.
        tone=10e6*461/1024;ts=(441.05+100*np.arange(count))*1e-9
        ideal=np.clip(np.floor((.9*10**(-1/20)*np.sin(2*np.pi*tone*ts)+.9)/LSB),0,255).astype(int)
        basis=np.column_stack([np.ones(count),np.sin(2*np.pi*tone*ts),np.cos(2*np.pi*tone*ts)])
        fit=np.linalg.lstsq(basis,x,rcond=None)[0]
        row.update(sndr_db=float(m['sndr_dbc']),enob_toolbox_bits=float(m['enob']),
            enob_sndr_bits=float((m['sndr_dbc']-1.76)/6.02),sfdr_db=float(m['sfdr_dbc']),
            coherent_bin=461,input_dbfs=-1,ideal_aperture_ns=41.05,
            ideal_code_mismatches=int((ideal!=code).sum()),
            sinefit_amplitude_v=float(np.hypot(fit[1],fit[2])),
            sinefit_gain_ratio=float(np.hypot(fit[1],fit[2])/(.9*10**(-1/20))),
            effective_fundamental_delay_ns=float(-np.arctan2(fit[2],fit[1])/(2*np.pi*tone)*1e9),
            logical_reference_mismatch_note='Raw logical-clock comparison is not phase-aligned; fit is diagnostic only, never applied before SNDR.',
            enob_target_pass=bool((m['sndr_dbc']-1.76)/6.02>=7))
    dump(f"transient/summary_{kind}.json",row);return {k:v for k,v in row.items() if k not in ('codes','levels_v','dnl_lsb','inl_raw_lsb')}

def pvt():
    rows=[]
    for p in sorted((OUT/'transient').glob('pvt_*_case.json')):
        name=p.stem.removesuffix('_case');case=load('transient/'+p.name);r,w=waves(name);vin=case['parameters']['VDIFF']
        first=1000*(diff(w,470)-vin);second=1000*(diff(w,570)-vin)
        rows.append({'name':name,'supply_v':case['parameters']['SUP'],'temperature_c':case['temperature_c'],
            'corner':case['corner'],'vdiff_v':vin,'acq_first_mv':1000*(diff(w,440.8)-vin),
            'hold_first_mv':first,'hold_second_mv':second,'accuracy_pass':max(abs(first),abs(second))<=LIMIT*1000,
            'warnings':warning(r)})
    assert len(rows)==13
    dump('transient/summary_pvt.json',rows)
    result={'cases':13,'first_and_second_accuracy_pass_count':sum(r['accuracy_pass'] for r in rows),
        'zero_cmi_cases':sum(r['warnings']['cmi_printed']==0 for r in rows),'scope':'5 TT input steps + 8 MOS endpoint steps; TT MOM; not closed-loop PVT'}
    dump('transient/summary_pvt_status.json',result);return result

def integrate():
    _,w=waves('stress_trace');trace=[];peaks=[]
    for step in range(8):
        ns=445.98+5*step;trial=sum((at(w,f'sel1<{b}>',ns)>.45)*(1<<b) for b in range(8))
        expected=.453515625-(-.9+trial*LSB);measured=diff(w,ns)
        trace.append({'bit':7-step,'time_ns':ns,'trial':trial,'ideal_residual_v':expected,'measured_v':measured,'raw_error_mv':1000*(measured-expected)})
    for side in 'pn':
        for bit in range(9):
            key=f'xcdac.b{side}{bit}';indices=np.flatnonzero((w['time']>400e-9)&(w['time']<500e-9))
            ix=indices[np.argmax(w[key][indices])]
            peaks.append({'bank':side+str(bit),'max_v':float(w[key][ix]),'time_ns':float(w['time'][ix]*1e9)})
    dump('transient/bit_settling.json',trace);dump('transient/stress_peaks.json',peaks)
    _,a=waves('precision_loop_conservative');_,b=waves('precision_loop_moderate')
    precision={'decision_residual_max_difference_mv':max(abs(diff(a,445.98+5*j)-diff(b,445.98+5*j))*1000 for j in range(8)),
               'codes_equal':bool((codes(a)[grid(a,2)]==codes(b)[grid(b,2)]).all()),'scope':'two outputs / eight decision instants at one DC input, not all-tone precision signoff'}
    dump('transient/precision.json',precision)
    mask=(a['time']>=400e-9)&(a['time']<=500e-9)
    energy={'scope':'named source energy in mixed fixture, not total ADC power','source_energy_pj':{},
        'reference_p_range_v':[float(a['vrefp'][mask].min()),float(a['vrefp'][mask].max())],
        'reference_n_range_v':[float(a['vrefn'][mask].min()),float(a['vrefn'][mask].max())]}
    for key,v in [('vvdd:p',.9),('vrefhigh:p',.9),('vvcm:p',.45)]:
        energy['source_energy_pj'][key]=float(-v*np.trapezoid(a[key][mask],a['time'][mask])*1e12)
    dump('transient/source_energy.json',energy)
    _,a=waves('literal_loop');_,b=waves('stress_trace');g=np.linspace(400e-9,590e-9,10001)
    delta=np.interp(g,a['time'],a['topp']-a['topn'])-np.interp(g,b['time'],b['topp']-b['topn'])
    correlation={'common_grid_max_mv':float(abs(delta).max()*1000),'codes_equal':bool((codes(a)[grid(a,2)]==codes(b)[grid(b,2)]).all())}
    dump('transient/correlation_loop.json',correlation)
    r,ideal=waves('ideal_input_ss');native=load('transient/summary_pvt.json')
    native=next(x for x in native if x['name']=='pvt_ss_810_-40_800')
    isolated={'ideal_input_acq_first_mv':1000*(diff(ideal,440.8)-.8),'ideal_input_hold_first_mv':1000*(diff(ideal,470)-.8),
              'native_input_hold_first_mv':native['hold_first_mv'],'ideal_input_warnings':warning(r),
              'scope':'only input Bootstrap replaced by 150-ohm ideal relay; same literal native CDAC'}
    dump('transient/input_isolation.json',isolated)
    _,cold=waves('pvt_ss_810_-40_800');trajectory=[]
    for ns in (401.5,405,410,415,420,425,430,435,440.8):
        trajectory.append({'time_ns':ns,'top_p_v':at(cold,'topp',ns),'top_n_v':at(cold,'topn',ns),
            'g_minus_vin_p_v':at(cold,'xbootp.g',ns)-at(cold,'vinp',ns),
            'g_minus_vin_n_v':at(cold,'xbootn.g',ns)-at(cold,'vinn',ns),
            'bottom_p7_v':at(cold,'xcdac.bp7',ns),'bottom_n7_v':at(cold,'xcdac.bn7',ns)})
    dump('transient/cold_sampling_trajectory.json',trajectory)
    scale=[]
    for name in ('cm_scale_500','cm_scale_250','cm_scale_125'):
        r,v=waves(name);keys=[f'xcdac.b{s}{bit}' for s in 'pn' for bit in range(9)]
        scale.append({'name':name,'warnings':warning(r),'codes':codes(v)[grid(v,2)].tolist(),
            'max_bottom_v':float(max(v[k].max() for k in keys)),'min_bottom_v':float(min(v[k].min() for k in keys)),
            'scope':'declared multiplier diagnostic; fractional leaf multipliers not physically realized'})
    dump('transient/summary_cm_scale.json',scale)
    return {'max_comparison_raw_error_mv':max(abs(x['raw_error_mv']) for x in trace),'precision':precision,
            'energy':energy,'closed_loop_correlation':correlation,'input_isolation':isolated,'cm_scale':scale}

def smoke(tag="initial"):
    suffix="" if tag=="initial" else "_"+tag;rows=[]
    for prefix in ("caps_smoke","device_smoke","sar_smoke"):
        name=prefix+suffix;r,w=waves(name);decoded=codes(w)
        row={"name":name,"warnings":warning(r),"codes_after_warmup":[int(np.interp(ns*1e-9,w["time"],decoded)) for ns in (490,590,690,790,890,990)]}
        if prefix=="caps_smoke":
            row["code_step_error_mv"]=[1000*(diff(w,490+i*100)-(.9-i*LSB)) for i in range(6)]
        else:
            row["acquisition_error_mv"]=1000*(diff(w,1040.8)-(at(w,"vinp_src",1040.8)-at(w,"vinn_src",1040.8)))
            row["bottom_msb_range_v"]=[float(min(w["xcdac.bp7"].min(),w["xcdac.bn7"].min())),float(max(w["xcdac.bp7"].max(),w["xcdac.bn7"].max()))]
            if prefix=="device_smoke":row["held_error_mv"]=1000*(diff(w,1070)-.8)
        rows.append(row)
    dump(f"transient/summary_smoke_{tag}.json",rows)
    print(json.dumps(rows,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("smoke","balanced","static","dynamic","dac","ideal","pvt","integration"));p.add_argument("--tag",default="initial");p.add_argument('--run-name');a=p.parse_args()
    if a.stage=="smoke":smoke(a.tag)
    else:print(json.dumps({'balanced':balanced,'pvt':pvt,'integration':integrate}.get(a.stage,lambda:system(a.stage,a.run_name))(),indent=2))
