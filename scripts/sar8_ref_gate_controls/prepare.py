"""Immutable matched controls, no changes to native MOS dimensions or timing sources."""
import re
from control import ROOT,OUT,VERIFY,read,dump,sha
HERE=ROOT/'scripts/sar8_ref_gate_controls'
VARIANTS={'null':(0,0),'hold100':(1/1600,0),'hold25':(1/400,0),
          'slew100':(0,100),'slew300':(0,300)}

def design(old,g,r):
    source=re.search(r'(?ms)^subckt sar8p_refdrv_b7 .*?^ends sar8p_refdrv_b7',old)[0]
    clone=source.replace('sar8p_refdrv_b7','sar8diag_refdrv_b7')
    clone=clone.replace('H L VDD VSS\n','H L VDD VSS PRESET SAMPLE\n',1)
    helpers=[]
    for tag in ['GNN','GNP','GPN','GPP']:
        clone,n=re.subn(r'(R'+tag+r'0\s+\()'+tag+r'DRV ',r'\1'+tag+'SLOW ',clone);assert n==1
        helpers.append(f'    Z{tag} ({tag}DRV {tag}SLOW PRESET SAMPLE VSS EN_{tag}) ref_slew_diag extra_r={r:g}')
    clone=clone.replace('ends sar8diag_refdrv_b7','\n'.join(helpers)+'\nends sar8diag_refdrv_b7')
    ref=re.search(r'(?ms)^subckt sar8i_refword .*?^ends sar8i_refword',old)[0]
    newref=ref.replace('XDRV7 (GNN7 GNP7 GPN7 GPP7 H7 L7 VDD VSS) sar8p_refdrv_b7',
       'XDRV7 (GNN7 GNP7 GPN7 GPP7 H7 L7 VDD VSS PRESET SAMPLE) sar8diag_refdrv_b7')
    assert newref!=ref
    holds=[]
    for b in range(7):
        for tag,cmd in [('GNN','L'),('GPN','H')]:
            holds.append(f'    ZH{tag}{b} ({tag}{b} VDD PRESET SAMPLE RST{b} {cmd}{b} VSS EN_{tag}{b}) ref_hold_diag conductance={g*2**b:.15g}')
    newref=newref.replace('ends sar8i_refword','\n'.join(holds)+'\nends sar8i_refword')
    new=old.replace(ref,newref,1)+'\n'+clone+'\n'
    assert new[:-len('\n'+clone+'\n')].replace(newref,ref,1)==old
    return new

def main():
    assert read(VERIFY/'preflight.json')['ok']
    names=[]
    for corner in ['125','m40']:
        src=ROOT/'output/sar8_ref_length'/f'l90_ff_099_{corner}_static'
        ctx0=read(src/'context.json');old=(src/'dut.scs').read_text();deck=(src/'test.scs').read_text()
        assert sha(src/'dut.scs')==ctx0['DUT_sha256'] and sha(src/'test.scs')==ctx0['deck_sha256']
        for variant,(g,r) in VARIANTS.items():
            name=f'{variant}_ff_{corner}';dest=OUT/name;assert not dest.exists();dest.mkdir()
            dut=design(old,g,r);text=deck.replace(old,dut,1)
            assert text.replace(dut,old,1)==deck
            extra=[f'XDUT.XREF.EN_{tag}{b}' for b in range(7) for tag in ['GNN','GPN']]
            extra+=[f'XDUT.XREF.XDRV7.{tag}SLOW' for tag in ['GNN','GNP','GPN','GPP']]
            extra+=[f'XDUT.XREF.XDRV7.EN_{tag}' for tag in ['GNN','GNP','GPN','GPP']]
            text=text.replace('ahdl_include "r4_perf_monitor.va"','save '+' '.join(extra)+'\nahdl_include "r4_perf_monitor.va"')
            (dest/'dut.scs').write_text(dut);(dest/'test.scs').write_text(text)
            monitor=(src/'r4_perf_monitor.va').read_bytes();helper=(HERE/'diagnostic.va').read_bytes()
            (dest/'r4_perf_monitor.va').write_bytes(monitor+b'\n'+helper)
            ctx=dict(ctx0);ctx.update(name=name,source_case=src.name,variant=variant,hold_unit_conductance=g,
              bit4_hold_r_ohm=1/(g*16) if g else None,bit7_extra_r_ohm=r,
              source_DUT_sha256=ctx0['DUT_sha256'],source_deck_sha256=ctx0['deck_sha256'],
              DUT_sha256=sha(dest/'dut.scs'),deck_sha256=sha(dest/'test.scs'),
              monitor_sha256=sha(dest/'r4_perf_monitor.va'),helper_sha256=sha(HERE/'diagnostic.va'),
              saved_signals=ctx0['saved_signals']+extra,inverse_check=True,OA_changed=False,
              qualification='Ideal diagnostic hold/resistance controls on unchanged native transistor ADC; not a transistor keeper implementation')
            dump(dest/'context.json',ctx);dump(VERIFY/(name+'_setup.json'),ctx);names.append(name)
    dump(VERIFY/'setup.json',dict(names=names,concurrency=2,threads=4,variants=VARIANTS,
         source='e94e802 L90, analyzed in1fb4906',scope='FF cold/hot six static frames; no noise/mismatch/PEX/full-code/FFT'))
    print('Prepared',names)

if __name__=='__main__':main()
