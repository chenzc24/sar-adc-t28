"""Owned testbench creation. Behavioral plant is explicit, native DUT intact."""
from pathlib import Path
import argparse
from circuit import Cell,LIB,hierarchy
from oa import OUT,ROOT,build,dump,exists,symbol
from virtuoso_bridge import VirtuosoClient

PLANT_IN=["VDD","VSS","VIN","SAMPLE","CMP_CLK"]+[f"C{i}" for i in range(7,-1,-1)]
PLANT_OUT=["P","N","TOPP","TOPN"]


def plant(c,resume=False):
    cell="sar8a_plant";path=ROOT/"models/veriloga"/(cell+".va")
    if exists(c,cell):
        assert resume and not exists(c,cell,"veriloga"),"Only resume the known symbol-only partial import"
        actual=c.symbol.read_ports(LIB,cell)
        assert {t["name"] for t in actual["terms"]}==set(PLANT_IN+PLANT_OUT)
    else:
        obj=Cell(cell,PLANT_IN,PLANT_OUT);symbol(c,obj)
    r=c.execute_skill(f'schViewToView("{LIB}" "{cell}" "{LIB}" "{cell}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    assert not r.errors and r.output.strip() not in ("nil",""),r
    info=c.library.get(LIB)
    c.upload_file(path,f"{info.path}/{cell}/veriloga/veriloga.va")
    r=c.execute_skill(f'ahdlUpdateViewInfo("{LIB}" ?cell "{cell}" ?view "veriloga")')
    assert not r.errors,r
    dump("oa/sar8a_plant_ports.json",c.symbol.read_ports(LIB,cell))
    print("VA_IMPORTED",cell,flush=True)


def plant_cdf(c):
    # Same verified new-behavioral-cell CDF pattern used by cdac8_device/oa.py.
    # No PDK CDF is edited.
    defaults={"pattern_mode":"0","pattern_word":"165","fault_mode":"0","fault_bit":"-1",
              "min_delay_s":"150p","delay_spread_s":"0","fault_frame":"-1"}
    body=" ".join(f'unless(cdfFindParamByName(d "{n}") unless(cdfCreateParam(d ?name "{n}" ?prompt "{n}" ?type "string" ?defValue "{v}" ?parseAsNumber "yes" ?parseAsCEL "yes") error("CDF creation failed")))' for n,v in defaults.items())
    expression=f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "sar8a_plant")) unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "sar8a_plant"))) {body} cdfSaveCDF(d))'
    r=c.execute_skill(expression,timeout=60);assert not r.errors,r
    data=c.fetch(f'cdfGetCellCDF(ddGetObj("{LIB}" "sar8a_plant"))~>parameters',["name","type","defValue"])
    assert set(defaults)<={p["name"] for p in data},data
    dump("oa/sar8a_plant_cdf.json",data);print("CDF_OK",flush=True)


def sources(c):
    c.add("VVDD","vdc",{"PLUS":"VDD","MINUS":"gnd!"},"analogLib",vdc="SUP")
    for name,delay,width,period,v0,v1 in (
        ("RST_N","2n","1m","2m","0","SUP"),
        ("SAMPLE","1n","40n","100n","0","SUP"),
        ("HOLD_START","43n","500p","100n","0","SUP"),
        ("DEADLINE","89n","500p","100n","0","SUP"),
        ("PREPARE","90n","10n","100n","0","SUP")):
        c.add("VSRC_"+name,"vpulse",{"PLUS":name,"MINUS":"gnd!"},"analogLib",
              v1=v0,v2=v1,td=delay,pw=width,per=period,tr="20p",tf="20p")
    c.add("VVIN","vdc",{"PLUS":"VIN","MINUS":"gnd!"},"analogLib",vdc="VIN_DIFF")


def logic_bench(strongarm=False):
    c=Cell("tb_sar8a_strongarm" if strongarm else "tb_sar8a_logic",[],[]);sources(c)
    dut=hierarchy()[-1]
    c.add("XCTRL",dut.name,{p:("gnd!" if p=="VSS" else p) for p in dut.inputs+dut.outputs})
    pins={p:p for p in PLANT_IN+PLANT_OUT}
    pins.update(VSS="gnd!")
    pins.update({f"C{i}":f"CODE{i}" for i in range(8)})
    pins.update(P="MODEL_P" if strongarm else "COMP_P",N="MODEL_N" if strongarm else "COMP_N")
    c.add("XPLANT","sar8a_plant",pins,pattern_mode="PATTERN_MODE",pattern_word="PATTERN_WORD",
          fault_mode="FAULT_MODE",fault_bit="FAULT_BIT",fault_frame="FAULT_FRAME",min_delay_s="COMP_DELAY",delay_spread_s="DELAY_SPREAD")
    if strongarm:
        c.add("XCOMP","sar_strongarm_t28",{"CLK":"CMP_CLK","VINP":"TOPP","VINN":"TOPN",
              "OUTP":"COMP_P","OUTN":"COMP_N","VDD":"VDD","VSS":"gnd!"})
    nets=set(dut.outputs+PLANT_OUT+["MODEL_P","MODEL_N"] if strongarm else dut.outputs+PLANT_OUT)
    # Correct names after mapping plant outputs to comparator rails.
    nets.discard("P");nets.discard("N");nets.update(("COMP_P","COMP_N"))
    for i,net in enumerate(sorted(nets)):
        c.add(f"RMON{i:02d}","res",{"PLUS":net,"MINUS":"gnd!"},"analogLib",r="1T")
        if net.startswith(("D0","D1","D2","D3","D4","D5","D6","D7","SEL")) or net in ("CMP_CLK","COMP_P","COMP_N","BUSY","VALID","FAULT"):
            c.add(f"CLOAD{i:02d}","cap",{"PLUS":net,"MINUS":"gnd!"},"analogLib",c="5f" if net.startswith("D") or net in ("BUSY","VALID","FAULT") else "10f")
    return c


def gate_bench():
    c=Cell("tb_sar8a_gates",[],[])
    c.add("VVDD","vdc",{"PLUS":"VDD","MINUS":"gnd!"},"analogLib",vdc="SUP")
    for name,delay,width,period in (("A","2n","4n","6n"),("B","3n","2n","7n"),("CK","4n","1n","2n"),("RST","0","1n","30n")):
        c.add("VSRC_"+name,"vpulse",{"PLUS":name,"MINUS":"gnd!"},"analogLib",v1="0",v2="SUP",td=delay,pw=width,per=period,tr="20p",tf="20p")
    for role in ("dac","valid","capture","reset","advance","publish","bbm"):
        c.add("XD_"+role,"sar8a_delay_"+role,{"A":"A","Y":"Y_"+role,"VDD":"VDD","VSS":"gnd!"})
        c.add("CL_"+role,"cap",{"PLUS":"Y_"+role,"MINUS":"gnd!"},"analogLib",c="5f")
    c.add("XFF","sar8a_dffr",{"D":"B","CK":"CK","RST":"RST","Q":"Q","VDD":"VDD","VSS":"gnd!"})
    c.add("CLQ","cap",{"PLUS":"Q","MINUS":"gnd!"},"analogLib",c="5f")
    return c


def main():
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["plant","refresh-plant","cdf","gates","logic","strongarm"])
    ap.add_argument("--rebuild-owned",action="store_true");ap.add_argument("--resume-plant",action="store_true");args=ap.parse_args()
    c=VirtuosoClient.from_env(profile="t28_io")
    if args.command=="plant":plant(c,args.resume_plant)
    elif args.command=="refresh-plant":
        assert exists(c,"sar8a_plant","veriloga")
        c.upload_file(ROOT/"models/veriloga/sar8a_plant.va",c.library.get(LIB).path+"/sar8a_plant/veriloga/veriloga.va")
        r=c.execute_skill(f'ahdlUpdateViewInfo("{LIB}" ?cell "sar8a_plant" ?view "veriloga")');assert not r.errors,r
        plant_cdf(c)
    elif args.command=="cdf":plant_cdf(c)
    else:build(c,gate_bench() if args.command=="gates" else logic_bench(args.command=="strongarm"),args.rebuild_owned)


if __name__=="__main__":main()
