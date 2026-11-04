"""Streaming native diagnostic export, preserving exact points near turnoff."""
from __future__ import print_function
import argparse,json,os,gzip
import bootstrap_pvt_reduce
from reduce import frames
def main():
    bootstrap_pvt_reduce.main()
    ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--output-dir',required=True);a=ap.parse_args()
    src=[a.run_dir+'/raw/'+s for s in os.listdir(a.run_dir+'/raw') if s.endswith('.tran.tran')][0]
    names=['clks','vinp','vinn','xadc.topp','xadc.topn','hp','hn']
    for prefix in ['xadc.xp.xs','xadc.xn.xs','xhp','xhn']:
        names +=[prefix+'.'+n for n in ['net1','net2','net3','net4','net7','clksb','vmd:1']]
    out=gzip.open(a.output_dir+'/diagnostic.csv.gz','wb');out.write(('time,'+','.join(names)+'\n').encode('ascii'))
    last=-1.;count=0
    for t,v in frames(src):
        phase=(t*1e9)%100
        dense=47<=phase<=54
        if t>=110e-9 and (dense or t-last>=50e-12):
            out.write((','.join(['%.15g'%t]+['%.15g'%v[k] for k in names])+'\n').encode('ascii'));last=t;count+=1
    out.close()
    if sum(os.path.getsize(a.output_dir+'/'+x) for x in os.listdir(a.output_dir))>28*1024**2:raise ValueError('derived size guard')
    print('Diagnostic points',count)
if __name__=='__main__':main()
