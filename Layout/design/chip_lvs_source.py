"""LVS source of the partial chip assembly sar8_adc_chip (Stage 5).

The chip top holds the ring schematic's own netlist (si/auCdl of SAR_ADC_T28_LAYOUT/sar8_io_ring/schematic) inline,
so its internal POC_dig net is a chip-level net like the POC_dig text on the ring's POC rail, and the ADC core
subcircuit of Layout/design/toplevel_lvs_source.py, connected as io_ring.json chip_netlist XADC for the drawn routes
only: VINP, VINN, VREFP, VREFN, VDD! -> AVDD_CORE, 0 -> AVSS_CORE, SAMPLE -> SAMPLE_CORE. D0-D7 of the core (ADC_D0-7)
end there, as the output register is not drawn. The IO cells come from the IO library's SPICE netlist, included
the way the ring's own LVS deck includes it.
"""
import argparse
import hashlib
import json
import re

from Layout.project import ROOT

TOP = "sar8_adc_chip"
RING_DECK = ROOT.parent.parent / "t28-ioring/skills/t28-ioring-generator/calibre/T28/_calibre_T28.lvs_"
XADC = {"SAMPLE": "SAMPLE_CORE", "VINN": "VINN", "VINP": "VINP", "VREFP": "VREFP", "VREFN": "VREFN",
        "VDD!": "AVDD_CORE", "0": "AVSS_CORE", **{f"D{k}": f"ADC_D{k}" for k in range(8)}}


def io_spice():
    deck = RING_DECK.read_text(encoding="ascii")
    paths = re.findall(r'"([^"]+)"', re.search(r"(?m)^SOURCE PATH (.*)$", deck).group(1))
    spi = [p for p in paths if p.endswith(".spi")]
    if len(spi) != 1:
        raise ValueError("Expected one IO SPICE netlist in the ring deck's SOURCE PATH")
    return spi[0]


def build(ring_cdl, core_cdl):
    ring = ring_cdl.replace("\n+", " ")
    m = re.search(r"(?ms)^\.SUBCKT sar8_io_ring ([^\n]*)\n(.*?)^\.ENDS", ring)
    ports, body = m.group(1).split(), m.group(2)
    body = [l for l in body.splitlines() if l.strip() and not l.startswith("*")]
    body = [re.sub(r"\bnet(\d+)\b", r"RING_net\1", l) for l in body]
    core = re.search(r"(?m)^\.SUBCKT sar8_adc_core ([^\n]*)$", core_cdl).group(1).split()
    conn = [XADC.get(p, "ADC_" + re.sub(r"[^A-Za-z0-9_]", "_", p)) for p in core]
    lines = [f"* LVS source of {TOP}: Layout/design/chip_lvs_source.py", f'.INCLUDE "{io_spice()}"', "",
             core_cdl.strip(), "",
             f".SUBCKT {TOP} " + " ".join(ports + ["POC_dig"])] + body + [
             "XADC " + " ".join(conn) + " sar8_adc_core", f".ENDS {TOP}", ""]
    return "\n".join(lines), dict(ring_ports=ports, ports=ports + ["POC_dig"], xadc=dict(zip(core, conn)),
                                  ring_instances=len([l for l in body if l.startswith("X")]), io_spice=io_spice())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ring-cdl", required=True)
    ap.add_argument("--core-cdl", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    text, info = build((ROOT / a.ring_cdl).read_text(encoding="latin1"), (ROOT / a.core_cdl).read_text(encoding="ascii"))
    (ROOT / a.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / a.out).write_text(text, encoding="ascii")
    info["sha256"] = hashlib.sha256(text.encode("ascii")).hexdigest()
    print(json.dumps({k: v for k, v in info.items() if k != "xadc"}, indent=1))


if __name__ == "__main__":
    main()
