"""Combine the two authorized size changes, all other frozen bytes preserved."""
import json,re,hashlib
from setup import W,ROOT,write,recipe
run='cmpdesign-edge-b2i2-ff-hot-v1'
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
base=W/'testbenches/cmpdesign-r200-f500-a4-ff-hot-v1';dest=W/'testbenches'/run
original=(base/'dut.scs').read_text();dut=original
for dev,old in [('M3',1),('M5',1),('M8',4),('M9',4)]:
    line=re.search(r'^'+dev+r' .*$',dut,re.M).group(0)
    assert 'multi=%d '%old in line
    dut=dut.replace(line,line.replace('multi=%d '%old,'multi=2 '))
assert sum(a!=b for a,b in zip(original.splitlines(),dut.splitlines()))==4
write(dest/'dut.scs',dut)
for n in ['test.scs','models.scs']:write(dest/n,(base/n).read_text())
cfg=json.loads((base/'measure.json').read_text());cfg.pop('single_variable',None)
cfg.update(run_id=run,combined_changes={'source_run_id':base.name,'M3_M5_multi':'1->2','M8_M9_multi':'4->2','all_sources_identical':True})
write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge500_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,M3_M5_multi=2,M8_M9_multi=2,noise=False,mismatch=False,PEX=False))
write(dest/'validation.json',json.dumps(dict(only_four_multi_changed=True,all_sources_identical=True,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
print(run,'frozen')
