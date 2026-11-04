import json,re,shutil
from pathlib import Path
R=Path.cwd();B=R/'verification/manual_adc';d=B/'stress_diagnosis';p=d/'baseline_v1';p.mkdir(exist_ok=True)
lib=json.loads((d/'native_cell_connectivity.json').read_text());dut=(B/'joined_dc_v1/dut.scs').read_text();sar=dut.split('subckt manual_sar ',1)[1].split('ends manual_sar')[0]
signals=set(json.loads((B/'joined_dc_v1/measure.json').read_text())['signals']);devices=[];instances=[]
for name,ports,cell in re.findall(r'^(\w+) \(([^)]+)\) (\w+)',sar,re.M):
 if cell not in lib:continue
 mapping=dict(zip(lib[cell]['ports'],ports.split()));full='XADC.XL.'+name
 def node(n):
  if n in mapping:
   x=mapping[n]
   if x=='GND':return '0'
   if x=='VDD':return 'VDD'
   return 'XADC.XL.'+x
  return full+'.'+n
 for m in lib[cell]['mos']:
  terms=[node(n) for n in m['terminals']]
  devices.append(dict(path=full+'.'+m['name'],cell=cell,instance=name,mos=m['name'],terminals=terms))
  signals.update(x for x in terms if x!='0')
 instances.append(dict(path=full,cell=cell))
# Selected branch currents around internal clear/transfer nodes; all are external subckt-terminal currents.
for inst in ['I5','I12']:
 for m in lib['DFCNQD1BWP12T30P140']['mos']:
  if any(n in ['qf','mq','net176','net093','net0152'] for n in m['terminals']):
   signals.update('XADC.XL.%s.%s:%d'%(inst,m['name'],i) for i in range(1,5))
for f in ['dut.scs','models.scs']:shutil.copyfile(B/'joined_dc_v1'/f,p/f)
test=(B/'joined_dc_v1/test.scs').read_text().split('\nsave ')[0].replace('stop=420n','stop=120n')+'\nsave '+' '.join(sorted(signals))+'\n';(p/'test.scs').write_text(test)
cfg=dict(stop_s=120e-9,signals=sorted(signals),devices=devices,instances=instances,kind='stress_baseline_v1');(p/'measure.json').write_text(json.dumps(cfg,indent=2))
r=json.loads((R/'management/recipes/manual8-joined-dc-v1.yaml').read_text());r.update(run_id='manual8-stress-baseline-v1',analyzer='stress_reduce.py',expected_stop_s=120e-9,summary_signals=['CLKS','XADC.XL.CLKSN','XADC.CMPCK','XADC.XL.VALID'],qualification_scope='Save-only internal standard-cell stress diagnosis, unchanged joined circuit; 120ns includes startup/first convert/second reset')
r['inputs']=[dict(source=str((p/f).relative_to(R)).replace('\\','/'),name=f) for f in ['dut.scs','models.scs','test.scs','measure.json']]+[dict(source='scripts/manual_adc/stress_reduce.py',name='stress_reduce.py'),dict(source='scripts/manual_adc/reduce.py',name='reduce.py')];r['resources']['analysis_wall_seconds']=1200
(R/'management/recipes/manual8-stress-baseline-v1.yaml').write_text(json.dumps(r,indent=2)+'\n')
print('Mapped',len(devices),'MOS in',len(instances),'standard instances;',len(signals),'saved signals')
