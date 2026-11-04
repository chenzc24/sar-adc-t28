"""Isolated native M0 conductance vs source/body bias and imposed VGS."""
import json,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_ss_diagnosis_v1'
def main():
    for tag,corner,temp,vdd in [('tt','tt',27,.9),('ss','ss',-40,.81)]:
        src=OUT/tag;dst=OUT/('m0_'+tag);dst.mkdir(exist_ok=True)
        (dst/'models.scs').write_text((src/'models.scs').read_text())
        mos=next(s for s in (src/'boot.scs').read_text().splitlines() if s.startswith('M0 '))
        params=mos.split('nch_18_mac',1)[1].replace('multi=main_mult','multi=6')
        deck=['simulator lang=spectre','global 0','include "models.scs"'];cases=[]
        for vgs in [.8,.81,.889,.9]:
            for vin in [.05,.25,.45,.65,.85]:
                i=len(cases);d,g,s=['%s%d'%(n,i) for n in ['d','g','s']]
                deck += ['VS%d (%s 0) vsource dc=%.9g'%(i,s,vin),'VG%d (%s %s) vsource dc=%.9g'%(i,g,s,vgs),
                         'VD%d (%s %s) vsource dc=.001'%(i,d,s),'M%d (%s %s %s 0) nch_18_mac%s'%(i,d,g,s,params)]
                cases.append({'index':i,'VIN_V':vin,'VGS_V':vgs,'VDS_V':.001,'current':'vd%d:1'%i})
        deck += ['simulatorOptions options reltol=1e-7 vabstol=1e-8 iabstol=1e-14 temp=%d tnom=27'%temp,
                 'saveOptions options save=selected currents=selected','tran_test tran stop=2n maxstep=20p errpreset=conservative',
                 'save '+' '.join('VD%d:1'%i for i in range(len(cases)))]
        (dst/'test.scs').write_text('\n'.join(deck)+'\n');(dst/'measure.json').write_text(json.dumps({'cases':cases,'tag':tag,'corner':corner,'temperature_C':temp},indent=2)+'\n')
        run='manual8-bootss-m0-'+tag+'-v1';rec=json.loads((R/('management/recipes/manual8-bootss-probe-'+tag+'-v1.yaml')).read_text())
        rec.update(run_id=run,analyzer='bootstrap_ss_m0_reduce.py',expected_stop_s=2e-9,summary_signals=["VD0:1"],qualification_scope='Isolated M0 small-VDS conductance; gate/body-bias diagnostic, not a replacement circuit')
        rec['inputs']=[{'source':p.relative_to(R).as_posix(),'name':p.name} for p in sorted(dst.iterdir())]
        rec['inputs'] += [{'source':'scripts/manual_adc/'+n,'name':n} for n in ['bootstrap_ss_m0_reduce.py','reduce.py']]
        rec['test_conditions'].update(stimulus='constant VDS1mV, VGS0.8/0.81/0.889/0.9V, VIN0.05/0.25/0.45/0.65/0.85V, body0V')
        (R/('management/recipes/'+run+'.yaml')).write_text(json.dumps(rec,indent=2)+'\n')
        (OUT/('m0_'+tag+'_manifest.json')).write_text(json.dumps({'run_id':run,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()}},indent=2)+'\n')
if __name__=='__main__':main()

