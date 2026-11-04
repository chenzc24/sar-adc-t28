"""Freeze unchanged native SAR and explicit isolation fixtures; never submit here."""
import json,re,hashlib,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];B=R/'verification/manual_adc';D=B/'sar_isolation_v1'
mode=sys.argv[1] if len(sys.argv)>1 else 'a'
assert mode in ('a','b')
version=sys.argv[2] if len(sys.argv)>2 else 'v2'
run='manual8-sar-%s-tt-%s'%(mode,version);p=D/('tb_'+mode+'_'+version);p.mkdir(exist_ok=True)
source=(B/'candidate_io_v1/dut.scs').read_text()
sar=re.search(r'subckt manual_sar .*?ends manual_sar',source,re.S).group()
assert len(re.findall(r'^DELAY',sar,re.M))==17 and 'resistor' not in sar
original_sar=sar
delay_paths=[]
if version in ('v3','v4','v5','v6'):
 def convert(m):
  name,o,g,inp,g2,td=m.groups();assert g==g2=='GND'
  delay_paths.append(dict(name=name,input='XDUT.'+inp,output='XDUT.'+o,td_s=2e-9 if td=='tloop' else 100e-12))
  return '%s (%s GND %s VDD) sar_logic_delay td=%s trf=50p'%(name,o,inp,td)
 sar=re.sub(r'^(DELAY\d+) \((\w+) (\w+) (\w+) (\w+)\) delay td=(\w+) gain=1.0$',convert,sar,flags=re.M)
 assert len(delay_paths)==17
(p/'dut.scs').write_text(sar+'\n')
shutil.copyfile(B/'joined_dc_v1/models.scs',p/'models.scs')
lib=json.loads((B/'stress_diagnosis/native_cell_connectivity.json').read_text())
pins=sar.splitlines()[0].split()[2:];top={k:k for k in pins};top['GND']='0'
def snode(n):return top.get(n,'XDUT.'+n)
signals={'VDD','VVDD:1','CLKS','CMPCK','DCMPP','DCMPN','XDUT.VALID','XDUT.CLKSN','XDUT.CMPCKe','XDUT.net35'}
signals.update('DO_'+str(i) for i in range(8))
signals.update('DCTRL'+s+'_'+str(i) for s in ['P','N'] for i in range(8))
reps=['I5','I12','I14','I22','I28','I30','I38','I44','I46_3','I46_7']
devices=[];dffs=[]
for name,ports,cell in re.findall(r'^(\w+) \(([^)]+)\) (\w+)',sar,re.M):
 if cell not in lib:continue
 mapping={k:snode(v) for k,v in zip(lib[cell]['ports'],ports.split())}
 if cell.startswith(('DFQ','DFCN')):
  dffs.append(dict(name=name,cell=cell,ports=mapping));signals.update(mapping.values())
 if name not in reps:continue
 for m in lib[cell]['mos']:
  terms=[mapping.get(x,'XDUT.'+name+'.'+x) for x in m['terminals']]
  devices.append(dict(path='XDUT.'+name+'.'+m['name'],cell=cell,terminals=terms))
  signals.update(terms)
signals.discard('0');assert len(dffs)==32
signals.update(n for path in delay_paths for n in [path['input'],path['output']])
cdac=re.search(r'subckt manual_cdac .*?ends manual_cdac',source,re.S).group()
loads=[]
for side in ['P','N']:
 for name,ports,rest in re.findall(r'^(M\w+) \(([^)]+)\) (.*)$',cdac,re.M):
  gate=ports.split()[1].replace('DCTRL_','DCTRL'+side+'_');rail='VDD' if rest.startswith('pch') else '0'
  loads.append('LOAD%s%s (%s %s %s %s) %s'%(side,name,rail,gate,rail,rail,rest))
assert len(loads)==28
codes=[0,255,85,170,128,127,1,254]*2
lines=['simulator lang=spectre','global 0','include "models.scs"','include "dut.scs"',
 'VVDD (VDD 0) vsource dc=.9',
 'VCLK (CLKS 0) vsource type=pulse val0=0 val1=.9 delay=10n rise=50p fall=50p width=39.9n period=100n',
 'XDUT ('+' '.join(top[k] for k in pins)+') manual_sar tloop=2n tgate=100p']
inputs=['dut.scs','models.scs','test.scs','measure.json']
extras=[]
if version in ('v3','v4','v5','v6'):
 lines+=['ahdl_include "logic_delay.va"'];extras.append((D/'logic_delay.va','logic_delay.va'))
if mode=='a':
 lines+=['ahdl_include "response.va"','XRESP (CLKS CMPCK VDD 0 DCMPP DCMPN) sar_test_response td=200p trf=50p rout=1']
 extras.append((D/('response.va' if version=='v1' else 'response_v2.va'),'response.va'))
else:
 for m in ['sample','cdac','cmp']:
  lines+=['ahdl_include "manual8_%s.va"'%m];extras.append((B/('behavioral_v1/manual8_'+m+'.va'),'manual8_'+m+'.va'))
 for side in ['P','N']:
  w=[]
  for i,c in enumerate(codes):
   vd=(c+.5)*1.8/256-.9;v=.45+(.5 if side=='P' else -.5)*vd
   if i:w+=['%.12g'%(i*100e-9),'%.12g'%old,'%.12g'%(i*100e-9+50e-12),'%.12g'%v]
   else:w+=['0','%.12g'%v]
   old=v
  lines+=['VIN%s (VIN%s 0) vsource type=pwl wave=[%s]'%(side,side,' '.join(w)),
   'XS%s (CLKS 0 VDD VIN%s TOP%s) manual8_sample ron=1 roff=1T trf=10p cin=0 qclk=0'%(side,side,side)]
  gates=['DCTRL'+('N' if side=='P' else 'P')+'_7']+['DCTRL'+side+'_'+str(i) for i in range(6,0,-1)]
  lines+=['XC%s (0 VDD TOP%s REF 0 %s) manual8_cdac cunit=10f ronunit=10 ctop=0'%(side,side,' '.join(gates))]
 lines+=['VREF (REF 0) vsource dc=.9','XCMP (CMPCK TOPP TOPN VDD 0 DCMPP DCMPN) manual8_cmp td=200p trf=50p rout=1 vos=0 cin=0 treg=0 qkickp=0 qkickn=0']
 signals.update(['VINP','VINN','TOPP','TOPN','REF'])
lines+=loads+['COUT%d (DO_%d 0) capacitor c=5f'%(i,i) for i in range(8)]
lines+=['simulatorOptions options reltol='+('1e-5' if version in ('v5','v6') else '1e-6')+' vabstol=1e-8 iabstol=1e-14 temp=27 tnom=27',
 'saveOptions options save=selected currents=selected',
 'tran_test tran stop=1620n maxstep=100p errpreset=conservative'+(' reltol=1e-6' if version=='v4' else ''),'save '+' '.join(sorted(signals))]
(p/'test.scs').write_text('\n'.join(lines)+'\n')
cfg=dict(mode=mode,stop_s=1620e-9,codes=codes,signals=sorted(signals),devices=devices,dffs=dffs,representatives=reps,
 delay_paths=delay_paths,delay_implementation='VA threshold + transition' if version in ('v3','v4','v5','v6') else 'Spectre analog delay',
 original_sar_sha256=hashlib.sha256(original_sar.encode()).hexdigest(),
 source_sha256=hashlib.sha256((B/'candidate_io_v1/dut.scs').read_bytes()).hexdigest(),
 sar_sha256=hashlib.sha256(sar.encode()).hexdigest(),limits=dict(stress_V=.99,conversion_s=40e-9,power_W=100e-6),
 scope='All 32 DFF external pins; ten representative DFF internals only. Static gate replicas exclude bottom-plate Miller; ideal source/delay power excluded.')
(p/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
r=json.loads((R/'management/recipes/manual8-beh-smoke-v2.yaml').read_text())
r.update(run_id=run,design_id='manual8_sar_isolation_v1',entry='test.scs',analyzer='sar_isolation_reduce.py',expected_stop_s=cfg['stop_s'],summary_signals=['CLKS','CMPCK','XDUT.VALID'],qualification_scope=cfg['scope'],test_conditions=dict(corner='tt',vdd=.9,temperature_c=27,noise=False,mismatch=False,PEX=False))
r['inputs']=[dict(source=(p/f).relative_to(R).as_posix(),name=f) for f in inputs]+[dict(source=f.relative_to(R).as_posix(),name=n) for f,n in extras]+[dict(source='scripts/manual_adc/'+s,name=s) for s in ['sar_isolation_reduce.py','reduce.py']]
r['resources'].update(max_output_mib=8192,simulation_wall_seconds=3600,analysis_wall_seconds=1800)
(R/('management/recipes/'+run+'.yaml')).write_text(json.dumps(r,indent=2)+'\n')
print(run,'signals',len(signals),'DFF',len(dffs),'MOS',len(devices))
