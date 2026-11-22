"""Stitch the segments of a split TT FFT (prepare_stage6 fft --segment) into one 1024-point record.

Each segment's collected result (noise_fft_reduce.py) holds its eight warm-up frames and 64 FFT frames. Segment
k's warm-up frames are the record's frames 64k-8 .. 64k-1, which segment k-1 also measured as its last eight FFT
frames. Those overlaps are compared code by code: with independent noise seeds they should agree within +/-1
code. The 1024 codes then give the coherent spectrum (dynamic_reduce.spectrum). Per segment this also reports
the functional result, its seed and power, and the RMS error of its codes against the least-squares sine of the
whole record.
Usage: python -m Layout.tools.analysis.fft_stitch RUN_ID [RUN_ID ...] --output Layout/results/....json
"""
import argparse
import json
import math
import sys

from Layout.project import ROOT

sys.path.insert(0, str(ROOT / 'tools/saradc/measure'))
from dynamic_reduce import spectrum  # noqa: E402

RUNS = ROOT / 'work/output/managed_execution/runs'


def sine_fit(codes, k):
    """Least-squares offset + sine at bin k of len(codes); returns the fitted values."""
    n = len(codes)
    c = [math.cos(2 * math.pi * k * i / n) for i in range(n)]
    s = [math.sin(2 * math.pi * k * i / n) for i in range(n)]
    mean = sum(codes) / n
    a = 2 * sum((x - mean) * ci for x, ci in zip(codes, c)) / n
    b = 2 * sum((x - mean) * si for x, si in zip(codes, s)) / n
    return [mean + a * ci + b * si for ci, si in zip(c, s)]


def stitch(run_ids):
    segs = []
    for rid in run_ids:
        res = json.loads((RUNS / rid / 'collected/derived/result.json').read_bytes())
        ctx = res['context']
        seg = ctx.get('segment')
        if not seg:
            raise ValueError('Not an FFT segment: ' + rid)
        all_codes = [int(r[1]) for r in res['frames']]
        segs.append(dict(run_id=rid, index=seg['index'], segments=seg['segments'], seed=ctx['noiseseed'],
                         first=seg['fft_frames'][0],
                         bin=ctx['bin'], warm=all_codes[:ctx['warmup']], codes=res['codes'],
                         functional_pass=res['functional_pass'], invalid_frames=res['invalid_all_frames'],
                         power_core_plus_reference_w=res['power_core_plus_reference_w'],
                         source_deck=ctx['source_deck']))
    segs.sort(key=lambda s: s['index'])
    n = segs[0]['segments']
    if [s['index'] for s in segs] != list(range(n)) or len({s['source_deck'] for s in segs}) != 1 \
            or len({s['seed'] for s in segs}) != n:
        raise ValueError('Need every segment once, of one deck, each with its own seed')
    overlaps = []
    for prev, cur in zip(segs, segs[1:]):
        diff = [a - b for a, b in zip(cur['warm'], prev['codes'][-len(cur['warm']):])]
        if cur['first'] != prev['first'] + len(prev['codes']):
            raise ValueError('Segments %d and %d do not abut' % (prev['index'], cur['index']))
        overlaps.append(dict(segment=cur['index'], frames=[cur['first'] - len(diff), cur['first'] - 1],
                             max_abs_diff=max(abs(d) for d in diff), differing=sum(1 for d in diff if d), diff=diff))
    codes = [c for s in segs for c in s['codes']]
    if len(codes) != 1024:
        raise ValueError('Expected 1024 stitched codes')
    fit = sine_fit(codes, segs[0]['bin'])
    per = []
    for s in segs:
        m = len(s['codes'])
        part = slice(s['first'], s['first'] + m)
        err = [c - f for c, f in zip(codes[part], fit[part])]
        per.append(dict(index=s['index'], run_id=s['run_id'], seed=s['seed'], functional_pass=s['functional_pass'],
                        invalid_frames=s['invalid_frames'], power_core_plus_reference_w=s['power_core_plus_reference_w'],
                        rms_error_vs_record_sine_lsb=math.sqrt(sum(e * e for e in err) / m),
                        max_abs_error_vs_record_sine_lsb=max(abs(e) for e in err)))
    return dict(source_deck=segs[0]['source_deck'], segments=per, overlaps=overlaps,
                stitching_sound=all(o['max_abs_diff'] <= 1 for o in overlaps),
                functional_pass=all(s['functional_pass'] for s in segs), spectrum=spectrum(codes, segs[0]['bin']),
                codes=codes, method=__doc__.strip(),
                limitations=['Independent noise seed per segment: noise below about 140 kHz is not continuous across '
                             'segment boundaries', 'Single noise seed per segment; noise bandwidth convergence not established'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_ids', nargs='+')
    ap.add_argument('--output')
    a = ap.parse_args()
    data = stitch(a.run_ids)
    text = json.dumps(data, indent=1) + '\n'
    if a.output:
        (ROOT / a.output).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.output).write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps(dict(sndr_db=data['spectrum']['sndr_db'], enob_bits=data['spectrum']['enob_bits'],
                          stitching_sound=data['stitching_sound'], functional_pass=data['functional_pass']), indent=1))
