"""Leakage and ON differential resistance at common external biases."""
import sys
import re
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha
from prepare import DCNAMES
sys.path.insert(0,str(ROOT/'scripts/sar8_ref_load'))
from native import load

def main():
    rows=[]
    for name in DCNAMES:
        folder=OUT/name;ctx=read(folder/'context.json');receipt=read(folder/'receipt.json')
        raw=folder/'native/test.raw/dc_iv.dc';assert sha(raw)==receipt['native_files']['test.raw/dc_iv.dc']
        log=(folder/'native/spectre.out').read_text();status=(folder/'native/test.raw/logStatus').read_text()
        assert 'spectre completes with 0 errors' in log and re.search(r'dc_iv\s+PASS',status)
        w=load(raw);assert np.allclose(w['delta'],[-.001,0,.001],rtol=0,atol=1e-12)
        # Current conservation and equal frozen leakage across the independent Ron sweep.
        for dev in ['xoffn.mn_low','xoffn.mp_high','xoffp.mn_low','xoffp.mp_high','mronn','mronp']:
            assert np.max(abs(sum(w[dev+':'+str(i)] for i in range(1,5))))<1e-10
        leak={side:float(w['xoff'+side+'.mp_high:3'][1]*1e6) for side in ['n','p']}
        ron={side:float(.002/(w['mron'+side+':1'][2]-w['mron'+side+':1'][0])) for side in ['n','p']}
        assert all(v>0 for v in ron.values()) and all(v>0 for v in leak.values())
        row=dict(name=name,length_nm=ctx['length_nm'],off_N_pair_high_rail_ua=leak['n'],
          off_P_pair_high_rail_ua=leak['p'],estimated_array_rail_load_ua=(leak['n']+leak['p'])*255/128,
          Ron_bit7_ohm=ron,Ron_bit0_ohm={k:v*128 for k,v in ron.items()},
          native_psf_sha256=sha(raw),CMI='WARNING (CMI-' in log,
          effective_settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1]
             for k in ['reltol','abstol(V)','abstol(I)','temp']})
        rows.append(row)
    prior=read(ROOT/'verification/sar8_ref_load/pair_ffhot.json')['at_delta0']
    assert abs(rows[0]['off_N_pair_high_rail_ua']-prior['actual_n']['high_load_ua'])<.002
    assert abs(rows[0]['off_P_pair_high_rail_ua']-prior['actual_p']['high_load_ua'])<.002
    candidates=[r for r in rows if r['estimated_array_rail_load_ua']<=10]
    chosen=min(candidates,key=lambda r:r['length_nm']) if candidates else min(rows,key=lambda r:r['estimated_array_rail_load_ua'])
    dump(VERIFY/'dc_results.json',dict(rows=rows,
      estimate_scope='Fixed-bias array estimate: each complementary state totals multi765, b7 probe multi384. Neglects per-bit gate bias variation and reference-source feedback; integrated result is authoritative.',
      leakage_target_ua=10,Ron_scope='Central derivative over +/-1mV external VDS, ON gate0/.99V, measured hot reference/body biases. Both transistor sizes fixed. Not full-swing large-signal Ron.'))
    dump(VERIFY/'selection.json',dict(selected_length_nm=chosen['length_nm'],screen_target_met=bool(candidates),
      rationale='Shortest scanned length meeting provisional 10uA/rail fixed-bias target; hence lower Ron and gate loading than longer candidates. Integration still required.',
      selected_metrics=chosen))
    for row in rows:print(row)
    print('Selected',chosen['length_nm'])

if __name__=='__main__':main()
