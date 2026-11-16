"""Full-DUT MC evidence and gross timing; Python 2.7/3, bounded streaming."""
from __future__ import print_function
import argparse
import hashlib
import json
import math
import os
import shutil
import reference_short as native


def findone(root,suffix):
    found=[os.path.join(p,n) for p,_,names in os.walk(root) for n in names if n==suffix]
    if len(found)!=1:raise ValueError('Expected one '+suffix+': '+str(found))
    return found[0]


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()


def random_evidence(root,out):
    paths={n:findone(root+'/raw',n) for n in ['mismatch.params','mismatch.values','process.params','process.values']}
    files=[]
    for name,path in sorted(paths.items()):
        if os.path.getsize(path)>8*1024**2:raise ValueError('Unexpectedly large random parameter file')
        shutil.copyfile(path,out+'/'+name)
        files.append(dict(name=name,sha256=digest(path),bytes=os.path.getsize(path)))
    prefixes={'comparator':'XDUT.XCOMP.','cdac':'XDUT.XCDAC.','sar':'XDUT.XCTRL.',
              'reference':'XDUT.XREF.','bootstrap_p':'XDUT.XBOOTP.','bootstrap_n':'XDUT.XBOOTN.',
              'sequence':'XDUT.XSEQ.','sample_clock':'XDUT.XSAMPLE.','idle':'XDUT.XIDLE.'}
    counts={k:0 for k in prefixes};nonzero={k:0 for k in prefixes};outsiders=[];mom=0;ins={};n=0
    # Values are preserved as files; only compact coverage is returned.
    with open(paths['mismatch.params']) as labels,open(paths['mismatch.values']) as values:
        columns=next(labels).split()
        if next(values).strip()!='#1':raise ValueError('Expected exactly MC sample 1')
        for line in labels:
            name=line.strip().upper()
            if not name:continue
            row=[float(x) for x in next(values).split()]
            if len(row)!=len(columns) or any(math.isnan(x) or math.isinf(x) for x in row):raise ValueError('Invalid local draw')
            n+=1;active=any(row)
            for group,prefix in prefixes.items():
                if name.startswith(prefix):counts[group]+=1;nonzero[group]+=int(active)
            if name.startswith('XDUT.XCDAC.CMOM'):mom+=1
            if name in ('XDUT.XCOMP.MNINP','XDUT.XCOMP.MNINN'):ins[name]=row
            # Spectre also emits the DUT root's inherited statistical row.
            if active and name!='XDUT' and not name.startswith('XDUT.'):outsiders.append(name)
        if any(line.strip() for line in values):raise ValueError('Extra local draw rows')
    # This Spectre export has one scalar per label, with no iteration column.
    text=open(paths['process.values']).read()
    numeric=[]
    for line in text.splitlines():
        if line.strip().startswith(('#',';')):continue
        numeric.extend(float(x) for x in line.split())
    if not numeric or any(math.isnan(x) or math.isinf(x) for x in numeric):raise ValueError('Invalid global draw')
    labels=[line for line in open(paths['process.params']) if line.strip() and not line.lstrip().startswith(('#',';'))]
    if len(labels)!=len(numeric):raise ValueError('Global labels/data count differs')
    global_present=bool(numeric) and any(x!=0 for x in numeric)
    local_valid=all(nonzero[k]>0 for k in prefixes) and mom==18 and len(ins)==2 and len(set(tuple(v) for v in ins.values()))==2 and not outsiders
    return dict(valid=global_present and local_valid,global_present=global_present,local_coverage_valid=local_valid,
                coverage_rows=counts,coverage_nonzero_rows=nonzero,mom_instances=mom,instance_rows=n,
                non_dut_nonzero=outsiders[:10],global_numeric_count=len(numeric),files=files,
                process_values_sha256=digest(paths['process.values']),mismatch_values_sha256=digest(paths['mismatch.values']))


def finish(frame,ctx):
    f=native.finish(frame,ctx)
    f['nominal_code_delta']=None if f['code_98'] is None else f['code_98']-f['expected_code']
    f['diagnostic_issues']=f['issues']
    issues=[];screens=[]
    if not f['timing_pass']:issues.append(dict(bit=None,reason='handshake_or_deadline'))
    if not f['observer_crosscheck']:issues.append(dict(bit=None,reason='native_observer_disagreement'))
    for bit in f['bits']:
        if not bit.get('receiver_valid_at_write'):issues.append(dict(bit=bit['bit'],reason='receiver_not_valid_at_write'))
        # Twice the maximum bottom error bounds the differential contribution
        # for ANY positive capacitances, since each side's normalized sum <= 1.
        b=bit['bottom'];bound=None if b is None else 2*b['max_bottom_error_v']/ctx['lsb_v']
        bit['conservative_settling_bound_lsb']=bound
        bit['settling_screen_pass']=bound is not None and bound<=ctx['settling_band_lsb']
        if not bit['settling_screen_pass']:screens.append(dict(bit=bit['bit'],reason='settling_requires_same_draw_reference'))
    f['issues']=issues
    f['settling_review']=screens
    f['pass_function_timing']=not issues and len(f['bits'])==8
    return f


def analyze(root,out):
    evidence=random_evidence(root,out)
    result=native.analyze(root,out,frame_finisher=finish)
    result.update(random_evidence=evidence,
        timing_pass=result['pass_function_timing'],
        settling_screen_pass=all(not f['settling_review'] for f in result['frames']),
        all_screens_pass=evidence['valid'] and result['pass_function_timing'] and all(not f['settling_review'] for f in result['frames']),
        settling_scope=result['context']['settling_scope'],
        limitations=['36 samples are a gross timing regression screen, not yield/sigma evidence',
                     'Fixed nominal centers do not target each sample actual comparator threshold',
                     'Conservative bottom-plate screen does not qualify floating-top kickback or reference accuracy',
                     'Receiver validity uses native 50 percent crossings, not Liberty setup/hold signoff',
                     'No transient noise, PEX, supply ramp or full-terminal qualification'])
    result['first_settling_review']=next((dict(frame=f['frame'],**f['settling_review'][0]) for f in result['frames'] if f['settling_review']),None)
    result['pilot_pass']=bool(evidence['valid'] and result['timing_pass'] and result['settling_screen_pass'])
    with open(out+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir')
    a=p.parse_args();analyze(a.source_run_dir or a.run_dir,a.output_dir)
