"""Diagnostic variants of an immutable native export; not final OA netlists."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import re

from support import OLD, OUT, batch, blocks, digest, dump, sha


@dataclass(frozen=True)
class Variant:
    name: str
    p_fast: int = 1
    n_buffer: str = "none"  # none, shared, independent
    n_strength: int = 1
    gap_ps: int = 200
    edge_ps: int = 20


SCREEN = [Variant("baseline"), *[Variant(f"pfast{x}", p_fast=x) for x in (2, 4, 8)],
          *[Variant(f"shared{x}", n_buffer="shared", n_strength=x) for x in (1, 2, 4)],
          *[Variant(f"independent{x}", n_buffer="independent", n_strength=x) for x in (1, 2)],
          Variant("gap50", gap_ps=50), Variant("gap500", gap_ps=500)]


def device_line(body, name):
    match = re.search(rf"(?m)^    {name} \([^\n]*(?:\n        [^\n]*)*", body)
    assert match, name
    return match[0]


def clone_inverter(body, suffix, output, input_node, strength):
    out = []
    for channel in "NP":
        old = device_line(body, f"M{channel}_IS")
        new = old.replace(f"M{channel}_IS (ES_B ES ", f"M{channel}_{suffix} ({output} {input_node} ", 1)
        new = re.sub(r"multi=(\d+)\*MULT_D", lambda m: f"multi={int(m[1])*strength}*MULT_D", new)
        assert new != old
        out.append(new)
    return "\n".join(out) + "\n"


def modify(text, variant):
    original = blocks(text)
    bootstrap = original["sar_bootstrap_canvas_flat_8b"]
    phi = re.search(r"(?m)^VPHI .*\n[^\n]*", text)[0]
    for bit in range(8):
        name = f"cdac8_ref_switch_b{bit}"
        before = original[name]
        after = before
        if variant.n_buffer != "none":
            if variant.n_buffer == "shared":
                extra = clone_inverter(before, "IN2", "ES_N", "ES_B", variant.n_strength)
            else:
                extra = clone_inverter(before, "IN1", "ES_NB", "ES", 1)
                extra += clone_inverter(before, "IN2", "ES_N", "ES_NB", variant.n_strength)
            after = after.replace("MN_CM (BOT ES ", "MN_CM (BOT ES_N ", 1)
            after = after.replace(f"ends {name}", extra + f"ends {name}")
        if variant.p_fast != 1:
            old_line = device_line(after, "MN_IS")
            new_line = re.sub(r"multi=(\d+)\*MULT_D",
                              lambda m: f"multi={int(m[1])*variant.p_fast}*MULT_D", old_line)
            after = after.replace(old_line, new_line, 1)
        text = text.replace(before, after, 1)
    text, count = re.subn(r"(VDACSAMPLE .*?width=)48\.2n", rf"\g<1>{48+variant.gap_ps/1000:.9g}n", text, count=1, flags=re.S)
    assert count == 1
    pattern = r"(VDACSAMPLE .*?fall=)20p"
    text, count = re.subn(pattern, rf"\g<1>{variant.edge_ps}p", text, count=1, flags=re.S)
    assert count == 1
    assert blocks(text)["sar_bootstrap_canvas_flat_8b"] == bootstrap
    assert re.search(r"(?m)^VPHI .*\n[^\n]*", text)[0] == phi
    # Capacitors, comparator and every other subcircuit remain byte-identical.
    changed = {f"cdac8_ref_switch_b{b}" for b in range(8)}
    for name, body in original.items():
        if name not in changed:
            assert blocks(text)[name] == body, name
    return text


def configure(text, *, vdiff=.453515625, sup=.9, corner="tt", temp=27,
              open_loop=0, fixed_code=-1, stim_mode=0, stop_ns=300, dense=False):
    match = re.search(r"(?m)^parameters ((?:[^\n]*\\\n)*[^\n]*)\n", text)
    names = match[1].replace("\\\n", " ").split()
    values = dict(MULT_D=1, MULT_S=1, MULT_R=1, CKB=.05e-15, DEAD_TIME=100e-12,
                  OPEN_LOOP=open_loop, FIXED_CODE=fixed_code, STIM_MODE=stim_mode,
                  VDIFF=vdiff, FIN=10e6*461/1024, RREF=50, SUP=sup, CDECAP=4e-12)
    assert set(names) in (set(values), set(values)-{"CKB"}), names
    values = {name: values[name] for name in names}
    text = text[:match.start()] + "parameters " + " ".join(f"{n}={values[n]:.14g}" for n in names) + "\n" + text[match.end():]
    text = text.replace("section=ttmacro_mos_moscap", f"section={corner}macro_mos_moscap")
    text = text.replace("temp=27", f"temp={temp}").replace("save=allpub", "save=selected")
    text = text.replace("reltol=1e-4", "reltol=1e-5").replace("vabstol=1e-6", "vabstol=1e-7").replace("iabstol=1e-12", "iabstol=1e-13")
    text = re.sub(r"(?m)^\w+ info .*\n", "", text)
    names = ["TOPP", "TOPN", "VINP", "VINN", "VDD!", "VCM", "VREFP", "VREFN", "PHI", "DAC_SAMPLE", "BASE", "VALID", "BUSY", "VVDD:p", "VVCM:p", "VREFHIGH:p", "VREFLOW:p"]
    names += [f"DOUT\\<{b}\\>" for b in range(8)]
    names += [f"SEL{q}\\<{b}\\>" for q in (0, 1) for b in range(8)]
    for side in "PN":
        for bit in range(9):
            names.append(f"XCDAC.B{side}{bit}")
            for node in ("EH_B", "EL_B", "EL_D", "ES_B", "ES_N", "ES_NB"):
                masters = blocks(text)
                prefix = "cdac8_reset_sw_b" if "cdac8_reset_sw_b0" in masters else "cdac8_ref_switch_b"
                master = masters[f"{prefix}{bit if bit<8 else 0}"]
                if re.search(rf"\b{node}\b", master):
                    names.append(f"XCDAC.XS{side}{bit}.{node}")
    text += "\nmodel macro_clamp diode is=1e-6 n=1 rs=5\n"
    text += f"tran tran stop={stop_ns}n maxstep={'10p' if dense else '100p'} errpreset=conservative\n"
    text += "save " + " ".join(names) + "\n"
    return text, values


def prepare(variant, *, prefix="screen", source=None, **case):
    source = source or OLD / "oa_netlists/tb_cdac8_nominal/balanced/input.scs"
    original = source.read_text()
    transformed = modify(original, variant)
    text, parameters = configure(transformed, **case)
    name = prefix + "_" + variant.name
    path = OUT / "decks" / (name + ".scs")
    assert not path.exists(), f"Preserve experiment: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("// DIAGNOSTIC MODIFICATION OF NATIVE OA EXPORT; NOT FINAL OA DUT\n" + text, encoding="utf-8")
    dump(f"cases/{name}.json", {
        "name": name, "variant": asdict(variant), "case": case,
        "parameters": parameters, "source": str(source), "source_sha256": sha(source),
        "bootstrap_sha256": digest(blocks(original)["sar_bootstrap_canvas_flat_8b"]),
        "phi_unchanged": True, "scope": "netlist_level_diagnostic_not_final_schematic",
    })
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["screen", "extra", "negative_baseline", "joint"])
    args = parser.parse_args()
    if args.mode == "screen":
        paths = [prepare(v) for v in SCREEN]
        batch(paths, "screen")
    elif args.mode == "extra":
        cases = [(Variant("pfast2_negative", p_fast=2), -.8),
                 (Variant("pfast2_positive", p_fast=2), .8),
                 (Variant("pfast3_negative", p_fast=3), -.8)]
        paths = [prepare(v, prefix="extra", vdiff=vin, stop_ns=200) for v, vin in cases]
        batch(paths, "extra")
    elif args.mode == "negative_baseline":
        path = prepare(Variant("negative_baseline"), prefix="ab", vdiff=-.8, stop_ns=200)
        batch([path], "ab", workers=1)
    else:
        cases = [(Variant("pfast2_edge100_negative", p_fast=2, edge_ps=100), -.8),
                 (Variant("pfast2_edge300_negative", p_fast=2, edge_ps=300), -.8),
                 (Variant("pfast2_edge100_positive", p_fast=2, edge_ps=100), .8)]
        paths = [prepare(v, prefix="joint", vdiff=vin, stop_ns=100) for v, vin in cases]
        batch(paths, "joint")


if __name__ == "__main__":
    main()
