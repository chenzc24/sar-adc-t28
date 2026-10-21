"""Fail closed before writing/downloading a complete native waveform."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/integration'))
import b_dynamic_512_remote as remote
flow, recovery = remote.flow, remote.recover


class RemotePolicyTests(unittest.TestCase):
    def test_no_bulk_download_or_legacy_watcher(self):
        fetch = Mock()
        with self.assertRaises(RuntimeError): recovery.watch()
        with self.assertRaises(RuntimeError):
            recovery.download_ranges(recovery.PACKED, flow.OUT/'forbidden.gz', 100, '0'*64, fetch)
        with self.assertRaises(RuntimeError): recovery.fetch_range(recovery.PACKED, 0, 100, flow.OUT/'forbidden.range')
        with self.assertRaises(RuntimeError):
            flow.LosslessTransfers(Mock()).download(recovery.REMOTE+'/b_dynamic_512.raw', flow.OUT/'forbidden.raw', recursive=True)
        fetch.assert_not_called()
        self.assertFalse((flow.OUT/'forbidden.gz').exists())

    def test_bounded_metrics_and_figure_only(self):
        remote.validate_asset('summary.json', 4096)
        remote.validate_asset('figure.png', 100000)
        for name, size in [('raw.gz', 1), ('waveform.pickle', 1), ('raw.csv', 1),
                           ('summary.json', 2**20+1), ('figure.png', 4*2**20+1), ('../summary.json', 1)]:
            with self.assertRaises(ValueError): remote.validate_asset(name, size)


if __name__ == '__main__': unittest.main(verbosity=2)
