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
import fast_gzip_analyze as native
import standard_cell_full_analyze as storage
import storage_gzip as history
import usage_gzip as usage
import read_info as opmap


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
    result['storage_observations']=history.observe_history(output,cfg)
    result['usage_observations']=usage.usage_observations(output,cfg)
    result['native_field_exposure']=opmap.observe(run,native.read(os.path.join(run,'inputs/mapping.json')))
    result['measurement_sha256']=storage.identity(cfgpath)['sha256'];result['external_identity']=external
    result.pop('peak_error_v',None);result.pop('peak_time_error_s',None)
    result['peak_snapshot_role']='Maximum diagnostic net176 value; MM64 stress uses every simultaneous native D/S pair, never this maximum as its minimum'
    result['physical_terminal_screen_pass']=not any(x['over_limit_native_points'] for x in result['full_history_voltage_stress'].values())
    result['native_warning_codes']=info.get('warning_codes');result['native_effective_settings']=info.get('effective_settings')
    result['whole_ADC_qualified']=None;result['returned_waveform']=history.verify_compressed(output,cfg,result)
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS budget exceeded')
    encoded=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    storage.collection_budget(run,output,cfg,len(encoded))
    native.write_new(os.path.join(output,'result.json'),result)
    print('NATIVE_MM65_FIELD_EXPOSURE_COMPLETE',result['native_points'],'ADC_unqualified')


if __name__=='__main__':main()
