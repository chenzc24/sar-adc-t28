"""Timing intervals from already measured native threshold crossings, no rerun."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];run=sys.argv[1]
p=R/'output/managed_execution/runs'/run/'collected/derived'
if not p.exists():p=p.parent
r=json.loads((p/'result.json').read_text());mode=r['mode'];version=run.rsplit('-',1)[1]
base=R/'verification/manual_adc/sar_isolation_v1';cfg=json.loads((base/('tb_'+mode+'_'+version)/'measure.json').read_text())
edges=r['edges'];rows=[]
for ff in cfg['dffs']:
 pins={k:v.lower() for k,v in ff['ports'].items()};cp=edges.get(pins['CP'],[]);de=edges.get(pins['D'],[])
 clocks=[t for t,di in cp if di and 49.975e-9<t<1611e-9]
 setups=[];holds=[]
 for t in clocks:
  prior=[u for u,di in de if u<=t];after=[u for u,di in de if u>=t]
  if prior:setups.append(t-max(prior))
  if after:holds.append(min(after)-t)
 widths=[cp[i+1][0]-cp[i][0] for i in range(len(cp)-1) if cp[i][1] and not cp[i+1][1] and cp[i][0]>49e-9]
 reset=pins.get('CDN');recoveries=[];removals=[]
 if reset:
  for t,di in edges.get(reset,[]):
   if not di or t<49e-9:continue
   before=[u for u in clocks if u<t];after=[u for u in clocks if u>t]
   if after:recoveries.append(min(after)-t)
   if before:removals.append(t-max(before))
 rows.append(dict(instance=ff['name'],cell=ff['cell'],clock_rises=len(clocks),
  min_D_setup_50pct_s=min(setups) if setups else None,min_D_hold_50pct_s=min(holds) if holds else None,
  min_CP_high_50pct_s=min(widths) if widths else None,min_reset_recovery_50pct_s=min(recoveries) if recoveries else None,
  min_reset_removal_50pct_s=min(removals) if removals else None,qualification='unknown; library timing limits not applied'))
# Check no thermometer Q falls between its first rise and next sampling edge.
thermometer=True;output_stable=True
for i in range(16):
 lo=49.975e-9+i*100e-9;hi=110.025e-9+i*100e-9
 for b in range(8):
  ev=[x for x in edges.get('xdut.clk_'+str(b),[]) if lo<x[0]<hi]
  if len(ev)!=1 or not ev[0][1]:thermometer=False
 for b in range(8):
  if any(hi+1e-9<u<hi+99e-9 and u<1620e-9 for u,di in edges.get('do_'+str(b),[])):output_stable=False
out=dict(run=run,rows=rows,thermometer_holds=thermometer,registered_output_stable=output_stable,
 caveat='50% timing is measured; not a Liberty setup/hold signoff. No D transition means undefined interval, not failure.')
(base/(run+'_timing.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
