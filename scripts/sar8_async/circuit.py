"""Declarative native-CMOS hierarchy shared by OA construction and audits.

No behavioral logic devices are used. All logic leaves are T28 MOS; delay
leaves use ordinary R/C plus the same MOS inverters.
"""
from __future__ import annotations
from dataclasses import dataclass, field

LIB = "SAR_ADC_T28"


@dataclass
class Part:
    name: str
    master: str
    terms: dict[str, str]
    lib: str = LIB
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class Cell:
    name: str
    inputs: list[str]
    outputs: list[str]
    parts: list[Part] = field(default_factory=list)

    def add(self, name, master, terms, lib=LIB, **params):
        assert name not in {p.name for p in self.parts}, (self.name, name)
        self.parts.append(Part(name, master, terms, lib, params))
        return name

    def g(self, master, output, *args, name=None):
        pins = ["A", "B"] if len(args) == 2 else ["A"]
        self.add(name or f"X{len(self.parts):03d}", "sar8a_"+master,
                 dict(zip(pins, args)) | {"Y":output, "VDD":"VDD", "VSS":"VSS"})
        return output

    def sr(self, name, s, r, q):
        self.add(name, "sar8a_sr", {"S":s,"R":r,"Q":q,"VDD":"VDD","VSS":"VSS"})

    def ff(self, name, d, ck, rst, q):
        self.add(name,"sar8a_dffr",{"D":d,"CK":ck,"RST":rst,"Q":q,"VDD":"VDD","VSS":"VSS"})

    def delay(self, role, source, target):
        self.add("XD_"+target,"sar8a_delay_"+role,
                 {"A":source,"Y":target,"VDD":"VDD","VSS":"VSS"})


def logic_cells():
    cells=[]
    def mos(c, name, kind, d,g,s,b,w):
        c.add(name,kind,{"D":d,"G":g,"S":s,"B":b},"tsmcN28",
              Wfg=w,l="30n",fingers="1",simM="1")
    c=Cell("sar8a_inv",["A","VDD","VSS"],["Y"])
    mos(c,"MP","pch_mac","Y","A","VDD","VDD","1u")
    mos(c,"MN","nch_mac","Y","A","VSS","VSS","500n");cells.append(c)
    c=Cell("sar8a_nand2",["A","B","VDD","VSS"],["Y"])
    for i,g in enumerate(("A","B")):mos(c,f"MP{i}","pch_mac","Y",g,"VDD","VDD","1u")
    mos(c,"MN0","nch_mac","Y","A","MID","VSS","1u")
    mos(c,"MN1","nch_mac","MID","B","VSS","VSS","1u")
    # Deliberate schematic loading, not simulator cmin: bound clock
    # feedthrough on the otherwise floating stack node. Area/power/layout
    # cost remains explicit and is not an optimized standard-cell claim.
    c.add("CMID","cap",{"PLUS":"MID","MINUS":"VSS"},"analogLib",c="10f")
    cells.append(c)
    c=Cell("sar8a_nor2",["A","B","VDD","VSS"],["Y"])
    # Avoid the floating stacked-PMOS middle node that failed SOA on
    # redundant SAMPLE/SYS_RST transitions in the first full-loop run.
    c.g("inv","AB","A");c.g("inv","BB","B")
    c.g("nand2","OR","AB","BB");c.g("inv","Y","OR")
    cells.append(c)
    for kind,first in (("and2","nand2"),("buf","inv")):
        c=Cell("sar8a_"+kind,["A"]+([] if kind=="buf" else ["B"])+["VDD","VSS"],["Y"])
        c.g(first,"N","A",*([] if kind=="buf" else ["B"]));c.g("inv","Y","N");cells.append(c)
    c=Cell("sar8a_or2",["A","B","VDD","VSS"],["Y"])
    c.g("inv","AB","A");c.g("inv","BB","B");c.g("nand2","Y","AB","BB");cells.append(c)
    c=Cell("sar8a_xor2",["A","B","VDD","VSS"],["Y"])
    c.g("nand2","N","A","B");c.g("nand2","NA","A","N")
    c.g("nand2","NB","B","N");c.g("nand2","Y","NA","NB");cells.append(c)
    c=Cell("sar8a_mux2",["D0","D1","SEL","VDD","VSS"],["Y"])
    c.g("inv","SB","SEL");c.g("nand2","N0","D0","SB")
    c.g("nand2","N1","D1","SEL");c.g("nand2","Y","N0","N1");cells.append(c)
    c=Cell("sar8a_sr",["S","R","VDD","VSS"],["Q"])
    c.g("inv","RB","R");c.g("nand2","SN","S","RB")
    c.g("nand2","Q","SN","QB");c.g("nand2","QB","RB","Q")
    c.add("CQB","cap",{"PLUS":"QB","MINUS":"VSS"},"analogLib",c="5f")
    cells.append(c)
    c=Cell("sar8a_dffr",["D","CK","RST","VDD","VSS"],["Q"])
    # 24-MOS static transmission-gate master/slave DFF. Each latch is
    # NAND(storage,RST_N)->INV with clock-selected input/feedback TGs.
    # Asserting reset forces both latch outputs low for either CK level.
    c.g("inv","CKB","CK");c.g("inv","RN","RST")
    def tg(stem,a,b,en,enb):
        mos(c,"MN_"+stem,"nch_mac",b,en,a,"VSS","1u")
        mos(c,"MP_"+stem,"pch_mac",b,enb,a,"VDD","2u")
    tg("MI","D","M","CKB","CK");tg("MF","MQ","M","CK","CKB")
    c.g("nand2","MB","M","RN");c.g("inv","MQ","MB")
    tg("SI","MQ","S","CK","CKB");tg("SF","Q","S","CKB","CK")
    c.g("nand2","SB","S","RN");c.g("inv","Q","SB")
    for net in ("M","S"):
        c.add("CSTORE_"+net,"cap",{"PLUS":net,"MINUS":"VSS"},"analogLib",c="5f")
    cells.append(c)
    # Seed R/C, to be measured under actual native input/output loads.
    for role,cap in {"dac":"200f","valid":"5f","capture":"8f","reset":"33f",
                     "advance":"8f","publish":"12f","bbm":"5f"}.items():
        c=Cell("sar8a_delay_"+role,["A","VDD","VSS"],["Y"])
        for n,inp,node,out in (("0","A","RC0","B"),("1","B","RC1","Y")):
            c.add("R"+n,"res",{"PLUS":inp,"MINUS":node},"analogLib",r="10k")
            c.add("C"+n,"cap",{"PLUS":node,"MINUS":"VSS"},"analogLib",c=cap)
            c.g("inv",out,node)
        # Fast return-to-zero is essential: an ordinary transport/RC chain
        # retains charge across short comparator/reset phases and can wrongly
        # report the next DAC trial settled. These clamps actively reset both
        # RC nodes whenever A=0, without an ideal timer or switch.
        c.g("inv","AB","A")
        mos(c,"MN_CLEAR","nch_mac","RC0","AB","VSS","VSS","2u")
        mos(c,"MP_CLEAR","pch_mac","RC1","A","VDD","VDD","3u")
        cells.append(c)
    c=Cell("sar8a_bbm",["CODE","HOLD","VDD","VSS"],["SEL0","SEL1"])
    c.g("inv","CB","CODE");c.g("and2","R1","CODE","HOLD")
    c.g("and2","R0","CB","HOLD")
    for bit in (0,1):
        c.delay("bbm",f"R{bit}",f"RD{bit}");c.g("and2",f"SEL{bit}",f"R{bit}",f"RD{bit}")
    cells.append(c)
    return cells


def controller_cells():
    cells=[]
    c=Cell("sar8a_frame",["RST_N","SAMPLE","HOLD_START","PREPARE","DEADLINE","FAULT","VDD","VSS"],
           ["SYS_RST","WORK_RST","ACCEPT","HOLD","KILL"])
    c.g("inv","SYS_RST","RST_N");c.g("or2","WORK_RST","SYS_RST","SAMPLE")
    c.delay("valid","HOLD_START","START_D")
    c.sr("XUSED","START_D","WORK_RST","USED");c.g("inv","UNUSED","USED")
    c.g("or2","B0","WORK_RST","PREPARE");c.g("or2","B1","B0","DEADLINE")
    c.g("inv","ALLOW","B1");c.g("and2","A0","HOLD_START","UNUSED")
    c.g("and2","ACCEPT","A0","ALLOW")
    # Deadline aborts through the fault/status path only while conversion is
    # uncommitted; a successful frame keeps reference ownership to PREPARE.
    c.g("or2","B2","B0","FAULT");c.sr("XHOLD","ACCEPT","B2","HOLD")
    c.g("inv","KILL","HOLD");cells.append(c)
    c=Cell("sar8a_cmp_if",["P","N","EVAL","CMP_CLK","KILL","VDD","VSS"],
           ["DATA","DEC_VALID","RESET_OK","BAD"])
    c.g("buf","PR","P");c.g("buf","NR","N");c.g("inv","NRB","NR")
    c.g("and2","DATA","PR","NRB");c.g("xor2","RV","PR","NR")
    c.delay("valid","RV","RV_D");c.g("and2","VQ","RV","RV_D")
    c.g("inv","LIVE","KILL");c.g("and2","ARMED","LIVE","EVAL")
    c.g("and2","DEC_VALID","VQ","ARMED")
    c.g("nor2","ILL","PR","NR");c.delay("valid","ILL","ILL_D")
    c.g("and2","IQ","ILL","ILL_D");c.g("and2","BAD","IQ","ARMED")
    c.g("inv","CR","CMP_CLK");c.delay("reset","CR","CR_D")
    c.g("and2","RP","PR","NR");c.g("and2","RQ","CR","CR_D")
    c.g("and2","RESET_OK","RQ","RP");cells.append(c)
    c=Cell("sar8a_seq",["ACCEPT","KILL","DEC_VALID","RESET_OK","LAST","VDD","VSS"],
           ["TRIAL","EVAL","CAPTURE","RESET","ADVANCE","PUBLISH","CMP_CLK"])
    c.g("inv","LIVE","KILL");c.delay("dac","TRIAL","TD")
    c.g("and2","TQ","TRIAL","TD");c.g("and2","ES0","TQ","RESET_OK")
    c.g("and2","ES","ES0","LIVE")
    c.g("or2","ER","KILL","CAPTURE");c.sr("XEVAL","ES","ER","EVAL")
    c.g("and2","CS","EVAL","DEC_VALID")
    c.g("or2","CAP_R","KILL","RESET");c.sr("XCAP","CS","CAP_R","CAPTURE")
    c.delay("capture","CAPTURE","CAP_D");c.g("and2","RS","CAPTURE","CAP_D")
    c.g("or2","RR0","TRIAL","PUBLISH");c.g("or2","RR","RR0","KILL")
    c.sr("XRESET","RS","RR","RESET")
    c.g("and2","ADVANCE","RESET","RESET_OK");c.delay("advance","ADVANCE","ADV_D")
    c.g("and2","ADV_Q","ADVANCE","ADV_D");c.g("inv","NOTLAST","LAST")
    c.g("and2","NEXT","ADV_Q","NOTLAST");c.g("or2","TS","ACCEPT","NEXT")
    c.g("or2","TR","KILL","EVAL");c.sr("XTRIAL","TS","TR","TRIAL")
    c.g("and2","FIN_S","ADV_Q","LAST");c.sr("XFIN","FIN_S","KILL","PUBLISH")
    c.g("inv","CAP_LOW","CAPTURE");c.g("and2","RESET_SAFE","RESET","CAP_LOW")
    c.g("or2","CMP_R","KILL","RESET_SAFE");c.sr("XCLOCK","EVAL","CMP_R","CMP_CLK")
    cells.append(c)
    c=Cell("sar8a_token8",["ADVANCE","WORK_RST","VDD","VSS"],[f"T{i}" for i in range(7,-1,-1)])
    c.ff("XF7","VDD","ADVANCE","WORK_RST","NT7");c.g("inv","T7","NT7")
    for i in range(6,-1,-1):c.ff(f"XF{i}",f"T{i+1}","ADVANCE","WORK_RST",f"T{i}")
    cells.append(c)
    c=Cell("sar8a_bit",["TOKEN","DATA","CAPTURE","WORK_RST","VDD","VSS"],["W","CODE"])
    c.add("XMUX","sar8a_mux2",{"D0":"W","D1":"DATA","SEL":"TOKEN","Y":"DN","VDD":"VDD","VSS":"VSS"})
    c.ff("XFF","DN","CAPTURE","WORK_RST","W");c.g("or2","CODE","W","TOKEN");cells.append(c)
    c=Cell("sar8a_out8",[f"W{i}" for i in range(7,-1,-1)]+["PUBLISH","SYS_RST","VDD","VSS"],
           [f"D{i}" for i in range(7,-1,-1)])
    for i in range(8):c.ff(f"XOUT{i}",f"W{i}","PUBLISH","SYS_RST",f"D{i}")
    cells.append(c)
    c=Cell("sar8a_status",["SAMPLE","PREPARE","DEADLINE","BAD","PUBLISH","ACCEPT","SYS_RST","WORK_RST","VDD","VSS"],
           ["BUSY","VALID","FAULT","COMMIT"])
    c.g("or2","VR","WORK_RST","FAULT")
    c.g("or2","NO_COMMIT","DEADLINE","FAULT");c.g("inv","COMMIT_ALLOWED","NO_COMMIT")
    c.g("and2","COMMIT_SET","PUBLISH","COMMIT_ALLOWED");c.sr("XCOMMIT","COMMIT_SET","VR","COMMIT")
    c.delay("publish","COMMIT","PUB_D");c.g("and2","VS","COMMIT","PUB_D")
    c.sr("XVALID","VS","VR","VALID")
    # Independent transaction state avoids a false BUSY pulse when SAMPLE
    # clears COMMIT before the reference HOLD latch has propagated low.
    # It also remembers an interrupted transaction long enough to record FAULT.
    c.g("or2","AR0","COMMIT","SYS_RST");c.g("or2","AR","AR0","FAULT")
    c.sr("XACTIVE","ACCEPT","AR","BUSY")
    c.g("or2","A0","SAMPLE","PREPARE");c.g("or2","A1","BAD","DEADLINE")
    c.g("or2","A2","A0","A1");c.g("and2","FS","A2","BUSY")
    # Clear the previous frame's fault during acquisition, before ACCEPT.
    # Clearing only on ACCEPT races the reset-priority reference HOLD latch:
    # the short start pulse can expire before old FAULT releases HOLD reset.
    c.g("or2","FR","WORK_RST","ACCEPT");c.sr("XFAULT","FS","FR","FAULT");cells.append(c)
    outputs=[f"D{i}" for i in range(7,-1,-1)]+[f"SEL{q}_{i}" for q in (0,1) for i in range(7,-1,-1)]
    outputs += [f"CODE{i}" for i in range(7,-1,-1)]+["BASE","BUSY","VALID","FAULT","CMP_CLK","CMP_RESET","CAPTURE","ADVANCE","PUBLISH"]
    c=Cell("sar_logic_8b_async",["RST_N","SAMPLE","HOLD_START","PREPARE","DEADLINE","COMP_P","COMP_N","VDD","VSS"],outputs)
    def child(name,master,mapping):
        obj=next(a for a in cells if a.name==master)
        c.add(name,master,{p:mapping.get(p,p) for p in obj.inputs+obj.outputs})
    child("XFRAME","sar8a_frame",{})
    child("XCMPIF","sar8a_cmp_if",{"P":"COMP_P","N":"COMP_N"})
    child("XSEQ","sar8a_seq",{});child("XTOKEN","sar8a_token8",{})
    c.ff("XLAST","T0","CAPTURE","WORK_RST","LAST")
    for i in range(8):
        child(f"XBIT{i}","sar8a_bit",{"TOKEN":f"T{i}","W":f"W{i}","CODE":f"CODE{i}"})
        c.add(f"XBBM{i}","sar8a_bbm",{"CODE":f"CODE{i}","HOLD":"HOLD",f"SEL0":f"SEL0_{i}",f"SEL1":f"SEL1_{i}","VDD":"VDD","VSS":"VSS"})
    c.add("XBASE","sar8a_bbm",{"CODE":"VSS","HOLD":"HOLD","SEL0":"BASE","SEL1":"BASE_UNUSED","VDD":"VDD","VSS":"VSS"})
    c.add("RBASE","res",{"PLUS":"BASE_UNUSED","MINUS":"VSS"},"analogLib",r="1T")
    for net in ("TRIAL","RESET"):
        c.add("RMON_"+net,"res",{"PLUS":net,"MINUS":"VSS"},"analogLib",r="1T")
    child("XOUT","sar8a_out8",{"PUBLISH":"COMMIT"});child("XSTATUS","sar8a_status",{})
    c.g("inv","CMP_RESET","CMP_CLK");cells.append(c)
    return cells


def hierarchy():
    return logic_cells()+controller_cells()
