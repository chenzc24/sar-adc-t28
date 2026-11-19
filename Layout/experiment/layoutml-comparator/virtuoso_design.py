"""Build the experimental comparator directly with native Virtuoso SKILL."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TOP="sar_strongarm_lml_exp"
LIB="SAR_ADC_T28_LAYOUT"
SOURCE=ROOT/"design/xtor/comparator/comparator.scs"


def electrical():
    text=SOURCE.read_text(encoding="utf-8")
    ports=re.search(r"^subckt sar_strongarm_t28 (.+)$",text,re.M)[1].split()
    devices={}
    cdl=["* Electrical source SHA256 "+hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         ".SUBCKT "+TOP+" "+" ".join(ports)]
    for name,nodes,model,length,width,mult,nf in re.findall(
        r"^\s*(M\w+) \(([^)]+)\) (\w+) l=(\S+) w=(\S+) multi=(\d+) nf=(\d+)",text,re.M):
        assert (length,mult,nf)==("30n","1","1")
        devices[name] = (model,{"500n":500,"1u":1000}[width],nodes.split())
        cdl.append(f"{name} {nodes} {model} L={length} W={width}")
    assert len(devices)==11
    return ports,devices,"\n".join(cdl+[".ENDS "+TOP,""])


def physical_devices(circuit):
    devices=dict(circuit)
    model,width,terminals=devices.pop("MNTAIL")
    assert width==1000 and terminals==["TAIL","CLK","VSS","VSS"]
    for name in ("MNTAIL_L","MNTAIL_R"):
        devices[name]=(model,width//2,terminals)
    return devices


class NativeLayout:
    def __init__(self, circuit):
        self.circuit=circuit
        self.operations=[]
        self.instances={}
        self.routes=[]
        self.ports={}

    def rect(self, layer, net, x1,y1,x2,y2, purpose="drawing"):
        assert x1<x2 and y1<y2 and all(v%5==0 for v in (x1,y1,x2,y2))
        n=f'"{net}"' if net else "nil"
        self.operations.append(f'saRect(cv "{layer}" "{purpose}" {n} {x1} {y1} {x2} {y2})')

    def h(self, metal,net,y,x1,x2,width):
        self.rect(metal,net,min(x1,x2),y-width//2,max(x1,x2),y+width//2)
        self.routes.append((net,metal,"H",y,min(x1,x2),max(x1,x2)))

    def v(self, metal,net,x,y1,y2,width):
        self.rect(metal,net,x-width//2,min(y1,y2),x+width//2,max(y1,y2))
        self.routes.append((net,metal,"V",x,min(y1,y2),max(y1,y2)))

    def via(self,model,x,y,enc1,enc2,rows=1,cols=1,space=90):
        params=(f'list(list("layer1Enc" saPt{tuple(enc1)}) list("layer2Enc" saPt{tuple(enc2)}) '
                f'list("cutRows" {rows}) list("cutColumns" {cols}) list("cutSpacing" saPt({space} {space})))')
        self.operations.append(f'saVia(cv "{model}" {x} {y} {params.replace(",","")})')

    def mos(self,name,gx,y,left_net,right_net,side,left="normal",right="normal"):
        model,width,nodes=self.circuit[name]
        drain,gate,source,body=nodes
        assert {left_net,right_net}=={source,drain}
        assert name not in self.instances
        ori="R0" if left_net==source else "MY"
        nets=" ".join(f'"{n}"' for n in nodes)
        self.operations.append(f'saMos(cv "{name}" "{model}" {width} {gx} {y} "{ori}" '
                               f'"{left}" "{right}" "{side}" list({nets}))')
        self.instances[name]=dict(model=model,width=width,gate_center_nm=[gx,y+width//2],
                                  box_nm=[gx-15,y,gx+15,y+width],gate=gate,orientation=ori,
                                  source=source,drain=drain,body=body,ends=[left,right],gate_side=side)

    def pin(self,name,metal,x,y,width,height):
        direction="input" if name in ("CLK","VINN","VINP") else "output" if name.startswith("OUT") else "inputOutput"
        self.operations.append(f'saPin(cv "{name}" "{metal}" {x} {y} {width} {height} "{direction}")')
        self.ports[name]=[metal,x,y,width,height]

    def substrate_ring(self,left,bottom,right,top):
        for layer,half in (("OD",50),("PP",115),("M1",35)):
            net="VSS" if layer=="M1" else None
            self.rect(layer,net,left-half,bottom-half,right+half,bottom+half)
            self.rect(layer,net,left-half,top-half,right+half,top+half)
            for x in (left,right):
                self.rect(layer,net,x-half,bottom+half,x+half,top-half)
        # Include corners once. Keep every side continuously tapped.
        from math import ceil
        def centers(lo,hi):
            count=ceil((hi-lo)/165)
            return [5*round((lo+i*(hi-lo)/count)/5) for i in range(count+1)]
        for y in (bottom,top):
            for x in centers(left,right):self.rect("CO",None,x-20,y-20,x+20,y+20)
        for x in (left,right):
            for y in centers(bottom,top)[1:-1]:self.rect("CO",None,x-20,y-20,x+20,y+20)


def layout(circuit):
    a=NativeLayout(circuit)
    # One Euler chain in a common well: X VDD OUTP VDD OUTN VDD Y.
    py=1550
    p_gates=["MPRSTX","MPLATP","MPRSTP","MPRSTN","MPLATN","MPRSTY"]
    p_nets=["X","VDD","OUTP","VDD","OUTN","VDD","Y"]
    for i,name in enumerate(p_gates):
        gx=-325+i*130
        a.mos(name,gx,py,p_nets[i],p_nets[i+1],"Bottom" if "LAT" in name else "Top",
              "normal" if i==0 else "same","normal" if i==5 else "same")
    for x in (-260,-130,0,130,260):
        a.via("M1_OD",x,py+250,(5,35),(5,35),rows=4)
    # Abut each latch to its input at the width transition. The wider device
    # supplies the one native S/D contact array at this boundary.
    a.mos("MNLATP",-195,500,"OUTP","X","Top","normal","small")
    a.mos("MNINN",-65,0,"X","TAIL","Bottom","largeExt","same")
    a.mos("MNINP",65,0,"TAIL","Y","Bottom","same","largeExt")
    a.mos("MNLATN",195,500,"Y","OUTN","Top","small","normal")
    a.via("M1_OD",0,500,(5,25),(5,25),rows=8)
    a.mos("MNTAIL_L",-585,0,"VSS","TAIL","Top")
    a.mos("MNTAIL_R",585,0,"TAIL","VSS","Top")
    # Complete the pitch seen by the exposed portion of the 1 um input
    # diffusion. The 0.5 um latch gates continue only over field oxide.
    for sign in (-1,1):
        gx=sign*195
        a.rect("PO",None,gx-15,-80,gx+15,500)
        dx=sign*325
        a.rect("PO",None,dx-15,-60,dx+15,500,"dummy1")
    # Continuous well / implant coverage for the row, separate from density fill.
    a.rect("NP",None,-770,-250,770,1275)
    a.rect("PP",None,-500,1275,500,2295)
    a.rect("PM",None,-715,1255,715,2340,"drawing1")
    a.rect("NW",None,-610,1275,610,2575)
    a.rect("NP",None,-315,2325,315,2525)
    a.via("M1_NW",0,2425,(35,35),(35,15),cols=4,space=90)
    a.substrate_ring(-970,-385,970,2770)
    for sign in (-1,1):
        a.h("M1","VSS",345,sign*970,sign*625,70)
    a.via("M2_M1",-970,345,(10,30),(25,25))
    a.v("M2","VSS",-970,235,455,100)
    a.pin("VSS","M2",-970,345,100,120)
    a.via("M2_M1",0,2425,(30,10),(15,30))
    a.v("M2","VDD",0,1905,2480,80)
    a.h("M2","VDD",1960,-775,315,100)
    for x in (-260,0,260):a.via("M2_M1",x,1960,(0,30),(30,25))
    a.pin("VDD","M2",-720,1960,100,100)
    # Each half connects straight to its end of the reset clock rail.
    for x in (-585,585):
        a.v("M1","CLK",x,560,2210,70)
    a.h("M1","CLK",2160,-620,695,100)
    a.via("M2_M1",640,2160,(30,25),(25,25))
    a.h("M2","CLK",2160,585,930,100)
    a.pin("CLK","M2",865,2160,100,100)
    a.h("M2","TAIL",235,-575,575,100)
    for x in (-520,0,520):a.via("M2_M1",x,235,(0,30),(30,25))
    for sign,input_net,decision,drain_net,cross_gate in (
            (-1,"VINN","X","OUTP","OUTN"),(1,"VINP","Y","OUTN","OUTP")):
        gx=sign*65
        a.v("M1",input_net,gx,-275,-60,70)
        a.via("M2_M1",gx,-180,(10,30),(5,30))
        a.v("M2",input_net,gx,-445,-125,60)
        a.pin(input_net,"M2",gx,-405,60,80)
        # X and Y leave their shared diffusion on M2 and return to M1 directly
        # in line with the PMOS end diffusion.
        a.v("M1",decision,sign*390,595,1600,50)
        a.h("M2",decision,650,sign*130-sign*55,sign*390+sign*55,100)
        for x in (sign*130,sign*390):a.via("M2_M1",x,650,(0,30),(30,25))
        # Side drain strap. The opposite gates join partway along the existing
        # output rail, without an excursion to the opposite outer edge.
        dn,np=sign*260,sign*130
        a.via("M2_M1",dn,905,(0,30),(15,30))
        a.v("M2",drain_net,dn,850,1530,80)
        a.h("M2",drain_net,1490,min(dn,np)-40,max(dn,np)+40,80)
        a.v("M2",drain_net,np,1450,1765,80)
        a.via("M2_M1",np,1710,(0,30),(15,30))
        y=1190 if drain_net=="OUTP" else 1360
        # Close the feedback on the metal already carrying this side's drain.
        # Export each signal at that junction; no drain-to-M3 detour is needed.
        a.h("M2",drain_net,y,min(-55,dn-40),max(55,dn+40),80)
        # The east-going pair crosses only one half of the core. Move that
        # shared escape corridor above the local feedback and input conductors.
        a.h("M3",drain_net,y,-110,110,80)
        a.via("M4_M3",0,y,(30,10),(25,25))
        a.h("M4",drain_net,y,-55,930,100)
        a.pin(drain_net,"M4",865,y,100,100)
        gate=sign*195
        yy=1360 if cross_gate=="OUTN" else 1190
        a.v("M1",cross_gate,gate,1060,1490,70)
        a.h("M1",cross_gate,yy,min(0,gate)-(55 if gate>0 else 35),max(0,gate)+(55 if gate<0 else 35),70)
        a.via("M2_M1",0,yy,(30,10),(30,10))
        a.via("M3_M2",0,yy,(30,10),(25,25))
    return a


def generate(out,predecessor):
    ports,circuit,cdl=electrical()
    physical=physical_devices(circuit)
    a=layout(physical)
    assert set(physical)==set(a.instances) and set(ports)==set(a.ports)
    wanted=hashlib.sha256((HERE/"virtuoso_core.il").read_bytes()+Path(__file__).read_bytes()).hexdigest()
    text=(HERE/"virtuoso_core.il").read_text(encoding="utf-8")
    start=[text,'procedure(saBuild() let((cv)',
           f'cv=dbOpenCellViewByType("{LIB}" "{TOP}" "layout" "maskLayout" "w")',
           'unless(cv error("Cannot open experimental cell"))',
           f'dbReplaceProp(cv "saNativeSource" "string" "{wanted}")']
    for n in sorted({k for _,_,nodes in circuit.values() for k in nodes}):start.append(f'dbMakeNet(cv "{n}")')
    finish=['unless(dbSave(cv) error("Failed to save native cell")) dbClose(cv)',
            f'printf("LML_OA_SAVED {TOP}\\n") t))','if(errset(saBuild() t) then exit(0) else exit(1))']
    check=['procedure(saCheck() let((cv fp inst tmp)',
           f'cv=dbOpenCellViewByType("{LIB}" "{TOP}" "layout" "" "r")',
           f'unless(cv && equal(cv~>saNativeSource "{wanted}") error("Changed source identity"))',
           f'unless(length(cv~>instances)=={len(physical)} && length(cv~>terminals)==7 error("OA interface"))',
           'fp=outfile(strcat(getShellEnvVar("LML_RUN_PATH") "/readback.txt"))']
    for n,instr in a.instances.items():
        x,y=instr["box_nm"][:2]
        x+=30 if instr["orientation"]=="MY" else 0
        check.extend([f'inst=dbFindAnyInstByName(cv "{n}")',
           f'unless(inst && inst~>libName=="tsmcN28" && inst~>cellName=="{instr["model"]}" && inst~>orient=="{instr["orientation"]}" && equal(inst~>xy list({x/1000:.4f} {y/1000:.4f})) error("MOS {n}"))',
           'unless(length(inst~>instTerms)==4 error("MOS ports"))',
           'foreach(sh inst~>master~>shapes when(sh~>purpose=="error" error("PCell error")))',
           'foreach(it inst~>instTerms fprintf(fp "IT %s %s %s\\n" inst~>name it~>name it~>net~>name))',
           'fprintf(fp "MOS %s %s %s %L\\n" inst~>name inst~>cellName inst~>orient inst~>xy)',
           'foreach(trm inst~>master~>terminals when(trm~>name=="G" foreach(p trm~>pins foreach(f p~>figs when(f~>layerName=="M1" fprintf(fp "GATE_M1 %s %L\\n" inst~>name dbTransformBBox(f~>bBox inst~>transform)))))))'])
    check+=['foreach(tn cv~>terminals foreach(p tn~>pins foreach(f p~>figs fprintf(fp "PORT %s %s %L\\n" tn~>name f~>layerName f~>bBox))))',
            'fprintf(fp "NATIVE_VIAS %d\\n" length(cv~>vias)) close(fp) dbClose(cv)',
            f'printf("LML_OA_READBACK {TOP}\\n") t))','if(errset(saCheck() t) then exit(0) else exit(1))']
    files={"build.il":"\n".join(start+a.operations+finish)+"\n","readback.il":"\n".join(check)+"\n","reference.cdl":cdl}
    out.mkdir(exist_ok=True,parents=True)
    for n,v in files.items():(out/n).write_bytes(v.encode("ascii"))
    data={"mode":"native-cdf","top":TOP,"library":LIB,"owned_predecessor":predecessor,"native_sha256":wanted,
          "electrical_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          "files":{n:hashlib.sha256(v.encode("ascii")).hexdigest() for n,v in files.items()}}
    for n,val in (("source.json",data),("intent.json",{"mos":a.instances,"ports":a.ports,"wires":a.routes})):
        (out/n).write_text(json.dumps(val,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--predecessor",required=True)
    args=p.parse_args()
    generate(args.out,args.predecessor)
