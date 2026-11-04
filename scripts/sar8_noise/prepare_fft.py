"""Freeze one explicitly authorized noisy B1024 recipe; no launch side effects."""
import copy,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run='sar8noise-b-tt-fft1024-g2-s101-v1'
    rec=json.loads((R/'management/recipes/sar8camp-b-tt-fft1024-mm-v1.yaml').read_text())
    dest=R/'verification/sar8_noise'/run;dest.mkdir(exist_ok=False)
    for item in rec['inputs']:
        src=R/item['source'];assert sha(src)==item['sha256']
        if item['name']=='test.scs':
            old=src.read_text();assert old.count('strobeoutput=strobeonly')==1
            new=old.replace('strobeoutput=strobeonly','strobeoutput=strobeonly noisefmin=10k noisefmax=2G noiseseed=101 noisescale=1')
        elif item['name']=='tb.scs':
            old=src.read_text();assert old.count('resistor r=50')==4
            new=old.replace('resistor r=50','resistor r=50 isnoisy=yes')
        elif item['name']=='context.json':
            c=json.loads(src.read_text());c.update(run_id=run,noise=True,noisefmax_hz=2000000000,noisefmin_hz=10000,noiseseed=101,noisescale=1,source_run_id=rec['run_id'],noise_scope='all enabled device model noise plus four external50ohm resistors',noise_model_section='noise_worst')
            new=json.dumps(c,indent=2)+'\n';rec['test_conditions']=c
        else:continue
        dst=dest/item['name'];dst.write_text(new,encoding='utf-8');item.update(source=dst.relative_to(R).as_posix(),sha256=sha(dst))
    src=R/'output/managed_execution/runs/sar8camp-b-tt-fft1024-mm-v1/collected/derived/result.json'
    baseline=json.loads(src.read_text());assert baseline['analysis_complete'] and baseline['native_decode_crosscheck'] and baseline['functional_pass']
    dst=dest/'baseline_result.json';dst.write_bytes(src.read_bytes())
    for path,name in [(dst,'baseline_result.json'),(R/'scripts/sar8_noise/reduce_fft.py','reduce_fft.py')]:
        rec['inputs'].append(dict(source=path.relative_to(R).as_posix(),name=name,sha256=sha(path)))
    rec.update(run_id=run,analyzer='reduce_fft.py',qualification_scope='Single-seed noisy1024FFT vs frozen no-noise B; bandwidth convergence and electrical qualification not established')
    out=R/'management/recipes'/(run+'.yaml');assert not out.exists();out.write_text(json.dumps(rec,indent=2)+'\n')
    print(run)
if __name__=='__main__':main()
