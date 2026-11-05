"""Shared B behavioral configuration and frame results.

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


