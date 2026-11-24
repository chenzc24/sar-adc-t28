"""Curated drawing recipes. Connectivity always comes from the Spectre instances.

These recipes seed editable @RNL comments; normal drawing reads those comments.
They deliberately keep clocks and supplies named at distant sections. Analog
signal paths, storage paths, local feedback and RC nodes are physically wired.
"""
import re
from .rnl import Sheet, POWER, GROUND, instances, strip

def top(s):
    s.text(-29,84,'SAR8   /   Asynchronous differential ADC',2.75)
    s.text(-29,76,'Sample control',1.35)
    s.text(111,76,'Reference preset',1.35)
    for n,x,y in [('XSAMPLE',0,62),('XSEQ',36,62),('XDONE',132,62),('XPRESET',161,62),
                  ('XBOOTN',0,27),('XBOOTP',0,4),('XCDAC',46,-12),
                  ('XCOMP',94,18),('XCTRL',139,18),('XREF',46,-48),
                  ('CL_COMP_N',113,-13),('CL_COMP_P',127,-24),('CL_CMP_CLK',95,51)]:
        s.place(n,x,y,'MX' if n=='CL_CMP_CLK' else 'R0')
    for n,label,dy in [('XSAMPLE','Buffer',0),('XSEQ','Acquisition',0),('XDONE','Done',8),
                       ('XPRESET','Preset',0),('XBOOTN','Sampler N',0),('XBOOTP','Sampler P',0),
                       ('XCDAC','MOM CDAC',0),('XCOMP','StrongARM',0),
                       ('XCTRL','SAR',5),('XREF','Reference drive',0)]:
        s.caption(n,label,dy)
    for n in ('CL_COMP_N','CL_COMP_P','CL_CMP_CLK'):
        s.emit('#'+n+' @TEXT("",key="value");')
    s.input_port('XSAMPLE:I',color='clock')
    s.input_port('XBOOTN:Vin',color='analog')
    s.input_port('XBOOTP:Vin',color='analog')
    s.route('XSAMPLE:Z','XSEQ:REQUEST')
    s.route('XDONE:Y','XPRESET:A1')
    for side,rail_y in [('N',27),('P',7)]:
        boot='XBOOT'+side+':VOUT';comp='XCOMP:VIN'+side;cdac='XCDAC:TOP'+side
        xb,yb=s.pin(boot)[0];xc,yc=s.pin(comp)[0];xd,_=s.pin(cdac)[0]
        branch=(xd,rail_y)
        lead=[(xb+6,yb),(xb+6,rail_y)] if yb!=rail_y else []
        s.wire('TOP'+side,boot,*lead,branch,(xc-6,rail_y),(xc-6,yc),comp,color='analog')
        s.wire('TOP'+side,cdac,branch,color='analog');s.dot(branch)
        s.text(xd+8,rail_y+1.6,'TOP'+side,1.13)
    for n,x in [('COMP_N',113),('COMP_P',122)]:
        s.join(n,['XCOMP:OUT'+n[-1],'XCTRL:'+n,'CL_'+n+':1'],'x',x,color='analog')
    s.join('CMP_CLK',['XCTRL:CMP_CLK','XCOMP:CLK','CL_CMP_CLK:1'],'y',42,color='clock')
    for prefix in ('GNN','GNP','GPN','GPP'):
        s.bus([('XREF',prefix+'0'),('XCDAC',prefix+'0')],[],color='#536f4b')
    for i,prefix in enumerate(('CODE','D')):
        a=s.pin('XCTRL:'+prefix+'0')[0];b=s.pin('XREF:'+prefix+'0')[0];x=161+i*9
        s.bus([('XCTRL',prefix+'0'),('XREF',prefix+'0')],[(x,a[1]),(x,b[1])],color='#66538a')
    s.text(121,-37,'Digital feedback',1.3)

def comparator(s):
    s.text(-48,68,'StrongARM  /  differential latch',1.7)
    placement={'MPLATN':(-20,42),'MPLATP':(20,42),'MNLATN':(-20,20),'MNLATP':(20,20),
               'MNINP':(-20,-5),'MNINN':(20,-5),'MNTAIL':(0,-30),
               'MPRSTN':(-42,42),'MPRSTP':(42,42),'MPRSTY':(-42,10),'MPRSTX':(42,10)}
    for n,(x,y) in placement.items():
        mirrored=(x<0 if n.startswith(('MPLAT','MNLAT')) else x>0)
        s.place(n,x,y,'MY' if mirrored else 'R0')
    s.join('VDD',[n+':3' for n in ('MPLATN','MPLATP','MPRSTN','MPRSTP')],'y',61,color='power')
    for name,outer in [('MPRSTY',-55),('MPRSTX',55)]:
        x,y=placement[name]
        s.wire('VDD',name+':3',(x,y+5),(outer,y+5),(outer,61),(x,61),color='power')
    s.join('OUTN',['MPLATN:1','MNLATN:1','MPRSTN:1'],'y',31,color='analog')
    s.join('OUTP',['MPLATP:1','MNLATP:1','MPRSTP:1'],'y',33,color='analog')
    s.wire('OUTN','MPLATN:1',(-20,36),(8,36),(8,42),'MPLATP:2',color='analog')
    s.wire('OUTN',(8,36),(8,20),'MNLATP:2',color='analog');s.dot((8,36))
    s.wire('OUTP','MPLATP:1',(20,28),(-8,28),(-8,42),'MPLATN:2',color='analog')
    s.wire('OUTP',(-8,28),(-8,20),'MNLATN:2',color='analog');s.dot((-8,28))
    s.join('Y',['MNLATN:3','MNINP:1','MPRSTY:1'],'y',4,color='analog')
    s.join('X',['MNLATP:3','MNINN:1','MPRSTX:1'],'y',4,color='analog')
    s.join('TAIL',['MNINP:3','MNINN:3','MNTAIL:1'],'y',-18,color='analog')

def bootstrap(s):
    s.text(-13,67,'Bootstrap  /  four parallel sampling switches',1.65)
    mains=['Mmain','Mmain_U1','Mmain_U2','Mmain_U3']
    pos={'MPCLK':(0,35),'MNCLK':(0,5),'M4B':(38,35),'M4C':(38,5),'M4A':(56,5),
         'Cboot':(80,21),'M2':(80,48),'M8':(80,-9),'Msin':(101,-9),
         'M4':(116,43),'Maux':(116,4),'MRSTG':(116,-22),
         'Mmain_U3':(158,38),'Mmain':(158,17),'Mmain_U1':(158,-4),'Mmain_U2':(158,-25)}
    for n,(x,y) in pos.items():s.place(n,x,y,'R270' if n.startswith('Mmain') else 'R0')
    s.join('CLKSB',['MPCLK:1','MNCLK:1'],'y',20)
    s.join('CTRL',['M4A:1','M4:2'],'y',60)
    s.wire('CTRL',(28,60),(31,60),(56,60))
    s.wire('CTRL','M4B:1',(38,29),(31,29),(31,60));s.dot((31,60))
    s.wire('CTRL','M4C:1',(38,12),(28,12),(28,60));s.dot((28,60))
    s.join('BTOP',['Cboot:1','M2:1'],'y',31,color='analog')
    s.wire('BTOP','M4:3',(116,48),(124,48),(124,31),(80,31),color='analog')
    s.join('BBOT',['Cboot:2','M4C:3','M4A:3','M8:1','Msin:1'],'y',-2,color='analog')
    s.join('G',['M4:1','Maux:1']+[m+':2' for m in mains],'x',138,color='analog')
    s.route('Maux:3','MRSTG:1')
    s.join('Vin',['Msin:3']+[m+':3' for m in mains],'x',146,color='analog')
    s.join('VOUT',[m+':1' for m in mains],'x',177,color='analog')
    s.text(-13,-37,'Clock inverter',1.15);s.text(33,-37,'Precharge and boost',1.15);s.text(144,-37,'Vin → VOUT',1.15)

def switch(s):
    s.place('MP_HIGH',0,20);s.place('MN_LOW',0,-10)
    s.join('BOT',['MP_HIGH:1','MN_LOW:1'],'y',5,color='analog')
    s.text(-20,48,s.name+' / real reference switches',1.3)

def cdac(s):
    s.text(-15,68,'Differential MOM CDAC  /  binary weights and unit dummy',1.65)
    for side,y in [('N',34),('P',-32)]:
        caprefs=[]
        for k in range(9):
            x=k*38;n='CMOM'+side+str(k);s.place(n,x,y);caprefs.append(n+':1')
            if k<8:
                sw='XS'+side+str(k);s.place(sw,x,y-22)
                s.route(n+':2',sw+':BOT')
        s.join('TOP'+side,caprefs,'y',y+12,color='analog')
        s.text(-15,y+20,'TOP'+side+' / '+('negative' if side=='N' else 'positive')+' bank',1.2)
        s.text(289,y-18,'Dummy → '+s.parts['CMOM'+side+'8'][0][1],1)

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


def placed_row(s, names, y, start=0, pitch=34):
    for column,name in enumerate(names):
        s.place(name,start+pitch*column,y)


def se_controller(s):
    s.text(-18,84,'Single-edge SAR',2.15)
    s.text(-18,67,'Compare / timing',1.25)
    s.text(56,67,'Next trial word',1.25)
    s.text(147,67,'Completion',1.25)
    placed_row(s,('XTIM','XWORD','XDONE','XACTIVE'),44,pitch=57)
    s.text(-18,20,'Registered settling taps',1.35)
    for row,bit in enumerate((9,7,6,5,4)):
        placed_row(s,tuple('XSEL'+str(bit)+suffix for suffix in ('_QB','_TB','_D','')),-row*26,pitch=31)
    s.text(122,20,'Bit stores',1.35)
    for bit in range(8):
        s.place(f'XBIT{bit}',140+(bit%2)*34,-(bit//2)*28)
    placed_row(s,('XMSBD','XMSBQ'),-112,start=140,pitch=42)
    s.local(distance=41)


def se_timing(s):
    s.text(-17,54,'Asynchronous compare and commit timing',2.05)
    rows=[('Latch decision',('XPR','XNR','XNRB','XDATA','XRAW','XVD','XVALID')),
          ('Commit and phase',('XSN','XW0','XW1','XCP','XPHA','XPHBN','XPHB','XPHX')),
          ('Settling window',('XPHR','XWINDOW','XREADY','XCLR','XSND1','XSND2','XSNQ')),
          ('Comparator clock',('XLIVE','XIDLE','XSET0','XSET','XHIGH','XCLOCK','XCMP'))]
    for index,(label,names) in enumerate(rows):
        y=22-index*50;s.text(-17,y+15,label,1.35);placed_row(s,names,y,pitch=39)
    s.local(distance=45)


def se_window(s):
    s.text(-14,59,'Settling window / delay chain and selected taps',1.9)
    placed_row(s,tuple(f'XDEL{k}' for k in range(1,12)),25,pitch=27)
    placed_row(s,tuple(f'XTAP{k}' for k in (4,5,6,7,9)),-24,pitch=54)
    for k in range(1,11):
        first=f'XDEL{k}';second=f'XDEL{k+1}'
        # The common terminal follows the actual stage-to-stage connection.
        common=(set(s.parts[first][0]) & set(s.parts[second][0])) - POWER - GROUND
        if len(common)==1:
            n=next(iter(common));a,b=(f'{inst}:{s.parts[inst][0].index(n)+1}' for inst in (first,second));s.route(a,b)
    s.local(distance=58)


def next_word(s):
    s.text(-18,45,'Next trial word',2)
    placed_row(s,('X01','X23','X45','X02','X03','X04','X05','X06'),22,pitch=34)
    for bit in range(8):
        names=[f'X{prefix}{bit}' for prefix in ('EMPTY','TRIAL','VISIBLE','READ','BASE','KEEP','NEXT')]
        y=-12-bit*32;s.text(-24,y+7,f'Bit {bit}',1.2)
        for column,name in enumerate(names):
            if name in s.parts:s.place(name,column*35,y)
    s.local(distance=39)


def se_reference(s):
    s.text(-17,70,'Single-edge reference decode and switch drive',2)
    placed_row(s,('XPRESET_N','WUNUSED'),38,pitch=31)
    for bit in range(8):
        names=[name for name in (f'XINITIAL{bit}_A',f'XINITIAL{bit}_B',f'XINITIAL{bit}',f'XINV{bit}',
                                 f'XPN{bit}',f'XNN{bit}',f'WNP{bit}',f'WPP{bit}') if name in s.parts]
        y=9-bit*25;s.text(-18,y+8,f'Bit {bit}',1.2);placed_row(s,names,y,pitch=34)
    s.local(distance=42)

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
    elif name=='sar8_se_ctrl':se_controller(s)
    elif name=='sar8_se_timing':se_timing(s)
    elif name=='sar8_se_window':se_window(s)
    elif name=='sar8_next_word':next_word(s)
    elif name=='sar8i_refword' and 'XPRESET_N' in s.parts:se_reference(s)
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
