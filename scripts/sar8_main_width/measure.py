"""Native width screening with explicit settling and net turn-off separation."""
import importlib.util
import json
import numpy as np
from width_flow import ROOT,OUT,VERIFY,NAMES,read,dump,prior
spec=importlib.util.spec_from_file_location('width_pvt_analysis',ROOT/'scripts/sar8_pvt_mismatch/analyze.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
analysis.OUT=OUT;analysis.VERIFY=VERIFY
LIMIT=.25*1.8/256

def measure(name):
    result,raw=analysis.analyze(name);ctx=read(OUT/name/'context.json')
    w={k:np.array(v) for k,v in raw['wave'].items()};t=w['time']*1e9
    diff=w['xdut.topp']-w['xdut.topn']
    for f in result['frames']:
        if ctx['kind']!='static':continue
        assert f['held_observation_before_first_compare']
        pre=f['preclose_time_ns'];held=f['held_observation_ns'];target=f['target_v']
        epre=float(np.interp(pre,t,diff)-target);eh=float(np.interp(held,t,diff)-target)
        assert abs(eh-f['held_error_v'])<1e-6
        f.update(settling_error_mv=epre*1e3,held_error_mv=eh*1e3,net_turnoff_delta_mv=(eh-epre)*1e3,
            settling_pass=abs(epre)<LIMIT,held_pass=abs(eh)<LIMIT,
            turnoff_definition='Held at frame+41.8ns minus preclose at enable50%-0.2ns; includes ongoing settling, feedthrough, charge injection and coupling; NOT isolated channel injection',
            preclose_single_ended_error_mv={s:float(np.interp(pre,t,w['xdut.top'+s]-w['vin'+s+'_src']))*1e3 for s in ['p','n']},
            held_single_ended_error_mv={s:float(np.interp(held,t,w['xdut.top'+s]-w['vin'+s+'_src']))*1e3 for s in ['p','n']},
            gate_vgs_preclose={s:float(np.interp(pre,t,w['xdut.xboot'+s+'.g']-w['vin'+s])) for s in ['p','n']},
            cboot_preclose={s:float(np.interp(pre,t,w['xdut.xboot'+s+'.btop']-w['xdut.xboot'+s+'.bbot'])) for s in ['p','n']})
    result.update(total_main_width_um=ctx['total_main_width_um'],reference_case=ctx['reference_case'],
        stress_detail_scope='445 original selected MOS node pairs; parallel main replicas have identical node voltages. Native CMI checks whole circuit.')
    dump(VERIFY/(name+'.json'),result)
    if ctx['kind']=='static':print(name,[(f['frame'],round(f['settling_error_mv'],4),round(f['net_turnoff_delta_mv'],4),round(f['held_error_mv'],4),f['code']) for f in result['frames']])

def select():
    rows=[]
    for name in NAMES:
        r=read(VERIFY/(name+'.json'));f=r['frames'][1:]
        row=dict(name=name,width_um=r['total_main_width_um'],codes=[x['code'] for x in r['frames']],
            max_abs_preclose_mv=max(abs(x['settling_error_mv']) for x in f),
            max_abs_held_mv=max(abs(x['held_error_mv']) for x in f),
            max_abs_net_turnoff_mv=max(abs(x['net_turnoff_delta_mv']) for x in f),
            functional=r['post_startup_static_code_pass'],timing=r['all_timing_pass'] and r['all_idle_pass'],
            CMI=r['CMI'],stress_failure_count=r['stress_failure_count'])
        row['eligible']=all(x['settling_pass'] and x['held_pass'] for x in f) and row['functional'] and row['timing'] and not row['CMI'] and not row['stress_failure_count']
        rows.append(row)
    eligible=[r['width_um'] for r in rows if r['eligible']]
    result=dict(rows=rows,selected_width_um=min(eligible) if eligible else None,
        criterion='Smallest width with preclose AND held errors below 0.25 LSB for frames1-5; static code/timing/stress pass. Startup reported separately.',
        baseline_promoted=False)
    dump(VERIFY/'selection.json',result);print(json.dumps(result,indent=2))

def summarize():
    setup=read(VERIFY/'setup.json');rows=[]
    for point,corner,sup,temp in prior.POINTS:
        width=setup['selected_width_um'];a=read(VERIFY/f'w{width}_{point}_static.json');b=read(VERIFY/f'w{width}_{point}_sine.json')
        old=read(ROOT/'verification/sar8_pvt_mismatch'/f'{point}_static.json')
        oldsine=read(ROOT/'verification/sar8_pvt_mismatch'/f'{point}_sine.json')
        assert len(a['frames'])==len(b['frames'])==6
        assert a['DUT_sha256']==b['DUT_sha256']==read(OUT/setup['pvt'][0]/'context.json')['DUT_sha256']
        assert a['effective_settings']==old['effective_settings']
        assert b['effective_settings']==oldsine['effective_settings']
        core=max([v for r in [a,b] for g,v in r['groups'].items() if g!='bootstrap'],key=lambda v:v['peak_v'])
        rows.append(dict(point=point,frames=len(a['frames'])+len(b['frames']),
            all_timing_pass=all(r['all_timing_pass'] and r['all_idle_pass'] for r in [a,b]),
            static_codes=[f['code'] for f in a['frames']],original_static_codes=[f['code'] for f in old['frames']],
            sine_codes=[f['code'] for f in b['frames']],original_sine_codes=[f['code'] for f in oldsine['frames']],
            post_startup_code_pass=a['post_startup_static_code_pass'],
            max_held_error_post_startup_mv=max(abs(f['held_error_mv']) for f in a['frames'][1:]),
            original_max_held_error_post_startup_mv=max(abs(f['held_error_v'])*1e3 for f in old['frames'][1:]),
            max_settling_error_post_startup_mv=max(abs(f['settling_error_mv']) for f in a['frames'][1:]),
            max_net_turnoff_post_startup_mv=max(abs(f['net_turnoff_delta_mv']) for f in a['frames'][1:]),
            CMI=a['CMI'] or b['CMI'],core_peak=core,
            stress_failure_pairs_by_case=dict(static=a['stress_failure_count'],sine=b['stress_failure_count']),
            max_conversion_ns=max(f['conversion_ns'] for r in [a,b] for f in r['frames']),
            startup=dict(held_error_mv=a['frames'][0]['held_error_mv'],code=a['frames'][0]['code'])))
    result=dict(selection=read(VERIFY/'selection.json'),PVT=rows,baseline_promoted=False,
        post_startup_sampling_all_five_pass=all(r['max_held_error_post_startup_mv']<LIMIT*1000 and r['max_settling_error_post_startup_mv']<LIMIT*1000 for r in rows),
        screen_all_checks_pass_excluding_startup=all(r['all_timing_pass'] and r['post_startup_code_pass'] and not r['CMI'] and not any(r['stress_failure_pairs_by_case'].values()) and r['max_held_error_post_startup_mv']<LIMIT*1000 and r['max_settling_error_post_startup_mv']<LIMIT*1000 for r in rows),
        scope='Five MOS PVT points, TT passives, six static and six sine frames per point; no mismatch/noise/PEX, no new FFT/INL/DNL',
        status=read(VERIFY/'status.json'))
    dump(VERIFY/'results.json',result);print(json.dumps(rows,indent=2))

if __name__=='__main__':
    import sys
    if sys.argv[1:] in [['select'],['summary']]: (select if sys.argv[1]=='select' else summarize)()
    else:
        for name in sys.argv[1:]:measure(name)
