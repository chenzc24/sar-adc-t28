"""Prepare original bit0 BBM standard-cell migration; local inputs only."""
from __future__ import annotations
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
from build_first_fixture import definitions, instances, ports, emit, flatten, closure

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE / 'generated/real_bbm_v1'
OUT = HERE / 'standard_cell_bbm_v1'
PROBE = HERE.parent / 'control/standard_cell_full_v1/library_probe.json'
TOP = 'sar8_realpre_unit'
INV, ND = 'INVD1BWP12T30P140', 'ND2D1BWP12T30P140'
VARIANT = 'original_bit0_BBM_native_stdcell_D1_ideal_CODE'
BASE_SHA = '5d4318d63e50ef8ea66443cf87f3db44edf16d169d824ab10d7604268194dae4'
SPI_SHA = 'b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_bytes())


def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def metadata():
    probe = read(PROBE)
    spi = next(p for p in probe['files'] if p.endswith('.spi'))
    assert probe['files'][spi] == dict(bytes=2452584, sha256=SPI_SHA)
    assert probe['query_read_only'] and not probe['foundry_geometry_or_body_copied']
    for name, pins, count in [(INV, ['I','ZN','VDD','VSS'], 2),
                              (ND, ['A1','A2','ZN','VDD','VSS'], 4)]:
        cell = probe['cells'][name]
        assert cell['pins'] == pins and len(cell['MOS']) == count
        assert not cell['non_MOS_statements']
        assert all(d['master'] in ['nch_mac','pch_mac'] and
                   d['dimension_units'] == dict(l='n',w='n') for d in cell['MOS'])
    nand = probe['cells'][ND]['MOS']
    assert next(d for d in nand if d['instance']=='MM4') == dict(
        B='VSS', D='ZN', G='A1', S='net10', dimension_units=dict(l='n',w='n'),
        instance='MM4', master='nch_mac')
    return probe, spi


def library_truth(probe):
    """Bounded actual-device ideal switch truth; no native timing claim."""
    rows = []
    for name, inputs in [(INV, ['I']), (ND, ['A1','A2'])]:
        cell = probe['cells'][name]
        nodes = {d[t] for d in cell['MOS'] for t in ['D','G','S','B']}
        for bits in itertools.product([0,1], repeat=len(inputs)):
            fixed = dict(VDD=1, VSS=0, **dict(zip(inputs,bits)))
            free = sorted(nodes-set(fixed)); values = set()
            for q in itertools.product([0,1], repeat=len(free)):
                v = dict(fixed, **dict(zip(free,q)))
                if all(v[d['D']]==v[d['S']] for d in cell['MOS']
                       if v[d['G']] == (1 if d['master']=='nch_mac' else 0)):
                    values.add(v['ZN'])
            expected = 1-(bits[0] if name==INV else bits[0]&bits[1])
            assert values == {expected}
            rows.append(dict(cell=name, inputs=dict(zip(inputs,bits)),
                             stable_outputs=sorted(values)))
    return rows


def binding(d):
    return {p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ports(d[TOP])}


def expanded(d, probe):
    flat = flatten(d, TOP, binding(d)); library = {}
    for n, part in list(flat.items()):
        if part['model'] not in [INV, ND]:
            continue
        cell = probe['cells'][part['model']]
        assert len(part['nodes']) == len(cell['pins'])
        bind = dict(zip(cell['pins'],part['nodes'])); del flat[n]
        for dev in cell['MOS']:
            path = n+'.'+dev['instance']
            flat[path] = dict(model=dev['master'],
                nodes=[bind.get(dev[t],n+'.'+dev[t]) for t in ['D','G','S','B']],
                parameters='EXTERNAL_NATIVE_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[path] = dict(cell=part['model'], native_MOS=dev['instance'])
    return flat, library


def candidate(probe):
    assert sha(OLD/'dut.scs') == BASE_SHA
    old = definitions((OLD/'dut.scs').read_text()); new = dict(old)
    new['sar8p_inv'] = emit('sar8p_inv',
        [('XLIB',['A','Y','VDD','VSS'],INV,'')],ports(old['sar8p_inv']))
    # Original output-adjacent NMOS gate A maps to native A1, not swapped.
    new['sar8p_nand2'] = emit('sar8p_nand2',
        [('XLIB',['A','B','Y','VDD','VSS'],ND,'')],ports(old['sar8p_nand2']))
    oldrows = list(instances(old[TOP])); replacements = []; removed = set(); pairs = {}
    for name, nodes, model, params in oldrows:
        if model != 'nch_mac':
            continue
        hits = [r for r in oldrows if r[2]=='pch_mac' and r[1][:2]==nodes[:2]]
        assert len(hits)==1 and nodes[2:]==['VSS','VSS']
        p = hits[0]; assert p[1][2:]==['VDD','VDD']
        assert re.fullmatch(r'G(?:NP|PN)[ABC]N',name)
        g, y = nodes[1],nodes[0]; fresh='XSTD_'+name
        replacements.append(dict(old_MOS=[name,p[0]],new_instance=fresh,
            cell=INV,input=g,output=y,initial_drive='D1 not load qualified'))
        removed.update([name,p[0]]); pairs[name]=(fresh,[g,y,'VDD','VSS'],INV,'')
    assert len(replacements)==6
    rows = [pairs[n] if n in pairs else (n,ns,m,p) for n,ns,m,p in oldrows
            if n not in removed or n in pairs]
    new[TOP]=emit(TOP,rows,ports(old[TOP]))
    before=flatten(old,TOP,binding(old)); after,library=expanded(new,probe)
    removed_flat=set(before)-set(after); added_flat=set(after)-set(before)
    assert added_flat==set(library)
    assert all(after[n]==before[n] for n in set(before)&set(after))
    omitted_caps=sorted(n for n in removed_flat if before[n]['model']=='cfmom_2t')
    assert omitted_caps==['XDUT.XBBM0.X002.X000.CMID','XDUT.XBBM0.X004.X000.CMID']
    clears=sorted(n for n,x in after.items() if x['model'] in ['nch_mac','pch_mac']
                  and n not in library and n.startswith('XDUT.XBBM0.'))
    assert clears==sorted('XDUT.XBBM0.XD_'+leg+'.'+dev for leg in ['HD','LD']
                          for dev in ['MN_CLEAR','MP_CLEAR'])
    for n in before:
        if n in removed_flat: continue
        assert after[n]==before[n]
    for leg in ['HD','LD']:
        for component in ['R0','R1','C0','C1','MN_CLEAR','MP_CLEAR']:
            key='XDUT.XBBM0.XD_'+leg+'.'+component
            assert after[key]==before[key]
    assert len(after)==194 and len(library)==42
    assert sum(x['model'].startswith(('nch_','pch_')) for x in after.values())==123
    migration=dict(baseline_dut_sha256=BASE_SHA,native_library_MOS=library,
        top_core_pair_replacements=replacements,
        changed_masters=[TOP,'sar8p_inv','sar8p_nand2'],
        removed_native_records=sorted(removed_flat),removed_custom_NAND_CMID=omitted_caps,
        retained_records=len(set(before)&set(after)),all_retained_records_exact=True,
        native_A1_maps_original_output_adjacent_A=True,
        native_NAND_A2_maps_original_source_adjacent_B=True,
        retained_RC_clear_MOS=clears,all_RC_and_clear_records_exact=True,
        C0_multi=1,all_IO_GNN_ABC_and_single_GPP_exact=True,
        Rgate_and_complete_CDAC_Bootstrap_comparator_reset_load_exact=True,
        exceptions=['RC MN_CLEAR/MP_CLEAR are analog charge reset, not Boolean gates',
                    'Existing GNN ABC and single GPP IO stages remain original',
                    'CDAC switches, Bootstrap and comparator analog devices unchanged'],
        source='generated/real_bbm_v1 original complete bit0; not full ADC',
        geometry_copied=False,external_library_only=True)
    return new, after, library, migration


def make_config(prior, graph, external, library, migration, corner):
    cfg=copy.deepcopy(prior)
    volts=sorted({p for x in graph.values() for p in x['nodes'] if p!='0'})
    currents=sorted(n+':'+str(j) for n,x in graph.items()
                    for j,p in enumerate(x['nodes'],1)
                    if n not in external or p!='0' or j==1)
    cat={}
    for b in currents:
        n,j=b.rsplit(':',1);j=int(j);x=graph[n]
        cat[b]=dict(instance=n,port=j,node=x['nodes'][j-1],model=x['model'])
    control={n:x for n,x in graph.items() if n in library or
             n.startswith('XDUT.XBBM0.')}
    critical={n for x in control.values() for n in x['nodes']}-{'VDD!','0'}
    critical|={n for n in prior['required_kcl_nodes'] if n in volts}
    kcl={n:[b for b,x in cat.items() if x['node']==n] for n in sorted(critical)}
    diag={b.lower() for q in kcl.values() for b in q}
    diag|={b.lower() for b,x in cat.items() if x['instance'] in control or
        re.match(r'XDUT\.(GNN[ABC][NP]|GPPI[NP]):',b) or
        re.match(r'XDUT\.XCDAC\.XS[NP]0\.(MN_LOW|MP_HIGH):',b) or
        b.startswith(('VVDD:','RREF','VREF','VCODE:'))}
    diagnostic_v=sorted(set(n.lower() for n in critical) |
        {n for n in prior['diagnostic_voltage_columns'] if n in {v.lower() for v in volts}})
    screens=[]
    for n,x in graph.items():
        if not x['model'].startswith(('nch_','pch_')):continue
        nodes=dict(zip('dgsb',x['nodes']))
        for a,b in ['ds','gs','gd','gb','bd','bs']:
            screens.append(dict(instance=n,model=x['model'],terminal=a+b,
                nodes=[nodes[a],nodes[b]],screen_v=.99 if x['model'] in ['nch_mac','pch_mac'] else 1.98))
    drivers={}
    for label,node,stem in [('L0','xdut.l0','xdut.xbbm0.x004.x001'),
            ('H0','xdut.h0','xdut.xbbm0.x002.x001'),
            ('PRE','xdut.pre','xdut.x025'),('GPNPRE','xdut.gpnpre','xdut.x008')]:
        drivers[label]=dict(node=node,source_port_branches=[stem+'.xlib.mm1:1',stem+'.xlib.mm0:1'])
    groups={}
    for n,x in graph.items():
        if not x['model'].startswith('pch'):continue
        groups[n]='BBM' if n.startswith('XDUT.XBBM0.') else 'H_driver_stdcell' if n.startswith(('XDUT.XSTD_','XDUT.X008.')) else 'X025_stdcell' if n.startswith('XDUT.X025.') else 'GNN_ABC_IO' if re.fullmatch(r'XDUT.GNN[ABC]P',n) else 'GPP_single_IO' if n=='XDUT.GPPIP' else 'physical_load'
    cfg.update(variant=VARIANT,scope='Native D1 ordinary core gates on original complete bit0 BBM/C0multi1; unchanged IO/Rgate/real loads; ideal CODE/rails, comparator reset, not full ADC qualification',
        voltage_saves=volts,current_saves=currents,terminal_current_catalog=cat,
        required_kcl_nodes=sorted(kcl),kcl_terms=kcl,
        selected_mos_pair_screens=screens,diagnostic_voltage_columns=diagnostic_v,
        diagnostic_current_columns=sorted(diag),edge_nodes=diagnostic_v,
        static_observations=diagnostic_v+['vvdd:1','vcode:1','rrefn:1','rrefp:1'],
        driver_source_ports=drivers,source_energy_groups=groups,
        mos_pair_scope='All123 actual MOS/738 six-pair screens; native core0.99V and retained IO1.98V, full0..52ns',
        standard_cell_migration=migration,
        comparison_baseline=dict(run='sar8audit-real-bbm-'+corner,baseline_dut_sha256=BASE_SHA,
            stimulus_and_solver_without_library_include_identical=True,
            internal_edges_not_aligned=True,full_ADC_candidate=False))
    cfg['boundary_inventory']=dict(all_actual_MOS=123,all_primitives=194,
        native_library_MOS=len(library),BBM_primitive_count=38,BBM_MOS=30,
        KCL_nodes=len(kcl),voltage_count=len(volts),mandatory_currents=len(currents))
    cfg['stimulus_contract']['standardization']='Ordinary core gates use original read-only library D1; RC/clear, IO and load exact; no internal timing compensation'
    return cfg


def prepare():
    probe,spi=metadata();truth=library_truth(probe)
    for c in read(OLD/'package_review.json')['cases']:
        for f in c['files']:assert sha(ROOT/f['source'])==f['sha256']
    defs,flat,library,migration=candidate(probe)
    OUT.mkdir(exist_ok=True);dut=OUT/'dut.scs'
    dut.write_text('\n\n'.join(defs[n] for n in closure(defs,[TOP]))+'\n',encoding='utf-8')
    migration['candidate_dut_sha256']=sha(dut)
    save(OUT/'migration.json',migration)
    save(OUT/'library_metadata.json',dict(cells={k:probe['cells'][k] for k in [INV,ND]},
        files=probe['files'],source_probe_sha256=sha(PROBE),
        actual_device_switch_truth=truth,foundry_geometry_copied=False,
        native_timing_verified=False))
    cases=[]
    from standard_cell_bbm_analyze import validate
    prefix='simulator lang=spice\n.include "'+spi+'"\nsimulator lang=spectre\n'
    for corner in ['ffcold','sscold']:
        folder=OUT/corner;folder.mkdir(exist_ok=True);prior=OLD/corner
        oldtest=(prior/'test.scs').read_text()
        body='\n'.join(l for l in oldtest.splitlines() if not l.startswith('save '))+'\n'
        assert body.count('include "dut.scs"\n')==1
        external={}
        for l in body.splitlines():
            m=re.fullmatch(r'(\w+) \(([^)]*)\) (\w+)(.*)',l)
            if m and m[1]!='XDUT':external[m[1]]=dict(nodes=m[2].split(),model=m[3],parameters=m[4].strip())
        graph=dict(flat);graph.update(external)
        cfg=make_config(read(prior/'measurement.json'),graph,external,library,migration,corner)
        test=body.replace('include "dut.scs"\n',prefix+'include "dut.scs"\n')
        assert test.replace(prefix,'',1)==body
        test+=''.join('save '+n+'\n' for n in sorted(set(cfg['voltage_saves']+cfg['current_saves'])))
        (folder/'test.scs').write_text(test,encoding='utf-8')
        files={'dut.scs':dut,'test.scs':folder/'test.scs',
            'reference_current_analyze.py':HERE/'reference_current_analyze.py',
            'io_cell_analyze.py':HERE/'io_cell_analyze.py',
            'standard_cell_bbm_analyze.py':HERE/'standard_cell_bbm_analyze.py',
            'migration.json':OUT/'migration.json','library_metadata.json':OUT/'library_metadata.json'}
        cfg['required_input_sha256']={n:sha(p) for n,p in files.items()}
        validate(cfg);save(folder/'measurement.json',cfg);files['measurement.json']=folder/'measurement.json'
        recipe=read(prior/'recipe_proposal.json')
        recipe.update(run_id='sar8audit-ref-bbm-stdcell-'+corner+'-v1',
            design_id='sar8_reference_original_bit0_stdcell_BBM_D1',
            analyzer='standard_cell_bbm_analyze.py',qualification_scope=cfg['scope'],
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=sha(p)) for n,p in files.items()])
        recipe['test_conditions']['variant']=VARIANT
        recipe['resources'].update(threads=4,simulation_rss_mib=1024,analysis_rss_mib=256)
        save(folder/'recipe_proposal.json',recipe)
        cases.append(dict(run_id=recipe['run_id'],recipe=(folder/'recipe_proposal.json').relative_to(ROOT).as_posix(),
            recipe_sha256=sha(folder/'recipe_proposal.json'),staged_bytes=sum(p.stat().st_size for p in files.values()),
            files=[dict(name=n,source=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()],
            signals=dict(voltages=len(cfg['voltage_saves']),currents=len(cfg['current_saves']),
                terminal_screens=len(cfg['selected_mos_pair_screens']),KCL=len(cfg['kcl_terms']),
                native_columns=1+len(cfg['diagnostic_voltage_columns'])+len(cfg['diagnostic_current_columns'])+len(cfg['kcl_terms']))))
    save(OUT/'package_review.json',dict(status='local_prepared_native_not_executed',
        registered=False,simulation_started=False,full_ADC_candidate=False,
        cases=cases,resource_notes=dict(simulation_threads=4,simulation_RSS_MiB=1024,
            analysis_RSS_MiB=256,derived_budget_MiB=30,expected_collection_MiB_max=32),
        native_acceptance_requires='Parent managed elaboration validates original SPICE/mac MM terminal current binding and model include; source hashes must be verified remotely before run.'))
    print('REFERENCE_STDCELL_BBM_LOCAL_READY',[(c['run_id'],c['staged_bytes'],c['signals']) for c in cases])


if __name__=='__main__':
    prepare()

