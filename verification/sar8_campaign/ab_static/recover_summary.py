"""Aggregate collected summaries; preserve raw settings and original server failure."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
segments = ['001-003', '004-035', '036-067', '068-099', '100-131',
            '132-163', '164-195', '196-227', '228-255']
summary = {}
for variant in 'ab':
    runs = [f'sar8camp-{variant}-tt-s{s}-v1' for s in segments]
    data = [json.loads((ROOT/'output/managed_execution/runs'/r/'collected/derived/result.json').read_text()) for r in runs]
    settings = []
    for d in data:
        assert d['functional_pass'] and d['analysis_complete'] and d['native_decode_crosscheck']
        s = dict(d['effective_settings'])
        assert s['maxstep'].split(', default ')[0] == '10 ps'
        s['maxstep'] = '10 ps'
        settings.append(s)
    assert all(s == settings[0] for s in settings)
    thresholds = [t for d in data for t in d['thresholds']]
    assert [t['k'] for t in thresholds] == list(range(1, 256))
    centers = [c for d in data for c in d['centers']]
    assert all(c['code'] == c['expected'] for c in centers)
    assert set(c['code'] for c in centers) == set(range(256))
    assert all(a['upper_v'] < b['lower_v'] for a,b in zip(thresholds, thresholds[1:]))
    mid = [(t['lower_v']+t['upper_v'])/2 for t in thresholds]
    lsb = 1.8/256
    ep = (mid[-1]-mid[0])/254
    dnl = [(b-a)/lsb-1 for a,b in zip(mid, mid[1:])]
    inl = [(v-(mid[0]+i*ep))/ep for i,v in enumerate(mid)]
    summary[variant] = dict(runs=runs, boundary_count=255, center_codes=256,
        functional_pass=True, dnl_min_lsb=min(dnl), dnl_max_lsb=max(dnl),
        inl_endpoint_abs_max_lsb=max(map(abs,inl)), offset_v=mid[0]-(-.9+lsb),
        endpoint_gain_error_percent=(ep/lsb-1)*100,
        max_bracket_width_lsb=max(t['upper_v']-t['lower_v'] for t in thresholds)/lsb,
        midpoints_v=mid, dnl_nominal_lsb=dnl, inl_endpoint_lsb=inl,
        raw_effective_settings=[d['effective_settings'] for d in data],
        limits='TT deterministic only; endpoint saturated widths excluded; electrical qualification deferred')
diff = [(b-a)/(1.8/256) for a,b in zip(summary['a']['midpoints_v'],summary['b']['midpoints_v'])]
summary['comparison'] = dict(max_boundary_difference_lsb=max(map(abs,diff)),
    changed_boundaries=[i+1 for i,d in enumerate(diff) if abs(d)>1e-8])
(OUT/'fullstatic_recovered.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:{f:v for f,v in d.items() if f not in ['runs','midpoints_v','dnl_nominal_lsb','inl_endpoint_lsb','raw_effective_settings']} for k,d in summary.items()},indent=2))
