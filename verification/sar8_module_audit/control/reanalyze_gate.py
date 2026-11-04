"""Read completed source into a separate managed result; Python 2.7/3 stdlib."""
from __future__ import print_function
import argparse
import json
import os
import re
import sys

import native_boundary_export as common
import supplement_native_export as checked
import full_gate_analyze as worker

SOURCES={
    'sar8audit-ctrl-snload-both-v1':'66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c',
    'sar8audit-ctrl-mp1shape-v1':'8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a',
}


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-dir',required=True)
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--source-run-dir',required=True)
    a=ap.parse_args(argv)
    run,out,source=common.validate_paths(a.run_dir,a.output_dir,a.source_run_dir)
    config=common.read_json(os.path.join(run,'inputs','reanalysis_manifest.json'))
    if SOURCES.get(config['source_run_id'])!=config['source_recipe_hash']:
        raise ValueError('Unexpected completed source binding')
    raw,provenance=common.source_preflight(source,config)
    source_recipe=common.read_json(os.path.join(source,'recipe.json'))
    all_inputs=checked.all_source_inputs(source,source_recipe)
    log=os.path.join(source,'raw','logStatus')
    with open(log) as handle:
        if not re.search(r'\btran_first\s+PASS\b',handle.read()):raise ValueError('Native PASS missing')
    provenance['small_file_sha256']['raw/logStatus']=common.sha(log)
    measure_path=os.path.join(run,'inputs','measurement.json')
    measure=common.read_json(measure_path)
    if not os.path.exists(out):os.mkdir(out)
    result=worker.summarize(raw,measure,out)
    provenance.update(all_registered_source_inputs=all_inputs,raw_path=raw,
        raw_full_sha256=common.sha(raw),raw_stat_after=common.stat_identity(raw),
        measurement_sha256=common.sha(measure_path),wrapper_sha256=common.sha(os.path.realpath(__file__)))
    if provenance['raw_stat_before']!=provenance['raw_stat_after'] or all_inputs!=checked.all_source_inputs(source,source_recipe):
        raise ValueError('Source changed during full-history reanalysis')
    for name,expected in provenance['small_file_sha256'].items():
        if common.sha(os.path.join(source,name))!=expected:raise ValueError('Source metadata changed')
    provenance['source_readonly_checks_pass']=True
    common.write_new(os.path.join(out,'source_readonly_provenance.json'),provenance)
    native=common.read_json(os.path.join(source,'simulation.state.json'))['native']
    result.update(source_run_id=config['source_run_id'],source_recipe_hash=config['source_recipe_hash'],
        source_raw_full_sha256=provenance['raw_full_sha256'],measurement_sha256=common.sha(measure_path),
        source_warning_codes=native.get('warning_codes'),export_only=True,simulation_started=False,
        source_completed_simulation_verified=True,source_END_scanned=result['native_PSF_END'])
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS cap exceeded')
    if sum(os.path.getsize(os.path.join(out,n)) for n in os.listdir(out))+65536>=32*1024**2:
        raise ValueError('Collection output cap exceeded')
    common.write_new(os.path.join(out,'result.json'),result)
    print('FULL_GATE_REANALYSIS_OK',config['source_run_id'],result['native_points'])


if __name__=='__main__':main()
