"""Generate tiny simulation-only CMI-limit probe; never changes PDK or launches."""
import argparse
import json
import re
import yaml
from prepare import ROOT,digest
from loaded import SEED


def main():
    run='sar8fix-ud12-limit-probe'
    folder=ROOT/'output/sar8_physical_repair'/run
    assert not folder.exists(),'Immutable probe already exists'
    cdf=json.loads((ROOT/'verification/sar8_physical_repair/io_cdf_audit.json').read_text())
    definitions=[]
    for name,nodes,pol in [('ND','HI LO 0 0','n'),('NS','HI 0 HI 0','n'),
                            ('PD','0 HH HI HI','p'),('PS','0 HI 0 HI','p')]:
        model=pol+'ch_18ud12_mac';params=dict(cdf[model]['parameters']);params['multi']=1
        for key in ['spmb','spmt']:
            if params[key]=='1.11111P':params[key]='1.11111e15'
        definitions.append(name+' ('+nodes+') '+model+' '+' '.join(k+'='+str(v) for k,v in params.items()))
    includes='\n'.join(x for x in (SEED/'test.scs').read_text().splitlines() if x.startswith('include "/home/process/'))
    includes=includes.replace('ffmacro_mos_moscap','ttmacro_mos_moscap')
    deck='// Isolated intentional overbias: read native CMI limits, never an ADC operating point.\n'
    deck+='simulator lang=spectre\nglobal 0\n'+includes+'\ninclude "dut.scs"\n'
    deck+='VHI (HI 0) vsource dc=2.2\nVLO (LO 0) vsource dc=-2.2\nVHH (HH 0) vsource dc=4.4\n'
    deck+='simulatorOptions options temp=27 tnom=27 reltol=1e-7 vabstol=1e-8 iabstol=1e-13\n'
    deck+='tran_probe tran stop=1p maxstep=100f errpreset=conservative\n'
    deck+='saveOptions options save=selected\nsave HI LO HH\n'
    folder.mkdir(parents=True)
    (folder/'test.scs').write_text(deck);(folder/'dut.scs').write_text('\n'.join(definitions)+'\n')
    recipe=dict(schema_version=1,run_id=run,design_id='isolated_ud12_native_limit_metadata',entry='test.scs',
        inputs=[dict(source=(folder/f).relative_to(ROOT).as_posix(),name=f) for f in ['test.scs','dut.scs']],
        expected_stop_s=1e-12,summary_signals=['HI','LO','HH'],oa_parity='none_metadata_probe',
        qualification_scope='Intentional isolated overbias for native warning thresholds; NOT an ADC test or operating recommendation',
        test_conditions=dict(corner='tt',temperature_c=27,family='18ud12',intentional_overbias=True),
        resources=dict(threads=1,simulation_rss_mib=512,simulation_virtual_mib=8192,
            analysis_rss_mib=128,analysis_virtual_mib=512,max_output_mib=32,
            simulation_wall_seconds=120,analysis_wall_seconds=120,queue_timeout_seconds=7200))
    (ROOT/'management/recipes'/(run+'.yaml')).write_text(yaml.safe_dump(recipe,sort_keys=False))
    manifest=dict(run_id=run,model_names=['nch_18ud12_mac','pch_18ud12_mac'],
        deliberate_overbias=True,ADC_changed=False,PDK_changed=False,
        files={f:digest(folder/f) for f in ['test.scs','dut.scs']})
    (ROOT/'verification/sar8_physical_repair'/(run+'_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


def recover():
    import time
    from loaded_flow import command
    from loaded_analyze import resolve
    run='sar8fix-ud12-limit-probe';last=None
    while True:
        s=command('run-status',run);key=(s['simulation']['status'],s['analysis']['status'])
        if key!=last:print(run,key,flush=True);last=key
        assert not any(x in ['failed','blocked','cancelled'] for x in key),s
        if key==('complete','not_started'):command('analyze',run,'--queue')
        if key==('complete','complete'):break
        time.sleep(30)
    command('collect',run);_,paths,receipt=resolve(run)
    log=paths['spectre.out'].read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    witnesses=[line.strip() for line in log.splitlines() if 'CMI-' in line and 'exceeded' in line]
    limits={p:{} for p in ['n','p']}
    for line in witnesses:
        m=re.search(r'\b([NP])[DS](?:\.\w+)*:\s+(V\w{2})\(.*?exceeded\s+v\w{2}_max\s*\(=\s*([\d.]+)\s*(m?V)',line)
        if m:
            pol,term,value,unit=m.groups();value=float(value)*(.001 if unit=='mV' else 1)
            existing=limits[pol.lower()].get(term)
            assert existing is None or existing==value
            limits[pol.lower()][term]=value
    result=dict(run_id=run,limits_v=limits,native_warning_witnesses=witnesses,
        all_six_pairs_both_polarities=set(limits['n'])==set(limits['p'])==set(['Vgs','Vgd','Vgb','Vds','Vbs','Vbd']),
        qualification='Native CMI screen thresholds only; no lifetime, DRC or operational ADC qualification',
        deliberate_simulation_only_overbias=True,collected_bytes=sum(x['bytes'] for x in receipt['files']),
        files_sha_verified=True)
    (ROOT/'verification/sar8_physical_repair'/('ud12_native_limits.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recover',action='store_true');a=p.parse_args()
    if a.recover:recover()
    else:main()
