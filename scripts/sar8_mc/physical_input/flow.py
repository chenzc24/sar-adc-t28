"""Finite nine-case recovery/paired experiment; existing managed APIs only."""
from __future__ import print_function
import hashlib,json,os,sys,traceback
from managed_campaign import Campaign,read,write,ROOT,DEST
def main():
    m=read(DEST+'/manifest.json');agent=ROOT+'/tools/agent_'+m['agent_sha256']+'.py';b=open(agent,'rb').read();assert hashlib.sha256(b).hexdigest()==m['agent_sha256']
    scope={'__name__':'managed_agent','__file__':agent};exec(compile(b,agent,'exec'),scope)
    for run,h in m['registered_hashes'].items():assert read(ROOT+'/runs/'+run+'/registered.json')['recipe_hash']==h
    c=Campaign(m,scope['main'])
    try:
        c.finish_many(m['initial_runs'],'initial_common_mode_controls')
        c.finish_many(m['paired_runs'],'final_physical_and_stiff_pairs')
        summary={run:{'native_data_valid':r['native_data_valid'],'threshold_valid':r['threshold_valid'],
          'source_offset_v':r['source_offset_midpoint_v'],'held_offset_v':r['held_offset_midpoint_v'],
          'all_retained_parameters_identical':r['sample_mapping']['identical'],'warning_codes':r['warning_codes']} for run,r in c.done.items()}
        write(DEST+'/summary.json',summary);c.state('complete',summary=summary)
    except Exception as exc:c.state('failed',error=repr(exc),traceback=traceback.format_exc());raise
if __name__=='__main__':main()
