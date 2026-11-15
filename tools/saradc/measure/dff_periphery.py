"""Native isolated DFF timing-order experiment; not an ADC acceptance test."""
from __future__ import print_function
import argparse,json,os
import soa
from native_stream import samples


def analyze(run_dir,output_dir):
    result=soa.analyze(run_dir,output_dir)
    with open(os.path.join(run_dir,'inputs','diagnostic.json')) as f:config=json.load(f)
    with open(os.path.join(output_dir,'terminal_results.json')) as f:terminals=json.load(f)
    cases={}
    for name in config['cases']:
        prefix='xdut.x'+name+'.'
        rows=[r for r in terminals if r['instance'].lower().startswith(prefix)]
        target=next(r for r in rows if r['instance'].lower()==prefix+'xff.mm64' and r['terminal_pair']=='ds')
        cases[name]=dict(mm64=target,violation_pairs=[r for r in rows if r['verdict']=='violation'],samples={})
    targets=[4.5e-9,6.5e-9,7.5e-9,9.9e-9];next_index=0
    previous=None
    for t,values in samples(os.path.join(run_dir,'raw','tran_short.tran.tran')):
        while next_index<len(targets) and t>=targets[next_index]:
            wanted=targets[next_index]
            assert previous is not None
            pt,pv=previous
            fraction=(wanted-pt)/(t-pt)
            for name,row in cases.items():
                prefix='xdut.x'+name+'.'
                row['samples'][str(wanted)]={node:pv[prefix+node]+fraction*(values[prefix+node]-pv[prefix+node]) for node in ('q','d','cdn','cp')}
            next_index+=1
        previous=t,values
    assert next_index==len(targets)
    for row in cases.values():
        row['primed_q_high']=row['samples'][str(targets[0])]['q']>.9*.99
        row['cleared_q_low']=row['samples'][str(targets[1])]['q']<.1*.99
        row['clear_held_after_release']=row['samples'][str(targets[-1])]['q']<.1*.99
    result.update(cases=cases,scope=config['scope'],limitations=config['limitations'])
    result.pop('observer_codes',None);result.pop('observer_codes_pass',None)
    with open(os.path.join(output_dir,'result.json'),'w') as f:json.dump(result,f,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();analyze(a.run_dir,a.output_dir)
