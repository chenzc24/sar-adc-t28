"""Read-only PDK length-selection and width-bin audit; no PDK body export."""
import json
import shlex
from control import PDK,VERIFY,remote,dump

program=r'''
import re,json,hashlib
p=%r+'/models/spectre/cln28ull_1d8_elk_v1d8_3.scs'
s=open(p).read();result={}
for model,width in [('nch',150),('pch',175)]:
 start=s.index('inline subckt '+model+'_mac ')
 end=s.index('.model '+model+'.global',start)
 block=s[start:end]
 lr=re.search(r'(?m)^\.param lrdr1=.*',block).group(0)
 lengths=[float(v)*1000 for v in re.findall(r'lrdr\d+=([\d.]+)',lr)]
 assert all(x in lengths for x in [30,60,90])
 assert ".param l0='l*factor*1e6'" in block
 assert ".param ll='(l+dl)*min(2*lf,1)'" in block
 bins=[]
 for m in re.finditer(r'\.model '+model+r'\.(\d+) [np]mos \(\s*lmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+lmax\s*=\s*\x27?([\deE.+-]+)\x27?\s*\+wmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+wmax\s*=\s*\x27?([\deE.+-]+)',s):
  idx=int(m.group(1));a,b,c,d=map(float,m.groups()[1:])
  for L in [30,60,90]:
   if a-1e-15<=L*.9e-9<=b+1e-15 and c-1e-15<=width*.9e-9<=d+1e-15:
    bins.append(dict(L_nm=L,model_bin=idx,length_scaled_range_nm=[a*1e9,b*1e9],width_scaled_range_nm=[c*1e9,d*1e9]))
 assert set(x['L_nm'] for x in bins)=={30,60,90},bins
 result[model+'_mac']=dict(width_nm=width,listed_short_lengths_nm=lengths,matched_bins=bins,
    length_selection_pass=True,netlist_lengths_nm=[30,60,90],scaled_geometries_nm=[27,54,81])
print(json.dumps(dict(path=p,sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),devices=result)))
'''%PDK
if __name__=='__main__':
    data=json.loads(remote('python -c '+shlex.quote(program)))
    data.update(scope='Model-domain legality: explicit legal short-length list and matching W/L bins. Not physical DRC or PCell readback.',
      geometry_policy='Single electrical variable: only L changes. Frozen OA-exported diffusion/LDE parameters retained; PCell callback/LDE reconciliation required before OA/layout promotion.',
      pdk_read_only=True,OA_changed=False)
    dump(VERIFY/'legality.json',data)
    print(json.dumps(data,indent=2))
