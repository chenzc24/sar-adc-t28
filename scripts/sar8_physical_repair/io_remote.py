"""Python 2 compatible managed stream reduction for small IO fixtures."""
from __future__ import print_function
import argparse,json,os,subprocess

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();inp=a.run_dir+'/inputs';out=a.output_dir
    exe=out+'/stream';subprocess.check_call(['g++','-O2','-std=c++11',inp+'/stream.cpp','-o',exe])
    raw=[a.run_dir+'/raw/'+f for f in os.listdir(a.run_dir+'/raw') if f.endswith('.tran.tran')]
    assert len(raw)==1
    subprocess.check_call([exe,raw[0],inp+'/selected.txt',inp+'/pairs.txt',out+'/wave'])
    mapping=json.load(open(inp+'/mapping.json'));meta=json.load(open(out+'/wave.meta.json'))
    assert meta['PSF_END'] and abs(meta['last_time_s']-mapping['stop_s'])<1e-15
    peaks=[list(map(float,l.split())) for l in open(out+'/wave.stress.tsv')]
    groups={}
    for d in mapping['records']:
        peak=peaks[d['pair_index']];d.update(peak_v=peak[1],time_s=peak[2])
        if d['model'] not in groups or peak[1]>groups[d['model']]['peak_v']:groups[d['model']]=d
    json.dump(dict(analysis_complete=True,meta=meta,groups=groups,
                  verdict='block_screen_only_UD12_limit_pending'),open(out+'/result.json','w'),indent=2)
    print('ANALYSIS_OK')

if __name__=='__main__':main()
