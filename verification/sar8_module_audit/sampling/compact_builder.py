"""Local compact sampling fixtures with the actual direct sample-clock path.

No remote access, recipe or simulator invocation. The previous full-load draft
is read-only. Immediate SAMPLE_INT gate units retain native parameters, but
their removed downstream output loading is inventoried rather than restored.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

import builder as base

HERE = Path(__file__).resolve().parent
OUT = HERE / "compact_v2"
ROOT = base.ROOT
PROPOSAL = HERE / "compact_proposal.json"
ORACLE = ROOT / "verification/sar8_module_audit/reference/oracle.py"
CLOCK_ROOTS = ["XDUT.XSAMPLE.", "XDUT.XIDLE.XA.", "XDUT.XIDLE.XB.", "XDUT.XSEQ."]
SAMPLE_INT = "XDUT.SAMPLE_INT"


def signature(rows):
    return base.sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode())


def select_proposal(original, proposal):
    groups = {}
    for group in proposal["groups"]:
        def take(name, device):
            if "prefixes" in group:
                return name.startswith(tuple(group["prefixes"]))
            if "instances" in group:
                return name in group["instances"]
            return (bool(re.match(group["instance_regex"], name)) and
                    (device["model"] == "rupolym" or bool(re.match(
                        r"^G(NN|NP|PN|PP)C[NP]$", name.split(".")[-1]))))
        rows = {n:d for n,d in original.items() if take(n,d)}
        assert len(rows) == group["primitives"]
        assert signature(rows) == group["map_sha256"]
        groups[group["id"]] = rows
    return groups


def compact_selection(original, proposal):
    groups = select_proposal(original, proposal)
    del groups["final_sample_buffer"]
    groups["direct_sample_clock"] = {n:d for n,d in original.items()
                                     if n.startswith(tuple(CLOCK_ROOTS))}
    selected = {n:d for rows in groups.values() for n,d in rows.items()}
    missing = [e for e in base.fanout(original, SAMPLE_INT) if e["instance"] not in selected]
    # Every missing direct input is a gate of a standalone native inverter.
    # Keep that whole two-MOS cell, and stop at its output.
    leaf_roots = sorted({e["instance"].rsplit(".",1)[0] + "." for e in missing})
    stubs = {}
    for prefix in leaf_roots:
        rows = {n:d for n,d in original.items() if n.startswith(prefix)}
        assert len(rows) == 2 and all(base.mos(d) for d in rows.values()), prefix
        assert all(d["nodes"][1] == SAMPLE_INT for d in rows.values()), prefix
        assert len({d["nodes"][0] for d in rows.values()}) == 1, prefix
        assert not (set(rows) & set(selected)), prefix
        stubs.update(rows)
    groups["immediate_sample_gate_units"] = stubs
    selected.update(stubs)
    assert len(selected) == 591 and sum(base.mos(d) for d in selected.values()) == 237
    return selected, groups, leaf_roots


def q128_targets():
    module_spec = importlib.util.spec_from_file_location("sampling_reference_oracle", ORACLE)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    # Unused synthetic analog clause satisfies the oracle's explicit schema;
    # no observations are made and no hardware accuracy/timing limit is set.
    contract = dict(schema_version=1, contract_id="symbolic-Q128-only", analog_requirements=[
        dict(id="unused-symbolic", stage="reset", bit=None, start_ns=0,
             end_ns=0, tolerance_v=0, purpose="No analog observation; preset truth only")])
    oracle = module.ReferenceOracle(dict(vrefp_v=.9, vrefn_v=0, vdd_v=.81,
        logic_low_max_v=.081, logic_high_min_v=.729), [], contract)
    for time, bit in enumerate(range(7,-1,-1)):
        oracle.apply(dict(time_ns=time, kind="reset_assert", bit=bit))
    assert oracle.qword() == 128
    targets = oracle.targets()
    assert targets["bp_v"] == [.9]*7+[0]
    assert targets["bn_v"] == [0]*7+[.9]
    return targets


def reference_inputs(original, selected):
    q128_targets()
    result = []
    for bit in range(8):
        q = int(bit == 7)
        for gate in ["GNN", "GNP", "GPN", "GPP"]:
            node = f"XDUT.XREF.XDRV{bit}.{gate}B"
            value = q if gate in ["GNN", "GNP"] else 1-q
            fans = base.fanout(selected, node)
            assert len(fans) == 2 and all(e["terminal"] == "g" for e in fans)
            assert not base.native_drivers(selected, node)
            drivers = {n:d for n,d in selected.items() if n in {e["instance"] for e in fans}}
            # Actual retained CP/CN pair is an inverter; output is !B.
            assert {d["nodes"][0] for d in drivers.values()} == {f"XDUT.XREF.XDRV{bit}.{gate}DRV"}
            output_bit = 1-value
            expected = (1-q) if gate in ["GNN", "GNP"] else q
            assert output_bit == expected
            result.append(dict(port=f"REF{bit}_{gate}B", original_node=node,
                               logic_value=value, ideal_value="SUP" if value else "0"))
    return result


def terminal_set(entries):
    return sorted((e["instance"],e["terminal"],e["model"]) for e in entries)


def boundary_inventory(original, selected, groups, leaf_roots, refs):
    watched = ["SAMPLE", SAMPLE_INT, "XDUT.XIDLE.SAMPLE_AND", "XDUT.SAMPLE_MATCH",
               "XDUT.XSEQ.QUAL", "XDUT.SEQ_SAMPLE", "XDUT.TOPP", "XDUT.TOPN",
               "XDUT.COMP_P", "XDUT.COMP_N", "XDUT.XCTRL.XTIM.PR", "XDUT.XCTRL.XTIM.NR"]
    loads = []
    for node in watched:
        before, after = base.fanout(original,node), base.fanout(selected,node)
        assert terminal_set(before) == terminal_set(after), node
        loads.append(dict(node=node, source_terminal_count=len(before),
            retained_terminal_count=len(after), direct_terminal_identity=True,
            terminal_set_sha256=signature(terminal_set(after))))
    omitted = []
    for prefix in leaf_roots:
        rows = groups["immediate_sample_gate_units"]
        leaf = {n:d for n,d in rows.items() if n.startswith(prefix)}
        output = next(iter(leaf.values()))["nodes"][0]
        before, after = base.fanout(original,output), base.fanout(selected,output)
        omitted.append(dict(cell=prefix.rstrip("."), output_node=output,
            source_terminal_count=len(before), selected_terminal_count=len(after),
            omitted_terminal_count=len(before)-len(after),
            original_parameters_and_nodes_sha256=signature(leaf),
            limitation="Original direct inverter retained; omitted output loading changes its Miller response; transient equivalence is not asserted"))
    assert not base.native_drivers(selected,base.CLOCK)
    return dict(schema_version=1, direct_loads=loads, reference_cut_inputs=refs,
        sample_load_gate_units=omitted,
        controller_loop_retained=False, reference_registers_retained=False,
        ideal_source_boundaries=["SAMPLE", "CMP_RESET"]+[r["port"] for r in refs],
        comparator_reset=dict(original_node=base.CLOCK, retained_native_drivers=0,
                              value_v=0),
        downstream_receiver_cuts=[dict(node=n, source=len(base.fanout(original,n)),
            selected=len(base.fanout(selected,n))) for n in ["XDUT.XCTRL.DATA","XDUT.XCTRL.XTIM.RAW"]],
        groups={name:dict(primitives=len(rows), MOS=sum(base.mos(d) for d in rows.values()),
            MOM=sum(d["model"]=="cfmom_2t" for d in rows.values()),
            resistors=sum(d["model"]=="rupolym" for d in rows.values()),
            map_sha256=signature(rows)) for name,rows in groups.items()},
        selected_map_sha256=signature(selected))


def fixture_text(selected, refs):
    aliases = {base.CLOCK:"CMP_RESET", **{r["original_node"]:r["port"] for r in refs}}
    ports = ["SAMPLE","VDD!","VINN","VINP","VREFN","VREFP","CMP_RESET"]
    ports += [r["port"] for r in refs] + ["0"]
    lines = ["// Compact native sampling attachment; not Spectre compiled.",
             "subckt sampling_compact " + " ".join(ports)]
    mapping = []
    for index,(name,d) in enumerate(selected.items()):
        label = ("M" if base.mos(d) else "C" if d["model"]=="cfmom_2t" else "R") + f"{index:04d}"
        nodes = [aliases.get(n,base.safe_node(n)) for n in d["nodes"]]
        lines.append(f"{label} ({' '.join(nodes)}) {d['model']} {d['parameters']}")
        mapping.append(dict(instance=name, label=label, nodes=nodes, model=d["model"],
            parameter_sha256=base.sha(d["parameters"].encode())))
    lines.append("ends sampling_compact")
    return "\n".join(lines)+"\n", ports, mapping


def make_deck(case, original_tb, ports, refs, mapping):
    points = base.sample_points(case)
    sources = base.source_lines(original_tb)
    includes = re.findall(r'(?m)^include ".*" section=.*$',original_tb)
    includes = [s.replace("ttmacro_mos_moscap","ssmacro_mos_moscap") for s in includes]
    wave = " ".join(f"{t:g}n {v}" for t,v in points)
    lines = ["// Short-low/long-low history diagnosis; not zero-precharge reproduction.",
        "// Local preparation only; not Spectre compiled.", "simulator lang=spectre",
        "global 0 VDD!", "parameters SUP=0.81"]
    lines += includes + ['include "fixture_dut.scs"',
        "XF ("+" ".join(ports)+") sampling_compact"]
    lines += [sources[n] for n in base.PROTECTED_SOURCES]
    lines += ["VVDD (VDD! 0) vsource dc=SUP type=dc",
        "VCMP_RESET (CMP_RESET 0) vsource dc=0 type=dc",
        f"VSAMPLE (SAMPLE 0) vsource type=pwl wave=[{wave}]"]
    for r in refs:
        lines.append(f"V{r['port']} ({r['port']} 0) vsource dc={r['ideal_value']} type=dc")
    lines += ["simulatorOptions options method=gear2only reltol=1e-6 vabstol=1e-8 "
        "iabstol=1e-13 temp=125 tnom=27 scalem=1.0 scale=1.0 "
        "gmin=1e-12 rforce=1 checklimitdest=psf",
        "saveOptions options save=allpub currents=selected subcktiprobes=no useprobes=no",
        "save VVDD:1 VREFHIGH:1 VREFLOW:1 VVINP:1 VVINN:1 VSAMPLE:1 VCMP_RESET:1"]
    for row in mapping:
        if row["instance"].startswith(("XDUT.XBOOTP.","XDUT.XBOOTN.")):
            count = 4 if row["model"].startswith(("nch_","pch_")) else 2
            lines.append("save "+" ".join("XF."+row["label"]+":"+str(i) for i in range(1,count+1)))
    lines.append("tran_startup tran stop=160n maxstep=10p errpreset=conservative lteratio=10")
    return "\n".join(lines)+"\n"


def payloads():
    spec = json.loads(base.SPEC.read_text())
    proposal = json.loads(PROPOSAL.read_text())
    for key,rec in spec["sources"].items():
        assert base.sha((ROOT/rec["path"]).read_bytes()) == rec["sha256"],key
    assert base.sha(Path(base.__file__).read_bytes()) == proposal["source"]["parser_sha256"]
    original_tb = (ROOT/spec["sources"]["candidate_testbench"]["path"]).read_text()
    original = base.flatten((ROOT/spec["sources"]["candidate_dut"]["path"]).read_text())
    selected,groups,leaf_roots = compact_selection(original,proposal)
    refs = reference_inputs(original,selected)
    boundary = boundary_inventory(original,selected,groups,leaf_roots,refs)
    fixture,ports,mapping = fixture_text(selected,refs)
    boundary["device_mapping_without_geometry"] = mapping
    outputs = {"fixture_dut.scs":fixture.encode(),
        "short_low_history.scs":make_deck("high_dc_short_low",original_tb,ports,refs,mapping).encode(),
        "long_low_history.scs":make_deck("low_dc_precharge",original_tb,ports,refs,mapping).encode(),
        "boundary_loads.json":(json.dumps(boundary,indent=2)+"\n").encode()}
    manifest = dict(schema_version=1, status="local_compact_not_Spectre_compiled",
        source=proposal["source"], builder_sha256=base.sha(Path(__file__).read_bytes()),
        reference_oracle=dict(path=ORACLE.relative_to(ROOT).as_posix(),
            sha256=base.sha(ORACLE.read_bytes()), Q_word=128, targets=q128_targets(),
            scope="symbolic reset truth only, no analog qualification"),
        primitives=len(selected), MOS=sum(base.mos(d) for d in selected.values()),
        native_parameters_unchanged=True, source_connections_unchanged_except_cut_aliases=True,
        whole_controller_or_reference_word_retained=False,
        clock_path="XSAMPLE -> XIDLE.XA/XB -> XSEQ.XD/XA/XB -> SEQ_SAMPLE",
        clock_independent_of_ACTIVE=True, QUAL_replay_required=False,
        actual_SEQ_SAMPLE_edges_ns=None, externally_common_rise_start_ns=101,
        externally_common_close_start_ns=141, external_edge_ns=.1, period_ns=100,
        history_pair="short-low versus long-low", zero_precharge_reproduction=False,
        high_dc_short_low_plateau_ns=.1, Cboot_initial_charge_forced=False,
        conditions=dict(corner="ss",vdd_v=.81,temp_c=125,passives="tt",noise=False,mismatch=False,PEX=False),
        observations=dict(held_ns=141.8,preclose="actual SEQ_SAMPLE close minus0.2ns",
            nominal_source_target_v=-.81,normal_sample_requires_observed_open_and_close=True,
            startup_limit_v=None,droop_limit_v=None),
        limitations=["Immediate SAMPLE_INT inverter loads retain native devices but lose downstream output loading; Miller response can differ",
            "RAW/DATA receiver downstream fanout is omitted",
            "reference driver input B is a known static Q128 preset; dynamic nonoverlap/register/reset sequencing is not qualified",
            "short low pulse may be filtered by the actual clock path; if no SEQ_SAMPLE opening occurs, acquisition duration and normal-pass remain unknown",
            "actual timing and startup state require simulation; no equivalence or successful acquisition is asserted"],
        artifacts={n:dict(sha256=base.sha(v),bytes=len(v)) for n,v in outputs.items()},
        simulator_invoked=False,remote_operation=False,recipe_created=False)
    outputs["manifest.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    return outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    outputs=payloads()
    if not args.check:OUT.mkdir(exist_ok=True)
    for name,data in outputs.items():
        p=OUT/name
        if p.exists():assert p.read_bytes()==data,f"existing compact artifact differs; no overwrite: {name}"
        elif args.check:raise AssertionError("missing compact artifact: "+name)
        else:p.write_bytes(data)
    print(json.dumps(dict(files=len(outputs),bytes=sum(map(len,outputs.values())),
        source_identity="PASS",simulator_invoked=False,fixture_MOS=237)))


if __name__=="__main__":main()
