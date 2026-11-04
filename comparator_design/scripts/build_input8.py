"""Only M8/M9 multi4 -> multi8 relative to frozen A4."""
import json,re,hashlib
from setup import W,ROOT,write,recipe

tag='A4I8';run='cmpdesign-input-a4i8-ff-hot-v1'
base=W/'testbenches/cmpdesign-precharge-a4-ff-hot-v1';dest=W/'testbenches'/run
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
original=(base/'dut.scs').read_text()
dut,count=re.subn(r'(?m)^(M[89] .*?)\bmulti=4\b',r'\1multi=8',original)
assert count==2
assert re.sub(r'(?m)^(M[89] .*?)\bmulti=8\b',r'\1multi=4',dut)==original
for m in ['M3','M5']:
    line=re.search(r'^'+m+r' .*$',dut,re.M).group(0)
    assert all(x in line for x in ['w=100n','l=30n','nf=1','multi=1'])
for m in ['M2','M4']:assert 'multi=4' in re.search(r'^'+m+r' .*$',dut,re.M).group(0)
write(dest/'dut.scs',dut.replace('cmp_A4','cmp_'+tag))
write(dest/'models.scs',(base/'models.scs').read_text())
deck=(base/'test.scs').read_text().replace('A4',tag)
extra=['X'+tag+'_held.'+m+':'+str(port) for m,port in [('M5',1),('M9',1),('M7',3),('M8',2),('M9',2)]]
assert deck.replace(tag,'A4')==(base/'test.scs').read_text()
write(dest/'test.scs',deck+'save '+' '.join(extra)+'\n')
cfg=json.loads((base/'measure.json').read_text().replace('A4',tag))
cfg['run_id']=run;cfg['candidates'][tag]['input']=8;cfg['signals']+=extra
assert cfg['candidates'][tag]['precharge']==1 and cfg['candidates'][tag]['precharge_latch']==4
cfg['single_variable']={'source_run_id':'cmpdesign-precharge-a4-ff-hot-v1','devices':['M8','M9'],'old_multi':4,'new_multi':8,'M2_M4_multi':4,'M3_M5_multi':1,'M3_M5_L_nm':30,'M3_M5_W_nm':100}
write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
recipe(run,dest,cfg['signals'],cfg['stop_s'],'precharge_b_reduce.py',{'corner':'ff','vdd':.99,'temperature_c':125,'single_variable':cfg['single_variable'],'noise':False,'mismatch':False,'PEX':False})
write(dest/'validation.json',json.dumps({'only_M8_M9_multi_changed':True,'TB_identical_except_name_and_observation':True,'geometry_unchanged':True,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}},indent=2)+'\n')
print('A4I8 length/width/multiplicity and full TB equality checks passed; only M8/M9 multi changed.')
