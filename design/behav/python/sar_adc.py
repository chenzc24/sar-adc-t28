"""B-view behavioral oracle: binary decisions and an explicit async event trace.

Updated from the historical sar_adc.py, sar_async.py and sar_async_simple.py.
The current model reads specs/arch.json; it never imports a historical config.
Voltage and time approximations are declared in design/behav/README.md.
"""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AdcSpec:
    bits: int
    vref: float
    timing: dict

    def __post_init__(self):
        if self.bits!=8 or not math.isfinite(self.vref) or self.vref<=0:
            raise ValueError('Positive reference and exactly eight B output pins required')

    @classmethod
    def load(cls, path=None):
        data = json.loads(Path(path or ROOT/'specs/arch.json').read_text(encoding='utf-8'))
        if data['resolution_bits'] != 8:
            raise ValueError('This view implements the eight physical B output pins')
        return cls(8,data['reference']['high_v']-data['reference']['low_v'],
                   dict(data['behavior_models']['default_timing']))

    @property
    def lsb(self):
        return 2*self.vref/(1 << self.bits)


@dataclass(frozen=True)
class AnalogConfig:
    gain: float = 1.0
    sampling_offset_v: float = 0.0
    comparator_offset_v: float = 0.0
    weight_errors: tuple = (0.0,)*8  # Relative effective weights, LSB first.
    dac_tau_s: float = 0.0
    sample_noise_rms_v: float = 0.0
    comparator_noise_rms_v: float = 0.0
    reference_noise_rms_v: float = 0.0
    stuck_bit: int = -1

    def __post_init__(self):
        values=[self.gain,self.sampling_offset_v,self.comparator_offset_v,self.dac_tau_s,
                self.sample_noise_rms_v,self.comparator_noise_rms_v,self.reference_noise_rms_v,*self.weight_errors]
        if not all(math.isfinite(x) for x in values):raise ValueError('Non-finite model parameter')
        if len(self.weight_errors)!=8 or any(x<=-1 for x in self.weight_errors):raise ValueError('Eight positive effective weights required')
        if min(self.dac_tau_s,self.sample_noise_rms_v,self.comparator_noise_rms_v,self.reference_noise_rms_v)<0:raise ValueError('Negative time/noise')
        if not -1<=self.stuck_bit<=7:raise ValueError('stuck_bit must be -1 or 0..7')


@dataclass
class FrameResult:
    code: int
    completed: bool
    issue: str | None
    issue_bit: int | None
    counts: tuple
    sample_close_s: float
    seq_close_s: float
    last_update_s: float | None
    finished_s: float | None
    trace: list = field(default_factory=list)

    @property
    def conversion_s(self):
        return None if self.last_update_s is None else self.last_update_s-self.seq_close_s


class SarAdcModel:
    def __init__(self, spec=None, analog=None, timing=None, seed=271828):
        self.spec = spec or AdcSpec.load()
        self.analog = analog or AnalogConfig()
        self.timing = dict(self.spec.timing)
        if timing:self.timing.update(timing)
        if any(not math.isfinite(v) or v<0 for v in self.timing.values()):raise ValueError('Invalid timing profile')
        if min(self.timing['comparator_floor_v'],self.timing['conversion_budget_s'],self.timing['transition_s'])<=0:
            raise ValueError('Positive decision floor, observation budget and output transition required')
        self.rng = random.Random(seed)

    def threshold(self, word):
        a=self.analog
        return -self.spec.vref+self.spec.lsb*sum((1<<b)*(1+a.weight_errors[b]) for b in range(8) if word&(1<<b))

    def ideal_code(self, vin):
        """Independent closed-form oracle; upper code at a mathematical tie."""
        if not math.isfinite(vin):raise ValueError('Non-finite input')
        return max(0,min(255,math.floor((vin+self.spec.vref+self.timing['decision_epsilon_v'])/self.spec.lsb)))

    def _noise(self, sigma):
        return self.rng.gauss(0,sigma) if sigma else 0.0

    def convert(self, vin, *, close_s=0.0, available_s=None):
        """Start at external SAMPLE fall; next acquisition cancels unfinished work.

        A deadline is an observer diagnosis. The physical B has no timeout pin.
        Counts cover completed events, including two reference captures per bit.
        """
        if not math.isfinite(vin) or not math.isfinite(close_s):raise ValueError('Non-finite input/time')
        t=self.timing;a=self.analog
        budget=t['conversion_budget_s'] if available_s is None else available_s
        if not math.isfinite(budget) or budget<=0:raise ValueError('Positive observation window required')
        deadline=close_s+budget
        sample_close=close_s+t['sample_buffer_s']
        seq_close=sample_close+t['seq_buffer_s']
        now=seq_close+t['first_compare_s']
        held=a.gain*vin+a.sampling_offset_v+self._noise(a.sample_noise_rms_v)
        word=0;counts=[0,0,0,0];trace=[];last_update=None
        dac=0.0;previous_target=0.0;mark=seq_close
        last_eval=seq_close

        def finish(issue,bit):
            return FrameResult(word,False,issue,bit,tuple(counts),sample_close,seq_close,last_update,None,trace)

        def event(name,bit,when):
            trace.append(dict(event=name,bit=bit,time_s=when,word=word))

        for bit in range(7,-1,-1):
            if now>=deadline:return finish('acquisition_deadline',bit)
            trial=word|(1<<bit)
            target=self.threshold(trial)
            # Current threshold starts at the previous reference update. Evolve
            # the old target to that update before applying the new trial.
            if a.dac_tau_s:
                dac=previous_target+(dac-previous_target)*math.exp(-max(0,mark-last_eval)/a.dac_tau_s)
                dac=target+(dac-target)*math.exp(-max(0,now-mark)/a.dac_tau_s)
            else:dac=target
            counts[0]+=1;event('cmp',bit,now)
            residual=held-dac-a.comparator_offset_v-self._noise(a.reference_noise_rms_v)+self._noise(a.comparator_noise_rms_v)
            delay=t['compare_to_write_s']+t['comparator_tau_s']*max(0,math.log(2*self.spec.vref/max(abs(residual),t['comparator_floor_v'])))
            if a.stuck_bit==bit:return finish('unresolved_comparator',bit)
            write=now+delay
            if write>=deadline:return finish('acquisition_deadline',bit)
            if residual>=-t['decision_epsilon_v']:word=trial
            counts[1]+=1;event('write',bit,write)
            update=write+t['write_to_update_s']
            if update>=deadline:return finish('acquisition_deadline',bit)
            counts[2]+=1;last_update=update;event('update',bit,update)
            cap1=update+t['update_to_capture_s']
            if cap1>=deadline:return finish('acquisition_deadline',bit)
            counts[3]+=1;event('cap',bit,cap1)
            cap2=cap1+t['capture_gap_s']
            if cap2>=deadline:return finish('acquisition_deadline',bit)
            counts[3]+=1;event('cap',bit,cap2)
            previous_target=target;last_eval=now;mark=update
            now=cap2+t['capture_to_next_compare_s']
        return FrameResult(word,True,None,None,tuple(counts),sample_close,seq_close,last_update,cap2,trace)

    def reconstruct(self, code, digital_weights=None):
        if not isinstance(code,int) or not 0<=code<=255:raise ValueError('Unsigned 8-bit code required')
        weights=tuple(digital_weights) if digital_weights is not None else tuple(1<<i for i in range(8))
        if len(weights)!=8 or not all(math.isfinite(x) for x in weights):raise ValueError('Eight finite digital weights required')
        return -self.spec.vref+self.spec.lsb*(sum(weights[b] for b in range(8) if code&(1<<b))+0.5)
