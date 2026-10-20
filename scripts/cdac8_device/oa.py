"""Owned OA builds. Existing eight/ten-bit cells and the PDK are read-only."""
from __future__ import annotations
import argparse
import json
from common import ROOT,OUT,LIB,dump,load,cfg
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_inst_by_master_name as inst,schematic_create_pin as pin,schematic_label_instance_term as term
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
from virtuoso_bridge.virtuoso.symbol.ops import symbol_create_rect,symbol_create_selection_box,symbol_create_pin,symbol_create_instance_label,symbol_create_logical_label,symbol_set_term_order

READONLY=("tb_cap_char","sar_cdac_flat_8b","sar_comparator_macro_8b","sar_macro_controller_8b",
          "sar_bootstrap_canvas_flat_8b","sar_strongarm_t28")

def skill(c,s):
    r=c.execute_skill(s,timeout=180)
    assert not r.errors,r
    return r.output

def exists(c,cell):return (skill(c,f'ddGetObj("{LIB}" "{cell}")') or '').strip() not in ('','nil')
def refuse(c,cell):assert not exists(c,cell),f"Refuse existing {cell}"
def add(s,name,master,x,y,terms,lib="analogLib"):
    s.add(inst(lib,master,"symbol",name,x,y,"R0"))
    for t,n in terms.items():s.add(term(name,t,n))
def setparams(c,cell,values):
    for name,p in values.items():_run_batched_param_update(c,LIB,cell,name,{k:str(v) for k,v in p.items()})

def check(c,cell,symbol=True):
    with c.schematic.modify(LIB,cell,timeout=180):pass
    data=c.schematic.read(LIB,cell,param_filters=None,include_positions=True)
    dump(f"oa/{cell}.json",data)
    marks=c.fetch(f'dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")~>markers',["objType","severity","bBox"])
    dump(f"oa/{cell}_markers.json",marks)
    assert not marks,(cell,marks)
    if symbol:dump(f"oa/{cell}_ports.json",c.symbol.read_ports(LIB,cell))
    print("OA_OK",cell,flush=True);return data

def export(c,cell,tag="initial"):
    check(c,cell,symbol=False)
    target=OUT/"oa_netlists"/cell/tag
    assert not (target/"input.scs").exists(),"Preserve original exact export"
    r=c.schematic.export_netlist(LIB,cell,target,simulator="spectre",timeout=180)
    dump(f"oa/{cell}_{tag}_export.json",r)
    print("EXPORTED",cell,tag,flush=True)

def symbol(c,cell,inputs,outputs=(),output_direction="inputOutput"):
    h=max(len(inputs),len(outputs))*.5+.75
    with c.symbol.create(LIB,cell,timeout=180) as s:
        s.add(symbol_create_rect("device","drawing",.75,-.5,7.25,h));s.add(symbol_create_selection_box(0,-.75,8,h+.25))
        for names,x,lx,direction,just in ((inputs,0,.9,"input","centerLeft"),(outputs,8,7.1,output_direction,"centerRight")):
            for i,n in enumerate(names):
                y=h-.5-i*.5
                s.add(symbol_create_pin(n,x,y,direction=direction,half_size=.025,label_x=lx,label_y=y,label_justification=just))
        s.add(symbol_create_instance_label(2,h+.4));s.add(symbol_create_logical_label(4,h/2));s.add(symbol_set_term_order([*inputs,*outputs]))

def pins(s,inputs,outputs,xout=35):
    for j,n in enumerate(inputs):s.add(pin(n,-12,12-j,"R0",direction="input"))
    for j,n in enumerate(outputs):s.add(pin(n,xout,12-j*3,"R180",direction="inputOutput"))

PORTS=["BASE","CLK_SAMPLE",*[f"SEL{q}<{b}>" for q in (0,1) for b in range(8)],"VCM","VREFN","VREFP","VDD","VSS"]

def selected_array(c,key):
    unit="cdac8_unit";refuse(c,unit)
    with c.schematic.create(LIB,unit) as s:
        add(s,"CUNIT","cfmom_2t",0,0,{"PLUS":"TOP","MINUS":"BOT"},"tsmcN28")
        pins(s,[],["TOP","BOT"])
    geo={**cfg()["unit_candidates"][key],"mismatch":"1"}
    setparams(c,unit,{"CUNIT":geo});c.symbol.generate_from_schematic(LIB,unit,overwrite=False,timeout=120);check(c,unit)
    for count in (1,2,4,8,16,32,64,128):
        cell=f"cdac8_bank_{count}";refuse(c,cell)
        with c.schematic.create(LIB,cell,timeout=180) as s:
            pins(s,[],["TOP","BOT"])
            for i in range(count):add(s,f"XU{i:03d}",unit,(i%16)*3,(i//16)*4,{"TOP":"TOP","BOT":"BOT"},LIB)
        c.symbol.generate_from_schematic(LIB,cell,overwrite=False,timeout=120);check(c,cell)
    # Independent source-voltage probes measure actual summed PDK capacitance
    # at each bank, including 512 local mismatch instances in one MC iteration.
    cell="tb_cdac8_caps";refuse(c,cell);values={}
    with c.schematic.create(LIB,cell,timeout=180) as s:
        add(s,"V_TOP","vdc",-8,0,{"PLUS":"CTOP","MINUS":"gnd!"});values["V_TOP"]={"vdc":".45","acm":"1"}
        for side,j in (("P",0),("N",1)):
            for i,count in enumerate((1,2,4,8,16,32,64,128,1)):
                suffix=f"{side}{i}";bot="B"+suffix
                add(s,"XC"+suffix,f"cdac8_bank_{count}",i*4,j*9,{"TOP":"CTOP","BOT":bot},LIB)
                add(s,"V_SENSE"+suffix,"vdc",i*4,j*9-4,{"PLUS":bot,"MINUS":"gnd!"});values["V_SENSE"+suffix]={"vdc":"0"}
    setparams(c,cell,values);export(c,cell)
    # First isolation stage: real PDK capacitor banks, ideal reference relays.
    cell="cdac8_caps_ideal_switch";refuse(c,cell);values={}
    with c.schematic.create(LIB,cell,timeout=180) as s:
        pins(s,PORTS,["TOPP","TOPN"])
        for side,y,r0,r1 in (("P",25,"VREFP","VREFN"),("N",-20,"VREFN","VREFP")):
            for bit in range(9):
                weight=1<<bit if bit<8 else 1;suffix=f"{side}{bit}";bot="B"+suffix;x=bit*4
                add(s,"XC"+suffix,f"cdac8_bank_{weight}",x,y,{"TOP":"TOP"+side,"BOT":bot},LIB)
                choices=[("S","VCM","CLK_SAMPLE"),("0",r0,f"SEL0<{bit}>" if bit<8 else "BASE")]
                if bit<8:choices.append(("1",r1,f"SEL1<{bit}>"))
                for j,(nm,ref,ctrl) in enumerate(choices):
                    name="SW"+suffix+nm
                    add(s,name,"switch",x,y-3-j*3,{"N+":bot,"N-":ref,"NC+":ctrl,"NC-":"VSS"})
                    values[name]={"rc":"150","ro":"1T","vt1":"350m","vt2":"550m"}
        # VDD is a common interface port only in the ideal-switch A/B cell.
        add(s,"R_UNUSED_VDD","res",30,-38,{"PLUS":"VDD","MINUS":"VSS"});values["R_UNUSED_VDD"]={"r":"1T"}
    setparams(c,cell,values);symbol(c,cell,PORTS,["TOPP","TOPN"]);check(c,cell)

def preflight(c):
    lib=c.library.get(LIB)
    assert lib.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and lib.technology_library=="tsmcN28"
    dump("oa/library.json",vars(lib));dump("oa/windows_before.json",c.list_windows())
    for cell in READONLY:
        # Behavioral-only controller has no schematic by design.
        data=c.symbol.read_ports(LIB,cell) if cell=="sar_macro_controller_8b" else c.schematic.read(LIB,cell,param_filters=None,include_positions=True)
        p=OUT/"oa"/(cell+"_before.json")
        if p.exists():assert json.loads(p.read_text())==data,cell
        else:dump(f"oa/{cell}_before.json",data)
    for cell in ("cfmom_2t","nch_mac","pch_mac","nch_hvt_mac","pch_hvt_mac"):
        parameters=c.fetch(f'cdfGetCellCDF(ddGetObj("tsmcN28" "{cell}"))~>parameters',
            ["name","type","defValue","choices","editable"],timeout=60)
        dump(f"pdk/{cell}_cdf.json",parameters)
        dump(f"pdk/{cell}_ports.json",c.symbol.read_ports("tsmcN28",cell))
    top="/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs"
    command=f'''/bin/sh -c 'grep -i "section.*mom" "{top}"; for cdac_tool in calibre assura pvs qrc; do command -v "$cdac_tool" || true; done; true' '''
    r=c.ssh_runner.run_command(command,timeout=30)
    dump("pdk/model_sections_and_tools.json",{"stdout":r.stdout,"stderr":r.stderr,"returncode":r.returncode})
    print("PREFLIGHT_OK",flush=True)

def units(c):
    for key,geo in cfg()["unit_candidates"].items():
        cell="cdac8_unit_candidate_"+key;refuse(c,cell)
        with c.schematic.create(LIB,cell) as s:
            add(s,"CUNIT","cfmom_2t",0,0,{"PLUS":"TOP","MINUS":"BOT"},"tsmcN28")
            s.add(pin("TOP",-3,1,"R0",direction="inputOutput"));s.add(pin("BOT",-3,-1,"R0",direction="inputOutput"))
        setparams(c,cell,{"CUNIT":geo})
        c.symbol.generate_from_schematic(LIB,cell,overwrite=False,timeout=120)
        state=check(c,cell)
        actual=state["instances"][0]["params"]
        assert actual["Nfinger"]==geo["Nfinger"] and actual["Lfinger"]==geo["Lfinger"],actual
        print("CAP_CDF",key,actual.get("c"),flush=True)
    cell="tb_cdac8_unit_char";refuse(c,cell)
    values={}
    with c.schematic.create(LIB,cell) as s:
        for j,key in enumerate("abc"):
            for i,bias in enumerate((0,.45,.9)):
                net=f"C{key}{i}"
                add(s,"XC"+key+str(i),"cdac8_unit_candidate_"+key,j*9,i*5,{"TOP":net,"BOT":"gnd!"},LIB)
                add(s,"VSRC"+key+str(i),"vdc",j*9+4,i*5,{"PLUS":net,"MINUS":"gnd!"})
                values["VSRC"+key+str(i)]={"vdc":str(bias),"acm":"1"}
    setparams(c,cell,values);c.open_window(LIB,cell,view="schematic");export(c,cell)

def force_mismatch(c):
    for key in "abc":
        cell="cdac8_unit_candidate_"+key
        setparams(c,cell,{"CUNIT":{"mismatch":"1"}})
        check(c,cell)
    export(c,"tb_cdac8_unit_char","forced_mismatch")

def model_audit(c):
    base="/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre"
    top=base+"/crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs"
    command=f"grep -n -i -E 'section|include|mom|ccoflag_cap' '{top}' | head -60"
    r=c.ssh_runner.run_command(command,timeout=30)
    dump("pdk/model_metadata_audit.json",{"stdout":r.stdout,"stderr":r.stderr,"returncode":r.returncode})
    print(r.stdout,flush=True)

def layout_audit(c):
    pdk="/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531"
    command=f'''/bin/sh -c 'printf "Known installations\\n"; ls -d /home/cadence/* /home/mentor/* /home/siemens/* 2>/dev/null; printf "Rule directories\\n"; find "{pdk}" -maxdepth 3 -type d 2>/dev/null | grep -i -E "calibre|assura|pvs|qrc|drc|lvs" | head -35; printf "pvs identity\\n"; readlink -f /usr/sbin/pvs; true' '''
    r=c.ssh_runner.run_command(command,timeout=60)
    dump("pdk/layout_prerequisites.json",{"stdout":r.stdout,"stderr":r.stderr,"returncode":r.returncode})
    print(r.stdout,flush=True)

def mos(s,name,master,x,y,d,g,src,b):
    s.add(inst("tsmcN28",master,"symbol",name,x,y,"R0"))
    s.add_net_label_to_transistor(name,drain_net=d,gate_net=g,source_net=src,body_net=b)

def switches(c,balanced=False):
    import math
    for bit in range(8):
        cell=f"cdac8_ref_switch_b{bit}"
        if not balanced:refuse(c,cell)
        else:skill(c,f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{cell}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
        inputs=["EH","EL","ES","VCM","VREFP","VREFN","VDD","VSS"]
        w=max(.25,math.sqrt((1<<bit)/128))
        scale=f"{1<<bit}*" if balanced else ""
        values={}
        with c.schematic.create(LIB,cell) as s:
            pins(s,inputs,["BOT"])
            for name,master,x,y,d,g,src,b,width,multi in (
                ("MP_HIGH","pch_mac",8,6,"BOT","EH_B","VREFP","VDD",.175 if balanced else w,scale+"MULT_R"),
                ("MN_LOW","nch_mac",8,1,"BOT","EL_D" if balanced else "EL","VREFN","VSS",.15 if balanced else w,scale+"MULT_R"),
                ("MN_CM","nch_mac",18,1,"BOT","ES","VCM","VSS",.25 if balanced else w,scale+"MULT_S"),
                ("MP_CM","pch_mac",18,6,"BOT","ES_B","VCM","VDD",.30 if balanced else w,scale+"MULT_S"),
                ("MN_IH","nch_mac",0,1,"EH_B","EH","VSS","VSS",.25,scale+"MULT_D"),
                ("MP_IH","pch_mac",0,6,"EH_B","EH","VDD","VDD",.30 if balanced else .25,scale+"MULT_D"),
                ("MN_IS","nch_mac",0,-8,"ES_B","ES","VSS","VSS",.25,scale+"MULT_D"),
                ("MP_IS","pch_mac",0,-3,"ES_B","ES","VDD","VDD",.30 if balanced else .25,scale+"MULT_D")):
                mos(s,name,master,x,y,d,g,src,b)
                values[name]={"Wfg":f"{width:.9g}u","w":f"{width:.9g}u","l":"30n","fingers":"1","simM":multi}
            if balanced:
                for name,master,x,y,d,g,src,b,width in (
                    ("MN_IL1","nch_mac",8,-9,"EL_B","EL","VSS","VSS",.25),
                    ("MP_IL1","pch_mac",8,-4,"EL_B","EL","VDD","VDD",.30),
                    ("MN_IL2","nch_mac",18,-9,"EL_D","EL_B","VSS","VSS",.25),
                    ("MP_IL2","pch_mac",18,-4,"EL_D","EL_B","VDD","VDD",.30)):
                    mos(s,name,master,x,y,d,g,src,b)
                    values[name]={"Wfg":f"{width}u","w":f"{width}u","l":"30n","fingers":"1","simM":scale+"MULT_D"}
        setparams(c,cell,values);symbol(c,cell,inputs,["BOT"]);check(c,cell)
    if not balanced:
        device_array(c)
        switch_char(c)
    else:
        balanced_exports(c)

def balanced_exports(c):
    # A master revision invalidates the parent's extraction timestamp.
    # Recheck owned hierarchy bottom-up; never suppress OSSHNL-109.
    for cell in ("cdac8_device","cdac8_device_nominal"):
        check(c,cell)
    for cell in ("tb_cdac8_switch_char","tb_cdac8_sampling","tb_cdac8_sar","tb_cdac8_nominal","tb_cdac8_nominal_sar"):
        if not (OUT/"oa_netlists"/cell/"balanced/input.scs").exists():
            export(c,cell,"balanced")

def device_array(c,repair=False):
    cell="cdac8_device"
    if not repair:refuse(c,cell)
    else:skill(c,f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{cell}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
    with c.schematic.create(LIB,cell,timeout=180) as s:
        pins(s,PORTS,["TOPP","TOPN"],xout=130)
        for side,y in (("P",25),("N",-20)):
            for bit in range(9):
                count=1<<bit if bit<8 else 1;suffix=f"{side}{bit}";bot="B"+suffix;x=bit*12
                add(s,"XC"+suffix,f"cdac8_bank_{count}",x,y,{"TOP":"TOP"+side,"BOT":bot},LIB)
                e0=f"SEL0<{bit}>" if bit<8 else "BASE";e1=f"SEL1<{bit}>" if bit<8 else "VSS"
                eh,el=(e0,e1) if side=="P" else (e1,e0)
                add(s,"XS"+suffix,f"cdac8_ref_switch_b{min(bit,7) if bit<8 else 0}",x,y-14,
                    {"BOT":bot,"EH":eh,"EL":el,"ES":"CLK_SAMPLE","VCM":"VCM","VREFP":"VREFP","VREFN":"VREFN","VDD":"VDD","VSS":"VSS"},LIB)
    symbol(c,cell,PORTS,["TOPP","TOPN"]);check(c,cell)

def switch_char(c,cell="tb_cdac8_switch_char",master="cdac8_ref_switch_b7"):
    refuse(c,cell);values={}
    with c.schematic.create(LIB,cell) as s:
        for i,(net,vdc) in enumerate((("VDD!","SUP"),("VCM","SUP/2"),("VREFP","SUP"))):
            name="VSRC"+str(i);add(s,name,"vdc",-8,i*5,{"PLUS":net,"MINUS":"gnd!"});values[name]={"vdc":vdc}
        for i,path in enumerate("HLS"):
            for j,on in enumerate((True,False)):
                suffix=path+("ON" if on else "OFF");bot="B"+suffix
                eh="VDD!" if on and path=="H" else "gnd!";el="VDD!" if on and path=="L" else "gnd!";es="VDD!" if on and path=="S" else "gnd!"
                add(s,"XDUT"+suffix,master,i*20,j*18,{"BOT":bot,"EH":eh,"EL":el,"ES":es,"VCM":"VCM","VREFP":"VREFP","VREFN":"gnd!","VDD":"VDD!","VSS":"gnd!"},LIB)
                nm="VPROBE"+suffix;add(s,nm,"vdc",i*20+10,j*18,{"PLUS":bot,"MINUS":"gnd!"})
                values[nm]={"vdc":("SUP-1m" if path=="H" else "1m" if path=="L" else "SUP/2+1m") if on else "VPROBE"}
    setparams(c,cell,values);export(c,cell)

def ref18(c,msb_only=False):
    for bit in ((7,) if msb_only else range(8)):
        cell=f'cdac8_ref18_b{bit}'
        if exists(c,cell):
            assert bit==7 and not msb_only
            continue
        inputs=['EH','EL','ES','VCM','VREFP','VREFN','VDD','VSS'];values={};scale=f'{1<<bit}*'
        with c.schematic.create(LIB,cell) as s:
            pins(s,inputs,['BOT'])
            rows=[('MP_HIGH','pch_18_mac',8,6,'BOT','EH_B','VREFP','VDD',1.,'MULT_R'),
                ('MN_LOW','nch_18_mac',8,1,'BOT','EL_D','VREFN','VSS',.5,'MULT_R'),
                ('MN_CM','nch_18_mac',18,1,'BOT','ES','VCM','VSS',1.,'MULT_S'),
                ('MP_CM','pch_18_mac',18,6,'BOT','ES_B','VCM','VDD',1.,'MULT_S')]
            for stem,x,y,out,inp in (('IH',0,1,'EH_B','EH'),('IS',0,-8,'ES_B','ES'),('IL1',8,-9,'EL_B','EL'),('IL2',18,-9,'EL_D','EL_B')):
                rows.extend([(f'MN_{stem}','nch_mac',x,y,out,inp,'VSS','VSS',.25,'MULT_D'),
                             (f'MP_{stem}','pch_mac',x,y+5,out,inp,'VDD','VDD',.30,'MULT_D')])
            for name,master,x,y,d,g,src,b,width,multi in rows:
                mos(s,name,master,x,y,d,g,src,b)
                values[name]={'Wfg':f'{width}u','w':f'{width}u','l':'150n' if '_18_' in master else '30n','fingers':'1','simM':scale+multi}
        setparams(c,cell,values);symbol(c,cell,inputs,['BOT']);check(c,cell)
    if msb_only:switch_char(c,'tb_cdac8_ref18_char','cdac8_ref18_b7')

def import_va(c,cell,inputs,outputs):
    refuse(c,cell);symbol(c,cell,inputs,outputs,output_direction="output")
    skill(c,f'schViewToView("{LIB}" "{cell}" "{LIB}" "{cell}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    r=c.upload_file(ROOT/f"models/veriloga/{cell}.va",f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{cell}/veriloga/veriloga.va",timeout=120)
    assert not r.errors,r
    skill(c,f'ahdlUpdateViewInfo("{LIB}" ?cell "{cell}" ?view "veriloga")')
    dump(f"oa/{cell}_ports.json",c.symbol.read_ports(LIB,cell))

CTRL_IN=["COMP_P","COMP_N","CLK_SAMPLE","PREPARE","HOLD_START","CLK_TRIAL","CLK_LATCH","CLK_COMPARE","VDD","VSS"]
CTRL_OUT=[*[f"SEL{q}_{b}" for q in (0,1) for b in range(7,-1,-1)],"BASE",*[f"D{b}" for b in range(7,-1,-1)],"BUSY","VALID","CMP_CLK","CMP_RESET"]

def controls(c):
    import_va(c,"cdac8_controller",CTRL_IN,CTRL_OUT)
    import_va(c,"cdac8_device_sequence",["VDD","VSS"],["VINP_SRC","VINN_SRC"])

def control_cdf(c):
    # These are NEW behavioral cells, not PDK CDFs. Native CDF APIs were
    # resolved with SKILL Finder; expose parameters to ordinary instance edits.
    for cell,defaults in (("cdac8_controller",{"open_loop":"0","fixed_code":"-1","dead_time_s":"100p"}),
            ("cdac8_device_sequence",{"stimulus_mode":"0","differential_v":"0","frequency_hz":"4.501953125Meg"})):
        params=" ".join(f'unless(cdfFindParamByName(d "{n}") unless(cdfCreateParam(d ?name "{n}" ?prompt "{n}" ?type "string" ?defValue "{v}" ?parseAsNumber "yes" ?parseAsCEL "yes") error("CDF creation failed")))' for n,v in defaults.items())
        expression=f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{cell}")) unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "{cell}"))) {params} cdfSaveCDF(d))'
        print("CDF_CREATE",cell,c.execute_skill(expression,timeout=60),flush=True)
        parameters=c.fetch(f'cdfGetCellCDF(ddGetObj("{LIB}" "{cell}"))~>parameters',["name","type","defValue"])
        assert {p["name"] for p in parameters}==set(defaults),parameters
        dump(f"oa/{cell}_cdf.json",parameters)

def bench(c,cell,cdac,native=False,real_comp=False,repair=False,tag="initial",safephase=False):
    if not repair:refuse(c,cell)
    else:skill(c,f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{cell}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
    values={}
    with c.schematic.create(LIB,cell,timeout=180) as s:
        terms={p:p for p in PORTS};terms.update(VDD="VDD!",VSS="gnd!",CLK_SAMPLE="DAC_SAMPLE",TOPP="TOPP",TOPN="TOPN")
        add(s,"XCDAC",cdac,0,8,terms,LIB)
        add(s,"XCTRL","cdac8_controller",26,4,{**{n:n for n in CTRL_IN+CTRL_OUT},"CLK_SAMPLE":"CYCLE" if safephase else "PHI","VDD":"VDD!","VSS":"gnd!",
            **{f"SEL{q}_{b}":f"SEL{q}<{b}>" for q in (0,1) for b in range(8)},**{f"D{b}":f"DOUT<{b}>" for b in range(8)}},LIB)
        values["XCTRL"]={"open_loop":"OPEN_LOOP","fixed_code":"FIXED_CODE","dead_time_s":"DEAD_TIME"}
        add(s,"XINPUT","cdac8_device_sequence",-24,-3,{"VDD":"VDD!","VSS":"gnd!","VINP_SRC":"VINP_SRC","VINN_SRC":"VINN_SRC"},LIB)
        values["XINPUT"]={"stimulus_mode":"STIM_MODE","differential_v":"VDIFF","frequency_hz":"FIN"}
        for side,y in (("P",17),("N",-7)):
            add(s,"RIN"+side,"res",-20,y,{"PLUS":"VIN"+side+"_SRC","MINUS":"VIN"+side});values["RIN"+side]={"r":"50"}
            if native:
                add(s,"XBOOT"+side,"sar_bootstrap_canvas_flat_8b",-10,y,{"CLKS":"PHI","CLKSB":"CLKB"+side,"Vin":"VIN"+side,"VOUT":"TOP"+side},LIB)
                add(s,"RMON"+side,"res",-2,y-3,{"PLUS":"CLKB"+side,"MINUS":"gnd!"});values["RMON"+side]={"r":"1T"}
            else:
                add(s,"SSAMPLE"+side,"switch",-10,y,{"N+":"VIN"+side,"N-":"TOP"+side,"NC+":"PHI","NC-":"gnd!"})
                values["SSAMPLE"+side]={"rc":"150","ro":"1T","vt1":".35","vt2":".55"}
        if real_comp:
            add(s,"XCOMP","sar_strongarm_t28",13,17,{"CLK":"CMP_CLK","VINP":"TOPP","VINN":"TOPN","OUTP":"COMP_P","OUTN":"COMP_N","VDD":"VDD!","VSS":"gnd!"},LIB)
            for i,net in enumerate(("COMP_P","COMP_N","CMP_RESET")):
                nm="CMPLOAD"+str(i)
                add(s,nm,"cap" if i<2 else "res",48,18-i*4,{"PLUS":net,"MINUS":"gnd!"});values[nm]={"c":"5f"} if i<2 else {"r":"1T"}
        else:
            add(s,"XCOMP","sar_comparator_macro_8b",13,17,{"TOPP":"TOPP","TOPN":"TOPN","COMP_P":"COMP_P","COMP_N":"COMP_N","CMP_RESET":"CMP_RESET","VDD":"VDD!","VSS":"gnd!","VCM":"VCM"},LIB)
            add(s,"RCMPCLK","res",48,6,{"PLUS":"CMP_CLK","MINUS":"gnd!"});values["RCMPCLK"]={"r":"1T"}
        for i,(name,net,dc) in enumerate((("VVDD","VDD!","SUP"),("VVCM","VCM","SUP/2"),("VREFHIGH","VREFP_SRC","SUP"),("VREFLOW","VREFN_SRC","0"))):
            add(s,name,"vdc",-25+i*4,-22,{"PLUS":net,"MINUS":"gnd!"});values[name]={"vdc":dc}
        for i,(name,net,delay,width,period,edge) in enumerate((("VPHI","PHI","1n","39.9n","100n","100p"),
            ("VDACSAMPLE","DAC_SAMPLE","42n","48.2n","100n","20p"),("VPREPARE","PREPARE","90n","200p","100n","20p"),("VHOLD","HOLD_START","43n","200p","100n","20p"),
            ("VTRIAL","CLK_TRIAL","48n","200p","5n","20p"),("VLATCH","CLK_LATCH","47.5n","200p","5n","20p"),
            ("VCOMPARE","CLK_COMPARE","46n","1.53n","5n","20p"))):
            add(s,name,"vpulse",-5+i*4,-27,{"PLUS":net,"MINUS":"gnd!"});values[name]={"v1":"SUP" if name=="VDACSAMPLE" else "0","v2":"0" if name=="VDACSAMPLE" else "SUP","td":delay,"pw":width,"per":period,"tr":edge,"tf":edge}
        if safephase:
            values['VPHI'].update(v1='SUP',v2='0',td='41n',pw='48.9n')
            values['VPREPARE']['td']='92n';values['VDACSAMPLE']['pw']='50.2n'
            add(s,'VCYCLE','vpulse',28,-32,{'PLUS':'CYCLE','MINUS':'gnd!'})
            values['VCYCLE']={'v1':'0','v2':'SUP','td':'1n','pw':'39.9n','per':'100n','tr':'100p','tf':'100p'}
        for i,side in enumerate("PN"):
            add(s,"RREF"+side,"res",13+i*6,-8,{"PLUS":"VREF"+side+"_SRC","MINUS":"VREF"+side});values["RREF"+side]={"r":"RREF"}
            add(s,"CREF"+side,"cap",13+i*6,-13,{"PLUS":"VREF"+side,"MINUS":"gnd!"});values["CREF"+side]={"c":"CDECAP"}
        for i,net in enumerate([*[f"DOUT<{b}>" for b in range(8)],"BUSY","VALID"]):
            nm="RLOAD"+str(i);add(s,nm,"res",28+i*2,-22,{"PLUS":net,"MINUS":"gnd!"});values[nm]={"r":"1G"}
    setparams(c,cell,values);c.open_window(LIB,cell,view="schematic");export(c,cell,tag)

def update_controls(c):
    symbol(c,"cdac8_controller",CTRL_IN,CTRL_OUT,output_direction="output")
    r=c.upload_file(ROOT/"models/veriloga/cdac8_controller.va",f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/cdac8_controller/veriloga/veriloga.va",timeout=120)
    assert not r.errors,r
    skill(c,f'ahdlUpdateViewInfo("{LIB}" ?cell "cdac8_controller" ?view "veriloga")')

def prep_benches(c):
    update_controls(c)
    bench(c,"tb_cdac8_device","cdac8_caps_ideal_switch",repair=True,tag="prep")
    bench(c,"tb_cdac8_sampling","cdac8_device",native=True,repair=True,tag="prep")
    bench(c,"tb_cdac8_sar","cdac8_device",native=True,real_comp=True,repair=True,tag="prep")

def nominal_fast(c):
    cell="cdac8_device_nominal";refuse(c,cell);values={}
    geo={**cfg()["unit_candidates"][cfg()["selected_unit"]],"mismatch":"1"}
    with c.schematic.create(LIB,cell,timeout=180) as s:
        pins(s,PORTS,["TOPP","TOPN"],xout=130)
        for side,y in (("P",25),("N",-20)):
            for bit in range(9):
                count=1<<bit if bit<8 else 1;suffix=f"{side}{bit}";bot="B"+suffix;x=bit*12
                name="CMOM"+suffix
                add(s,name,"cfmom_2t",x,y,{"PLUS":"TOP"+side,"MINUS":bot},"tsmcN28")
                values[name]={**geo,"m":str(count)}
                e0=f"SEL0<{bit}>" if bit<8 else "BASE";e1=f"SEL1<{bit}>" if bit<8 else "VSS"
                eh,el=(e0,e1) if side=="P" else (e1,e0)
                add(s,"XS"+suffix,f"cdac8_ref_switch_b{bit if bit<8 else 0}",x,y-14,
                    {"BOT":bot,"EH":eh,"EL":el,"ES":"CLK_SAMPLE","VCM":"VCM","VREFP":"VREFP","VREFN":"VREFN","VDD":"VDD","VSS":"VSS"},LIB)
    setparams(c,cell,values);symbol(c,cell,PORTS,["TOPP","TOPN"]);check(c,cell)
    bench(c,"tb_cdac8_nominal",cell,native=True)
    bench(c,"tb_cdac8_nominal_sar",cell,native=True,real_comp=True)

def softreset(c):
    # Slew only the VCM re-enable edge in the original phase fixture.
    # The fast acquisition-release edge and held/conversion timing stay intact.
    for cell in ('tb_cdac8_sampling','tb_cdac8_nominal','tb_cdac8_nominal_sar'):
        setparams(c,cell,{'VDACSAMPLE':{'tf':'1n'}})
        export(c,cell,'softreset')

def retain(c):
    # Timing experiments did not clear the stress gate; restore the fully
    # characterized balanced baseline instead of silently leaving an experiment.
    for cell in ('tb_cdac8_sampling','tb_cdac8_nominal','tb_cdac8_nominal_sar'):
        setparams(c,cell,{'VDACSAMPLE':{'tf':'20p'}})
        export(c,cell,'retained')

def benches(c,repair=False):
    bench(c,"tb_cdac8_device","cdac8_caps_ideal_switch",repair=repair)
    bench(c,"tb_cdac8_sampling","cdac8_device",native=True)
    bench(c,"tb_cdac8_sar","cdac8_device",native=True,real_comp=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("preflight","units","force-mismatch","model-audit","layout-audit","array","switches","repair-device","controls","control-cdf","benches","repair-benches","prep-benches","nominal-fast","balanced","balanced-exports","safephase","softreset","ref18-screen","retain","ideal-input"));p.add_argument("--unit",choices=list("abc"),default="a");a=p.parse_args()
    c=VirtuosoClient.from_env(profile="t28_io")
    if a.action=="array":selected_array(c,a.unit)
    elif a.action=="repair-device":device_array(c,True);switch_char(c)
    elif a.action=="repair-benches":benches(c,True)
    elif a.action=="prep-benches":prep_benches(c)
    elif a.action=="nominal-fast":nominal_fast(c)
    elif a.action=="balanced":switches(c,True)
    elif a.action=="balanced-exports":balanced_exports(c)
    elif a.action=="safephase":bench(c,'tb_cdac8_safephase','cdac8_device_nominal',native=True,safephase=True)
    elif a.action=="softreset":softreset(c)
    elif a.action=="ref18-screen":ref18(c,True)
    elif a.action=="retain":retain(c)
    elif a.action=="ideal-input":bench(c,'tb_cdac8_ideal_input','cdac8_device')
    else:{"preflight":preflight,"units":units,"force-mismatch":force_mismatch,"model-audit":model_audit,"layout-audit":layout_audit,"switches":switches,"controls":controls,"control-cdf":control_cdf,"benches":benches}[a.action](c)

if __name__=="__main__":main()
