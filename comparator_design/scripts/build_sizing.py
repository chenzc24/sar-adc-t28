"""Comparator-only grouped parallel sizing; preserves original legal geometry."""
import argparse,json,re,math
from pathlib import Path
from setup import W,ROOT,write,recipe

GROUPS={'input':['M8','M9'],'tail':['M10'],'regen_n':['M6','M7'],'regen_p':['M0','M1'],
        'precharge':['M2','M3','M4','M5'],'out_n':['M12','M14'],'out_p':['M11','M13']}
CANDIDATES={
    'B0':dict(input=1,tail=1,regen_n=1,regen_p=1,precharge=1,out_n=1,out_p=1),
    'I4':dict(input=4,tail=1,regen_n=1,regen_p=1,precharge=1,out_n=1,out_p=1),
    'T4':dict(input=4,tail=4,regen_n=1,regen_p=1,precharge=1,out_n=1,out_p=1),
    'R2':dict(input=4,tail=4,regen_n=2,regen_p=2,precharge=1,out_n=1,out_p=1),
    'O4':dict(input=4,tail=4,regen_n=2,regen_p=2,precharge=1,out_n=4,out_p=8),
    'P4':dict(input=4,tail=4,regen_n=2,regen_p=2,precharge=4,out_n=4,out_p=8)}

def pwl(name,node,points):
    return '%s (%s 0) vsource type=pwl wave=[%s]\n'%(name,node,' '.join('%.12g %.12g'%p for p in points))

def build(run,chosen,corner='tt',vdd=.9,temp=27,load=6.1e-15):
    folder=W/'testbenches'/run;source=(W/'baseline/comparator.scs').read_text()
    models=(W/'baseline/models_tt.scs').read_text().replace('section=ttmacro_mos_moscap','section='+corner+'macro_mos_moscap')
    # No standard-cell instances in comparator-only sizing; keep native MOS sections.
    models=models.split('simulator lang=spice')[0]
    write(folder/'models.scs',models)
    definitions='simulator lang=spectre\n';devices={};group_map={m:g for g,ms in GROUPS.items() for m in ms}
    for name in chosen:
        block=source.replace('manual_cmp','cmp_'+name).replace('parameters cmp_mult=1\n','')
        rows=[];dev=[]
        for line in block.splitlines():
            if line.startswith('M'):
                m=re.match(r'(\S+) \((.*?)\)',line);dev.append({'name':m[1],'nodes':m[2].split(),'group':group_map[m[1]]})
                line=line.replace('multi=cmp_mult','multi='+str(CANDIDATES[name][group_map[m[1]]]))
            rows.append(line)
        assert len(dev)==15
        definitions+='\n'.join(rows)+'\n';devices[name]=dev
    write(folder/'dut.scs',definitions)
    lsb=1.8/256;small=.25*lsb
    patterns=[(.45,[small,-small,2*small,-2*small,4*small,-4*small,.85,-.85]),
              (.675,[small,-small,2*small,-2*small,4*small,-4*small,.4,-.4]),
              (.45+lsb/2,[small,-small,2*small,-2*small,4*small,-4*small,small,-small]),
              (.45,[.8,small,-.8,small,.8,-small,-.8,-small])]
    events=[];clock=[(0,0)];track=[(0,1.)];inp=[(0,.45+small/2)];inn=[(0,.45-small/2)]
    for frame,(cm,ds) in enumerate(patterns):
        for j,diff in enumerate(ds):
            t=(54+frame*100+4*j)*1e-9
            events.append({'t':t,'clock50':t+25e-12,'fall50':t+1.525e-9,'end':t+3.8e-9,'cm':cm,'diff':diff,'frame':frame})
            clock += [(t,0),(t+50e-12,vdd),(t+1.5e-9,vdd),(t+1.55e-9,0)]
            track += [(t-2e-9,track[-1][1]),(t-1.95e-9,1),(t-.55e-9,1),(t-.5e-9,0)]
            inp += [(t-1.9e-9,inp[-1][1]),(t-1.85e-9,cm+diff/2)]
            inn += [(t-1.9e-9,inn[-1][1]),(t-1.85e-9,cm-diff/2)]
    deck='simulator lang=spectre\ninclude "models.scs"\ninclude "dut.scs"\n'
    deck+=pwl('VCK','CK',clock)+pwl('VTRACK','TRACK',track)+pwl('VIP','IP',inp)+pwl('VIN','IN',inn)
    signals=['CK','VCK:1','TRACK','IP','IN'];contexts=[]
    for name in chosen:
        for mode in ['driven','held']:
            key=name+'_'+mode;up='U'+key;un='N'+key;pp='P'+key;op='OP'+key;on='ON'+key
            deck+='VS%s (%s 0) vsource dc=%.12g\n'%(key,up,vdd)
            if mode=='held':
                deck+='SP%s (IP %s TRACK 0) relay rclosed=1 ropen=1e15 vt1=.4 vt2=.6\n'%(key,pp)
                deck+='SN%s (IN %s TRACK 0) relay rclosed=1 ropen=1e15 vt1=.4 vt2=.6\n'%(key,un)
                deck+='CP%s (%s 0) capacitor c=1.28p\nCN%s (%s 0) capacitor c=1.28p\n'%(key,pp,key,un)
            else:pp='IP';un='IN'
            inst='X'+key
            deck+='%s (CK %s %s %s 0 %s %s) cmp_%s\n'%(inst,pp,un,up,op,on,name)
            deck+='CLP%s (%s 0) capacitor c=%.12g\nCLN%s (%s 0) capacitor c=%.12g\n'%(key,op,load,key,on,load)
            mapping=dict(CLK='CK',VINP=pp,VINN=un,VDD=up,GND='0',DCMPP=op,DCMPN=on)
            ds=[]
            for dev in devices[name]:
                nodes=[mapping.get(n,inst+'.'+n) for n in dev['nodes']]
                ds.append({'name':dev['name'],'nodes':nodes,'group':dev['group']})
                signals += [n for n in nodes if n!='0']
            signals += ['VS'+key+':1']
            contexts.append({'name':key,'candidate':name,'mode':mode,'devices':ds,'supply_current':'VS'+key+':1',
                             'vinp':pp,'vinn':un,'op':op,'on':on,'internal':[inst+'.'+n for n in ['LP','LN','net1','net2']]})
    signals=sorted(set(signals));stop=400e-9
    deck+='simulatorOptions options reltol=1e-6 vabstol=1e-8 iabstol=1e-14 temp=%g tnom=27\nsaveOptions options save=selected currents=selected\ntran_test tran stop=400n maxstep=20p errpreset=conservative\nsave '%temp+' '.join(signals)+'\n'
    write(folder/'test.scs',deck)
    cfg={'run_id':run,'vdd':vdd,'corner':corner,'temperature_c':temp,'stop_s':stop,'load_F':load,'events':events,
         'signals':signals,'contexts':contexts,'candidates':{k:CANDIDATES[k] for k in chosen},'terminal_limit_V':.99,
         'goals':{'decision_s':1e-9,'reset_s':.5e-9,'residual_V':.1*lsb,'power_W':100e-6}}
    write(folder/'measure.json',json.dumps(cfg,indent=2))
    recipe(run,folder,signals,stop,'sizing_reduce.py',{'corner':corner,'vdd':vdd,'temperature_c':temp,'noise':False,'mismatch':False,'PEX':False})
    print('Built',run,chosen,'with output load',load)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',default='cmpdesign-sizing-tt-v1');p.add_argument('--candidates',default=','.join(CANDIDATES))
    p.add_argument('--corner',default='tt');p.add_argument('--vdd',type=float,default=.9);p.add_argument('--temp',type=float,default=27);p.add_argument('--load',type=float,default=6.1e-15)
    a=p.parse_args();build(a.run,a.candidates.split(','),a.corner,a.vdd,a.temp,a.load)
