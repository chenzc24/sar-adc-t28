"""Review four pilots, then process each normal/reference pair; keep raw records immutable."""
from __future__ import print_function
import hashlib
import os
import time
import traceback
from managed_campaign import ROOT,DEST,read,write
from cold_queue import ColdQueue

def check_draws(run):
    raw=ROOT+'/runs/'+run+'/raw'
    names=open(raw+'/mismatch.params').read().splitlines()[1:]
    vals=open(raw+'/mismatch.values').read().splitlines()[1:]
    names=[n for n in names if n.strip()]
    vals=[v for v in vals if v.strip()]
    assert len(names)==len(vals) and 18<=len(names)<256
    table={n.strip().upper():v.strip() for n,v in zip(names,vals)}
    assert all(n in ('XDUT.XCOMP','XDUT.XCDAC') or n.startswith(('XDUT.XCOMP.','XDUT.XCDAC.')) for n in table)
    assert sum(n.startswith('XDUT.XCDAC.CMOM') for n in table)==18
    assert table['XDUT.XCOMP.MNINN']!=table['XDUT.XCOMP.MNINP']
    return hashlib.sha256(open(raw+'/mismatch.values','rb').read()).hexdigest()

def compare(run,base,ref):
    twin=ref['context']['run_id']
    assert check_draws(run)==check_draws(twin)
    problems=[];bits=[]
    for f,g in zip(base['frames'],ref['frames']):
        if g['first_issue'] and g['first_issue']['reason']!='CDAC_rail_settling_screen':
            problems.append(dict(reference_issue=g['first_issue']));continue
        prev=0
        for i,(b,r) in enumerate(zip(f['bits'],g['bits'])):
            row=dict(frame=f['frame'],bit=7-i,rx_margin_ps=b.get('rx_margin_ps'))
            mask=(0xff<<(8-i))&0xff
            if (f['code']&mask)!=(g['code']&mask):
                row['issue']='decision_prefix_changed'
            elif not i or 'update_s' in prev:
                tbase=(base['context']['frame_origin_s']+f['frame']*1e-7) if not i else prev['update_s']
                tref=(ref['context']['frame_origin_s']+g['frame']*1e-7) if not i else g['bits'][i-1]['update_s']
                extra=(r['cmp_s']-tref)-(b['cmp_s']-tbase)
                row.update(extra_dwell_ps=extra*1e12,reference_plateau_pp_lsb=r['plateau_pp_v']/ref['context']['LSB'],same_phase_top_delta_lsb=(b['top_diff_v']-r['top_diff_v'])/ref['context']['LSB'],reference_plateau_v=r['plateau_v'])
                if extra<100e-12 or row['reference_plateau_pp_lsb']>.1:row['issue']='unverified_reference_dwell'
                elif abs(row['same_phase_top_delta_lsb'])>.25:row['issue']='cold_top_settling_screen'
            else:row['issue']='missing_update'
            if row.get('issue') and (not problems or problems[-1].get('frame')!=f['frame']):problems.append(row)
            bits.append(row)
            prev=b
    return dict(run=run,reference=twin,base_hash=base['sampling']['values_sha256'],bits=bits,problems=problems,passed=len(bits)==80 and not problems,reference_scope='Extended identical-word quiet interval; delta includes hold drift, edge feedthrough and settling.')
def main():
    m=read(DEST+'/manifest.json')
    agent=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
    blob=open(agent,'rb').read()
    assert hashlib.sha256(blob).hexdigest()==m['agent_sha256']
    ns={'__name__':'managed_agent','__file__':agent}
    eval(compile(blob,agent,'exec'),ns)
    campaign=ColdQueue(m,ns['main'])
    parent=ROOT+'/campaigns/sar8-timing-mc-20261104-cold'
    try:
        campaign.state('waiting_four_pilots')
        deadline=time.time()+8*3600
        while read(parent+'/status.json')['stage'] not in ('held','awaiting_independent_top_reference'):
            assert time.time()<deadline,'Pilot review deadline exceeded'
            time.sleep(15)
        bases=read(parent+'/manifest.json')['jobs']
        i=0
        while i<len(bases):
            width=2 if i<4 else (7 if read(ROOT+'/campaigns/sar8-timing-mc-20261104-modules/status.json')['stage']=='complete' else 4)
            normal=bases[i:i+width];twins=m['jobs'][i:i+width]
            if i>=4:
                assert os.path.exists(DEST+'/pilot_pass.json')
                campaign.finish_many(normal,'cold_samples')
            for run in normal:
                path=ROOT+'/runs/'+run
                assert read(path+'/analysis.state.json')['status']=='complete'
                assert read(path+'/registered.json')['recipe_hash']==m['base_hashes'][run]
                check_draws(run)
                result=read(path+'/derived/result.json')
                issue=result['first_issue']
                if issue and issue['reason']!='CDAC_rail_settling_screen':
                    write(DEST+'/first_issue.json',dict(run=run,issue=issue))
                    raise RuntimeError('Cold protocol/deadline issue '+run+' '+repr(issue))
            campaign.finish_many(twins,'same_seed_hold_references')
            for run,twin in zip(normal,twins):
                base=read(ROOT+'/runs/'+run+'/derived/result.json')
                review=compare(run,base,campaign.done[twin])
                write(DEST+'/'+run+'_review.json',review)
                if not review['passed']:
                    write(DEST+'/first_issue.json',dict(run=run,issue=review['problems'][:2]))
                    raise RuntimeError('Hold for reference or timing diagnosis '+run)
            if i==2:
                write(DEST+'/pilot_pass.json',{'runs':{r:m['base_hashes'][r] for r in bases[:4]},'pass':True})
                # The first driver stops on the legacy root-scope diagnostic. Never
                # run two controllers for the remaining sample sequence.
                assert read(parent+'/status.json')['stage']=='held'
            i+=len(normal)
        campaign.state('complete')
    except Exception as exc:
        campaign.state('held',error=repr(exc),traceback=traceback.format_exc());raise
if __name__=='__main__':main()
