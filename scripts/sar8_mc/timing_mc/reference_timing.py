"""Measure a plateau before the stretched comparator edge and retain all discrepancies."""
from __future__ import print_function
import argparse
import json
import os
from collections import deque
from normal import CLOCK,main as normal,findone
from native_stream import samples

def main():
    normal()
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    dest=a.output_dir+'/result.json'
    r=json.load(open(dest))
    # Spectre emits rows for both selected subcircuit roots as well as descendants.
    scope=r['sampling']
    assert set(scope['non_target_nonzero']).issubset(set(['XDUT.XCDAC','XDUT.XCOMP']))
    assert scope['mom_count']==18 and scope['input_count']==2
    history=deque()
    edges=[b for f in r['frames'] for b in f['bits']]
    idx=0
    for t,v in samples(findone(a.run_dir+'/raw','.tran.tran')):
        top=v['xdut.topp']-v['xdut.topn']
        history.append((t,top))
        while len(history)>1 and history[0][0]<t-0.31e-9:history.popleft()
        if idx<len(edges) and t>=edges[idx]['cmp_s']:
            edge=edges[idx];x=edge['cmp_s']
            early=[z for tau,z in history if x-.25e-9<=tau<=x-.06e-9]
            assert len(early)>=4,'Missing settled plateau samples'
            edge['plateau_pp_v']=max(early)-min(early)
            edge['plateau_v']=sum(early)/len(early)
            idx+=1
    assert idx==len(edges)
    with open(dest,'w') as f:json.dump(r,f,indent=2)
if __name__=='__main__':main()
