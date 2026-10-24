"""Validate the four immutable cases and summarize the recovered comparisons."""
import re
from stream_control import OUT,VERIFY,NAMES,read,dump,sha

def main():
 rows=[];comparisons=[]
 for name in NAMES:
  r=read(VERIFY/(name+'_stream_analysis.json'))
  receipt=read(VERIFY/(name+'_stream_receipt.json'))
  context=read(OUT/name/'context.json')
  assert sha(OUT/name/'test.scs')==context['deck_sha256']
  assert sha(OUT/name/'dut.scs')==context['DUT_sha256']
  assert sha(OUT/name/'r4_perf_monitor.va')==context['monitor_sha256']
  assert r['native_pass'] and r['stress_pair_count']==10998 and r['reference_crosschecks']==192
  assert len(r['settling'])==14 and len(r['frames'])==2
  assert r['all_codes_pass'] and r['all_timing_pass'] and r['all_idle_pass']
  assert receipt['source']['unchanged'] and receipt['memory_limit_bytes']==512*1024*1024
  assert '100e-09' in r['effective_settings']['reltol'] and '10 ps' in r['effective_settings']['maxstep']
  rows.append(dict(name=name,temperature_c=r['temperature_c'],points=r['points'],
   raw_bytes=receipt['source']['bytes'],compressed_bytes=r['compressed_bytes'],
   reducer_peak_rss_kib=r['reducer_peak_rss_kib'],elapsed_seconds=receipt['elapsed_seconds'],
   reference_peak=r['groups']['reference'],bottom_min=r['bottom_min'],
   worst_nominal_settling_ns=max(x['nominal']['settle_after_start_ns'] for x in r['settling']),
   max_deadline_residual_mv=max(x['nominal']['residual_at_deadline_mv'] for x in r['settling']),
   settling_passes=sum(x['nominal']['settled_by_deadline'] for x in r['settling']),
   codes=[f['code'] for f in r['frames']],held_error_mv=[f['held_error_mv'] for f in r['frames']],
   preclose_error_mv=[f['preclose_error_mv'] for f in r['frames']],
   all_timing_pass=r['all_timing_pass'],all_idle_pass=r['all_idle_pass'],CMI=r['CMI'],
   groups=r['groups'],failing_MOS=r['failing_MOS']))
 for temp in ['m40','125']:
  names=[f'rg{x}_strict200_ff_{temp}' for x in [1,4]]
  a,b=[read(VERIFY/(n+'_stream_analysis.json')) for n in names]
  da,db=[(OUT/n/'dut.scs').read_text().splitlines() for n in names]
  assert len(da)==len(db)
  changed=[]
  for x,y in zip(da,db):
   if x==y:continue
   expected,n=re.subn(r'(rupolym l=17\.13u w=1u m=)(\d+)',lambda m:m[1]+str(int(m[2])*4),x)
   assert n==1 and expected==y
   changed.append(x)
  assert len(changed)==320
  deltas={}
  for signal in ['xdut.seq_sample','xdut.sample_int']:
   for edge in ['rise','fall']:
    x=a['sample_edges_ns'][signal][edge];y=b['sample_edges_ns'][signal][edge]
    assert len(x)==len(y)
    deltas[signal+'.'+edge]=[(q-p)*1000 for p,q in zip(x,y)]
  maximum=max(abs(d) for ds in deltas.values() for d in ds)
  assert maximum<.001
  comparisons.append(dict(temperature=temp,only_changed_PDk_resistor_lines=320,
   sample_edge_deltas_ps=deltas,max_sample_edge_delta_ps=maximum,
   baseline=names[0],candidate=names[1]))
 result=dict(cases=rows,comparisons=comparisons,total_raw_bytes=sum(r['raw_bytes'] for r in rows),
  total_compressed_wave_bytes=sum(r['compressed_bytes'] for r in rows),
  max_parser_rss_kib=max(r['reducer_peak_rss_kib'] for r in rows),
  raw_preserved=True,no_simulations_started=True,no_OA_changes=True,
  conclusion='Rgate/4 is not an overvoltage repair; codes and settling are separate gates.',
  limits='200ns/two frames only; no full PVT, mismatch, FFT or SOA signoff. Requested MOS terminal currents absent.')
 dump(VERIFY/'stream_summary.json',result)
 for r in rows:
  print(r['name'],r['reference_peak']['peak_v'],r['bottom_min'][0],r['worst_nominal_settling_ns'],r['codes'])

if __name__=='__main__':main()
