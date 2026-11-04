"""Two independent multi-only experiments with frozen 200/500ps sources."""
import json,re,hashlib
from setup import W,ROOT,write,recipe

base=W/'testbenches/cmpdesign-r200-f500-a4-ff-hot-v1'
for tag,devices,oldmulti in [('b2',['M3','M5'],1),('i2',['M8','M9'],4)]:
    run='cmpdesign-edge-'+tag+'-ff-hot-v1'
    assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
    dest=W/'testbenches'/run;original=(base/'dut.scs').read_text();dut=original
    for dev in devices:
        line=re.search(r'^'+dev+r' .*$',dut,re.M).group(0)
        assert 'multi=%d '%oldmulti in line
        dut=dut.replace(line,line.replace('multi=%d '%oldmulti,'multi=2 '))
    changed=[(a,b) for a,b in zip(original.splitlines(),dut.splitlines()) if a!=b]
    assert len(changed)==2 and all(b==a.replace('multi=%d '%oldmulti,'multi=2 ') for a,b in changed)
    write(dest/'dut.scs',dut)
    for n in ['test.scs','models.scs']:write(dest/n,(base/n).read_text())
    cfg=json.loads((base/'measure.json').read_text())
    cfg.update(run_id=run,single_variable=dict(source_run_id=base.name,devices=devices,old_multi=oldmulti,new_multi=2,all_sources_identical=True))
    write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
    recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge500_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,changed_devices=devices,multi=2,noise=False,mismatch=False,PEX=False))
    write(dest/'validation.json',json.dumps(dict(changed_devices=devices,only_multi_changed=True,all_sources_identical=True,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
    print(run,'frozen',devices)
