"""Managed cold work after pilot release, bounded by the global admission gate."""
from __future__ import print_function
import os
import time
from managed_campaign import Campaign,read,write,ROOT,DEST

class ColdQueue(Campaign):
    def finish_many(self,runs,stage):
        assert 0<len(runs)<=7
        pending=list(runs)
        while pending:
            if time.time()-self.started>36*3600:raise RuntimeError('Queue deadline exceeded')
            for run in pending[:]:
                s=self.api({'action':'status','run_id':run})
                phase='analysis' if s['simulation']['status']=='complete' else 'simulation'
                item=s[phase]
                if item.get('observation'):raise RuntimeError(str(item))
                status=item['status']
                if phase=='analysis' and status=='complete':
                    r=read(ROOT+'/runs/'+run+'/derived/result.json')
                    assert r['analysis_complete'] and r['native_data_valid']
                    self.done[run]=r
                    write(DEST+'/'+run+'_result.json',r)
                    pending.remove(run)
                elif status=='not_started':
                    self.api({'action':'analyze' if phase=='analysis' else 'submit','run_id':run,'queue':True})
                elif status not in ('queued','submitted','starting','running','waiting'):
                    raise RuntimeError(str(item))
            self.state(stage,pending=pending)
            if pending:time.sleep(8)

