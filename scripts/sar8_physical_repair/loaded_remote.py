"""Python 2 managed exact-stress/energy reducer; compact plots are not timing truth."""
from __future__ import print_function
import argparse,json,os,subprocess

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();inp=a.run_dir+'/inputs';out=a.output_dir
    exe=out+'/stream';subprocess.check_call(['g++','-O2','-std=c++11',inp+'/stream.cpp','-o',exe])
    native=[a.run_dir+'/raw/'+x for x in os.listdir(a.run_dir+'/raw') if x.endswith('.tran.tran')]
    assert len(native)==1
    subprocess.check_call([exe,native[0],inp+'/selected.txt',inp+'/pairs.txt',out+'/wave'])
    config=json.load(open(inp+'/mapping.json'))
    m=json.load(open(out+'/wave.meta.json'));assert m['PSF_END'] and abs(m['last_time_s']-config['stop_s'])<1e-15
    pairs=[list(map(float,l.split())) for l in open(out+'/wave.stress.tsv')]
    records=config['records'];groups={};failed=[]
    for r in records:
        _,peak,at=pairs[r['pair_index']];r.update(peak_v=peak,time_ns=at*1e9,exceed=peak>r['limit_v'])
        if r['exceed']:failed.append(r)
        if r['group'] not in groups or peak/r['limit_v']>groups[r['group']]['peak_v']/groups[r['group']]['limit_v']:groups[r['group']]=r
    result=dict(analysis_complete=True,all_MOS_pairs=len(records),failing_pairs=len(failed),groups=groups,
        plotting_export_spacing_s=20e-12,stress_all_native_points=True,energy_all_native_points=True,
        events_all_native_points=True,meta=m,
        electrical_verdict='stress_failed' if failed else 'stress_screen_pass_not_full_qualification')
    json.dump(result,open(out+'/result.json','w'),indent=2)
    json.dump(failed,open(out+'/failing_pairs.json','w'),indent=2)
    print('ANALYSIS_OK',result['electrical_verdict'])

if __name__=='__main__':main()
