"""Prepare same-seed held-word references. Only the diagnostic quiet delay is lengthened."""
import concurrent.futures
import json
import re
from prepare import REC,ROOT,OUT,register,save,sha

def build_reference(base):
    run=base.replace('sar8tm-','sar8tm-ref-')
    rec=json.loads((REC/(base+'.yaml')).read_text())
    for item in rec['inputs']:
        old=ROOT/item['source']
        assert sha(old)==item['sha256']
        path=OUT/run/item['name']
        if item['name']=='dut.scs':
            txt=old.read_text()
            cell=re.search(r'(?ms)^subckt sar8p_delay_quiet .*?^ends sar8p_delay_quiet',txt).group()
            assert cell.count('multi=30 ')==2
            # Only the two quiet-delay capacitors are changed. They are outside MC DUT.
            save(path,txt.replace(cell,cell.replace('multi=30 ','multi=45 ')))
        elif item['name']=='context.json':
            ctx=json.loads(old.read_text())
            ctx.update(run_id=run,reference_of=base,quiet_load_ratio=1.5,scope='Same-seed independent longer same-word dwell; diagnostic circuit only')
            save(path,ctx)
            rec['test_conditions']=ctx
        elif item['name']=='timing.py':
            path=ROOT/'scripts/sar8_mc/timing_mc/reference_timing.py'
        else:continue
        item.update(source=path.relative_to(ROOT).as_posix(),sha256=sha(path))
    base_analyzer=ROOT/'scripts/sar8_mc/timing_mc/timing.py'
    rec['inputs'].append(dict(source=base_analyzer.relative_to(ROOT).as_posix(),name='normal.py',sha256=sha(base_analyzer)))
    rec.update(run_id=run,qualification_scope='Diagnostic same-word hold reference for '+base)
    save(REC/(run+'.yaml'),rec)
    return run

if __name__=='__main__':
    cold=json.loads((OUT/'cold.json').read_text())
    jobs=[build_reference(base) for base in cold['jobs']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        hashes=dict(zip(jobs,pool.map(register,jobs)))
    save(OUT/'refs.json',dict(jobs=jobs,registered_hashes=hashes,group='refs',agent_sha256=cold['agent_sha256'],base_hashes=cold['registered_hashes']))

