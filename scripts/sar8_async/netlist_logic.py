"""Event-level functional simulation of the ACTUAL exported native hierarchy.

Not a transistor simulator: native INV/NAND truth is audited as ideal MOS
switch connectivity; native SR/DFF cells are state abstractions and delays
are measured-fixture abstractions. This complements, never replaces, Spectre.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import heapq
import itertools
import json
import re
from oa import OUT,dump
from simulate import source


def parse(text):
    text=re.sub(r"\\\n\s*"," ",text)
    blocks={}
    for m in re.finditer(r"(?ms)^subckt (\w+) ([^\n]+)\n(.*?)^ends \1",text):
        devices=[]
        for name,pins,master in re.findall(r"(?m)^\s*(\w+) \(([^)]+)\) (\w+)",m[3]):
            devices.append((name,pins.split(),master))
        blocks[m[1]]=(m[2].split(),devices)
    assert "sar_logic_8b_async" in blocks
    return blocks


def audit_mos_truth(blocks):
    for name,nin in (("sar8a_inv",1),("sar8a_nand2",2)):
        ports,devices=blocks[name]
        for values in itertools.product((0,1),repeat=nin):
            fixed={"A":values[0],"VDD":1,"VSS":0}
            if nin==2:fixed["B"]=values[1]
            parent={x:x for _,pins,_ in devices for x in pins}
            def root(x):
                while parent[x]!=x:x=parent[x]
                return x
            for _,pins,model in devices:
                if model not in ("nch_mac","pch_mac"):continue
                d,g,s,b=pins;assert b==("VSS" if model=="nch_mac" else "VDD")
                assert g in fixed
                if fixed[g]==(1 if model=="nch_mac" else 0):parent[root(d)]=root(s)
            rails={fixed[k] for k in ("VDD","VSS") if root(k)==root("Y")}
            want=1-int(all(values))
            assert rails=={want},(name,values,rails,want)


@dataclass
class Primitive:
    kind: str
    nets: dict
    version: int=0
    clock: int=0
    state: int=0


class NetlistEngine:
    def __init__(self,text):
        self.blocks=parse(text);audit_mos_truth(self.blocks)
        self.parts=[];self.listeners={};self.v={"VDD":1,"VSS":0}
        self.q=[];self.serial=0;self.time=0.;self.trace=[];self.epoch=0;self.eval_index=0
        self.word=0;self.fault_bit=-1;self.fault_mode=0
        measured=json.loads((OUT/"analysis/tgdff_gates_tt.json").read_text(encoding="utf-8"))["delays"]
        self.delays={k:v["maximum_ns"] for k,v in measured.items()}
        top="sar_logic_8b_async";ports,_=self.blocks[top]
        self.expand(top,{p:p for p in ports},"XCTRL")
        self.v.update({n:0 for p in self.parts for n in p.nets.values() if n not in self.v})
        for i,p in enumerate(self.parts):
            for n in set(p.nets.values()):self.listeners.setdefault(n,[]).append(i)
        for i in range(len(self.parts)):self.evaluate(i)

    def expand(self,name,mapping,path):
        ports,devices=self.blocks[name]
        atomic=name in ("sar8a_inv","sar8a_nand2","sar8a_sr","sar8a_dffr") or name.startswith("sar8a_delay_")
        if atomic:self.parts.append(Primitive(name,mapping));return
        for ref,pins,model in devices:
            if model in ("resistor","capacitor"):continue
            assert model in self.blocks,(name,ref,model)
            child_ports=self.blocks[model][0];assert len(child_ports)==len(pins)
            bindings={cp:mapping.get(pin,path+"."+pin) for cp,pin in zip(child_ports,pins)}
            self.expand(model,bindings,path+"."+ref)

    def enqueue(self,t,call):
        self.serial+=1;heapq.heappush(self.q,(t,self.serial,call))

    def drive(self,net,value):
        value=int(bool(value))
        if self.v.get(net,0)==value:return
        self.v[net]=value
        if net in ("CMP_CLK","CAPTURE","ADVANCE","VALID","FAULT","XCTRL.COMMIT"):
            self.trace.append(dict(t_ns=self.time,net=net,value=value))
        if net=="CMP_CLK":
            self.epoch+=1;epoch=self.epoch
            if value:
                bit=7-self.eval_index;self.eval_index+=1
                data=(self.word>>max(0,bit))&1
                if not (self.fault_mode==1 and bit==self.fault_bit):
                    pair=(0,0) if self.fault_mode==2 and bit==self.fault_bit else (data,1-data)
                    def ready():
                        if epoch==self.epoch:
                            self.drive("COMP_P",pair[0]);self.drive("COMP_N",pair[1])
                    self.enqueue(self.time+.2+.03*((bit+3)%5),ready)
            else:
                def reset():
                    if epoch==self.epoch:self.drive("COMP_P",1);self.drive("COMP_N",1)
                self.enqueue(self.time+.05,reset)
        if net=="SAMPLE" and value:self.epoch+=1;self.eval_index=0
        for i in self.listeners.get(net,[]):self.evaluate(i)

    def evaluate(self,i):
        p=self.parts[i];n=p.nets;v=lambda pin:self.v.get(n[pin],0)
        if p.kind=="sar8a_dffr":
            ck=v("CK");rising=ck and not p.clock;p.clock=ck
            if v("RST"):new=0
            elif rising:new=v("D")
            else:return
            pin="Q";delay=.07
        elif p.kind=="sar8a_sr":
            if v("R"):new=0
            elif v("S"):new=1
            else:return
            pin="Q";delay=.025
        elif p.kind.startswith("sar8a_delay_"):
            new=v("A");pin="Y";delay=self.delays[p.kind.split("sar8a_delay_")[1]] if new else .035
        else:
            new=1-v("A") if p.kind=="sar8a_inv" else 1-(v("A")&v("B"))
            pin="Y";delay=.015
        p.version+=1;version=p.version
        # Inertial logic/delay, state-primitive updates retain only the most
        # recent excitation; physical setup/hold is a Spectre-only check.
        def update():
            if version==p.version:p.state=new;self.drive(n[pin],new)
        self.enqueue(self.time+delay,update)

    def frame(self,word,*,offset=0.,fault_mode=0,fault_bit=3,duplicate=False):
        self.word=word;self.fault_mode=fault_mode;self.fault_bit=fault_bit;start=len(self.trace)
        for t,net,val in ((0,"RST_N",0 if offset==0 else 1),(2,"RST_N",1),(1,"SAMPLE",1),(41,"SAMPLE",0),
                          (43,"HOLD_START",1),(43.5,"HOLD_START",0),(89,"DEADLINE",1),(89.5,"DEADLINE",0),
                          (90,"PREPARE",1),(99.9,"PREPARE",0)):
            self.enqueue(offset+t,lambda n=net,v=val:self.drive(n,v))
        self.enqueue(offset,lambda:(self.drive("COMP_P",1),self.drive("COMP_N",1)))
        if duplicate:
            self.enqueue(offset+60,lambda:self.drive("HOLD_START",1));self.enqueue(offset+60.5,lambda:self.drive("HOLD_START",0))
        while self.q and self.q[0][0]<=offset+99.99:
            self.time,_,call=heapq.heappop(self.q);call()
        trace=self.trace[start:]
        return dict(word=word,output=sum((1<<i)*self.v.get(f"D{i}",0) for i in range(8)),
                    valid=self.v["VALID"],fault=self.v["FAULT"],
                    captures=sum(x["net"]=="CAPTURE" and x["value"]==1 for x in trace),
                    advances=sum(x["net"]=="ADVANCE" and x["value"]==1 for x in trace),
                    evaluations=sum(x["net"]=="CMP_CLK" and x["value"]==1 for x in trace))


def main():
    text=source("tb_sar8a_logic","recovery");rows=[]
    for word in range(256):
        e=NetlistEngine(text);r=e.frame(word,duplicate=True)
        assert r["output"]==word and r["valid"]==1 and r["fault"]==0 and r["captures"]==r["advances"]==r["evaluations"]==8,r
        rows.append(r)
    faults=[]
    for mode in (1,2):
        for bit in range(8):
            e=NetlistEngine(text);assert e.frame(165)["valid"]
            r=e.frame(90,offset=100,fault_mode=mode,fault_bit=bit)
            assert not r["valid"] and r["fault"] and r["output"]==165,r
            recovery=e.frame(90,offset=200);assert recovery["valid"] and recovery["output"]==90,recovery
            faults.append(dict(mode=mode,bit=bit,**r))
    summary=dict(scope="actual_exported_native_hierarchy_functional_abstraction_NOT_Spectre",
                 netlist_sha256=hashlib.sha256(text.encode()).hexdigest(),all_patterns_pass=True,
                 patterns=len(rows),fault_positions=len(faults),primitive_count=len(NetlistEngine(text).parts),
                 state_assumptions="SR/DFF behavioral abstractions; no setup/hold/PVT or metastability proof")
    dump("netlist_logic/summary.json",summary);dump("netlist_logic/patterns.json",rows);dump("netlist_logic/faults.json",faults)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
