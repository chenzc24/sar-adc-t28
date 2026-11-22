"""Record of the core LVS of sar8_adc_core (Stage 5) from a fetched toplevel_physical lvs run.

Writes Layout/results/toplevel_lvs.json: the compared view and its layout.oa hash, the source netlist and how it was
built (Layout/design/toplevel_lvs_source.py), the deck changes (HCELLs, VIRTUAL CONNECT NAME), the verdict of every
compared cell, and the top cell's object counts before and after transformation with its warnings.
"""
import argparse
import datetime
import hashlib
import json
import re

from Layout.design.toplevel_route import WORK
from Layout.project import ROOT, write_json


def table(block):
    rows = {}
    for line in block.splitlines():
        m = re.match(r"^\s*(Ports|Nets|Instances|Total Inst):\s+(\d+)\s+(\d+)\s*\*?\s*(.*)$", line) or \
            re.match(r"^\s{10,}(\d+)\s+(\d+)\s*\*?\s+(\S.*)$", line)
        if not m:
            continue
        if len(m.groups()) == 4:
            key = m.group(1) if m.group(1) != "Instances" else "Instances " + m.group(4).strip()
            rows[key.strip()] = [int(m.group(2)), int(m.group(3))]
        else:
            rows["Instances " + m.group(3).strip()] = [int(m.group(1)), int(m.group(2))]
    return rows


def top_summary(rep, top):
    i = rep.index("CELL COMPARISON RESULTS ( TOP LEVEL )")
    j = rep.index("INFORMATION AND WARNINGS", i)
    head = rep[i:j]
    initial = head[head.index("INITIAL NUMBERS OF OBJECTS"):head.index("NUMBERS OF OBJECTS AFTER TRANSFORMATION")]
    after = head[head.index("NUMBERS OF OBJECTS AFTER TRANSFORMATION"):]
    warnings = sorted(set(w.strip() for w in re.findall(r"(?m)^\s*Warning:\s*(.*)$", head)))
    return dict(layout=re.search(r"LAYOUT CELL NAME:\s*(\S+)", head).group(1), initial=table(initial), after=table(after),
                warnings=warnings)


def build(args):
    m = json.loads((WORK / args.lvs / "manifest.json").read_bytes())
    rep = (WORK / args.lvs / "lvs/lvs.rep").read_text(encoding="utf-8", errors="replace")
    source = (ROOT / args.source).read_bytes()
    deck = m["decks"]["lvs"]
    return dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_lvs_record.py",
        stage="Stage 5 of chenzc24/sar-adc-t28#12: top-level LVS of the ADC core",
        cellview=dict(library="SAR_ADC_T28_LAYOUT", cell="sar8_adc_core", view=m["source"]["view"],
                      layout_oa_sha256=m["source"]["layout_oa_sha256"], stream_sha256=m["gds"]["sha256"]),
        source_netlist=dict(path=args.source, generator="Layout/design/toplevel_lvs_source.py",
                            sha256=hashlib.sha256(source).hexdigest(),
                            uploaded_sha256=m.get("source_netlist", {}).get("sha256"),
                            block_references=json.loads((ROOT / args.source_info).read_bytes())["references"]
                            if args.source_info else None),
        deck=dict(path=deck["path"], sha256=deck["sha256"], job_sha256=deck["job_sha256"], hcells=deck.get("hcells"),
                  virtual_connect_name=deck.get("virtual_connect_name"),
                  well_diodes="LVS FILTER D(pnwdio) LAYOUT OPEN (installed deck)"),
        evidence=dict(lvs=args.lvs, host="thu-wei"),
        verdict=m["checks"]["lvs"]["verdict"], cells=m["checks"]["lvs"]["cells"],
        top=top_summary(rep, "sar8_adc_core"),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lvs", required=True, help="evidence ID of the lvs run")
    ap.add_argument("--source", required=True, help="the uploaded source netlist")
    ap.add_argument("--source-info", help="JSON that toplevel_lvs_source.py printed")
    ap.add_argument("--out", default="Layout/results/toplevel_lvs.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    print(json.dumps(dict(verdict=record["verdict"], top=record["top"]), indent=1))


if __name__ == "__main__":
    main()
