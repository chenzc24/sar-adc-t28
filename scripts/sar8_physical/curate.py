"""Split a verified run into unchanged DUT, external TB and run setup."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument("name");a=p.parse_args()
folder=ROOT/"output/sar8_physical/runs"/a.name
result=json.loads((folder/"result.json").read_text());assert result["ok"]
context=json.loads((folder/"context.json").read_text())
source=folder/(a.name+".scs");text=source.read_text()
matches=list(re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1[^\r\n]*",text));assert matches
dut=text[matches[0].start():matches[-1].end()]+"\n"
tail=text[matches[-1].end():]
tb,options=re.split(r"(?m)(?=^simulatorOptions options)",tail,maxsplit=1)
header=text[:matches[0].start()]
header=re.sub(r"(?m)^//.*\n","",header)
dest=ROOT/"netlist/sar8_physical";dest.mkdir(parents=True,exist_ok=True)
files={"dut.scs":"// MOS terminal order: D G S B (drain gate source bulk/body)\n"+dut,
       "tb.scs":"// External interface sources / impedances / loads only.\n"+tb,
       "tt_nominal.scs":"// OA-derived full-parameter nominal test. Foundry models are not distributed.\n"+header+
                       'include "dut.scs"\ninclude "tb.scs"\n'+options}
for name,body in files.items():
    # Mechanical whitespace cleanup only; retain all device parameters.
    (dest/name).write_text("\n".join(line.rstrip() for line in body.splitlines())+"\n",encoding="utf-8")
canonical=lambda s:re.sub(r"\s+"," ",re.sub(r"\\\n\s*"," ",s)).strip()
curated=(dest/"dut.scs").read_text().split("\n",1)[1]
assert canonical(curated)==canonical(dut)
export=Path(context["source"])
assert hashlib.sha256(export.read_bytes()).hexdigest()==context["source_sha256"]
raw=export.read_text();raw_defs=list(re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1[^\r\n]*",raw))
assert canonical(dut)==canonical(raw[raw_defs[0].start():raw_defs[-1].end()])
receipt=dict(source_run=a.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
             DUT_unchanged=True,MOS_CDF_tails_preserved=True,
             DUT_identical_to_OA_export=True,OA_export_sha256=context["source_sha256"],
             files={name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in files})
(dest/"provenance.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
