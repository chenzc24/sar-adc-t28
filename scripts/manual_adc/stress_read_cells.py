from pathlib import Path
import json,subprocess,base64,re
root=Path.cwd();out=root/'verification/manual_adc/stress_diagnosis';out.mkdir(exist_ok=True)
lib=re.search(r'\.include "([^"]+)"',(root/'verification/manual_adc/candidate_v1/models.scs').read_text()).group(1)
script="""import json,re
p=%r
want=['DFCNQD1BWP12T30P140','DFQD1BWP12T30P140','BUFFD4BWP12T30P140','INVD4BWP12T30P140']
r={};cell=None
for line in open(p):
 a=line.split()
 if not a:continue
 if a[0].upper()=='.SUBCKT':
  cell=a[1] if a[1] in want else None
  if cell:r[cell]={'ports':a[2:],'mos':[]}
 elif a[0].upper()=='.ENDS':cell=None
 elif cell and a[0].upper().startswith('M'):r[cell]['mos'].append({'name':a[0],'terminals':a[1:5],'model':a[5]})
print(json.dumps(r))
"""%lib
enc=base64.b64encode(script.encode()).decode()
r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',"python -c \"import base64;exec(base64.b64decode('"+enc+"'))\""],capture_output=True,text=True,check=True)
j=json.loads(r.stdout);(out/'native_cell_connectivity.json').write_text(json.dumps(j,indent=2)+'\n')
for cell,v in j.items():
 print(cell,v['ports'],'MOS',len(v['mos']),'nodes',len(set(n for m in v['mos'] for n in m['terminals'])))
 for m in v['mos']:
  if m['name'] in ['MM3','MM4','MM64','MM76','MSLTn1','MM79']:print(m)
