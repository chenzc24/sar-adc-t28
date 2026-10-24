"""Scalar real PSF ASCII reader, including TRACE property blocks and GROUP 1."""
from array import array
import numpy as np

def load(path):
    section=None;sweep=None;prop=False;group=None;aliases={};series={};state={};x=array('d');ended=False
    def snapshot():
        assert set(state)==set(series)
        for k in series:series[k].append(state[k])
    with path.open() as f:
        for line in f:
            line=line.strip()
            if line in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
                section=line;prop=False
                if line=='END':
                    if x:snapshot()
                    ended=True;break
                continue
            if not line or section not in ['SWEEP','TRACE','VALUE']:continue
            if prop:
                if line==')':prop=False
                continue
            assert line.startswith('"'),line
            _,key,tail=line.split('"',2);tail=tail.strip()
            if section=='SWEEP':
                assert sweep is None;sweep=key;prop=tail.endswith('PROP(')
            elif section=='TRACE':
                if tail.startswith('GROUP'):
                    assert tail=='GROUP 1';group=key
                else:
                    assert key not in series;series[key]=array('d')
                    if group is not None:aliases[group]=key;group=None
                    prop=tail.endswith('PROP(')
            else:
                value=float(tail.split()[-1])
                if key==sweep:
                    if x:snapshot()
                    x.append(value)
                else:
                    key=aliases.get(key,key);assert key in series
                    state[key]=value
    assert ended and len(x)>1
    w={sweep.lower():np.frombuffer(x,dtype=np.float64)}
    w.update({k.replace('\\','').lower():np.frombuffer(v,dtype=np.float64) for k,v in series.items()})
    assert np.all(np.diff(w[sweep.lower()])>0)
    assert all(len(v)==len(x) and np.all(np.isfinite(v)) for v in w.values())
    return w
