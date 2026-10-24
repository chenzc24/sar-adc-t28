"""Python 2/3 stdlib native-PSF reducer. Read every sample; never delete raw data."""
from __future__ import print_function
import array
import gzip
import hashlib
import json
import os
import sys

def main():
    ctx=json.load(open('context.json')); path='test.raw/tran_perf.tran.tran'
    assert not os.path.exists('reduced.json.gz')
    state={}; series={}; groups={}; pending=None; section=None; sweep=None
    times=array.array('d'); ended=False
    def snapshot():
        assert set(state)==set(series)
        for k in series:series[k].append(state[k])
    with open(path) as f:
        for line in f:
            line=line.strip()
            if line in ('HEADER','TYPE','SWEEP','TRACE','VALUE','END'):
                section=line
                if line=='END':
                    if times:snapshot()
                    ended=True;break
                continue
            if not line or section not in ('SWEEP','TRACE','VALUE'):continue
            if section=='SWEEP' and sweep is not None:continue
            _,key,tail=line.split('"',2)
            if section=='SWEEP':sweep=key
            elif section=='TRACE':
                if tail.strip().startswith('GROUP'):
                    assert tail.strip()=='GROUP 1';pending=key
                else:
                    series[key]=array.array('d')
                    if pending is not None:groups[pending]=key
                    pending=None
            else:
                value=float(tail.strip())
                if key==sweep:
                    if times:snapshot()
                    times.append(value)
                else:state[groups.get(key,key)]=value
    assert ended and sweep=='time' and times[-1]>=ctx['stop_ns']*1e-9-1e-14
    wave={k.replace('\\','').lower():v for k,v in series.items()}
    assert all(len(v)==len(times) for v in wave.values())
    assert all(b>a for a,b in zip(times,times[1:]))
    zeros=array.array('d',[0.])*len(times);cache={};stress=[]
    for d in ctx['stress_devices']:
        for a,b in [('d','s'),('g','s'),('g','d'),('g','b'),('b','d'),('b','s')]:
            na,nb=[d['nodes'][n].lower() for n in (a,b)];key=tuple(sorted((na,nb)))
            if key not in cache:
                va=wave[na] if na!='0' else zeros;vb=wave[nb] if nb!='0' else zeros
                peak,idx=max((abs(x-y),i) for i,(x,y) in enumerate(zip(va,vb)))
                cache[key]=(peak,idx)
            peak,idx=cache[key]
            stress.append(dict(instance=d['instance'],group=d['group'],model=d['model'],terminal=a+b,
                peak_v=peak,time_ns=times[idx]*1e9,limit_v=d['limit_v'],exceed=peak>d['limit_v'],nodes=[na,nb]))
    keep=set(x.lower() for x in ctx['timing_signals'])
    reduced={k:list(wave[k]) for k in sorted(keep)};reduced['time']=list(times)
    # Preserve all saved nodes in a 4-ns native-resolution window around each group maximum.
    windows=[]
    for group in sorted(set(d['group'] for d in stress)):
        worst=max((s for s in stress if s['group']==group),key=lambda s:s['peak_v'])
        lo=(worst['time_ns']-1)*1e-9;hi=(worst['time_ns']+3)*1e-9
        ids=[i for i,t in enumerate(times) if lo<=t<=hi]
        windows.append(dict(group=group,worst=worst,wave=dict([(k,[v[i] for i in ids]) for k,v in wave.items()]+[('time',[times[i] for i in ids])])))
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk:break
            h.update(chunk)
    result=dict(wave=reduced,stress=stress,windows=windows,native_points=len(times),
        native_psf_sha256=h.hexdigest(),native_psf_bytes=os.path.getsize(path),PSF_END=True,
        note='All native samples checked; reduced timing wave is not decimated. Other nodes retained around group maxima.')
    with gzip.open('reduced.json.gz','wb',compresslevel=1) as f:
        f.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode('utf-8'))
    print('REDUCTION_OK',len(times),os.path.getsize('reduced.json.gz'))

if __name__=='__main__':main()
