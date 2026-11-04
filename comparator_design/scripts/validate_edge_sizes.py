"""Frozen inputs, native pulses, functional counts and effective settings."""
import ast,json,re,hashlib
import numpy as np
from setup import W,ROOT,write
from review_edge_sizes import RUNS,STEM
from review_fall import read
from review_precharge import pulse

base=W/'testbenches'/RUNS['Baseline'];summary=json.loads((W/'results'/(STEM+'_comparison.json')).read_text());audit={}
if STEM=='edge_combo':
    previous=json.loads((W/'results/edge_sizes_comparison.json').read_text())
    for tag in ['Baseline','Precharge x2','Input x2']:assert summary[tag]==previous[tag],'Read-only existing case changed'
if STEM=='combo_a8':
    previous=json.loads((W/'results/edge_combo_comparison.json').read_text())
    assert summary['Baseline']==previous['Combined'],'Read-only combined case changed'
for tag,run in RUNS.items():
    src=W/'testbenches'/run
    for n in ['test.scs','models.scs']:assert (src/n).read_bytes()==(base/n).read_bytes()
    original=(base/'dut.scs').read_text();dut=(src/'dut.scs').read_text()
    changes=[(a,b) for a,b in zip(original.splitlines(),dut.splitlines()) if a!=b]
    assert len(original.splitlines())==len(dut.splitlines())
    devices=['M3','M5','M8','M9'] if tag=='Combined' else (['M3','M5'] if tag=='Precharge x2' else (['M8','M9'] if tag=='Input x2' else []))
    if tag=='Latch x8':devices=['M2','M4']
    assert len(changes)==len(devices)
    assert sorted(a.split()[0] for a,b in changes)==devices
    for a,b in changes:assert b==a.replace('multi=%d '%(1 if a.split()[0] in ['M3','M5'] else 4),'multi=%d '%(8 if tag=='Latch x8' else 2))
    r,d,cfg=read(tag,run);t=d['time'];ck=d['ck'];checks=[];errs=[]
    assert 0<=cfg['stop_s']-t[-1]<21e-12
    assert cfg['events']==json.loads((base/'measure.json').read_text())['events']
    for e,row in zip(cfg['events'],r['contexts']['A4_held']['rows']):
        for center,up in [(e['clock50'],True),(e['fall50'],False)]:
            idx=np.where((t[:-1]>center-300e-12)&(t[1:]<center+300e-12)&((ck[:-1]<.495)&(ck[1:]>=.495) if up else (ck[:-1]>.495)&(ck[1:]<=.495)))[0]
            assert len(idx)==1
            j=idx[0];at=t[j]+(t[j+1]-t[j])*(.495-ck[j])/(ck[j+1]-ck[j]);errs.append(abs(at-center))
        m=(t>=e['fall_start'])&(t<e['fall50']+.8e-9);tt=t[m];good=np.maximum(d['opa4_held'][m],d['ona4_held'][m])<=.198
        bad=np.where(~good)[0];j=int(bad[-1]+1) if len(bad) else 0
        assert j<len(tt) and good[j:].all() and abs(tt[j]-row['reset_since_s'])<2e-15
    assert max(errs)<1e-15
    for g in ['startup_input','startup_latch','reset_input','reset_latch']:
        for metric in ['worst_peak_pulse','longest_pulse']:
            p=summary[tag]['held'][g][metric]
            if p is None:continue
            e=cfg['events'][p['event_index']]
            lo,hi=(e['fall_start']-20e-12,e['fall50']+.5e-9) if g.startswith('reset') else (e['rise_start']-40e-12,e['t']+800e-12)
            m=(t>=lo)&(t<hi);tt=t[m];y=d['xa4_held.'+p['node']][m]
            j=int(np.argmin(abs(tt-p['time_s'])));left=right=j
            while left>0 and y[left-1]>.99:left-=1
            while right+1<len(y) and y[right+1]>.99:right+=1
            assert left>0 and right+1<len(y)
            q=pulse(tt[left-1:right+2],y[left-1:right+2],.99)
            assert abs(q['peak_V']-p['peak_V'])<1e-10 and abs(q['width_s']-p['duration_s'])<1e-14
            checks.append(dict(group=g,metric=metric,peak_error_V=q['peak_V']-p['peak_V'],width_error_s=q['width_s']-p['duration_s']))
    for mode,c in r['contexts'].items():assert len(c['rows'])==32 and c['all_correct'] and c['all_reset']
    # Global worst terminal belongs to a saved node; confirm peak on raw CSV.
    key,p=summary[tag]['held']['worst_terminal_pairs'][0];dev,pair=key.split(':')
    device=next(z for z in cfg['contexts'][1]['devices'] if z['name']==dev) if cfg['contexts'][1]['name']=='A4_held' else next(z for c in cfg['contexts'] if c['name']=='A4_held' for z in c['devices'] if z['name']==dev)
    def voltage(n):
        if n=='0':return np.zeros_like(t)
        if n.lower()=='ua4_held':return np.full_like(t,.99)
        return d[n.lower()]
    y=abs(voltage(device['nodes']['DGSB'.index(pair[0])])-voltage(device['nodes']['DGSB'.index(pair[1])]))
    assert abs(y.max()-p['peak_V'])<1e-10
    states={n:json.loads((W/'results'/run/(n+'.state.json')).read_text()) for n in ['simulation','analysis']}
    for s in states.values():assert s['exit_code']==0
    s=states['simulation'];a=states['analysis'];assert s['native']['zero_error_footer']
    audit[tag]=dict(run_id=run,only_multi_changed=devices,identical_sources_models=True,all64_function_pass=True,clock50_max_error_s=max(errs),native_pulses=checks,global_peak_csv_match=True,warnings=s['native']['warning_codes'],effective_settings=s['native']['effective_settings'],simulation_seconds=s['elapsed_seconds'],simulation_RSS_MiB=s['peak_rss_bytes']/1048576,analysis_RSS_MiB=a['peak_rss_bytes']/1048576,input_sha256={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']})
for n in ['build_edge_sizes','build_edge_combo','build_combo_a8','review_edge_sizes','validate_edge_sizes']:ast.parse((W/'scripts'/(n+'.py')).read_text())
write(W/'results'/(STEM+'_validation.json'),json.dumps(audit,indent=2)+'\n')
print('All source identity, edge50, native pulses, global stress peak, reset and64-case checks passed; electrical failures retained.')
