"""Isolated evidence and native-Spectre execution for the reset experiment."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/cdac8_reset"
OLD = ROOT / "output/cdac8_device"
LIB = "SAR_ADC_T28"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def dump(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def selected_variant():
    import yaml
    cfg = yaml.safe_load((ROOT / "config/cdac8_reset.yaml").read_text(encoding="utf-8"))["candidate"]
    assert cfg["vcm_n_added_buffer"] is False, "Define an explicit buffered candidate before building it"
    selected = dict(name=cfg["name"], p_fast=cfg["vcm_p_gate_pull_down_multiplier"],
                    n_buffer="none", n_strength=1,
                    gap_ps=cfg["reference_release_to_vcm_gap_ps"],
                    edge_ps=cfg["vcm_reenable_edge_ps"])
    old = OUT / "selected_variant.json"
    if old.exists():
        assert load("selected_variant.json") == selected, "Generated candidate selection disagrees with tracked config"
    return selected


def blocks(text):
    return {m[1]: m[0] for m in re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1$", text)}


def statements(text):
    return text.replace("\\\n", " ").splitlines()


def batch(paths, category, workers=3):
    for path in paths:
        assert not (OUT / category / f"{path.stem}_result.json").exists(), "Preserve accepted run; use a new case/category"
    from virtuoso_bridge.spectre import SpectreSimulator

    sim = SpectreSimulator.from_env(
        profile="t28_io", timeout=1800, work_dir=OUT / "spectre" / category,
        spectre_args=["+aps", "+lqtimeout", "5"],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    for offset in range(0, len(paths), workers):
        chunk = paths[offset:offset+workers]
        with (OUT / (category + "_runner.log")).open("a", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                results = sim.run_parallel([(p, {}) for p in chunk], max_workers=workers)
        for path, result in zip(chunk, results, strict=True):
            dump(f"{category}/{path.stem}_result.json", {
                "ok": result.ok, "errors": result.errors, "warnings": result.warnings,
                "metadata": result.metadata, "mode": "native_spectre_aps",
                "deck_sha256": sha(path),
            })
            if result.ok:
                # Deliberately exclude model/element info: they are not waveforms.
                wave = {str(k).strip('"').replace("\\", "").lower(): v
                        for k, v in result.data.items()
                        if isinstance(v, (list, tuple)) and str(k).strip('"').lower() != "units"}
                dump(f"{category}/{path.stem}_waveform.json", wave)
            print("SPECTRE", path.stem, result.ok, result.errors[:2], flush=True)
        assert all(r.ok for r in results), "Inspect per-run errors; no partial run is accepted"
        del results
