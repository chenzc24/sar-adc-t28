"""Read-only installed PDK width-domain audit; export derived bounds, not model bodies."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

W = Path(__file__).resolve().parents[1]
base = W / 'testbenches/cmpdesign-precharge-a4-ff-hot-v1'
deck = (base / 'models.scs').read_text()
wrapper = re.search(r'include "([^"]+)"', deck).group(1)
remote = r'''
import os,re,json,hashlib
wrapper=os.path.realpath(WRAPPER)
root=os.path.dirname(os.path.dirname(os.path.dirname(wrapper)))
leaf=os.path.join(os.path.dirname(wrapper),'cln28ull_1d8_elk_v1d8_3.scs')
s=open(leaf).read(); ws=open(wrapper).read()
assert os.path.basename(leaf) in ws
a=s.index('inline subckt pch_mac '); b=s.index('.model pch.global',a)
block=s[a:b]
assert "w0='w/nf*factor*1e6'" in block
assert 'pch w=w+dw*nf l=ll' in block
assert '+dl=0 dw=0' in block
assert '.param factor_mos=0.9' in s
bins=[]
pattern=r'\.model pch\.(\d+) pmos \(\s*lmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+lmax\s*=\s*\x27?([\deE.+-]+)\x27?\s*\+wmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+wmax\s*=\s*\x27?([\deE.+-]+)'
for m in re.finditer(pattern,s):
    lo,hi,wlo,whi=map(float,m.groups()[1:])
    if lo-1e-18<=27e-9<=hi+1e-18:
        bins.append(dict(bin=int(m.group(1)),line=s.count('\n',0,m.start())+1,scaled_length_nm=[lo*1e9,hi*1e9],scaled_width_nm=[wlo*1e9,whi*1e9]))
assert bins
minimum=min(x['scaled_width_nm'][0] for x in bins)
paths=[wrapper,leaf,os.path.join(root,'tsmcN28/setting')]
result=dict(device='pch_mac',netlist_L_nm=30,netlist_W_nm=100,nf=1,multi=1,scale=0.9,
    bins_at_scaled_L27nm=bins,minimum_scaled_W_nm=minimum,minimum_netlist_W_nm=minimum/0.9,
    sources=[dict(path=p,sha256=hashlib.sha256(open(p,'rb').read()).hexdigest()) for p in paths])
result['candidate_widths']=[dict(netlist_W_nm=w,scaled_W_nm=w*.9,model_bin_covered=any(x['scaled_width_nm'][0]-1e-9<=w*.9<=x['scaled_width_nm'][1]+1e-9 for x in bins)) for w in [50,60,75,80,90,100]]
print(json.dumps(result))
'''.replace('WRAPPER', repr(wrapper))
p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'thu-wei', 'python', '-'], input=remote, text=True, capture_output=True, timeout=60, check=True)
data = json.loads(p.stdout)
log = (W/'results/cmpdesign-precharge-a4-ff-hot-v1/spectre.out').read_text()
assert re.search(r'scalefactor\s*=\s*0\.9\b', log)
dut = (base/'dut.scs').read_text()
for name in ['M3','M5']:
    line = re.search(r'^'+name+r' .*$', dut, re.M).group(0)
    assert 'w=100n' in line and 'l=30n' in line and 'multi=1' in line and 'nf=1' in line
for name in ['M2','M4']:
    assert 'multi=4' in re.search(r'^'+name+r' .*$', dut, re.M).group(0)
data.update(source_run_id='cmpdesign-precharge-a4-ff-hot-v1',
    observed_native_scalefactor=0.9, M2_M4_multi=4,
    smaller_width_sweep_submitted=False,
    decision='Current W100nm is the installed pch model-bin lower boundary at L30nm. No smaller supported width to sweep.',
    scope='Model applicability audit, not a PCell callback or physical DRC signoff. Encrypted callback/PCell implementation was not decoded.',
    local_source_sha256={n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs']})
out=W/'results/precharge_width_legality.json'
out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(json.dumps(data,indent=2))
