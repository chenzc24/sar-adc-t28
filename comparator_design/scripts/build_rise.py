"""A4 fixed-size rise-only sweep; preserve all 50% and falling-edge times."""
import json,re,hashlib,ast
from setup import W,ROOT,write,recipe

base=W/'testbenches/cmpdesign-precharge-a4-ff-hot-v1'
original=(base/'test.scs').read_text()
oldline=re.search(r'^VCK .*$',original,re.M).group(0)
tokens=oldline.split('wave=[')[1].rstrip(']').split()
old=[(float(tokens[i]),float(tokens[i+1])) for i in range(0,len(tokens),2)]
assert len(old)==129
for ps in [100,200]:
    run='cmpdesign-rise%d-a4-ff-hot-v1'%ps
    assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
    dest=W/'testbenches'/run
    cfg=json.loads((base/'measure.json').read_text())
    points=list(old);audit=[]
    for i,e in enumerate(cfg['events']):
        k=1+i*4
        center=(old[k][0]+old[k+1][0])/2
        assert abs(center-e['clock50'])<1e-20
        points[k]=(center-ps*1e-12/2,0.)
        points[k+1]=(center+ps*1e-12/2,.99)
        assert points[k+2:k+4]==old[k+2:k+4]
        e['rise_start']=points[k][0];e['rise_end']=points[k+1][0]
        assert abs((e['rise_start']+e['rise_end'])/2-e['clock50'])<1e-20
        audit.append({'event':i,'rise_start_s':e['rise_start'],'rise_end_s':e['rise_end'],'clock50_s':e['clock50'],'fall_start_s':old[k+2][0],'fall_end_s':old[k+3][0]})
    newline='VCK (CK 0) vsource type=pwl wave=['+' '.join('%.16g %.16g'%p for p in points)+']'
    deck=original.replace(oldline,newline)
    assert deck.replace(newline,oldline)==original
    for n in ['dut.scs','models.scs']:write(dest/n,(base/n).read_text())
    write(dest/'test.scs',deck)
    cfg['run_id']=run
    cfg['rise_time_s']=ps*1e-12
    cfg['single_variable']={'source_run_id':'cmpdesign-precharge-a4-ff-hot-v1','clock_rise_ps':ps,'clock50_fixed':True,'falling_edge_fixed':True,'DUT_identical':True}
    write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
    recipe(run,dest,cfg['signals'],cfg['stop_s'],'rise_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,noise=False,mismatch=False,PEX=False,single_variable=cfg['single_variable']))
    write(dest/'validation.json',json.dumps({'only_VCK_line_changed':True,'DUT_identical':True,'all32_clock50_and_falling_edges_preserved':True,'events':audit,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}},indent=2)+'\n')

r=json.loads((W/'recipes/cmpdesign-a4-start-reset-review-v1.yaml').read_text())
r['run_id']='cmpdesign-rise50-a4-review-v1'
r['analyzer']='rise_reduce.py'
r['inputs'][0]={'source':'comparator_design/scripts/rise_reduce.py','name':'rise_reduce.py'}
r['qualification_scope']='Read-only original A4 waveforms; same full-edge kick and native startup pulse measurement as rise100/200'
write(W/'recipes'/(r['run_id']+'.yaml'),json.dumps(r,indent=2)+'\n')
ast.parse((W/'scripts/rise_reduce.py').read_text())
print('Two rise-only decks verified; analysis-only baseline bound to completed A4. No simulations launched.')
