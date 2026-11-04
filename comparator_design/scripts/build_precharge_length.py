"""PDK-domain checked M3/M5 L60/90 sweep, exact A4 single-variable copies."""
import json,re,hashlib,subprocess
from setup import W,ROOT,write,recipe

base=W/'testbenches/cmpdesign-precharge-a4-ff-hot-v1'
obs=W/'testbenches/cmpdesign-precharge-a4b2-ff-hot-v1'
wrapper=re.search(r'include "([^"]+)"',(base/'models.scs').read_text()).group(1)
program=r'''
import os,re,json,hashlib
p=os.path.join(os.path.dirname(os.path.realpath(WRAPPER)),'cln28ull_1d8_elk_v1d8_3.scs')
s=open(p).read();a=s.index('inline subckt pch_mac ');b=s.index('.model pch.global',a);block=s[a:b]
lr=re.search(r'(?m)^\.param lrdr1=.*',block).group(0)
lengths=[float(v)*1000 for v in re.findall(r'lrdr\d+=([\d.]+)',lr)]
assert all(x in lengths for x in [30,60,90])
assert ".param l0='l*factor*1e6'" in block
assert ".param ll='(l+dl)*min(2*lf,1)'" in block
bins=[]
pattern=r'\.model pch\.(\d+) pmos \(\s*lmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+lmax\s*=\s*\x27?([\deE.+-]+)\x27?\s*\+wmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+wmax\s*=\s*\x27?([\deE.+-]+)'
for m in re.finditer(pattern,s):
 lo,hi,wlo,whi=map(float,m.groups()[1:])
 for L in [30,60,90]:
  if lo-1e-18<=L*.9e-9<=hi+1e-18 and wlo-1e-18<=90e-9<=whi+1e-18:
   bins.append(dict(L_nm=L,model_bin=int(m.group(1)),scaled_L_range_nm=[lo*1e9,hi*1e9],scaled_W_range_nm=[wlo*1e9,whi*1e9]))
assert set(x['L_nm'] for x in bins)==set([30,60,90])
print(json.dumps(dict(model_path=p,sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),listed_short_lengths_nm=lengths,bins=bins,pass_model_domain=True)))
'''.replace('WRAPPER',repr(wrapper))
p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python','-'],input=program,text=True,capture_output=True,timeout=60,check=True)
audit=json.loads(p.stdout);audit.update(scope='Model-domain only, no PCell/DRC signoff',geometry_policy='Only L changed; frozen exported junction/LDE parameters retained for electrical isolation',W_nm=100,nf=1,multi=1)
write(W/'results/precharge_length_legality.json',json.dumps(audit,indent=2)+'\n')
original=(base/'dut.scs').read_text()
for L in [60,90]:
 tag='A4L'+str(L);run='cmpdesign-precharge-'+tag.lower()+'-ff-hot-v1';dest=W/'testbenches'/run
 assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
 dut,count=re.subn(r'(?m)^(M[35] .*?)\bl=30n\b',lambda m:m.group(1)+'l='+str(L)+'n',original)
 assert count==2
 assert re.sub(r'(?m)^(M[35] .*?)\bl='+str(L)+r'n\b',r'\1l=30n',dut)==original
 dut=dut.replace('cmp_A4','cmp_'+tag)
 write(dest/'dut.scs',dut);write(dest/'models.scs',(base/'models.scs').read_text())
 deck=(obs/'test.scs').read_text().replace('A4B2',tag)
 # Existing A4B2 adds only three observational currents to the A4 stimulus.
 extra='save '+' '.join('X'+tag+'_held.'+m+':'+str(port) for m,port in [('M5',1),('M9',1),('M7',3)])+'\n'
 assert deck.endswith(extra)
 assert deck[:-len(extra)].replace(tag,'A4')==(base/'test.scs').read_text()
 write(dest/'test.scs',deck)
 cfg=json.loads((obs/'measure.json').read_text().replace('A4B2',tag).replace('a4b2',tag.lower()))
 cfg['candidates'][tag]['precharge']=1
 cfg['single_variable']={'source_run_id':'cmpdesign-precharge-a4-ff-hot-v1','devices':['M3','M5'],'old_L_nm':30,'new_L_nm':L,'W_nm':100,'nf':1,'multi':1,'M2_M4_multi':4,'frozen_diffusion_LDE':True}
 write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
 recipe(run,dest,cfg['signals'],cfg['stop_s'],'precharge_b_reduce.py',{'corner':'ff','vdd':.99,'temperature_c':125,'single_variable':cfg['single_variable'],'noise':False,'mismatch':False,'PEX':False})
 write(dest/'validation.json',json.dumps({'only_M3_M5_L_changed':True,'models_identical':True,'TB_identical_except_name_and_observation':True,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs']}},indent=2)+'\n')
print(json.dumps(audit,indent=2));print('Two length-only decks checked and created; no simulation submitted.')
