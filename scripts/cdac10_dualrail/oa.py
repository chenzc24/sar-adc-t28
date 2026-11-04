"""Independent native OA builds; old Bootstrap/StrongARM/MOM masters are read-only."""
import argparse
from common import ROOT, OUT, LIB, dump
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_inst_by_master_name as inst, schematic_create_pin as pin, schematic_label_instance_term as term
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
from virtuoso_bridge.virtuoso.symbol.ops import symbol_create_rect, symbol_create_selection_box, symbol_create_pin, symbol_create_instance_label, symbol_create_logical_label, symbol_set_term_order

CTRL_IN=['COMP_P','COMP_N','PHI','PREPARE','HOLD_START','CLK_LATCH','CLK_COMPARE','VDD','VSS']
CTRL_OUT=['PH<8:0>','PL<8:0>','NH<8:0>','NL<8:0>','DOUT<9:0>','BUSY','VALID','CMP_CLK','CMP_RESET']
ARRAY_IN=['PH<8:0>','PL<8:0>','NH<8:0>','NL<8:0>','VREFP','VREFN','VDD','VSS']
ARRAY_OUT=['TOPP','TOPN']
GEO={'Wfinger':'50n','Sfinger':'50n','Lfinger':'2u','Nfinger':'8','StartMn':'1','StopMn':'3','mismatch':'1'}

def skill(c, expr):
    r=c.execute_skill(expr,timeout=180)
    assert not r.errors, r
    return r.output

def refuse(c, cell):
    assert skill(c,f'ddGetObj("{LIB}" "{cell}")').strip()=='nil', f'Refuse existing {cell}'

def add(s,name,master,x,y,terms,lib='analogLib'):
    s.add(inst(lib,master,'symbol',name,x,y,'R0'))
    for t,n in terms.items(): s.add(term(name,t,n))

def params(c,cell,values):
    # Reuse the bridge's verified callback expressions, grouped to reduce SSH
    # round trips. Every expression still targets its explicit library/cell.
    from types import SimpleNamespace
    class Queue:
        def __init__(self): self.expressions=[]
        def execute_skill(self,expr,timeout=30):
            self.expressions.append(expr)
            return SimpleNamespace(errors=[])
    queue=Queue()
    for name,p in values.items():
        _run_batched_param_update(queue,LIB,cell,name,{k:str(v) for k,v in p.items()})
    for j in range(0,len(queue.expressions),8):
        skill(c,'progn('+' '.join(queue.expressions[j:j+8])+')')

def pins(s,inputs,outputs,xout=130):
    for j,n in enumerate(inputs): s.add(pin(n,-12,12-j,'R0',direction='input'))
    for j,n in enumerate(outputs): s.add(pin(n,xout,12-3*j,'R180',direction='inputOutput'))

def symbol(c,cell,inputs,outputs,output_direction='inputOutput'):
    h=max(len(inputs),len(outputs))*.6+1
    with c.symbol.create(LIB,cell,timeout=180) as s:
        s.add(symbol_create_rect('device','drawing',.75,-.5,7.25,h))
        s.add(symbol_create_selection_box(0,-.75,8,h+.25))
        for names,x,lx,direction,just in ((inputs,0,.9,'input','centerLeft'),(outputs,8,7.1,output_direction,'centerRight')):
            for j,n in enumerate(names):
                y=h-.5-j*.6
                s.add(symbol_create_pin(n,x,y,direction=direction,half_size=.025,label_x=lx,label_y=y,label_justification=just))
        s.add(symbol_create_instance_label(2,h+.4)); s.add(symbol_create_logical_label(4,h/2))
        s.add(symbol_set_term_order(inputs+outputs))

def check(c,cell):
    with c.schematic.modify(LIB,cell,timeout=180): pass
    d=c.schematic.read(LIB,cell,param_filters=None,include_positions=True)
    dump(f'oa/{cell}.json',d)
    marks=c.fetch(f'dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")~>markers',['objType','severity','bBox'])
    dump(f'oa/{cell}_markers.json',marks)
    assert not marks,(cell,marks)
    print('OA_OK',cell,flush=True)
    return d

def export(c,cell,tag='initial'):
    check(c,cell)
    dst=OUT/'oa_netlists'/cell/tag
    assert not (dst/'input.scs').exists(),f'Preserve exact export {cell}'
    r=c.schematic.export_netlist(LIB,cell,dst,simulator='spectre',timeout=180)
    dump(f'oa/{cell}_{tag}_export.json',r)
    print('EXPORTED',cell,flush=True)

def mos(s,name,master,x,y,d,g,src,body):
    s.add(inst('tsmcN28',master,'symbol',name,x,y,'R0'))
    s.add_net_label_to_transistor(name,drain_net=d,gate_net=g,source_net=src,body_net=body)

def switches(c):
    for bit in range(9):
        cell=f'cdac10_dr_sw_b{bit}'; refuse(c,cell); values={}
        inputs=['EH','EL','VREFP','VREFN','VDD','VSS']
        rows=[('MP_HIGH','pch_mac',8,6,'BOT','EH_B','VREFP','VDD',.175,'MULT_R'),
              ('MN_LOW','nch_mac',8,1,'BOT','EL_D','VREFN','VSS',.15,'MULT_R'),
              ('MN_IH','nch_mac',0,1,'EH_B','EH','VSS','VSS',.25,'MULT_D'),
              ('MP_IH','pch_mac',0,6,'EH_B','EH','VDD','VDD',.30,'MULT_D'),
              ('MN_IL1','nch_mac',0,-9,'EL_B','EL','VSS','VSS',.25,'MULT_D'),
              ('MP_IL1','pch_mac',0,-4,'EL_B','EL','VDD','VDD',.30,'MULT_D'),
              ('MN_IL2','nch_mac',8,-9,'EL_D','EL_B','VSS','VSS',.25,'MULT_D'),
              ('MP_IL2','pch_mac',8,-4,'EL_D','EL_B','VDD','VDD',.30,'MULT_D')]
        with c.schematic.create(LIB,cell,timeout=180) as s:
            pins(s,inputs,['BOT'],xout=25)
            for name,master,x,y,d,g,src,body,w,mult in rows:
                mos(s,name,master,x,y,d,g,src,body)
                values[name]={'Wfg':f'{w}u','w':f'{w}u','l':'30n','fingers':'1','simM':f'{1<<bit}*{mult}'}
        params(c,cell,values); symbol(c,cell,inputs,['BOT']); check(c,cell)

def arrays(c):
    cell='cdac10_dr_bank256'; refuse(c,cell)
    with c.schematic.create(LIB,cell,timeout=180) as s:
        pins(s,[],['TOP','BOT'],xout=25)
        for j in range(2): add(s,f'X128_{j}','cdac8_bank_128',j*12,0,{'TOP':'TOP','BOT':'BOT'},LIB)
    c.symbol.generate_from_schematic(LIB,cell,overwrite=False,timeout=120);check(c,cell)
    for literal in (False,True):
        cell='cdac10_dr_literal' if literal else 'cdac10_dr_nominal';refuse(c,cell);values={}
        with c.schematic.create(LIB,cell,timeout=180) as s:
            pins(s,ARRAY_IN,ARRAY_OUT)
            for side,y in [('P',25),('N',-20)]:
                for b in range(10):
                    weight=1<<b if b<9 else 1
                    bot=f'B{side}{b}' if b<9 else 'VREFP'
                    name=f'XC{side}{b}' if literal else f'CMOM{side}{b}'
                    terms={'TOP':'TOP'+side,'BOT':bot} if literal else {'PLUS':'TOP'+side,'MINUS':bot}
                    master=('cdac10_dr_bank256' if b==8 else f'cdac8_bank_{weight}') if literal else 'cfmom_2t'
                    add(s,name,master,b*12,y,terms,LIB if literal else 'tsmcN28')
                    if not literal:values[name]={**GEO,'m':str(weight)}
                    if b<9:
                        add(s,f'XS{side}{b}',f'cdac10_dr_sw_b{b}',b*12,y-14,
                            {'BOT':bot,'EH':f'{side}H<{b}>','EL':f'{side}L<{b}>','VREFP':'VREFP','VREFN':'VREFN','VDD':'VDD','VSS':'VSS'},LIB)
        params(c,cell,values);symbol(c,cell,ARRAY_IN,ARRAY_OUT);check(c,cell)

def import_va(c,cell,inputs,outputs,defaults):
    refuse(c,cell);symbol(c,cell,inputs,outputs,'output')
    skill(c,f'schViewToView("{LIB}" "{cell}" "{LIB}" "{cell}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    r=c.upload_file(ROOT/f'models/veriloga/{cell}.va',f'/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{cell}/veriloga/veriloga.va',timeout=120)
    assert not r.errors,r
    skill(c,f'ahdlUpdateViewInfo("{LIB}" ?cell "{cell}" ?view "veriloga")')
    if defaults:
        ps=' '.join(f'cdfCreateParam(d ?name "{n}" ?prompt "{n}" ?type "string" ?defValue "{v}" ?parseAsNumber "yes" ?parseAsCEL "yes")' for n,v in defaults.items())
        skill(c,f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{cell}")) unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "{cell}"))) {ps} cdfSaveCDF(d))')
    dump(f'oa/{cell}_ports.json',c.symbol.read_ports(LIB,cell))
    print('VA_IMPORTED',cell,flush=True)

def controls(c):
    import_va(c,'cdac10_dualrail_controller',CTRL_IN,CTRL_OUT,{'dead_time_s':'100p'})
    import_va(c,'cdac10_dualrail_input',['VDD','VSS'],['VINP_SRC','VINN_SRC'],
              {'stimulus_mode':'0','differential_v':'0','frequency_hz':'4.4921875Meg'})
    import_va(c,'cdac10_dualrail_comparator',['VINP','VINN','CLK','VDD','VSS'],['OUTP','OUTN'],{})

def bench(c,cell,array='cdac10_dr_nominal',strongarm=False,ideal_sample=False):
    refuse(c,cell);values={}
    with c.schematic.create(LIB,cell,timeout=180) as s:
        add(s,'XCDAC',array,0,8,{**{n:n for n in ARRAY_IN+ARRAY_OUT},'VDD':'VDD!','VSS':'gnd!'},LIB)
        add(s,'XCTRL','cdac10_dualrail_controller',28,8,{**{n:n for n in CTRL_IN+CTRL_OUT},'VDD':'VDD!','VSS':'gnd!'},LIB)
        values['XCTRL']={'dead_time_s':'DEAD_TIME'}
        add(s,'XINPUT','cdac10_dualrail_input',-28,-4,{'VDD':'VDD!','VSS':'gnd!','VINP_SRC':'VINP_SRC','VINN_SRC':'VINN_SRC'},LIB)
        values['XINPUT']={'stimulus_mode':'STIM_MODE','differential_v':'VDIFF','frequency_hz':'FIN'}
        for side,y in [('P',17),('N',-7)]:
            add(s,'RIN'+side,'res',-20,y,{'PLUS':'VIN'+side+'_SRC','MINUS':'VIN'+side});values['RIN'+side]={'r':'50'}
            if ideal_sample:
                add(s,'SSAMPLE'+side,'switch',-10,y,{'N+':'VIN'+side,'N-':'TOP'+side,'NC+':'PHI','NC-':'gnd!'})
                values['SSAMPLE'+side]={'rc':'150','ro':'1T','vt1':'.35','vt2':'.55'}
            else:
                add(s,'XBOOT'+side,'sar_bootstrap_canvas_flat_8b',-10,y,{'CLKS':'PHI','CLKSB':'CLKB'+side,'Vin':'VIN'+side,'VOUT':'TOP'+side},LIB)
                add(s,'RMON'+side,'res',-2,y-3,{'PLUS':'CLKB'+side,'MINUS':'gnd!'});values['RMON'+side]={'r':'1T'}
        if strongarm:
            add(s,'XCOMP','sar_strongarm_t28',13,17,{'CLK':'CMP_CLK','VINP':'TOPP','VINN':'TOPN','OUTP':'COMP_P','OUTN':'COMP_N','VDD':'VDD!','VSS':'gnd!'},LIB)
        else:
            add(s,'XCOMP','cdac10_dualrail_comparator',13,17,{'CLK':'CMP_CLK','VINP':'TOPP','VINN':'TOPN','OUTP':'COMP_P','OUTN':'COMP_N','VDD':'VDD!','VSS':'gnd!'},LIB)
        for j,n in enumerate(['COMP_P','COMP_N']):
            add(s,f'COMPLOAD{j}','cap',49,18-j*4,{'PLUS':n,'MINUS':'gnd!'});values[f'COMPLOAD{j}']={'c':'5f'}
        add(s,'RRST','res',49,10,{'PLUS':'CMP_RESET','MINUS':'gnd!'});values['RRST']={'r':'1T'}
        for j,(name,net,dc) in enumerate([('VVDD','VDD!','SUP'),('VREFHIGH','VREFP_SRC','SUP'),('VREFLOW','VREFN_SRC','0')]):
            add(s,name,'vdc',-25+j*5,-22,{'PLUS':net,'MINUS':'gnd!'});values[name]={'vdc':dc}
        for j,(name,net,delay,width,period,edge) in enumerate([
            ('VPHI','PHI','1n','39.9n','100n','100p'),('VPREP','PREPARE','94n','200p','100n','20p'),
            ('VHOLD','HOLD_START','43n','200p','100n','20p'),('VLATCH','CLK_LATCH','47.5n','200p','5n','20p'),
            ('VCOMPARE','CLK_COMPARE','46n','1.53n','5n','20p')]):
            add(s,name,'vpulse',-5+j*5,-27,{'PLUS':net,'MINUS':'gnd!'});values[name]={'v1':'0','v2':'SUP','td':delay,'pw':width,'per':period,'tr':edge,'tf':edge}
        for j,side in enumerate('PN'):
            add(s,'RREF'+side,'res',13+j*6,-8,{'PLUS':'VREF'+side+'_SRC','MINUS':'VREF'+side});values['RREF'+side]={'r':'RREF'}
            add(s,'CREF'+side,'cap',13+j*6,-13,{'PLUS':'VREF'+side,'MINUS':'gnd!'});values['CREF'+side]={'c':'CDECAP'}
        for j,net in enumerate([*[f'DOUT<{b}>' for b in range(10)],'BUSY','VALID']):
            nm=f'RLOAD{j}';add(s,nm,'res',28+j*2,-22,{'PLUS':net,'MINUS':'gnd!'});values[nm]={'r':'1G'}
    params(c,cell,values);c.open_window(LIB,cell,view='schematic');export(c,cell)

def reset_phase(c):
    for cell in ['tb_cdac10_dr_nominal','tb_cdac10_dr_literal','tb_cdac10_dr_strongarm','tb_cdac10_dr_ideal_sample']:
        skill(c,f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{cell}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
        params(c,cell,{'VPHI':{'v1':'SUP','v2':'0','td':'41n','pw':'52.9n'},'VPREP':{'td':'3n'}})
        export(c,cell,'sample_reset')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['switches','arrays','controls','benches','reset-phase']);a=p.parse_args()
    c=VirtuosoClient.from_env(profile='t28_io')
    if a.action=='benches':
        for cell,arr,strong,ideal in [('tb_cdac10_dr_nominal','cdac10_dr_nominal',False,False),
            ('tb_cdac10_dr_literal','cdac10_dr_literal',False,False),('tb_cdac10_dr_strongarm','cdac10_dr_nominal',True,False),
            ('tb_cdac10_dr_ideal_sample','cdac10_dr_nominal',False,True)]:
            bench(c,cell,arr,strong,ideal)
    else: {'switches':switches,'arrays':arrays,'controls':controls,'reset-phase':reset_phase}[a.action](c)

if __name__=='__main__':main()
