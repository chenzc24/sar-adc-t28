"""Read-only native PSF window export, Python 2/3; original files never changed."""
from __future__ import print_function
import gzip
import hashlib
import json
import os
import sys

source, destination = sys.argv[1:]
assert not os.path.exists(destination)
keys = ['SAMPLE','VDD!','VINP_SRC','VINN_SRC','VINP','VINN','XDUT.TOPP','XDUT.TOPN',
        'XDUT.SEQ_SAMPLE','XDUT.CMP_CLK','VREFP','VREFN']
keys += ['XDUT.XBOOT'+side+'.'+node for side in ['P','N']
         for node in ['G','BTOP','BBOT','CTRL','CLKSB','GRESET']]
keys += ['XDUT.XCDAC.B'+side+str(i) for side in ['P','N'] for i in range(8)]
keep=set(x.lower() for x in keys)
state={}; groups={}; pending=None; section=None; sweep=None; now=None; ended=False
wave={'time':[]}
def snapshot():
    if now is not None and 85e-9 <= now <= 145e-9:
        wave['time'].append(now)
        for key in state:wave.setdefault(key,[]).append(state[key])
path=source+'/test.raw/tran_perf.tran.tran'
h=hashlib.sha256()
with open(path,'rb') as f:
    for raw in f:
        h.update(raw)
        line=raw.decode('ascii').strip()
        if line in ('HEADER','TYPE','SWEEP','TRACE','VALUE','END'):
            section=line
            if line=='END':snapshot();ended=True
            continue
        if not line or section not in ('SWEEP','TRACE','VALUE'):continue
        if section=='SWEEP' and sweep is not None:continue
        _,key,tail=line.split('"',2)
        if section=='SWEEP':sweep=key
        elif section=='TRACE':
            if tail.strip().startswith('GROUP'):pending=key
            else:
                if pending is not None:groups[pending]=key
                pending=None
        elif key==sweep:
            snapshot();now=float(tail.strip())
        else:
            key=groups.get(key,key).replace('\\','').lower()
            if key in keep:state[key]=float(tail.strip())
assert ended and all(len(v)==len(wave['time']) for v in wave.values())
assert keep <= set(wave), sorted(keep-set(wave))
assert all(b>a for a,b in zip(wave['time'],wave['time'][1:]))
result=dict(source=source,native_psf_sha256=h.hexdigest(),native_psf_bytes=os.path.getsize(path),
            window_ns=[85,145],decimated=False,PSF_END=ended,wave=wave)
with gzip.open(destination,'wb',compresslevel=1) as f:
    f.write(json.dumps(result,separators=(',',':')).encode('utf-8'))
print('EXTRACT_OK',len(wave['time']),os.path.getsize(destination))
