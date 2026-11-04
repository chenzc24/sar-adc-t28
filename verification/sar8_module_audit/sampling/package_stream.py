"""Local native-stream inputs for compact_v2; no registration or dispatch."""
import argparse
import json
import math
from pathlib import Path
import re

import builder as b
import compact_builder as c

HERE=c.HERE
OUT=HERE/'stream_package'
STREAM=b.ROOT/'output/sar8_physical_repair/sar8fix-loaded-both-rx2-tt/stream.cpp'
REMOTE=b.ROOT/'scripts/sar8_physical_repair/loaded_remote.py'


def build_inputs():
    manifest=json.loads((c.OUT/'manifest.json').read_text())
    for name,r in manifest['artifacts'].items():
        assert b.sha((c.OUT/name).read_bytes())==r['sha256'],name
    inv=json.loads((c.OUT/'boundary_loads.json').read_text())
    rows=inv['device_mapping_without_geometry']
    text=(c.OUT/'fixture_dut.scs').read_text()
    ports=b.parse_cells(text)['sampling_compact'][0]
    def voltage(n):return n.lower() if n in ports else 'xf.'+n.lower()
    records=[];pairs=[];indices={}
    for row in rows:
        if not row['model'].startswith(('nch_','pch_')):continue
        group=('bootstrap' if '.XBOOT' in row['instance'] else
               'reference_switch' if '.XCDAC.' in row['instance'] else
               'reference_driver' if '.XREF.XDRV' in row['instance'] else
               'comparator' if '.XCOMP.' in row['instance'] else 'clock_or_load')
        nodes=dict(zip('dgsb',map(voltage,row['nodes'])))
        for a,z in ['ds','gs','gd','gb','bd','bs']:
            pair=tuple(sorted([nodes[a],nodes[z]]))
            if pair not in indices:indices[pair]=len(pairs);pairs.append(pair)
            records.append(dict(instance=row['instance'],fixture_instance='XF.'+row['label'],
                model=row['model'],group=group,terminal=a+z,nodes=pair,
                pair_index=indices[pair],limit_v=.99 if row['model'] in ['nch_mac','pch_mac'] else 1.98))
    assert len(records)==237*6
    signals={key:voltage(value) for key,value in {
        'sample':'SAMPLE','sample_int':'XDUT__SAMPLE_INT',
        'sample_and':'XDUT__XIDLE__SAMPLE_AND','sample_match':'XDUT__SAMPLE_MATCH',
        'qual':'XDUT__XSEQ__QUAL','seq_sample':'XDUT__SEQ_SAMPLE',
        'top_p':'XDUT__TOPP','top_n':'XDUT__TOPN','vin_p':'VINP','vin_n':'VINN',
        'vin_p_source':'VINP_SRC','vin_n_source':'VINN_SRC','vref_p':'VREFP','vref_n':'VREFN',
        'vref_p_source':'VREFP_SRC','vref_n_source':'VREFN_SRC','vdd':'VDD!',
        'cmp_reset':'CMP_RESET'}.items()}
    # VIN*_SRC and VREF*_SRC are top-level bench nodes rather than DUT ports.
    for key in ['vin_p_source','vin_n_source','vref_p_source','vref_n_source']:
        signals[key]=signals[key].removeprefix('xf.')
    selected=set(signals.values());current_saves=set()
    for side in ['P','N']:
        for node in ['G','BTOP','BBOT','CTRL','GRESET','CLKSB']:
            signals['boot_'+side.lower()+'_'+node.lower()]='xf.xdut__xboot'+side.lower()+'__'+node.lower()
            selected.add(signals['boot_'+side.lower()+'_'+node.lower()])
        for bit in range(8):selected.add('xf.xdut__xcdac__b'+side.lower()+str(bit))
    for row in rows:
        if row['instance'].startswith(('XDUT.XBOOTP.','XDUT.XBOOTN.','XDUT.XCDAC.XS')):
            count=4 if row['model'].startswith(('nch_','pch_')) else 2
            current_saves.update('XF.'+row['label']+':'+str(i) for i in range(1,count+1))
    current_saves.update(n+':1' for n in ['VVDD','VREFHIGH','VREFLOW','VVINP','VVINN','VSAMPLE','VCMP_RESET',
                                            'RREFP','RREFN','CREFP','CREFN'])
    currents={n.lower() for n in current_saves}
    selected.update(currents)
    events=[signals[k] for k in ['sample','sample_int','sample_and','sample_match','qual','seq_sample','cmp_reset']]
    products=[('VDD','vdd!','vvdd:1'),('REFP','vrefp_src','vrefhigh:1'),
              ('REFN','vrefn_src','vreflow:1'),('INPUTP','vinp_src','vvinp:1'),
              ('INPUTN','vinn_src','vvinn:1'),('CLOCK','sample','vsample:1')]
    mapping=dict(records=records,pairs=pairs,stop_s=160e-9,signal_map=signals,
        measurements=dict(held_s=141.8e-9,preclose_offset_s=.2e-9,
            close_search_start_s=141e-9,open_search_start_s=101e-9,
            normal_duration_requires_actual_open=True,
            clock_evidence='all native half-VDD crossings, including absent crossings',
            analog_estimates='20ps compact interpolation, explicitly not exact native sample values'),
        energy_bins_s=[[0,100e-9],[100e-9,160e-9]])
    common={'fixture_dut.scs':(c.OUT/'fixture_dut.scs').read_bytes(),
        'stream.cpp':STREAM.read_bytes(),
        'mapping.json':(json.dumps(mapping,indent=2)+'\n').encode(),
        'pairs.txt':('\n'.join(' '.join(p) for p in pairs)+'\n').encode(),
        'selected.txt':('\n'.join(sorted(selected))+'\n').encode(),
        'events.txt':('\n'.join(events)+'\n').encode(),
        'products.txt':('\n'.join(' '.join(p) for p in products)+'\n').encode()}
    # The original compact decks already save Bootstrap terminal currents.
    # Add all exact branch names needed by selected.txt; this is measurement only.
    recipes=[];cases={}
    for suffix,original_name in [('short','short_low_history.scs'),('long','long_low_history.scs')]:
        deck=(c.OUT/original_name).read_text()+'\n// Measurement-only stream saves.\n'
        deck+='\n'.join('save '+name for name in sorted(current_saves))+'\n'
        cases[suffix]=deck.encode()
        inputs=[dict(source=(OUT/'common'/name).relative_to(b.ROOT).as_posix(),name=name)
                for name in common]
        inputs += [dict(source=(OUT/suffix/'test.scs').relative_to(b.ROOT).as_posix(),name='test.scs'),
                   dict(source=REMOTE.relative_to(b.ROOT).as_posix(),name='loaded_remote.py')]
        recipes.append(dict(schema_version=1,run_id='sar8audit-sample-v2-'+suffix,
            design_id='sar8_compact_sampling_history_v2',entry='test.scs',inputs=inputs,
            analyzer='loaded_remote.py',summary_signals=['XF.XDUT__SEQ_SAMPLE','XF.XDUT__TOPP','XF.XDUT__TOPN'],
            expected_stop_s=160e-9,qualification_scope='SS hot short-low/long-low diagnosis, not integrated timing equivalence',
            oa_parity='netlist_only',test_conditions=dict(corner='ss',vdd=.81,temperature_c=125,
                passives='tt',noise=False,mismatch=False,PEX=False,history=suffix,
                external_rise_start_ns=101,external_close_start_ns=141),
            resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,
                analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=8192,
                simulation_wall_seconds=1800,analysis_wall_seconds=1200,queue_timeout_seconds=7200)))
    maximum_points=math.ceil(160e-9/20e-12)+2
    bound=maximum_points*(len(selected)+1)*8
    assert bound+4*1024**2<32*1024**2
    package=dict(status='local_only_not_registered_or_run',
        reuse=dict(stream_source=STREAM.relative_to(b.ROOT).as_posix(),stream_sha256=b.sha(STREAM.read_bytes()),
            analyzer_source=REMOTE.relative_to(b.ROOT).as_posix(),analyzer_sha256=b.sha(REMOTE.read_bytes()),
            stream_byte_identical=True,analyzer_unmodified=True),
        MOS_count=237,terminal_pair_records=len(records),unique_node_pairs=len(pairs),
        selected_signals=len(selected),native_event_signals=len(events),
        native_energy_products=len(products),analysis_rss_limit_mib=256,collection_limit_mib=32,
        compact_binary_upper_bound_bytes=bound,collection_reserve_bytes=4*1024**2,
        energy_bin_note='100-160ns is a partial60ns bin; do not divide it by100ns',
        files={name:dict(sha256=b.sha(value),bytes=len(value)) for name,value in common.items()},
        cases={name:dict(sha256=b.sha(data),bytes=len(data)) for name,data in cases.items()},
        post_collection_review='review_stream.py uses native events and 20ps compact analog estimates; it never infers a missing opening',
        memory_claim='configured limits and structural one-native-point parser; new-run RSS not measured yet')
    return common,cases,recipes,package


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    common,cases,recipes,manifest=build_inputs()
    data={**{'common/'+n:v for n,v in common.items()},
          **{case+'/test.scs':v for case,v in cases.items()},
          'recipe_suggestions.json':(json.dumps(dict(register_only_after_parent_review=True,recipes=recipes),indent=2)+'\n').encode(),
          'package_manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
    for name,value in data.items():
        target=OUT/name
        if target.exists():assert target.read_bytes()==value,'existing package differs: '+name
        elif a.check:raise AssertionError('missing package: '+name)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
    print(json.dumps(dict(files=len(data),MOS=237,pairs=manifest['terminal_pair_records'],
        selected=manifest['selected_signals'],binary_bound_bytes=manifest['compact_binary_upper_bound_bytes'],remote=False)))


if __name__=='__main__':main()
