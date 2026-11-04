"""A4 rise200 fixed; fall-only sweep centered on original fall50."""
import json,re,hashlib,ast
from setup import W,ROOT,write,recipe

base=W/'testbenches/cmpdesign-rise200-a4-ff-hot-v1'
original=(base/'test.scs').read_text()
oldline=re.search(r'^VCK .*$',original,re.M).group(0)
tokens=oldline.split('wave=[')[1].rstrip(']').split()
old=[(float(tokens[i]),float(tokens[i+1])) for i in range(0,len(tokens),2)]
assert len(old)==129
for ps in [100,200]:
    run='cmpdesign-rise200-fall%d-a4-ff-hot-v1'%ps
    assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
    dest=W/'testbenches'/run
    cfg=json.loads((base/'measure.json').read_text())
    points=list(old);audit=[]
    for i,e in enumerate(cfg['events']):
        k=3+i*4
        center=(old[k][0]+old[k+1][0])/2
        assert abs(center-e['fall50'])<1e-20
        points[k]=(center-ps*1e-12/2,.99)
        points[k+1]=(center+ps*1e-12/2,0.)
        assert points[k-2:k]==old[k-2:k]
        e['fall_start']=points[k][0];e['fall_end']=points[k+1][0]
        assert abs((e['fall_start']+e['fall_end'])/2-e['fall50'])<1e-20
        audit.append({'event':i,'rise_start_s':e['rise_start'],'rise_end_s':e['rise_end'],'clock50_s':e['clock50'],'fall50_s':e['fall50'],'fall_start_s':e['fall_start'],'fall_end_s':e['fall_end']})
    newline='VCK (CK 0) vsource type=pwl wave=['+' '.join('%.16g %.16g'%p for p in points)+']'
    deck=original.replace(oldline,newline)
    assert deck.replace(newline,oldline)==original
    for n in ['dut.scs','models.scs']:write(dest/n,(base/n).read_text())
    write(dest/'test.scs',deck)
    cfg['run_id']=run
    cfg['fall_time_s']=ps*1e-12
    cfg['single_variable']={'source_run_id':'cmpdesign-rise200-a4-ff-hot-v1','clock_rise_ps':200,'clock_fall_ps':ps,'clock50_fixed':True,'rising_edge_fixed':True,'DUT_identical':True}
    write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
    recipe(run,dest,cfg['signals'],cfg['stop_s'],'fall_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,noise=False,mismatch=False,PEX=False,single_variable=cfg['single_variable']))
    write(dest/'validation.json',json.dumps({'only_VCK_line_changed':True,'DUT_identical':True,'all32_clock50_and_rising_edges_preserved':True,'events':audit,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}},indent=2)+'\n')

r=json.loads((W/'recipes/cmpdesign-a4-start-reset-review-v1.yaml').read_text())
r['run_id']='cmpdesign-fall50-a4-review-v1'
r['source_run_id']='cmpdesign-rise200-a4-ff-hot-v1'
r['test_conditions']={'corner':'ff','vdd':.99,'temperature_c':125,'clock_rise_ps':200,'clock_fall_ps':50,'noise':False,'mismatch':False,'PEX':False}
r['analyzer']='fall_reduce.py'
r['inputs'][0]={'source':'comparator_design/scripts/fall_reduce.py','name':'fall_reduce.py'}
r['qualification_scope']='Read-only rise200 fall50 A4 waveforms; common native reset pulse measurement'
write(W/'recipes'/(r['run_id']+'.yaml'),json.dumps(r,indent=2)+'\n')
ast.parse((W/'scripts/fall_reduce.py').read_text())
print('Two fall-only decks verified; baseline analysis bound to completed rise200 A4. No simulations launched.')
