"""Differential acquisition, gain/offset and one noise draw per frame."""
import math


class Sampler:
    def __init__(self, analog, tau_s=0.0):
        if not math.isfinite(tau_s) or tau_s<0:
            raise ValueError('Nonnegative acquisition time constant required')
        self.analog,self.tau_s=analog,tau_s

    def acquire(self, vin, duration_s, initial_v=0.0):
        if not all(math.isfinite(x) for x in (vin,duration_s,initial_v)) or duration_s<0:
            raise ValueError('Finite input and nonnegative acquisition interval required')
        return vin if not self.tau_s else vin+(initial_v-vin)*math.exp(-duration_s/self.tau_s)

    def capture(self, vin, rng):
        a=self.analog
        return a.gain*vin+a.sampling_offset_v+(rng.gauss(0,a.sample_noise_rms_v) if a.sample_noise_rms_v else 0.0)
