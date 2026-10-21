"""Python2-compatible bounded PSF-ASCII startup probe; read-only data access."""
from __future__ import print_function
import json
import sys

path=sys.argv[1]
wanted=set(["XDUT.SAMPLE_INT","XDUT.TOPP","XDUT.TOPN","VINP","VINN",
            "XDUT.XREF.CAP_CLK","XDUT.XREF.Q7","XDUT.GPP7","XDUT.GNP7",
            "XDUT.XCDAC.BP7","XDUT.XCDAC.BN7","XDUT.XBOOTP.G","XDUT.XBOOTN.G",
            "XDUT.XCOMP.X","XDUT.XCOMP.Y"])
wanted.update("XDUT.XREF.Q%d"%i for i in range(8))
targets=[0,1,1.1,1.3,1.48,1.54,1.6,2,3,5]
result=[]; extrema={}; current={}; active=False; index=[0]
def consume(row):
    if "time" not in row:return
    t=row["time"]*1e9
    for k in wanted:
        if k not in row:continue
        v=row[k]
        e=extrema.setdefault(k,dict(min_v=v,min_ns=t,max_v=v,max_ns=t))
        if v<e["min_v"]:e.update(min_v=v,min_ns=t)
        if v>e["max_v"]:e.update(max_v=v,max_ns=t)
    while index[0]<len(targets) and t>=targets[index[0]]:
        result.append(dict(requested_ns=targets[index[0]],actual_ns=t,values={k:row[k] for k in wanted if k in row}))
        index[0]+=1
with open(path) as stream:
    for line in stream:
        if not active:
            if line.strip()=="VALUE":active=True
            continue
        parts=line.strip().split()
        if len(parts)!=2:continue
        name=parts[0].strip('"')
        try:value=float(parts[1])
        except ValueError:continue
        if name=="time":
            consume(current)
            if value>6e-9:break
            current={"time":value}
        elif name in wanted:current[name]=value
print(json.dumps(dict(interval_ns=[0,6],sampling="first saved point at or after requested time",rows=result,extrema=extrema)))
