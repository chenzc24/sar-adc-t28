"""Authorized latch-precharge point: I4 with only M2/M4 multi changed."""
import argparse,hashlib,json,re
from setup import W,ROOT,write,recipe
import build_sizing as b

p=argparse.ArgumentParser();p.add_argument('--multi',type=int,choices=[2,4],default=2)
multi=p.parse_args().multi;candidate='A'+str(multi)
run='cmpdesign-precharge-'+candidate.lower()+'-ff-hot-v1'
dest=W/'testbenches'/run
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered; do not regenerate'
base=dict(b.CANDIDATES['I4'])
b.GROUPS['precharge_latch']=['M2','M4']
b.GROUPS['precharge']=['M3','M5']
b.CANDIDATES[candidate]=dict(base,precharge_latch=multi)
b.build(run,[candidate],'ff',.99,125)
old=W/'testbenches/cmpdesign-b0-i4-ff-hot-v1'
new=(dest/'dut.scs').read_text()
original=re.search(r'subckt cmp_I4\b.*?ends cmp_I4',(old/'dut.scs').read_text(),re.S).group(0)
target=re.search(r'subckt cmp_'+candidate+r'\b.*?ends cmp_'+candidate,new,re.S).group(0).replace('cmp_'+candidate,'cmp_I4')
restored=re.sub(r'(?m)^(M[24] .*?)multi='+str(multi)+r'\b',r'\1multi=1',target)
assert restored==original,'Unexpected topology/geometry change'
assert (dest/'models.scs').read_bytes()==(old/'models.scs').read_bytes()
deck=(dest/'test.scs').read_text();olddeck=(old/'test.scs').read_text()
for name in ['VCK','VTRACK','VIP','VIN','simulatorOptions','tran_test']:
    assert next(l for l in deck.splitlines() if l.startswith(name+' '))==next(l for l in olddeck.splitlines() if l.startswith(name+' '))
currents=['X'+candidate+'_held.'+m+':'+str(port) for m,port in [('M6',2),('M0',2),('M7',1),('M1',1),('M4',1),('M13',2),('M14',2)]]
deck+='save '+' '.join(currents)+'\n';write(dest/'test.scs',deck)
cfg=json.loads((dest/'measure.json').read_text());cfg['signals']+=currents
cfg['single_variable']={'source_run_id':'cmpdesign-b0-i4-ff-hot-v1','source_candidate':'I4','devices':['M2','M4'],'old_multi':1,'new_multi':multi}
write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
recipe(run,dest,cfg['signals'],cfg['stop_s'],'precharge_reduce.py',{'corner':'ff','vdd':.99,'temperature_c':125,'single_variable':cfg['single_variable'],'noise':False,'mismatch':False,'PEX':False})
write(dest/'validation.json',json.dumps({'only_M2_M4_multi_changed':True,'models_identical':True,'sources_clock_solver_identical':True,'output_load_F':cfg['load_F'],'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs']}},indent=2)+'\n')
source='cmpdesign-b0-i4-ff-hot-v1';review='cmpdesign-i4-ffhot-reset-review-v1'
r=json.loads((W/'recipes'/(source+'.yaml')).read_text())
r.update(run_id=review,kind='analysis_only',source_run_id=source,analyzer='precharge_reduce.py')
for key in ['entry','spectre_args']:r.pop(key,None)
r['inputs']=[{'source':'comparator_design/scripts/'+n,'name':n} for n in ['precharge_reduce.py','native_frames.py']]
r['resources']['max_output_mib']=32
if not (W/'recipes'/(review+'.yaml')).exists():write(W/'recipes'/(review+'.yaml'),json.dumps(r,indent=2)+'\n')
print('Single-variable validation passed; baseline review is analysis-only.')
