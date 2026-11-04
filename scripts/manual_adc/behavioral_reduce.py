"""Small native streaming checker; accepts Python 2.7 and 3. No third-party libs."""
from __future__ import print_function
import argparse, json, os, gzip
from reduce import frames, norm


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();cfg=json.load(open(os.path.join(a.run_dir,'inputs','measure.json')))
    state=json.load(open(os.path.join(a.run_dir,'simulation.state.json')))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):
        raise ValueError('Native simulation did not succeed')
    sources=[os.path.join(a.run_dir,'raw',s) for s in os.listdir(os.path.join(a.run_dir,'raw')) if s.endswith('.tran.tran')]
    if len(sources)!=1:raise ValueError('expected one native transient')
    names=[norm(s) for s in cfg['signals']];prev=None;count=0;last_export=-1;edges={};samples=[]
    targets=[(111e-9+i*100e-9,c) for i,c in enumerate(cfg['codes'])]
    checkpoints=[3.6e-9,5.5e-9,55e-9,63e-9,70e-9];probe=[];cm=[];fault_peak=0;abort_clock_edges=[]
    fout=gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb')
    fout.write(('time,'+','.join(names)+'\n').encode('ascii'))
    for t,v in frames(sources[0]):
        if set(names)-set(v):raise ValueError('missing saved nodes')
        count+=1;fault_peak=max(fault_peak,v['fault'])
        if prev:
            for name in ['xadc.cmpck','eoc','xabort.cmpck']:
                if prev[1][name]<.45<=v[name]:
                    when=prev[0]+(t-prev[0])*(.45-prev[1][name])/(v[name]-prev[1][name])
                    edges.setdefault(name,[]).append(when)
                    if name=='eoc':cm.append({'time_s':when,'cm_V':(v['xadc.topp']+v['xadc.topn'])/2,'residual_V':v['xadc.topp']-v['xadc.topn']})
            while targets and t>=targets[0][0]:
                at,expected=targets.pop(0);row=prev[1]
                actual=sum(1<<i for i in range(8) if row['do_'+str(i)]>.45)
                samples.append({'time_s':at,'expected':expected,'actual':actual})
            while checkpoints and t>=checkpoints[0]:
                at=checkpoints.pop(0);probe.append({'time_s':at,'values':{k:prev[1][k] for k in ['cop','con','badfault','timeoutfault','abusy','aeoc','afault']}})
        if t-last_export>=50e-12 or prev is None:
            fout.write((','.join(['%.12g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'));last_export=t
        prev=(t,v)
    fout.close()
    clocks=edges.get('xadc.cmpck',[]);done=edges.get('eoc',[])
    frame_counts=[sum(50e-9+i*100e-9<x<110e-9+i*100e-9 for x in clocks) for i in range(8)]
    bytime={int(round(r['time_s']*1e10)):r['values'] for r in probe}
    p36=bytime[36];p55=bytime[55];p550=bytime[550];p630=bytime[630];p700=bytime[700]
    checks={
        'stop_complete':abs(t-cfg['stop_s'])<1e-14,
        'eight_codes_correct':len(samples)==8 and all(r['actual']==r['expected'] for r in samples),
        'eight_comparisons_per_frame':frame_counts==[8]*8 and len(clocks)==64,
        'eight_completions':len(done)==8,
        'no_main_fault':fault_peak<.45,
        'charge_redistribution_cm':len(cm)==8 and all(abs(r['cm_V']-(.45+cfg['lsb_V']/2))<1e-4 for r in cm),
        'residual_bound':len(cm)==8 and all(abs(r['residual_V'])<cfg['lsb_V']+1e-4 for r in cm),
        'cancelled_compare_stays_reset':max(p36['cop'],p36['con'])<.1,
        'new_compare_after_cancel_works':p55['cop']>.8 and p55['con']<.1,
        'invalid_pair_fault':p550['badfault']>.8,
        'missing_result_timeout':p630['timeoutfault']>.8,
        'sample_aborts_pending_frame':p700['afault']>.8 and p700['abusy']<.1 and p700['aeoc']<.1,
        'no_stale_compare_after_abort':not any(54.2e-9<x<90e-9 for x in edges.get('xabort.cmpck',[]))}
    result={'checks':checks,'ok':all(checks.values()),'captures':samples,'clock_counts':frame_counts,
            'edges':edges,'completed_residuals':cm,'probes':probe,'fault_peak_V':fault_peak,'native_points':count,
            'native_state':state.get('native'),'scope':'Behavioral smoke only; not ADC electrical/performance qualification'}
    json.dump(result,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2,sort_keys=True)
    if not result['ok']:raise ValueError('Behavioral checks failed: '+str([k for k,v in checks.items() if not v]))
    print('All behavioral checks passed;',count,'native time points')


if __name__=='__main__':main()
