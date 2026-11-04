"""Independent search arithmetic and exact one-variable circuit diff checks."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input'
def strip_input_rows(t):
    for name in ['MNINN','MNINP']:
        p=r'(?ms)(^\s*'+name+r' \([^\n]+.*?)(?=^\s*(?:MN|MP)\w+ \(|^ends )'
        t,n=re.subn(p,'<'+name+'>\n',t);assert n==1
    return t
def main():
    checked=0
    for tag in ['nominal','s4121','s4124']:
        parent='sar8phys-'+tag+'-hold-v2';candidate='sar8phys-'+tag+'-w2-v1'
        a=(V/parent/'test.scs').read_text();b=(V/candidate/'test.scs').read_text();assert strip_input_rows(a)==strip_input_rows(b)
        assert len(re.findall(r'(?m)^\s*MNIN[NP] .*\bw=2u\b',b))==2
        for key in ['clock_sources.scs','held_search.va','library_include.scs']:
            # Content is shared from the same frozen package, not a new driver.
            recs=[json.loads((R/'management/recipes'/(run+'.yaml')).read_text()) for run in [parent,candidate]]
            assert next(x['sha256'] for x in recs[0]['inputs'] if x['name']==key)==next(x['sha256'] for x in recs[1]['inputs'] if x['name']==key)
        checked+=1
    recomputed=[];invalid=[]
    for p in sorted((V/'results').glob('*/result.json')):
        d=json.loads(p.read_text());c=d['context'];rows=d['records'];assert d['native_event_crosscheck'] and d['sample_mapping']['identical']
        assert len(d['pulses'])==c['cycles']*8
        if c['search_steps']==0:
            assert rows[0][2]==-1 and rows[1][2]==1 and rows[0][1]==-c['search_range_v'] and rows[1][1]==c['search_range_v'];recomputed.append(c['run_id']);continue
        lo=-c['search_range_v'];hi=c['search_range_v'];hl=lo;hh=hi
        for row in rows[2:12]:
            assert abs(row[1]-(lo+hi)/2)<1e-12
            if row[2]>0:hi=row[1];hh=row[5]
            elif row[2]<0:lo=row[1];hl=row[5]
            assert abs(row[3]-lo)<1e-12 and abs(row[4]-hi)<1e-12
        assert abs((hl+hh)/2-d['held_offset_midpoint_v'])<1e-12
        if d['threshold_valid']:recomputed.append(c['run_id'])
        else:invalid.append(c['run_id'])
    assert invalid==['sar8phys-nominal-stiff-v2'],invalid
    tight=(V/'sar8phys-nominal-hold-rt7-v1/test.scs').read_text();parent=(V/'sar8phys-nominal-hold-v2/test.scs').read_text();assert tight.replace('reltol=1e-7','reltol=1e-6')==parent
    h=hashlib.sha256((R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs').read_bytes()).hexdigest();assert h=='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
    out={'width2_exactly_two_input_rows_changed':checked,'other_circuit_text_and_drivers_unchanged':True,'source_search_arithmetic_recomputed':recomputed,
      'invalid_thresholds_preserved':invalid,'tight_run_only_solver_reltol_changed':True,'frozen_B_unchanged':True}
    (V/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
