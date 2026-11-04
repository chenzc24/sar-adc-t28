"""A4 200/200ps baseline -> rise500, fall500 and both500; fixed edge50."""
import ast,hashlib,json,re
from setup import W,ROOT,write,recipe

base=W/'testbenches/cmpdesign-rise200-fall200-a4-ff-hot-v1'
original=(base/'test.scs').read_text()
line=re.search(r'^VCK .*$',original,re.M).group(0)
tokens=line.split('wave=[')[1].rstrip(']').split()
old=[(float(tokens[i]),float(tokens[i+1])) for i in range(0,len(tokens),2)]
assert len(old)==129
for riseps,fallps in [(500,200),(200,500),(500,500)]:
    run='cmpdesign-r%d-f%d-a4-ff-hot-v1'%(riseps,fallps)
    assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
    dest=W/'testbenches'/run;cfg=json.loads((base/'measure.json').read_text())
    points=list(old);audit=[]
    for i,e in enumerate(cfg['events']):
        k=1+4*i
        for offset,ps,center,volts in [(0,riseps,e['clock50'],(0.,.99)),(2,fallps,e['fall50'],(.99,0.))]:
            assert abs((old[k+offset][0]+old[k+offset+1][0])/2-center)<1e-20
            if ps!=200:
                points[k+offset]=(center-ps*1e-12/2,volts[0]);points[k+offset+1]=(center+ps*1e-12/2,volts[1])
            else:assert points[k+offset:k+offset+2]==old[k+offset:k+offset+2]
        e.update(rise_start=points[k][0],rise_end=points[k+1][0],fall_start=points[k+2][0],fall_end=points[k+3][0])
        assert abs((e['rise_start']+e['rise_end'])/2-e['clock50'])<1e-20
        assert abs((e['fall_start']+e['fall_end'])/2-e['fall50'])<1e-20
        audit.append({key:e[key] for key in ['rise_start','rise_end','clock50','fall_start','fall_end','fall50']})
    assert all(points[i+1][0]>points[i][0] for i in range(len(points)-1))
    new='VCK (CK 0) vsource type=pwl wave=['+' '.join('%.16g %.16g'%p for p in points)+']'
    deck=original.replace(line,new);assert deck.replace(new,line)==original
    for n in ['dut.scs','models.scs']:write(dest/n,(base/n).read_text())
    write(dest/'test.scs',deck)
    cfg.update(run_id=run,rise_time_s=riseps*1e-12,fall_time_s=fallps*1e-12,single_variable={'source_run_id':base.name,'clock_rise_ps':riseps,'clock_fall_ps':fallps,'clock50_fixed':True,'DUT_identical':True})
    write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
    recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge500_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,clock_rise_ps=riseps,clock_fall_ps=fallps,noise=False,mismatch=False,PEX=False))
    write(dest/'validation.json',json.dumps({'only_VCK_line_changed':True,'DUT_identical':True,'events':audit,'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}},indent=2)+'\n')
ast.parse((W/'scripts/edge500_reduce.py').read_text())
print('500/200,200/500,500/500 decks verified; all edge50 fixed; not launched.')
