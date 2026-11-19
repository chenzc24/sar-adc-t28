"""Curated drawing recipes. Connectivity always comes from the Spectre instances.

These recipes seed editable @RNL comments; normal drawing reads those comments.
They deliberately keep clocks and supplies named at distant sections. Analog
signal paths, storage paths, local feedback and RC nodes are physically wired.
"""
import re
from .rnl import Sheet, POWER, GROUND, instances, strip

def top(s):
    s.text(-24,105,'SAR8 / current transistor hierarchy',2)
    s.text(-24,97,'VIN pair → Bootstrap → MOM CDAC → StrongARM → asynchronous SAR',1.15)
    for n,x,y in [('XSAMPLE',0,67),('XIDLE',65,67),('XSEQ',130,67),
                  ('XBOOTN',0,12),('XBOOTP',0,-25),('XCDAC',72,-7),
                  ('XCOMP',137,-7),('XCTRL',204,-7),('XREF',72,-91),
                  ('CL_COMP_N',168,-45),('CL_COMP_P',184,-45),('CL_CMP_CLK',222,-45)]:s.place(n,x,y)
    for n,label in [('XSAMPLE','Sample buffer'),('XIDLE','Idle / preset'),('XSEQ','Sample edge'),
                    ('XBOOTN','Bootstrap -'),('XBOOTP','Bootstrap +'),('XCDAC','MOM CDAC'),
                    ('XCOMP','StrongARM'),('XCTRL','Async SAR'),('XREF','Reference word')]:
        x,y,_=s.pos[n];s.text(x-12,y+s.geometry[n].height/2+5,label,2.4)
    s.route('XSAMPLE:Y','XIDLE:SAMPLE')
    s.route('XIDLE:SAMPLE_MATCH','XSEQ:A')
    s.join('SEQ_SAMPLE',['XSEQ:Y','XBOOTN:CLKS','XBOOTP:CLKS'],'x',-25,color='clock')
    s.route('XBOOTN:VOUT','XCDAC:TOPN',[(32,12),(32,24),(98,24),(98,s.pin('XCDAC:TOPN')[0][1])])
    s.route('XBOOTP:VOUT','XCDAC:TOPP',[(36,-25),(36,-31),(101,-31),(101,s.pin('XCDAC:TOPP')[0][1])])
    for n in ['TOPN','TOPP']:
        s.route('XCDAC:'+n,'XCOMP:VIN'+n[-1])
    for n in ['COMP_N','COMP_P']:
        a='XCOMP:OUT'+n[-1];b='XCTRL:'+n;c='CL_'+n+':1'
        x=s.pin(c)[0][0];s.join(n,[a,b,c],'x',x)
    s.join('CMP_CLK',['XCTRL:CMP_CLK','XCOMP:CLK','CL_CMP_CLK:1'],'y',34,color='clock')
    for i,p in enumerate(['GNN','GNP','GPN','GPP']):
        a=s.pin('XREF:'+p+'0')[0];b=s.pin('XCDAC:'+p+'0')[0];x=41-i*4
        s.bus([('XREF',p+'0'),('XCDAC',p+'0')],[(111+i*4,a[1]),(111+i*4,-60-i*4),(x,-60-i*4),(x,b[1])])
    for i,p in enumerate(['CODE','D']):
        a=s.pin('XCTRL:'+p+'0')[0];b=s.pin('XREF:'+p+'0')[0]
        s.bus([('XCTRL',p+'0'),('XREF',p+'0')],[(244+i*4,a[1]),(244+i*4,-132-i*4),(43-i*4,-132-i*4),(43-i*4,b[1])])
    s.text(155,-128,'CODE[7:0] / D[7:0] feedback',.95)
    # Clock/sample controls cross sections by their exact source net names.
    s.text(-24,-145,'All three physical comparator/clock MOM loads are shown. VDD! / 0 are global rails.',.95)

def comparator(s):
    s.text(-47,72,'StrongARM / 11 MOS / symmetric latch and input pair',1.5)
    placement={'MPLATN':(-20,42),'MPLATP':(20,42),'MNLATN':(-20,20),'MNLATP':(20,20),
               'MNINP':(-20,-5),'MNINN':(20,-5),'MNTAIL':(0,-30),
               'MPRSTN':(-42,42),'MPRSTP':(42,42),'MPRSTY':(-42,10),'MPRSTX':(42,10)}
    for n,(x,y) in placement.items():
        mirrored=(x<0 if n.startswith(('MPLAT','MNLAT')) else x>0)
        s.place(n,x,y,'MY' if mirrored else 'R0')
    s.join('VDD',[n+':3' for n in placement if n.startswith('MP')],'y',61,color='power')
    s.join('OUTN',['MPLATN:1','MNLATN:1','MPRSTN:1'],'y',31,color='analog')
    s.join('OUTP',['MPLATP:1','MNLATP:1','MPRSTP:1'],'y',33,color='analog')
    s.wire('OUTN','MPLATN:1',(-20,36),(8,36),(8,42),'MPLATP:2',color='analog')
    s.wire('OUTN',(8,36),(8,20),'MNLATP:2',color='analog');s.dot((8,36))
    s.wire('OUTP','MPLATP:1',(20,28),(-8,28),(-8,42),'MPLATN:2',color='analog')
    s.wire('OUTP',(-8,28),(-8,20),'MNLATN:2',color='analog');s.dot((-8,28))
    s.join('Y',['MNLATN:3','MNINP:1','MPRSTY:1'],'y',4,color='analog')
    s.join('X',['MNLATP:3','MNINN:1','MPRSTX:1'],'y',4,color='analog')
    s.join('TAIL',['MNINP:3','MNINN:3','MNTAIL:1'],'y',-18,color='analog')
    s.text(-46,-48,'VINP → Y → OUTN; VINN → X → OUTP. CLK resets PMOS and enables tail NMOS.',.95)

def bootstrap(s):
    s.text(-13,70,'Bootstrap / two parallel sampling switches / MOM bootstrap capacitor',1.5)
    pos={'MPCLK':(0,35),'MNCLK':(0,5),'M4B':(38,35),'M4C':(38,5),'M4A':(56,5),
         'Cboot':(80,21),'M2':(80,48),'M8':(80,-9),'Msin':(101,-9),
         'M4':(116,43),'Maux':(116,4),'MRSTG':(116,-22),
         'Mmain':(158,17),'Mmain_U1':(158,-8)}
    for n,(x,y) in pos.items():s.place(n,x,y,'R270' if n.startswith('Mmain') else 'R0')
    s.join('CLKSB',['MPCLK:1','MNCLK:1'],'y',20)
    s.join('CTRL',['M4B:1','M4C:1','M4A:1','M4:2'],'y',60)
    s.join('BTOP',['Cboot:1','M2:1','M4:3'],'y',31,color='analog')
    s.join('BBOT',['Cboot:2','M4C:3','M4A:3','M8:1','Msin:1'],'y',-2,color='analog')
    s.join('G',['M4:1','Maux:1','Mmain:2','Mmain_U1:2'],'x',138,color='analog')
    s.route('Maux:3','MRSTG:1')
    s.join('Vin',['Msin:3','Mmain:3','Mmain_U1:3'],'x',146,color='analog')
    s.join('VOUT',['Mmain:1','Mmain_U1:1'],'x',177,color='analog')
    s.text(-13,-44,'Clock inverter',1.1);s.text(33,-44,'Precharge / boosted G and BTOP',1.1);s.text(144,-44,'Vin → VOUT',1.1)
    s.text(-13,-51,'Bulk connections remain explicit: M2/M4 use BTOP; sampling MOS uses 0. No ideal replacement.',.9)

def switch(s):
    s.place('MP_HIGH',0,20);s.place('MN_LOW',0,-10)
    s.join('BOT',['MP_HIGH:1','MN_LOW:1'],'y',5,color='analog')
    s.text(-20,48,s.name+' / real reference switches',1.3)

def cdac(s):
    s.text(-17,85,'Differential binary MOM CDAC / 1, 2, 4, …, 128 units + 1 dummy per side',1.5)
    for side,y in [('N',40),('P',-40)]:
        caprefs=[]
        for k in range(9):
            x=k*43;n='CMOM'+side+str(k);s.place(n,x,y);caprefs.append(n+':1')
            if k<8:
                sw='XS'+side+str(k);s.place(sw,x,y-24)
                s.route(n+':2',sw+':BOT')
        s.join('TOP'+side,caprefs,'y',y+15,color='analog')
        s.text(-17,y+25,'TOP'+side+' / '+('negative' if side=='N' else 'positive')+' bank',1.2)
        s.text(340,y-24,'dummy → VREFP' if side=='P' and s.parts['CMOMP8'][0][1]=='VREFP' else 'dummy → '+s.parts['CMOM'+side+'8'][0][1],.9)
    s.text(-17,-100,'Each switch expands to the real PMOS/NMOS pair. GP/GN are physical gates, not ideal switch controls.',1)

def delay(s):
    s.text(-18,47,s.name+' / two RC stages with active clear',1.4)
    for n,x,y,o in [('R0',12,15,'R90'),('X002',42,15,'R0'),('R1',70,15,'R90'),('X005',104,15,'R0'),
                    ('C0',28,-4,'R0'),('C1',86,-4,'R0'),('MN_CLEAR',17,-23,'R0'),('MP_CLEAR',76,39,'R0'),('X006',-14,-23,'R0')]:s.place(n,x,y,o)
    s.join('RC0',['R0:2','C0:1','X002:A','MN_CLEAR:1'],'x',28)
    s.join('RC1',['R1:2','C1:1','X005:A','MP_CLEAR:1'],'x',86)
    s.route('X002:Y','R1:1');s.route('X006:Y','MN_CLEAR:2')
    s.text(-18,-44,'R/C values and multiplicities are read from the netlist; clear transistors are retained.',.9)

def simple(s):
    sr = {'X000':(0,-24),'X001':(38,20),'X002':(76,20),'X003':(76,-24)}
    presets={
        'sar8p_inv':{'XLIB':(0,0)},'sar8p_nand2':{'XLIB':(0,0)},
        'sar8p_clkbuf':{'X000':(0,0),'XFINAL':(34,0)},
        'sar8p_buf':{'X000':(0,0),'X001':(34,0)},
        'sar8p_and2':{'X000':(0,0),'X001':(34,0)},
        'sar8p_or2':{'X000':(0,16),'X001':(0,-16),'X002':(40,0)},
        'sar8p_xor2':{'X000':(0,0),'X001':(40,20),'X002':(40,-20),'X003':(80,0)},
        'sar8p_mux2':{'X000':(0,-26),'X001':(42,15),'X002':(42,-15),'X003':(84,0)},
        'sar8p_dffr':{'XRESET':(0,-20),'XFF':(43,0)},
        'sar8p_sr':{**sr,'CQB':(108,-37)}, 'sar8p_sr_static':sr,
        'sar8r_edge':{'XD':(0,-20),'XA':(43,0),'XB':(80,0)},
        'sar8p_bit':{'XMUX':(0,0),'XSTORE':(43,0),'X002':(84,0)},
        'sar8p_nonoverlap':{'X000':(0,18),'XD_LD':(36,18),'XD_HD':(36,-18),'X004':(76,18),'X002':(76,-18)},
        'sar8i_idle':{'XN':(0,18),'XD':(42,18),'XP':(84,18),'XA':(0,-24),'XB':(42,-24)}
    }
    pos=presets.get(s.name)
    if pos is None:return graph(s)
    if set(pos)!=set(s.parts):return graph(s)
    for n,(x,y) in pos.items():s.place(n,x,y)
    s.local(distance=110)
    # Fanout inside small logic circuits is shown rather than hidden in labels.
    for n in {v for nodes,_,_ in s.parts.values() for v in nodes}-POWER-GROUND:
        refs=s.refs(n)
        if len(refs)>2 and not any((r.split(':')[0],int(r.split(':')[1])) in s.wired for r in refs):
            pts=[s.pin(r)[0] for r in refs];s.join(n,refs,'x',min(p[0] for p in pts)-5)
    s.text(-16,46,s.name+' / native standard-cell composition',1.3)

def refdriver(s):
    s.text(-28,27,s.name+' / four physical gate-driver chains',1.5)
    for row,prefix in enumerate(['GNN','GNP','GPN','GPP']):
        y=-row*38
        pre=[n for n,(nodes,master,_) in s.parts.items() if master=='sar8p_inv' and nodes[-1]==prefix+'PRE']
        for n in pre:s.place(n,-17,y)
        # Discover exact instances by real output node, never by guessed designators.
        for i,out in enumerate([prefix+'A',prefix+'B',prefix+'DRV']):
            n=next(n for n,(ns,m,_) in s.parts.items() if m=='INVD1BWP12T30P140' and ns[1]==out);s.place(n,18+i*29,y)
        resistors=[];at=prefix+'DRV'
        while at!=prefix:
            n,ns=next((n,ns) for n,(ns,m,_) in s.parts.items() if m=='rupolym' and at in ns and n not in resistors)
            resistors.append(n);at=next(v for v in ns if v!=at)
        for i,n in enumerate(resistors):s.place(n,110+i*25,y,'R90')
        s.text(104,y+15,prefix+' / 10 series poly sections',.95)
    s.local(distance=48)
    s.text(-28,-148,'GP and GN chains keep their source polarity, device sizing and series R; no zero-delay abstraction.',1)

def bitseq(s):
    for k in range(7,-1,-1):s.place('XF'+str(k),(7-k)*43,0)
    s.place('X001',22,27)
    s.local(exclude=('SAMPLE','PHI_U'),distance=60)
    s.text(-16,50,'Token shift / bit 7 → bit 0 / asynchronous reset',1.4)

def timing(s):
    s.text(-18,73,'Asynchronous completion / write / update / quiet / comparator clock',1.5)
    pos={'X002':(0,36),'X003':(0,0),'X004':(35,0),'X005':(72,36),
         'X006':(110,0),'XD_RAW_D':(151,-21),'X008':(196,0),'X009':(232,0),'X010':(268,0),'X011':(306,0),
         'XD_WRITE_D':(349,-21),'X013':(394,0),'X014':(433,0),
         'X000':(0,-72),'X001':(36,-72),'X015':(80,-72),'X016':(80,-112),'X017':(121,-112),
         'X018':(121,-72),'X019':(161,-72),'X020':(201,-72),'XD_QUIET_D':(243,-93),'X022':(288,-72),
         'X023':(329,-112),'XCLOCK':(372,-72),'X025':(417,-72)}
    for n,(x,y) in pos.items():s.place(n,x,y)
    s.local(exclude=('SAMPLE','SN','CMP_CLK','PHI_U','PHI_W'),distance=90)
    s.text(109,49,'VALID → WRITE → UPDATE',1.3);s.text(78,-46,'QUIET detection → SET / RESET latch → CMP_CLK',1.3)
    s.text(-18,-140,'Expand the delay and clock latch instances to inspect the timing path.',1)

def sar(s):
    s.text(-23,82,'8-bit SAR / one token, eight bit stores, asynchronous handshake',1.5)
    s.place('XTIM',0,39);s.place('XSEQ',0,-17)
    for k in range(7,-1,-1):s.place('XBIT'+str(k),73,-(7-k)*35)
    for i in range(4):s.place('X'+str(12+i).zfill(3),142,-i*70)
    s.place('X016',184,-35);s.place('X017',184,-175);s.place('X018',225,-105)
    for n in ['A0','A1','A2','A3','A01','A23','ACTIVE']:s.join(n,s.refs(n),'x',None)
    # Shared phase/data backbones, independently drawn so the order is legible.
    for i,n in enumerate(['DATA','PHI_W']):s.join(n,s.refs(n),'x',33+i*5,color='clock' if n=='PHI_W' else 'wire')
    s.text(121,-246,'OR reduction → ACTIVE',1.15)
    s.text(-23,-274,'T[7:0] selects one bit; CODE is the trial word and D the stored output. SAMPLE resets the controller.',.95)

def refword(s):
    s.text(-24,205,s.name+' / capture, sequential reset, nonoverlap and gate drive',1.5)
    if 'XRSTEP1' in s.parts:
        s.text(-24,187,'Sequential preset / bit 7 -> bit 0',1.1)
        for k in range(1,8):s.place('XRSTEP'+str(k),k*43,160)
        for k in range(7,-1,-1):s.place('XRR'+str(k),(7-k)*43,125)
        s.place('XRDONE',344,125)
        for k in range(1,8):
            refs=s.refs('TAP'+str(k));s.join('TAP'+str(k),refs,'x',k*43+20)
    s.text(-24,90,'Capture request / first and late clocks / acknowledge',1.1)
    pos={'X000':(0,65),'X001':(43,65),'X002':(86,65),'X007':(171,65),'X008':(214,65),
         'X003':(0,25),'XREQUEST':(43,25),'XD_LATE_CLK':(86,25),'XD_ACK':(129,25)}
    for n,(x,y) in pos.items():s.place(n,x,y)
    bottom=-25
    for k in range(7,-1,-1):
        y=bottom-(7-k)*38
        for typ,x in [('MUX',0),('STORE',86),('BBM',155),('DRV',218)]:
            n='X'+typ+str(k)
            if n in s.parts:s.place(n,x,y)
        s.text(-24,y+14,'bit '+str(k),1)
    s.place('X017',43,bottom);s.place('X018',118,bottom)
    s.local(exclude=('PHI_U','SAMPLE','PRESET','CAP_CLK','CAP_REQ'),distance=67)
    s.text(-24,bottom-7*38-27,'CODE / D → MUX → resettable storage → break-before-make → physical GP/GN drivers',1.1)

def graph(s):
    """Small ancillary levels and testbenches: sources → DUT → receiver/load.

    Clock inputs stay named. Unknown candidate internals get a complete pin
    drawing and are identified as an automatically placed schematic, not a
    hand-reviewed circuit layout.
    """
    sources=[];blocks=[];loads=[]
    for n,(_,m,_) in s.parts.items():
        (sources if m in {'vsource','isource'} else loads if m in {'cfmom_2t','capacitor','resistor','rupolym'} else blocks).append(n)
    for group,x in [(sources,-70),(blocks,0),(loads,90)]:
        for i,n in enumerate(group):s.place(n,x+(i//12)*55,-(i%12)*33)
    s.local(exclude=tuple(POWER|GROUND),distance=120)
    s.text(-89,30,s.name+' / source-derived connections',1.4)
    if not s.parts:
        s.text(-20,5,'Interface view only — no transistor body is distributed here.',1.2)
        s.text(-20,-2,'Ports: '+', '.join(s.ports[s.name]),.9)

def layout(name,body,portmap):
    s=Sheet(name,body,portmap)
    if name=='sar_adc8_join_r4':top(s)
    elif name=='sar_strongarm_t28':comparator(s)
    elif name=='sar_bootstrap_flat_8b_p':bootstrap(s)
    elif name=='sar8j_r1_cdac':cdac(s)
    elif re.fullmatch(r'sar8j_r1_sw_b\d',name):switch(s)
    elif 'R0' in s.parts and 'MN_CLEAR' in s.parts:delay(s)
    elif 'refdrv_b' in name:refdriver(s)
    elif name=='sar8p_bitseq8':bitseq(s)
    elif name=='sar8p_timing':timing(s)
    elif name in {'sar8i_ctrl','sar_logic_8b_physical'}:sar(s)
    elif name in {'sar8i_refword','sar8s_refword','sar8p_refword'}:
        if 'X000' in s.parts:refword(s)
        else:graph(s)
    else:simple(s)
    return s.finish()

def annotate(name,body,portmap):
    clean=strip(body)
    tail=re.search(r'(?m)^ends\b',clean)
    if not tail:raise ValueError('No subcircuit end: '+name)
    return clean[:tail.start()]+layout(name,clean,portmap)+clean[tail.start():],len(instances(clean))
