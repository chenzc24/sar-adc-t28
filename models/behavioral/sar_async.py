"""Event-timed SAR reference. No fixed bit clock and no transistor claim."""
from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import math
import numpy as np


@dataclass(frozen=True)
class AsyncConfig:
    bits: int = 8
    span_v: float = 1.8
    start_ns: float = 43.0
    deadline_ns: float = 89.0
    initial_reset_ns: float = .5
    dac_guard_ns: float = 3.0
    valid_guard_ns: float = .1
    capture_ns: float = .15
    reset_guard_ns: float = .5
    advance_ns: float = .15
    publish_ns: float = .2
    comparator_min_ns: float = .15
    comparator_tau_ns: float = .035
    comparator_floor_v: float = 1e-9
    sample_noise_rms_v: float = 0.0
    comparator_noise_rms_v: float = 0.0
    comparator_offset_v: float = 0.0
    reference_noise_rms_v: float = 0.0
    dac_tau_ns: float = 0.0
    weight_error: tuple[float, ...] = ()  # Relative error, index 0 = LSB weight.

    def __post_init__(self):
        if not 1 <= self.bits <= 20 or self.span_v <= 0:raise ValueError("bits/span")
        if self.deadline_ns <= self.start_ns:raise ValueError("deadline")
        for k,v in vars(self).items():
            if k.endswith("_ns") and v < 0:raise ValueError(k)
        if self.weight_error and len(self.weight_error)!=self.bits:raise ValueError("weights")


@dataclass
class AsyncResult:
    code: int
    valid: bool
    fault: str | None
    completion_ns: float | None
    captures: int
    trace: list[dict] = field(default_factory=list)
    commit_ns: float | None = None


class AsyncSAR:
    def __init__(self,config=AsyncConfig(),seed=271828):
        self.cfg=config;self.rng=np.random.default_rng(seed);self.output=0;self.epoch=0

    def reset(self):
        self.output=0;self.epoch+=1

    def convert(self,vin_v,*,delays_ns=None,stuck_bit=None,illegal_bit=None,
                abort_ns=None,duplicate_ready=False,stale_ready=False,reset_ns=None):
        """One frame; timeout/abort priority wins ties and retains old output.

        The optional fault injections model protocol-level events, not a
        physical metastability detector. Delayed events carry an epoch so they
        cannot cross a new sample/frame.
        """
        c=self.cfg;self.epoch+=1;epoch=self.epoch;queue=[];serial=0;trace=[]
        work=0;bit=c.bits-1;phase="idle";captures=0;valid=False;fault=None;done=None;commit=None
        held=float(vin_v)+self.rng.normal(0,c.sample_noise_rms_v)
        dac_value=-c.span_v/2;target=dac_value;pending_data=0
        def push(t,kind,priority=1,event_epoch=epoch):
            nonlocal serial
            serial+=1;heapq.heappush(queue,(float(t),priority,serial,kind,event_epoch))
        def log(t,event,**extra):
            trace.append(dict(t_ns=float(t),event=event,bit=bit,work=work,phase=phase,**extra))
        push(c.deadline_ns,"deadline",0)
        if abort_ns is not None:push(abort_ns,"abort",0)
        push(c.start_ns+c.initial_reset_ns,"trial")
        if stale_ready:push(c.start_ns-.1,"ready",event_epoch=epoch-1)
        while queue:
            t,_,_,event,e=heapq.heappop(queue)
            if e!=epoch:log(t,"ignored_old_epoch");continue
            if event in ("abort","deadline"):
                if event=="deadline" and commit is not None:
                    log(t,"deadline_after_commit");continue
                if event=="abort" and commit is not None:
                    phase="idle";log(t,"acquisition_after_commit");break
                if not valid:
                    fault=event;phase="aborted";log(t,event)
                break
            if phase=="aborted":continue
            if event=="trial":
                phase="settle";trial=work|(1<<bit)
                errs=c.weight_error or (0.,)*c.bits
                target=-c.span_v/2+sum((1<<i)*c.span_v/(1<<c.bits)*(1+errs[i]) for i in range(c.bits) if trial&(1<<i))
                alpha=0 if c.dac_tau_ns==0 else math.exp(-c.dac_guard_ns/c.dac_tau_ns)
                dac_value=target+(dac_value-target)*alpha
                log(t,"trial",trial=trial);push(t+c.dac_guard_ns,"eval")
            elif event=="eval" and phase=="settle":
                phase="evaluate"
                residual=held-dac_value+c.comparator_offset_v+self.rng.normal(0,c.comparator_noise_rms_v)+self.rng.normal(0,c.reference_noise_rms_v)
                pending_data=int(residual>=0);index=c.bits-1-bit
                delay=(delays_ns[index] if delays_ns is not None else
                       c.comparator_min_ns+c.comparator_tau_ns*max(0,math.log(c.span_v/max(abs(residual),c.comparator_floor_v))))
                if not math.isfinite(delay) or delay < 0:raise ValueError("comparator delay")
                log(t,"eval",residual_v=residual,comparison_ns=delay)
                if bit!=stuck_bit:push(t+delay,"illegal" if bit==illegal_bit else "ready")
            elif event=="illegal" and phase=="evaluate":
                fault="illegal_rails";phase="aborted";log(t,"illegal");break
            elif event=="ready" and phase=="evaluate":
                phase="qualify";log(t,"ready");push(t+c.valid_guard_ns,"capture")
                if duplicate_ready:push(t+.01,"ready")
            elif event=="ready":log(t,"ignored_duplicate_ready")
            elif event=="capture" and phase=="qualify":
                phase="capture";captures+=1
                work=(work|(1<<bit)) if pending_data else (work&~(1<<bit))
                log(t,"capture",data=pending_data);push(t+c.capture_ns,"reset")
            elif event=="reset" and phase=="capture":
                phase="reset";log(t,"reset")
                duration=max(c.reset_guard_ns,reset_ns or 0)
                push(t+duration,"advance")
            elif event=="advance" and phase=="reset":
                phase="advance";log(t,"advance")
                if bit==0:push(t+c.advance_ns,"publish")
                else:bit-=1;push(t+c.advance_ns,"trial")
            elif event=="publish" and phase=="advance":
                phase="publish";self.output=work;commit=t
                log(t,"publish");push(t+c.publish_ns,"valid")
            elif event=="valid" and phase=="publish":
                self.output=work;valid=True;done=t;phase="done";log(t,"valid");break
        return AsyncResult(self.output,valid,fault,done,captures,trace,commit)
