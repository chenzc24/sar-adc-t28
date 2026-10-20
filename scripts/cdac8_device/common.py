"""Contracts and collision-safe evidence for the PDK eight-bit CDAC target."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output/cdac8_device"
LIB="SAR_ADC_T28"
LSB=1.8/256
LIMIT=LSB/4
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER","1")

def dump(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,default=str)+"\n",encoding="utf-8")

def load(name):return json.loads((OUT/name).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cfg():return yaml.safe_load((ROOT/"config/cdac_flat_8b_device.yaml").read_text())
def stage(name,text):
    p=OUT/"decks"/(name+".scs");p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding="utf-8");return p

def batch(paths,category,includes=(),workers=3,timeout=3600,mode="spectre",extra_args=()):
    from virtuoso_bridge.spectre import SpectreSimulator
    from virtuoso_bridge.spectre.runner import spectre_mode_args
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre"/category,
        timeout=timeout,spectre_args=[*spectre_mode_args(mode),*extra_args])
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/(category+"_runner.log")).open("a",encoding="utf-8") as f:
        with contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
            results=sim.run_parallel([(p,{"include_files":list(includes)}) for p in paths],max_workers=workers)
    failed=[]
    for p,r in zip(paths,results,strict=True):
        row={"name":p.stem,"ok":r.ok,"errors":r.errors,"warnings":r.warnings,"metadata":r.metadata,"mode":mode,
             "deck_sha256":sha(p),"include_sha256":{Path(x).name:sha(x) for x in includes}}
        dump(f"{category}/{p.stem}_result.json",row)
        if r.ok:
            data={str(k).strip('"').replace("\\","").lower():v for k,v in r.data.items()}
            # Complex AC values are encoded explicitly, never as an opaque string.
            def encode(v):
                if isinstance(v,complex):return {"real":v.real,"imag":v.imag}
                if isinstance(v,(list,tuple)):return [encode(x) for x in v]
                return v
            dump(f"{category}/{p.stem}_waveform.json",{k:encode(v) for k,v in data.items()})
        else:failed.append(row)
        print("SPECTRE",p.stem,"OK" if r.ok else str(r.errors)[:300],flush=True)
    assert not failed,[(r["name"],r["errors"]) for r in failed]
    return results
