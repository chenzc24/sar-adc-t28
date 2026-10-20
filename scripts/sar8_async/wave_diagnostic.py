"""Read rejected waveform quality without repairing/nonfinite-filling it."""
import json
from pathlib import Path
import sys
import numpy as np
from oa import OUT,dump
from simulate import validate_vectors
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
name=sys.argv[1]
r=json.loads((OUT/"results"/(name+".json")).read_text(encoding="utf-8"))
raw=Path(r["metadata"]["output_dir"])
files=list(raw.glob("*tran*"));print([p.name for p in files])
rows=[]
for p in files:
    parsed=parse_spectre_psf_ascii(p)
    for k,v in parsed.data.items():
        if isinstance(v,list) and len(v)>1:
            a=np.asarray(v,dtype=float);bad=np.where(~np.isfinite(a))[0]
            if len(bad):rows.append(dict(file=p.name,net=k,count=len(bad),length=len(v),first_index=int(bad[0])))
dump("diagnostic/"+name+"_nonfinite.json",rows);print(json.dumps(rows,indent=2))
if "--recover-traces" in sys.argv:
    assert len(files)==1
    data=parse_spectre_psf_ascii(files[0]).data
    text=(OUT/"decks"/(name+".scs")).read_text(encoding="utf-8")
    vectors,validation=validate_vectors(data,text)
    r["waveform_validation"]=validation
    dump("results/"+name+".json",r);dump("waves/"+name+".json",vectors)
    print("RECOVERED_REQUESTED_TRACES",validation)
