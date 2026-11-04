"""Frozen M0=6um hybrid experiment; observation only, no circuit edits."""
import hashlib
import json
import re
from pathlib import Path

R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_fft_v1'

def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8')

def observer():
    bits=', '.join('D%d'%i for i in range(7,-1,-1))
    ports='VDD, CLK, CK, EOC, FAULT, TP, TN, '+bits
    decode='+'.join('((V(D%d)>0.5*V(VDD)) ? %d : 0)'%(i,1<<i) for i in range(8))
    return '''`include "constants.vams"
`include "disciplines.vams"
// Infinite input impedance; no contributions, no changes to DUT models.
module bootfft_observer(%s);
 input %s;
 electrical %s;
 parameter integer tag=0;
 integer frame,comparisons,completed,faults,code;
 real held,lastclose;
 analog begin
  @(initial_step) begin
   frame=0;comparisons=0;completed=0;faults=0;held=0;lastclose=0;
  end
  @(cross(V(CK)-0.5*V(VDD),+1)) comparisons=comparisons+1;
  @(cross(V(EOC)-0.5*V(VDD),+1)) completed=completed+1;
  @(cross(V(FAULT)-0.5*V(VDD),+1)) faults=faults+1;
  @(cross(V(CLK)-0.5*V(VDD),-1)) lastclose=$abstime;
  @(timer(150.975n,100n)) held=V(TP,TN);
  @(timer(211n,100n)) begin
   code=%s;
   $display("BOOTFFT %%d %%d %%.15g %%d %%d %%d %%d %%.15g %%.15g",tag,frame,$abstime,code,comparisons,completed,faults,held,lastclose);
   frame=frame+1;comparisons=0;completed=0;faults=0;
  end
 end
endmodule
'''%(ports,ports,ports,decode)

def main():
    runs=[]
    cases=[('pilot2','ss',461,16,0)]+[(c+'-k'+str(k),c,k,1056,32) for k in [461,17,257] for c in ['ss','tt']]
    for label,c,k,n,warm in cases:
        src=R/('verification/manual_adc/bootstrap_pvt_v1/ss_cold_sine' if c=='ss' else 'verification/manual_adc/bootstrap_width_v1/sine_m6')
        dst=OUT/label
        stop=(n*100+120)*1e-9
        freq=10e6*k/1024
        for f in src.iterdir():
            if f.suffix not in ['.va','.scs']:continue
            s=f.read_text()
            if f.name=='test.scs':
                s=s.replace('freq=4501953.125','freq=%.12g'%freq)
                s=re.sub(r'tran_test tran[^\n]+','tran_test tran stop=%.12g maxstep=50p errpreset=conservative strobeperiod=1n strobeoutput=strobeonly'%stop,s)
                saves=['CLKS','VDD','VINP','VINN','XADC.TOPP','XADC.TOPN','XIDEAL.TOPP','XIDEAL.TOPN','FAULT','IFAULT']
                saves+=['DO_'+str(i) for i in range(8)]+['IDO_'+str(i) for i in range(8)]
                s=re.sub(r'^save .*$', 'save '+' '.join(saves),s,flags=re.M)
                s+='\nahdl_include "bootfft_observer.va"\n'
                for tag,inst,prefix,eoc,fault in [(0,'XADC','DO_','EOC','FAULT'),(1,'XIDEAL','IDO_','IEOC','IFAULT')]:
                    s+='XOBS%d (VDD CLKS %s.CMPCK %s %s %s.TOPP %s.TOPN %s) bootfft_observer tag=%d\n'%(tag,inst,eoc,fault,inst,inst,' '.join(prefix+str(i) for i in range(7,-1,-1)),tag)
            write(dst/f.name,s)
        write(dst/'bootfft_observer.va',observer())
        cfg=dict(corner=c,vdd_V=.81 if c=='ss' else .9,temperature_C=-40 if c=='ss' else 27,
                 frames=n,warmup=warm,fft_N=1024,k=k,frequency_Hz=freq,fs_Hz=1e7,stop_s=stop,
                 M0_total_width_um=6,source_directory=src.relative_to(R).as_posix())
        write(dst/'measure.json',json.dumps(cfg,indent=2)+'\n')
        run='manual8-bootfft-'+label+'-v1'
        rec=json.loads((R/'management/recipes/manual8-bootpvt-ss-cold-sine-v1.yaml').read_text())
        rec.update(run_id=run,design_id='manual8_bootstrap_m6_fft_v1',analyzer='bootstrap_fft_reduce.py',expected_stop_s=stop,
                   qualification_scope='Bootstrap-only MOS hybrid FFT; ideal remaining blocks/external sources; no whole ADC or reliability qualification')
        rec['test_conditions'].update(corner=c,vdd=cfg['vdd_V'],temperature_c=cfg['temperature_C'],frequency_hz=freq,fft_samples=1024,warmup_frames=warm)
        rec['summary_signals']=['CLKS','VDD','VINP','VINN','XADC.TOPP','XADC.TOPN','FAULT']
        rec['resources'].update(simulation_wall_seconds=7200,analysis_wall_seconds=900,max_output_mib=512,queue_timeout_seconds=7200)
        rec['inputs']=[dict(source=f.relative_to(R).as_posix(),name=f.name) for f in sorted(dst.iterdir())]
        rec['inputs'] += [dict(source='scripts/manual_adc/'+name,name=name) for name in ['bootstrap_fft_reduce.py','reduce.py']]
        write(R/('management/recipes/'+run+'.yaml'),json.dumps(rec,indent=2)+'\n')
        unchanged={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in src.iterdir() if f.suffix in ['.va','.scs'] and f.name!='test.scs'}
        assert all(hashlib.sha256((dst/name).read_bytes()).hexdigest()==h for name,h in unchanged.items())
        runs.append(dict(run_id=run,label=label,config=cfg,unchanged_circuit_sha256=unchanged))
    write(OUT/'manifest.json',json.dumps(dict(runs=runs),indent=2)+'\n')
    print('\n'.join(x['run_id'] for x in runs))

if __name__=='__main__':main()


