"""Freeze a native reference-switch CDAC + ideal surrounding modules. No OA edits."""
import hashlib, json, re, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'verification/manual_adc/cdac_isolation_v1'
BEH=ROOT/'verification/manual_adc/behavioral_v1'
NATIVE=ROOT/'verification/manual_adc/candidate_io_v1/dut.scs'
RUN='manual8-cdac-isolation-tt-v1'


def main():
    BASE.mkdir(exist_ok=True)
    native=NATIVE.read_text()
    source=native.split('subckt manual_cdac ',1)[1].split('ends manual_cdac',1)[0]
    elements=[line for line in source.splitlines() if re.match(r'^[MC]\w+\s+\(',line)]
    mos=[line for line in elements if line.startswith('M')]
    caps=[line for line in elements if line.startswith('C')]
    assert len(mos)==14 and len(caps)==8
    ports='GND VDD VTOP VREFP VREFN '+' '.join('DCTRL_'+str(i) for i in range(7,0,-1))
    core='simulator lang=spectre\n// Original MOS and capacitor lines retained verbatim; Bootstrap excluded.\nsubckt manual_cdac_core '+ports+'\nparameters cunit=10f\n'+'\n'.join(elements)+'\nends manual_cdac_core\n'
    (BASE/'cdac_core.scs').write_text(core)
    # Unchanged behavioral models; no duplicate behavior-CDAC instance.
    va=['manual8_sample.va','manual8_cmp.va','manual8_sar.va']
    for name in va:shutil.copyfile(BEH/name,BASE/name)
    w=(BEH/'wrappers.scs').read_text().replace('ahdl_include "manual8_cdac.va"','include "models.scs"\ninclude "cdac_core.scs"')
    w=w.replace(') manual8_cdac cunit=cunit ron_unit=ref_ron',') manual_cdac_core cunit=cunit')
    w=w.replace('manual_adc_beh','manual_adc_cdac_real')
    (BASE/'wrappers.scs').write_text(w)
    models=(ROOT/'verification/manual_adc/joined_dc_v1/models.scs').read_text()
    models='\n'.join(line for line in models.splitlines() if line.startswith('include ') or line in ['simulator lang=spectre','global 0'])+'\n'
    (BASE/'models.scs').write_text(models)
    test=(BEH/'tb_adc.scs').read_text().split('\nsave ')[0]
    test=test.replace('VREF (REF 0) vsource dc=.9','VREFP (REFP 0) vsource dc=.9\nVREFN (REFN 0) vsource dc=0')
    test=test.replace('VINP VINN REF 0 DO_7','VINP VINN REFP REFN DO_7').replace('manual_adc_beh','manual_adc_cdac_real').replace('maxstep=100p','maxstep=20p')
    signals=['VDD','VVDD:1','REFP','REFN','VREFP:1','VREFN:1','VINP','VINN','VINP:1','VINN:1','CLKS','BUSY','EOC','FAULT']
    signals+=['DO_'+str(i) for i in range(8)]
    signals+=['XADC.'+n for n in ['TOPP','TOPN','CMPCK','DCMPP','DCMPN']]
    signals+=['XADC.'+side+'_'+str(i) for side in ['DP','DN'] for i in range(8)]
    devices=[];gate_currents=[];bottom_nodes={}
    for side in ['P','N']:
        prefix='XADC.X'+side+'.XD.'
        mapping={'GND':'0','VDD':'VDD','VTOP':'XADC.TOP'+side,'VREFP':'REFP','VREFN':'REFN'}
        for i in range(1,8):
            control=('DN' if side=='P' else 'DP') if i==7 else 'D'+side
            mapping['DCTRL_'+str(i)]='XADC.'+control+'_'+str(i)
        for line in mos:
            m=re.match(r'(\w+)\s+\(([^)]+)\)\s+(\w+)',line)
            terms=[mapping.get(p,prefix+p) for p in m[2].split()]
            devices.append({'path':prefix+m[1],'model':m[3],'terminals':terms,'side':side})
            signals+=terms
            current=prefix+m[1]+':2';signals.append(current)
            gate_currents.append({'current':current,'gate':terms[1]})
        bottom_nodes[side]=[prefix+n for n in ['net1','net2','net4','net3','net5','net6','net7']]
    signals=sorted(set(signals)-{'0'})
    test+='\nsave '+' '.join(signals)+'\n'
    (BASE/'test.scs').write_text(test)
    lsb=1.8/256
    criteria={'lsb_V':lsb,'step_dm_limit_V':.1*lsb,'compare_cm_limit_V':.1*lsb,
              'held_drift_limit_V':.05*lsb,'settling_budget_s':2e-9,'conversion_budget_s':50e-9,'terminal_limit_V':.99}
    cfg={'stop_s':820e-9,'signals':signals,'devices':devices,'gate_currents':gate_currents,'bottom_nodes':bottom_nodes,
         'codes':[0,255,85,170,127,128,1,254],'criteria':criteria,'vref_V':.9,'vdd_V':.9,
         'scope':'TT reference MOS plus ideal capacitors; all other blocks behavioral/ideal; not physical capacitor/PVT qualification'}
    (BASE/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
    provenance={'source':str(NATIVE.relative_to(ROOT)),'sha256':hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
                'native_MOS_lines_per_side':14,'unchanged_capacitor_lines_per_side':8,'element_lines_sha256':hashlib.sha256(('\n'.join(elements)+'\n').encode()).hexdigest(),
                'only_electrical_boundary_change':'Remove embedded Bootstrap; instantiate external behavioral sampler with Ron=1ohm/qclk=0.',
                'parameter_change':'none: cunit10f, native W/L/nf/multi preserved',
                'criteria_type':'Provisional diagnostic allocations; no ADC specification relaxation'}
    (BASE/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    r=json.loads((ROOT/'management/recipes/manual8-beh-smoke-v2.yaml').read_text())
    files=va+['models.scs','cdac_core.scs','wrappers.scs','test.scs','measure.json']
    r.update(run_id=RUN,design_id='manual8_cdac_isolation_v1',entry='test.scs',analyzer='cdac_isolation_reduce.py',
             inputs=[{'source':str((BASE/f).relative_to(ROOT)).replace('\\','/'),'name':f} for f in files]+[
                 {'source':'scripts/manual_adc/cdac_isolation_reduce.py','name':'cdac_isolation_reduce.py'},
                 {'source':'scripts/manual_adc/reduce.py','name':'reduce.py'}],
             summary_signals=['CLKS','XADC.TOPP','XADC.TOPN','XADC.CMPCK','EOC','FAULT'],
             qualification_scope=cfg['scope'],test_conditions={'corner':'tt','vdd':.9,'temperature_c':27,'noise':False,'mismatch':False,'PEX':False})
    r['resources'].update(max_output_mib=512,simulation_wall_seconds=900,analysis_wall_seconds=600)
    (ROOT/'management/recipes'/(RUN+'.yaml')).write_text(json.dumps(r,indent=2)+'\n')
    print('Built',RUN,'28 MOS, 168 terminal pairs; original MOS/cap lines unchanged.')


if __name__=='__main__':main()
