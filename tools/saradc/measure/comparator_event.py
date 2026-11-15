"""Managed source-bound comparator diagnostic windows; not a full SOA verdict."""
from __future__ import print_function
import argparse,csv,json,os,subprocess

NODES=['vdd!','xdut.topp','xdut.topn','xdut.xcomp.x','xdut.xcomp.y',
       'xdut.xcomp.tail','xdut.cmp_clk','xdut.comp_p','xdut.comp_n',
       'xdut.xctrl.phi_w','xdut.phi_u','xdut.sample_int']
NODES += ['vrefp','vrefn','xdut.preset']
NODES += ['xdut.code%d'%i for i in range(8)]
NODES += ['xdut.'+s+str(i) for i in (6,7) for s in ('gnn','gnp','gpn','gpp')]
NODES += ['xdut.xcdac.b'+s+str(i) for i in (6,7) for s in ('n','p')]
WINDOWS=[(98e-9,106e-9),(198e-9,206e-9),(1498e-9,1506e-9)]

def extract(run_dir,output_dir,source):
    inputs=os.path.join(run_dir,'inputs')
    with open(os.path.join(source,'inputs','soa_context.json')) as f:ctx=json.load(f)
    if not os.path.isdir(output_dir):os.makedirs(output_dir)
    scratch=os.path.join(run_dir,'event_scratch')
    if not os.path.isdir(scratch):os.makedirs(scratch)
    binary=os.path.join(scratch,'native_window')
    subprocess.check_call(['g++','-std=c++11','-O2',os.path.join(inputs,'native_window.cpp'),'-o',binary])
    # Exercise grouped traces, escaped names, carried values, and exact window ends.
    test=os.path.join(scratch,'test.psf');layout=os.path.join(scratch,'test.layout');out=os.path.join(scratch,'test.csv')
    with open(test,'w') as f:f.write('SWEEP\n"time" FLOAT\nTRACE\n"grp" GROUP 1\n"V\\!" FLOAT\nVALUE\n"time" 0\n"grp" 1\n"time" 1\n"grp" 2\n"time" 2\nEND\n')
    with open(layout,'w') as f:f.write('1 1\nv!\n1 2\n')
    subprocess.check_call([binary,test,layout,out])
    with open(out) as f:rows=list(csv.DictReader(f))
    assert [(float(r['time']),float(r['v!'])) for r in rows]==[(1.,2.),(2.,2.)]
    with open(test,'w') as f:f.write('SWEEP\n"time" FLOAT\nTRACE\n"other" FLOAT\nVALUE\n"time" 0\n"other" 1\nEND\n')
    assert subprocess.call([binary,test,layout,out])!=0
    layout=os.path.join(scratch,'window.layout')
    with open(layout,'w') as f:
        f.write('%d %d\n'%(len(NODES),len(WINDOWS))+'\n'.join(NODES)+'\n')
        for a,b in WINDOWS:f.write('%.17g %.17g\n'%(a,b))
    raw=os.path.join(source,'raw','tran_short.tran.tran');out=os.path.join(output_dir,'events.csv')
    receipt=json.loads(subprocess.check_output([binary,raw,layout,out]).decode())
    assert abs(receipt['stop']-ctx['expected_stop_s'])<1e-14
    summaries=[]
    with open(out) as f:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
    for a,b in WINDOWS:
        data=[r for r in rows if a<=r['time']<=b];assert data
        peak=max(data,key=lambda r:abs(r['xdut.topp']-r['xdut.xcomp.y']))
        summaries.append(dict(start_s=a,end_s=b,samples=len(data),peak_vgd_row=peak,
            signed_vgd_at_peak=peak['xdut.topp']-peak['xdut.xcomp.y'],
            extrema={n:dict(min=min(r[n] for r in data),max=max(r[n] for r in data)) for n in NODES}))
    result=dict(analysis_complete=True,source_run_id=ctx['run_id'],corner=ctx['corner'],
        extraction=receipt,windows=summaries,raw_waveform=raw,
        scope='Native diagnostic windows only; full-run SOA verdict remains in original result',
        selftest='group aliases, escapes, carried values, closed window endpoints, missing node rejection')
    with open(os.path.join(output_dir,'result.json'),'w') as f:json.dump(result,f,indent=2)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True)
    a=p.parse_args();extract(a.run_dir,a.output_dir,a.source_run_dir)
