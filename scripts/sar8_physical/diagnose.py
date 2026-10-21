"""Inspect actual UPDATE width and word capture in an owned integrated run."""
import argparse
import numpy as np
from analyze import load,edge

p=argparse.ArgumentParser();p.add_argument("name");a=p.parse_args()
folder,r,w=load(a.name);t=w["time"]*1e9
word=lambda prefix,ns:sum((1<<i) for i in range(8) if np.interp(ns,t,w[prefix+str(i)])>.45)
up=edge(t,w["xdut.phi_u"]);down=edge(t,w["xdut.phi_u"],False)
print("CAP_RISES",edge(t,w["xdut.xref.cap_clk"])[:20])
for u in up[:8]:
    d=down[down>u][0]
    print("UPDATE",round(u,6),"width_ps",round((d-u)*1000,3),
          "CODE",[(dt,word("xdut.code",u+dt)) for dt in (0,.02,.05,.1,.15,.2,.3,.5)],
          "REF",word("xdut.xref.q",u+.5))
