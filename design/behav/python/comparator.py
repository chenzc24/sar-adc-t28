"""Decision polarity, input-referred errors and input-dependent response time."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Decision:
    high: bool
    delay_s: float | None
    residual_v: float


class Comparator:
    def __init__(self, spec, analog, timing):
        self.spec,self.analog,self.timing=spec,analog,timing

    def decide(self, held_v, threshold_v, bit, rng):
        a=self.analog;t=self.timing
        noise=lambda sigma:rng.gauss(0,sigma) if sigma else 0.0
        residual=held_v-threshold_v-a.comparator_offset_v-noise(a.reference_noise_rms_v)+noise(a.comparator_noise_rms_v)
        delay=t['compare_to_write_s']+t['comparator_tau_s']*max(0,math.log(2*self.spec.vref/max(abs(residual),t['comparator_floor_v'])))
        return Decision(residual>=-t['decision_epsilon_v'],None if a.stuck_bit==bit else delay,residual)
