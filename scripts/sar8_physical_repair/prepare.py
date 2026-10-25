"""Build immutable native-PDK candidates; never launch outside managed execution."""
import argparse, hashlib, json, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'output/sar8_stress_closure/rg1_strict200_ff_m40'
OUT = ROOT/'output/sar8_physical_repair'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def mapping(text):
    cells={m[1]:(m[2].split(),m[3]) for m in re.finditer(
        r'(?ms)^subckt (\w+) ([^\n]+)\n(.*?)^ends \1',text.replace('\\\n',' '))}
    devices={}
    def walk(master,path,bind):
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)',cells[master][1]):
            label,nodes,model,tail=m.groups();name=path+'.'+label
            ns=[bind.get(n,n if n in ['0','VDD!'] else path+'.'+n) for n in nodes.split()]
            if model in cells:
                assert len(ns)==len(cells[model][0]);walk(model,name,dict(zip(cells[model][0],ns)))
            else:devices[name]=dict(model=model,nodes=ns,parameters=tail)
    ports=cells['sar_adc8_join_r4'][0]
    walk('sar_adc8_join_r4','XDUT',dict(zip(ports,ports)))
    return devices

def prepare(tag, cap_units=1, resistor_factor=4):
    run='sar8fix-'+tag+'-ffcold';folder=OUT/run
    assert not folder.exists(), 'Immutable candidate already exists'
    folder.mkdir(parents=True)
    old=(BASE/'dut.scs').read_text();dut=old;changes=[]
    for bit in range(8):
        cell='sar8p_refdrv_b%d'%bit
        block=re.search(r'(?ms)^subckt '+cell+r' .*?^ends '+cell,dut)[0]
        new,n=re.subn(r'(rupolym l=17\.13u w=1u m=)(\d+)',
            lambda m:m[1]+str(int(m[2])*resistor_factor),block)
        assert n==40
        caps=['    CBUF%s (%s VSS) cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=%d mismatchflag=1'
              %(g,g,cap_units*2**bit) for g in ['GNN','GNP','GPN','GPP']]
        new=new.replace('ends '+cell,'\n'.join(caps)+'\nends '+cell)
        dut=dut.replace(block,new,1)
        changes.append(dict(cell=cell,resistor_parallel_factor=resistor_factor,
                            added_MOM_units_per_gate=cap_units*2**bit))
    original=mapping(old);devices=mapping(dut)
    assert all(devices[k]==v for k,v in original.items() if v['model']!='rupolym')
    mos={k:v for k,v in devices.items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']}
    assert len(mos)==1833
    pair_index={};pairs=[];records=[]
    for name,v in mos.items():
        group=('bootstrap' if '.XBOOT' in name else 'reference' if '.XCDAC.' in name else
               'comparator' if '.XCOMP.' in name else 'reference_driver' if '.XREF.XDRV' in name else 'digital_control')
        ns=dict(zip('dgsb',v['nodes']))
        for a,b in ['ds','gs','gd','gb','bd','bs']:
            p=tuple(sorted([ns[a].lower(),ns[b].lower()]))
            if p not in pair_index:pair_index[p]=len(pairs);pairs.append(p)
            records.append(dict(instance=name,group=group,terminal=a+b,nodes=p,
                pair_index=pair_index[p],limit_v=1.98 if '_18_' in v['model'] else .99))
    probe=json.loads((ROOT/'output/sar8_ref_current_probe/baseline_cold/manifest.json').read_text())
    selected=probe['voltages']
    # All MOS voltages participate in exact native-point stress screening.
    saves=set(selected)|{n for v in mos.values() for n in v['nodes'] if n!='0'}
    currents=[s for s in probe['currents'] if s.startswith(('XDUT.XCDAC.XSP7.','XDUT.XCDAC.XSN4.','RREF','CREF'))]
    saves.update(currents)
    deck=(BASE/'test.scs').read_text().replace(old,'include "dut.scs"\n',1)
    deck=re.sub(r'^save .*\n','',deck,flags=re.M)
    deck=deck.replace('saveOptions options save=selected','saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no')
    deck+='\n'+'\n'.join('save '+s for s in sorted(saves))+'\n'
    for source in ['VSAMPLE','VVDD','VREFHIGH','VREFLOW','RREFP','RREFN','CREFP','CREFN','VVINP','VVINN']:
        assert re.findall('(?m)^'+source+r' .*',deck)==re.findall('(?m)^'+source+r' .*',(BASE/'test.scs').read_text())
    (folder/'dut.scs').write_text(dut)
    (folder/'test.scs').write_text(deck)
    (folder/'r4_perf_monitor.va').write_bytes((BASE/'r4_perf_monitor.va').read_bytes())
    (folder/'selected.txt').write_text('\n'.join(s.lower() for s in selected+currents)+'\n')
    (folder/'pairs.txt').write_text('\n'.join(' '.join(p) for p in pairs)+'\n')
    (folder/'mapping.json').write_text(json.dumps(dict(records=records,pairs=pairs,changes=changes),indent=2))
    # Reuse the verified parser, changing ONLY plotting export density. Every native
    # sample still participates in extrema/stress. Compact export is not exact-waveform evidence.
    parser=(ROOT/'scripts/sar8_ref_current_probe/stream_psf.cpp').read_text()
    parser=parser.replace('bool have=false','double exported=-1;unsigned long long exported_points=0;bool have=false')
    before='binary.write(reinterpret_cast<char*>(&t),8);for(int i:selectidx){double v=val(i);binary.write(reinterpret_cast<char*>(&v),8);}'
    after='if(t-exported>=10e-12 || section=="END") {'+before+'exported=t;++exported_points;}'
    assert before in parser;parser=parser.replace(before,after)
    parser=parser.replace('<<points<<",\\\"last_time_s', '<<exported_points<<",\\\"native_points\\\":"<<points<<",\\\"last_time_s')
    assert 'native_points' in parser
    (folder/'stream.cpp').write_text(parser)
    manifest=dict(run_id=run,source_sha256=digest(BASE/'dut.scs'),dut_sha256=digest(folder/'dut.scs'),
        edits=changes,MOS_count=len(mos),MOS_pair_count=len(records),saved_count=len(saves),
        source_commit='de70f82',sample_sources_unchanged=True,OA_changed=False,
        added_MOM_units=4*255*cap_units,nominal_added_gate_cap_pf=4*255*cap_units*4.004/1000,
        unchanged_sources=['50 ohm input/reference','4 pF reference decap','40 ns sample','0.99 V core','0.9 V reference'])
    vf=ROOT/'verification/sar8_physical_repair';vf.mkdir(exist_ok=True)
    (vf/(run+'_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    inputs=[dict(source=(folder/f).relative_to(ROOT).as_posix(),name=f) for f in
            ['dut.scs','test.scs','r4_perf_monitor.va','selected.txt','pairs.txt','mapping.json','stream.cpp']]
    inputs.append(dict(source='scripts/sar8_physical_repair/remote_analyze.py',name='remote_analyze.py'))
    recipe=dict(schema_version=1,run_id=run,design_id='sar8_l90_mmain2_gate_charge_buffer_'+tag,
        entry='test.scs',inputs=inputs,analyzer='remote_analyze.py',summary_signals=['XDUT.GNN4','XDUT.XCDAC.BP7'],
        expected_stop_s=200e-9,qualification_scope='Native physical candidate, not adopted; full MOS screening; two static frames only',
        oa_parity='netlist_only_not_synchronized',test_conditions=dict(corner='ff',temperature_c=-40,vdd=.99,vrefp=.9,
        input_diff=[.81,-.81],Mmain_um=2,reference_L_nm=90,noise=False,mismatch=False,PEX=False),
        resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,
        analysis_virtual_mib=1024,max_output_mib=32768,simulation_wall_seconds=3600,
        analysis_wall_seconds=1800,queue_timeout_seconds=3600))
    target=ROOT/'management/recipes'/(run+'.yaml');target.write_text(yaml.safe_dump(recipe,sort_keys=False))
    print(json.dumps(manifest,indent=2));print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--cap-units',type=int,default=1)
    p.add_argument('--resistor-factor',type=int,default=4);a=p.parse_args()
    assert a.cap_units>0 and a.resistor_factor>0
    prepare(a.tag,a.cap_units,a.resistor_factor)
