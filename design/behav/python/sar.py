"""MSB-first asynchronous sequencing; sampling cancels pending bit events."""
from .config import FrameResult


class SarController:
    def __init__(self, timing):
        self.timing=timing

    def run(self, held, close_s, budget, cdac, comparator, reference, rng):
        t=self.timing;deadline=close_s+budget
        sample_close=close_s+t['sample_buffer_s']
        seq_close=sample_close+t['seq_buffer_s']
        now=seq_close+t['first_compare_s']
        word=0;counts=[0,0,0,0];trace=[];last_update=None
        cdac.reset(seq_close)

        def finish(issue,bit):
            return FrameResult(word,False,issue,bit,tuple(counts),sample_close,seq_close,last_update,None,trace)

        def event(name,bit,when):
            trace.append(dict(event=name,bit=bit,time_s=when,word=word))

        for bit in range(7,-1,-1):
            if now>=deadline:return finish('acquisition_deadline',bit)
            trial=word|(1<<bit);threshold=cdac.evaluate(trial,now)
            counts[0]+=1;event('cmp',bit,now)
            decision=comparator.decide(held,threshold,bit,rng)
            if decision.delay_s is None:return finish('unresolved_comparator',bit)
            write=now+decision.delay_s
            if write>=deadline:return finish('acquisition_deadline',bit)
            if decision.high:word=trial
            counts[1]+=1;event('write',bit,write)
            update=write+t['write_to_update_s']
            if update>=deadline:return finish('acquisition_deadline',bit)
            counts[2]+=1;last_update=update;event('update',bit,update)
            cap1,cap2=reference.captures(update)
            if cap1>=deadline:return finish('acquisition_deadline',bit)
            counts[3]+=1;event('cap',bit,cap1)
            if cap2>=deadline:return finish('acquisition_deadline',bit)
            counts[3]+=1;event('cap',bit,cap2)
            cdac.commit(trial,now,update);now=reference.next_compare(cap2)
        return FrameResult(word,True,None,None,tuple(counts),sample_close,seq_close,last_update,cap2,trace)
