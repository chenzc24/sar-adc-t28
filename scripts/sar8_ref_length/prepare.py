"""Generate immutable DC probes and selected integrated PVT decks."""
import re
import sys
from control import ROOT,OUT,VERIFY,SOURCE,read,dump,sha,wf
DCNAMES=[f'dc_l{l}_ffhot_v2' for l in [30,60,90]]

def resized(dut,length):
    changes=[]
    def sub(match):
        old=match[0];new,n=re.subn(r'\bl=30n\b',f'l={length}n',old)
        assert n==2
        changes.append((old,new));return new
    new,n=re.subn(r'(?ms)^subckt sar8j_r1_sw_b[0-7] .*?^ends sar8j_r1_sw_b[0-7]',sub,dut)
    assert n==8
    inverse=new
    for old,changed in changes:inverse=inverse.replace(changed,old,1)
    assert inverse==dut
    return new

def writecase(name,text,ctx,source=SOURCE,dut=None):
    folder=OUT/name;assert not folder.exists();folder.mkdir()
    (folder/'test.scs').write_text(text)
    (folder/'r4_perf_monitor.va').write_bytes((source/'r4_perf_monitor.va').read_bytes())
    if dut is not None:(folder/'dut.scs').write_text(dut);ctx['DUT_sha256']=sha(folder/'dut.scs')
    ctx.update(name=name,deck_sha256=sha(folder/'test.scs'),OA_changed=False)
    dump(folder/'context.json',ctx);dump(VERIFY/(name+'_setup.json'),ctx)
    print('Prepared',name)

def dc():
    assert read(VERIFY/'preflight.json')['ok']
    legal=read(VERIFY/'legality.json')
    assert all(x['length_selection_pass'] for x in legal['devices'].values())
    data=read(ROOT/'verification/sar8_ref_load/branches_ffhot.json')
    original=(SOURCE/'dut.scs').read_text()
    assert sha(SOURCE/'dut.scs')==read(SOURCE/'context.json')['DUT_sha256']
    header=(ROOT/'netlist/sar8_physical/tt_nominal.scs').read_text().split('include "dut.scs"')[0]
    header=header.replace('ttmacro_mos_moscap','ffmacro_mos_moscap')
    for length,name in zip([30,60,90],DCNAMES):
        dut=resized(original,length)
        cell=re.search(r'(?ms)^subckt sar8j_r1_sw_b7 .*?^ends sar8j_r1_sw_b7',dut)[0]
        vp=data['reference_p_v'];vn=data['reference_n_v']
        text=header+'\n'+cell+'\nparameters DELTA=0\n'
        text+=f'VP (VP 0) vsource dc={vp:.16g}\nVN (VN 0) vsource dc={vn:.16g}\nVB (VB 0) vsource dc=0.99\n'
        saves=[]
        for side in ['P','N']:
            row=next(x for x in data['branches'] if x['side']==side and x['bit']==7)
            text+=f"VGN_{side} (GN_{side} 0) vsource dc={row['gn_v']:.16g}\nVGP_{side} (GP_{side} 0) vsource dc={row['gp_v']:.16g}\n"
            text+=f'Xoff{side} (BOT_{side} GN_{side} GP_{side} VB VN VP 0) sar8j_r1_sw_b7\n'
            saves += [f'BOT_{side}',f'Xoff{side}.MN_LOW:currents',f'Xoff{side}.MP_HIGH:currents']
        # Independent fully ON devices. Delta is signed external drain-source voltage.
        for tag,dev,ports,src in [('N','MN_LOW','DN VB VN 0',vn),('P','MP_HIGH','DP 0 VP VB',vp)]:
            lines=cell.splitlines();first=next(i for i,s in enumerate(lines) if s.strip().startswith(dev+' '))
            last=first
            while lines[last].rstrip().endswith('\\'):last+=1
            line='\n'.join(lines[first:last+1]).strip()
            assert 'spomb1=' in line and '\n' in line
            line=re.sub(dev+r' \([^)]*\)',f'MRon{tag} ({ports})',line, count=1)
            text+=line+'\n'+f'VD{tag} (D{tag} 0) vsource dc={src:.16g}+DELTA\n'
            saves += [f'D{tag}',f'MRon{tag}:currents']
        text+='opts options temp=125 tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13\n'
        text+='saveOptions options save=selected\ndc_iv dc param=DELTA start=-0.001 stop=0.001 step=0.001\n'
        text+='save '+' '.join(saves)+'\n'
        ctx=dict(length_nm=length,corner='ff',temperature_c=125,vdd=.99,
          spectre_args=['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],
          source_DUT_sha256=sha(SOURCE/'dut.scs'),fixed_reference_v=[vn,vp],
          fixed_W_nm={'N':150,'P':175},multi=384,nf=1,
          leakage='Exact b7 pair in each complementary state with measured hot gates; common bias across L.',
          Ron='Independent ON N/P, rail gate and original body, central slope over VDS=-1..+1mV. Bit7 multiplicity384; bit0 resistance=128*bit7.',
          geometry_policy=legal['geometry_policy'])
        writecase(name,text,ctx)

def integrated():
    selection=read(VERIFY/'selection.json');length=selection['selected_length_nm']
    assert length in [60,90]
    names=[]
    for point,corner,sup,temp in wf.prior.POINTS:
        source=ROOT/'output/sar8_main_width'/f'w2_{point}_static'
        old=(source/'dut.scs').read_text();dut=resized(old,length)
        ctx=read(source/'context.json');text=(source/'test.scs').read_text()
        assert sha(source/'test.scs')==ctx['deck_sha256'] and sha(source/'dut.scs')==ctx['DUT_sha256']
        assert text.count(old)==1;text=text.replace(old,dut,1)
        assert text.replace(dut,old,1)==(source/'test.scs').read_text()
        name=f'l{length}_{point}_static';names.append(name)
        ctx.update(length_nm=length,source_case=source.name,source_DUT_sha256=sha(source/'dut.scs'),
                   source_deck_sha256=sha(source/'test.scs'),inverse_DUT_and_deck_check=True)
        writecase(name,text,ctx,source,dut)
    dump(VERIFY/'integrated_setup.json',dict(names=names,selected_length_nm=length,concurrency=2,threads=4))

if __name__=='__main__':globals()[sys.argv[1]]()
