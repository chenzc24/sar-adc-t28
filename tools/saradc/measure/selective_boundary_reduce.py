"""Same-draw full-transistor boundary diagnostics. Remote Python 2.7 compatible."""
from __future__ import print_function
import argparse,json,os,re,math,shutil
from collections import deque
import reference_short as native
import mc_short_reduce as gross


def vectors(folder):
    paths={k:gross.findone(folder,k) for k in ['process.params','process.values','mismatch.params','mismatch.values']}
    with open(paths['mismatch.params']) as f:
        columns=next(f).split();names=[l.strip().upper() for l in f if l.strip()]
    with open(paths['mismatch.values']) as f:
        assert next(f).strip()=='#1'
        values=[[float(v) for v in l.split()] for l in f if l.strip()]
    assert len(names)==len(values) and len(set(names))==len(names)
    assert all(len(v)==len(columns) and all(not math.isnan(x) and not math.isinf(x) for x in v) for v in values)
    process=[float(x) for line in open(paths['process.values']) if not line.lstrip().startswith(('#',';')) for x in line.split()]
    assert process and all(not math.isnan(x) and not math.isinf(x) for x in process)
    labels=[l.split()[0] for l in open(paths['process.params']) if l.strip() and not l.lstrip().startswith(('#',';'))]
    assert len(labels)==len(process)
    return dict(columns=columns,rows=dict(zip(names,values)),process_labels=labels,process=process),paths


def belongs(name,roots):return any(name==p or name.startswith(p+'.') for p in roots)


def compare_draw(actual,expected,roots):
    wanted={k:v for k,v in expected['rows'].items() if belongs(k,roots)}
    missing=sorted(set(wanted)-set(actual['rows']))
    changed=sorted(k for k in wanted if k in actual['rows'] and actual['rows'][k]!=wanted[k])
    outside=sorted(k for k,v in actual['rows'].items() if k!='XDUT' and not belongs(k,roots) and any(v))
    process_equal=(actual['process_labels']==expected['process_labels'] and actual['process']==expected['process'])
    return dict(valid=process_equal and actual['columns']==expected['columns'] and not missing and not changed and not outside,
        global_equal=process_equal,columns_equal=actual['columns']==expected['columns'],kept_rows=len(wanted),
        missing=missing[:20],changed=changed[:20],outside_nonzero=outside[:20])


def boundary_check(records,frames,pilot):
    assert len(records)==len(frames)
    errors=[];brackets=[]
    for i,(r,f) in enumerate(zip(records,frames)):
        if r['frame']!=i or r['code']!=f['code_98']:errors.append(dict(frame=i,reason='source_native_decode'))
        if r['guard_bad']:errors.append(dict(frame=i,reason='boundary_not_bracketed'))
    if not pilot:
        for start,k in [(2,64),(16,128)]:
            lo=records[start]['input_v'];hi=records[start+1]['input_v']
            if records[start]['code']>=k or records[start+1]['code']<k:errors.append(dict(frame=start,reason='guard'))
            for j in range(start+2,start+10):
                r=records[j]
                if abs(r['input_v']-(lo+hi)/2)>1e-10:errors.append(dict(frame=j,reason='search_sequence'))
                if r['code']>=k:hi=r['input_v']
                else:lo=r['input_v']
            center=(lo+hi)/2
            for j,delta in enumerate([-.25,-.1,.1,.25]):
                r=records[start+10+j]
                if abs(r['input_v']-(center+delta*.00703125))>1e-10:errors.append(dict(frame=start+10+j,reason='probe_sequence'))
                if (r['code']>=k)!=(delta>0):errors.append(dict(frame=start+10+j,reason='boundary_side_or_history'))
                if r['code']!=(k if delta>0 else k-1):errors.append(dict(frame=start+10+j,reason='nonadjacent_boundary_code'))
            brackets.append(dict(boundary=k,low_v=lo,high_v=hi,midpoint_v=center,width_lsb=(hi-lo)/.00703125))
        for idx,delta,expected_code in [(31,-.1,127),(33,.1,128)]:
            if abs(records[idx]['input_v']-(brackets[-1]['midpoint_v']+delta*.00703125))>1e-10:
                errors.append(dict(frame=idx,reason='history_probe_sequence'))
            if records[idx]['code']!=expected_code:errors.append(dict(frame=idx,reason='history_probe_code'))
    return dict(valid=not errors,errors=errors,brackets=brackets,scope='Adaptive static-input conversion boundaries; not full ADC INL or a calibrated comparator Vos')


def analyze(root,out):
    ctx=json.load(open(root+'/inputs/context.json'));expected=json.load(open(root+'/inputs/expected_draw.json'))
    actual,paths=vectors(root+'/raw');mapping=compare_draw(actual,expected,ctx['local_roots'])
    for n,p in paths.items():shutil.copyfile(p,out+'/'+n)
    records=[]
    for line in open(root+'/spectre.out'):
        m=re.search(r'BOUNDARY,([^\r\n]+)',line)
        if m:
            v=[float(x) for x in m.group(1).split(',')];assert len(v)==9
            records.append(dict(frame=int(v[0]),target=int(v[1]),stage=int(v[2]),input_v=v[3],code=int(v[4]),low_v=v[5],high_v=v[6],estimate_v=v[7],guard_bad=int(v[8])))
    assert len(records)==ctx['frames']
    measurements=[];original=native.samples
    # One bounded window for each comparator edge, recorded in the same stream
    # as the existing native event checker. This is excursion, not settled error.
    def tracked(path):
        history=deque();active=[];previous=None;counts={}
        for t,v in original(path):
            td=v['xdut.topp']-v['xdut.topn'];cm=.5*(v['xdut.topp']+v['xdut.topn'])
            history.append((t,td,cm))
            while history and history[0][0]<t-.25e-9:history.popleft()
            if previous:
                pt,pv=previous;a=pv['xdut.cmp_clk']-.5*pv['vdd!'];z=v['xdut.cmp_clk']-.5*v['vdd!']
                if a<=0<z:
                    cross=pt-a/(z-a)*(t-pt);idx=int(math.floor((cross-ctx['frame_origin_s'])/ctx['period_s']))
                    if 0<=idx<ctx['frames']:
                        frac=(cross-pt)/(t-pt);at=(pv['xdut.topp']-pv['xdut.topn'])+frac*(td-pv['xdut.topp']+pv['xdut.topn'])
                        pre=[x for x in history if cross-.2e-9<=x[0]<=cross-.02e-9]
                        item=dict(frame=idx,bit=7-counts.get(idx,0),compare_s=cross,top_at_compare_v=at,
                            top_cm_at_compare_v=cm,pre_200_to_20ps_span_v=max(x[1] for x in pre)-min(x[1] for x in pre) if pre else None,
                            post_100ps_excursion_v=0.,last_post_s=0.)
                        counts[idx]=counts.get(idx,0)+1;measurements.append(item);active.append(item)
            for q in active:
                if 0<=t-q['compare_s']<=.1e-9:
                    q['post_100ps_excursion_v']=max(q['post_100ps_excursion_v'],abs(td-q['top_at_compare_v']))
                    q['last_post_s']=t-q['compare_s']
            active=[q for q in active if t-q['compare_s']<=.1e-9]
            previous=t,v
            yield t,v
    native.samples=tracked
    try:result=native.analyze(root,out,frame_finisher=gross.finish)
    finally:native.samples=original
    check=boundary_check(records,result['frames'],ctx['pilot'])
    timing=result['pass_function_timing'];settling=all(not f['settling_review'] for f in result['frames'])
    result.update(random_evidence=mapping,source_run_id=ctx['source_run_id'],boundary=check,stimulus=records,
        top_interface=measurements,timing_pass=timing,settling_screen_pass=settling,
        pass_diagnostic=mapping['valid'] and timing and settling and check['valid'],
        pilot_pass=mapping['valid'] and timing and settling and check['valid'],
        limitations=['Selected paired cases, not a yield sample','Transient noise and PEX off',
            'Top waveform excursions include kickback and continuing settling; not an independent equilibrium-error measurement',
            'Boundary bisection has finite 0.0625 LSB bracket width','Terminal warnings retained; no SOA qualification'])
    with open(out+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();analyze(a.run_dir,a.output_dir)
