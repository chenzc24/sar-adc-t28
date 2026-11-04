"""One bounded read-only exact170a library metadata query; no remote writes."""
import base64,hashlib,json,shlex,subprocess
from pathlib import Path
OWN=Path(__file__).resolve().parent
SPI='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a/tcbn28hpcplusbwp12t30p140_170a.spi'
SHA='b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e'
CODE=r'''from __future__ import print_function
import hashlib,json,os,re,socket,time
p=PATH
raw=open(p,'rb').read()
if len(raw)!=2452584 or hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('Exact parent-verified SPI identity changed')
text=raw.decode('ascii')
blocks={}
for m in re.finditer(r'(?ims)^\.subckt\s+(\w+)\s+([^\n]+)\n(.*?)^\.ends\b[^\n]*',text):
 blocks[m.group(1)]=(m.group(0),m.group(2).split(),m.group(3))
old='INVD1BWP12T30P140'
choices=[]
inventory=sorted(n for n in blocks if n.startswith('INVD') and n.endswith('BWP12T30P140'))
for n in inventory:
 m=re.match(r'^INVD(\d+)(?:P(\d+))?BWP12T30P140$',n)
 if not m:raise ValueError('Unparsed actual INV strength suffix; do not guess next drive')
 strength=float(m.group(1))+float('0.'+m.group(2)) if m.group(2) else float(m.group(1))
 if strength>1:choices.append((strength,n))
if not choices or old not in blocks:raise ValueError('Existing D1 and actual next greater numeric INV strength absent')
nextn=sorted(choices)[0][1]
units={'':1.,'n':1e-9,'u':1e-6,'m':1e-3,'p':1e-12}
def parse_num(value):
 m=re.match(r'^([0-9.]+(?:e[+-]?\d+)?)([numkp]?)$',value,re.I)
 if not m or m.group(2).lower() not in units:raise ValueError('Unverified literal dimension/multiplicity')
 return float(m.group(1))*units[m.group(2).lower()]
cells={};sizes={}
for name in [old,nextn]:
 block,pins,body=blocks[name];body=re.sub(r'\n\+\s*',' ',body)
 devices=[];other=[];size=[]
 for line in body.splitlines():
  line=line.strip()
  if not line or line.startswith('*'):continue
  parts=line.split()
  if not parts[0].lower().startswith('m'):
   other.append(parts[0]);continue
  if len(parts)<6:raise ValueError('Malformed actual MOS')
  instance,D,G,S,B,model=parts[:6]
  attrs=dict((k.lower(),v) for k,v in re.findall(r'(\w+)\s*=\s*([^\s]+)',line))
  if model not in ['nch_mac','pch_mac']:raise ValueError('Unverified native master')
  if set(['w','l'])-set(attrs):raise ValueError('No actual explicit W/L')
  width,length=parse_num(attrs['w']),parse_num(attrs['l'])
  mult=parse_num(attrs.get('m','1'))
  if any(k in attrs for k in ['nf','multi']):raise ValueError('Explicit extra folding/multiplicity requires separate interpretation')
  size.append((model,width*mult,length))
  devices.append(dict(instance=instance,D=D,G=G,S=S,B=B,master=model,
      dimension_units=dict((k,re.match(r'.*?([a-z]?)$',attrs[k],re.I).group(1).lower()) for k in ['w','l'])))
 if pins!=['I','ZN','VDD','VSS'] or other:raise ValueError('Actual native pins or primitive-only structure differs')
 for d in devices:
  if d['D']!='ZN' or d['G']!='I' or d['S']!=('VSS' if d['master']=='nch_mac' else 'VDD') or d['B']!=d['S']:raise ValueError('Not ordinary rail-body native inverter')
 cells[name]=dict(pins=pins,MOS=devices,non_MOS_statements=other,source_block_sha256=hashlib.sha256(block.encode('ascii')).hexdigest())
 sizes[name]=size
ratios={}
for model in ['nch_mac','pch_mac']:
 a=[x for x in sizes[old] if x[0]==model];b=[x for x in sizes[nextn] if x[0]==model]
 if not a or not b or set(x[2] for x in a)!=set(x[2] for x in b):raise ValueError('Native model length class changed')
 ratios[model]=sum(x[1] for x in b)/sum(x[1] for x in a)
 if ratios[model]<=1:raise ValueError('Nominal next cell not wider in actual source')
print(json.dumps(dict(file=p,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
 hostname=socket.gethostname(),uid=os.getuid(),observed_epoch=time.time(),query_read_only=True,
 previous_cell=old,selected_cell=nextn,actual_INV_inventory=inventory,actual_numeric_INV_candidates=[n for v,n in sorted(choices)],
 cells=cells,next_to_D1_effective_width_ratio=ratios,same_actual_model_length_classes=True,
 source_geometry_copied=False,query_scope='Read exact verified SPI; inventory INV numeric names; selected D1/next header/MOS connectivity/body/units/hash and relative width proof only. No W/L absolute geometry or cell body emitted.')))
'''
CODE=CODE.replace('PATH',repr(SPI)).replace('EXPECTED',repr(SHA))
cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(CODE.encode()).decode()+"'))")
proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','thu-wei',cmd],
    stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=40)
if proc.returncode:
 print('READ_ONLY_LIBRARY_QUERY_FAILED',proc.returncode,proc.stderr[-1200:]);raise SystemExit(proc.returncode)
lines=[x for x in proc.stdout.splitlines() if x.strip().startswith('{')]
if len(lines)!=1:raise ValueError('One metadata JSON object expected')
data=json.loads(lines[0]);data['query_script_sha256']=hashlib.sha256(CODE.encode()).hexdigest()
(OWN/'library_probe.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('VERIFIED_NEXT_NATIVE_INV',data['selected_cell'],data['next_to_D1_effective_width_ratio'],
      'MOS', {k:len(v['MOS']) for k,v in data['cells'].items()})

