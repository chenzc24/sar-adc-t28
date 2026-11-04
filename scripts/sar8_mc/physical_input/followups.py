"""Small retained-sample diagnostic controls; no full mismatch expansion."""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';S=R/'scripts/sar8_mc/physical_input';sys.path.insert(0,str(R/'scripts/management'))
import execution
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make(parent,run,kind):
    old=json.loads((R/'management/recipes'/(parent+'.yaml')).read_text());rec=copy.deepcopy(old);p=V/run;p.mkdir(exist_ok=False)
    source=V/parent;t=(source/'test.scs').read_text();ctx=json.loads((source/'context.json').read_text());ex=json.loads((source/'expected_mismatch.json').read_text())
    ctx.update(run_id=run,diagnostic=kind,parent_run_id=parent)
    if kind=='nominal_guard':
        t=t.replace('sar8_phys_search cm=0.45','sar8_phys_search cm=0.45 range_v=0.0000625 steps=0').replace('stop=2259n','stop=259n')
        ctx.update(cycles=2,search_steps=0,search_range_v=.0000625,stop_s=259e-9)
    elif kind=='input_pair_nominal':
        assert 'ignore=[XHOLD]' in t
        t=t.replace('ignore=[XHOLD]','ignore=[XHOLD XCMP.MNINN XCMP.MNINP] usesamesequence=yes')
        ctx['nominalized_instances']=['XCMP.MNINN','XCMP.MNINP']
        for name in ctx['nominalized_instances']:assert name in ex['rows'];del ex['rows'][name]
        ex['nominalized_instances']=ctx['nominalized_instances']
    elif kind in ['regen_n','regen_p']:
        prefix='MNLAT' if kind=='regen_n' else 'MPLAT'
        pair=['XCMP.'+prefix+side for side in 'NP']
        ignore='ignore=[XHOLD XCMP.MNINN XCMP.MNINP]'
        lines=t.splitlines(keepends=True)
        indices=[i for i,line in enumerate(lines) if line.startswith('mc montecarlo ') and ignore in line]
        assert len(indices)==1
        i=indices[0]
        lines[i]=lines[i].replace(ignore,ignore[:-1]+' '+' '.join(pair)+']')
        t=''.join(lines)
        for name in pair:del ex['rows'][name]
        assert len(ex['rows'])==87
        ctx['nominalized_instances']=ctx['nominalized_instances']+pair
        ex['nominalized_instances']=ctx['nominalized_instances']
    elif kind in ['input_width_x4','input_width_x2']:
        # One independent geometry variable, with derived diffusion geometry.
        factor=4 if kind=='input_width_x4' else 2
        replacement=[('w=1u','w=%du'%factor),('ad=7.5e-14','ad=%.10g'%(7.5e-14*factor)),('as=7.5e-14','as=%.10g'%(7.5e-14*factor)),
          ('pd=2.15u','pd=%.10gu'%(2*factor+.15)),('ps=2.15u','ps=%.10gu'%(2*factor+.15)),('nrd=0.289519','nrd=%.10g'%(.289519/factor)),('nrs=0.289519','nrs=%.10g'%(.289519/factor))]
        for name in ['MNINN','MNINP']:
            pattern=r'(?ms)(^\s*'+name+r' \([^\n]+.*?)(?=^\s*(?:MN|MP)\w+ \(|^ends )'
            m=re.search(pattern,t);assert m,name;row=m[1]
            for old_value,new_value in replacement:
                assert row.count(old_value)==1,(name,old_value);row=row.replace(old_value,new_value)
            t=t[:m.start(1)]+row+t[m.end(1):]
        ctx.update(input_pair_width_scale=factor,derived_geometry='ad/as proportional W; pd/ps=2W+150nm; diffusion squares inverse W; L/nf/multi unchanged')
        rec['resources']['max_output_mib']=768
    elif kind=='tight_reltol':
        assert t.count('reltol=1e-6')==1;t=t.replace('reltol=1e-6','reltol=1e-7');ctx.update(reltol=1e-7,only_solver_change='reltol1e-6 to1e-7');rec['resources']['max_output_mib']=1024
    else:raise ValueError(kind)
    (p/'test.scs').write_text(t);(p/'context.json').write_text(json.dumps(ctx,indent=2)+'\n');(p/'expected_mismatch.json').write_text(json.dumps(ex,indent=2)+'\n')
    mapping={'test.scs':p/'test.scs','context.json':p/'context.json','expected_mismatch.json':p/'expected_mismatch.json','reduce.py':S/'reduce_flexible.py'}
    rec.update(run_id=run,test_conditions=ctx,expected_stop_s=ctx['stop_s']);rec['inputs']=[{'source':mapping.get(f['name'],R/f['source']).relative_to(R).as_posix(),'name':f['name'],'sha256':sha(mapping.get(f['name'],R/f['source']))} for f in rec['inputs']]
    recipe=R/'management/recipes'/(run+'.yaml');recipe.write_text(json.dumps(rec,indent=2)+'\n');return recipe
def main():
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['controls','width4','width2','accuracy','regen']);ap.add_argument('--register',action='store_true');a=ap.parse_args();runs=[]
    if a.kind=='controls':
        jobs=[('sar8phys-nominal-stiff-v2','sar8phys-nominal-guard-v3','nominal_guard')]+[('sar8phys-s%d-hold-v2'%seed,'sar8phys-s%d-noinputmm-v1'%seed,'input_pair_nominal') for seed in [4121,4124]]
    elif a.kind=='regen':jobs=[('sar8phys-s%d-noinputmm-v1'%seed,'sar8phys-s%d-regen%s-v1'%(seed,side),'regen_'+side) for seed in [4121,4124] for side in 'np']
    elif a.kind=='width4':jobs=[('sar8phys-'+tag+'-hold-v2','sar8phys-'+tag+'-w4-v1','input_width_x4') for tag in ['nominal','s4121','s4124']]
    elif a.kind=='width2':jobs=[('sar8phys-'+tag+'-hold-v2','sar8phys-'+tag+'-w2-v1','input_width_x2') for tag in ['nominal','s4121','s4124']]
    else:jobs=[('sar8phys-nominal-hold-v2','sar8phys-nominal-hold-rt7-v1','tight_reltol')]
    for parent,run,kind in jobs:
        recipe=make(parent,run,kind);runs.append(run)
        if a.register:print('Registered',run,json.dumps(execution.register(recipe.relative_to(R))),flush=True)
    (V/('followup_'+a.kind+'_manifest.json')).write_text(json.dumps({'runs':runs},indent=2)+'\n');print(json.dumps({'prepared':runs}))
if __name__=='__main__':main()
