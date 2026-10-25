"""Compare identical circuit at two numerical settings; no simulation launch."""
import json
import numpy as np
from loaded_analyze import ROOT, VERIFY, resolve

def main():
    names=['sar8fix-loaded-ref-ffcold','sar8fix-loaded-ref-screen-ffcold']
    rr=[json.loads((VERIFY/(n+'_analysis.json')).read_text()) for n in names]
    paths=[resolve(n)[1] for n in names]
    stress=[np.loadtxt(p['derived/wave.stress.tsv']) for p in paths]
    assert np.array_equal(stress[0][:,0],stress[1][:,0])
    ds=np.abs(stress[0][:,1]-stress[1][:,1]);worst=int(np.argmax(ds))
    def events(p):
        out={}
        for row in p['derived/wave.events.tsv'].read_text().splitlines():
            n,s,t=row.split();out.setdefault(n+':'+s,[]).append(float(t))
        return out
    ev=[events(p) for p in paths]
    same_events=set(ev[0])==set(ev[1]) and all(len(ev[0][k])==len(ev[1][k]) for k in ev[0])
    dt=max(float(np.max(np.abs(np.array(ev[0][k])-ev[1][k]))) for k in ev[0]) if same_events else None
    en=[r['frames'][1]['supply_reference_average_uw'] for r in rr]
    de=abs(en[1]/en[0]-1)
    code=all(r['all_codes_pass'] and r['all_event_counts_pass'] for r in rr)
    result=dict(runs=names,effective_settings=[r['effective_settings'] for r in rr],
        peak_difference_mv=float(ds[worst]*1000),worst_pair_index=worst,
        all_event_counts_same=same_events,max_event_difference_ps=None if dt is None else dt*1e12,
        second_frame_power_uw=en,power_relative_difference_percent=de*100,
        code_events_pass=code,triage_gate_pass=bool(code and same_events and ds[worst]<1e-4 and dt<5e-12 and de<.005),
        guardrails=dict(peak_difference_mv=.1,event_difference_ps=5,power_difference_percent=.5),
        managed_elapsed_s=[r['simulation_elapsed_s'] for r in rr],
        scope='Different numerical precision; not equal-accuracy speed comparison. Strict runs retained for PVT.')
    (VERIFY/'loaded_numerical_calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
