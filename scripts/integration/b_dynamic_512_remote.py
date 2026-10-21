"""Bounded metrics/figure exchange only, no native launch or raw download."""
import argparse
import json
from pathlib import Path

import b_dynamic_512 as flow
import b_dynamic_512_recover as recover

REMOTE_SCRIPT = recover.REMOTE + '/remote_analysis_v1/status.py'


def validate_asset(name, size):
    policy = flow.data_policy()
    if Path(name).name != name: raise ValueError('Result asset must be a simple filename')
    suffix = Path(name).suffix.lower()
    limit = policy.get('max_metrics_json_bytes', 0) if suffix == '.json' else policy.get('max_figure_png_bytes', 0) if suffix == '.png' else 0
    if not 0 <= size <= limit or not limit: raise ValueError('Only bounded metrics JSON and PNG figures may be returned')


def install():
    source = Path(__file__).with_name('b_dynamic_512_remote_status.py').read_text(encoding='utf-8')
    ssh = recover.client()
    try:
        r = ssh.spectre_runner.run_command('mkdir -p ' + recover.REMOTE + '/remote_analysis_v1', timeout=25)
        assert r.returncode == 0
        r = ssh.spectre_runner.upload_text(source, REMOTE_SCRIPT, timeout=30)
        assert r.returncode == 0
    finally: ssh.close()


def status():
    flow.check()
    text = recover.query('/usr/bin/python ' + REMOTE_SCRIPT)
    validate_asset('status.json', len(text.encode('utf-8')))
    result = json.loads(text)
    assert result['exact_root'] == recover.REMOTE
    assert result['deck_sha256'] == flow.read(flow.OUT / 'context.json')['deck_sha256']
    assert not result['raw_downloaded'] and not result['native_restarted']
    flow.dump(flow.OUT / 'remote_only_status.json', result)
    flow.stage(result['stage'], remote_only=True, total_frames=516)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['install', 'status'])
    globals()[p.parse_args().action]()
