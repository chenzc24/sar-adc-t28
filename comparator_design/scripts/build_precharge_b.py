"""Fix A4; vary only M3/M5 multiplicity. Existing sources are immutable."""
import json,re,hashlib
from setup import W,ROOT,write,recipe
import build_sizing as b
base=W/'testbenches/cmpdesign-precharge-a4-ff-hot-v1'
original=(base/'dut.scs').read_text();base_deck=(base/'test.scs').read_text()
b.GROUPS['precharge_latch']=['M2','M4'];b.GROUPS['precharge']=['M3','M5']
for multi in [2,4]:
    candidate='A4B'+str(multi);run='cmpdesign-precharge-'+candidate.lower()+'-ff-hot-v1';dest=W/'testbenches'/run
    assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
    b.CANDIDATES[candidate]=dict(b.CANDIDATES['I4'],precharge_latch=4,precharge=multi)
    b.build(run,[candidate],'ff',.99,125)
    target=(dest/'dut.scs').read_text().replace('cmp_'+candidate,'cmp_A4')
    assert re.sub(r'(?m)^(M[35] .*?)multi='+str(multi)+r'\b',r'\1multi=1',target)==original
    assert (dest/'models.scs').read_bytes()==(base/'models.scs').read_bytes()
    currents=['X'+candidate+'_held.'+m+':'+str(port) for m,port in [('M6',2),('M0',2),('M7',1),('M1',1),('M4',1),('M13',2),('M14',2)]]
    deck=(dest/'test.scs').read_text()+'save '+' '.join(currents)+'\n'
    assert deck.replace(candidate,'A4')==base_deck,'TB differs'
    extra=['X'+candidate+'_held.'+m+':'+str(port) for m,port in [('M5',1),('M9',1),('M7',3)]]
    deck+='save '+' '.join(extra)+'\n';write(dest/'test.scs',deck)
    cfg=json.loads((dest/'measure.json').read_text());cfg['signals']+=currents+extra
    cfg['single_variable']={'source_run_id':'cmpdesign-precharge-a4-ff-hot-v1','source_candidate':'A4','devices':['M3','M5'],'old_multi':1,'new_multi':multi,'M2_M4_multi':4}
    write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
    recipe(run,dest,cfg['signals'],cfg['stop_s'],'precharge_b_reduce.py',{'corner':'ff','vdd':.99,'temperature_c':125,'single_variable':cfg['single_variable'],'noise':False,'mismatch':False,'PEX':False})
    write(dest/'validation.json',json.dumps({'only_M3_M5_multi_changed':True,'models_identical':True,'complete_TB_identical_except_observations_and_name':True,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs']}},indent=2)+'\n')
source='cmpdesign-precharge-a4-ff-hot-v1';run='cmpdesign-a4-start-reset-review-v1'
r=json.loads((W/'recipes'/(source+'.yaml')).read_text());r.update(run_id=run,kind='analysis_only',source_run_id=source,analyzer='precharge_b_reduce.py')
for key in ['entry','spectre_args']:r.pop(key,None)
r['inputs']=[{'source':'comparator_design/scripts/'+n,'name':n} for n in ['precharge_b_reduce.py','native_frames.py']];r['resources']['max_output_mib']=32
assert not (ROOT/'management/runs'/(run+'.yaml')).exists()
write(W/'recipes'/(run+'.yaml'),json.dumps(r,indent=2)+'\n')
print('Both single-variable checks passed; A4 baseline review is analysis-only.')
