"""Small exact-hierarchy/provenance audit; no proprietary content is copied."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import hashlib
import re
from circuit import hierarchy
from netlist_logic import parse
from simulate import source
from oa import OUT,dump


def normalized_blocks(text):
    joined=re.sub(r"\\\n\s*"," ",text)
    return {m[1]:re.sub(r"\s+"," ",m[2]).strip() for m in
            re.finditer(r"(?ms)^subckt (\w+) (.*?)^ends \1",joined)}


def main():
    a=source("tb_sar8a_logic","recovery");b=source("tb_sar8a_strongarm","recovery")
    ab,bb=normalized_blocks(a),normalized_blocks(b);objects={o.name:o for o in hierarchy()}
    assert all(ab.get(n)==bb.get(n) for n in objects),"Logic differs across testbenches"
    before=normalized_blocks(source("tb_sar8a_logic","tgdff"))
    changed=[n for n in objects if before.get(n)!=ab[n]]
    assert changed==["sar8a_status"],changed
    # Unit-characterization evidence is reusable only because each native
    # primitive definition is byte-equivalent after whitespace normalization.
    for name,body in ab.items():
        assert not re.search(r"\b(?:bsource|vsource|sar8a_plant|veriloga)\b",body),name
    def counts(name):
        r=Counter()
        for p in objects[name].parts:
            if p.master in objects:r.update(counts(p.master))
            else:r[p.lib+"/"+p.master]+=1
        return r
    summary=dict(native_cells=len(objects),hierarchy_counts=dict(counts("sar_logic_8b_async")),
                 identical_native_logic_in_both_fixtures=True,behavioral_elements_inside_controller=0,
                 changed_cells_since_tgdff=changed,unchanged_unit_cells=True,
                 hierarchy_sha256=hashlib.sha256(json.dumps({n:ab[n] for n in sorted(objects)},sort_keys=True).encode()).hexdigest())
    dump("audit/hierarchy.json",summary);print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
