"""Read actual Spectre MC scalar paths; bind analysis to completed source run."""
from __future__ import print_function
import argparse,hashlib,json,math,os,re,sys
import reduce_mc as mc

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()

def evidence(root):
    pairs={};files=[]
    for d,dirs,names in os.walk(root+'/raw'):
        for n in names:
            if n in ['mismatch.params','mismatch.values']:
                p=d+'/'+n;assert os.path.getsize(p)<16*1024**2
                pairs[n]=p;files.append({'path':os.path.relpath(p,root),'bytes':os.path.getsize(p),'sha256':digest(p)})
    if not pairs:return {'files':[],'selected_parameters':{},'mom_count':0,'mos_count':0}
    assert set(pairs)==set(['mismatch.params','mismatch.values'])
    selected={};mom=0;mos=0;rows=0
    with open(pairs['mismatch.params']) as labels,open(pairs['mismatch.values']) as data:
        columns=next(labels).split()
        assert next(data).strip()=='#1'
        names=(x.strip() for x in labels if x.strip())
        vals=(x.strip() for x in data if x.strip())
        for name,line in zip(names,vals):
            row=[float(x) for x in line.split()];assert len(row)==len(columns)
            assert all(not math.isnan(x) and not math.isinf(x) for x in row)
            rows+=1
            if '.CMOM' in name.upper():
                selected[name]={'par_mom':row[columns.index('par_mom')]};mom+=1
            elif '.MNINP' in name.upper() or '.MNINN' in name.upper():
                selected[name]=dict((key,row[columns.index(key)]) for key in ['plo_tox','parl1','parl2','parl3']);mos+=1
    assert mom==18 and mos>=2,(mom,mos)
    return {'files':files,'columns':columns,'instance_rows':rows,'mom_count':mom,'mos_count':mos,
        'selected_parameters':selected,'values_sha256':digest(pairs['mismatch.values'])}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True);a=p.parse_args()
    mc.mismatch_parameters=evidence
    sys.argv=[sys.argv[0],'--run-dir',a.source_run_dir,'--output-dir',a.output_dir]
    mc.main()
    f=a.output_dir+'/result.json';r=json.load(open(f));lines=[]
    for line in open(a.source_run_dir+'/spectre.out'):
        if re.search(r'Defined process parameters|Defined mismatch parameters|Number of random variables',line):lines.append(line.strip())
    r['native_statistical_counts']=lines
    with open(f,'w') as out:json.dump(r,out,indent=2);out.write('\n')
if __name__=='__main__':main()
