"""Independent physical-array/search checks for the corrected30-draw results."""
import json,hashlib
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_mc/blocks'
def load(f,seed):return json.loads((V/'results'/('sar8mc-%s-s%d-v2'%(f,seed))/'result.json').read_text())
def main():
    capdiff=[];search_width=[]
    for seed in range(4101,4131):
        a=load('cdac',seed);p=a['mismatch_evidence']['selected'];assert len(p)==18 and not any('turbo' in x for x in p)
        assert len(set(x['par_mom'] for x in p.values()))==18
        c=np.array([[a['capacitance_f'][side+str(i)] for i in range(9)] for side in 'PN'])
        assert not np.array_equal(c[0],c[1]);capdiff.append(float(np.max(abs(c[0]/c[1]-1))))
        w=.9*np.sum(c[:,:8]/c.sum(axis=1)[:,None],axis=0)
        assert np.max(abs(w-np.array(a['weights']['differential_weights_v'])))<1e-14
        levels=np.array([np.dot(w,[(code>>i)&1 for i in range(8)]) for code in range(256)])
        dnl=np.diff(levels)/(1.8/256)-1;ep=(levels[-1]-levels[0])/255;inl=(levels-levels[0]-np.arange(256)*ep)/ep
        assert abs(max(abs(dnl))-a['weights']['dac_dnl_abs_max_lsb'])<1e-10
        assert abs(max(abs(inl))-a['weights']['dac_inl_endpoint_abs_max_lsb'])<1e-10
        b=load('comp',seed)
        for probe in b['speed_probes']:
            assert not probe['resolved'] or probe['polarity']==(1 if probe['overdrive_about_estimated_offset_v']>0 else -1)
        q=b['mismatch_evidence']['selected'];assert len(q)>=2 and not any('turbo' in x for x in q)
        assert len(set(json.dumps(v,sort_keys=True) for v in q.values()))>=2
        lo=-.064;hi=.064
        for row in b['records'][2:12]:
            probe=(lo+hi)/2;assert abs(row[1]-probe)<1e-12
            if row[2]>0:hi=probe
            elif row[2]<0:lo=probe
            assert abs(row[4]-lo)<1e-12 and abs(row[5]-hi)<1e-12
        assert abs((lo+hi)/2-b['offset_midpoint_v'])<1e-12;search_width.append(hi-lo)
    assert hashlib.sha256((R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs').read_bytes()).hexdigest()=='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
    r={'samples_per_module':30,'all18_MOM_rows_distinct':True,'all_PN_capacitor_samples_distinct':True,
        'independent_numpy_weight_metrics_agree':True,'search_algorithm_recomputed':True,'B_DUT_unchanged':True,
        'max_PN_relative_cap_difference':max(capdiff),'threshold_interval_width_v_range':[min(search_width),max(search_width)]}
    (V/'validation_v2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
