"""Scoped evidence checks, never launch or modify any circuit."""
import hashlib,json,re
from probe import ROOT,OUT,VERIFY,read,dump,sha,launch,reduce

rows=[]
for name in ['smoke_cold','baseline_cold','baseline_hot']:
 m=read(VERIFY/(name+'_manifest.json'));d=OUT/name
 original=ROOT/'output/sar8_stress_closure'/m['source']
 for fn,h in m['source_hashes'].items():assert sha(original/fn)==h
 for fn,h in m['files'].items():assert sha(d/fn)==h
 a=re.sub(r'^save .*\n','',(original/'test.scs').read_text(),flags=re.M).strip()
 b=re.sub(r'^save .*\n','',(d/'test.scs').read_text(),flags=re.M).strip()
 b=b.replace(' currents=selected subcktiprobes=no useprobes=no','')
 b=b.replace('tran_perf tran stop='+m['stop'],'tran_perf tran stop=200n')
 assert a==b
 assert sha(d/'dut.scs')==sha(original/'dut.scs')
 row=dict(name=name,canonical_deck_sha256=hashlib.sha256(a.encode()).hexdigest(),measurement_only=True)
 if name!='smoke_cold':
  r=read(VERIFY/(name+'_analysis.json'));receipt=read(d/'reduced_v2/receipt.json')
  assert r['same_circuit_inventory'] and r['codes']==[243,12] and r['counts']==[[8,8,8,16]]*2
  assert len(r['settling'])==14 and all(x['settled_by_deadline'] for x in r['settling'])
  assert max(abs(x) for x in r['sample_close_delta_ps'])<.001
  assert abs(r['events']['gate']['peak_voltage_v']-r['original_peak_reference_v'])<1e-6
  assert abs(r['events']['bottom']['peak_voltage_v']*1000-r['original_bottom_min_mv'])<.001
  assert r['baseline_comparison']['maximum_interpolated_difference_v']<.0001
  assert all(x['residual_a']<max(1e-9,.001*x['peak_branch_a']) for x in r['kcl'].values())
  assert all(x['max_kcl_residual_a']<1e-9 for x in r['rail_kcl'].values())
  assert receipt['inputs_rehashed_after_simulation'] and receipt['raw_unchanged']
  for fn,data in receipt['files'].items():assert sha(d/'reduced_v2'/fn)==data['sha256']
  dump(VERIFY/(name+'_receipt.json'),receipt)
  for kind in ['gate','bottom','idle_bottom']:
   assert (ROOT/'docs/figures/sar8_ref_current_probe'/(name+'_'+kind+'.png')).is_file()
  row.update(codes=r['codes'],settled_windows=14,raw_unchanged=True,
   max_voltage_difference_uv=r['baseline_comparison']['maximum_interpolated_difference_v']*1e6,
   max_kcl_residual_pa=max(x['residual_a'] for x in r['kcl'].values())*1e12,
   native_resource=r['native_resource'])
 rows.append(row)
assert read(VERIFY/'smoke_validation.json')['passed']
assert read(VERIFY/'parser_validation.json')['sparse_current_PROP_fixture']
for entry in [launch,reduce]:
 try:entry('must_not_launch')
 except RuntimeError as error:assert 'disabled' in str(error)
 else:raise AssertionError('Historical execution was not disabled')
dump(VERIFY/'validation.json',dict(passed=True,cases=rows,OA_changed=False,baseline_promoted=False,
 legacy_execution_disabled=True,
 limits='Two static frames per FF corner, not complete PVT or transistor reliability signoff'))
print(json.dumps(rows,indent=2))
