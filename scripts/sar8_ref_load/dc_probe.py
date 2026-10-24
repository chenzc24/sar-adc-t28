"""Exact bit7 switch pair, measured hot biases versus ideal OFF gates; not an ADC fix."""
import contextlib
import re
from control import ROOT,OUT,VERIFY,SOURCE,read,dump,sha,wf
DCNAMES=['pair_ffhot','pair_ffcold_fixedbias']

def prepare():
    data=read(VERIFY/'branches_ffhot.json')
    dut=(SOURCE/'dut.scs').read_text()
    cell=re.search(r'(?ms)^subckt sar8j_r1_sw_b7 .*?^ends sar8j_r1_sw_b7',dut)[0]
    header=(ROOT/'netlist/sar8_physical/tt_nominal.scs').read_text().split('include "dut.scs"')[0]
    header=header.replace('ttmacro_mos_moscap','ffmacro_mos_moscap')
    for name,temp in zip(DCNAMES,[125,-40]):
        folder=OUT/name;assert not folder.exists();folder.mkdir()
        text=header+'\n'+cell+'\nparameters DELTA=0\n'
        text+=f"VP (VP 0) vsource dc={data['reference_p_v']:.16g}\nVN (VN 0) vsource dc={data['reference_n_v']:.16g}\nVB (VB 0) vsource dc=0.99\n"
        saves=[];biases={}
        for side in ['P','N']:
            row=next(x for x in data['branches'] if x['side']==side and x['bit']==7)
            assert row['off_device'] in ['MN_LOW','MP_HIGH']
            for mode in ['actual','ideal']:
                label=mode+'_'+side;gn=row['gn_v'];gp=row['gp_v']
                if mode=='ideal':
                    if row['off_device']=='MN_LOW':gn=0.
                    else:gp=.99
                ng=f'{gn:.16g}'+('+DELTA' if row['off_device']=='MN_LOW' else '')
                pg=f'{gp:.16g}'+('-DELTA' if row['off_device']=='MP_HIGH' else '')
                text+=f'VGN_{label} (GN_{label} 0) vsource dc={ng}\nVGP_{label} (GP_{label} 0) vsource dc={pg}\n'
                text+=f'X{label} (BOT_{label} GN_{label} GP_{label} VB VN VP 0) sar8j_r1_sw_b7\n'
                saves += [f'BOT_{label}',f'GN_{label}',f'GP_{label}']
                saves += [f'X{label}.{dev}:currents' for dev in ['MN_LOW','MP_HIGH']]
                biases[label]=dict(source_integrated=row,off_gate_policy=mode)
        text+=f'opts options temp={temp} tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13\nsaveOptions options save=selected\n'
        text+='dc_leak dc param=DELTA start=-0.05 stop=0.05 step=0.005\nsave '+' '.join(saves)+'\n'
        (folder/'test.scs').write_text(text)
        (folder/'r4_perf_monitor.va').write_bytes((SOURCE/'r4_perf_monitor.va').read_bytes())
        ctx=dict(name=name,temperature_c=temp,corner='ff',vdd=.99,
            deck_sha256=sha(folder/'test.scs'),spectre_args=['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],
            source_DUT_sha256=read(SOURCE/'context.json')['DUT_sha256'],
            fixed_reference_v=[data['reference_n_v'],data['reference_p_v']],biases=biases,
            scope='Exact isolated bit7 pair; both temperatures use SAME measured hot reference/gate biases. Delta0 actual/ideal OFF-gate comparison. Delta>0 weakens OFF bias. Diagnostic only, not a negative-gate design.',
            OA_changed=False,ADC_changed=False)
        dump(folder/'context.json',ctx);dump(VERIFY/(name+'_setup.json'),ctx)

def prepare_op():
    source=OUT/'pair_ffhot';folder=OUT/'pair_ffhot_op'
    assert not folder.exists();folder.mkdir()
    text=(source/'test.scs').read_text()
    old='dc_leak dc param=DELTA start=-0.05 stop=0.05 step=0.005'
    assert text.count(old)==1
    text=text.replace(old,'dc_oper dc\ndc_info info what=oppoint where=rawfile')
    (folder/'test.scs').write_text(text)
    (folder/'r4_perf_monitor.va').write_bytes((source/'r4_perf_monitor.va').read_bytes())
    ctx=read(source/'context.json');ctx.update(name='pair_ffhot_op',deck_sha256=sha(folder/'test.scs'),
        scope='Same measured-bias pair at DELTA=0; native internal operating-point evidence only')
    dump(folder/'context.json',ctx);dump(VERIFY/'pair_ffhot_op_setup.json',ctx)

if __name__=='__main__':
    import sys
    prepare_op() if sys.argv[1:]==['op'] else prepare()
