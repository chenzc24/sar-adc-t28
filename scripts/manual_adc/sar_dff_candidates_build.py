"""Create two native-cell substitutions of the completed CDN1x fixture."""
import hashlib,json,re,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/manual_adc/sar_isolation_v1/dff_candidates_v1'
BASE=ROOT/'verification/manual_adc/sar_isolation_v1/cdn_slew_v1/s0'
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 library_path=re.search(r'\.include "([^"]+)"',(BASE/'models.scs').read_text())[1]
 libs=json.loads((ROOT/'output/manual_adc_dff_inventory/native_inventory_private.json').read_text())
 lib=next(x for x in libs if x['path']==library_path)
 actual=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei','sha256sum '+shlex.quote(library_path)],text=True).split()[0]
 assert actual==lib['sha256']
 old=(BASE/'test.scs').read_text().splitlines()
 frozen=[l for l in old if not l.startswith(('save ','XA ','XB '))]
 reduce_src=ROOT/'scripts/manual_adc/sar_cdn_reduce.py'
 reducer=ROOT/'scripts/manual_adc/sar_dff_candidates_reduce.py'
 reducer.write_text(reduce_src.read_text().replace("scope='TT two D1 cells, 5fF diagnostic load, ideal finite sources; no PVT or ADC qualification'","scope='TT two native '+cfg['cell']+' cells, 5fF diagnostic load, ideal finite sources; no PVT or ADC qualification'"),encoding='utf-8')
 built=[]
 for short,cell in [('syn','SDFSYNCNQD1BWP12T30P140'),('gdf','GDFCNQMCOD1BWP12T30P140')]:
  c=next(c for c in lib['cells'] if c['name']==cell);assert not c['other']
  assert set(c['ports'])==({'D','CP','CDN','Q','VDD','VSS','SI','SE'} if short=='syn' else {'D','CP','CDN','Q','VDD','VSS'})
  out=OUT/short;out.mkdir(parents=True,exist_ok=True)
  devices=[];signals={'VDD','CDN','CP','DA','DB','QA','QB'};instances=[]
  for inst,d,q in [('XA','DA','QA'),('XB','DB','QB')]:
   ports=dict(D=d,CP='CP',CDN='CDN',Q=q,VDD='VDD',VSS='0',SI='0',SE='0')
   instances.append(inst+' ('+' '.join(ports[p] for p in c['ports'])+') '+cell)
   for m in c['mos']:
    nodes=[ports.get(n,inst+'.'+n) for n in m['nodes']]
    signals.update(n for n in nodes if n!='0');devices.append(dict(path=inst+'.'+m['name'],terminals=nodes,model=m['model']))
  currents=['VVDD:1','VCDN:1','VCP:1','VDA:1','VDB:1']
  for inst in ['XA','XB']:
   for m in ['MM64','MM65','MM66','MM75','MM76','MM78']:
    assert any(x['name']==m for x in c['mos']);currents.extend(inst+'.'+m+':'+str(i) for i in range(1,5))
  signals=sorted(signals)+currents
  lines=frozen+instances+['save '+' '.join(signals[i:i+8]) for i in range(0,len(signals),8)]
  assert [l for l in lines if not l.startswith(('save ','XA ','XB '))]==frozen
  (out/'test.scs').write_text('\n'.join(lines)+'\n');(out/'models.scs').write_bytes((BASE/'models.scs').read_bytes())
  dump(out/'measure.json',dict(case=short,cell=cell,factor=1,devices=devices,signals=signals,stop_s=9e-9,window_s=[4.85e-9,6.2e-9],threshold_V=.99))
  rid='manual8-dff-'+short+'-tt-v1'
  recipe=json.loads((ROOT/'management/recipes/manual8-cdn-s0-tt-v1.yaml').read_text())
  recipe.update(run_id=rid,design_id='manual8_sar_dff_candidates_v1',analyzer='sar_dff_candidates_reduce.py',qualification_scope='Native '+cell+' substitution only; ideal identical CDN1x/CP/D and 5fF Q load; not PVT/SAR qualification')
  recipe['inputs']=[dict(source=(out/n).relative_to(ROOT).as_posix(),name=n) for n in ['test.scs','models.scs','measure.json']]+[dict(source='scripts/manual_adc/'+n,name=n) for n in ['sar_dff_candidates_reduce.py','reduce.py']]
  dump(ROOT/'management/recipes'/(rid+'.yaml'),recipe)
  built.append(dict(run_id=rid,cell=cell,native_ports=c['ports'],mos_per_instance=len(c['mos']),test_sha256=sha(out/'test.scs'),models_sha256=sha(out/'models.scs'),instances=instances,only_cell_and_observation_changed=True))
 dump(OUT/'build_receipt.json',dict(baseline_run='manual8-cdn-s0-tt-v1',baseline_analysis='manual8-cdn-s0-reduce-v2',library_path=library_path,library_sha256=actual,baseline_deck_sha256=sha(BASE/'test.scs'),runs=built,resources='1 thread, sim1GiB analysis256MiB, output512MiB; managed2 slots total',OA_changed=False))
 print(json.dumps(built,indent=2))
if __name__=='__main__':main()
