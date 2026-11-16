import importlib.util,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/saradc/measure'
sys.path.insert(0,str(P))
import selective_boundary_reduce as pair

def test_pairing_rejects_global_drift_and_extra_local_rows():
    expected=dict(columns=['a'],process_labels=['g'],process=[.7],rows={'XDUT.XCOMP.M1':[.2],'XDUT.XCTRL.M1':[.9]})
    actual=dict(expected,rows={'XDUT.XCOMP.M1':[.2]})
    assert pair.compare_draw(actual,expected,['XDUT.XCOMP'])['valid']
    assert not pair.compare_draw(dict(actual,process=[.8]),expected,['XDUT.XCOMP'])['valid']
    assert not pair.compare_draw(expected,expected,['XDUT.XCOMP'])['valid']
    assert not pair.compare_draw(dict(actual,rows={'XDUT.XCOMP.M1':[.3]}),expected,['XDUT.XCOMP'])['valid']

def test_process_only_rejects_any_device_local_draw():
    expected=dict(columns=['a'],process_labels=['g'],process=[.7],rows={'XDUT.XCOMP.M1':[.2]})
    assert pair.compare_draw(dict(expected,rows={}),expected,[])['valid']
    assert not pair.compare_draw(expected,expected,[])['valid']

def test_pilot_native_disagreement_is_not_a_pass():
    r=[dict(frame=0,code=12,guard_bad=0)]
    assert pair.boundary_check(r,[dict(code_98=12)],True)['valid']
    assert not pair.boundary_check(r,[dict(code_98=13)],True)['valid']

def test_boundary_side_failure_preserved():
    lsb=.00703125;records=[dict(frame=i,code=0,guard_bad=0,input_v=0) for i in range(34)]
    for start,k in [(2,64),(16,128)]:
        center=-.9+k*lsb;lo=center-8*lsb;hi=center+8*lsb;actual=center+.017*lsb
        def point(j,v):records[j].update(input_v=v,code=k if v>=actual else k-1)
        point(start,lo);point(start+1,hi)
        for j in range(start+2,start+10):
            mid=(lo+hi)/2;point(j,mid)
            if mid>=actual:hi=mid
            else:lo=mid
        for j,d in enumerate([-.25,-.1,.1,.25]):point(start+10+j,(lo+hi)/2+d*lsb)
    records[31].update(input_v=(lo+hi)/2-.1*lsb,code=127)
    records[33].update(input_v=(lo+hi)/2+.1*lsb,code=128)
    frames=[dict(code_98=r['code']) for r in records]
    assert pair.boundary_check(records,frames,False)['valid']
    records[12]['code']=64;frames[12]['code_98']=64
    assert not pair.boundary_check(records,frames,False)['valid']
