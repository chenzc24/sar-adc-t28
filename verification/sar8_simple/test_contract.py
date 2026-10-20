"""Focused deterministic checks of exactly this new timing contract."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "models/behavioral"))
from sar_async_simple import Timing, convert


def main():
    import yaml
    sys.path.insert(0, str(ROOT / "scripts/sar8_simple"))
    from circuit import TOP, hierarchy
    contract = yaml.safe_load((ROOT / "config/sar8_simple.yaml").read_text(encoding="utf-8"))
    spec = yaml.safe_load((ROOT / "config/design_spec.yaml").read_text(encoding="utf-8"))
    assert spec["converter"]["control_contract"] == "config/sar8_simple.yaml"
    assert contract["top_cell"] == TOP
    objects = {obj.name: obj for obj in hierarchy()}
    top = objects[TOP]
    assert top.inputs == ["SAMPLE", "COMP_P", "COMP_N", "VDD", "VSS"]
    assert len(top.outputs) == 41 and "EOC" not in top.outputs
    assert not any(part.master.startswith("sar8a_") for obj in objects.values() for part in obj.parts)
    for word in range(256):
        row = convert(pattern=word)
        assert row["word"] == word and row["token"] == 0
        for event in ("compare", "write", "update_reset"):
            assert sum(item[1] == event for item in row["trace"]) == 8
        assert row["final_write_ns"] < 95
        # Exercise actual binary-search arithmetic away from thresholds too.
        analog = convert(vin=-0.9 + (word + 0.375) * 1.8 / 256)
        assert analog["word"] == word, (word, analog)
    for bit in range(8):
        row = convert(pattern=165, stuck_bit=bit)
        assert not row["complete_observer_only"] and row["token"] == 1 << bit
        assert sum(item[1] == "write" for item in row["trace"]) == 7 - bit
        assert convert(pattern=90)["word"] == 90
    for at in (41, 45, 52, 65):
        row = convert(pattern=165, interrupt_ns=at)
        assert row["interrupted"] and row["word"] == 0 and row["token"] == 128
    slow = convert(pattern=165, timing=Timing(comparator_min_ns=1.0))
    assert slow["word"] == 165 and slow["final_write_ns"] < 95
    row = dict(scope="timing_contract_model_NOT_native_netlist_or_Spectre", words=256,
               analog_code_centers=256, stuck_positions=8, interrupted_cases=4,
               all_checks_pass=True, sample_initializes=True, no_eoc_or_status_state=True)
    output = ROOT / "output/sar8_simple/model_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(row, indent=2))


if __name__ == "__main__":
    main()
