"""Drive registered work only via the managed agent, separate from log inspection."""
from __future__ import print_function
import hashlib
import os
import traceback
from managed_campaign import Campaign, read, write, ROOT, DEST


def main():
    m=read(DEST+'/manifest.json')
    agent=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
    blob=open(agent,'rb').read()
    assert hashlib.sha256(blob).hexdigest()==m['agent_sha256']
    scope={'__name__':'managed_agent','__file__':agent}
    eval(compile(blob,agent,'exec'),scope)
    campaign=Campaign(m,scope['main'])
    try:
        for run,h in m['registered_hashes'].items():
            assert read(ROOT+'/runs/'+run+'/registered.json')['recipe_hash']==h
        jobs=m['jobs']
        # Each of the two campaigns uses two concurrent slots.
        def pairs(batch,stage):
            for i in range(0,len(batch),2):
                current=batch[i:i+2]
                campaign.finish_many(current,stage)
                if m['group']=='cold':
                    for run in current:
                        r=campaign.done[run]
                        write(DEST+'/'+run+'_review.json',dict(run=run,elapsed_s=read(ROOT+'/runs/'+run+'/simulation.state.json')['elapsed_seconds'],first_issue=r['first_issue'],valid=r['measurement_valid']))
                        if stage!='four_pilots' and (r['first_issue'] or not r['measurement_valid']):
                            raise RuntimeError('Hold at '+run+'; see bit-level review')
        if m['group']=='cold':
            pairs(jobs[:4],'four_pilots')
            assert all(campaign.done[r]['measurement_valid'] and not campaign.done[r]['first_issue'] for r in jobs[:4]),'Pilot issue; inspect four per-bit review receipts'
            # The bottom-plate rail bound cannot qualify the held top-node reference.
            # A hash-bound physical reference review must exist before expansion.
            import time
            campaign.state('awaiting_independent_top_reference')
            while not os.path.isfile(DEST+'/reference_review.json'):time.sleep(20)
            reference=read(DEST+'/reference_review.json')
            assert reference['pass'] and reference['runs']=={r:m['registered_hashes'][r] for r in jobs[:4]},'Independent reference failed'
            write(DEST+'/pilot_pass.json',{'pilots':jobs[:4]})
            pairs(jobs[4:],'remaining_cold_samples')
        else:
            pairs(jobs,'TT_module_extension')
        campaign.state('complete')
    except Exception as exc:
        campaign.state('held',error=repr(exc),traceback=traceback.format_exc())
        raise
if __name__=='__main__':
    main()
