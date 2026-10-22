"""Small provenance helpers; independent of the unfinished performance scripts."""
from pathlib import Path
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'netlist/sar8_physical'
os.environ.setdefault('VB_DISABLE_CONTROL_MASTER', '1')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + '\n', encoding='utf-8')


def blocks(text):
    text = re.sub(r'\\\r?\n\s*', ' ', text)
    return {m[1]: ' '.join(m[0].split()) for m in re.finditer(r'(?ms)^subckt (\w+) .*?^ends \1\s*$', text)}


def records(log, prefix):
    return [[s.strip() for s in m[1].split(',')] for m in re.finditer(re.escape(prefix)+r',([^\r\n]+)', log)]
