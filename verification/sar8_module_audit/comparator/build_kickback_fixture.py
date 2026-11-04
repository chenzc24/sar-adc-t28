"""One local TT charge/kickback package; never register, simulate or use SSH."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

import build_d_fixture as d

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "generated/kickback_v1"
D2 = HERE / "generated/deterministic_v2"
STARTS = [20, 60, 100, 140, 180, 220]
SIGNS = [1, 1, -1, 1, -1, -1]
VDIFF = 1.8 / 256 / 4

INITIALIZER = '''// Testbench charge initialization only; not a transistor sampling switch.
`include "disciplines.vams"
module cmp_charge_initializer(p, n, control, reference);
    inout p, n;
    input control, reference;
    electrical p, n, control, reference;
    parameter real ron = 10.0 from (0:inf);
    parameter real control_high = 0.9 from (0:inf);
    real factor;
    analog begin
        factor = V(control, reference) / control_high;
        if (factor < 0.0) factor = 0.0;
        if (factor > 1.0) factor = 1.0;
        I(p, n) <+ factor * V(p, n) / ron;
    end
endmodule
'''


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def exact(path, blob):
    blob = blob.encode() if isinstance(blob, str) else blob
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != blob:
        raise ValueError("Preserve immutable package; use a new version: " + str(path))
    if not path.exists():
        path.write_bytes(blob)


def js(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def cap_load(original):
    caps = [x for x in d.instances(original["sar8j_r1_cdac"]) if x[2] == "cfmom_2t"]
    if len(caps) != 18:
        raise ValueError("Expected exactly eighteen native CDAC MOM instances")
    rows, identities, units = [], [], {"P": 0, "N": 0}
    for name, nodes, model, params in caps:
        remapped = ["VCM" if re.fullmatch(r"B[PN][0-7]", n) else n for n in nodes]
        rows.append("    %s (%s) %s %s" % (name, " ".join(remapped), model, params))
        mult = int(re.search(r"\bmulti=(\d+)\b", params)[1])
        units[name[4]] += mult
        identities.append(dict(name=name, model=model, parameters=params,
                               original_nodes=nodes, held_nodes=remapped))
    if units != {"P": 256, "N": 256}:
        raise ValueError("Flat8 CDAC unit-weight sum changed")
    return ("subckt audit_cdac_hold TOPN TOPP VCM VREFN VREFP\n" +
            "\n".join(rows) + "\nends audit_cdac_hold\n"), identities


def init_wave():
    points = [(0., "SUP")]
    for i, at in enumerate(STARTS):
        if i:
            points += [(at - 16., 0.), (at - 15.9, "SUP")]
        points += [(at - 2., "SUP"), (at - 1.9, 0.)]
    points.append((260., 0.))
    return d.pwl(points)


def prepare():
    frozen = json.loads((D2 / "manifest.json").read_text())
    for name in ["cells.scs", "tt.scs"]:
        if sha((D2 / name).read_bytes()) != frozen["files"][name]:
            raise ValueError("Frozen D2 input changed: " + name)
    source = d.check_source(json.loads((HERE / "fixture_spec.json").read_text()))
    original = d.blocks((ROOT / source["rx2_dut"]["path"]).read_text())
    cap_text, cap_identity = cap_load(original)
    defs = d.blocks((D2 / "cells.scs").read_text())
    pins = d.ports(defs["audit_comparator_d"])
    cap_defs = d.blocks(cap_text)
    all_devices, binds, roots = {}, {}, {}
    for arm, prefix, suffix in [("evaluate", "XACTIVE", "A"), ("reset", "XRESET", "B")]:
        binding = {p: p for p in pins}
        binding.update(TOPP="TOPP_" + suffix, TOPN="TOPN_" + suffix,
                       CMP_CLK="CMP_CLK" if suffix == "A" else "0", VDD="VDD!", VSS="0")
        binding.update({"D" + str(i): "D%d_%s" % (i, suffix) for i in range(8)})
        binds[arm] = binding
        native = d.flatten(defs, "audit_comparator_d", binding, prefix=prefix)
        all_devices.update(native)
        all_devices.update(d.flatten(cap_defs, "audit_cdac_hold",
            dict(TOPP=binding["TOPP"], TOPN=binding["TOPN"], VCM="VCM",
                 VREFN="VREFN", VREFP="VREFP"), prefix=prefix + "_CDAC"))
        roots[arm] = dict(prefix=prefix, topp=binding["TOPP"].lower(), topn=binding["TOPN"].lower(),
            comp_p=(prefix + ".COMP_P").lower(), comp_n=(prefix + ".COMP_N").lower(),
            data=(prefix + ".XCTRL.DATA").lower(), write=(prefix + ".XCTRL.PHI_W").lower(),
            d0=binding["D0"].lower(), gate_p=(prefix + ".XCOMP.MNINP:2").lower(),
            gate_n=(prefix + ".XCOMP.MNINN:2").lower())
    if sum(x["model"].startswith(("nch_", "pch_")) for x in all_devices.values()) != 934:
        raise ValueError("D2 MOS count changed")
    pairs, voltage = [], {"CMP_CLK", "CINIT", "PREP", "PREN", "VDD!", "VCM", "VREFP", "VREFN"}
    for arm in roots.values():
        voltage.update(arm[n] for n in ["topp", "topn", "comp_p", "comp_n", "data", "write", "d0"])
    for name, item in all_devices.items():
        if not item["model"].startswith(("nch_", "pch_")):
            continue
        if not any(tag in name for tag in [".XCOMP.", ".XCTRL.XTIM.X002.", ".XCTRL.XTIM.X003."]):
            continue
        model = item["model"]
        limit = .99 if model in ["nch_mac", "pch_mac"] else 1.98
        if model not in ["nch_mac", "pch_mac", "nch_18_mac", "pch_18_mac", "nch_na18_mac"]:
            raise ValueError("Unreviewed selected MOS class: " + model)
        ns = dict(zip("dgsb", item["nodes"]))
        voltage.update(n for n in ns.values() if n != "0")
        for a, b in ["ds", "gs", "gd", "gb", "bd", "bs"]:
            pairs.append(dict(instance=name.lower(), terminal=a+b,
                              nodes=[ns[a].lower(), ns[b].lower()], screen_v=limit))
    currents, kcl, terminals = {"VVDD:1"}, {}, {}
    for arm, suffix in [("evaluate", "A"), ("reset", "B")]:
        prefix = roots[arm]["prefix"]
        for side, top in [("P", "TOPP_" + suffix), ("N", "TOPN_" + suffix)]:
            terms = []
            for name, item in all_devices.items():
                for i, node in enumerate(item["nodes"], 1):
                    if node == top:
                        term = name + ":" + str(i)
                        terms.append(term.lower()); currents.add(term)
                        terminals[term.lower()] = dict(node=top.lower(), port=i, model=item["model"])
            sense = "VSENSE_%s%s:1" % (suffix, side)
            terms.append(sense.lower()); currents.add(sense)
            terminals[sense.lower()] = dict(node=top.lower(), port=1, model="vsource")
            if len(terms) != 11:
                raise ValueError("Top KCL must include nine MOMs, input gate, initializer sensor")
            kcl[top.lower()] = terms
    lines = (D2 / "tt.scs").read_text().splitlines()
    deck = []
    for line in lines:
        if line.startswith("//") or line.startswith("save "):
            continue
        if line.startswith("XDUT "):
            for arm in ["evaluate", "reset"]:
                deck.append(roots[arm]["prefix"] + " (" + " ".join(binds[arm][p] for p in pins) + ") audit_comparator_d")
            deck += ['include "cdac_load.scs"', 'ahdl_include "initializer.va"']
            for arm, suffix in [("evaluate", "A"), ("reset", "B")]:
                deck.append("%s_CDAC (TOPN_%s TOPP_%s VCM VREFN VREFP) audit_cdac_hold" % (roots[arm]["prefix"], suffix, suffix))
                for side, pre in [("P", "PREP"), ("N", "PREN")]:
                    top = "TOP%s_%s" % (side, suffix)
                    deck += ["VSENSE_%s%s (%s HOLD_%s%s) vsource dc=0" % (suffix, side, top, suffix, side),
                             "XINIT_%s%s (HOLD_%s%s %s CINIT 0) cmp_charge_initializer ron=10 control_high=0.9" % (suffix, side, suffix, side, pre)]
            continue
        if line.startswith("VTOPP "):
            line = line.replace("VTOPP (TOPP 0)", "VPREP (PREP 0)")
        if line.startswith("VTOPN "):
            line = line.replace("VTOPN (TOPN 0)", "VPREN (PREN 0)")
        if line.startswith("tran_d "):
            line = line.replace("tran_d", "tran_kickback", 1)
        deck.append(line)
    deck += ["VINIT (CINIT 0) vsource type=pwl wave=[" + init_wave() + "]",
             "VVCM (VCM 0) vsource dc=0.45", "VREFLOW (VREFN 0) vsource dc=0", "VREFHIGH (VREFP 0) vsource dc=0.9"]
    voltage = sorted({n.lower() for n in voltage if n != "0"})
    currents = sorted(n.lower() for n in currents)
    deck += ["save " + n for n in voltage + currents]
    deck = ("// TT native CDAC held-input diagnostic; not yet Spectre compiled.\n"
            "// Original comparator/receiver/clock settings; ideal temporary initialization and fixed bottom rails.\n" +
            "\n".join(deck) + "\n")
    payload = {"test.scs": deck.encode(), "cells.scs": (D2 / "cells.scs").read_bytes(),
               "cdac_load.scs": cap_text.encode(), "initializer.va": INITIALIZER.encode(),
               "kickback_analyze.py": (HERE / "kickback_analyze.py").read_bytes()}
    cycles = [dict(index=i, start_s=at*1e-9, clock_fall_end_s=(at+12.1)*1e-9,
                   release_start_s=(at-2)*1e-9, release_end_s=(at-1.9)*1e-9,
                   next_acquire_s=(STARTS[i+1]-16)*1e-9 if i+1 < len(STARTS) else 260e-9,
                   target_diff_v=sign*VDIFF, target_cm_v=.45, expected_DATA=1 if sign>0 else 0)
              for i, (at, sign) in enumerate(zip(STARTS, SIGNS))]
    cfg = dict(schema_version=1, scope="TT fixed-bottom physical MOM input-load diagnostic; no ADC/noise/mismatch/PVT qualification",
        stop_s=260e-9, arms=roots, cycles=cycles, voltage_saves=voltage, current_saves=currents,
        kcl_terms=kcl, terminal_catalog=terminals, mos_pairs=pairs,
        pair_scope="N4 plus both rx2 buffers only; attached storage/forward logic not requalified here",
        required_input_sha256={n:sha(v) for n,v in payload.items()},
        charge_current_sign="Native current positive from node into component; native multiplicity already included",
        max_output_bytes=30*1024**2, max_events=1000, acceptance_pass=None,
        boundaries=dict(bottom_bit_plates_v=.45, dummy_n_v=0., dummy_p_v=.9,
                        initializer_ron_ohm=10., initializer_off_conductance_s=0.,
                        retained_sampler=False, retained_reference_driver=False,
                        external_clocks_and_rails="ideal", simultaneous_bottom_switching=False),
        numerical_policy="Frozen D2 deck options and clocks; inspect actual native Spectre settings after run")
    payload["measurement.json"] = js(cfg).encode()
    for name, blob in payload.items():
        exact(OUT/name, blob)
    inputs = [dict(name=n, source=(OUT/n).relative_to(ROOT).as_posix(), sha256=sha(v)) for n,v in payload.items()]
    recipe = dict(run_id="sar8audit-comp-kickback-tt-v1", design_id="sar8_comp_cdac_hold_tt_v1",
        entry="test.scs", analyzer="kickback_analyze.py", inputs=inputs, expected_stop_s=260e-9,
        summary_signals=["topp_a", "topn_a", "topp_b", "topn_b", "cmp_clk"],
        qualification_scope=cfg["scope"], oa_parity="netlist_only",
        test_conditions=dict(corner="ttmacro_mos_moscap/TT passives",vdd_v=.9,temperature_c=27,
                             mismatch=False,transient_noise=False,PEX=False),
        spectre_args=["+preset=cx", "+mt=1", "+lqtimeout", "60", "-preset_override"],
        resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,
            analysis_rss_mib=256,analysis_virtual_mib=512,max_output_mib=2048,
            simulation_wall_seconds=1800,analysis_wall_seconds=1800,queue_timeout_seconds=3600))
    exact(OUT/"recipe_proposal.json", js(recipe))
    exact(OUT/"manifest.json", js(dict(status="local_package_not_Spectre_compiled", remote_submitted=False,
        D2_manifest_sha256=sha((D2/"manifest.json").read_bytes()), source_DUT=source["rx2_dut"],
        builder_sha256=sha(Path(__file__).read_bytes()), input_hashes=cfg["required_input_sha256"],
        generated_measurement_sha256=sha(payload["measurement.json"]), native_MOS=934,
        native_CDAC_MOMs=36, units_per_arm_per_side=256, selected_MOS_pairs=len(pairs),
        CDAC_original_to_held_bottom_mapping=cap_identity,
        total_package_bytes=sum(len(v) for v in payload.values()), acceptance_pass=None)))
    print("LOCAL_KICKBACK_PACKAGE", OUT, "MOS=934 MOM=36 selected_pairs="+str(len(pairs)))
    return cfg


if __name__ == "__main__":
    prepare()
