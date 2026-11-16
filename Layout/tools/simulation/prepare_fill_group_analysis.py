"""Bind completed fill-group physical evidence to a managed read-only analysis."""
import argparse
import json
from pathlib import Path
import re

from Layout.tools.simulation.prepare_full_sim import pull, sha
from Layout.project import config as site_config,evidence as find_evidence

ROOT = Path(__file__).resolve().parents[3]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_id')
    p.add_argument('metal_only_evidence')
    p.add_argument('odpo_only_evidence')
    a = p.parse_args()
    assert all(re.fullmatch(r'[a-z][a-z0-9-]{1,55}', v) for v in vars(a).values())
    dest = ROOT / 'work/layout' / a.run_id
    assert not dest.exists(), 'Do not reuse an execution identity'
    baseline = ROOT / 'work/output/managed_execution/runs/cdac-top-loading-audit-v2/collected/derived/result.json'
    measured = json.loads(baseline.read_text())
    assert measured['analysis_complete']
    config = dict(source_run_id='cdac-full-tt-filled-hold-v1',
                  owned_evidence_roots=[site_config()['remote_root']+'/evidence',site_config()['legacy_root']+'/evidence'],
                  unit_f=measured['cases']['filled']['predicted']['unit_capacitance_f'],
                  cases={})
    payload = {'loading_baseline.json': baseline.read_bytes()}
    common = []
    for name, evidence, omitted in [('metal_only', a.metal_only_evidence, 'odpo'),
                                     ('odpo_only', a.odpo_only_evidence, 'metal')]:
        directory=find_evidence(evidence)
        raw = pull(directory + '/manifest.json')
        m = json.loads(raw)
        assert not m.get('error') and m['case'] == 'full'
        assert all(m['checks'][k]['returncode'] == 0 for k in ('drc', 'lvs', 'phdb', 'rcc', 'format'))
        assert m['checks']['lvs']['verdict'] == 'CORRECT'
        assert m['diagnostic']['omitted_fill'] == omitted
        common.append((m['diagnostic']['source_gds_sha256'], m['diagnostic']['functional_top_sha256']))
        config['cases'][name] = dict(physical_directory=directory,
                                    manifest_sha256=sha(raw), omitted_fill=omitted)
        payload[name + '_physical.json'] = raw
    assert common[0] == common[1]
    config.update(zip(('source_gds_sha256', 'functional_top_sha256'), common[0]))
    payload['fill_groups_context.json'] = (json.dumps(config, indent=2) + '\n').encode()
    for name in ('analyze_fill_groups.py', 'analyze_top_loading.py'):
        payload[name] = (ROOT / 'Layout/tools/analysis' / name).read_bytes()
    dest.mkdir()
    for name, blob in payload.items():
        (dest / name).write_bytes(blob)
    recipe = dict(run_id=a.run_id, kind='analysis_only', source_run_id=config['source_run_id'],
                  design_id='sar8_cdac_fill_group_diagnostic', entry='analyze_fill_groups.py',
                  analyzer='analyze_fill_groups.py',
                  inputs=[dict(name=n, source=(dest/n).relative_to(ROOT).as_posix(), sha256=sha(b))
                          for n, b in payload.items()],
                  resources=dict(threads=1, analysis_rss_mib=256, analysis_virtual_mib=1024,
                                 analysis_wall_seconds=600, queue_timeout_seconds=3600, max_output_mib=32),
                  summary_signals=['post_d_p'], expected_stop_s=260e-9,
                  qualification_scope='Hash-bound native fill-group extraction analysis and charge-model prediction; no new transient result or physical signoff')
    (dest / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
    print((dest / 'recipe.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
