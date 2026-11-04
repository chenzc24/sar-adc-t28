"""Separate immutable solver trials; never loosen a live/reference run."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_campaign'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def clone(source,run,profile):
    rec=json.loads(source.read_text());folder=V/run;folder.mkdir()
    for item in rec['inputs']:
        path=R/item['source'];name=item['name'];assert sha(path)==item['sha256']
        if name=='test.scs':
            text=path.read_text();assert text.count('errpreset=conservative')==1
            dest=folder/name;dest.write_text(text.replace('errpreset=conservative','errpreset=moderate'))
        elif name=='context.json':
            ctx=json.loads(path.read_text());ctx.update(run_id=run,solver_profile=profile,solver_reference=rec['run_id'])
            dest=folder/name;write(dest,ctx);rec['test_conditions']=ctx
        else:continue
        item.update(source=dest.relative_to(R).as_posix(),sha256=sha(dest))
    if profile=='mm':rec['spectre_args']=[x.replace('+preset=cx','+preset=mx') for x in rec['spectre_args']]
    rec['run_id']=run;rec['resources']['queue_timeout_seconds']=86400
    write(R/'management/recipes'/(run+'.yaml'),rec)
def main():
    m=json.loads((V/'manifest.json').read_text());profiles={}
    for label in ['a','b']:
        profiles[label]={}
        for profile in ['cm','mm']:
            d=dict(bench='sar8camp-%s-%s-bench-v1'%(label,profile),points={})
            clone(R/'management/recipes'/('sar8ab-phase60-'+label+'-tt-v1.yaml'),d['bench'],profile)
            for point in ['tt','ssc','ssh','ffc','ffh']:
                key='dynamic' if point=='tt' else 'screen'
                source=m['labels'][label]['points'][point][key]
                run=source.replace('-v1','-'+profile+'-v1');d['points'][point]={key:run}
                clone(R/'management/recipes'/(source+'.yaml'),run,profile)
            profiles[label][profile]=d
    write(V/'speed_profiles.json',profiles)
    print('Prepared24 conditional solver benchmark/priority cases.')
if __name__=='__main__':main()
