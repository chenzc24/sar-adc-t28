"""Owned native candidate construction using existing checked bridge builders."""
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import sys
from pathlib import Path

from circuit import ROOT, LIB, all_objects

os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
OUT = ROOT / "output/sar8_physical"


def dump(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def builder_module():
    # join_r1 imports the historical module named circuit; isolate that import
    # while retaining this module's already bound physical-cell functions.
    previous = sys.modules.pop("circuit", None)
    sys.path.insert(0, str(ROOT / "scripts/sar8_simple"))
    sys.path.insert(0, str(ROOT / "scripts/integration"))
    spec = importlib.util.spec_from_file_location("_physical_oa_reference", ROOT / "scripts/integration/join_r1.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    sys.path.pop(0)
    sys.path.pop(0)
    if previous is not None:
        sys.modules["circuit"] = previous
    mod.OUT = OUT
    mod.dump = dump
    return mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["inventory", "build", "readback", "recheck", "open", "export", "repair-params", "repair-owned"])
    p.add_argument("--cell")
    p.add_argument("--tag", default="initial")
    args = p.parse_args()
    objects = all_objects()
    if args.action == "inventory":
        dump("cells.json", [dataclasses.asdict(c) for c in objects])
        print("\n".join(c.name for c in objects))
        return
    from virtuoso_bridge import VirtuosoClient
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    b = builder_module()
    if args.action == "open":
        assert args.cell in {x.name for x in objects}
        result=c.open_window(LIB,args.cell,view="schematic")
        assert not result.errors,result.errors
        print("OPENED",LIB,args.cell,flush=True)
        return
    if args.action == "export":
        assert args.cell in {x.name for x in objects}
        dest = OUT / "exports" / args.cell / args.tag
        assert not (dest / "input.scs").exists(), "Use a fresh tag"
        result = c.schematic.export_netlist(LIB, args.cell, dest, simulator="spectre", timeout=300)
        dump(f"exports/{args.cell}/{args.tag}/receipt.json", result)
        assert Path(result["input_file"]).exists()
        print("EXPORTED", result["input_file"], flush=True)
        return
    if args.cell:
        objects = [obj for obj in objects if obj.name == args.cell]
    assert objects
    windows = c.list_windows()
    for obj in objects:
        assert not any(obj.name + " " in w["name"] for w in windows), obj.name
        if b.exists(c, obj.name):
            assert (OUT / "owned" / f"{obj.name}.json").exists(), "Existing unowned cell"
        if args.action == "recheck":
            # Child symbol regeneration invalidates the parent extraction
            # timestamp even when its interface is unchanged. Check & Save
            # the owned parent, then demand the same exact readback.
            with c.schematic.modify(LIB, obj.name, timeout=180):
                pass
            b.readback(c, obj)
        elif args.action == "repair-owned":
            owner = OUT / "owned" / f"{obj.name}.json"
            previous = json.loads(owner.read_text())
            live = c.schematic.read(LIB, obj.name, include_positions=True, param_filters=None)
            actual = {i["name"]:(i["cell"],i["lib"],i["terms"]) for i in live["instances"]}
            expected = {i["name"]:(i["master"],i["lib"],i["terms"]) for i in previous["parts"]}
            removed_ports = {"sar_bootstrap_flat_8b_p": {"CLKSB"},
                             "sar_logic_8b_physical": {"PHI_W"},
                             "sar8p_refword": {"CAP_CLK"} | {f"Q{i}" for i in range(8)},
                             "sar_adc8_join_r4": {"CMP_CLK", "COMP_P", "COMP_N", "TOPP", "TOPN"}}
            # Replacing owned child symbols automatically drops those known
            # debug terminals from their existing owned parent instances.
            expected = {name:(master, lib, {k:v for k,v in terms.items()
                         if k not in removed_ports.get(master, set())})
                        for name,(master,lib,terms) in expected.items()}
            for name, (master, lib, terms) in list(actual.items()):
                if master in removed_ports:
                    want_master, want_lib, want_terms = expected[name]
                    assert (master, lib) == (want_master, want_lib)
                    assert all(want_terms.get(k) == v for k,v in terms.items())
                    # Our symbol regeneration changed pin coordinates, leaving
                    # old terminal stubs behind. Only missing connections on
                    # those explicitly repaired child masters are permitted.
                    actual[name] = (master, lib, want_terms)
            if actual != expected:
                print("OWNED_INTERFACE_DIFF", {name:dict(actual=actual.get(name), expected=expected.get(name))
                      for name in set(actual) | set(expected) if actual.get(name) != expected.get(name)}, flush=True)
                raise RuntimeError("Owned candidate interface requires inspection")
            dest = OUT / "repair_topology" / obj.name
            if dest.exists():
                dest = OUT / "repair_topology" / (obj.name + "_" + __import__("hashlib").sha256(
                       json.dumps(dataclasses.asdict(obj),sort_keys=True).encode()).hexdigest()[:10])
            assert not dest.exists(), "Use a new explicit repair identity"
            dump(str(dest.relative_to(OUT) / "source_before.json"), previous)
            dump(str(dest.relative_to(OUT) / "oa_before.json"), live)
            complete = OUT / "owned_complete" / f"{obj.name}.json"
            if complete.exists():
                complete.rename(dest / "completion_before.json")
            dump(f"owned/{obj.name}.json", dataclasses.asdict(obj))
            b.build(c, obj)
        elif args.action == "repair-params":
            previous = json.loads((OUT / "owned" / f"{obj.name}.json").read_text())
            before = [(x["name"], x["master"], x["terms"], x["lib"]) for x in previous["parts"]]
            after = [(x.name, x.master, x.terms, x.lib) for x in obj.parts]
            assert before == after, "Parameter repair may not change topology"
            dump(f"repair_before/{obj.name}.json", previous)
            b.set_params(c, obj)
            b.readback(c, obj)
            dump(f"owned/{obj.name}.json", dataclasses.asdict(obj))
            dump(f"owned_complete/{obj.name}.json", dict(complete=True))
        elif args.action == "build":
            b.build(c, obj)
        else:
            b.readback(c, obj)


if __name__ == "__main__":
    main()
