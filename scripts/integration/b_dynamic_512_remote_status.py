#!/usr/bin/python
"""Remote Python2/3 stdlib metric extraction; never sends log/raw waveforms."""
from __future__ import print_function
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import time

ROOT = '/tmp/virtuoso_bridge_chenzc_intern25/90590/virtuoso_bridge_spectre/cf76d807'


def metrics(root=ROOT):
    assert root == ROOT
    with io.open(root + '/spectre.out', encoding='utf-8', errors='replace') as stream:
        log = stream.read()
    rows = re.findall(r'R3MEAS,(\d+),(\d+),(\d+),(\d+),(\d+),([^\s,]+)', log)
    probes = re.findall(r'BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)', log)
    ps = subprocess.check_output(['ps', '-u', 'chenzc_intern25', '-ww', '-o', 'pid,etime,pcpu,comm,args'], universal_newlines=True)
    native = []
    for line in ps.splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5 and parts[0].isdigit() and parts[3] == 'spectre' and root + '/b_dynamic_512.scs' in parts[4]:
            native.append(dict(pid=int(parts[0]), elapsed=parts[1], cpu_percent=float(parts[2])))
    raw = root + '/b_dynamic_512.raw/tran_b_sine.tran.tran'
    size = os.path.getsize(raw)
    with open(raw, 'rb') as stream:
        stream.seek(max(0, size - 65536))
        tail = stream.read().decode('utf-8', errors='replace')
    times = re.findall(r'^"time"\s+([^\s]+)', tail, re.M)
    footer = next((line for line in log.splitlines() if line.startswith('spectre completes with')), None)
    full_history = [int(r[0]) for r in rows] == list(range(516)) and [int(r[0]) for r in probes] == list(range(516))
    invalid = [int(r[0]) for r in rows if r[2] != '8' or r[4] != '1' or r[1] != r[3]]
    peak = .9 * 10**(-1./20)
    gross = []
    for row in rows:
        frame, code = int(row[0]), int(row[1])
        if frame < 4: continue
        sample = (frame * 100 + 41.05 - 1.781261) * 1e-9
        expected = max(0, min(255, int(math.floor((peak * math.sin(2 * math.pi * 4511718.75 * sample - .4 * math.pi) + .9) / (1.8 / 256)))))
        if abs(code-expected) > 8: gross.append(frame)
    fatal = [line.strip() for line in log.splitlines() if re.match(r'\s*(FATAL|ERROR)\s*\(', line)]
    normal = bool(footer and footer.startswith('spectre completes with 0 errors'))
    state = 'running_native_remote_only' if native else ('native_complete_remote_analysis_pending' if full_history and normal else 'native_exited_incomplete')
    notes = [line.strip() for line in log.splitlines() if 'SPECTRE-16780' in line]
    deck_hash = hashlib.sha256()
    with open(root + '/b_dynamic_512.scs', 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): deck_hash.update(block)
    return dict(stage=state, checked_unix_s=time.time(), exact_root=root,
        native_processes=native, completed_frames=len(rows), observed_frames=max(0, len(rows)-4),
        requested_frames=516, full_history=full_history, native_footer=footer,
        invalid_frames=invalid, gross_code_frames=gross, LTE_count=log.count('SPECTRE-16780'),
        LTE_notes=notes[-3:], has_CMI='CMI-2754' in log, fatal_lines=fatal[-3:],
        raw_bytes=size, raw_mtime_unix_s=os.path.getmtime(raw), raw_last_time_s=float(times[-1]) if times else None,
        last_records=rows[-2:], native_os_exit_status=None, deck_sha256=deck_hash.hexdigest(),
        native_restarted=False, raw_downloaded=False, analysis_location='remote',
        runtime_python=sys.version.split()[0], full_dynamic_analysis_complete=False,
        failure_cause='unknown' if state == 'native_exited_incomplete' else None)


if __name__ == '__main__': print(json.dumps(metrics(), sort_keys=True, allow_nan=False))
