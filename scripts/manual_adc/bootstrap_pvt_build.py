"""Selected6um Bootstrap: four risk corners, fixed reference/input and timing."""
import hashlib
import json
import re
from pathlib import Path

R=Path(__file__).resolve().parents[2]
OLD=R/'verification/manual_adc/bootstrap_width_v1'
OUT=R/'verification/manual_adc/bootstrap_pvt_v1'
CORNERS=[('ss_cold','ss',.81,-40),('ss_hot','ss',.81,125),
         ('ff_cold','ff',.99,-40),('ff_hot','ff',.99,125)]


def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')


def main():
    audit=json.loads((OUT/'model_corner_check.json').read_text())
    for c in ['ss','ff']:
        assert any(x.endswith(c.upper()+'_18') for x in audit['io18_sections'][c+'macro_mos_moscap'])
    runs=[]
    for tag,corner,vdd,temp in CORNERS:
        for case in ['dc','sine']:
            src=OLD/(case+'_m6');dst=OUT/(tag+'_'+case)
            for f in src.iterdir():
                if f.suffix not in ['.va','.scs']:continue
                text=f.read_text()
                if f.name=='models.scs':
                    text=text.replace('section=ttmacro_mos_moscap','section='+corner+'macro_mos_moscap')
                if f.name=='test.scs':
                    for name,node in [('VVDD','VDD'),('VVDDH','VDDH')]:
                        text=text.replace('%s (%s 0) vsource type=pwl wave=[0 0 1n .9]'%(name,node),
                                          '%s (%s 0) vsource type=pwl wave=[0 0 1n %.2f]'%(name,node,vdd))
                    text=text.replace('val1=.9 delay=110n','val1=%.2f delay=110n'%vdd)
                    text=text.replace('temp=27 tnom=27','temp=%d tnom=27'%temp)
                write(dst/f.name,text)
            cfg=json.loads((src/'measure.json').read_text())
            cfg.update(corner=corner,vdd_V=vdd,temperature_C=temp,reference_V=.9,input_CM_V=.45)
            write(dst/'measure.json',json.dumps(cfg,indent=2)+'\n')
            run='manual8-bootpvt-'+tag.replace('_','-')+'-'+case+'-v1'
            rec=json.loads((R/('management/recipes/manual8-bootwidth-'+case+'-m6-v1.yaml')).read_text())
            rec.update(run_id=run,design_id='manual8_bootstrap_selected_m6_pvt_v1',analyzer='bootstrap_pvt_reduce.py',
                       qualification_scope='Selected6um Bootstrap risk-corner short test; other blocks behavioral; no full PVT/noise/mismatch/FFT/lifetime acceptance')
            rec['test_conditions'].update(corner=corner,vdd=vdd,temperature_c=temp,reference_v=.9,input_cm_v=.45)
            rec['inputs']=[{'source':f.relative_to(R).as_posix(),'name':f.name} for f in sorted(dst.iterdir()) if f.suffix in ['.va','.scs','.json']]
            rec['inputs'] += [{'source':'scripts/manual_adc/bootstrap_pvt_reduce.py','name':'bootstrap_pvt_reduce.py'},
                              {'source':'scripts/manual_adc/reduce.py','name':'reduce.py'}]
            write(R/('management/recipes/'+run+'.yaml'),json.dumps(rec,indent=2)+'\n')
            # Exact electrical delta: only MOS corner, supply/clock amplitude and temperature.
            for f in src.glob('*'):
                if f.suffix not in ['.va','.scs']:continue
                text=(dst/f.name).read_text()
                if f.name=='models.scs':text=text.replace('section='+corner+'macro_mos_moscap','section=ttmacro_mos_moscap')
                if f.name=='test.scs':
                    for name,node in [('VVDD','VDD'),('VVDDH','VDDH')]:
                        text=text.replace('%s (%s 0) vsource type=pwl wave=[0 0 1n %.2f]'%(name,node,vdd),
                                          '%s (%s 0) vsource type=pwl wave=[0 0 1n .9]'%(name,node))
                    text=text.replace('val1=%.2f delay=110n'%vdd,'val1=.9 delay=110n').replace('temp=%d tnom=27'%temp,'temp=27 tnom=27')
                assert text==f.read_text(),(tag,case,f.name)
            runs.append({'run_id':run,'tag':tag,'case':case,'corner':corner,'vdd_V':vdd,'temperature_C':temp,
                         'directory':dst.relative_to(R).as_posix(),'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in dst.iterdir()}})
    write(OUT/'manifest.json',json.dumps({'runs':runs,'electrical_delta_check_pass':True,
           'TT_reuse':['manual8-bootwidth-dc-m6-v1','manual8-bootwidth-sine-m6-v1']},indent=2)+'\n')
    write(OUT/'selected_candidate.json',json.dumps({'selection':'User selected6um Bootstrap for subsequent netlist tests',
           'M0_per_instance_W_um':1,'M0_multi':6,'L_nm':150,'other_MOS_W_um':1,'other_MOS_multi':1,
           'first_clock_ns':110,'period_ns':100,'pulse_width_ns':39.9,'edges_ps':50,'Cboot_pF':1,
           'OA_changed':False,'whole_ADC_baseline_adopted':False,'PVT_qualification':'pending'},indent=2)+'\n')
    print('\n'.join(x['run_id'] for x in runs))


if __name__=='__main__':main()
