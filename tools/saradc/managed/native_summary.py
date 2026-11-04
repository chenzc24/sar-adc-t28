"""Bounded all-sample transient summary. Python 2.7/3, no waveform arrays."""
from __future__ import print_function
import argparse,json,os,re

def summarize(path,selected):
    section=None;sweep=None;pending=None;aliases={};values={};names=[];time_value=None;count=0;last=None;stats={};ended=False
    def sample(t):
        for name in selected:
            assert name in values,'Missing selected native signal '+name
            v=values[name];s=stats.setdefault(name,dict(min=v,max=v,sum=0.,first=v,last=v))
            s['min']=min(s['min'],v);s['max']=max(s['max'],v);s['sum']+=v;s['last']=v
    with open(path) as f:
        for raw in f:
            line=raw.strip()
            if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                section=line
                if line=='END':
                    if time_value is not None:sample(time_value);count+=1;last=time_value
                    ended=True;break
                continue
            if not line or section not in ['SWEEP','TRACE','VALUE']:continue
            if section=='SWEEP' and sweep is not None:continue
            if not line.startswith('"'):continue
            _,key,tail=line.split('"',2)
            if section=='SWEEP':sweep=key
            elif section=='TRACE':
                if tail.strip().startswith('GROUP'):pending=key
                else:
                    name=key.replace('\\','').lower();aliases[key]=name;names.append(name)
                    if pending is not None:aliases[pending]=name;pending=None
            elif key==sweep:
                t=float(tail.strip())
                if time_value is not None:
                    assert t>time_value;sample(time_value);count+=1
                time_value=t
            else:
                name=aliases.get(key,key.replace('\\','').lower())
                if name in selected:values[name]=float(tail.strip())
    assert ended and sweep=='time' and count>0
    for s in stats.values():s['sample_mean']=s.pop('sum')/count
    return dict(native_points=count,last_time_s=last,PSF_END=ended,signals=stats,summary_scope='all native points; sample mean is not time-weighted; no ADC qualification')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    recipe=json.load(open(a.run_dir+'/recipe.json'))
    native=[a.run_dir+'/raw/'+s for s in sorted(os.listdir(a.run_dir+'/raw')) if s.endswith('.tran.tran')]
    assert len(native)==1,'Default summary requires exactly one transient analysis'
    result=summarize(native[0],recipe['summary_signals'])
    assert result['last_time_s']>=recipe['expected_stop_s']-max(1e-15,recipe['expected_stop_s']*1e-9)
    result.update(analysis_complete=True,electrical_verdict='not_inferred')
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    print('SUMMARY_OK',result['native_points'])

if __name__=='__main__':main()
