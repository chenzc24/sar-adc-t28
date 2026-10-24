"""Isolated transport for native stress-closure experiments."""
from pathlib import Path
import importlib.util
import sys
import contextlib
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('closure_transport', ROOT/'scripts/sar8_ref_gate_controls/control.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
OUT = ROOT/'output/sar8_stress_closure'
VERIFY = ROOT/'verification/sar8_stress_closure'
REMOTE = '/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
OUT.mkdir(exist_ok=True)
VERIFY.mkdir(exist_ok=True)
transport.OUT, transport.VERIFY, transport.REMOTE = OUT, VERIFY, REMOTE
wf = transport.wf
wf.OUT = wf.base.OUT = OUT
wf.VERIFY = VERIFY
wf.REMOTE = wf.base.REMOTE = REMOTE
# Target login currently incurs ~23s latency. Keep retries bounded but do not
# confuse the inherited30s status deadline with failed native simulation.
_original_command = wf.base.command
def command(ssh, cmd, timeout=90):
    return _original_command(ssh, cmd, timeout=max(timeout, 90))
wf.base.command = command

if __name__ == '__main__':
    if sys.argv[1] == 'preflight':
        wf.preflight()
    elif sys.argv[1] == 'remote':
        print(transport.remote(sys.argv[2]))
    elif sys.argv[1] == 'status':
        wf.status()
    elif sys.argv[1] in ['launch', 'collect', 'reduce']:
        action, names = sys.argv[1], sys.argv[2:]
        with (OUT/(action+'.log')).open('a') as log, contextlib.redirect_stdout(log):
            if action == 'reduce':
                # Include current traces in the lossless reduced window set.
                ssh = wf.base.client()
                import shlex
                for name in names:
                    folder = OUT/name
                    ctx = transport.read(folder/'context.json')
                    remote = transport.read(folder/'launch.json')['remote']
                    assert wf.base.command(ssh, 'cat '+shlex.quote(remote+'/exit_code')).strip() == '0'
                    assert not (folder/'reduction.json').exists()
                    ctx['timing_signals'] = ctx['saved_signals']
                    transport.dump(folder/'reduction_context.json', ctx)
                    for src, dest in [(folder/'reduction_context.json', 'context.json'),
                                      (ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py', 'reduce.py')]:
                        r = ssh.upload(src, remote+'/'+dest, timeout=60)
                        assert r.returncode == 0, r.stderr
                    cmd = 'cd '+shlex.quote(remote)+' && python reduce.py > reduce.log 2>&1; echo $? > '+shlex.quote(remote+'/reduce_exit')
                    pid = wf.base.command(ssh, 'nohup sh -c '+shlex.quote(cmd)+' > /dev/null 2>&1 < /dev/null & echo $!')
                    transport.dump(folder/'reduction.json', dict(remote=remote,pid=pid.strip()))
            else:
                getattr(wf, action)(names)
        print(action, names)
    else:
        raise ValueError('Unknown action')
