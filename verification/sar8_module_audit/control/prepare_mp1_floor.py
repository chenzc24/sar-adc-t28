"""One new pullup branch, composed of three already-used PDK poly resistors."""
import copy
import json
import re

import gate_observer_support as observer
import prepare_first_event as base
from review_both_result import read_current_run

OWN,ROOT=base.OWN,base.ROOT
SRC=OWN/'mp1_shape_v1'
DEST=OWN/'mp1_floor_v1'
RUN='sar8audit-ctrl-mp1shape-v1'
HASH='8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a'
P='XDUT.XCTRL.XTIM.'
GATE=P+'X020.X000.B_PM'


def main():
    _,_,_,_,proof=read_current_run(RUN,HASH)
    analyzer=observer.generate()
    dut=(SRC/'dut.scs').read_text();deck=(SRC/'test.scs').read_text()
    m=json.loads((SRC/'measurement.json').read_bytes())
    poly=base.parts(base.cells(dut)['sar8p_delay_quiet'])['R0']
    nodes=['VDD', 'FLOOR1', 'FLOOR2', 'B_PM']
    additions=['    RPU%d (%s %s) %s %s'%(i,nodes[i],nodes[i+1],poly['model'],poly['parameters']) for i in range(3)]
    anchor='ends sar8audit_nand2_mp1shape'
    if dut.count(anchor)!=1:raise ValueError('Target private NAND boundary differs')
    new=dut.replace(anchor,'\n'.join(additions)+'\n'+anchor)
    old_leaf=base.flatten(dut,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    new_leaf=base.flatten(new,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    extra={P+'X020.X000.RPU'+str(i) for i in range(3)}
    if set(new_leaf)-set(old_leaf)!=extra or any(new_leaf.get(k)!=v for k,v in old_leaf.items()):
        raise ValueError('Change exceeds one added three-resistor branch')
    cat=m['terminal_current_catalog']
    for name in sorted(extra):
        part=new_leaf[name]
        if part['model']!=poly['model'] or part['parameters']!=poly['parameters']:
            raise ValueError('Original legal PDK resistor dimensions changed')
        for port,node in enumerate(part['nodes'],1):
            cat[name+':'+str(port)]=dict(instance=name,terminal='PLUS' if port==1 else 'MINUS',port=port,node=node,kcl_coefficient=1)
    m['scope']='Positive-floor MP1 gate experiment: one three-resistor VDD pullup branch on the shaped conditional-load fixture; no full-ADC qualification'
    m['current_saves']=sorted(cat)
    m['voltage_saves']=sorted({item['node'] for item in cat.values() if item['node']!='0'})
    m['kcl_terms']={node:[trace.lower() for trace,item in cat.items() if item['node']==node]
                   for node in m['voltage_saves'] if node!='VDD!'}
    internal=[P+'X020.X000.FLOOR1',P+'X020.X000.FLOOR2']
    m['critical_kcl_nodes']+=internal
    m['diagnostic_voltage_columns'] += [node.lower() for node in internal]
    m['diagnostic_current_columns']=sorted(set(m['diagnostic_current_columns'])|
        {name.lower()+':'+str(port) for name in extra for port in [1,2]})
    m.update(observer.observations(GATE))
    m['gate_floor_experiment']=dict(base_run=RUN,base_recipe_sha256=HASH,
        one_added_branch='VDD -> three equal original R0 copies -> B_PM',
        low_state_relation='Approximately B_PM=(VDD+3*LIVE)/4 when gate leakage is small; the actual loaded DC solution is measured.',
        rationale='Provide positive low-gate headroom and reduce MP1 holding strength before NM1 discharge, rather than only filtering a zero-volt gate waveform.',
        copied_resistor_model=poly['model'],copied_resistor_parameters=poly['parameters'],
        all_existing_device_and_PWL_inputs_unchanged=True,no_new_supply_or_clock=True,
        no_fitted_capacitor=True,no_forced_initial_state=True,
        expected_tradeoff='New low-state static current about VDD/(4*R0), approximately25uA/25uW at0.99V and observed R0~9.79kOhm; not a measured result.',
        pass_not_inferred=True,remaining_checks=['All-native MP1 VSG/VGD and N-to-ground rail limit',
            'B_PM DC/undershoot, LIVE logic low, QUIET counts/delay and native KCL',
            'All-five-source signed energy/current and full logs; retain any residual overvoltage',
            'First-event experiment only; full-cycle/PVT/startup still needed'])
    saved=set(re.findall(r'(?m)^save\s+(\S+)',deck))
    deck='// One added positive-floor branch, unchanged external sampling/supply.\n'+deck
    deck+=''.join('save '+name+'\n' for name in sorted(set(m['voltage_saves']+m['current_saves'])-saved))
    base.exact_write(DEST/'dut.scs',new);base.exact_write(DEST/'test.scs',deck)
    for path in (SRC/'pwl').iterdir():base.exact_write(DEST/'pwl'/path.name,path.read_bytes())
    base.write_json(DEST/'measurement.json',m)
    recipe=json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-mp1floor-v1',design_id='sar8_control_MP1_positive_gate_floor',
                  analyzer='full_gate_analyze.py',qualification_scope=m['scope'])
    files=[('test.scs',DEST/'test.scs'),('dut.scs',DEST/'dut.scs'),('measurement.json',DEST/'measurement.json'),
           ('full_gate_analyze.py',analyzer)]
    files += [('pwl/'+p.name,p) for p in sorted((DEST/'pwl').iterdir())]
    recipe['inputs']=[dict(source=p.relative_to(ROOT).as_posix(),name=name,sha256=base.digest(p.read_bytes())) for name,p in files]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest=dict(base_run=RUN,base_recipe_sha256=HASH,base_proof=proof,
        original_leaf_identity_unchanged=True,new_instances={k:new_leaf[k] for k in sorted(extra)},
        total_MOS=101,total_passive=22,voltage_saves=len(m['voltage_saves']),current_saves=len(m['current_saves']),
        critical_kcl_nodes=len(m['critical_kcl_nodes']),
        all_five_sources_full_history_configured=True,MP1_VSG_VGD_full_history_configured=True,
        native_PWL_bytes_unchanged=True,external_supply_and_sampling_unchanged=True,
        declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),remote_operations=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['base_proof','new_instances']},indent=2))


if __name__=='__main__':main()
