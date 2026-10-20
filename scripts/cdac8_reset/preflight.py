"""Read-only CIW/library/dependency verification before independent OA builds."""
from dataclasses import asdict
from support import LIB, OLD, OUT, dump
from virtuoso_bridge import VirtuosoClient


def main():
    assert not (OUT / "preflight/library.json").exists(), "Preserve initial snapshots; use audit.py for rechecks"
    c = VirtuosoClient.from_env(profile="t28_io")
    lib = c.library.get(LIB)
    assert lib.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert lib.technology_library == "tsmcN28"
    dump("preflight/library.json", asdict(lib))
    dump("preflight/windows.json", c.list_windows())
    cells = ["sar_bootstrap_canvas_flat_8b", "cdac8_device", "cdac8_device_nominal",
             "tb_cdac8_nominal", "tb_cdac8_sampling", "sar_strongarm_t28"]
    cells += [f"cdac8_ref_switch_b{b}" for b in range(8)]
    for cell in cells:
        state = c.schematic.read(LIB, cell, param_filters=None, include_positions=True)
        dump(f"preflight/{cell}.json", state)
        old = OLD / f"oa/{cell}.json"
        if cell == "sar_bootstrap_canvas_flat_8b":
            old = OLD / f"oa/{cell}_before.json"
        if old.exists():
            import json
            assert state == json.loads(old.read_text()), f"Dependency drift: {cell}"
    for cell in [f"cdac8_reset_sw_b{b}" for b in range(8)] + [
        "cdac8_reset_nominal", "cdac8_reset_device", "tb_cdac8_reset_nominal",
        "tb_cdac8_reset_literal", "tb_cdac8_reset_strongarm",
    ]:
        r = c.execute_skill(f'ddGetObj("{LIB}" "{cell}")')
        assert not r.errors and r.output.strip() == "nil", (cell, r)
    print("PREFLIGHT_OK", lib, flush=True)


if __name__ == "__main__":
    main()
