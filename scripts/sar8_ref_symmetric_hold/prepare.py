"""Generate isolated null/hold decks and prove native devices/sources unchanged."""
import re
import importlib.util
import sys
from control import ROOT,OUT,VERIFY,read,dump,sha
HERE=ROOT/'scripts/sar8_ref_symmetric_hold'
VARIANTS={'null':0,'symmetric25':1/400}

def design(old,g):
    new=old;changes=[]
    for b in range(8):
        cell=f'sar8p_refdrv_b{b}'
        source=re.search(r'(?ms)^subckt '+cell+r' .*?^ends '+cell,old)[0]
        clone=source.replace(cell,f'sar8sym_refdrv_b{b}')
        clone=clone.replace('H L VDD VSS\n','H L VDD VSS PRESET SAMPLE\n',1)
        additions=[]
        for tag in ['GNN','GNP','GPN','GPP']:
            assert f'({tag}DRV {tag}B VSS VSS) nch_mac' in source
            additions.append(f'    ZH{tag} ({tag} VDD VSS {tag}B PRESET SAMPLE ENH_{tag} ENL_{tag}) ref_symmetric_diag conductance={g*2**b:.15g}')
        clone=clone.replace(f'ends sar8sym_refdrv_b{b}','\n'.join(additions)+f'\nends sar8sym_refdrv_b{b}')
        changes.append(clone)
    ref=re.search(r'(?ms)^subckt sar8i_refword .*?^ends sar8i_refword',old)[0]
    newref=ref
    for b in range(8):
        line=f'XDRV{b} (GNN{b} GNP{b} GPN{b} GPP{b} H{b} L{b} VDD VSS) sar8p_refdrv_b{b}'
        assert newref.count(line)==1
        newref=newref.replace(line,line.replace('VDD VSS)','VDD VSS PRESET SAMPLE)').replace('sar8p_','sar8sym_'))
    new=old.replace(ref,newref,1)
    assert new.replace(newref,ref,1)==old
    return new+'\n'+'\n'.join(changes)+'\n'

def main():
    assert read(VERIFY/'preflight.json')['ok']
    sys.path.insert(0,str(ROOT/'scripts/sar8_ff_overvoltage'))
    spec=importlib.util.spec_from_file_location('sym_mapping',ROOT/'scripts/sar8_ff_overvoltage/localize.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    names=[];audits=[]
    for corner in ['125','m40']:
        src=ROOT/'output/sar8_ref_length'/f'l90_ff_099_{corner}_static'
        ctx0=read(src/'context.json');old=(src/'dut.scs').read_text();deck=(src/'test.scs').read_text()
        assert sha(src/'dut.scs')==ctx0['DUT_sha256'] and sha(src/'test.scs')==ctx0['deck_sha256']
        for variant,g in VARIANTS.items():
            name=f'{variant}_ff_{corner}';dest=OUT/name;assert not dest.exists();dest.mkdir()
            dut=design(old,g);text=deck.replace(old,dut,1)
            assert text.replace(dut,old,1)==deck
            extra=[f'XDUT.XREF.XDRV{b}.{pin}_{tag}' for b in range(8) for tag in ['GNN','GNP','GPN','GPP'] for pin in ['ENH','ENL']]
            extra += [f'XDUT.XREF.XDRV{b}.{tag}B' for b in range(8) for tag in ['GNN','GNP','GPN','GPP']]
            extra=[x for x in extra if x not in ctx0['saved_signals']]
            text=text.replace('ahdl_include "r4_perf_monitor.va"','save '+' '.join(extra)+'\nahdl_include "r4_perf_monitor.va"')
            (dest/'dut.scs').write_text(dut);(dest/'test.scs').write_text(text)
            (dest/'r4_perf_monitor.va').write_bytes((src/'r4_perf_monitor.va').read_bytes()+b'\n'+(HERE/'diagnostic.va').read_bytes())
            mos=lambda txt:{k:v for k,v in mod.mapping(txt).items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']}
            assert mos(old)==mos(dut) and len(mos(dut))==1833
            for tag in ['VSAMPLE','VVDD','VVINP','VVINN','RREFP','RREFN','CREFP','CREFN','tran_perf']:
                assert re.findall(r'(?m)^'+tag+' .*',deck)==re.findall(r'(?m)^'+tag+' .*',text)
            ctx=dict(ctx0);ctx.update(name=name,source_case=src.name,variant=variant,hold_unit_conductance=g,
              source_DUT_sha256=ctx0['DUT_sha256'],source_deck_sha256=ctx0['deck_sha256'],
              DUT_sha256=sha(dest/'dut.scs'),deck_sha256=sha(dest/'test.scs'),monitor_sha256=sha(dest/'r4_perf_monitor.va'),
              helper_sha256=sha(HERE/'diagnostic.va'),saved_signals=ctx0['saved_signals']+extra,OA_changed=False,
              qualification='Ideal complementary finite conductance and settled-state detector on native ADC, not real keeper implementation')
            dump(dest/'context.json',ctx);dump(VERIFY/(name+'_setup.json'),ctx);names.append(name)
            audits.append(dict(name=name,native_MOS_identical=1833,source_timing_and_supplies_identical=True,inverse_check=True))
    dump(VERIFY/'setup.json',dict(names=names,concurrency=2,threads=4,variants=VARIANTS,source='e94e802 L90, prior diagnostic89e33e6'))
    dump(VERIFY/'source_validation.json',dict(status='PASS',cases=audits))
    print('Prepared/audited',names)

if __name__=='__main__':main()
