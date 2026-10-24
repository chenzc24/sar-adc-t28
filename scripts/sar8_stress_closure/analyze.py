"""All-device stress and native reference terminal-current evidence."""
import importlib.util
import sys
import numpy as np
from control import ROOT, OUT, VERIFY, transport
read,dump,sha=transport.read,transport.dump,transport.sha
sys.path.insert(0,str(ROOT/'scripts/sar8_pvt_mismatch'))
spec=importlib.util.spec_from_file_location('closure_checks',ROOT/'scripts/sar8_pvt_mismatch/analyze.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
checks.OUT=OUT;checks.VERIFY=VERIFY


def main(name):
    report,raw=checks.analyze(name)
    ctx=read(OUT/name/'context.json')
    assert len(raw['stress'])==1833*6
    report['stress_detail_scope']='All10998 pairs on1833 MOS; per-model0.99/1.98V screening limits; not foundry signoff'
    dump(VERIFY/(name+'.json'),report)
    w={k:np.asarray(v) for k,v in raw['wave'].items()};t=w['time']*1e9
    required={s.lower() for s in ctx['saved_signals']}
    assert required<=set(w),sorted(required-set(w))
    events=[]
    for side in ['p','n']:
        bot='xdut.xcdac.b'+side+'7'
        mask=(t>140)&(t<146)
        ix=np.flatnonzero(mask)[np.argmin(w[bot][mask])]
        if w[bot][ix]>-.001:continue
        prefix=f'xdut.xcdac.xs{side}7.'
        rows={}
        for mos in ['mn_low','mp_high']:
            currents=[w[prefix+mos+':'+str(i)] for i in range(1,5)]
            rows[mos]=dict(at_min_a=dict(zip('dgsb',[float(c[ix]) for c in currents])),
                max_KCL_abs_a=float(max(abs(sum(currents)))),
                max_terminal_abs_a=float(max(max(abs(c)) for c in currents)))
        events.append(dict(bottom=bot,time_ns=float(t[ix]),bottom_mv=float(w[bot][ix])*1000,
            reference_n_mv=float(w['vrefn'][ix])*1000,reference_p_v=float(w['vrefp'][ix]),currents=rows))
    gates=[f'xdut.g{s}{p}{b}' for s in ['n','p'] for p in ['n','p'] for b in range(8)]
    worst_hi=max((float(max(w[g]-w['vdd!']))*1000,g) for g in gates)
    worst_lo=min((float(min(w[g]))*1000,g) for g in gates)
    metrics=dict(name=name,codes=[f['code'] for f in report['frames']],
        codes_pass=report['static_code_pass'],timing_pass=report['all_timing_pass'],
        idle_pass=report['all_idle_pass'],CMI=report['CMI'],groups=report['groups'],
        full_MOS_count=1833,terminal_pair_count=len(raw['stress']),
        gate_high_excursion_mv=worst_hi,gate_low_excursion_mv=worst_lo,
        events=events,effective_settings=report['effective_settings'],
        held_errors_mv=[f['held_error_v']*1000 for f in report['frames']],
        sample_edges_ns={n:crossings(t,w[n],.495) for n in ['xdut.seq_sample','xdut.sample_int']},
        current_note='D/G/S/B wrapper terminal currents include displacement current; no pure channel/shoot-through attribution',
        qualification='200ns initial screen only; not repair closure')
    dump(VERIFY/(name+'_metrics.json'),metrics)
    keep=(t>140)&(t<146)
    np.savez_compressed(OUT/(name+'_handoff.npz'),**{k:v[keep] for k,v in w.items()})
    print(name,'REF_PEAK',report['groups']['reference']['peak_v'],'EVENTS',events,flush=True)


def crossings(t,v,level):
    result={}
    for direction in ['rise','fall']:
        mask=(v[:-1]<level)&(v[1:]>=level) if direction=='rise' else (v[:-1]>level)&(v[1:]<=level)
        i=np.flatnonzero(mask)
        result[direction]=(t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])).tolist()
    return result


if __name__=='__main__':
    for name in sys.argv[1:]:main(name)
