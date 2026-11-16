"""Generate the shared CDAC functional core and its verification wrapper.

Native PCell helpers are reused from the verified three-cap pilot.  The LVS
reference is generated independently from the electrical source, never from
the physical assignment.  Generated decks and detailed placement live in work/.
"""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "work/layout/full-cdac"
NX, NY = 32, 8
PX, PY = 0.96, 5.0
PORTS = [f"G{s}{p}{b}" for s in "NP" for p in "NP" for b in range(8)]
PORTS += ["TOPN", "TOPP", "VDD", "VREFN", "VREFP", "VSS"]
HALF_PORTS = ["TOP", "TERM", "VDD", "VREFN", "VREFP", "VSS"]
HALF_PORTS += [f"G{p}{b}" for p in "NP" for b in range(8)]
SUPPLY_X = {"TERM": 35.04, "VREFN": 35.52, "VREFP": 36.0, "VDD": 36.48, "VSS": 36.96}
BIT_X = {f"B{b}": 33.0 + 0.24*b for b in range(8)}
TOP_X = 37.6
GATE_X = {f"G{p}{b}": 38.4 + .24*(2*b+(p == "P")) for b in range(8) for p in "NP"}
PIN_Y = -45.0
MIRROR_X = 88.0


def cap_assignment():
    # Pair sites under central inversion. Singleton B0 and electrical CTERM
    # occupy opposite central sites; their centroid exception is explicit.
    special = (15, 3)
    opposite = (NX-1-special[0], NY-1-special[1])
    pairs = []
    for r in range(NY//2):
        for c in range(NX):
            if (c, r) != special:
                pairs.append(((c, r), (NX-1-c, NY-1-r)))
    # A bit-reversal ordering distributes the larger weights across the array.
    pairs.sort(key=lambda p: int(f"{p[0][1]*NX+p[0][0]:07b}"[::-1], 2))
    codes = []
    for k in range(1, 128):
        trailing = (k & -k).bit_length()-1
        codes.append(7-trailing)
    grid = {special: "B0", opposite: "TERM"}
    for pair, bit in zip(pairs, codes):
        for site in pair:
            grid[site] = f"B{bit}"
    counts = Counter(grid.values())
    assert counts == Counter({**{f"B{b}": 2**b for b in range(8)}, "TERM": 1})
    stats = {}
    for net in counts:
        sites = [p for p, n in grid.items() if n == net]
        stats[net] = {"units": len(sites), "centroid_grid": [sum(p[i] for p in sites)/len(sites) for i in (0, 1)]}
        if net not in ("B0", "TERM"):
            assert stats[net]["centroid_grid"] == [(NX-1)/2, (NY-1)/2]
    return grid, stats


def independent_reference():
    text = (ROOT / "design/xtor/cdac/cdac.scs").read_text()
    electrical = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))
    electrical = re.sub(r"\\\s*\n\s*", " ", electrical)
    header = re.search(r"^subckt sar8j_r1_cdac (.+)$", electrical, re.M)[1].split()
    assert header == PORTS
    caps = re.findall(r"^\s*(CMOM[NP]\d) \((\w+) (\w+)\) cfmom_2t (.*)$", electrical, re.M)
    assert len(caps) == 18
    result = ["* Independent reference from current CDAC electrical source, unchanged interface.",
              ".SUBCKT sar8j_r1_cdac " + " ".join(PORTS)]
    for name, a, b, raw in caps:
        p = dict(re.findall(r"(\w+)=(\S+)", raw))
        assert {k: p[k] for k in ('nr','lr','w','s','stm','spm')} == dict(nr='8',lr='2u',w='50n',s='50n',stm='1',spm='3')
        for k in range(int(p['multi'])):
            result.append(f"X{name}_{k} {a} {b} cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=1")
    # Physical boundary devices have both plates tied together and introduce
    # no additional ideal DAC weight. Explicitly account for their recognition.
    for k in range(168):
        result.append(f"XBOUNDARY_{k} VSS VSS cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=1")
    for side in "NP":
        for bit in range(8):
            block = re.search(rf"subckt sar8j_r1_sw_b{bit} .*?\n(.*?)ends sar8j_r1_sw_b{bit}", electrical, re.S)[1]
            for p, source, body, model in [('N','VREFN','VSS','nch_mac'),('P','VREFP','VDD','pch_mac')]:
                params = dict(re.findall(r"(\w+)=(\S+)", re.search(rf"{model} (.*)", block)[1]))
                assert int(params['multi']) == 3*2**bit and params['nf'] == '1' and params['l'] == '90n'
                result.append(f"M{side}{p}{bit} B{side}{bit} G{side}{p}{bit} {source} {body} {model} W={params['w']} L=90n M={params['multi']}")
    result += [".ENDS sar8j_r1_cdac", ""]
    return "\n".join(result), hashlib.sha256(electrical.encode()).hexdigest()


class Skill:
    def __init__(self):
        self.lines = []
    def __call__(self, s):
        self.lines.append(s)
    def net(self, name):
        return f'fullNet(cv "{name}")'
    def wire(self, net, layer, x0,y0,x1,y1,w=.12):
        self(f'cmpWire(cv {self.net(net)} "M{layer}" cmpPoint({x0:.5f} {y0:.5f}) cmpPoint({x1:.5f} {y1:.5f}) {w})')
    def via(self, x,y,lo,hi,redundant=False):
        for layer in range(lo,hi):
            for dx in (-.065,.065) if redundant else (0,):
                self(f'cmpVia(cv "M{layer+1}_M{layer}" cmpPoint({x+dx:.5f} {y:.5f}))')
    def port(self, net, layer, x,y):
        self(f'cmpPort(cv {self.net(net)} "M{layer}" cmpPoint({x:.5f} {y:.5f}) 0.16)')


def generate():
    DEST.mkdir(parents=True, exist_ok=True)
    grid, centroids = cap_assignment()
    reference, source_sha = independent_reference()
    helper = (ROOT / "Layout/design/compact.il").read_text().split("procedure(cmpReadback()")[0]
    helper = helper.replace("< 2.0 &&", "< 3.5 &&")
    helper = helper.replace('cmpPort(cv gate "M1" cmpPoint((car(xs)+cadr(xs))/2.0 yGate) 0.08)',
                            'cmpSquare(cv "M1" cmpPoint((car(xs)+cadr(xs))/2.0 yGate) 0.08)')
    helper = helper.replace('cmpPort(cv net "M1" p 0.16)', 'cmpSquare(cv "M1" p 0.16)')
    helper = helper.replace('procedure(cmpVia(cv name p)', 'procedure(fullNativeVia(cv name p)')
    helper += '''
procedure(cmpVia(cv name p)
  let((lo hi)
    fullNativeVia(cv name p)
    lo=atoi(substring(name 5 1))
    hi=atoi(substring(name 2 1))
    for(k max(2 lo) hi cmpSquare(cv sprintf(nil "M%d" k) p 0.14))
  )
)
procedure(fullNet(cv name)
  or(car(setof(n cv~>nets equal(n~>name name))) dbCreateNet(cv name))
)
procedure(fullMom(cv name x y)
  let((i)
    i=dbCreateParamInstByMasterName(cv "tsmcN28" "cfmom_2t" "layout" name cmpPoint(x y) "R0" 1
      list(list("Nfinger" "string" "8") list("Lfinger" "string" "2u")
           list("Wfinger" "string" "50n") list("Sfinger" "string" "50n")
           list("StartMn" "string" "1") list("StopMn" "string" "3")))
    cmpRequire(i "Cannot instantiate full CDAC MOM")
    cmpRequire(equal(cmpLanding(i "MINUS" "M3" nil) cmpPoint(x+0.38 y)) "MOM landing changed")
    i
  )
)
procedure(fullBankDevice(cv model w fingers name x y bot gate ref body)
  let((i route drainX gateX pmos wellHi)
    i=cmpMOS(cv model w sprintf(nil "%d" fingers) name x y)
    pmos=equal(model "pch_mac")
    gateX=x-if(pmos then 0.44 else 0.22)
    drainX=x+0.33
    route=cmpSwitchRoutes(cv i fullNet(cv gate) fullNet(cv bot) fullNet(cv ref) drainX y-0.33 y+0.33 fingers)
    ; Expose all macro nets to row buses, with gate escape outside the device.
    cmpWire(cv fullNet(cv gate) "M1" cmpPoint(x+0.045 y+0.33) cmpPoint(gateX y+0.33) 0.08)
    for(k 1 5 cmpVia(cv sprintf(nil "M%d_M%d" k+1 k) cmpPoint(gateX y+0.33)))
    cmpWire(cv fullNet(cv ref) "M2" cmpPoint(cadr(cadr(route)) y-0.33) cmpPoint(x-0.12 y-0.33) 0.12)
    cmpVia(cv "M3_M2" cmpPoint(x-0.12 y-0.33))
    cmpVia(cv "M4_M3" cmpPoint(x-0.12 y-0.33))
    when(pmos
      cmpRect(cv "NW" x-0.70 y-0.23 caadr(i~>bBox)+0.20 y+0.55))
    cmpTap(cv fullNet(cv body) if(pmos then "NP" else "PP") cmpPoint(x-0.45 y+0.075))
    for(k 1 3 cmpVia(cv sprintf(nil "M%d_M%d" k+1 k) cmpPoint(x-0.45 y+0.075)))
    i
  )
)
procedure(fullGuard(cv x0 y0 x1 y1)
  let((vss p)
    vss=fullNet(cv "VSS")
    foreach(segment list(list(x0 y0 x1 y0) list(x0 y1 x1 y1) list(x0 y0 x0 y1) list(x1 y0 x1 y1))
      cmpRect(cv "OD" min(car(segment) caddr(segment))-0.09 min(cadr(segment) cadddr(segment))-0.09 max(car(segment) caddr(segment))+0.09 max(cadr(segment) cadddr(segment))+0.09)
      cmpRect(cv "PP" min(car(segment) caddr(segment))-0.165 min(cadr(segment) cadddr(segment))-0.165 max(car(segment) caddr(segment))+0.165 max(cadr(segment) cadddr(segment))+0.165)
      cmpWire(cv vss "M1" cmpPoint(car(segment) cadr(segment)) cmpPoint(caddr(segment) cadddr(segment)) 0.24))
    for(k 1 floor((x1-x0)/0.5)-1
      foreach(y list(y0 y1) cmpSquare(cv "CO" cmpPoint(x0+k*0.5 y) 0.04)))
    for(k 1 floor((y1-y0)/0.5)-1
      foreach(x list(x0 x1) cmpSquare(cv "CO" cmpPoint(x y0+k*0.5) 0.04)))
  )
)
'''
    helper += "\n" + (ROOT / "Layout/design/hierarchy.il").read_text()
    s = Skill()
    s('procedure(fullBuild() let((cv i p cvTop master inst net point term shape)')
    s('cmpRequire(equal(ddGetObj("SAR_ADC_T28_LAYOUT")~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") "Not unified layout library")')
    s('cv=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8_cdac_half" "layout" "maskLayout" "w")')
    s('cmpRequire(cv && !cv~>instances && !cv~>shapes "Cannot recreate owned working half")')
    supply_x = {**BIT_X, **SUPPLY_X}
    # Every row, including dummy rows, has identical pitch and legal channels.
    for r in range(-1, NY+1):
        rownets = defaultdict(list)
        for c in range(-1, NX+1):
            net = grid.get((c,r), "VSS")
            x,y=c*PX,r*PY
            s(f'i=fullMom(cv "C_{c+1}_{r+1}_{net}" {x:.5f} {y:.5f})')
            xc=x+.38
            if net == 'VSS':
                # A boundary MOM is shorted to quiet ground, no floating metal.
                s.via(xc,y,3,4); s.via(xc,y+2.42,3,4)
                s.wire(net,4,xc,y,xc,y+2.42)
            else:
                s.wire("TOP",3,xc,y+2.42,xc,y+2.70)
            rownets[net].append(xc)
            lane = 9 if net == 'VSS' else 8 if net == 'TERM' else int(net[1:])
            yb=y-.25-.20*lane-(.04 if net=='VSS' else 0)
            s.wire(net,3,xc,y,xc,yb)
            s.via(xc,yb,3,4)
        for net, xs in rownets.items():
            lane = 9 if net == 'VSS' else 8 if net == 'TERM' else int(net[1:])
            yb=r*PY-.25-.20*lane-(.04 if net=='VSS' else 0)
            s.wire(net,4,min(xs),yb,supply_x[net],yb)
            s.via(supply_x[net],yb,4,5,redundant=net in SUPPLY_X)
        if 0 <= r < NY:
            s.wire('TOP',3,.38,r*PY+2.70,TOP_X,r*PY+2.70)
    s.wire('TOP',3,TOP_X,2.70,TOP_X,(NY-1)*PY+2.70)
    s.port('TOP',3,TOP_X,20.20)
    # 65 folded switch pairs per side: 3, 6, then 12-finger chunks.
    groups=[]
    for b in reversed(range(8)):
        left=3*2**b
        while left:
            n=min(12,left); left-=n
            groups.append((b,n))
    assert len(groups)==65 and sum(n for _,n in groups)==765
    bankrows=defaultdict(list)
    for index,(b,n) in enumerate(groups):
        r,c=divmod(index,9)
        bankrows[r].append((c,b,n))
    for r, entries in bankrows.items():
        y=-11.0-4.2*r
        s(f'cmpRect(cv "NW" 0 {y-1.23:.5f} 32.2 {y-.45:.5f})')
        bits=sorted({b for c,b,n in entries})
        for c,b,n in entries:
            x=.70+3.60*c
            for p,dy,w,model,ref,body in [('N',0,'150n','nch_mac','VREFN','VSS'),('P',-1,'175n','pch_mac','VREFP','VDD')]:
                s(f'fullBankDevice(cv "{model}" "{w}" {n} "SW_{p}_{r}_{c}" {x:.5f} {y+dy:.5f} "B{b}" "G{p}{b}" "{ref}" "{body}")')
                yg=y+1.6+.20*(2*bits.index(b)+(p=='P'))
                gatex=x-(.44 if p=='P' else .22)
                s.wire(f'G{p}{b}',5,gatex,y+dy+.33,gatex,yg)
                # Gate escape M6 landing to a vertical M5 spur, then M6 bus.
                s.via(gatex,yg,5,6)
            yb=y+.80+.20*bits.index(b)
            s.wire(f'B{b}',3,x+.33,y-1.12,x+.33,yb)
            s.via(x+.33,yb,3,4)
        for net,dy in [('VSS',.075),('VREFN',-.33),('VDD',-.925),('VREFP',-1.33)]:
            s.wire(net,4,.25,y+dy,SUPPLY_X[net],y+dy,.16)
            s.via(SUPPLY_X[net],y+dy,4,5,redundant=True)
        for b in bits:
            xs=[.70+3.60*c for c,bb,n in entries if b==bb]
            yb=y+.80+.20*bits.index(b)
            s.wire(f'B{b}',4,min(xs)+.33,yb,BIT_X[f'B{b}'],yb)
            s.via(BIT_X[f'B{b}'],yb,4,5)
            for p in 'NP':
                net=f'G{p}{b}'; yg=y+1.6+.20*(2*bits.index(b)+(p=='P'))
                s.wire(net,6,min(xs)-(.44 if p=='P' else .22),yg,GATE_X[net],yg)
                s.via(GATE_X[net],yg,6,7)
    for net,x in supply_x.items():
        s.wire(net,5,x,PIN_Y,x,42.0 if net=='VSS' else 38.5,.12 if net.startswith('B') else .24)
        if net in HALF_PORTS:
            s.port(net,5,x,PIN_Y)
    for net,x in GATE_X.items():
        s.wire(net,7,x,PIN_Y,x,-7.0,.12)
        s.port(net,7,x,PIN_Y)
    s('fullGuard(cv -1.0 -42.8 32.6 -8.4)')
    s.via(32.6,-10.925,1,4,redundant=True)
    s.wire('VSS',4,32.6,-10.925,SUPPLY_X['VSS'],-10.925,.16)
    # All device-local labels are internal. Only these 22 terms are retained
    # for hierarchical hookup (local terminal labels may repeat but no ports
    # are added to the parent unless explicitly promoted below).
    s('cmpRequire(dbSave(cv) "Cannot save full CDAC half")')
    s('dbClose(cv)')
    s('master=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8_cdac_half" "layout" "" "r")')
    s('cvTop=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8j_r1_cdac_core" "layout" "maskLayout" "w")')
    s('cmpRequire(master && cvTop && !cvTop~>instances && !cvTop~>shapes "Cannot recreate owned full CDAC")')
    for side,origin,orient in [('N',0,'R0'),('P',MIRROR_X,'MY')]:
        s(f'inst=dbCreateInst(cvTop master "X{side}" cmpPoint({origin} 0) "{orient}")')
        port_location={**{n:(5,x,PIN_Y) for n,x in SUPPLY_X.items()},**{n:(7,x,PIN_Y) for n,x in GATE_X.items()},'TOP':(3,TOP_X,20.20)}
        for n,(layer,x,y) in port_location.items():
            xp=x if side=='N' else origin-x
            name = f'TOP{side}' if n=='TOP' else f'G{side}{n[1:]}' if n.startswith('G') else 'VREFN' if n=='TERM' and side=='N' else 'VREFP' if n=='TERM' else n
            if n in ('TERM','VDD','VREFN','VREFP','VSS'):
                # Short child TERM only to the frozen side's reference at top.
                # M6 global supply straps are below all signal escape pins.
                target={'VDD':-48.0,'VREFN':-48.6,'VREFP':-49.2,'VSS':-49.8}[name]
                s(f'cmpWire(cvTop fullNet(cvTop "{name}") "M5" cmpPoint({xp:.5f} {y}) cmpPoint({xp:.5f} {target}) 0.24)')
                for dx in (-.065,.065):
                    s(f'cmpVia(cvTop "M6_M5" cmpPoint({xp+dx:.5f} {target}))')
            else:
                s(f'cmpPort(cvTop fullNet(cvTop "{name}") "M{layer}" cmpPoint({xp:.5f} {y}) 0.16)')
    for name,y in [('VDD',-48.0),('VREFN',-48.6),('VREFP',-49.2),('VSS',-49.8)]:
        s(f'cmpWire(cvTop fullNet(cvTop "{name}") "M6" cmpPoint(35.04 {y}) cmpPoint({MIRROR_X-35.04} {y}) 0.40)')
        s(f'cmpPort(cvTop fullNet(cvTop "{name}") "M6" cmpPoint({MIRROR_X/2} {y}) 0.40)')
    s('cmpRequire(length(cvTop~>terminals)==38 "Wrong full CDAC port count")')
    s('cmpRequire(dbSave(cvTop) "Cannot save full CDAC")')
    s('dbClose(cvTop) dbClose(master)')
    s('cdacWrapCore(nil)')
    s('cvTop=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8j_r1_cdac" "layout" "" "r")')
    s('printf("PILOT_OA_OK sar8j_r1_cdac instances=%d ports=%d bbox=%L\\n" length(cvTop~>instances) length(cvTop~>terminals) cvTop~>bBox)')
    s('dbClose(cvTop) t))')
    s('if(errset(fullBuild() t) then exit(0) else exit(1))')
    (DEST/'cdac-full.il').write_text(helper+'\n'+'\n'.join(s.lines)+'\n',encoding='ascii')
    (DEST/'cdac-full-reference.cdl').write_text(reference,encoding='ascii')
    mapping={"top":"sar8j_r1_cdac","core":"sar8j_r1_cdac_core","half":"sar8_cdac_half","ports":PORTS,
        "electrical_source_sha256":source_sha,"active_units_per_side":256,
        "boundary_dummy_units_per_side":84,"switch_fingers_per_polarity_per_side":765,
        "centroids":centroids,"pitch_um":[PX,PY],"array_grid":[NX,NY],
        "centroid_exceptions":["B0", "TERM"],"dummy_connection":"both plates VSS",
        "assignment":[{"column":c,"row":r,"net":grid[c,r]} for r in range(NY) for c in range(NX)],
        "qualification":"physical candidate, pending DRC/LVS/PEX/postlayout"}
    (DEST/'placement.json').write_text(json.dumps(mapping,indent=2)+'\n')
    print(json.dumps({k:v for k,v in mapping.items() if k!='assignment'},indent=2))


if __name__=='__main__':
    generate()
