"""Native streaming TT A/B measurements; Python2.7/3, no complete-waveform arrays."""
from __future__ import print_function
import argparse,bisect,csv,json,os,re

EVENTS={'sample':'sample','sample_int':'xdut.sample_int','seq_sample':'xdut.seq_sample',
        'cmp':'xdut.cmp_clk','write':'xdut.xctrl.phi_w','update':'xdut.phi_u','cap':'xdut.xref.cap_clk'}

def samples(path):
    section=None;sweep=None;pending=None;aliases={};values={};t=None;ended=False
    with open(path) as f:
        for raw in f:
            line=raw.strip()
            if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                section=line
                if line=='END':
                    if t is not None:yield t,dict(values)
                    ended=True;break
                continue
            if section not in ['SWEEP','TRACE','VALUE'] or not line.startswith('"'):continue
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
                    yield t,dict(values)
                t=new
            else:values[aliases.get(key,key.replace('\\','').lower())]=float(tail.strip())
    assert ended and sweep=='time','Incomplete native file'

def finalize(frame,rows,events,ctx):
    times=[r[0] for r in rows];base=ctx['frame_origin_s']+frame*1e-7
    def at(t):
        j=bisect.bisect_left(times,t)
        if j==0:return rows[0]
        if j>=len(rows):return rows[-1]
        a,b=rows[j-1],rows[j];f=(t-a[0])/(b[0]-a[0])
        return [t]+[a[k]+f*(b[k]-a[k]) for k in range(1,4)]+[a[4] if f<.5 else b[4]]
    def edge(key,d):return [e['time_s'] for e in events if e['signal']==key and e['direction']==d]
    close=edge('seq_sample',-1);si=edge('sample_int',-1);ext=edge('sample',-1)
    cr=edge('cmp',1);wr=edge('write',1);up=edge('update',1);cap=edge('cap',1)
    result=dict(frame=frame,expected_code=ctx['expected_codes'][frame],code_98=int(at(base+98e-9)[4]),
        code_90=int(at(base+90e-9)[4]),events=events,counts=[len(cr),len(wr),len(up),len(cap)],
        sample_int_close_s=si,seq_sample_close_s=close,external_close_s=ext)
    result['code_pass']=result['code_98']==result['expected_code']
    result['output_stable_90_98']=all(int(r[4])==result['code_98'] for r in rows if base+90e-9<=r[0]<=base+98e-9)
    result['ordered_8_cycles']=len(cr)==len(wr)==len(up)==8 and all(cr[i]<wr[i]<up[i] for i in range(8)) and all(up[i]<cr[i+1] for i in range(7))
    if len(close)==1:
        c=close[0];pre=at(c-1e-12);hold=at(c+.2e-9)
        # rows: time, source differential, actual input differential, top differential, code.
        result.update(preclose_error_source_v=pre[3]-pre[1],preclose_error_pin_v=pre[3]-pre[2],
            hold_200ps_error_v=hold[3]-at(c)[1],hold_200ps_has_update=any(c<=u<=c+.2e-9 for u in up),
            acquisition_last_outside_quarter_lsb_s=max([r[0] for r in rows if base+1e-9<r[0]<c and abs(r[3]-r[1])>ctx['LSB']*.25] or [base+1e-9]),
            conversion_ns=(up[-1]-c)*1e9 if up else None)
    tails=[]
    for i,u in enumerate(up):
        nextcmp=next((c for c in cr if c>u),None)
        if nextcmp is None:continue
        end=nextcmp-20e-12;window=[r for r in rows if u<=r[0]<=end]
        if not window:continue
        target=at(end)[3];out=[r[0] for r in window if abs(r[3]-target)>.25*ctx['LSB']]
        last=max(out) if out else u
        tails.append(dict(update_index=i,update_s=u,next_cmp_s=nextcmp,reference_top_diff_v=target,
            last_outside_band_s=last,quiet_margin_ps=(end-last)*1e12,settling_after_update_ps=(last-u)*1e12,
            scope='relative to measured pre-next-compare value; not ideal DAC accuracy'))
    result['dac_tail_diagnostics']=tails
    result['timing_pass']=result['ordered_8_cycles'] and len(cap)==16 and result['output_stable_90_98'] and len(close)==len(si)==len(ext)==1 and bool(up) and up[-1]<base+90e-9
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.run_dir+'/inputs/context.json'));paths=[a.run_dir+'/raw/'+s for s in os.listdir(a.run_dir+'/raw') if s.endswith('.tran.tran')];assert len(paths)==1
    output=[];rows=[];ev=[];prev=None;active=0;points=0;lastplot=-1.;native98={};precharge_last=None;precharge_points=0
    plot=open(a.output_dir+'/timeline.csv','w');writer=csv.writer(plot)
    cols=['time_s','source_diff_v','top_diff_v','sample','sample_int','seq_sample','cmp','write','update','cap','bootp_vgs','bootn_vgs','code']
    writer.writerow(cols)
    for t,v in samples(paths[0]):
        assert all(s in v for s in ctx['signals'])
        points+=1
        if t < ctx['frame_origin_s']:
            precharge_points+=1
            precharge_last=dict(time_s=t,sample=v['sample'],seq_sample=v['xdut.seq_sample'],
                bootp_charge_v=v['xdut.xbootp.btop']-v['xdut.xbootp.bbot'],
                bootn_charge_v=v['xdut.xbootn.btop']-v['xdut.xbootn.bbot'],
                bootp_gate_v=v['xdut.xbootp.g'],bootn_gate_v=v['xdut.xbootn.g'])
            continue
        frame=min(9,int((t-ctx['frame_origin_s']+1e-16)/1e-7))
        if frame!=active:
            output.append(finalize(active,rows,ev,ctx));rows=[];ev=[];active=frame
        code=sum((1<<b) for b in range(8) if v['d%d'%b]>.45)
        rows.append((t,v['vinp_src']-v['vinn_src'],v['vinp']-v['vinn'],v['xdut.topp']-v['xdut.topn'],code))
        derived=dict((name,v[node]) for name,node in EVENTS.items())
        derived.update(bootp_vgs=v['xdut.xbootp.g']-v['vinp'],bootn_vgs=v['xdut.xbootn.g']-v['vinn'])
        if prev:
            pt,pd=prev
            for name,x in derived.items():
                y=pd[name]
                if (y<.45<=x) or (y>.45>=x):
                    cross=pt+(.45-y)/(x-y)*(t-pt)
                    ev.append(dict(signal=name,time_s=cross,direction=1 if x>y else -1))
        prev=(t,derived)
        if t-lastplot>=.1e-9:
            writer.writerow([t,rows[-1][1],rows[-1][3]]+[derived[k] for k in cols[3:-1]]+[code]);lastplot=t
    output.append(finalize(active,rows,ev,ctx));plot.close()
    assert len(output)==10 and t>=ctx['expected_stop_s']-1e-14
    settings={};warnings=set();observers=[]
    with open(a.run_dir+'/spectre.out') as f:
        for line in f:
            m=re.search(r'R4MEAS,([^\r\n]+)',line)
            if m:observers.append([float(s) for s in m.group(1).split(',')])
            warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
            for key in ['maxstep','reltol','abstol(V)','abstol(I)','method','errpreset']:
                m=re.match(r'\s*'+re.escape(key)+r' = (.+)',line)
                if m:settings[key]=m.group(1).strip()
    assert len(observers)==10
    for r,o in zip(output,observers):
        assert int(o[0])==r['frame'] and int(o[1])==r['code_98'],'Native/event code disagreement'
        # Counts have different reset boundaries if SAMPLE_INT glitches; report rather than hide.
        r['observer_counts']=[int(x) for x in o[2:6]];r['observer_valid']=bool(o[7])
        r['count_crosscheck']=r['counts']==r['observer_counts']
    result=dict(analysis_complete=True,precharge_last=precharge_last,precharge_points=precharge_points,startup_code_pass=output[0]['code_pass'],startup_timing_pass=output[0]['timing_pass'] and output[0]['count_crosscheck'],all_code_pass=all(r['code_pass'] for r in output),context=ctx,frames=output,native_points=points,native_end_s=t,
        native_event_code_crosscheck=True,steady_code_pass=all(r['code_pass'] for r in output[1:]),
        steady_timing_pass=all(r['timing_pass'] and r['count_crosscheck'] for r in output[1:]),
        warning_codes=sorted(warnings),effective_settings=settings,electrical_verdict='deferred_not_qualified',
        plotted_samples='decimated at >=100ps; measurements use full native points',
        limitations=['Low-first DC initialized startup; no supply ramp or POR qualification','VGS0.45 crossings are diagnostic, not transistor turnoff thresholds','DAC tail uses measured precompare reference, not ideal accuracy'])
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    print('AB_ANALYSIS_COMPLETE',ctx['label'])
if __name__=='__main__':main()
