"""Prepare bounded read-only full-history stress/energy jobs, no Spectre reruns."""
import copy
import json
import re

import gate_observer_support as observer
import prepare_first_event as base
from review_both_result import read_current_run

OWN,ROOT=base.OWN,base.ROOT
DEST=OWN/'gate_reanalysis_v1'
CASES=[('mp1shape','sar8audit-ctrl-mp1shape-v1','8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a','XDUT.XCTRL.XTIM.X020.X000.B_PM'),
       ('both','sar8audit-ctrl-snload-both-v1','66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c','XDUT.XCTRL.XTIM.LIVE')]


def main():
    worker=observer.generate()
    for label,run,signature,gate in CASES:
        _,_,_,measure,proof=read_current_run(run,signature)
        target=DEST/label
        measure=copy.deepcopy(measure);measure.update(observer.observations(gate))
        measure['scope']='Read-only whole-native-history MP1 stress and five-source energy; no circuit change or new simulation'
        base.write_json(target/'measurement.json',measure)
        source=ROOT/'output/managed_execution/runs'/run/'inputs'
        config=dict(source_run_id=run,source_recipe_hash=signature,
            source_input_sha256={name:base.digest((source/name).read_bytes()) for name in ['dut.scs','test.scs']},
            signals=[dict(frozen_save_name=name,native_match_name=name.lower()) for name in [gate,'XDUT.XCTRL.XTIM.X020.N','VDD!']])
        saved=set(re.findall(r'(?m)^save\s+(\S+)',(source/'test.scs').read_text()))
        if any(item['frozen_save_name'] not in saved for item in config['signals']):raise ValueError('Stress save missing')
        base.write_json(target/'manifest.json',config)
        files=[('reanalyze_gate.py',OWN/'reanalyze_gate.py'),('full_gate_analyze.py',worker),
            ('native_boundary_export.py',OWN/'native_boundary_export.py'),
            ('supplement_native_export.py',OWN/'supplement_native_export.py'),
            ('measurement.json',target/'measurement.json'),('reanalysis_manifest.json',target/'manifest.json')]
        recipe=dict(kind='analysis_only',run_id='sar8audit-ctrl-'+label+'-stress-v1',source_run_id=run,
            design_id='sar8_control_full_native_gate_stress_energy',analyzer='reanalyze_gate.py',
            inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=name,sha256=base.digest(p.read_bytes())) for name,p in files],
            expected_stop_s=measure['source_history_stop_s'],summary_signals=[gate.lower()],qualification_scope=measure['scope'],
            oa_parity='read_only_source_no_OA_change',
            resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,simulation_wall_seconds=1,
                analysis_rss_mib=256,analysis_virtual_mib=1024,analysis_wall_seconds=900,max_output_mib=64,queue_timeout_seconds=600))
        base.write_json(target/'recipe.suggested.yaml',recipe)
        base.write_json(target/'package_manifest.json',dict(source=proof,run_id=recipe['run_id'],declared_input_bytes=sum(p.stat().st_size for _,p in files),
            source_unchanged=True,no_new_simulation=True,full_history_targets=list(measure['stress_voltage_pairs']),
            all_source_energy_ports=list(measure['source_power_ports']),remote_operations=False))
        print(label,recipe['run_id'],sum(p.stat().st_size for _,p in files))


if __name__=='__main__':main()
