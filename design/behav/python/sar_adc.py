"""B top-level composition; replace functional modules through their interfaces."""
import math
import random
from .config import AdcSpec, AnalogConfig, FrameResult
from .sampler import Sampler
from .cdac import Cdac
from .comparator import Comparator
from .sar import SarController
from .reference import ReferenceControl


class SarAdcModel:
    def __init__(self, spec=None, analog=None, timing=None, seed=271828, *, sampler=None, cdac=None, comparator=None, sar=None, reference=None):
        self.spec = spec or AdcSpec.load()
        self.analog = analog or AnalogConfig()
        self.timing = dict(self.spec.timing)
        if timing:self.timing.update(timing)
        if any(not math.isfinite(v) or v<0 for v in self.timing.values()):raise ValueError('Invalid timing profile')
        if min(self.timing['comparator_floor_v'],self.timing['conversion_budget_s'],self.timing['transition_s'])<=0:
            raise ValueError('Positive decision floor, observation budget and output transition required')
        self.rng = random.Random(seed)
        self.sampler=sampler or Sampler(self.analog)
        self.cdac=cdac or Cdac(self.spec,self.analog)
        self.comparator=comparator or Comparator(self.spec,self.analog,self.timing)
        self.sar=sar or SarController(self.timing)
        self.reference=reference or ReferenceControl(self.timing)

    def threshold(self, word):
        return self.cdac.threshold(word)

    def ideal_code(self, vin):
        """Independent closed-form oracle; upper code at a mathematical tie."""
        if not math.isfinite(vin):raise ValueError('Non-finite input')
        return max(0,min(255,math.floor((vin+self.spec.vref+self.timing['decision_epsilon_v'])/self.spec.lsb)))

    def convert(self, vin, *, close_s=0.0, available_s=None):
        if not math.isfinite(vin) or not math.isfinite(close_s):raise ValueError('Non-finite input/time')
        budget=self.timing['conversion_budget_s'] if available_s is None else available_s
        if not math.isfinite(budget) or budget<=0:raise ValueError('Positive observation window required')
        held=self.sampler.capture(vin,self.rng)
        return self.sar.run(held,close_s,budget,self.cdac,self.comparator,self.reference,self.rng)

    def reconstruct(self, code, digital_weights=None):
        if not isinstance(code,int) or not 0<=code<=255:raise ValueError('Unsigned 8-bit code required')
        weights=tuple(digital_weights) if digital_weights is not None else tuple(1<<i for i in range(8))
        if len(weights)!=8 or not all(math.isfinite(x) for x in weights):raise ValueError('Eight finite digital weights required')
        return -self.spec.vref+self.spec.lsb*(sum(weights[b] for b in range(8) if code&(1<<b))+0.5)
