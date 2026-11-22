"""LVS source of the integrated chip sar8_adc_chip/layout_full: the full io_ring.json chip_netlist.

It extends the partial assembly's source (Layout/design/chip_lvs_source.py: the ring schematic's netlist inline, the
ADC core with its block references, the IO library SPICE) with the chip-level objects of Layout/design/chip_objects.py:
- XOUT_REG (sar8_out_reg, design/chip/output_register.scs as placed and routed): D0-D7 = ADC_D0-ADC_D7,
  Q0-Q7 = D0_CORE-D7_CORE, CK = SAMPLE_CORE, VDD = DVDD, VSS = VSS;
- XESD_CLAMPS (three PCLAMPC_H_G): VDDESD = AVDD_CORE, VSSESD = AVSS_CORE;
- XDECAP_ANALOG/PAIR/SAR (nmoscap, AVDD_CORE / AVSS_CORE) and XDECAP_DVDD (DVDD / VSS).
The core VSS ring and the ADC guard ring hold no devices; their metal joins VSS and AVSS_CORE in the layout.
Standard-cell bodies the base source lacks come from the installed foundry SPICE (fetched into work/, not tracked).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from Layout.design.chip_objects import lvs_source
from Layout.project import ROOT, config

TOP = "sar8_adc_chip"
STD_SPICE = ("/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/"
             "digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a/tcbn28hpcplusbwp12t30p140_170a.spi")
OBJECTS = [("XESD_CLAMPS", "clamps", ["AVDD_CORE", "AVSS_CORE"]),
           ("XDECAP_ANALOG", "decap_analog", ["AVDD_CORE", "AVSS_CORE"]),
           ("XDECAP_PAIR", "decap_pair", ["AVDD_CORE", "AVSS_CORE"]),
           ("XDECAP_SAR", "decap_sar", ["AVDD_CORE", "AVSS_CORE"]),
           ("XDECAP_DVDD", "decap_dvdd", ["DVDD", "VSS"])]
XOREG = [f"ADC_D{k}" for k in range(8)] + [f"D{k}_CORE" for k in range(8)] + ["SAMPLE_CORE", "DVDD", "VSS"]


def subckt_names(text):
    return {m.upper() for m in re.findall(r"(?im)^\.subckt[ \t]+(\S+)", text)}


def std_bodies(cells):
    if not cells:
        return ""
    cfg = config()
    pattern = "|".join(re.escape(c) for c in sorted(cells))
    script = (f"awk 'BEGIN{{IGNORECASE=1}} /^\\.subckt[ \\t]+({pattern})[ \\t]/{{p=1}} p{{print}} /^\\.ends/{{if(p)print \"\"; p=0}}' "
              f"{STD_SPICE}")
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", cfg["host"], script], capture_output=True, timeout=120, check=True)
    text = out.stdout.decode("latin1")
    if subckt_names(text) != {c.upper() for c in cells}:
        raise ValueError("Missing standard-cell bodies: " + str(sorted({c.upper() for c in cells} - subckt_names(text))))
    return text


def build(base, oreg_cdl, contents):
    head, sep, tail = base.partition(f".SUBCKT {TOP} ")
    if not sep:
        raise ValueError("No chip top in the base source")
    body, sep2, rest = tail.partition(f".ENDS {TOP}")
    if not sep2:
        raise ValueError("No chip top end")
    blocks = [oreg_cdl.strip()]
    for _, name, _ in OBJECTS:
        text = lvs_source(contents[name])
        blocks.append("\n".join(l for l in text.splitlines() if not l.startswith(".INCLUDE")).strip())
    defined = subckt_names(head)
    used = set(re.findall(r"(?m)^X\S+[^\n]*[ \t]([A-Z0-9_]+BWP12T30P140)[ \t]*$", "\n".join(blocks)))
    missing = {c for c in used if c.upper() not in defined}
    std = std_bodies(missing)
    inst = [f"XOUT_REG {' '.join(XOREG)} sar8_out_reg"]
    for n, o, p in OBJECTS:
        # Each object's ports are the chip nets it joins, in its subcircuit's order (that order follows the cell's
        # terminals, so it can differ between revisions of a cell).
        ports = [t["net"] for t in contents[o]["terminals"]]
        if sorted(ports) != sorted(p):
            raise ValueError(f"{o}: ports {ports} differ from the chip nets {p}")
        inst.append(f"{n} {' '.join(ports)} {contents[o]['cell']}")
    text = (head + f"* Standard-cell bodies added for the output register: {', '.join(sorted(missing))}\n" + std + "\n"
            + "\n\n".join(blocks) + "\n\n" + sep + body.rstrip("\n") + "\n" + "\n".join(inst) + "\n" + sep2 + rest)
    text = text.replace("* LVS source of sar8_adc_chip: Layout/design/chip_lvs_source.py",
                        "* LVS source of sar8_adc_chip/layout_full: Layout/design/chip_full_source.py on "
                        "Layout/design/chip_lvs_source.py", 1)
    return text, sorted(missing)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="the partial assembly's chip source (CDL)")
    ap.add_argument("--register", required=True, help="sar8_out_reg.cdl from Layout/design/output_register.py convert")
    ap.add_argument("--contents", required=True, help="directory with content_<object>.json")
    ap.add_argument("--objects-rev", type=int, choices=(1, 2), default=1,
                    help="2: the grown pad decaps and moved analog clamp (content_<object>_r2.json)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    suffix = "_r2" if a.objects_rev == 2 else ""
    contents = {o: json.loads((Path(a.contents) / f"content_{o}{suffix}.json").read_text(encoding="utf-8"))
                for _, o, _ in OBJECTS}
    text, missing = build(Path(a.base).read_text(encoding="latin1"), Path(a.register).read_text(encoding="ascii"), contents)
    Path(a.out).write_text(text, encoding="latin1", newline="\n")
    print(json.dumps(dict(out=a.out, sha256=hashlib.sha256(text.encode("latin1")).hexdigest(), std_added=missing,
                          lines=len(text.splitlines())), indent=1))


if __name__ == "__main__":
    main()
