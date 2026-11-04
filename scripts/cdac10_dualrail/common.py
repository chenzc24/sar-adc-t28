"""Owned candidate contracts; never write into the eight-bit experiment."""
from pathlib import Path
import os
import json
import hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/cdac10_dualrail'
LIB = 'SAR_ADC_T28'
LSB = 1.8 / 1024
LIMIT = LSB / 4
os.environ.setdefault('VB_DISABLE_CONTROL_MASTER', '1')

def dump(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, default=str)+'\n', encoding='utf-8')

def load(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def oracle(v, ref=.9, caps=None):
    """Ten actual sign decisions; ideal charge-conserving monotonic switching."""
    weights = caps or [ref*(1<<b)/512 for b in range(8,-1,-1)]
    residual = v
    code = 0
    trajectory = []
    for j in range(10):
        positive = residual >= 0
        code = 2*code + int(positive)
        trajectory.append(residual)
        if j < 9:
            residual += -weights[j] if positive else weights[j]
    return code, trajectory
