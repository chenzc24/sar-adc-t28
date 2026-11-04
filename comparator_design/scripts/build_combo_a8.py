"""Only double M2/M4 copies in the frozen combined candidate."""
import json,re,hashlib
from setup import W,ROOT,write,recipe
run='cmpdesign-combo-a8-ff-hot-v1';source='cmpdesign-edge-b2i2-ff-hot-v1'
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
base=W/'testbenches'/source;dest=W/'testbenches'/run
original=(base/'dut.scs').read_text();dut=original
for dev in ['M2','M4']:
    line=re.search(r'^'+dev+r' .*$',dut,re.M).group(0);assert 'multi=4 ' in line
    dut=dut.replace(line,line.replace('multi=4 ','multi=8 '))
assert sum(a!=b for a,b in zip(original.splitlines(),dut.splitlines()))==2
write(dest/'dut.scs',dut)
for n in ['test.scs','models.scs']:write(dest/n,(base/n).read_text())
cfg=json.loads((base/'measure.json').read_text());cfg.pop('combined_changes',None)
cfg.update(run_id=run,single_variable={'source_run_id':source,'M2_M4_multi':'4->8','all_sources_identical':True})
write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge500_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,M2_M4_multi=8,M3_M5_multi=2,M8_M9_multi=2,noise=False,mismatch=False,PEX=False))
write(dest/'validation.json',json.dumps(dict(only_two_multi_changed=True,all_sources_identical=True,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
print(run,'frozen')
