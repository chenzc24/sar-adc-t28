"""Full standard-cell candidate and isolated loaded storage benches; local only."""
from __future__ import annotations
import collections
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re

import prepare_first_event as base

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN / 'standard_cell_full_v1'
INV = 'INVD1BWP12T30P140'
ND = 'ND2D1BWP12T30P140'
FF = 'DFCNQD1BWP12T30P140'
STOP = 20e-9


def read(path):
    return json.loads(Path(path).read_bytes())


def header(block):
    return block.replace('\\\n', ' ').splitlines()[0].split()[2:]


def replace_statement(block, name, replacement):
    lines=block.splitlines(True)
    found=[i for i,line in enumerate(lines) if re.match(r'^\s*'+re.escape(name)+r'\s+\(',line)]
    if len(found)!=1:raise ValueError('Exact statement count differs: '+name)
    i=found[0];end=i+1
    while lines[end-1].rstrip().endswith('\\'):
        end+=1
    lines[i:end]=[('    '+replacement+'\n') if replacement else '']
    return ''.join(lines)


def source():
    m = read(OWN / 'standard_cell_mapping.json')
    f = m['source_full_ADC']
    text = (ROOT / f['path']).read_text()
    if base.digest((ROOT / f['path']).read_bytes()) != f['sha256']:
        raise ValueError('Frozen full ADC source differs')
    return text, m


def switch_states(cell, fixed):
    """Enumerate ideal-switch DC solutions, including unpowered memory states.

    No timing, analog charge sharing, noise or metastability claim is made.
    Every conducting D/S component must have a single Boolean value.
    """
    devices = cell['MOS']
    nodes = sorted({x[k] for x in devices for k in ['D', 'G', 'S', 'B']})
    free = sorted(set(nodes) - set(fixed))
    if len(free) > 18:
        raise ValueError('Bounded switch-state query exceeds18 unknown bits')
    result = []
    for bits in itertools.product((0, 1), repeat=len(free)):
        v = dict(fixed, **dict(zip(free, bits)))
        valid = True
        for d in devices:
            on = v[d['G']] == (1 if d['master'].startswith('nch_') else 0)
            if on and v[d['D']] != v[d['S']]:
                valid = False
                break
        if valid:
            result.append(v)
    return result


def library_truth(probe):
    cells = probe['cells']
    expected = {INV: ['I', 'ZN', 'VDD', 'VSS'],
                ND: ['A1', 'A2', 'ZN', 'VDD', 'VSS'],
                FF: ['D', 'CP', 'CDN', 'Q', 'VDD', 'VSS']}
    for name, pins in expected.items():
        if cells[name]['pins'] != pins or cells[name]['non_MOS_statements']:
            raise ValueError('Actual foundry pins/body class differs')
        if any(d['master'] not in ['nch_mac', 'pch_mac'] for d in cells[name]['MOS']):
            raise ValueError('Unverified native model')
        if any(d['dimension_units'] != {'l': 'n', 'w': 'n'} for d in cells[name]['MOS']):
            raise ValueError('Explicit native dimension units differ')
    rows = {}
    for name, inputs in [(INV, ['I']), (ND, ['A1', 'A2'])]:
        rows[name] = []
        for bits in itertools.product((0, 1), repeat=len(inputs)):
            inp = dict(zip(inputs, bits))
            states = switch_states(cells[name], dict(VDD=1, VSS=0, **inp))
            values = sorted({s['ZN'] for s in states})
            want = 1 - (inp['I'] if name == INV else inp['A1'] & inp['A2'])
            if values != [want]:
                raise ValueError('Library INV/NAND truth differs')
            rows[name].append(dict(inputs=inp, outputs=values, stable_states=len(states)))
    reduced = []
    states_by = {}
    for cp, d, cdn in itertools.product((0, 1), repeat=3):
        states = switch_states(cells[FF], dict(VDD=1, VSS=0, CP=cp, D=d, CDN=cdn))
        if not states:
            raise ValueError('No stable DFCNQ state')
        if cdn == 0 and {x['Q'] for x in states} != {0}:
            raise ValueError('DFCNQ is not asynchronous low clear')
        if cdn and cp == 0 and {x['mq'] for x in states} != {d}:
            raise ValueError('DFCNQ master is not transparent at CP low')
        if cdn and cp == 1 and any(x['Q'] != x['mq'] for x in states):
            raise ValueError('DFCNQ slave is not transparent at CP high')
        states_by[cp, d, cdn] = states
        reduced.append(dict(CP=cp, D=d, CDN=cdn, stable_states=len(states),
                            Q_values=sorted({x['Q'] for x in states}),
                            mq_values=sorted({x['mq'] for x in states})))
    transitions = []
    for oldq, d, newd in itertools.product((0, 1), repeat=3):
        low = [x for x in states_by[0, d, 1] if x['Q'] == oldq]
        high = [x for x in states_by[1, newd, 1] if x['mq'] == d]
        if not low or not high or {x['Q'] for x in high} != {d}:
            raise ValueError('Ideal positive-edge transfer proof failed')
        low_after = [x for x in states_by[0, newd, 1] if x['Q'] == d]
        if not low_after:
            raise ValueError('Falling edge hold proof failed')
        transitions.append(dict(previous_Q=oldq, D_before_rise=d,
                                D_after_rise=newd, Q_after_rise=d,
                                falling_edge_preserves_Q=True))
    return dict(actual_cell_graph_verified=True, combinational=rows,
                DFCNQ_stable_rows=reduced, ideal_rising_transfer=transitions,
                CP='positive edge in ideal switch/master-memory model',
                CDN='asynchronous active-low output clear; reset output0 for both clock levels',
                difference_from_custom='During asserted clear with CP low native master may track D; output Q remains0. Original custom master was also cleared. Native overlap/release must be tested.',
                dynamic_native_timing_verified=False,
                setup_hold_recovery_removal_limits=None,
                method='Enumerate every Boolean internal node, actual MOS on-state D/S constraints, and continuity of master/slave memory across clock phases; not SPICE or Liberty timing.')


def candidate(text):
    original = base.cells(text)
    replacements = {
        'sar8p_inv': 'subckt sar8p_inv A VDD VSS Y\n'
                     '    XLIB (A Y VDD VSS) ' + INV + '\nends sar8p_inv',
        'sar8p_nand2': 'subckt sar8p_nand2 A B VDD VSS Y\n'
                       '    XLIB (A B Y VDD VSS) ' + ND + '\nends sar8p_nand2',
        'sar8p_clkbuf': 'subckt sar8p_clkbuf A VDD VSS Y\n'
                        '    X000 (A VDD VSS AB) sar8p_inv\n'
                        '    XFINAL (AB VDD VSS Y) sar8p_inv\nends sar8p_clkbuf',
        'sar8p_dffr': 'subckt sar8p_dffr CK D Q RST VDD VSS\n'
                      '    XRESET (RST RN VDD VSS) ' + INV + '\n'
                      '    XFF (D CK RN Q VDD VSS) ' + FF + '\nends sar8p_dffr'}
    driver_pairs = []
    for master in sorted(k for k in original if re.fullmatch(r'sar8p_refdrv_b[0-7]', k)):
        block = original[master]
        parts = base.parts(block)
        for name, nmos in parts.items():
            if nmos['model'] != 'nch_mac':
                continue
            pnames = [k for k, v in parts.items() if v['model'] == 'pch_mac'
                      and v['nodes'][:2] == nmos['nodes'][:2]]
            if len(pnames) != 1 or nmos['nodes'][2:] != ['VSS', 'VSS']:
                raise ValueError('Unclassified reference pull-down pair')
            pname = pnames[0]
            if parts[pname]['nodes'][2:] != ['VDD', 'VDD']:
                raise ValueError('Nonordinary reference pull-up requires separate treatment')
            d, g = nmos['nodes'][:2]
            # Entire ordinary CMOS inverter pair replaced; real Rgate remains.
            block = replace_statement(block,name,
                                      'XSTD_' + name + ' (' + ' '.join([g, d, 'VDD', 'VSS']) + ') ' + INV)
            block = replace_statement(block,pname,'')
            driver_pairs.append(dict(master=master, removed=[name, pname],
                                     input=g, output=d, candidate_master=INV,
                                     drive='D1 initial candidate, not load/slew qualified',
                                     reason='Ordinary core CMOS inverter; analog load is not exemption'))
        replacements[master] = block
    if len(driver_pairs) != 96:
        raise ValueError('Exactly96 ordinary reference-driver inverter pairs expected')
    new = text
    for master, block in replacements.items():
        new = new.replace(original[master], block)
    after = base.cells(new)
    for master in set(original) - set(replacements):
        if after[master] != original[master]:
            raise ValueError('Unowned source block changed: ' + master)
    if header(after['sar_adc8_join_r4']) != header(original['sar_adc8_join_r4']):
        raise ValueError('Top pin contract changed')
    return new, driver_pairs, sorted(replacements)


def expand_library(text, top, probe, rootports):
    flat = base.flatten(text, top, rootports)
    libraries = {}
    for path, part in list(flat.items()):
        if part['model'] not in probe['cells']:
            continue
        cell = probe['cells'][part['model']]
        bind = dict(zip(cell['pins'], part['nodes']))
        if len(bind) != len(cell['pins']):
            raise ValueError('Library pin count mismatch')
        del flat[path]
        for d in cell['MOS']:
            p = path + '.' + d['instance']
            flat[p] = dict(model=d['master'], nodes=[bind.get(d[t], path + '.' + d[t])
                                                   for t in ['D', 'G', 'S', 'B']],
                           parameters='READ_ONLY_NATIVE_LIBRARY_NOT_COPIED')
            libraries[p] = dict(master=part['model'], native_instance=d['instance'])
    return flat, libraries


def flat_project(text):
    c = base.cells(text)
    return base.flatten(text, 'sar_adc8_join_r4', {k: k for k in header(c['sar_adc8_join_r4'])})


def migration_manifest(original, new, pairs, changed, mapping, probe):
    oldflat = flat_project(original)
    newflat, lib = expand_library(new, 'sar_adc8_join_r4', probe,
                                  {k: k for k in header(base.cells(new)['sar_adc8_join_r4'])})
    retained = {p: v for p, v in oldflat.items() if p in newflat and newflat[p] == v}
    clear = {p: v for p, v in newflat.items() if p not in lib and v['model'] in ['nch_mac', 'pch_mac']}
    if len(clear) != 60 or any(not p.endswith(('.MN_CLEAR', '.MP_CLEAR')) for p in clear):
        raise ValueError('Remaining nonlibrary core MOS are not exactly30 RC-clear pairs')
    for p, part in oldflat.items():
        if any(x in p for x in ['.XBOOTN.', '.XBOOTP.', '.XCDAC.', '.XCOMP.']) or '.RG' in p:
            if newflat.get(p) != part:
                raise ValueError('Protected analog/Rgate source changed: ' + p)
    delays = [u for u in mapping['units'] if u['kind'] == 'RC_pulse_qualification']
    return dict(source=mapping['source_full_ADC'], source_role='Original core-reference audit baseline, NOT later IO/single-GPP repair',
                candidate_dut_sha256=base.digest(new.encode()), changed_source_masters=changed,
                ordinary_reference_pairs=pairs, ordinary_reference_pairs_count=96,
                retained_custom_core_MOS=clear,
                retained_custom_core_reason='60 MOS are charge-clear devices in30 RC timing blocks, not standalone Boolean inverters. No other ordinary core inverter is exempted.',
                retained_delay_blocks=[dict(instance=u['instance'], master=u['master'], ports=u['ports'],
                    retained='R0/R1/C0/C1/MN_CLEAR/MP_CLEAR byte-identical; three INV standardized',
                    limits='RC input slew, clear/reset, PVT delay and overshoot remain unqualified') for u in delays],
                retained_SR_CQB='Both explicit wrapper CQB MOM capacitors unchanged; library hidden nodes untouched',
                removed_private_passives=[p for p in oldflat if p not in newflat and oldflat[p]['model'] == 'cfmom_2t'],
                analog_leaves_unchanged=len(retained), native_library_MOS=len(lib),
                total_candidate_MOS=sum(v['model'].startswith(('nch_', 'pch_')) for v in newflat.values()),
                reference_Rgate_and_real_CDAC_retained=True, fitted_equivalent_load_capacitors_added=0,
                top_external_pin_order_unchanged=True, external_stimulus_modified=False,
                internal_effective_sampling_edge='Propagation changes are unmeasured; must verify against protected source-close contract before adoption. No input edge retiming or forced internal alignment.',
                architecture_or_handshake_changed=False, digital_library_drive='D1 everywhere as first complete structural candidate, not frozen optimal drive strength',
                full_ADC_qualified=None, OA_modified=False)


def sr_phases():
    states = [(1, 0), (0, 0), (0, 1), (0, 0), (1, 0),
              (1, 1), (0, 1), (1, 1), (1, 0), (0, 0)]
    result, q = [], 0
    for i, (r, s) in enumerate(states):
        q = 0 if r else 1 if s else q
        result.append(dict(index=i, start_s=i * 1e-9, stop_s=(i + 1) * 1e-9,
                           R=r, S=s, Q=q, QB=1-q,
                           hold_start_s=(i+.4)*1e-9, hold_stop_s=(i+.9)*1e-9))
    result.append(dict(index=10, start_s=10e-9, stop_s=STOP, R=0, S=0, Q=0, QB=1,
                       hold_start_s=10.4e-9, hold_stop_s=19.9e-9))
    return result


def ff_phases():
    # CK,D,RST. Reset priority is exercised at either clock level and at a rise.
    states = [(0,0,1),(0,1,1),(0,1,0),(1,1,0),(1,0,0),
              (0,0,0),(1,0,0),(1,1,0),(0,1,0),(1,1,0),
              (1,1,1),(1,1,0),(0,1,0),(1,1,1),(1,0,1),
              (0,0,0),(1,0,0),(0,1,0),(1,1,0),(1,1,1)]
    result, oldck, q = [], 0, 0
    for i, (ck,d,r) in enumerate(states):
        if r: q=0
        elif not oldck and ck: q=d
        result.append(dict(index=i, start_s=i*1e-9, stop_s=(i+1)*1e-9,
                           CK=ck,D=d,RST=r,Q=q, overlap_clock_reset=(i==13),
                           hold_start_s=(i+.4)*1e-9,hold_stop_s=(i+.9)*1e-9))
        oldck=ck
    return result


def input_names(master):
    if master == 'sar8p_dffr': return ['CK','D','RST']
    if master == 'sar8p_sr': return ['R','S']
    if master == 'sar8p_mux2': return ['D0','D1','SEL']
    return ['A','B'] if master in ['sar8p_and2','sar8p_or2','sar8p_nand2','sar8p_xor2'] else ['A']


def output_names(master):
    return ['Q'] if master in ['sar8p_dffr','sar8p_sr'] else ['Y']


def loaded_fixture(new, mapping, probe):
    """All26 storage instances, each with exact native immediate input fanout.

    Fanout blocks retain native full cells or complete RC qualification blocks.
    Other inputs are independently conditioned; outputs end at the cut, not at
    a fitted capacitor. This is explicitly not downstream analog/ADC closure.
    """
    cells=base.cells(new); units=mapping['units']
    targets=[u for u in units if u['master'] in ['sar8p_dffr','sar8p_sr']]
    lines=['subckt sar8audit_std_storage VDD VSS SR_R SR_S FF_CK FF_D FF_RST CONTEXT']
    observations=[]; boundaries=[]; loadcount=0
    for i,u in enumerate(targets):
        name='U%02d'%i; q=name+'_Q'; master=u['master']; ports=u['ports']
        if master=='sar8p_sr':
            # Real standard gate drivers, independent commands; no ideal SR pin clamp.
            lines += ['    XR%s (SR_R VSS VDD VSS %s_R) sar8p_or2'%(name,name),
                      '    XS%s (SR_S VDD VDD VSS %s_S) sar8p_and2'%(name,name),
                      '    X%s (%s %s_R %s_S VDD VSS) sar8p_sr'%(name,q,name,name)]
            obs=dict(name=name,source_instance=u['instance'],kind='SR',Q='XDUT.'+q,
                     QB='XDUT.X'+name+'.QB',R='XDUT.'+name+'_R',S='XDUT.'+name+'_S')
        else:
            lines += ['    XC%s (FF_CK VDD VSS %s_CK) sar8p_clkbuf'%(name,name),
                      '    XD%s (FF_D VDD VSS %s_D) sar8p_buf'%(name,name),
                      '    XR%s (FF_RST VDD VSS %s_RST) sar8p_buf'%(name,name),
                      '    X%s (%s_CK %s_D %s %s_RST VDD VSS) sar8p_dffr'%(name,name,name,q,name)]
            obs=dict(name=name,source_instance=u['instance'],kind='DFF',Q='XDUT.'+q,
                     CK='XDUT.'+name+'_CK',D='XDUT.'+name+'_D',RST='XDUT.'+name+'_RST',
                     CDN='XDUT.X'+name+'.RN')
        observations.append(obs)
        original_q=ports['Q']; loads=[]
        for v in units:
            if v['instance']==u['instance'] or v['instance'].startswith(u['instance']+'.'):
                continue
            incoming=[k for k in input_names(v['master']) if v['ports'].get(k)==original_q]
            if incoming:
                loads.append((v,incoming))
        # Pure inverters in the original direct reference driver are now native
        # library instances; storage Q only reaches them through BBM, not directly.
        for j,(v,incoming) in enumerate(loads):
            wire={}; conditioning={}
            for pin,node in v['ports'].items():
                if pin=='VDD': wire[pin]='VDD'
                elif pin=='VSS': wire[pin]='VSS'
                elif pin in incoming: wire[pin]=q
                elif pin in output_names(v['master']): wire[pin]=name+'_L%d_'%j+pin
                elif pin=='RST': wire[pin]='VDD';conditioning[pin]='VDD (load register held reset; no forced target state)'
                elif pin in ['CK','R','S']: wire[pin]='VSS';conditioning[pin]='VSS'
                else: wire[pin]='CONTEXT';conditioning[pin]='CONTEXT'
            lines.append('    XL%s_%d (%s) %s'%(name,j,' '.join(wire[k] for k in header(cells[v['master']])),v['master']))
            loadcount+=1
            boundaries.append(dict(target=u['instance'],original_output_node=original_q,
                replica='XDUT.XL'+name+'_'+str(j),source_load_instance=v['instance'],
                source_master=v['master'],signal_input_pins=incoming,other_input_conditioning=conditioning,
                output_cut='Native load-cell outputs retain their own transistor networks, with subsequent fanout omitted; no fitted capacitance.',
                complete_RC_block_retained=v['kind']=='RC_pulse_qualification'))
        obs['native_immediate_load_blocks']=len(loads)
        if not loads: raise ValueError('Target has no source immediate fanout')
    lines.append('ends sar8audit_std_storage')
    # Only reachable definitions are carried to the testbench, never unused ADC.
    extra='\n'.join(lines)+'\n';alltext=new+'\n'+extra;allcells=base.cells(alltext)
    needed=set()
    def visit(master):
        if master in needed:return
        needed.add(master)
        for p in base.parts(allcells[master]).values():
            if p['model'] in allcells:visit(p['model'])
    visit('sar8audit_std_storage')
    reduced='\n\n'.join(allcells[k] for k in sorted(needed))+'\n'
    return reduced, observations, boundaries, loadcount


def pwl(phases,key,vdd):
    rows=[(0., phases[0][key]*vdd)];last=rows[0][1]
    for ph in phases[1:]:
        value=ph[key]*vdd
        if value != last:
            rows += [(ph['start_s']-10e-12,last),(ph['start_s']+10e-12,value)]
            last=value
    rows.append((STOP,last))
    return ''.join('%.17g %.17g\n'%r for r in rows)


def measurement(text,observations,probe,vdd):
    root={'VDD':'VDD!','VSS':'0',**{k:k for k in ['SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT']}}
    flat,library=expand_library(text,'sar8audit_std_storage',probe,root)
    mos={};catalog={};pairs={}
    for path,item in flat.items():
        ismos=item['model'].startswith(('nch_','pch_'));roles=['D','G','S','B'] if ismos else ['PLUS','MINUS']
        for port,node in enumerate(item['nodes'],1):
            catalog[path+':'+str(port)]=dict(instance=path,terminal=roles[port-1],port=port,node=node)
        if ismos:
            d,g,s,b=item['nodes'];mos[path]=dict(model=item['model'],nodes=item['nodes'],library=path in library)
            for label,(a,z) in dict(VGS=(g,s),VGD=(g,d),VDS=(d,s),VGB=(g,b),VDB=(d,b),VSB=(s,b)).items():
                pairs[path+'_'+label]=dict(positive_node=a,negative_node=z,limit_abs_v=.99)
    for name,node in [('VVDD','VDD!')]+[('V'+x,x) for x in ['SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT']]:
        catalog[name+':1']=dict(instance=name,terminal='PLUS',port=1,node=node)
    volts=sorted({n for x in flat.values() for n in x['nodes'] if n!='0'})
    currents=sorted(catalog)
    kcl={n:[p.lower() for p,v in catalog.items() if v['node']==n] for n in volts if n!='VDD!'}
    functional=sorted({x[k] for x in observations for k in ['Q','QB','R','S','CK','D','RST','CDN'] if k in x})
    # Keep every voltage/timestamp for functional, all internal stress/history
    # is streamed from raw. Few selected power currents bound returned bytes.
    source_ports={name:dict(voltage_node=node,current=name+':1') for name,node in
                  [('VVDD','VDD!')]+[('V'+x,x) for x in ['SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT']]}
    max_wave=64*1024**2
    return dict(scope='All26 isolated standard storage contexts with native immediate fanout; not whole ADC/analog driver qualification',
        voltage_saves=volts,current_saves=currents,terminal_current_catalog=catalog,observed_mos=mos,
        library_mos=library,stress_voltage_pairs=pairs,kcl_terms=kcl,critical_kcl_nodes=[],
        diagnostic_voltage_columns=sorted(set(functional+['VDD!','SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT'])),
        diagnostic_current_columns=[p['current'] for p in source_ports.values()],
        diagnostic_start_s=0.,diagnostic_stop_s=STOP,source_history_stop_s=STOP,
        max_derived_binary_bytes=max_wave,source_power_ports=source_ports,
        expected_edges={},expected_initial_state=dict(values_v={'VDD!':vdd}),
        expected_native_peak=dict(node=observations[0]['Q'],value_v=0.,time_s=0.),
        proposed_reproduction_contract=dict(status='not_a_source_peak_fit_or_ADC_gate'),
        storage=dict(observers=observations,SR_phases=sr_phases(),DFF_phases=ff_phases(),
                     hold_rail_low=.1,hold_rail_high=.9,collection_cap_bytes=30*1024**2,
                     user_collection_cap_bytes=32*1024**2,final_state_reserve_bytes=256*1024,
                     max_analysis_rss_bytes=256*1024**2,
                     raw_all_actual_MOS_ports=True,full_history_all_KCL=True,
                     raw_retained_remote=True,phase_expected_end_source='independent20ps commands; actual native pins also checked',
                     corner_boundary_policy='Each corner regenerates command levels from its own VDD, no FF analogue history retagged SS'))


def main():
    probe=read(OUT/'library_probe.json');truth=library_truth(probe)
    base.write_json(OUT/'library_truth.json',truth)
    old,mapping=source();new,pairs,changed=candidate(old)
    base.exact_write(OUT/'full_adc/dut.scs',new)
    base.write_json(OUT/'migration_manifest.json',migration_manifest(old,new,pairs,changed,mapping,probe))
    bench,observers,boundaries,count=loaded_fixture(new,mapping,probe)
    base.exact_write(OUT/'storage_dut.scs',bench)
    base.write_json(OUT/'load_boundaries.json',dict(native_load_replicas=count,targets=len(observers),
        boundaries=boundaries,scope='Exact mapped immediate gate/complete RC input fanout only. Subsequent output loading and ADC feedback omitted deliberately; full candidate retains all actual Rgate/CDAC.',
        driver_boundary='Independent command sources drive standard real R/S or CK/D/RST drivers. These are testbench conditioners, not a claim that all original upstream ADC qualification paths are reproduced.',
        no_fitted_load_capacitance=True,no_ideal_internal_Q_clamp=True,source_baseline='Original core-reference b9bf source, not later IO repairs'))
    template=read(OWN/'sr_cycle_v1/rb_upper/recipe.suggested.yaml')
    base_deck=(OWN/'sr_cycle_v1/rb_upper/test.scs').read_text()
    model_lines=[l for l in base_deck.splitlines() if l.startswith('include "/home/process/')]
    cases={}
    for tag,corner,vdd,temp in [('ff','ff',.99,-40),('ss','ss',.81,-40)]:
        dest=OUT/tag;run='sar8audit-ctrl-stdfull-storage-'+tag+'-v1'
        cfg=measurement(bench,observers,probe,vdd)
        base.write_json(dest/'measurement.json',cfg)
        deck='simulator lang=spectre\nglobal 0 VDD!\n'+'\n'.join(model_lines).replace('ffmacro_mos_moscap',corner+'macro_mos_moscap')+'\n'
        spi=next(k for k in probe['files'] if k.endswith('.spi'))
        deck+='simulator lang=spice\n.include "'+spi+'"\nsimulator lang=spectre\ninclude "dut.scs"\n'
        deck+='VVDD (VDD! 0) vsource dc=%.17g\n'%vdd
        for kind,phases,keys in [('SR',sr_phases(),['R','S']),('FF',ff_phases(),['CK','D','RST'])]:
            for key in keys:
                name=kind+'_'+key;file='pwl/'+name.lower()+'.pwl'
                base.exact_write(dest/file,pwl(phases,key,vdd))
                deck+='V%s (%s 0) vsource type=pwl file="%s"\n'%(name,name,file)
        # Other native fanout-cell inputs switch independently, exposing real
        # feedthrough without recreating a global ADC feedback experiment.
        ctx=[dict(start_s=i*2e-9,CONTEXT=i%2) for i in range(10)]
        base.exact_write(dest/'pwl/context.pwl',pwl(ctx,'CONTEXT',vdd))
        deck+='VCONTEXT (CONTEXT 0) vsource type=pwl file="pwl/context.pwl"\n'
        deck+='XDUT (VDD! 0 SR_R SR_S FF_CK FF_D FF_RST CONTEXT) sar8audit_std_storage\n'
        deck+='simulatorOptions options psfversion="1.4.0" method=gear2only reltol=1e-6 vabstol=1e-8 iabstol=1e-13 temp=%d tnom=27 scalem=1 scale=1 gmin=1e-12 rforce=1 checklimitdest=psf\n'%temp
        deck+='saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no\ntran_first tran stop=20n maxstep=10p errpreset=conservative lteratio=10\n'
        deck+=''.join('save '+s+'\n' for s in sorted(cfg['voltage_saves']+cfg['current_saves']))
        base.exact_write(dest/'test.scs',deck)
        external=dict(file=spi,**probe['files'][spi],model_files={p:v for p,v in probe['files'].items() if p!=spi},
                      parser_mode='Original SPICE include then restore spectre; numeric1..4 currents on actual M instance',
                      foundry_contents_copied=False)
        base.write_json(dest/'external_library.json',external)
        files=[('test.scs',dest/'test.scs'),('dut.scs',OUT/'storage_dut.scs'),('measurement.json',dest/'measurement.json'),
               ('external_library.json',dest/'external_library.json'),('library_probe.json',OUT/'library_probe.json'),
               ('library_truth.json',OUT/'library_truth.json'),('load_boundaries.json',OUT/'load_boundaries.json'),
               ('full_gate_analyze.py',OWN/'full_gate_analyze.py'),('standard_cell_full_analyze.py',OWN/'standard_cell_full_analyze.py')]
        files += [('pwl/'+p.name,p) for p in sorted((dest/'pwl').glob('*.pwl'))]
        recipe=copy.deepcopy(template)
        recipe.update(run_id=run,design_id='standard_cell_full_storage_'+tag,
                      analyzer='standard_cell_full_analyze.py',expected_stop_s=STOP,
                      qualification_scope=cfg['scope'],summary_signals=[o['Q'].lower() for o in observers])
        recipe['test_conditions'].update(corner=corner,vdd=vdd,temperature_c=temp)
        recipe['spectre_args']=['+preset=cx','+mt=1','+lqtimeout','60','-preset_override']
        recipe['resources'].update(threads=1,simulation_rss_mib=1024,analysis_rss_mib=256,
                                  simulation_wall_seconds=1200,analysis_wall_seconds=1200,max_output_mib=2048)
        recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
        base.write_json(dest/'recipe.suggested.yaml',recipe)
        freeze=dict(recipe_file_sha256=base.digest((dest/'recipe.suggested.yaml').read_bytes()),
                    inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files])
        base.write_json(dest/'freeze.json',freeze)
        cases[tag]=dict(run_id=run,**freeze,observed_MOS=len(cfg['observed_mos']),
                        physical_pairs=len(cfg['stress_voltage_pairs']),raw_voltages=len(cfg['voltage_saves']),
                        raw_currents=len(cfg['current_saves']),returned_voltage_columns=len(cfg['diagnostic_voltage_columns']),
                        returned_current_columns=len(cfg['diagnostic_current_columns']),
                        temporary_binary_cap_mib=64,returned_waveform='lossless gzip, every native row',collection_guard_mib=30,user_collection_mib=32,
                        submitted=False)
    base.write_json(OUT/'manifest.json',dict(cases=cases,full_ADC_candidate_ready_structurally=True,
        full_ADC_native_simulated=False,storage_contexts=len(observers),native_load_replicas=count,
        whole_ADC_sampling_contract_modified=False,server_queries='one bounded read-only library/model metadata query',
        old_custom_SR_pair_not_submitted=True,OA_modified=False))
    print(json.dumps({k:{a:v[a] for a in ['run_id','observed_MOS','physical_pairs','raw_voltages','raw_currents','recipe_file_sha256']} for k,v in cases.items()},indent=2))


if __name__=='__main__':
    main()
