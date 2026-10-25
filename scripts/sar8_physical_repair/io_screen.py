"""Small native device-class screen. Generates frozen inputs; never launches SSH."""
import argparse
import json
import re
from pathlib import Path
import yaml
from prepare import ROOT, BASE, digest

CORNERS = {'tt': ('tt', .9, 27), 'sscold': ('ss', .81, -40),
           'sshot': ('ss', .81, 125), 'ffcold': ('ff', .99, -40), 'ffhot': ('ff', .99, 125)}
MOM = 'cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 mismatchflag=1'

def build(corner, hybrid=False, long_window=False, native=False):
    assert not (hybrid and native), 'Choose one physical candidate family'
    process, supply, temp = CORNERS[corner]
    assert not long_window or hybrid or native
    run = 'sar8fix-'+('natlong' if native and long_window else 'natscreen' if native else 'hyblong' if long_window else 'hybscreen' if hybrid else 'ioscreen')+'-'+corner
    stop=50e-9 if long_window else 20e-9
    folder = ROOT/'output/sar8_physical_repair'/run
    folder.mkdir(exist_ok=False)
    cdf = json.loads((ROOT/'verification/sar8_physical_repair/io_cdf_audit.json').read_text())
    if native:cdf.update(json.loads((ROOT/'verification/sar8_physical_repair/native_cdf_audit.json').read_text()))
    source = (BASE/'dut.scs').read_text().replace('\\\n', ' ')
    def block(name):
        return re.search(r'(?ms)^subckt '+name+r' .*?\n(.*?)^ends '+name, source)[1]
    def devices(name):
        return list(re.findall(r'(?m)^\s*(\w+) \(([^)]*)\) (\w+)([^\n]*)', block(name)))
    templates = {m: p for _, _, m, p in devices('sar8p_inv')}
    refs = {m: p for _, _, m, p in devices('sar8j_r1_sw_b7')}
    lines, records, saves, selected = [], [], set(), set()
    def mos(name, nodes, family, pol, multi=1, original=None):
        model = pol+'ch_mac' if family == 'core' else pol+'ch_'+family+'_mac'
        if family == 'core':
            params = original or templates[model]
            params = re.sub(r'\bmulti=\S+', 'multi='+str(multi), params)
        else:
            pars = dict(cdf[model]['parameters'])
            # Spectre P (peta) rewritten explicitly to avoid unit-case ambiguity.
            for k in ['spmb', 'spmt']:
                if pars[k] == '1.11111P': pars[k] = '1.11111e15'
            pars['multi'] = multi
            params = ' '.join(k+'='+str(v) for k,v in pars.items())
        lines.append(name+' ('+nodes+') '+model+' '+params)
        ns = nodes.split(); assert len(ns) == 4
        saves.update(n for n in ns if n != '0')
        # UD12 limit is deliberately NOT inferred from its name. Retain measurements
        # but require independent native-model limit audit before qualification.
        records.append(dict(instance=name, model=model, nodes=ns,
                            limit_v=.99 if family=='core' else 1.98 if family in ['18','na18'] else None))
    def inv(name, a, out, family):
        mos(name+'N', out+' '+a+' 0 0', family, 'n', 1 if family=='core' else 2)
        mos(name+'P', out+' '+a+' VDD VDD', family, 'p', 1 if family=='core' else 4)
    families=['core','N1','N4','N16'] if native else ['core','18h2','18h4','18h8'] if hybrid else ['core','18','18ud12']
    for label in families:
        family='18' if 'h' in label or label.startswith('N') else label
        tag = 'F'+label
        inv(tag+'I', 'CLK', tag+'Y', family)
        selected.add(tag+'Y')
        for j in range(4): inv(tag+'L'+str(j), tag+'Y', tag+'L'+str(j)+'Y', family)
        # Full StrongARM topology retained; only device class/default geometry changes.
        for sign in [1,-1]:
            prefix=tag+('CP' if sign==1 else 'CN')
            binding=dict(CLK='CLK',OUTN=prefix+'ON',OUTP=prefix+'OP',VDD='VDD',VSS='0',
                         VINP='VIP' if sign==1 else 'VIN',VINN='VIN' if sign==1 else 'VIP')
            for name, nodes, model, params in devices('sar_strongarm_t28'):
                multi=1
                if family!='core':
                    width=re.search(r'\bw=(\S+)',params)[1]
                    multi={'500n':2,'1u':4}[width]
                device_family=family
                if label.startswith('N') and name in ['MNINP','MNINN','MNLATP','MNLATN']:
                    device_family='na18'
                    multi=(2 if name.startswith('MNIN') else 1)*int(label[1:])
                if 'h' in label and name in ['MNINP','MNINN']:
                    device_family='core';multi=1
                    ns=nodes.split();ns[0]='I'+ns[0];nodes=' '.join(ns)
                mos(prefix+name, ' '.join(binding.get(n,prefix+n) for n in nodes.split()),
                    device_family,model[0],multi,params)
            if 'h' in label:
                for node in ['X','Y']:
                    mos(prefix+'CAS'+node,prefix+node+' VDD '+prefix+'I'+node+' 0',
                        '18','n',int(label[-1]))
            for term in ['ON','OP']:
                lines.append('C'+prefix+term+' ('+prefix+term+' 0) '+MOM+' multi=2')
                selected.add(prefix+term)
        for scale in ([] if hybrid or native else [1] if family=='core' else [1,2,4]):
            p=tag+'S'+str(scale)
            lines.extend([
                'V'+p+'R ('+p+'RS 0) vsource dc=.9',
                'R'+p+'R ('+p+'RS '+p+'RP) resistor r=50',
                'C'+p+'R ('+p+'RP 0) capacitor c=4p',
                'C'+p+'B ('+p+'B 0) '+MOM+' multi=128'])
            for pol, nodes in [('n',p+'B CLK 0 0'),('p',p+'B CLK '+p+'RP VDD')]:
                mos(p+pol,nodes,family,pol,384 if family=='core' else 128*scale,
                    refs[pol+'ch_mac'])
                # Independent linear-region DC fixtures: 10 mV drain/source drop.
                for state in ['on','off']:
                    q=p+pol+state
                    drain=.01 if pol=='n' else .89
                    lines.append('V'+q+'D ('+q+'D 0) vsource dc='+str(drain))
                    lines.append('V'+q+'S ('+q+'S 0) vsource dc='+('0' if pol=='n' else '.9'))
                    gate=('VDD' if pol=='n' else '0') if state=='on' else ('0' if pol=='n' else 'VDD')
                    mos(q,q+'D '+gate+' '+q+'S '+('0' if pol=='n' else 'VDD'),family,pol,
                        384 if family=='core' else 128*scale,refs[pol+'ch_mac'])
                    saves.add(q+':1'); selected.add(q+':1')
            selected.update([p+'B',p+'RP'])
    stimulus = ['VVDD (VDD 0) vsource dc='+str(supply),
        'VCLK (CLK 0) vsource type=pulse val0=0 val1='+str(supply)+' delay=2n rise=100p fall=100p width=1.9n period=4n',
        'VIP (VIP 0) vsource dc=0.45087890625', 'VIN (VIN 0) vsource dc=0.44912109375']
    if long_window: stimulus[1]=stimulus[1].replace('width=1.9n period=4n','width=5.9n period=10n')
    selected.update(['VDD','CLK','VIP','VIN']); saves.update(selected)
    pairs=[]; index={}; expanded=[]
    for d in records:
        ns=dict(zip('dgsb',d['nodes']))
        for a,b in ['ds','gs','gd','gb','bd','bs']:
            key=tuple(sorted([ns[a].lower(),ns[b].lower()]))
            if key not in index: index[key]=len(pairs);pairs.append(key)
            expanded.append(dict(d,terminal=a+b,pair_index=index[key]))
    includes='\n'.join(l for l in (BASE/'test.scs').read_text().splitlines() if l.startswith('include '))
    includes=includes.replace('ffmacro_mos_moscap',process+'macro_mos_moscap')
    deck='// Native block feasibility bench; ideal excitation, NOT integrated ADC.\nsimulator lang=spectre\nglobal 0\n'+includes+'\ninclude "dut.scs"\n'
    deck+='\n'.join(stimulus)+'\n'
    deck+='simulatorOptions options temp='+str(temp)+' tnom=27 reltol=1e-7 vabstol=1e-8 iabstol=1e-13 method=gear2only\n'
    deck+='tran_screen tran stop='+str(stop)+' maxstep=5p errpreset=conservative\nsaveOptions options save=selected currents=selected subcktiprobes=no useprobes=no\n'
    deck+='\n'.join('save '+s for s in sorted(saves))+'\n'
    files={'dut.scs':'\n'.join(lines)+'\n','test.scs':deck,
           'selected.txt':'\n'.join(s.lower() for s in sorted(selected))+'\n',
           'pairs.txt':'\n'.join(' '.join(p) for p in pairs)+'\n',
           'mapping.json':json.dumps(dict(records=expanded,stop_s=stop),indent=2)}
    for name, content in files.items(): (folder/name).write_text(content)
    (folder/'stream.cpp').write_bytes((ROOT/'scripts/sar8_ref_current_probe/stream_psf.cpp').read_bytes())
    inputs=[dict(source=(folder/name).relative_to(ROOT).as_posix(),name=name) for name in list(files)+['stream.cpp']]
    inputs.append(dict(source='scripts/sar8_physical_repair/io_remote.py',name='io_remote.py'))
    recipe=dict(schema_version=1,run_id=run,design_id='native_low_voltage_IO_feasibility',entry='test.scs',inputs=inputs,
        analyzer='io_remote.py',expected_stop_s=stop,summary_signals=['CLK']+['F'+f+'Y' for f in families],
        qualification_scope='Block screen only: ideal clocks/input/reference sources; no ADC qualification',
        oa_parity='netlist_only',test_conditions=dict(corner=process,vdd=supply,temperature_c=temp),
        resources=dict(threads=4,simulation_rss_mib=512,simulation_virtual_mib=8192,
        analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=1024,
        simulation_wall_seconds=300,analysis_wall_seconds=180,queue_timeout_seconds=3600))
    (ROOT/'management/recipes'/(run+'.yaml')).write_text(yaml.safe_dump(recipe,sort_keys=False))
    manifest=dict(run_id=run,source_sha256=digest(BASE/'dut.scs'),MOS_count=len(records),MOS_pairs=len(expanded),
        files={name:digest(folder/name) for name in files},supply=supply,corner=process,temp_c=temp,families=families,
        hybrid=hybrid,long_window=long_window,native=native,stop_s=stop,
        note='Core baseline vs legal CDF-default IO geometry; UD12 stress limit not yet certified; unchanged external supply contract.')
    (ROOT/'verification/sar8_physical_repair'/(run+'_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corner',choices=CORNERS);p.add_argument('--hybrid',action='store_true');p.add_argument('--long-window',action='store_true');p.add_argument('--native',action='store_true')
    a=p.parse_args();build(a.corner,a.hybrid,a.long_window,a.native)
