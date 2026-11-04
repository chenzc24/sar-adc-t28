"""Python2.7/3 bounded native PSF and VA-record cross-check. No waveform arrays."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re

FIELDS=['frame','code','compares','writes','updates','captures','early_code','valid',
        'rail_error_v','aperture_time_s','aperture_source_v','held_diff_v','final_top_diff_v','conversion_s']


def native_frames(path, frames):
    section=None; sweep=None; pending=None; aliases={}; values={}; t=None; result=[]; count=0; ended=False
    def sample(time):
        index=int(round((time-98e-9)/100e-9))
        if 0 <= index < frames and abs(time-(98+100*index)*1e-9)<1e-13:
            code=sum((1<<b) for b in range(8) if values['d%d'%b]>.45)
            result.append(dict(frame=index,time_s=time,code=code,input_v=values['vinp_src']-values['vinn_src']))
    with open(path) as f:
        for raw in f:
            line=raw.strip()
            if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                section=line
                if line=='END':
                    if t is not None: sample(t);count+=1
                    ended=True;break
                continue
            if not line.startswith('"') or section not in ['SWEEP','TRACE','VALUE']:continue
            _,key,tail=line.split('"',2)
            if section=='SWEEP':
                if sweep is None:sweep=key
            elif section=='TRACE':
                if tail.strip().startswith('GROUP'):pending=key
                else:
                    name=key.replace('\\','').lower();aliases[key]=name
                    if pending is not None:aliases[pending]=name;pending=None
            elif key==sweep:
                new=float(tail.strip())
                if t is not None:
                    assert new>t
                    sample(t);count+=1
                t=new
            else:
                name=aliases.get(key,key.replace('\\','').lower())
                if name in ['d%d'%b for b in range(8)]+['vinp_src','vinn_src']:values[name]=float(tail.strip())
    assert ended and sweep=='time'
    assert [x['frame'] for x in result]==list(range(frames)), 'Native frame coverage'
    return result, count, t


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.run_dir+'/inputs/context.json'))
    assert hashlib.sha256(open(a.run_dir+'/inputs/dut.scs','rb').read()).hexdigest()==ctx['dut_sha256']
    logs=dict((k,[]) for k in ['R4MEAS','R4SEARCH','R4CENTER','R4THR','R4STATIC_DONE'])
    warnings=set(); settings={};diagnostics=[];versions=[]
    with open(a.run_dir+'/spectre.out') as f:
        for line in f:
            match=re.search(r'(R4MEAS|R4SEARCH|R4CENTER|R4THR|R4STATIC_DONE),([^\r\n]+)',line)
            if match:logs[match.group(1)].append([s.strip() for s in match.group(2).split(',')])
            warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
            if re.search(r'CMI-|LTE.*(?:relax|fail)|convergence failure|relax.*LTE',line,re.I):
                if len(diagnostics)<80:diagnostics.append(line.strip())
            if 'Version ' in line or 'spectre completes with' in line:versions.append(line.strip())
            for key in ['maxstep','reltol','abstol(V)','abstol(I)','method','errpreset','lteratio','relref']:
                m=re.match(r'\s*'+re.escape(key)+r' = (.+)$',line)
                if m:settings[key]=m.group(1).strip()
    rows=[]
    for vals in logs['R4MEAS']:
        assert len(vals)==len(FIELDS)
        rows.append(dict(zip(FIELDS,[int(v) if i<8 else float(v) for i,v in enumerate(vals)])))
    assert [r['frame'] for r in rows]==list(range(ctx['frames']))
    paths=[a.run_dir+'/raw/'+s for s in os.listdir(a.run_dir+'/raw') if s.endswith('.tran.tran')]
    assert len(paths)==1
    native,points,last=native_frames(paths[0],ctx['frames'])
    assert last>=ctx['stop_s']-1e-14
    assert [r['code'] for r in rows]==[r['code'] for r in native]
    thresholds=[dict(k=int(k),lower_v=float(lo),upper_v=float(hi),status=int(s)) for k,lo,hi,s in logs['R4THR']]
    centers=[dict(expected=int(k),input_v=float(v),code=int(c)) for k,v,c in logs['R4CENTER']]
    assert [r['k'] for r in thresholds]==list(range(ctx['first'],ctx['last']+1))
    assert [r['expected'] for r in centers]==list(range(ctx['first']-1,ctx['last']+1))
    assert logs['R4STATIC_DONE']==[[str(ctx['first']),str(ctx['last'])]]
    assert len(logs['R4SEARCH'])==ctx['frames']-ctx['warmup']
    for frame,k,phase,vin,code in logs['R4SEARCH']:
        frame=int(frame); vin=float(vin)
        assert int(code)==rows[frame]['code']
        assert abs(native[frame]['input_v']-vin)<1e-9
        assert abs(rows[frame]['aperture_source_v']-vin)<1e-9
    measured=rows[ctx['warmup']:]
    bad=[r['frame'] for r in measured if not r['valid'] or not 0<r['conversion_s']<60e-9]
    bracket_pass=all(r['status']==0 and 0<r['upper_v']-r['lower_v']<=1.8/256/128+1e-10 for r in thresholds)
    center_pass=all(r['expected']==r['code'] for r in centers)
    monotonic=all(a1['upper_v']<b1['lower_v'] for a1,b1 in zip(thresholds,thresholds[1:]))
    result=dict(analysis_complete=True,context=ctx,native_points=points,native_last_time_s=last,
        native_decode_crosscheck=True,frames=rows,startup_frames=rows[:ctx['warmup']],
        thresholds=thresholds,centers=centers,invalid_steady_frames=bad,
        center_pass=center_pass,bracket_pass=bracket_pass,monotonic_pass=monotonic,
        functional_pass=center_pass and bracket_pass and monotonic and not bad,
        max_conversion_ns=max(r['conversion_s'] for r in measured)*1e9,
        warning_codes=sorted(warnings),diagnostic_examples=diagnostics,effective_settings=settings,
        simulator_lines=versions,electrical_verdict='deferred_not_qualified',
        scope='TT local boundaries; not full-code unless combined1..255; no FFT/PVT/MC claim')
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    print('ANALYSIS_COMPLETE functional_pass=%s'%result['functional_pass'])


if __name__=='__main__':main()
