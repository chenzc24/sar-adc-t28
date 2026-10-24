"""Native-only first screen: full MOS probes and lower reference-gate resistance."""
import importlib.util
import re
import sys
from control import ROOT, OUT, VERIFY, transport
read, dump, sha = transport.read, transport.dump, transport.sha
sys.path.insert(0, str(ROOT/'scripts/sar8_ff_overvoltage'))
spec=importlib.util.spec_from_file_location('closure_mapping', ROOT/'scripts/sar8_ff_overvoltage/localize.py')
mapping=importlib.util.module_from_spec(spec); spec.loader.exec_module(mapping)


def group(inst):
    if '.XBOOT' in inst:return 'bootstrap'
    if '.XCDAC.' in inst:return 'reference'
    if '.XCOMP.' in inst:return 'comparator'
    if '.XREF.XDRV' in inst:return 'reference_driver'
    return 'digital_control'


def manifest(ctx):
    keys=['name','stop_ns','frames','input_diff_v','spectre_args','DUT_sha256','deck_sha256',
          'monitor_sha256','source_DUT_sha256','rg_parallel_factor','edits','OA_changed','qualification']
    return dict({k:ctx[k] for k in keys},context_path='output/sar8_stress_closure/'+ctx['name']+'/context.json',
                context_sha256=sha(OUT/ctx['name']/'context.json'),MOS_count=len(ctx['stress_devices']),
                saved_signals_count=len(ctx['saved_signals']),current_signals=ctx['current_signals'])


def main():
    assert read(VERIFY/'preflight.json')['ok']
    names=[]
    # 200ns first screen contains two completed conversions and first idle reset.
    # Later600ns/PVT regressions remain required; no closure from this screen.
    for corner in ['m40', '125']:
        src=ROOT/'output/sar8_ref_length'/f'l90_ff_099_{corner}_static'
        ctx0=read(src/'context.json'); old=(src/'dut.scs').read_text()
        assert sha(src/'dut.scs')==ctx0['DUT_sha256']
        assert sha(src/'test.scs')==ctx0['deck_sha256']
        for factor in [1,4]:
            name=f'rg{factor}_strict200_ff_{corner}';dest=OUT/name
            assert not dest.exists(), name
            dut=old
            edits=[]
            if factor!=1:
                for bit in range(8):
                    cell=f'sar8p_refdrv_b{bit}'
                    block=re.search(r'(?ms)^subckt '+cell+r' .*?^ends '+cell,dut)[0]
                    # Parallel copies of existing PDK resistors; no geometry change.
                    new,n=re.subn(r'(rupolym l=17\.13u w=1u m=)(\d+)',
                                  lambda m:m[1]+str(int(m[2])*factor),block)
                    assert n==40,(cell,n)
                    dut=dut.replace(block,new,1);edits.append(dict(cell=cell,resistors=n,parallel_factor=factor))
            devices=mapping.mapping(dut)
            mos={k:v for k,v in devices.items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']}
            assert len(mos)==1833
            oldmos={k:v for k,v in mapping.mapping(old).items() if k in mos}
            assert oldmos==mos
            stress=[dict(instance=k,model=v['model'],nodes=dict(zip('dgsb',v['nodes'])),group=group(k),
                         limit_v=1.98 if '_18_' in v['model'] else .99) for k,v in mos.items()]
            saves=set(ctx0['saved_signals'])
            saves.update(n for v in mos.values() for n in v['nodes'] if n!='0')
            # Indexed wrapper terminal currents D/G/S/B, matching verified D G S B pins.
            currents=[f'XDUT.XCDAC.XS{s}{b}.{m}:{p}' for s in ['P','N'] for b in range(8)
                      for m in ['MN_LOW','MP_HIGH'] for p in [1,2,3,4]]
            currents+=['VREFHIGH:1','VREFLOW:1']
            saves.update(currents)
            # Case-insensitive duplicate saves can confuse parser equality checks.
            saves=sorted({s.lower() for s in saves})
            text=(src/'test.scs').read_text().replace(old,dut,1)
            text,n=re.subn(r'(?m)^tran_perf tran stop=600n', 'tran_perf tran stop=200n',text);assert n==1
            text,n=re.subn(r'(?m)^save .*$', 'save '+' '.join(saves),text);assert n==1
            assert 'ref_symmetric_diag' not in text
            for source in ['VSAMPLE','VVDD','VREFHIGH','VREFLOW','RREFP','RREFN','CREFP','CREFN']:
                assert re.findall(r'(?m)^'+source+r' .*',text)==re.findall(r'(?m)^'+source+r' .*',(src/'test.scs').read_text())
            dest.mkdir()
            (dest/'dut.scs').write_text(dut);(dest/'test.scs').write_text(text)
            (dest/'r4_perf_monitor.va').write_bytes((src/'r4_perf_monitor.va').read_bytes())
            ctx=dict(ctx0,name=name,stop_ns=200,frames=2,input_diff_v=ctx0['input_diff_v'][:2],
                     spectre_args=['+preset=cx','+mt=4','+lqtimeout','60','-preset_override'],
                     DUT_sha256=sha(dest/'dut.scs'),deck_sha256=sha(dest/'test.scs'),
                     monitor_sha256=sha(dest/'r4_perf_monitor.va'),stress_devices=stress,saved_signals=saves,
                     current_signals=currents,rg_parallel_factor=factor,source_DUT_sha256=ctx0['DUT_sha256'],
                     edits=edits,OA_changed=False,qualification='Unqualified native resistor-only candidate; no ideal helper')
            dump(dest/'context.json',ctx)
            dump(VERIFY/(name+'_setup.json'),manifest(ctx))
            names.append(name)
            print(name,len(stress),'MOS',len(saves),'signals')
    dump(VERIFY/'setup.json',dict(names=names,concurrency=2,threads=4,scope='Native full-inventory200ns initial screen, not closure'))


if __name__=='__main__':main()
