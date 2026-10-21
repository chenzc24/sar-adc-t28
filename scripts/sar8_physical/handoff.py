"""Measure reference handoff skew from an exact saved integrated record."""
import argparse
import numpy as np
from analyze import load,edge

p=argparse.ArgumentParser();p.add_argument("name");p.add_argument("--frame",type=int,default=1);a=p.parse_args()
folder,r,w=load(a.name);t=w["time"]*1e9
u=edge(t,w["xdut.phi_u"]);u=u[(u>100*a.frame+40)&(u<100*a.frame+60)][0]
mask=(t>=u-.1)&(t<=u+1)
def cross(key,level,rise):
    tm=t[mask];v=w[key][mask]
    ids=np.flatnonzero((v[:-1]<level)&(v[1:]>=level) if rise else (v[:-1]>level)&(v[1:]<=level))
    if not len(ids):return None
    i=ids[0];return float(tm[i]+(level-v[i])*(tm[i+1]-tm[i])/(v[i+1]-v[i]))
for key,level,rise in (("xdut.xref.q7",.45,False),("xdut.xref.q6",.45,True),
                       ("xdut.gnp7",.6,True),("xdut.gnn7",.3,True),
                       ("xdut.gnp6",.6,False),("xdut.gnn6",.3,False),
                       ("xdut.xcdac.bn7",.81,False),("xdut.xcdac.bn6",.09,True)):
    print("CROSS",key,level,"rise" if rise else "fall",cross(key,level,rise))
for key in ("xdut.topp","xdut.topn","xdut.xcdac.bn7","xdut.xcdac.bp7"):
    v=w[key][mask];tm=t[mask];hi=int(np.argmax(v));lo=int(np.argmin(v))
    print("EXTREMA",key,"max",float(v[hi]),float(tm[hi]),"min",float(v[lo]),float(tm[lo]))
