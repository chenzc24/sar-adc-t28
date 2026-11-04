"""Stream native codes for a noncoherent noise pilot; Python2/3. No FFT claim."""
from __future__ import print_function
import argparse,json,os,re
from native_stream import samples

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    c=json.load(open(a.run_dir+'/inputs/context.json'));rows=[];noise_lines=[];warnings=set()
    for line in open(a.run_dir+'/spectre.out'):
        m=re.search(r'R4MEAS,([^\r\n]+)',line)
        if m:rows.append([float(x) for x in m.group(1).split(',')])
        if 'noise' in line.lower():noise_lines.append(line.strip())
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
    assert len(rows)==c['frames'] and all(len(r)==14 for r in rows)
    files=[a.run_dir+'/raw/'+n for n in os.listdir(a.run_dir+'/raw') if n.endswith('.tran.tran')];assert len(files)==1
    codes=[];held=[];points=0
    for t,v in samples(files[0]):
        points+=1
        j=int(round((t-157e-9)/100e-9))
        if 0<=j<c['frames'] and abs(t-(157+j*100)*1e-9)<1e-13:
            codes.append(sum(1<<b for b in range(8) if v['d%d'%b]>.45))
        j=int(round((t-100.8e-9)/100e-9))
        if 0<=j<c['frames'] and abs(t-(100.8+j*100)*1e-9)<1e-13:
            held.append(dict(frame=j,top_diff_v=v['xdut.topp']-v['xdut.topn'],pin_diff_v=v['vinp']-v['vinn']))
    assert t>=c['stop_s']-1e-13 and len(codes)==c['frames'] and len(held)==c['frames']
    assert codes==[int(r[1]) for r in rows]
    bad=[int(r[0]) for r in rows if r[2:6]!=[8,8,8,16] or r[1]!=r[6] or r[7]!=1 or not 0<r[13]<60e-9]
    result=dict(context=c,analysis_complete=True,native_decode_crosscheck=True,functional_pass=not bad,invalid_frames=bad,
        codes=codes,frames=rows,held_samples=held,native_points=points,native_noise_lines=noise_lines,warning_codes=sorted(warnings),
        electrical_verdict='not_qualified',noise_activation_verdict='requires_native_log_review',
        limitations=['32 measured samples at original frequency are noncoherent: no FFT performance claim','1MHz low-frequency shaping cutoff is diagnostic only','Single seed cannot establish noise bandwidth convergence','No mismatch,PEX,external source noise or external clock jitter'])
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2)
    print('NOISE_PILOT_COMPLETE',len(codes),not bad)
if __name__=='__main__':main()
