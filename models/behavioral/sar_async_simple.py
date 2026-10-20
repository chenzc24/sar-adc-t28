"""Timing contract model; not a transistor/noise/metastability simulator."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Timing:
    acquisition_ns: float = 40.0
    first_settle_ns: float = 3.0
    write_after_decision_ns: float = 0.20
    update_after_write_ns: float = 0.50
    quiet_after_update_ns: float = 3.0
    comparator_min_ns: float = 0.15
    comparator_tau_ns: float = 0.035
    frame_ns: float = 100.0


def convert(vin=0.123, *, pattern=None, timing=Timing(), stuck_bit=None, interrupt_ns=None):
    """One frame; SAMPLE initializes pointer/register, no EOC/status state.

    A stuck comparator leaves a partial word until the next acquisition. A
    new acquisition cancels all old local events. Completion is observer-only.
    """
    now = timing.acquisition_ns + timing.first_settle_ns
    stored = 0; token = 128; trace = []; interrupted = False
    while token:
        bit = token.bit_length() - 1
        if interrupt_ns is not None and now >= interrupt_ns:
            interrupted = True; stored = 0; token = 128; break
        code = stored | token
        residual = vin + 0.9 - code * 1.8 / 256
        latency = timing.comparator_min_ns + timing.comparator_tau_ns * max(0, math.log(1.8 / max(abs(residual), 1e-9)))
        trace.append((now, "compare", bit, code))
        if bit == stuck_bit:
            break
        value = bool(pattern & token) if pattern is not None else residual >= 0
        write = now + latency + timing.write_after_decision_ns
        update = write + timing.update_after_write_ns
        if interrupt_ns is not None and update >= interrupt_ns:
            interrupted = True; stored = 0; token = 128; break
        stored = (stored | token) if value else (stored & ~token)
        trace.append((write, "write", bit, stored))
        token >>= 1
        trace.append((update, "update_reset", bit, token))
        now = update + timing.quiet_after_update_ns
    return dict(word=stored, token=token, trace=trace, interrupted=interrupted,
                final_write_ns=next((row[0] for row in reversed(trace) if row[1] == "write"), None),
                complete_observer_only=(not token and not interrupted))
