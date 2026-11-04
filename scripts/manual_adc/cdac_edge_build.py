"""Build single-variable CDAC stimuli; retain original native core and clock."""
import hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'verification/manual_adc/cdac_isolation_v1'
BASE=ROOT/'verification/manual_adc/cdac_edge_v1'
CASES={'b10':(10,0),'s50':(50,0),'s100':(100,0),'r500':(10,500)}


def main():
    BASE.mkdir(exist_ok=True)
    sample=(SRC/'manual8_sample.va').read_text()
    sample=sample.replace('VIN, VOUT);','VIN, VOUT, MON);')
    sample=sample.replace('electrical CLKS, GND, VDD, VIN, VOUT;',
        'output MON;\n    electrical CLKS, GND, VDD, VIN, VOUT, MON;')
    sample=sample.replace('parameter real trf = 10p from (0:inf);',
        '''parameter real trf = 10p from (0:inf);
    parameter real trise = 10p from (0:inf);
    parameter real t_on_start = 10.025n from (0:inf);
    parameter real period = 100n from (0:inf);''')
    sample=sample.replace('@(cross(V(CLKS,GND)-threshold*V(VDD,GND), +1)) tracking = 1;',
        '// Known periodic testbench only: align conductance midpoint across rise sweeps.\n        @(timer(t_on_start, period)) tracking = 1;')
    sample=sample.replace('transition(tracking, 0, trf, trf);',
        'transition(tracking, 0, trise, trf);\n        V(MON,GND) <+ on_fraction; // 1 V = fully on')
    sar=(SRC/'manual8_sar.va').read_text()
    sar=sar.replace('DCTRLN_0, BUSY, EOC, FAULT);','DCTRLN_0, BUSY, EOC, FAULT, REFRST);')
    sar=sar.replace('input CLKS, VDD, DCMPP, DCMPN;', 'input CLKS, VDD, DCMPP, DCMPN, REFRST;\n    electrical REFRST;')
    sar=sar.replace('        // Sample wins', '''        // Reset only the reference gate bank; preserve previous raw code until capture.
        @(cross(V(REFRST,GND)-threshold*V(VDD,GND), +1)) begin
            gate_p=0; gate_n=0;
        end
        // Sample wins''')
    wrapper=(SRC/'wrappers.scs').read_text()
    wrapper=wrapper.replace('sample_ron=1 ref_ron=10', 'sample_rise=10p sample_start=10.025n sample_ron=1 ref_ron=10')
    wrapper=wrapper.replace('XS (CLKS GND VDD VIN VTOP) manual8_sample ron=sample_ron qclk=sample_qclk',
        'XS (CLKS GND VDD VIN VTOP SAMPLE_FRAC) manual8_sample ron=sample_ron qclk=sample_qclk trise=sample_rise t_on_start=sample_start')
    wrapper=wrapper.replace('DO_0 BUSY EOC FAULT\n','DO_0 BUSY EOC FAULT REF_RST\n')
    wrapper=wrapper.replace('manual_cdac_beh cunit=cunit sample_ron=',
        'manual_cdac_beh cunit=cunit sample_rise=sample_rise sample_start=sample_start sample_ron=')
    wrapper=wrapper.replace('DN_0 BUSY EOC FAULT) manual8_sar','DN_0 BUSY EOC FAULT REF_RST) manual8_sar')
    manifest={}
    for key,(rise_ps,advance_ps) in CASES.items():
        folder=BASE/key;folder.mkdir(exist_ok=True)
        for name in ['cdac_core.scs','models.scs','manual8_cmp.va']:
            shutil.copyfile(SRC/name,folder/name)
        for name,content in [('manual8_sample.va',sample),('manual8_sar.va',sar),('wrappers.scs',wrapper)]:
            (folder/name).write_text(content)
        start_ns=10.030-rise_ps*.0005
        test=(SRC/'test.scs').read_text()
        test=test.replace('BUSY EOC FAULT) manual_adc_cdac_real',
            'BUSY EOC FAULT REF_RST) manual_adc_cdac_real sample_rise=%dp sample_start=%.9fn'%(rise_ps,start_ns))
        reset='VRST (REF_RST 0) vsource dc=0\n'
        if advance_ps:
            reset='VRST (REF_RST 0) vsource type=pulse val0=0 val1=.9 delay=%.9fn rise=50p fall=50p width=1n period=100n\n'%(10.025-advance_ps*.001-.025)
        test=test.replace('simulatorOptions options',reset+'simulatorOptions options')
        test=test.rstrip()+' REF_RST XADC.XP.SAMPLE_FRAC XADC.XN.SAMPLE_FRAC\n'
        (folder/'test.scs').write_text(test)
        cfg=json.loads((SRC/'measure.json').read_text())
        cfg['signals']+=['REF_RST','XADC.XP.SAMPLE_FRAC','XADC.XN.SAMPLE_FRAC']
        cfg['experiment']={'case':key,'sample_rise_s':rise_ps*1e-12,'sample_fall_s':10e-12,
            'sample_start_s':start_ns*1e-9,'sample_center_s':10.030e-9,'ref_advance_s':advance_ps*1e-12,
            'next_boundary_s':min(start_ns*1e-9,10.025e-9-advance_ps*1e-12) if advance_ps else start_ns*1e-9,
            'period_s':100e-9,'scope':'Native CDAC ref MOS; ideal capacitors and surroundings. Same external clock and sampling 50% midpoint/falling edge.'}
        (folder/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
        run='manual8-cdac-edge-'+key+'-tt-v1'
        recipe=json.loads((ROOT/'management/recipes/manual8-cdac-isolation-tt-v1.yaml').read_text())
        recipe.update(run_id=run,design_id='manual8_cdac_edge_v1',analyzer='cdac_edge_reduce.py',oa_parity='none; OA untouched')
        files=['manual8_sample.va','manual8_cmp.va','manual8_sar.va','models.scs','cdac_core.scs','wrappers.scs','test.scs','measure.json']
        recipe['inputs']=[{'source':str((folder/f).relative_to(ROOT)).replace('\\','/'),'name':f} for f in files]
        recipe['inputs'] += [{'source':'scripts/manual_adc/'+f,'name':f} for f in ['cdac_edge_reduce.py','reduce.py']]
        recipe['test_conditions']['single_variable']=cfg['experiment']
        (ROOT/'management/recipes'/(run+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
        assert (folder/'cdac_core.scs').read_bytes()==(SRC/'cdac_core.scs').read_bytes()
        manifest[key]={'run_id':run,'experiment':cfg['experiment'],
            'hashes':{f:hashlib.sha256((folder/f).read_bytes()).hexdigest() for f in files}}
    # All four cases differ only in test parameters/reset stimulus and measurement metadata.
    for f in ['manual8_sample.va','manual8_sar.va','manual8_cmp.va','cdac_core.scs','models.scs','wrappers.scs']:
        assert len({x['hashes'][f] for x in manifest.values()})==1
    original_clock=next(x for x in (SRC/'test.scs').read_text().splitlines() if x.startswith('VCLK '))
    for key in CASES:
        assert original_clock in (BASE/key/'test.scs').read_text().splitlines()
    (BASE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built four fixtures; native core/common models/external clock identical.')


if __name__=='__main__':main()
