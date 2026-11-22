"""Run a simulation's own analyzer again on its retained waveform, as an analysis-only job (Python 2.7 on the host).

Used when the source run's analysis phase was rejected (queue timeout) after its simulation completed. The source
analyzer reads --run-dir only, so it is pointed at the source run directory; its bytes are the source deck's.
"""
from __future__ import print_function
import argparse
import json
import os
import subprocess
import sys

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'reanalyze.json')) as stream:
        analyzer = json.load(stream)['source_analyzer']
    sys.exit(subprocess.call([sys.executable, os.path.join(here, analyzer), '--run-dir', a.source_run_dir,
                              '--output-dir', a.output_dir], cwd=here))
