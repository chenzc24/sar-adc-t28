"""Read-only classification of privately cached native tcb DFF metadata.

No simulator invocation; no library bodies are emitted into verification/.
Topology collapses parallel MOS, keeps N/P and D/G/S/B roles, fixes port names,
and ignores widths, lengths and Vt. Equal WL signatures are checked by an exact
port-preserving graph mapping before reporting equivalence.
"""
import collections, hashlib, itertools, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PRIVATE=ROOT/'output/manual_adc_dff_inventory'
OUT=ROOT/'verification/manual_adc/sar_isolation_v1/dff_inventory'
OUT.mkdir(exist_ok=True)

def number(v):
 scales={'n':1e-9,'u':1e-6,'p':1e-12}
 return float(v[:-1])*scales[v[-1]] if v[-1] in scales else float(v)

def collapsed(c):
 d=collections.defaultdict(list)
 for m in c['mos']:d[(m['model'][0].upper(),*m['nodes'])].append(m)
 return {k:{'w':sum(number(m['params']['w'])*float(m['params'].get('m',1)) for m in ms),
            'lengths':sorted(set(m['params']['l'] for m in ms)),
            'models':sorted(set(m['model'] for m in ms)),
            'names':[m['name'] for m in ms]} for k,ms in d.items()}

def graph(c):
 edges=list(collapsed(c));nets=sorted({n for e in edges for n in e[1:]})
 adj={('n',n):[] for n in nets};labels={('n',n):'PORT:'+n if n in c['ports'] else 'NET' for n in nets}
 for i,e in enumerate(edges):
  k=('m',i);adj[k]=[];labels[k]=e[0]
  for role,n in zip('DGSB',e[1:]):
   adj[k].append((role,('n',n)));adj[('n',n)].append((role,k))
 for _ in range(24):
  labels={k:hashlib.sha256(repr((labels[k],sorted((r,labels[v]) for r,v in adj[k]))).encode()).hexdigest() for k in adj}
 digest=hashlib.sha256(''.join(sorted(labels.values())).encode()).hexdigest()
 return edges,nets,labels,digest

def exact_map(a,b):
 ea,na,la,ha=graph(a);eb,nb,lb,hb=graph(b)
 if ha!=hb:return None
 opts={n:[v for v in nb if la[('n',n)]==lb[('n',v)]] for n in na}
 order=sorted(na,key=lambda n:len(opts[n]));target=set(eb)
 def search(i,mp,used):
  if i==len(order):return dict(mp) if {(e[0],*(mp[n] for n in e[1:])) for e in ea}==target else None
  n=order[i]
  for v in opts[n]:
   if v in used:continue
   mp[n]=v
   if all((e[0],*(mp[z] for z in e[1:])) in target for e in ea if all(z in mp for z in e[1:])):
    r=search(i+1,mp,used|{v})
    if r is not None:return r
   del mp[n]
  return None
 return search(0,{},set())

def compare(a,b):
 mp=exact_map(a,b)
 if mp is None:return {'same_topology':False}
 aa=collapsed(a);bb=collapsed(b);changes=[]
 for e,x in aa.items():
  z=bb[(e[0],*(mp[n] for n in e[1:]))]
  if abs(x['w']-z['w'])>1e-18 or x['lengths']!=z['lengths'] or x['models']!=z['models']:
   changes.append({'base_devices':x['names'],'candidate_devices':z['names'],'output_connected':any(p in e[1:] for p in ['Q','QN']),
                   'width_ratio':z['w']/x['w'],'length_changed':x['lengths']!=z['lengths'],'model_changed':x['models']!=z['models']})
 return {'same_topology':True,'proof':'exact D/G/S/B, N/P, port-preserving net mapping after parallel collapse',
         'changed_branches':len(changes),'internal_changed_branches':sum(not x['output_connected'] for x in changes),
         'changes':changes}

def main():
 raw=json.loads((PRIVATE/'native_inventory_private.json').read_text())
 supplemental=PRIVATE/'mux_inventory_private.json'
 if supplemental.exists():
  sup=json.loads(supplemental.read_text())
  for lib in raw:lib['cells']+=sup.get(lib['sha256'],[])
 unique={}
 for lib in raw:
  if lib['sha256'] in unique:unique[lib['sha256']]['aliases'].append(lib['path']);continue
  unique[lib['sha256']]={**lib,'aliases':[]}
 libs=list(unique.values())
 mainlib=unique['b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e']
 maincells={c['name']:c for c in mainlib['cells']}
 summaries=[]
 for lib in libs:
  families=collections.Counter(re.sub(r'D\d+BWP.*','',c['name']) for c in lib['cells'])
  summaries.append({k:lib[k] for k in ['path','sha256','bytes','all_subcircuits','aliases']}|{'DFF_count':len(lib['cells']),'families':dict(families)})
 rows=[];reps={}
 for c in mainlib['cells']:
  assert not c['other'],(c['name'],c['other'])
  edges,nets,labels,h=graph(c)
  if h in reps:assert exact_map(reps[h],c) is not None
  else:reps[h]=c
  rows.append({'name':c['name'],'ports':c['ports'],'MOS_lines':len(c['mos']),'parallel_collapsed_branches':len(edges),
               'internal_nodes':len(set(nets)-set(c['ports'])),'topology_sha256':h,'models':sorted({m['model'] for m in c['mos']})})
 comparisons=[]
 for stem in ['DFQ','DFCNQ']:
  base=maincells[stem+'D1BWP12T30P140']
  for name in [stem+'D2BWP12T30P140',stem+'D4BWP12T30P140']:
   comparisons.append({'baseline':base['name'],'candidate':name,**compare(base,maincells[name])})
  for lib in libs:
   if lib is mainlib:continue
   cand=next((c for c in lib['cells'] if c['name'].startswith(stem+'D1BWP')),None)
   if cand:comparisons.append({'baseline':base['name'],'candidate':cand['name'],**compare(base,cand)})
 selection=['GDFCNQMCOD1','GDFQMCOD1','SDFSYNCNQD1','SDFSYNQD1','DFCNQOPTMAD8','DFQOPTMAD8','DFCNQOPTSADD8','DFQOPTSADD8','SDFCNQOPTBD1','SDFQOPTBD1','DFKCNQD1','DFMQD1']
 candrows=[]
 for stem in selection:
  c=maincells[stem+'BWP12T30P140']
  b=maincells[('DFCNQD1' if 'CDN' in c['ports'] else 'DFQD1')+'BWP12T30P140']
  candrows.append({'name':c['name'],'ports':c['ports'],'MOS_lines':len(c['mos']),'collapsed_branches':len(collapsed(c)),
                   'same_as_reference_topology':exact_map(b,c) is not None})
 result={'read_only':True,'new_simulations':0,'source_files':summaries,'main_library_cells':rows,'comparisons':comparisons,'structural_candidates':candrows,
         'method':'N/P typed MOS graph; D/G/S/B roles retained; port names fixed; internal names ignored; parallel MOS collapsed; widths, L, Vt compared separately; exact equivalence verified after hash grouping',
         'limits':'Topology difference is not stress qualification; no electrical tests, function simulation or PVT performed. Raw library bodies remain in ignored output only.'}
 (OUT/'inventory.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print('unique libraries',len(libs),'main DFF entries',len(rows),'main exact topology groups',len(reps))
 for x in comparisons:print(x['candidate'],x['same_topology'],x.get('changed_branches'),x.get('internal_changed_branches'))
 for x in candrows:print(x['name'],x['MOS_lines'],x['collapsed_branches'])

if __name__=='__main__':main()
