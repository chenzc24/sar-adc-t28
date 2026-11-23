"""Current SAR FFT: native-code crosscheck, protocol records, bounded reduction.

Python 2/3, no scientific runtime required on the simulation host.
"""
from __future__ import print_function
import argparse
import json
import math
import os
import re
from native_stream import samples
from dynamic_reduce import spectrum


def protocol_valid(row):
    return (len(row) == 14 and row[2:6] == [8, 8, 8, 0] and
            row[1] == row[6] and row[7] == 1 and 0 < row[13] < 60e-9)


def analyze(run_dir, output_dir):
    c = json.load(open(run_dir+'/inputs/context.json'))
    records = []
    warnings = set()
    effective = {}
    for line in open(run_dir+'/spectre.out'):
        m = re.search(r'FFTMEAS,([^\r\n]+)', line)
        if m:
            records.append([float(v) for v in m.group(1).split(',')])
        warnings.update(re.findall(r'WARNING \(([^)]+)\)', line))
        for key in ['maxstep', 'reltol', 'method', 'noisefmin', 'noisefmax', 'noiseseed']:
            m = re.match(r'\s*'+key+r' = (.+)', line)
            if m:
                effective[key] = m.group(1).strip()
    assert len(records) == c['frames'], 'Missing or duplicate observer frame'
    assert [int(row[0]) for row in records] == list(range(c['frames']))
    assert all(len(row)==14 and all(not math.isnan(v) and not math.isinf(v) for v in row) for row in records)
    assert 'noisefmax' in effective, 'No native evidence that transient noise is enabled'
    files = [run_dir+'/raw/'+n for n in os.listdir(run_dir+'/raw') if n.endswith('.tran.tran')]
    assert len(files) == 1
    codes = []
    points = 0
    prev = None
    area = dict(vdd=0., ref_high=0., clock=0.)
    begin = c['frame_origin_s']+c['warmup']*c['period_s']
    end = begin+c['samples']*c['period_s']
    for t, v in samples(files[0]):
        points += 1
        assert all(k in v and not math.isnan(v[k]) and not math.isinf(v[k]) for k in c['signals'])
        frame = int(round((t-c['frame_origin_s']-98e-9)/c['period_s']))
        if 0 <= frame < c['frames'] and abs(t-(c['frame_origin_s']+98e-9+frame*c['period_s'])) < 1e-13:
            assert frame == len(codes), 'Duplicate or missing native decode sample'
            codes.append(sum(1 << bit for bit in range(8) if v['d%d'%bit] > .5*v['vdd!']))
        power = dict(vdd=-v['vdd!']*v['vvdd:p'], ref_high=-.9*v['vrefhigh:p'], clock=-v['sample']*v['vsample:p'])
        if prev:
            pt, pv = prev
            lo, hi = max(pt, begin), min(t, end)
            if hi > lo:
                for key in area:
                    vl = pv[key]+(power[key]-pv[key])*(lo-pt)/(t-pt)
                    vh = pv[key]+(power[key]-pv[key])*(hi-pt)/(t-pt)
                    area[key] += .5*(vl+vh)*(hi-lo)
        prev = t, power
    assert points and t >= c['stop_s']-1e-13 and len(codes) == c['frames']
    assert codes == [int(row[1]) for row in records], 'Native/observer code disagreement'
    bad = [int(row[0]) for row in records if not protocol_valid(row)]
    measured = codes[c['warmup']:]
    assert len(measured) == c['samples']
    # A segment of a split record has no coherent spectrum of its own; fft_stitch.py combines the segments.
    fft = spectrum(measured, c['bin']) if not c['pilot'] and not c.get('segment') else None
    watts = dict((k, v/(end-begin)) for k, v in area.items())
    result = dict(analysis_complete=True, context=c, native_decode_crosscheck=True,
                  frames=records, codes=measured, invalid_all_frames=bad,
                  invalid_steady_frames=[i for i in bad if i >= c['warmup']],
                  functional_pass=not bad, spectrum=fft, effective_settings=effective,
                  native_points=points, warning_codes=sorted(warnings),
                  power_w=watts, power_core_plus_reference_w=watts['vdd']+watts['ref_high'],
                  power_qualification='10 ps grid estimate; convergence unverified; ideal input source power excluded; clock separate',
                  electrical_verdict='not_full_terminal_qualified',
                  limitations=['Single noise seed; noise bandwidth convergence not established',
                               'No process variation, mismatch, PEX or external source jitter',
                               'Transient model noise including external 50 ohm resistors; ideal sources remain noiseless',
                               'No reference capture clock in current design: record column 5 is zero, not a missing event',
                               'Pilot uses 2 MHz low-frequency shaping floor and is not a qualified noise spectrum' if c['pilot'] else 'Noise shaping floor 10 kHz, bandwidth 2 GHz; no sub-10-kHz flicker qualification'])
    with open(output_dir+'/result.json','w') as f:
        json.dump(result, f, indent=2)
    print('NOISE_FFT_COMPLETE', result['functional_pass'], len(measured))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    analyze(a.run_dir, a.output_dir)
