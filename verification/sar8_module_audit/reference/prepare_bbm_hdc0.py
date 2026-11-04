"""Clone only HD delay master to change exactly one MOM multiplicity."""
import hashlib,json,re
from pathlib import Path
from build_first_fixture import definitions,instances,ports,flatten,emit,closure
from bbm_hdc0_analyze import validate,VARIANT

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_bbm_v1';OUT=HERE/'generated/bbm_hdc0_v1';TOP='sar8_realpre_unit'
TARGET='XDUT.XBBM0.XD_HD.C0'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def params(s):return dict(re.findall(r'(\w+)=([^\s]+)',s))


def prepare():
    for case in json.loads((OLD/'package_review.json').read_text())['cases']:
        for x in case['files']:assert sha(ROOT/x['source'])==x['sha256']
    d=definitions((OLD/'dut.scs').read_text());pins=ports(d[TOP]);binding={n:'VDD!' if n=='VDD' else '0' if n=='VSS' else n for n in pins};before=flatten(d,TOP,binding)
    master='sar8p_delay_bbm';clone='sar8p_delay_bbm_HD_C0x4';rows=list(instances(d[master]));count=0;newrows=[]
    for n,nodes,m,p in rows:
        if n=='C0':p,count=re.subn(r'(?<!\w)multi=1\b','multi=4',p);assert count==1 and m=='cfmom_2t'
        newrows.append((n,nodes,m,p))
    assert count==1;d[clone]=emit(clone,newrows,ports(d[master]));bbm=[]
    for n,nodes,m,p in instances(d['sar8p_nonoverlap']):bbm.append((n,nodes,clone if n=='XD_HD' else m,p))
    d['sar8p_nonoverlap']=emit('sar8p_nonoverlap',bbm,ports(d['sar8p_nonoverlap']));after=flatten(d,TOP,binding)
    changed=[n for n in before if before[n]!=after[n]];assert changed==[TARGET] and set(before)==set(after)
    old,new=before[TARGET],after[TARGET];a,b=params(old['parameters']),params(new['parameters'])
    assert old['nodes']==new['nodes'] and old['model']==new['model'] and a.pop('multi')=='1' and b.pop('multi')=='4' and a==b
    examples={}
    for n,x in before.items():
        if x['model']!='cfmom_2t':continue
        p=params(x['parameters']);multi=p.pop('multi')
        if p==a and multi in ['2','200']:examples['same_unit_multi'+multi]=dict(instance=n,parameters=x['parameters'])
        if multi=='4':examples.setdefault('same_model_multi4',dict(instance=n,parameters=x['parameters']))
    assert 'same_model_multi4' in examples and 'same_unit_multi2' in examples
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs';dut.write_text('\n\n'.join(d[n] for n in closure(d,[TOP]))+'\n');cases=[]
    contrast=dict(instance=TARGET,old_multi=1,new_multi=4,model='cfmom_2t',old_parameters=old['parameters'],new_parameters=new['parameters'],nodes=new['nodes'],
        all195_other_flat_records_identical=True,all_commands_and_saves_identical=True,HD_master_cloned_to_avoid_changing_LD=True,
        model_parameter_evidence=examples,legality_scope='Unit geometry unchanged and previously native accepted; model multi4 exists in same completed fixture at lr2u, multi2/200 at target lr2.5u. Native candidate validation still required; no layout signoff.')
    for corner in ['ffcold','sscold']:
        prior=OLD/corner;folder=OUT/corner;folder.mkdir(exist_ok=True);(folder/'test.scs').write_bytes((prior/'test.scs').read_bytes())
        cfg=json.loads((prior/'measurement.json').read_text());cfg.update(variant=VARIANT,scope='Only HD delay-leg C0 MOM multi1->4 on complete BBM/real load; CODE/sampling unchanged, no RC1 repair or wholeADC claim',single_component_contrast=contrast)
        cfg['comparison_baseline']=dict(run='sar8audit-real-bbm-'+corner,result_sha256=sha(ROOT/'output/managed_execution/runs'/('sar8audit-real-bbm-'+corner)/'collected/derived/result.json'),
            baseline_dut_sha256=sha(OLD/'dut.scs'),exact_one_flat_record_change=TARGET,all_input_clocks_and_waveforms_unchanged=True)
        files={'dut.scs':dut,'test.scs':folder/'test.scs','reference_current_analyze.py':HERE/'reference_current_analyze.py','io_cell_analyze.py':HERE/'io_cell_analyze.py',
            'real_bbm_analyze.py':HERE/'real_bbm_analyze.py','bbm_hdc0_analyze.py':HERE/'bbm_hdc0_analyze.py','bbm_boundary.json':OLD/'bbm_boundary.json'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()};validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=json.loads((prior/'recipe_proposal.json').read_text());recipe.update(run_id='sar8audit-bbm-hdc0x4-'+corner,design_id='sar8_reference_BBM_HD_C0_multi4_single_variable',
            analyzer='bbm_hdc0_analyze.py',qualification_scope=cfg['scope'],inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=VARIANT;save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
            files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(cfg['voltage_saves']),mandatory_currents=len(cfg['current_saves']),terminal_screens=len(cfg['selected_mos_pair_screens']),KCL=len(cfg['kcl_terms']),native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms']))))
    save(OUT/'package_review.json',dict(status='local_unexecuted_HD_C0_multi4_only',registered=False,simulation_started=False,baseline_dut_sha256=sha(OLD/'dut.scs'),candidate_dut_sha256=sha(dut),
        primitive_count=196,MOS_count=123,single_component_contrast=contrast,cases=cases))
    print('BBM_HD_C0X4_LOCAL_PAIR_READY',[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':prepare()
