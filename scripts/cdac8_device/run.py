"""Spectre experiments; primary runs consume exact saved-OA exports."""
from __future__ import annotations
import argparse
import re
from common import ROOT,OUT,stage,batch,dump,sha

def oa(cell,tag="initial"):
    source=OUT/"oa_netlists"/cell/tag/"input.scs"
    text=source.read_text()
    text=text.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5").replace("vabstol=1e-6","vabstol=1e-7").replace("iabstol=1e-12","iabstol=1e-13")
    return text

def variables(text,values):
    m=re.search(r"(?m)^parameters ((?:[^\n]*\\\n)*[^\n]*)\n",text)
    names=m[1].replace("\\\n"," ").split() if m else []
    assert m and set(names)==set(values),(names,values)
    return text[:m.start()]+"parameters "+" ".join(f"{n}={values[n]:.14g}" for n in names)+"\n"+text[m.end():]

def parameter_names(text):
    m=re.search(r"(?m)^parameters ((?:[^\n]*\\\n)*[^\n]*)\n",text)
    assert m
    return m[1].replace("\\\n"," ").split()

def transient(cell,name,*,override=None,stop=1.1e-6,strobe=False,maxstep="100p",tag="initial",corner="tt",temperature=27,accuracy="conservative"):
    text=oa(cell,tag)
    params={"CKB":.05e-15,"DEAD_TIME":100e-12,"OPEN_LOOP":0,"FIXED_CODE":-1,"STIM_MODE":0,
        "VDIFF":.453515625,"FIN":10e6*461/1024,"RREF":50,"SUP":.9,"CDECAP":4e-12,
        "MULT_R":1,"MULT_S":1,"MULT_D":1,**(override or {})}
    values={n:params[n] for n in parameter_names(text)}
    text=variables(text,values)
    text=text.replace("section=ttmacro_mos_moscap",f"section={corner}macro_mos_moscap").replace("temp=27",f"temp={temperature}")
    if cell!="tb_cdac8_sar":text+="\nmodel macro_clamp diode is=1e-6 n=1 rs=5\n"
    analysis=f"tran tran stop={stop:.14g} maxstep={maxstep} errpreset={accuracy}"
    if strobe:analysis+=" strobeperiod=100n strobedelay=90n strobeoutput=strobeonly"
    saved=["TOPP","TOPN","VINP","VINN","VINP_SRC","VINN_SRC","PHI","DAC_SAMPLE","BASE","BUSY","VALID","CMP_CLK","COMP_P","COMP_N","VREFP","VREFN"]
    saved += [f"DOUT\\<{b}\\>" for b in range(8)]
    if not strobe:
        saved += [f"SEL{q}\\<{b}\\>" for q in (0,1) for b in range(8)]
        saved += ["VVDD:p","VREFHIGH:p","VREFLOW:p","VVCM:p"]
        if cell!="tb_cdac8_device":
            if cell!='tb_cdac8_ideal_input':saved += ["XBOOTP.G","XBOOTN.G"]
            saved += ["XCDAC.XSP7.EH_B","XCDAC.XSP7.ES_B","XCDAC.BP7","XCDAC.BN7"]
            saved += [f'XCDAC.B{s}{b}' for s in 'PN' for b in range(9) if b!=7]
            saved += [f'XCDAC.XS{s}5.{n}' for s in 'PN' for n in ('ES_B','EL_D','EH_B')]
    text+="\n"+analysis+"\nsave "+" ".join(saved)+"\n"
    dump(f"transient/{name}_case.json",{"cell":cell,"oa_tag":tag,"parameters":values,"stop_s":stop,
        "corner":corner,"temperature_c":temperature,"strobe":strobe,"accuracy":accuracy,"oa_sha256":sha(OUT/"oa_netlists"/cell/tag/"input.scs"),
        "owned_va_sha256":{p.name:sha(p) for p in (ROOT/"models/veriloga").glob("cdac8_*.va")}})
    return stage(name,text)

def smoke(tag="initial"):
    suffix="" if tag=="initial" else "_"+tag
    paths=[transient("tb_cdac8_device","caps_smoke"+suffix,override={"OPEN_LOOP":1,"VDIFF":0},tag=tag),
        transient("tb_cdac8_sampling","device_smoke"+suffix,override={"OPEN_LOOP":1,"FIXED_CODE":128,"STIM_MODE":3,"VDIFF":.8},tag=tag),
        transient("tb_cdac8_sar","sar_smoke"+suffix,tag=tag)]
    batch(paths,"transient",workers=3)

def aps_probe(tag):
    p=transient("tb_cdac8_sar","sar_aps_probe",stop=600e-9,tag=tag)
    batch([p],"transient",workers=1,timeout=240,mode="aps",extra_args=("+lqtimeout","5"))

def balanced_smoke():
    paths=[]
    for cell,name,over in (
        ("tb_cdac8_sampling","balanced_literal",{"OPEN_LOOP":1,"FIXED_CODE":128,"STIM_MODE":3,"VDIFF":.8}),
        ("tb_cdac8_nominal","balanced_nominal",{"OPEN_LOOP":1,"FIXED_CODE":128,"STIM_MODE":3,"VDIFF":.8}),
        ("tb_cdac8_nominal_sar","balanced_comparator",{})):
        paths.append(transient(cell,name,override=over,stop=600e-9,tag="balanced"))
    batch(paths,"transient",workers=3,mode="aps",extra_args=("+lqtimeout","5"))

def safephase_smoke():
    paths=[transient('tb_cdac8_safephase','safephase_step',tag='initial',stop=600e-9,
                    override={'OPEN_LOOP':1,'FIXED_CODE':128,'STIM_MODE':3,'VDIFF':.8}),
           transient('tb_cdac8_safephase','safephase_loop',tag='initial',stop=600e-9)]
    batch(paths,'transient',workers=2,mode='aps',extra_args=('+lqtimeout','5'))

def softreset_smoke():
    paths=[transient('tb_cdac8_nominal','softreset_step',tag='softreset',stop=600e-9,
                    override={'OPEN_LOOP':1,'FIXED_CODE':128,'STIM_MODE':3,'VDIFF':.8}),
           transient('tb_cdac8_nominal','softreset_loop',tag='softreset',stop=600e-9),
           transient('tb_cdac8_nominal_sar','softreset_comparator',tag='softreset',stop=600e-9)]
    batch(paths,'transient',workers=3,mode='aps',extra_args=('+lqtimeout','5'))

def sweep_system(kind):
    over={"static":{"STIM_MODE":1},"dynamic":{"STIM_MODE":2},"dac":{"OPEN_LOOP":1,"VDIFF":0}}[kind]
    stop={"static":26.02e-6,"dac":26.02e-6,"dynamic":103.22e-6}[kind]
    p=transient("tb_cdac8_nominal","final_"+kind,override=over,stop=stop,strobe=True,tag="balanced",accuracy="moderate",maxstep="250p")
    batch([p],"transient",workers=1,mode="aps",extra_args=("+lqtimeout","5"))

def switch_screen(tag="initial"):
    paths=[]
    for corner in ("tt","ss","ff"):
        for sup in (.81,.9,.99):
            for temp in (-40,27,125):
                params={"SUP":sup,"VPROBE":.45,"MULT_R":1,"MULT_S":1,"MULT_D":1}
                text=variables(oa("tb_cdac8_switch_char",tag),params)
                text=text.replace("section=ttmacro_mos_moscap",f"section={corner}macro_mos_moscap").replace("temp=27",f"temp={temp}")
                text+="\ndc_leak dc param=VPROBE start=0 stop=SUP step=SUP/8\nsave "+" ".join(f"VPROBE{x}{mode}:p" for x in "HLS" for mode in ("ON","OFF"))+"\n"
                name=f"switch_{corner}_{round(sup*1000)}_{temp}"+("" if tag=="initial" else "_"+tag)
                dump(f"switches/{name}_case.json",{"corner":corner,"supply_v":sup,"temperature_c":temp,"parameters":params})
                paths.append(stage(name,text))
    batch(paths,"switches",workers=3)

def ref18_screen():
    paths=[]
    for corner,sup,temp in [('tt',.9,27),('ss',.81,-40),('ff',.99,125)]:
        text=variables(oa('tb_cdac8_ref18_char'),{'SUP':sup,'VPROBE':.45,'MULT_R':1,'MULT_S':1,'MULT_D':1})
        text=text.replace('section=ttmacro_mos_moscap',f'section={corner}macro_mos_moscap').replace('temp=27',f'temp={temp}')
        text+='\ndc_leak dc param=VPROBE start=0 stop=SUP step=SUP/8\nsave '+' '.join(f'VPROBE{x}{mode}:p' for x in 'HLS' for mode in ('ON','OFF'))+'\n'
        paths.append(stage(f'ref18_{corner}_{round(sup*1000)}_{temp}',text))
    batch(paths,'ref18',workers=3)

def pvt():
    paths=[]
    settings=[('tt',.9,27,v) for v in (-.8,-.4,0,.4,.8)]
    settings += [(c,s,t,.8) for c in ('ss','ff') for s in (.81,.99) for t in (-40,125)]
    for corner,sup,temp,vin in settings:
        name=f'pvt_{corner}_{round(sup*1000)}_{temp}_{round(vin*1000)}'
        paths.append(transient('tb_cdac8_nominal',name,tag='balanced',stop=600e-9,corner=corner,temperature=temp,
            override={'OPEN_LOOP':1,'FIXED_CODE':128,'STIM_MODE':3,'VDIFF':vin,'SUP':sup}))
    paths.append(transient('tb_cdac8_nominal','precision_loop_conservative',tag='balanced',stop=600e-9))
    paths.append(transient('tb_cdac8_nominal','precision_loop_moderate',tag='balanced',stop=600e-9,accuracy='moderate',maxstep='250p'))
    batch(paths,'transient',workers=3,mode='aps',extra_args=('+lqtimeout','5'))

def stress_trace():
    p=transient('tb_cdac8_nominal','stress_trace',tag='balanced',stop=600e-9)
    batch([p],'transient',workers=1,mode='aps',extra_args=('+lqtimeout','5'))

def cm_scale():
    # Declared instance multiplier sensitivity only. Fractional effective leaf
    # multipliers are not layout-realized sizes and are never promoted directly.
    paths=[transient('tb_cdac8_nominal',f'cm_scale_{round(m*1000)}',tag='balanced',stop=600e-9,
                     override={'MULT_S':m}) for m in (.5,.25,.125)]
    batch(paths,'transient',workers=3,mode='aps',extra_args=('+lqtimeout','5'))

def baseline_completeness():
    paths=[transient('tb_cdac8_device','ideal_dac',tag='prep',stop=26.02e-6,strobe=True,
                     override={'OPEN_LOOP':1,'VDIFF':0},accuracy='moderate',maxstep='250p'),
           transient('tb_cdac8_sampling','literal_loop',tag='balanced',stop=600e-9)]
    batch(paths,'transient',workers=2,mode='aps',extra_args=('+lqtimeout','5'))

def ideal_input():
    p=transient('tb_cdac8_ideal_input','ideal_input_ss',stop=600e-9,corner='ss',temperature=-40,
                override={'OPEN_LOOP':1,'FIXED_CODE':128,'STIM_MODE':3,'VDIFF':.8,'SUP':.81})
    batch([p],'transient',workers=1,mode='aps',extra_args=('+lqtimeout','5'))

def acceleration_probe():
    # batch captures process-global streams; use separate sequential captures,
    # not nested redirect_stdout contexts in independent Python threads.
    for mode in ('ax','aps'):
        path=transient('tb_cdac8_nominal','sine_probe_'+mode,stop=600e-9,tag='balanced',
            override={'STIM_MODE':2},accuracy='moderate',maxstep='250p')
        args=('+lqtimeout','5')+(('+mt=4',) if mode=='ax' else ())
        batch([path],'transient',workers=1,mode=mode,timeout=300,extra_args=args)

def accelerated_full():
    paths=[transient('tb_cdac8_nominal','final_dynamic_ax',tag='balanced',stop=103.22e-6,strobe=True,
                     override={'STIM_MODE':2},accuracy='moderate',maxstep='250p'),
           transient('tb_cdac8_nominal','dac_ax',tag='balanced',stop=26.02e-6,strobe=True,
                     override={'OPEN_LOOP':1,'VDIFF':0},accuracy='moderate',maxstep='250p')]
    batch(paths,'transient',workers=2,mode='ax',timeout=7200,extra_args=('+mt=4','+lqtimeout','5'))

def unit_ac(mc=0,tag="initial"):
    cell="tb_cdac8_unit_char"
    text=oa(cell,tag)
    saves=" ".join("VSRC"+k+str(i)+":p" for k in "abc" for i in range(3))
    if mc:
        analysis=(f"mc_cap montecarlo numruns={mc} seed=9031 variations=mismatch sampling=standard donominal=no "
            'savemismatchparams=yes mismatchparamfile="cap_mismatch_params.txt" savefamilyplots=yes savedatainseparatedir=yes {\n'
            '  ac_unit ac start=1Meg stop=2Meg lin=2\n}\n')
    else:analysis="ac_unit ac start=1K stop=1G dec=5\n"
    text+="\n"+analysis+"save "+saves+"\n"
    name=("units_mc_"+str(mc) if mc else "units_nominal_ac")+("" if tag=="initial" else "_"+tag)
    dump(f"units/{name}_case.json",{"numruns":mc,"cell":cell,"oa_sha256":sha(OUT/"oa_netlists"/cell/tag/"input.scs")})
    batch([stage(name,text)],"units",workers=1)

def unit_bipolar():
    text=oa("tb_cdac8_unit_char","forced_mismatch")
    # Stimulus-only variant: no device/model/connectivity statement is edited.
    text=text.replace("dc=900.0m mag=1", "dc=-900.0m mag=1").replace("dc=450.00m mag=1", "dc=-450.00m mag=1")
    text+="\nac_unit ac start=1K stop=1G dec=5\nsave "+" ".join("VSRC"+k+str(i)+":p" for k in "abc" for i in range(3))+"\n"
    batch([stage("units_negative_bias_ac",text)],"units",workers=1)

def bank_ac(mc=0):
    text=oa("tb_cdac8_caps")
    saves=" ".join(f"V_SENSE{s}{b}:p" for s in "PN" for b in range(9))
    if mc:
        analysis=(f"mc_bank montecarlo numruns={mc} seed=61231 variations=mismatch sampling=standard donominal=no "
            'savemismatchparams=yes mismatchparamfile="bank_mismatch.txt" savefamilyplots=yes savedatainseparatedir=yes {\n'
            '  ac_bank ac start=1Meg stop=2Meg lin=2\n}\n')
    else:analysis="ac_bank ac start=1Meg stop=2Meg lin=2\n"
    name=f"banks_mc_{mc}"
    dump(f"banks/{name}_case.json",{"numruns":mc,"oa_sha256":sha(OUT/"oa_netlists/tb_cdac8_caps/initial/input.scs")})
    batch([stage(name,text+"\n"+analysis+"save "+saves+"\n")],"banks",workers=1)

def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("unit-ac","unit-mc","unit-bipolar","bank-ac","bank-mc","switches","smoke","aps-probe","balanced-smoke","safephase-smoke","softreset-smoke","ref18-screen","pvt","stress-trace","cm-scale","baseline-completeness","ideal-input","acceleration-probe","accelerated-full","static","dynamic","dac"));p.add_argument("--runs",type=int,default=5);p.add_argument("--tag",default="initial");a=p.parse_args()
    if a.action=="switches":switch_screen(a.tag)
    elif a.action=="balanced-smoke":balanced_smoke()
    elif a.action=="safephase-smoke":safephase_smoke()
    elif a.action=="softreset-smoke":softreset_smoke()
    elif a.action=="ref18-screen":ref18_screen()
    elif a.action=="pvt":pvt()
    elif a.action=="stress-trace":stress_trace()
    elif a.action=="cm-scale":cm_scale()
    elif a.action=="baseline-completeness":baseline_completeness()
    elif a.action=="ideal-input":ideal_input()
    elif a.action=="acceleration-probe":acceleration_probe()
    elif a.action=="accelerated-full":accelerated_full()
    elif a.action in ("static","dynamic","dac"):sweep_system(a.action)
    elif a.action=="unit-bipolar":unit_bipolar()
    elif a.action=="smoke":smoke(a.tag)
    elif a.action=="aps-probe":aps_probe(a.tag)
    elif a.action.startswith("bank"):bank_ac(a.runs if a.action=="bank-mc" else 0)
    else:unit_ac(a.runs if a.action=="unit-mc" else 0,a.tag)

if __name__=="__main__":main()
