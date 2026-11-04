"""Reuse native per-frame measurements; adapt MC family paths and capture RVs.

Remote Python2/3; bounded streaming only. No waveform copies or circuit writes.
"""
from __future__ import print_function
import argparse,hashlib,json,os,re,sys
import baseline_reduce as base

def paths(root):
    found=[]
    for d,dirs,files in os.walk(root):
        for n in files:
            if n.endswith('.tran.tran'):found.append(d+'/'+n)
    return found

def mismatch_parameters(root):
    files=[];samples={};count=0
    for d,dirs,names in os.walk(root+'/inputs'):
        dirs[:]=[x for x in dirs if x not in ['input.ahdlSimDB']]
        for n in names:
            if not any(x in n for x in ['mismatch.params','mismatch.values']):continue
            p=d+'/'+n
            if os.path.getsize(p)>16*1024*1024:raise ValueError('Unexpected mismatch file size')
            digest=hashlib.sha256();rows=[]
            with open(p,'rb') as f:
                for line in f:
                    digest.update(line)
                    line=line.decode('ascii','replace').strip()
                    if len(rows)<5:rows.append(line[:250])
                    # Names/values are original sampled parameters, not PDK model source.
                    if 'par_mom' in line.lower() or ('xdut' in line.lower() and len(samples)<40):
                        samples[p.split('/')[-1]+':'+str(count)]=line[:400]
                    count+=1
            files.append({'path':os.path.relpath(p,root),'bytes':os.path.getsize(p),'sha256':digest.hexdigest(),'head':rows})
    return {'files':files,'line_count':count,'selected_parameter_rows':samples}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    a=parser.parse_args();ctx=json.load(open(a.run_dir+'/inputs/context.json'))
    raw=paths(a.run_dir+'/raw');assert len(raw)==1,raw
    # Existing reducer only enumerates the raw root. Redirect that read to the
    # one actual MC-family transient without copying/symlinking original data.
    old_listdir=base.os.listdir;old_samples=base.samples
    def listdir(p):
        if p==a.run_dir+'/raw':return ['MC_SELECTED.tran.tran']
        return old_listdir(p)
    def samples(p):return old_samples(raw[0] if p.endswith('/MC_SELECTED.tran.tran') else p)
    base.os.listdir=listdir;base.samples=samples
    sys.argv=[sys.argv[0],'--run-dir',a.run_dir,'--output-dir',a.output_dir]
    try:base.main()
    finally:base.os.listdir=old_listdir;base.samples=old_samples
    p=a.output_dir+'/result.json';r=json.load(open(p));e=mismatch_parameters(a.run_dir)
    native=[]
    for line in open(a.run_dir+'/spectre.out'):
        if re.search(r'monte carlo|montecarlo|seed|mismatch',line,re.I):native.append(line.strip()[:500])
    r.update(mismatch_evidence=e,native_mc_lines=native[:150],native_transient_path=os.path.relpath(raw[0],a.run_dir),
        native_data_valid=r['native_event_code_crosscheck'],
        protocol_pass=r['startup_timing_pass'] and r['steady_timing_pass'],
        nominal_center_code_deviations=[{'frame':f['frame'],'reference':f['expected_code'],'actual':f['code_98'],
            'delta':f['code_98']-f['expected_code']} for f in r['frames'] if not f['code_pass']],
        statistical_scope='Ten nominal center inputs; code changes measure random circuit variation and require interpretation; not full DNL/INL or yield')
    if ctx['seed'] is not None:assert e['files'],'No saved native mismatch parameters'
    with open(p,'w') as f:json.dump(r,f,indent=2);f.write('\n')
    print('MC_KEY_CODE_ANALYSIS',ctx['seed'],r['protocol_pass'],len(r['nominal_center_code_deviations']))

if __name__=='__main__':main()
