"""One new PDK poly resistor in X020 MP1 gate path; no external clock change."""
import copy
import json
import re

import prepare_first_event as base
import prepare_sn_load_variants as loads
from review_both_result import HASH, RUN, read_current_run

OWN,ROOT=base.OWN,base.ROOT
SOURCE=OWN/'sn_load_variants_v1/both'
TARGET=OWN/'mp1_shape_v1'
P='XDUT.XCTRL.XTIM.'
MP=P+'X020.X000.MP1'
GATE=P+'X020.X000.B_PM'
RES=P+'X020.X000.RSLEW'


def prepare():
    # This also checks every registered both input before using it.
    _,_,_,_,proof=read_current_run()
    dut=(SOURCE/'dut.scs').read_text()
    deck=(SOURCE/'test.scs').read_text()
    measurement=json.loads((SOURCE/'measurement.json').read_bytes())
    blocks=base.cells(dut)
    poly=base.parts(blocks['sar8p_delay_quiet'])['R0']
    if poly['model']!='rupolym':raise ValueError('Expected the existing PDK poly resistor')
    old_nand=blocks['sar8p_nand2']
    if old_nand.count('MP1 (Y B VDD VDD)')!=1:raise ValueError('Unexpected original MP1 gate')
    special=old_nand.replace('subckt sar8p_nand2 ','subckt sar8audit_nand2_mp1shape ')
    special=special.replace('MP1 (Y B VDD VDD)','MP1 (Y B_PM VDD VDD)')
    special=special.replace('ends sar8p_nand2',
        '    RSLEW (B B_PM) '+poly['model']+' '+poly['parameters']+'\nends sar8audit_nand2_mp1shape')
    and_cell='\n'.join(['subckt sar8audit_and2_mp1shape A B VDD VSS Y',
        '    X000 (A B VDD VSS N) sar8audit_nand2_mp1shape',
        '    X001 (N VDD VSS Y) sar8p_inv','ends sar8audit_and2_mp1shape'])
    line='X020 (Q1 LIVE VDD VSS QUIET) sar8p_and2'
    if dut.count(line)!=1:raise ValueError('Expected exactly one targeted X020')
    dut=dut.replace(line,'X020 (Q1 LIVE VDD VSS QUIET) sar8audit_and2_mp1shape')
    dut+='\n'+special+'\n\n'+and_cell+'\n'
    old=base.flatten((SOURCE/'dut.scs').read_text(),'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    new=base.flatten(dut,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    changed=[name for name in old if old[name]!=new.get(name)]
    if changed!=[MP] or set(new)-set(old)!={RES}:raise ValueError('Circuit change exceeds one gate and resistor')
    wanted=copy.deepcopy(old[MP]);wanted['nodes'][1]=GATE
    if new[MP]!=wanted or new[RES]['model']!=poly['model'] or new[RES]['parameters']!=poly['parameters']:
        raise ValueError('Unexpected original MOS or PDK resistor parameter change')
    if new[RES]['nodes']!=[P+'LIVE',GATE]:raise ValueError('Unexpected gate-shaping connectivity')
    # MN1 remains directly driven. All original source/PWL/device parameters remain.
    if new[P+'X020.X000.MN1']!=old[P+'X020.X000.MN1']:raise ValueError('MN1 path changed')
    m=copy.deepcopy(measurement)
    cat=m['terminal_current_catalog']
    cat[MP+':2']['node']=GATE
    for port,node in [(1,P+'LIVE'),(2,GATE)]:
        cat[RES+':'+str(port)]=dict(instance=RES,terminal='PLUS' if port==1 else 'MINUS',
                                  port=port,node=node,kcl_coefficient=1)
    m['scope']='One-PDK-poly-resistor asymmetric MP1 gate shaping on the corrected conditional SN-load fixture; no ADC qualification'
    m['current_saves']=sorted(cat)
    m['voltage_saves']=sorted({entry['node'] for entry in cat.values() if entry['node']!='0'})
    m['kcl_terms']={node:[trace.lower() for trace,item in cat.items() if item['node']==node]
                    for node in m['voltage_saves'] if node!='VDD!'}
    m['critical_kcl_nodes'] += [P+'LIVE',GATE]
    m['diagnostic_voltage_columns'].append(GATE.lower())
    m['diagnostic_current_columns']=sorted(set(m['diagnostic_current_columns']) |
        set(sum((m['kcl_terms'][node] for node in [P+'LIVE',GATE]),[])) |
        {MP.lower()+':3',MP.lower()+':4','vvdd:1'})
    if len(m['kcl_terms'][GATE])!=2:raise ValueError('Gate KCL must contain resistor return plus MP1 gate')
    if MP.lower()+':2' in m['kcl_terms'][P+'LIVE']:raise ValueError('Old LIVE gate incidence remains')
    m['local_suppression_experiment']=dict(base_run=RUN,base_recipe_sha256=HASH,
        single_change='Only X020 NAND MP1 gate receives LIVE through one PDK rupolym; MN1 remains direct.',
        new_resistor_instance=RES,resistor_model=poly['model'],resistor_parameters=poly['parameters'],
        copied_from_existing_instance=P+'XD_QUIET_D.R0',new_gate=GATE,
        no_new_capacitor=True,no_new_voltage_or_clock_source=True,all_MOS_sizes_unchanged=True,
        original_external_sampling_inputs_unchanged=True,
        rationale='Spread MP1 gate displacement injection while the direct MN1 path discharges MID. The amount of improvement, overlap current and delay are to be measured.',
        unknown_new_gate_initial_value=True,
        observations=['N and new gate terminal voltages, MP1 total currents and integrated charge',
            'LIVE/QUIET/QUIET_D edge counts/order/delay; no assumption of preserved internal latency',
            'New gate/LIVE/N/SN/bias-node KCL; native warnings including any new gate overvoltage',
            'Local VDD current is recorded but ideal diffusion-bias sources prevent whole-ADC power qualification'],
        acceptance_pass=None)
    m['boundary_differences'].append('Only MP1 receives a new PDK series gate resistor; conditional SN diffusion biases and original v1 cuts remain.')
    # No waveform endpoint, source setting or transient setup is changed.
    saved=set(re.findall(r'(?m)^save\s+(\S+)',deck))
    deck='// Local suppression experiment: one copied PDK poly resistor in X020 MP1 gate.\n'+deck
    deck+=''.join('save '+name+'\n' for name in sorted(set(m['voltage_saves']+m['current_saves'])-saved))
    base.exact_write(TARGET/'dut.scs',dut)
    base.exact_write(TARGET/'test.scs',deck)
    for path in (SOURCE/'pwl').iterdir():base.exact_write(TARGET/'pwl'/path.name,path.read_bytes())
    base.write_json(TARGET/'measurement.json',m)
    recipe=json.loads((SOURCE/'recipe.suggested.yaml').read_bytes())
    recipe['run_id']='sar8audit-ctrl-mp1shape-v1'
    recipe['design_id']='sar8_control_local_MP1_gate_shape'
    recipe['qualification_scope']=m['scope']
    recipe['summary_signals']=[(P+'X020.N').lower(),(P+'LIVE').lower(),GATE.lower()]
    files=[('test.scs',TARGET/'test.scs'),('dut.scs',TARGET/'dut.scs'),
           ('measurement.json',TARGET/'measurement.json'),('first_event_analyze.py',OWN/'first_event_analyze.py')]
    files += [('pwl/'+path.name,path) for path in sorted((TARGET/'pwl').iterdir())]
    recipe['inputs']=[dict(source=path.relative_to(ROOT).as_posix(),name=name,sha256=base.digest(path.read_bytes())) for name,path in files]
    base.write_json(TARGET/'recipe.suggested.yaml',recipe)
    identity=dict(base_run=RUN,base_recipe_sha256=HASH,base_completed_result=proof,
        changed_original_instances={MP:dict(before=old[MP],after=new[MP])},new_instances={RES:new[RES]},
        unchanged_original_instances=len(old)-1,all_original_MOS_models_and_parameters_unchanged=True,
        new_MOS=0,total_MOS=101,total_passive=19,new_voltage_sources=0,new_clocks=0,
        external_source_and_bias_PWL_hashes_unchanged=True,
        recipe_file_sha256=base.digest((TARGET/'recipe.suggested.yaml').read_bytes()),
        declared_package_bytes=sum(path.stat().st_size for _,path in files),
        voltage_saves=len(m['voltage_saves']),current_saves=len(m['current_saves']),
        critical_kcl_nodes=len(m['critical_kcl_nodes']),
        original_gate_initial_witness_does_not_exist=True,simulation_started_by_this_session=False)
    base.write_json(TARGET/'change_manifest.json',identity)
    print(json.dumps(identity,indent=2))


if __name__=='__main__':prepare()
