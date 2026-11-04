"""Native streaming TT A/B measurements; Python2.7/3, no complete-waveform arrays."""
from __future__ import print_function
import argparse,bisect,csv,json,os,re

EVENTS={'sample':'sample','sample_int':'xdut.sample_int','seq_sample':'xdut.seq_sample',
        'cmp':'xdut.cmp_clk','write':'xdut.xctrl.phi_w','update':'xdut.phi_u','cap':'xdut.xref.cap_clk'}

def samples(path):
    section=None;sweep=None;pending=None;aliases={};values={};t=None;ended=False
    with open(path) as f:
        for raw in f:
            line=raw.strip()
            if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                section=line
                if line=='END':
                    if t is not None:yield t,dict(values)
                    ended=True;break
                continue
            if section not in ['SWEEP','TRACE','VALUE'] or not line.startswith('"'):continue
            _,key,tail=line.split('"',2)
            if section=='SWEEP':
                if sweep is None:sweep=key
            elif section=='TRACE':
                if tail.strip().startswith('GROUP'):pending=key
                else:
                    name=key.replace('\\','').lower();aliases[key]=name
                    if pending is not None:aliases[pending]=name;pending=None
            elif key==sweep:
                new=float(tail.strip())
                if t is not None:
                    assert new>t
                    yield t,dict(values)
                t=new
            else:values[aliases.get(key,key.replace('\\','').lower())]=float(tail.strip())
    assert ended and sweep=='time','Incomplete native file'
