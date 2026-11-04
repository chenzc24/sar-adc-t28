"""Independent native-window pulse/clock checks and frozen-input provenance."""
import csv,gzip,json,re,hashlib,ast
from array import array
import numpy as np
from setup import W,ROOT,write
from review_edge500 import RUNS
from review_precharge import pulse

summary=json.loads((W/'results/edge500_comparison.json').read_text())
baseline=W/'testbenches/cmpdesign-rise200-fall200-a4-ff-hot-v1'
old=json.loads((W/'results/cmpdesign-rise200-fall200-a4-ff-hot-v1/result.json').read_text())
audit={}
for ps,run in RUNS.items():
    src=baseline if ps=='200/200' else W/'testbenches'/run
    cfg=json.loads((src/'measure.json').read_text())
    col=ROOT/'output/managed_execution/runs'/run/'collected'
    r=json.loads((col/'derived/result.json').read_text())
    s=json.loads((col/'simulation.state.json').read_text()) if ps!='200/200' else json.loads((W/'results/cmpdesign-rise200-fall200-a4-ff-hot-v1/simulation.state.json').read_text())
    a=json.loads((col/'analysis.state.json').read_text())
    assert s['exit_code']==0 and s['native']['zero_error_footer']
    assert (src/'dut.scs').read_bytes()==(baseline/'dut.scs').read_bytes()
    assert (src/'models.scs').read_bytes()==(baseline/'models.scs').read_bytes()
    original=(baseline/'test.scs').read_text();deck=(src/'test.scs').read_text()
    assert re.sub(r'^VCK .*$', '',deck,flags=re.M)==re.sub(r'^VCK .*$', '',original,flags=re.M)
    rp,fp=map(int,ps.split('/'))
    raw=re.search(r'^VCK .*wave=\[(.*)\]$',deck,re.M).group(1).split()
    points=[(float(raw[i]),float(raw[i+1])) for i in range(0,len(raw),2)]
    assert len(points)==129
    for i,e in enumerate(cfg['events']):
        k=1+4*i
        assert abs((points[k+1][0]-points[k][0])-rp*1e-12)<1e-20
        assert abs((points[k+3][0]-points[k+2][0])-fp*1e-12)<1e-20
        assert abs((points[k+1][0]+points[k][0])/2-e['clock50'])<1e-20
        assert abs((points[k+3][0]+points[k+2][0])/2-e['fall50'])<1e-20
    names=['time','ck','opa4_held','ona4_held']+['xa4_held.'+n for n in ['net1','net2','lp','ln']]
    buf={n:array('d') for n in names}
    with gzip.open(col/'derived/wave.csv.gz','rt') as f:
        rows=csv.reader(f);head=next(rows);ids=[head.index(n) for n in names]
        for row in rows:
            for n,i in zip(names,ids):buf[n].append(float(row[i]))
    d={n:np.frombuffer(v,dtype='d') for n,v in buf.items()};t=d['time'];ck=d['ck']
    # Display export is decimated outside event windows; native reducer checks exact stop.
    assert 0<=cfg['stop_s']-t[-1]<21e-12
    err=[]
    for e in cfg['events']:
        for center,up in [(e['clock50'],True),(e['fall50'],False)]:
            indices=np.where((t[:-1]>center-300e-12)&(t[1:]<center+300e-12)&((ck[:-1]<.495)&(ck[1:]>=.495) if up else (ck[:-1]>.495)&(ck[1:]<=.495)))[0]
            assert len(indices)==1
            k=indices[0];cross=t[k]+(t[k+1]-t[k])*(.495-ck[k])/(ck[k+1]-ck[k])
            err.append(abs(cross-center))
    assert max(err)<1e-15
    # Independently check the changed reset search window, including before fall50.
    for e,row in zip(cfg['events'],r['contexts']['A4_held']['rows']):
        mask=(t>=e['fall_start'])&(t<e['fall50']+.8e-9)
        tt=t[mask];good=np.maximum(d['opa4_held'][mask],d['ona4_held'][mask])<=.2*.99
        bad=np.where(~good)[0]
        k=int(bad[-1]+1) if len(bad) else 0
        assert k<len(tt) and good[k:].all()
        assert abs(tt[k]-row['reset_since_s'])<2e-15
    checks=[]
    for group in ['reset_latch','reset_input','startup_input','startup_latch']:
        for metric in ['worst_peak_pulse','longest_pulse']:
            p=summary[str(ps)]['held'][group][metric]
            if p is None:continue
            e=cfg['events'][p['event_index']]
            if group.startswith('reset'):
                mask=(t>=e.get('fall_start',e['fall50']-25e-12)-20e-12)&(t<e['fall50']+.5e-9)
            else:
                mask=(t>=e['rise_start']-40e-12)&(t<e['t']+800e-12)
            tt=t[mask];yy=d['xa4_held.'+p['node']][mask]
            # An event can have a sharp peak followed by a separate, tiny long tail.
            # Select the pulse containing the reported peak time, then independently
            # find its two threshold brackets in the exported native samples.
            k=int(np.argmin(abs(tt-p['time_s'])));lo=hi=k
            assert yy[k]>.99
            while lo>0 and yy[lo-1]>.99:lo-=1
            while hi+1<len(tt) and yy[hi+1]>.99:hi+=1
            assert lo>0 and hi+1<len(tt)
            q=pulse(tt[lo-1:hi+2],yy[lo-1:hi+2],.99)
            assert not q['window_clipped']
            assert abs(q['peak_V']-p['peak_V'])<1e-10
            assert abs(q['width_s']-p['duration_s'])<1e-14
            checks.append({'group':group,'metric':metric,'peak_delta_V':q['peak_V']-p['peak_V'],'width_delta_s':q['width_s']-p['duration_s']})
    for key,c in r['contexts'].items():
        assert len(c['rows'])==32 and c['all_correct'] and c['all_reset']
        if ps=='200/200':
            for f in ['max_decision_s','max_reset_s','terminal_pairs','max_residual_V','mean_comparator_supply_W']:
                assert c[f]==old['contexts'][key][f]
    audit[ps]={'run_id':run,'DUT_models_identical':True,'only_VCK_source_changed':True,'native_complete400ns':True,'all64_decision_reset_pass':True,'clock50_max_error_s':max(err),'native_pulse_crosscheck':checks,'baseline_existing_metrics_identical':True if ps=='200/200' else None,'effective_settings':s['native']['effective_settings'],'warnings':s['native']['warning_codes'],'simulation_seconds':s['elapsed_seconds'],'simulation_RSS_MiB':s['peak_rss_bytes']/1048576.,'analysis_RSS_MiB':a['peak_rss_bytes']/1048576.,'inputs_sha256':{n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}}
    del buf,d,t,ck
for n in ['build_edge500.py','edge500_reduce.py','review_edge500.py','validate_edge500.py']:
    ast.parse((W/'scripts'/n).read_text())
write(W/'results/edge500_validation.json',json.dumps(audit,indent=2)+'\n')
print('All native clock50, pulse, source identity, baseline equivalence and64-case functional checks passed; electrical failures retained.')
