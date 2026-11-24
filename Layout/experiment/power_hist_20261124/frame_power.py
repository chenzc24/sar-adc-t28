"""Convert signed Stage 6 rail charges to nominal-supply-referred energy per conversion."""
import argparse
import hashlib
import json
from pathlib import Path


def measure(run):
    source = run / "collected/derived/result.json"
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    receipt = json.loads((run / "collected/collection_receipt.json").read_bytes())
    if not any(f["name"] == "derived/result.json" and f["sha256"] == digest for f in receipt["files"]):
        raise ValueError(f"No matching result receipt for {run.name}")
    data = json.loads(raw)
    parent = run.parent / data["run_id"]
    ctx = json.loads((parent / "inputs/context.json").read_bytes())
    recipe = json.loads((run / "recipe.json").read_bytes())
    if recipe["source"]["run_id"] != parent.name or ctx["run_id"] != parent.name:
        raise ValueError("Rail analysis and simulation identities differ")
    start, period = ctx["frame_origin_s"], ctx["period_s"]
    first = max(1, ctx["warmup_frames"])
    frames = [r for r in data["per_frame"] if r["frame"] >= first]
    if [r["frame"] for r in frames] != list(range(first, ctx["frames"])):
        raise ValueError("Missing steady-state frame")
    if start + ctx["frames"] * period > ctx["expected_stop_s"] + 1e-12:
        raise ValueError("Last frame would be truncated")
    low, high = ctx["reference_v"]
    energy = []
    for frame in frames:
        core = ctx["vdd_v"] * frame["vdd_charge_c"]
        reference = high * frame["vrefp_charge_c"] - low * frame["vrefn_charge_c"]
        energy.append(dict(frame=frame["frame"], core_J=core, reference_J=reference))
    core = sum(f["core_J"] for f in energy) / len(energy)
    reference = sum(f["reference_J"] for f in energy) / len(energy)
    return dict(corner=ctx["corner"], run=run.name, parent=parent.name, result_sha256=digest,
                recipe_hash=receipt["status"]["registered"]["recipe_hash"], first_frame=first,
                period_s=period, frames=energy, core_uW=core/period*1e6, reference_uW=reference/period*1e6,
                combined_uW=(core+reference)/period*1e6, combined_pJ_per_conversion=(core+reference)*1e12)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("runs", type=Path)
    args = cli.parse_args()
    cases = [measure(run) for run in sorted(args.runs.glob("sar8-s6f-*-rails3"))]
    if len(cases) != 9 or len({(r["corner"], r["parent"].split("-")[3]) for r in cases}) != 9:
        raise ValueError("Expected verify, extreme and carry in each of three corners")
    print(json.dumps(cases, indent=2))
