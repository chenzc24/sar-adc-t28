"""Continue known failed analysis attempts through bound analysis-only identities."""
from __future__ import print_function
import hashlib,json,os,time,traceback
from managed_campaign import Campaign,read,write,ROOT,DEST
def main():
    m=read(DEST+'/manifest.json');agent=ROOT+'/tools/agent_'+m['agent_sha256']+'.py';b=open(agent,'rb').read();assert hashlib.sha256(b).hexdigest()==m['agent_sha256']
    scope={'__name__':'managed_agent','__file__':agent};exec(compile(b,agent,'exec'),scope);api=scope['main'];c=Campaign(m,api)
    try:
        for run,h in m['registered_hashes'].items():assert read(ROOT+'/runs/'+run+'/registered.json')['recipe_hash']==h
        waiting=set(m['recovery_runs'])
        while waiting:
            for run in list(waiting):
                s=api({'action':'status','run_id':run});assert s['simulation']['status']=='not_applicable';v=s['analysis'];status=v['status']
                if status=='complete':
                    r=read(ROOT+'/runs/'+run+'/derived/result.json');assert r['analysis_complete'] and r['native_data_valid'];c.done[run]=r;waiting.remove(run)
                elif status=='not_started':api({'action':'analyze','run_id':run,'queue':True})
                elif status not in ['running','queued','starting','submitted','waiting']:raise RuntimeError('Bound analysis failure '+run+' '+str(v))
            c.state('recover_completed_initial_waveforms',pending=sorted(waiting))
            if time.time()-c.started>20*3600:raise RuntimeError('Finite20h deadline')
            if waiting:time.sleep(15)
        c.finish_many(m['paired_runs'],'final_physical_and_stiff_pairs')
        summary={run:{'context_run_id':r['context']['run_id'],'native_data_valid':r['native_data_valid'],'threshold_valid':r['threshold_valid'],'source_offset_v':r['source_offset_midpoint_v'],
          'held_offset_v':r['held_offset_midpoint_v'],'all_retained_parameters_identical':r['sample_mapping']['identical'],'warning_codes':r['warning_codes']} for run,r in c.done.items()}
        write(DEST+'/summary.json',summary);c.state('complete',summary=summary)
    except Exception as exc:c.state('failed',error=repr(exc),traceback=traceback.format_exc());raise
if __name__=='__main__':main()
