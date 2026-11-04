"""Bounded native DFF analysis; Python2.7/3; does not launch Spectre."""
from __future__ import print_function
import argparse
import json
import os
import re
import struct
import sys
sys.dont_write_bytecode=True
import full_gate_analyze as frozen
import fast_gate_analyze as native
import standard_cell_full_analyze as storage


def pin_edges(rows,index,rail):
    levels={}
    for fraction in [.1,.2,.5,.8,.9]:
        hits=[];level=fraction*rail
        for a,b in zip(rows,rows[1:]):
            x,y=a[index]-level,b[index]-level
            direction=1 if x<0<=y else -1 if x>0>=y else 0
            if direction:hits.append(dict(time_s=a[0]-x*(b[0]-a[0])/(y-x),direction=direction,native_bracket_s=[a[0],b[0]]))
        levels[fraction]=hits
    out=[]
    for e in levels[.5]:
        found={}
        for f,hits in levels.items():
            selected=[h for h in hits if h['direction']==e['direction'] and abs(h['time_s']-e['time_s'])<=.25e-9]
            found[f]=selected[0] if len(selected)==1 else None
        value=dict(e,crossings=dict((str(f),v) for f,v in found.items()))
        for name,a,b in [('slew_10_90_s',.1,.9),('slew_20_80_s',.2,.8)]:
            value[name]=abs(found[b]['time_s']-found[a]['time_s']) if found[a] and found[b] else None
        out.append(value)
    return out


def usage_observations(output,cfg):
    names=native.read(os.path.join(output,'peak.columns.json'))['names'];index=dict((n,i) for i,n in enumerate(names))
    pins=cfg['usage']['input_pins'];columns=[0]+[index[native.norm(n)] for n in pins.values()]
    rows=[];pack=struct.Struct('<'+'d'*len(names));observed=0
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob=handle.read(pack.size)
            if not blob:break
            if len(blob)!=pack.size:raise ValueError('Incomplete native diagnostic row')
            row=pack.unpack(blob);rows.append(tuple(row[i] for i in columns));observed+=1
            if observed>200000:raise ValueError('Diagnostic edge-memory budget exceeded')
    return dict(actual_pin_edges=dict((key,pin_edges(rows,j+1,cfg['usage']['vdd_v'])) for j,key in enumerate(pins)),
        pin_waveform_rows=observed,threshold_policy='10/90 and20/80 percent declared0.99V; native linear crossing brackets retained; no library table range inferred',
        intrinsic_channel_overlap_junction_split=None,region_saved=False,
        source_timing_unchanged=True,whole_ADC_qualified=None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();run=os.path.realpath(args.run_dir);output=os.path.realpath(args.output_dir)
    if output!=os.path.join(run,'derived') or (os.path.isdir(output) and os.listdir(output)):
        raise ValueError('Fresh managed derived directory required')
    state=native.read(os.path.join(run,'simulation.state.json'));info=state.get('native',{})
    if state['status']!='complete' or state['exit_code']!=0 or not info.get('native_analysis_pass') or not info.get('zero_error_footer'):
        raise ValueError('Native simulation must be complete/PASS')
    with open(os.path.join(run,'raw/logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):raise ValueError('Native transient PASS missing')
    external=storage.verify_external(os.path.join(run,'inputs/external_library.json'))
    raw=[os.path.join(run,'raw',x) for x in os.listdir(os.path.join(run,'raw')) if x.endswith('.tran.tran')]
    if len(raw)!=1:raise ValueError('Exactly one native ASCII transient required')
    cfgpath=os.path.join(run,'inputs/measurement.json');cfg=native.read(cfgpath)
    result=native.summarize(raw[0],cfg,output)
    result['storage_observations']=storage.observe_history(output,cfg)
    result['usage_observations']=usage_observations(output,cfg)
    result['measurement_sha256']=storage.identity(cfgpath)['sha256'];result['external_identity']=external
    result.pop('peak_error_v',None);result.pop('peak_time_error_s',None)
    result['peak_snapshot_role']='Maximum diagnostic net176 value; MM64 stress uses every simultaneous native D/S pair, never this maximum as its minimum'
    result['physical_terminal_screen_pass']=not any(x['over_limit_native_points'] for x in result['full_history_voltage_stress'].values())
    result['native_warning_codes']=info.get('warning_codes');result['native_effective_settings']=info.get('effective_settings')
    result['whole_ADC_qualified']=None;result['returned_waveform']=storage.compress_history(output)
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS budget exceeded')
    encoded=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    storage.collection_budget(run,output,cfg,len(encoded))
    native.write_new(os.path.join(output,'result.json'),result)
    print('NATIVE_DFF_USAGE_DIAGNOSTIC_COMPLETE',result['native_points'],'ADC_unqualified')


if __name__=='__main__':main()
