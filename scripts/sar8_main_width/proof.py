"""Read-only source, native deck and measurement provenance verification."""
import re
import shlex
from width_flow import ROOT,OUT,VERIFY,OLD,REMOTE,base,read,dump,sha,design

def main():
    setup=read(VERIFY/'setup.json');names=setup['sweep']+setup.get('pvt',[])
    ssh=base.client();paths=[REMOTE+'/'+n+'/test.scs' for n in names]
    hashes=base.command(ssh,'sha256sum '+' '.join(shlex.quote(p) for p in paths))
    actual={s.split(None,1)[1].strip():s.split()[0] for s in hashes.splitlines()}
    rows=[]
    for name,path in zip(names,paths):
        folder=OUT/name;ctx=read(folder/'context.json');r=read(VERIFY/(name+'.json'))
        old,dut=design(ctx['total_main_width_um'])
        assert (folder/'dut.scs').read_text()==dut
        assert actual[path]==ctx['deck_sha256']==sha(folder/'test.scs')
        assert sha(folder/'dut.scs')==ctx['DUT_sha256']==r['DUT_sha256']
        text=(folder/'test.scs').read_text();original=(OLD/ctx['reference_case']/'test.scs').read_text()
        assert text.count(dut)==1
        restored=text.replace(dut,old,1)
        # Sweep differs additionally in the explicitly declared input PWL values only.
        def without_inputs(s):return re.sub(r'(?m)^VVIN[PN] \([^\n]+$', '', s)
        assert without_inputs(restored)==without_inputs(original)
        if name in setup.get('pvt',[]):assert restored==original
        else:
            assert ctx['input_diff_v']==[.81,-.81,.81,-.81,0,.123046875]
            sweep_control=(OUT/setup['sweep'][0]/'test.scs').read_text()
            assert re.findall(r'(?m)^VVIN[PN] \([^\n]+$',text)==re.findall(r'(?m)^VVIN[PN] \([^\n]+$',sweep_control)
        assert sha(folder/'r4_perf_monitor.va')==sha(OLD/ctx['reference_case']/'r4_perf_monitor.va')
        receipt=read(folder/'reduced_receipt.json')
        assert receipt['native_exit']==receipt['reduction_exit']==0
        assert receipt['compressed_sha256']==sha(folder/'reduced/reduced.json.gz')
        rows.append(dict(name=name,deck_sha256=actual[path],DUT_sha256=ctx['DUT_sha256'],
            reference_case=ctx['reference_case'],width_um=ctx['total_main_width_um'],
            kind=ctx['kind'],corner=ctx['corner'],vdd=ctx['vdd'],temperature_c=ctx['temperature_c'],
            input_diff_v=ctx.get('input_diff_v'),spectre_args=ctx['spectre_args'],stop_ns=ctx['stop_ns'],
            only_main_units_changed=True,external_timing_unchanged=True,
            original_stimulus_unchanged=name in setup.get('pvt',[]),native_exit=0,
            native_psf_sha256=r['native_psf_sha256'],native_psf_bytes=r['native_psf_bytes'],
            effective_settings=r['effective_settings'],frames=len(r['frames'])))
    local_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    assert local_bytes<2*1024**3
    readonly={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'netlist/sar8_physical/dut.scs',ROOT/'netlist/sar8_r4_idle/idle_cells.scs',ROOT/'config/design_spec.yaml']}
    previous=read(ROOT/'verification/sar8_pvt_mismatch/provenance.json')['untouched_readonly_dependencies']
    assert readonly==previous
    dump(VERIFY/'provenance.json',dict(cases=rows,local_bytes=local_bytes,
        model_evidence=read(VERIFY/'preflight.json')['dependencies_sha256'],
        read_only_sources=readonly,read_only_sources_unchanged=True,
        remote_raw_root=REMOTE,raw_waveforms_retained=True,OA_changed=False,PDK_changed=False))
    print('Provenance verified:',len(rows),'cases;',local_bytes,'local bytes')

if __name__=='__main__':main()
