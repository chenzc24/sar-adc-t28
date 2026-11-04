"""Create immutable B noise pilot recipes from the measured FFT baseline."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def main():
    source=R/'management/recipes/sar8camp-b-tt-fft1024-mm-v1.yaml'
    for tag,fmax in [('off',0),('g1',1000000000),('g2',2000000000)]:
        rec=json.loads(source.read_text());run='sar8noise-b-short-'+tag+'-s101-v1'
        dest=R/'verification/sar8_noise'/run;dest.mkdir(parents=True,exist_ok=False)
        new=[]
        for old in rec['inputs']:
            src=R/old['source'];assert sha(src)==old['sha256'];name=old['name'];target=src
            if name=='test.scs':
                text=src.read_text();assert 'stop=103259n' in text
                text=text.replace('stop=103259n','stop=4059n')
                if fmax:text=text.replace('strobeoutput=strobeonly','strobeoutput=strobeonly noisefmin=1M noisefmax=%d noiseseed=101 noisescale=1'%fmax)
                text+='\nsave VINP VINN XDUT.TOPP XDUT.TOPN\n';target=dest/name;target.write_text(text)
            elif name=='tb.scs':
                text=src.read_text();assert text.count('resistor r=50')==4
                target=dest/name;target.write_text(text.replace('resistor r=50','resistor r=50 isnoisy=yes'))
            elif name=='context.json':
                c=json.loads(src.read_text());c.update(run_id=run,kind='noise_pilot',frames=40,samples=32,bin=None,stop_s=4059e-9,noise=bool(fmax),noisefmax_hz=fmax,noisefmin_hz=1000000 if fmax else None,noiseseed=101 if fmax else None,noisescale=1,source_run_id=rec['run_id'],noise_scope='device models plus external50ohm resistors; ideal sources')
                target=dest/name;save(target,c);rec['test_conditions']=c
            elif name=='dynamic_reduce.py':
                name='reduce_short.py';target=R/'scripts/sar8_noise/reduce_short.py'
            new.append(dict(source=target.relative_to(R).as_posix(),name=name,sha256=sha(target)))
        rec.update(run_id=run,inputs=new,analyzer='reduce_short.py',expected_stop_s=4059e-9,qualification_scope='Transient-noise activation and bandwidth diagnostic only; not32point FFT')
        rec['summary_signals']+=['vinp','vinn','xdut.topp','xdut.topn']
        rec['resources'].update(max_output_mib=2048,simulation_wall_seconds=86400)
        save(R/'management/recipes'/(run+'.yaml'),rec);print(run)
if __name__=='__main__':main()
