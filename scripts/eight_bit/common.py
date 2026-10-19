"""Small shared contracts for the independent 8-bit flat implementation."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/eight_bit_flat"
LIB = "SAR_ADC_T28"
BITS = 8
LSB = 1.8 / 256
LIMIT = LSB / 4
CU = 6.86047e-15
CDAC = "sar_cdac_flat_8b"
CTRL = "sar_macro_controller_8b"
MACRO_TB = "tb_sar_macro_flat_8b"
BOOT_TB = "tb_bootstrap_flat_8b"
NATIVE = "sar_bootstrap_canvas_cdac_t28"
SIZED = "sar_bootstrap_canvas_flat_8b"
COMP_TB = "tb_cdac_strongarm_flat_8b"


def dump(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def config():
    return yaml.safe_load((ROOT / "config/eight_bit_flat.yaml").read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(data):
    return {str(k).strip('"').replace("\\", "").lower():v for k,v in data.items()}


def stage(name, text):
    path = OUT / "decks" / (name + ".scs")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_batch(jobs, category, *, includes=(), workers=3, timeout=1800):
    """Each result carries its unique physical result directory and hashes."""
    from virtuoso_bridge.spectre import SpectreSimulator
    from virtuoso_bridge.spectre.runner import spectre_mode_args

    os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
    sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre" / category,
                                    timeout=timeout, spectre_args=spectre_mode_args("spectre"))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / (category + "_runner.log")).open("a", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            results = sim.run_parallel([(p, {"include_files":list(includes)}) for p in jobs], max_workers=workers)
    records = []
    for path, result in zip(jobs, results, strict=True):
        row = {"name":path.stem, "ok":result.ok, "errors":result.errors, "warnings":result.warnings,
               "metadata":result.metadata, "deck_sha256":digest(path),
               "include_sha256":{Path(p).name:digest(p) for p in includes}}
        dump(f"{category}/{path.stem}_result.json", row)
        if not result.ok:
            raise RuntimeError(f"{path.stem}: {result.errors}")
        dump(f"{category}/{path.stem}_waveform.json", normalized(result.data))
        records.append(row)
        print("SPECTRE_OK", category, path.stem, flush=True)
    return records
