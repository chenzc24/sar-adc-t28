"""Equivalent zero-volt drain probes; no MOS sizing or timing changes."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_ss_diagnosis_v1'
def main():
    runs=[]
    for tag,source,oldrun,corner,vdd,temp in [
      ('tt','bootstrap_width_v1/sine_m6','manual8-bootwidth-sine-m6-v1','tt',.9,27),
      ('ss','bootstrap_pvt_v1/ss_cold_sine','manual8-bootpvt-ss-cold-sine-v1','ss',.81,-40)]:
        src=R/'verification/manual_adc'/source;dst=OUT/tag;dst.mkdir(parents=True,exist_ok=True)
        for p in src.iterdir():
            if p.suffix not in ['.scs','.va','.json']:continue
            text=p.read_text()
            if p.name=='boot.scs':
                assert text.count('M0 (VOUT net1 VIN GND)')==1
                text=text.replace('M0 (VOUT net1 VIN GND)','VMD (VOUT m0d) vsource dc=0\nM0 (m0d net1 VIN GND)')
                assert text.replace('VMD (VOUT m0d) vsource dc=0\nM0 (m0d net1 VIN GND)','M0 (VOUT net1 VIN GND)')==p.read_text()
            if p.name=='test.scs':text+='\nsave XADC.XP.XS.VMD:1 XADC.XN.XS.VMD:1 XHP.VMD:1 XHN.VMD:1\n'
            (dst/p.name).write_text(text)
        cfg=json.loads((dst/'measure.json').read_text())
        cfg.update(corner=corner,vdd_V=vdd,temperature_C=temp,reference_V=.9,input_CM_V=.45,diagnostic_source_run=oldrun)
        cfg['signals']+=['XADC.XP.XS.VMD:1','XADC.XN.XS.VMD:1','XHP.VMD:1','XHN.VMD:1']
        (dst/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
        run='manual8-bootss-probe-'+tag+'-v1'
        rec=json.loads((R/'management/recipes/manual8-bootpvt-ss-cold-sine-v1.yaml').read_text())
        rec.update(run_id=run,design_id='manual8_bootstrap_m6_ss_diagnosis',analyzer='bootstrap_ss_reduce.py',qualification_scope='Save-only ideal zero-volt M0 drain probes; diagnose tracking/gate/turnoff, no adoption')
        rec['test_conditions'].update(corner=corner,vdd=vdd,temperature_c=temp)
        rec['inputs']=[{'source':p.relative_to(R).as_posix(),'name':p.name} for p in sorted(dst.iterdir())]
        rec['inputs']+=[{'source':'scripts/manual_adc/'+name,'name':name} for name in ['bootstrap_ss_reduce.py','bootstrap_pvt_reduce.py','reduce.py']]
        (R/('management/recipes/'+run+'.yaml')).write_text(json.dumps(rec,indent=2)+'\n')
        runs.append({'run_id':run,'tag':tag,'source_run':oldrun,'directory':dst.relative_to(R).as_posix(),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()}})
    (OUT/'manifest.json').write_text(json.dumps({'runs':runs,'electrical_change':'zero-volt M0 drain current probes only; all MOS/VA/source/timing parameters unchanged'},indent=2)+'\n')
if __name__=='__main__':main()
