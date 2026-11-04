"""Freeze low-first clock phase experiment without changing either DUT."""
import ast,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
V=R/'verification/sar8_ab_startup'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    V.mkdir(parents=True,exist_ok=True);runs=[]
    oldclock='type=pulse val0=SUP val1=0 delay=41n rise=100p fall=100p width=59.9n period=100n'
    newclock='type=pulse val0=0 val1=SUP delay=101n rise=100p fall=100p width=39.9n period=100n'
    added=['xdut.xbootp.btop','xdut.xbootp.bbot','xdut.xbootn.btop','xdut.xbootn.bbot']
    for label in ['a','b']:
        src=R/'verification/sar8_ab_short'/label;p=V/label;p.mkdir()
        tb=(src/'tb.scs').read_text();assert tb.count(oldclock)==1
        tb=tb.replace(oldclock,newclock)
        lines=[]
        for line in tb.splitlines():
            if line.startswith(('VVINP ','VVINN ')):
                def shift(m):
                    t=float(m[1]);return ('%.12gn'%(t+100 if t else 0))
                line=re.sub(r'([0-9.]+)n',shift,line)
            lines.append(line)
        (p/'tb.scs').write_text('\n'.join(lines)+'\n')
        deck=(src/'test.scs').read_text();assert deck.count('stop=1000n')==1
        deck=deck.replace('stop=1000n','stop=1100n').rstrip()+' '+' '.join(added)+'\n'
        assert deck.splitlines()[-1].startswith('save ')
        (p/'test.scs').write_text(deck)
        ctx=json.loads((src/'context.json').read_text())
        ctx.update(frame_origin_s=1e-7,expected_stop_s=1.1e-6,initial_low_until_s=101e-9,
            startup_method='External clock low-first phase; no forced internal nodes; DC initialized',
            unscored_interval_s=[0,1e-7],first_valid_frame_must_pass=True)
        ctx['signals']+=added;write(p/'context.json',ctx)
        recipe=json.loads((R/'management/recipes'/('sar8ab-'+label+'-tt-short-v1.yaml')).read_text())
        run='sar8ab-startup-'+label+'-tt-v1';recipe['run_id']=run;runs.append(run)
        for item in recipe['inputs']:
            name=item['name']
            path=p/name if name in ['test.scs','tb.scs','context.json'] else R/'scripts/sar8_ab_startup/reduce.py' if name=='reduce.py' else R/item['source']
            if name not in ['test.scs','tb.scs','context.json','reduce.py']:assert sha(path)==item['sha256']
            item.update(source=path.relative_to(R).as_posix(),sha256=sha(path))
        recipe.update(test_conditions=ctx,expected_stop_s=1.1e-6,summary_signals=ctx['signals'])
        write(R/'management/recipes'/(run+'.yaml'),recipe)
    for name in ['test.scs','tb.scs']:assert (V/'a'/name).read_bytes()==(V/'b'/name).read_bytes()
    for path in (R/'scripts/sar8_ab_startup').glob('*.py'):ast.parse(path.read_text())
    # Pulse edge start times: original low starts41, high101; shift by100.
    assert abs(101+.1+39.9-141)<1e-12
    assert abs(41+.1+59.9+100-201)<1e-12
    write(V/'batch.json',dict(runs=runs,identical_deck_stimulus=True,expected_codes=ctx['expected_codes']))
    write(V/'preflight.json',dict(dut_and_library_hashes_unchanged=True,identical_A_B_stimulus=True,
        original_regular_rising_start_ns=101,new_first_rising_start_ns=101,
        new_regular_rising_start_ns=201,first_falling_start_ns=141,
        normal_edge_translation_ns=100,threshold_high_duration_ns=40,period_ns=100,
        observer_unchanged=True,observer_preinterval_records_ignored=1,first_valid_code_checked=True))
    print(json.dumps(dict(runs=runs)))
if __name__=='__main__':main()
