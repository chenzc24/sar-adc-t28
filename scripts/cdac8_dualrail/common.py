"""Owned dual-rail candidate contracts; preserve the original eight-bit baseline."""
from pathlib import Path
import os
import json
import hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/cdac8_dualrail'
LIB = 'SAR_ADC_T28'
LSB = 1.8 / 256
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

def oracle(v, ref=.9):
    """Eight-bit binary SAR; complementary arrays preserve ideal common-mode."""
    code = 0
    trajectory = []
    for b in range(7,-1,-1):
        trial = code + (1<<b)
        residual = v + ref - trial*(2*ref/256)
        trajectory.append(residual)
        if residual >= 0: code = trial
    return code, trajectory
