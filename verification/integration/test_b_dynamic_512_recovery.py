"""Focused collection gates/resume regressions; no simulator execution."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/integration'))
import b_dynamic_512_recover as recover
flow = recover.flow


def full_log():
    rows = [f'R3MEAS,{f},128,8,128,1,1e-8\nBSINE,{f},.1,.1,0' for f in range(516)]
    return '\n'.join(rows) + '\nspectre completes with 0 errors, 7 warnings, and 6 notices.\n'


class RecoveryTests(unittest.TestCase):
    def test_missing_exit_status_is_not_upgraded_to_success(self):
        from virtuoso_bridge.spectre.runner import _SpectreRunResult, _build_simulation_result
        result = _build_simulation_result(_SpectreRunResult(False, None, -1, full_log(), '',
            'Original execution status lost', {}), None)
        self.assertFalse(result.ok)
        self.assertTrue(result.errors)

    def test_wrong_host_hash_or_process_is_rejected(self):
        ctx = flow.read(flow.OUT / 'context.json')
        hashes = {Path(p).name: h for p, h in ctx['include_sha256'].items()}
        hashes[flow.DECK.name] = ctx['deck_sha256']
        rows = '\n'.join(f'{h}  {recover.REMOTE}/{p}' for p, h in hashes.items())
        for response in ('wrong-host\n'+rows, 'thu-wei\n'+rows.replace(ctx['deck_sha256'], '0'*64),
                         'thu-wei\n4639 spectre /unrelated/other.scs\n'+rows):
            with patch.object(recover, 'query', return_value=response):
                with self.assertRaises(AssertionError): recover.identity()

    def test_terminal_gates(self):
        p = dict(native_processes=[], clear_anomaly_reasons=[])
        log = full_log()
        self.assertTrue(recover.complete_gate(p, log))
        for bad in (log.replace('BSINE,515,', 'BSINE,514,'),
                    log.replace('R3MEAS,515,', 'R3MEAS,514,'),
                    log.replace('R3MEAS,2,128,8', 'R3MEAS,2,128,7'),
                    log.replace('0 errors,', '1 errors,'),
                    log + '\nERROR (SPECTRE-1): failed\n',
                    log + '\nconvergence failure\n'):
            with self.assertRaises(AssertionError): recover.complete_gate(p, bad)
        with self.assertRaises(AssertionError):
            recover.complete_gate(dict(native_processes=[dict(command='spectre')], clear_anomaly_reasons=[]), log)
        with self.assertRaises(AssertionError):
            recover.complete_gate(dict(native_processes=[], clear_anomaly_reasons=['repeated LTE']), log)

    def test_interrupted_transfer_resume_and_crash_tail(self):
        payload = bytes(range(251)) * 1000
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory(prefix='recovery_test_', dir=flow.OUT) as directory:
            target = Path(directory) / 'small.gz'
            def fail_at_second(remote, offset, length, dest):
                Path(dest).write_bytes(payload[offset:offset+length//2])
                if offset: raise RuntimeError('Simulated SSH connection reset')
                Path(dest).write_bytes(payload[:length])
            with patch.object(recover.time, 'sleep'):
                with self.assertRaises(RuntimeError):
                    recover.download_ranges('/fixture', target, len(payload), digest, fail_at_second, 65536)
            state = flow.read(target.with_suffix('.gz.checkpoint.json'))
            self.assertEqual(state['downloaded_bytes'], 65536)
            partial = target.with_suffix('.gz.partial')
            with partial.open('ab') as stream: stream.write(b'uncommitted crash tail')
            requests = []
            def fetch(remote, offset, length, dest):
                requests.append(offset); Path(dest).write_bytes(payload[offset:offset+length])
            recover.download_ranges('/fixture', target, len(payload), digest, fetch, 65536)
            self.assertEqual(requests[0], 65536)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(flow.sha(target), digest)
            recover.download_ranges('/fixture', target, len(payload), digest, fetch, 65536)

    def test_corrupt_prefix_and_wrong_remote_are_rejected(self):
        payload = b'abcd' * 40000
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory(prefix='recovery_test_', dir=flow.OUT) as directory:
            target = Path(directory) / 'small.gz'
            def fail(remote, offset, length, dest):
                if offset: raise RuntimeError('disconnect')
                Path(dest).write_bytes(payload[:length])
            with patch.object(recover.time, 'sleep'):
                with self.assertRaises(RuntimeError):
                    recover.download_ranges('/fixture', target, len(payload), digest, fail, 65536)
            with self.assertRaises(AssertionError):
                recover.download_ranges('/wrong', target, len(payload), digest, fail, 65536)
            with target.with_suffix('.gz.partial').open('r+b') as stream: stream.write(b'corrupt')
            with self.assertRaises(AssertionError):
                recover.download_ranges('/fixture', target, len(payload), digest, fail, 65536)


if __name__ == '__main__': unittest.main(verbosity=2)
