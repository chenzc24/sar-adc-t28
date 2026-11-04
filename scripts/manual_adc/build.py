"""Freeze manual OA-derived netlists; never writes OA or launches simulation."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/manual_adc'
NATIVE=ROOT/'output/manual_adc/native'
LIB='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a/tcbn28hpcplusbwp12t30p140_170a.spi'
def clean(s):
 s=s.replace('\\\n',' ')
 return re.sub(r'\\<([0-9]+)\\>',r'_\1',s)
def body(cell):
 s=(NATIVE/cell/'input.scs').read_text()
 marker='// Cell name: '+cell+'\n// View name: schematic\n'
 return clean(s.split(marker)[-1].split('simulatorOptions')[0]).strip()
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def build():
 boot=body('L2_bootstrap_switch')
 boot=re.sub(r'(M0 .*?multi=)1\b',r'\g<1>main_mult',boot)
 cmp=body('L2_StrongArm_CMP')
 cmp=re.sub(r'multi=1\b','multi=cmp_mult',cmp)
 cdac=body('L2_CDAC_8bit').replace('L2_bootstrap_switch','manual_boot')
 cdac=cdac.replace('I1 (CLKS GND VDD VIN VTOP) manual_boot','I1 (CLKS GND VDD VIN VTOP) manual_boot main_mult=main_mult')
 sar=body('L2_SAR_logic')
 sar=re.sub(r'( VALID )CLKS( CLK_\d VDD GND\) DFCN)',r'\1CLKSN\2',sar)
 sar='IRESET (CLKS CLKSN VDD GND) INVD4BWP12T30P140\n'+sar
 raw={7:'net31',6:'net33',5:'net24',4:'net27',3:'net28',2:'net29',1:'net30',0:'net14'}
 for bit,node in raw.items():
  sar=sar.replace('I46_%d (DCTRLP_%d CLKS'%(bit,bit),'I46_%d (%s CLKS'%(bit,node))
 sar=sar.replace('td=5n','td=tloop').replace('td=100p','td=tgate')
 ports=['CLKS','GND','VDD','DCMPP','DCMPN','CMPCK']+['DO_'+str(i) for i in range(7,-1,-1)]+['DCTRL'+s+'_'+str(i) for s in ['P','N'] for i in range(7,-1,-1)]
 text='// Native-derived candidate, external standard library unchanged.\n'
 for name,ps,b,params in [('manual_boot','CLKS GND VDD VIN VOUT',boot,'main_mult=1'),('manual_cmp','CLK VINP VINN VDD GND DCMPP DCMPN',cmp,'cmp_mult=1'),('manual_cdac','CLKS GND VDD VIN VTOP VREFP VREFN '+' '.join('DCTRL_'+str(i) for i in range(7,0,-1)),cdac,'cunit=10f main_mult=1'),('manual_sar',' '.join(ports),sar,'tloop=2n tgate=100p')]:
  text+='\nsubckt '+name+' '+ps+'\nparameters '+params+'\n'+b+'\nends '+name+'\n'
 topports='CLKS GND VDD VINP VINN VREFP VREFN '+' '.join('DO_'+str(i) for i in range(7,-1,-1))
 text+='\nsubckt manual_adc '+topports+'\nparameters cunit=10f main_mult=1 cmp_mult=1 tloop=2n tgate=100p\n'
 text+='XP (CLKS GND VDD VINP TOPP VREFP VREFN DN_7 '+' '.join('DP_'+str(i) for i in range(6,0,-1))+') manual_cdac cunit=cunit main_mult=main_mult\n'
 text+='XN (CLKS GND VDD VINN TOPN VREFP VREFN DP_7 '+' '.join('DN_'+str(i) for i in range(6,0,-1))+') manual_cdac cunit=cunit main_mult=main_mult\n'
 text+='XC (CMPCK TOPP TOPN VDD GND DCMPP DCMPN) manual_cmp cmp_mult=cmp_mult\n'
 text+='XL (CLKS GND VDD DCMPP DCMPN CMPCK '+' '.join('DO_'+str(i) for i in range(7,-1,-1))+' '+' '.join('D'+s+'_'+str(i) for s in ['P','N'] for i in range(7,-1,-1))+') manual_sar tloop=tloop tgate=tgate\nends manual_adc\n'
 write(OUT/'candidate_v1/dut.scs',text)
 header='\n'.join(l for l in (NATIVE/'L2_bootstrap_switch/input.scs').read_text().splitlines() if l.startswith('include '))
 write(OUT/'candidate_v1/models.scs','simulator lang=spectre\nglobal 0\n'+header+'\nsimulator lang=spice\n.include "'+LIB+'"\nsimulator lang=spectre\n')
 identity={f.parent.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in NATIVE.glob('*/input.scs')}
 write(OUT/'candidate_v1/provenance.json',json.dumps(dict(native_exports_sha256=identity,source='SAR_ADC_T28_manual read-only OCEAN export',changes=['CDN uses standard inverter of CLKS','first bit only crossed at new top','output latches read original positive decisions','feedback delay parameterized default2ns; original5ns','all source ground aliases unified'],initial_parameters={'cunit_F':1e-14,'total_cap_per_side_F':1.28e-12,'main_mult':1,'cmp_mult':1,'tloop_s':2e-9},note='Native CDAC nf=10 for NMOS differs from live CDF nf=1; retain actual emitted native parameters; no hand CDF reinterpretation'),indent=2)+'\n')
 return ports
def pulse(name,node,delay,width,period=100):return '%s (%s 0) vsource type=pulse val0=0 val1=.9 delay=%gn rise=50p fall=50p width=%gn period=%gn\n'%(name,node,delay,width,period)
def make_case(name,extra,stop,saves):
 p=OUT/name;p.mkdir(exist_ok=True)
 for f in ['dut.scs','models.scs']:(p/f).write_bytes((OUT/'candidate_v1'/f).read_bytes())
 deck='simulator lang=spectre\ninclude "models.scs"\ninclude "dut.scs"\nVVDD (VDD 0) vsource dc=.9\n'+extra
 deck+='simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp=27 tnom=27 gmin=1e-12 checklimitdest=psf\nsaveOptions options save=selected currents=selected\ntran_test tran stop=%gn maxstep=20p errpreset=conservative\n'%stop
 if name.startswith('logic_codes'):deck=deck.replace('maxstep=20p','maxstep=200p')
 deck+='save '+' '.join(sorted(set(saves+['VDD','VVDD:1'])))+'\n'
 write(p/'test.scs',deck)
 write(p/'measure.json',json.dumps(dict(stop_s=stop*1e-9,signals=sorted(set(saves+['VDD','VVDD:1'])),kind=name),indent=2))
 inputs=[{'source':str((p/f).relative_to(ROOT)).replace('\\','/'),'name':f} for f in ['test.scs','dut.scs','models.scs','measure.json']]
 inputs.append({'source':'scripts/manual_adc/reduce.py','name':'reduce.py'})
 recipe=dict(schema_version=1,run_id='manual8-'+name.replace('_','-'),design_id='manual8_candidate_v1',entry='test.scs',analyzer='reduce.py',inputs=inputs,expected_stop_s=stop*1e-9,summary_signals=saves,qualification_scope='Manual ADC isolated nominal diagnostic; no performance or reliability pass implied',oa_parity='netlist_only; user OA unchanged',test_conditions=dict(corner='tt',vdd=.9,temperature_c=27,noise=False,mismatch=False,PEX=False),spectre_args=['+preset=cx','+mt=1','-preset_override'],resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=1024,simulation_wall_seconds=1200,analysis_wall_seconds=600,queue_timeout_seconds=3600))
 write(ROOT/('management/recipes/'+recipe['run_id']+'.yaml'),json.dumps(recipe,indent=2)+'\n')
def initial_cases():
 build()
 # Baseline 3 real sampling switches driving the full128C load, two cycles after precharge.
 x=pulse('VCLK','CLKS',10,39.9)
 s=['CLKS']
 for j,v in enumerate([.05,.45,.85]):
  x+='VIN%d (IN%d 0) vsource dc=%g\nX%d (CLKS 0 VDD IN%d OUT%d) manual_boot\nCLOAD%d (OUT%d 0) capacitor c=1.28p\n'%(j,j,v,j,j,j,j,j)
  s+=['IN%d'%j,'OUT%d'%j]+['X%d.%s'%(j,n) for n in ['net1','net2','net3','net4','net7','CLKSB']]
 make_case('sample_base_v2',x,215,s)
 # Comparator both signs, CM0.45/0.675, realistic VALID OR and capture D inputs.
 x=pulse('VCLK','CK',10,3,10);s=['CK']
 for j,(cm,dm) in enumerate([(.45,.003515625),(.45,-.003515625),(.675,.003515625),(.675,-.003515625)]):
  x+='VP%d (P%d 0) vsource dc=%g\nVN%d (N%d 0) vsource dc=%g\nX%d (CK P%d N%d VDD 0 OP%d ON%d) manual_cmp\n'%(j,j,cm+dm/2,j,j,cm-dm/2,j,j,j,j,j)
  x+='LV%d (OP%d ON%d VALID%d VDD 0) OR2D4BWP12T30P140\n'%(j,j,j,j)
  for k in range(8):
   x+='LD%dP%d (OP%d 0 QP%d_%d VDD 0) DFQD1BWP12T30P140\nLD%dN%d (ON%d 0 QN%d_%d VDD 0) DFQD1BWP12T30P140\n'%(j,k,j,j,k,j,k,j,j,k)
  s+=['OP%d'%j,'ON%d'%j,'VALID%d'%j]+['X%d.%s'%(j,n) for n in ['LP','LN','net1','net2','net3']]
 make_case('cmp_base_v1',x,55,s)
 # Digital external response source drives 8 valid decisions per frame, all256 patterns.
 x=pulse('VCLK','CLKS',10,39.9)
 for side in ['P','N']:
  pts=[(0,0)]
  for code in range(256):
   for b in range(7,-1,-1):
    t=54+(256 and code)*100+(7-b)*5
    high=((code>>b)&1)==(side=='P')
    if high:pts += [(t,0),(t+.05,.9),(t+1.5,.9),(t+1.55,0)]
  points=' '.join('%gn %g'%(t,v) for t,v in pts)
  x+='VRESP'+side+' (DCMP'+side+' 0) vsource type=pwl wave=['+points+']\n'
 x+='XDUT (CLKS 0 VDD DCMPP DCMPN CMPCK '+' '.join('DO_'+str(i) for i in range(7,-1,-1))+' '+' '.join('DCTRL'+s+'_'+str(i) for s in ['P','N'] for i in range(7,-1,-1))+') manual_sar\n'
 # Gate loading: instantiate original reference MOS with drain/source/body tied to actual rails.
 cd=body('L2_CDAC_8bit')
 for side in ['P','N']:
  for line in cd.splitlines():
   m=re.match(r'(M\w+) \(([^)]+)\)(.*)',line)
   if not m:continue
   terms=m[2].split();gate=terms[1].replace('DCTRL_','DCTRL'+side+'_');rail='VDD' if 'pch_mac' in m[3] else '0'
   x+='LOAD'+side+m[1]+' ('+rail+' '+gate+' '+rail+' '+rail+')'+m[3]+'\n'
 s=['CLKS','DCMPP','DCMPN','CMPCK']+['DO_'+str(i) for i in range(8)]+['XDUT.CLK_'+str(i) for i in range(8)]+['DCTRL'+side+'_'+str(i) for side in ['P','N'] for i in range(8)]
 make_case('logic_codes_v1',x,25620,s)
 print('Built native-derived candidate + three module recipes')

if __name__=="__main__":initial_cases()
