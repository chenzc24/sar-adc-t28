"""RNL drawing primitives. Every wire endpoint is checked against the electrical source."""
import json
import re
from dataclasses import dataclass

INSTANCE = re.compile(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\S+)([^\n]*)')
RECORD = re.compile(r'(?ms)^// BEGIN SARADC RNL\r?\n.*?^// END SARADC RNL\r?\n')
EXTERNAL = {'INVD1BWP12T30P140':['A','Y','VDD','VSS'],
            'ND2D1BWP12T30P140':['A','B','Y','VDD','VSS'],
            'DFCNQD1BWP12T30P140':['D','CK','RN','Q','VDD','VSS'],
            'iprobe':['p','n']}  # Native ideal current probe, two connected terminals.
POWER = {'VDD','VDD!','AVDD','DVDD'}
GROUND = {'VSS','0'}
COLORS = {'wire':'#30485d','clock':'#94601a','analog':'#226e85','power':'#647584'}

def q(value): return json.dumps(str(value), ensure_ascii=False)
def xy(point): return '(%g,%g)' % tuple(point)
def net(name): return '&'+q(name)
def strip(text): return RECORD.sub('',text)
def record(lines): return '// BEGIN SARADC RNL\n'+''.join(('// '+s).rstrip()+'\n' for s in lines)+'// END SARADC RNL\n'
def instances(body):
    return {m[1]:(m[2].split(),m[3],m[4]) for m in INSTANCE.finditer(strip(body).replace('\\\n',' '))}

@dataclass
class Symbol:
    name: str
    pins: dict
    directions: dict
    width: float
    height: float
    lines: list

def symbol(master, ports):
    """Port numbers always follow the real subckt; grouped pins retain every bit."""
    groups=[];seen=set()
    for p in ports:
        if p in seen:continue
        m=re.fullmatch(r'(CODE|D|GNN|GNP|GPN|GPP|T)(\d+)',p)
        members=[v for v in ports if m and re.fullmatch(re.escape(m[1])+r'\d+',v)] if m else [p]
        if len(members)<2:members=[p]
        seen.update(members);groups.append((p,members))
    outputs={'Y','Q','OUTN','OUTP','VOUT','H','L','DATA','ACTIVE','PRESET','SAMPLE_MATCH','RST_DONE','NEXT_D','TOPN','TOPP'}
    if master in {'sar8i_ctrl','sar_logic_8b_physical','sar8p_timing','b_sar'}:outputs|={'CMP_CLK','PHI_U','PHI_W'}
    if master=='sar8p_bit':outputs|={'CODE','D'}
    if 'refdrv' in master:outputs|={'GNN','GNP','GPN','GPP'}
    if master=='sar8p_sr':outputs|={'Q'}
    exact={'sar8i_idle':{'PRESET','SAMPLE_MATCH'},'sar8p_timing':{'CMP_CLK','DATA','PHI_U','PHI_W'},
           'sar8p_bit':{'CODE','D'},'sar_bootstrap_flat_8b_p':{'VOUT'},'sar_strongarm_t28':{'OUTN','OUTP'}}
    if master in exact:outputs=exact[master]
    sides={'left':[],'right':[],'up':[],'down':[]}
    for p,members in groups:
        side='up' if p in POWER else 'down' if p in GROUND else 'right' if p in outputs or re.fullmatch(r'(CODE|D|GNN|GNP|GPN|GPP|T)\d+',p) else 'left'
        if master in {'sar8i_refword','sar8s_refword','sar8p_refword','b_reference'} and re.fullmatch(r'(CODE|D)\d+',p):side='left'
        if master in {'sar8j_r1_cdac','b_cdac'} and p.startswith(('GNN','GNP','GPN','GPP')):side='left'
        if master in {'sar_adc8_join_r4','tb_sar_top','tb_sar_stalled_top'}:side='right' if p.startswith('D') and p[1:].isdigit() else side
        sides[side].append((p,members))
    h=max(6,(max(len(sides['left']),len(sides['right']))+1)*1.65);w=11
    pins={};dirs={};lines=[]
    def pin(members,x,y,d):
        ids=[ports.index(p)+1 for p in members]
        term=str(ids[0]) if len(ids)==1 else json.dumps(ids)
        lines.append('%s @PIN(terminal=%s,direction=%s);'%(xy((x,y)),term,q(d)))
        for t in ids:pins[t]=(x,y);dirs[t]=d
    def text(x,y,t,size=1.1,align='middle'):
        lines.append('%s @TEXT(%s,size=%g,halign=%s,valign="middle");'%(xy((x,y)),q(t),size,q(align)))
    for side,items in sides.items():
        for i,(p,members) in enumerate(items):
            x,y=((-w-2 if side=='left' else w+2),(len(items)-1-2*i)*1.65) if side in {'left','right'} else ((i-(len(items)-1)/2)*7,(h+2 if side=='up' else -h-2))
            pin(members,x,y,side)
            ex=x+(2 if side=='left' else -2 if side=='right' else 0);ey=y+(-2 if side=='up' else 2 if side=='down' else 0)
            lines.append('@LINE {%s %s};'%(xy((x,y)),xy((ex,ey))))
            label=(re.sub(r'\d+$','',p)+'[%s:%s]'%(re.search(r'\d+$',members[-1])[0],re.search(r'\d+$',members[0])[0])) if len(members)>1 else p
            text(ex+(.5 if side=='left' else -.5 if side=='right' else 0),ey+(.8 if side=='down' else -.8 if side=='up' else 0),label,align='start' if side=='left' else 'end' if side=='right' else 'middle')
    lines.insert(0,'@LINE {(-11,%g) (11,%g) (11,%g) (-11,%g) (-11,%g)};'%(h,h,-h,-h,h))
    # Native library symbols include their real power terminals; no made-up body.
    gate='INV' if master in {'sar8p_inv','INVD1BWP12T30P140'} else 'BUF' if master in {'sar8p_buf','sar8p_clkbuf'} else 'NAND' if master in {'sar8p_nand2','ND2D1BWP12T30P140'} else 'AND' if master=='sar8p_and2' else 'OR' if master=='sar8p_or2' else 'XOR' if master=='sar8p_xor2' else 'DFF' if master in {'sar8p_dffr','DFCNQD1BWP12T30P140'} else 'MUX' if master=='sar8p_mux2' else None
    if gate:
        # Compact full-pin logic symbol, with clock/reset polarity explicit.
        lines=[];pins={};dirs={};w=5;h=5
        ins=[p for p in ports if p not in POWER|GROUND|{'Y','Q'}];out='Y' if 'Y' in ports else 'Q'
        for i,p in enumerate(ins):
            y=(len(ins)-1-2*i)*1.7;pin([p],-7,y,'left');lines.append('@LINE {(-7,%g) (-5,%g)};'%(y,y))
            if gate in {'DFF','MUX'}:text(-4.5,y,p,align='start',size=.7)
            if gate=='DFF' and p=='CK':lines.append('@LINE {(-5,%g) (-3.8,%g) (-5,%g)};'%(y+.7,y,y-.7))
            if gate=='DFF' and p=='RN':lines.append('(-5.4,%g) @CIRCLE(radius=0.4);'%y)
        pin([out],7,0,'right');lines.append('@LINE {(5,0) (7,0)};')
        for p in ports:
            if p in POWER|GROUND:
                y=7 if p in POWER else -7;pin([p],0,y,'up' if p in POWER else 'down');lines.append('@LINE {(0,%g) (0,%g)};'%(y,5 if p in POWER else -5))
        if gate in {'INV','BUF'}:
            lines+=['@LINE {(-5,5) (-5,-5) (4,0) (-5,5)};']
            if gate=='INV':lines+=['(4.5,0) @CIRCLE(radius=0.5);']
        elif gate in {'AND','NAND'}:
            lines+=['@LINE {(-5,5) (0,5) (3,4) (4.4,2) (5,0) (4.4,-2) (3,-4) (0,-5) (-5,-5) (-5,5)};']
            if gate=='NAND':lines+=['(5.5,0) @CIRCLE(radius=0.5);']
        elif gate in {'OR','XOR'}:
            lines+=['@LINE {(-5,5) (-1,4.6) (2,3) (5,0) (2,-3) (-1,-4.6) (-5,-5) (-3.8,-2) (-3.5,0) (-3.8,2) (-5,5)};']
            if gate=='XOR':lines+=['@LINE {(-6,5) (-4.8,2) (-4.5,0) (-4.8,-2) (-6,-5)};']
        else:
            lines+=['@LINE {(-5,5) (5,5) (5,-5) (-5,-5) (-5,5)};'];text(1,0,gate,.85)
    if re.fullmatch(r'sar8j_r1_sw_b\d',master):
        lines=['@LINE {(-11,7) (11,7) (11,-7) (-11,-7) (-11,7)};'];pins={};dirs={};w=11;h=7
        for p,x,y,d in [('BOT',0,12,'up'),('GN',-5,-12,'down'),('GP',5,-12,'down'),
                        ('VREFN',-13,-4,'left'),('VREFP',-13,4,'left'),('VDD',13,4,'right'),('VSS',13,-4,'right')]:
            pin([p],x,y,d)
            ex=x+(2 if d=='left' else -2 if d=='right' else 0);ey=7 if d=='up' else -7 if d=='down' else y
            lines.append('@LINE {%s %s};'%(xy((x,y)),xy((ex,ey))))
            text(ex+(1 if d=='left' else -1 if d=='right' else 0),ey+(.8 if d=='down' else -.8 if d=='up' else 0),p,.65,'start' if d=='left' else 'end' if d=='right' else 'middle')
    lines+=['? @TEXT("${name}",key="name",size=1.6,halign="middle") => @PLACE(0,%g);'%(h+3.5),
            '? @TEXT("${model}",key="model",size=0.85,halign="middle") => @PLACE(0,%g);'%(-h-4)]
    return Symbol('S_'+master,pins,dirs,w*2+4,h*2+8,lines)

def primitive(master):
    if master.startswith(('nch','pch')):
        pm=master.startswith('pch');return Symbol('PMOS_4TERM' if pm else 'NMOS_4TERM',{1:(0,-2 if pm else 2),2:(-3,0),3:(0,2 if pm else -2),4:(1,0)},{1:'down' if pm else 'up',2:'left',3:'up' if pm else 'down',4:'right'},12,14,[])
    lookup={'cfmom_2t':'CAPACITOR','capacitor':'CAPACITOR','resistor':'RESISTOR','rupolym':'RESISTOR','vsource':'VOLTAGE_SOURCE','isource':'CURRENT_SOURCE'}
    if master in lookup:return Symbol(lookup[master],{1:(0,2),2:(0,-2)},{1:'up',2:'down'},10,14,[])

def turn(p,o):
    x,y=p;return {'R0':(x,y),'R90':(-y,x),'R180':(-x,-y),'R270':(y,-x),'MY':(-x,y),'MX':(x,-y)}[o]

class Sheet:
    def __init__(self,name,body,portmap):
        self.name=name;self.body=strip(body);self.parts=instances(body);self.ports=portmap
        self.pos={};self.geometry={};self.lines=[];self.wired=set();self.serial=0;self.links=[]
    def emit(self,line):self.lines.append(line)
    def text(self,x,y,t,size=1.1):
        t=t.replace('→','->').replace('…','...').replace('—','-')
        self.emit('%s @TEXT(%s,size=%g,halign="start",textcolor="#223d52");'%(xy((x,y)),q(t),size))
    def refs(self,n):
        return [inst+':'+str(i) for inst,(nodes,_,_) in self.parts.items() for i,v in enumerate(nodes,1) if v==n and inst in self.pos]
    def place(self,name,x,y,orient='R0'):
        nodes,master,params=self.parts[name];sym=primitive(master) or symbol(master,self.ports[master])
        self.pos[name]=(x,y,orient);self.geometry[name]=sym
        self.emit('#%s @SET-SYMBOL $%s;'%(name,sym.name))
        self.emit('#%s @PLACE%s => @ORIENT(%s);'%(name,xy((x,y)),q(orient)))
        if not sym.lines:
            # Keep labels off horizontal pass-device/RC wires.
            self.emit('#%s @TEXT(%s,key="name",size=1.3,halign="start") => @PLACE%s;'%(name,q(name),xy((x+3,y+3))))
            vals=' '.join(re.findall(r'\b(?:w|l|multi|c|r|nr|lr)=[^\s]+',params))
            self.emit('#%s @TEXT(%s,key="value",size=0.9,halign="start") => @PLACE%s;'%(name,q(vals),xy((x+3,y-4))))
            self.emit('#%s @TEXT("",key="model");'%name)
        return self
    def pin(self,ref):
        inst,t=ref.split(':');sym=self.geometry[inst];nodes,master,_=self.parts[inst]
        i=int(t) if t.isdigit() else self.ports[master].index(t)+1
        x,y,o=self.pos[inst];dx,dy=turn(sym.pins[i],o)
        return (x+dx,y+dy),nodes[i-1],inst,i
    def wire(self,n,*points,color='wire'):
        out=[];refs=[]
        for p in points:
            if isinstance(p,str):
                at,actual,inst,i=self.pin(p)
                if actual!=n:raise ValueError('%s: %s is %s, not %s'%(self.name,p,actual,n))
                out.append('#'+inst+':'+str(i));self.wired.add((inst,i));refs.append(p)
            else:out.append(xy(p))
        self.emit('%s @WIRE(mode="straight",linecolor=%s,linewidth=0.16) {%s};'%(net(n),q(COLORS[color]),' '.join(out)))
        self.links.append((n,refs))
    def join(self,n,refs,axis=None,value=None,color='wire'):
        if len(refs)<2:return
        pts=[self.pin(r)[0] for r in refs]
        if axis is None:axis='y' if max(p[0] for p in pts)-min(p[0] for p in pts)>max(p[1] for p in pts)-min(p[1] for p in pts) else 'x'
        v=value if value is not None else (sum(p[1 if axis=='y' else 0] for p in pts)/len(pts))
        taps=[(p[0],v) if axis=='y' else (v,p[1]) for p in pts]
        backbone=sorted(set(taps),key=lambda p:p[0] if axis=='y' else p[1])
        if len(backbone)>1:self.wire(n,*backbone,color=color)
        for ref,tap in zip(refs,taps):
            self.wire(n,ref,tap,color=color);self.dot(tap)
    def dot(self,p):self.emit('$JUNCTION @ATTACH %s;'%xy(p))
    def route(self,a,b,via=None):
        p,n,_,_=self.pin(a);e,en,_,_=self.pin(b)
        if n!=en:raise ValueError('Different nets: '+a+' '+b)
        if via is None:
            mid=(p[0]+e[0])/2;via=[(mid,p[1]),(mid,e[1])]
        self.wire(n,a,*via,b)
    def bus(self,refs,via=None):
        """Join complete grouped pins, preserving their explicit scalar order."""
        nets=None;ends=[]
        for inst,first in refs:
            i=self.ports[self.parts[inst][1]].index(first)+1;sym=self.geometry[inst]
            members=[t for t,p in sym.pins.items() if p==sym.pins[i]]
            got=[self.parts[inst][0][t-1] for t in members]
            if nets is not None and got!=nets:raise ValueError('Bus order differs: '+inst)
            nets=got;ends.append((inst,i,self.pin(inst+':'+str(i))[0]));self.wired.update((inst,t) for t in members)
        a,ai,p=ends[0];b,bi,e=ends[-1];mid=(p[0]+e[0])/2
        points=via if via is not None else [(mid,p[1]),(mid,e[1])]
        self.emit('{%s} @WIRE(mode="straight",linewidth=0.3) {#%s:%s %s #%s:%s};'%(' '.join(net(n) for n in nets),a,ai,' '.join(xy(v) for v in points),b,bi))
    def local(self,exclude=(),distance=65):
        """Wire short internal links. Global clocks and cross-section nets use named ports."""
        by={}
        for inst,(nodes,master,_) in self.parts.items():
            if inst not in self.pos:continue
            for i,n in enumerate(nodes,1):
                if (inst,i) in self.wired or n in POWER|GROUND or n in exclude:continue
                sym=self.geometry[inst]
                if sum(p==sym.pins[i] for p in sym.pins.values())>1:continue
                by.setdefault(n,[]).append(inst+':'+str(i))
        for n,rs in by.items():
            if len(rs)<2:continue
            pts=[self.pin(r)[0] for r in rs]
            if max(p[0] for p in pts)-min(p[0] for p in pts)>distance or max(p[1] for p in pts)-min(p[1] for p in pts)>distance:continue
            if len(rs)==2:self.route(*rs)
    def finish(self):
        if set(self.parts)!=set(self.pos):raise ValueError('Unplaced instances in '+self.name+': '+str(set(self.parts)-set(self.pos)))
        # Every remaining terminal gets a visible net or bus stub, including bulk/power.
        for inst,(nodes,master,_) in self.parts.items():
            done=set();sym=self.geometry[inst]
            for i,n in enumerate(nodes,1):
                if (inst,i) in self.wired or sym.pins[i] in done:continue
                same=[j for j,p in sym.pins.items() if p==sym.pins[i]];done.add(sym.pins[i]);p,_,_,_=self.pin(inst+':'+str(i))
                direction=sym.directions[i];v={'left':(-1,0),'right':(1,0),'up':(0,1),'down':(0,-1)}[direction];vx,vy=turn(v,self.pos[inst][2]);end=(p[0]+3*vx,p[1]+3*vy)
                nets=[nodes[j-1] for j in same]
                if len(same)>1:
                    self.emit('{%s} @WIRE(mode="straight",linewidth=0.3) {#%s:%d %s};'%(' '.join(net(k) for k in nets),inst,i,xy(end)))
                    base=re.sub(r'\d+$','',nets[0]);label=base+'[%s:%s]'%(re.search(r'\d+$',nets[-1])[0],re.search(r'\d+$',nets[0])[0]) if all(re.fullmatch(re.escape(base)+r'\d+',k) for k in nets) else ','.join(nets)
                else:self.wire(n,inst+':'+str(i),end);label=n
                self.emit('%s @TEXT(%s,size=1.1,halign=%s,valign=%s);'%(xy((end[0]+vx*.4,end[1]+vy*.4)),q(label),q('end' if vx<0 else 'start' if vx>0 else 'middle'),q('bottom' if vy>0 else 'top' if vy<0 else 'middle')))
        return record(['@RNL(author="saradc topology") {']+self.lines+['}'])
