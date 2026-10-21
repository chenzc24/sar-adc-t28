"""Readback ownership isolation and audit the exact OA-exported DUT hierarchy."""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from circuit import ROOT, LIB, TOP, all_objects
from oa import OUT, builder_module, dump


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(); p.add_argument("--tag", required=True); args=p.parse_args()
    from virtuoso_bridge import VirtuosoClient
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    info=c.library.get(LIB)
    assert info.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library=="tsmcN28"
    b=builder_module()
    from freeze_r0 import schematic_surface, blocks
    unchanged=[]
    for path in sorted((OUT/"baseline").glob("*.json")):
        before=json.loads(path.read_text())
        after=c.schematic.read(LIB,path.stem,include_positions=True,param_filters=None)
        dump(f"postflight/{path.name}",after)
        assert schematic_surface(before)==schematic_surface(after),path.stem
        unchanged.append(dict(cell=path.stem,surface_sha256=sha(schematic_surface(after)),
                              full_readback_identical=sha(before)==sha(after),full_readback_sha256=sha(after)))
    owned=[]
    for obj in all_objects():
        data=b.readback(c,obj)
        owned.append(dict(cell=obj.name,instances=len(data["instances"]),
                          surface_sha256=sha(schematic_surface(data)),full_readback_sha256=sha(data),
                          declarative_source_sha256=sha(dataclasses.asdict(obj)),markers=0))
    path=OUT/"exports/tb_sar_adc8_join_r4"/args.tag/"input.scs"
    raw=path.read_text(); flat=re.sub(r"\\\n\s*"," ",raw)
    definitions=blocks(raw)
    parsed={}
    for name,body in definitions.items():
        # The public blocks helper retains the terminal list in each body;
        # parse instance lines from the unflattened export for traversal.
        match=re.search(rf"(?ms)^subckt {re.escape(name)} .*?^ends {re.escape(name)}",flat)
        assert match,name
        rows=[]
        for line in match[0].splitlines()[1:-1]:
            m=re.match(r"\s*(\w+)\s+\((.*?)\)\s+(\w+)\b(.*)",line)
            if m: rows.append(dict(instance=m[1],nodes=m[2].split(),master=m[3],params=m[4].strip()))
        parsed[name]=rows
    expanded=[]
    def visit(name,instance):
        assert name in parsed,name
        for row in parsed[name]:
            loc=instance+"."+row["instance"]
            if row["master"] in parsed: visit(row["master"],loc)
            else: expanded.append(dict(path=loc,master=row["master"]))
    visit(TOP,"XDUT")
    counts={m:sum(r["master"]==m for r in expanded) for m in sorted({r["master"] for r in expanded})}
    assert set(counts)<= {"nch_mac","pch_mac","nch_18_mac","pch_18_mac","rupolym","cfmom_2t"},counts
    assert "ahdl_include" not in raw
    report=dict(library=LIB,technology=info.technology_library,dut=TOP,export_tag=args.tag,
                export_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                unchanged_dependencies=unchanged,owned_readback=owned,
                expanded_leaf_instances=counts,
                multiplicity_note="Counts are hierarchical declarations, not effective MOS widths or physical unit counts.",
                internal_ideal_control_absent=True,internal_ideal_passives_absent=True,
                subcircuit_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in definitions.items()})
    dump(f"postflight/{args.tag}_audit.json",report)
    print("POSTFLIGHT_OK",counts,flush=True)


if __name__=="__main__":main()
