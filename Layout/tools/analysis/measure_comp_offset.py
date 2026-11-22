"""Trip point of the comparator binary search (comp_search.va CMPMC records); Python 2.7 on the host.

Row fields: cycle, probe, polarity, valid, lower, upper, raw delay, receiver delay, reset minimum, guard_bad,
unresolved, time. Cycles 0 and 1 are the +/- range guards; cycles 2 .. steps+1 bisect; the offset is the midpoint
after the last bisection step. The later cycles probe the offset at small steps for a consistency check.
"""
from __future__ import print_function
import argparse
import json
import re


def analyze(root, out):
    with open(root + '/inputs/context.json') as stream:
        ctx = json.load(stream)
    rows = []
    with open(root + '/spectre.out') as stream:
        for line in stream:
            m = re.search(r'CMPMC,([^\r\n]+)', line)
            if m:
                rows.append([float(x) for x in m.group(1).split(',')])
    steps = ctx['steps']
    last = [r for r in rows if int(r[0]) == steps + 1]
    if len(last) != 1:
        raise ValueError('Search did not complete')
    lower, upper = last[0][4], last[0][5]
    checks = [dict(cycle=int(r[0]), probe_v=r[1], polarity=int(r[2])) for r in rows if int(r[0]) > steps + 1]
    offset = (lower + upper) / 2
    consistent = all((c['polarity'] == 1) == (c['probe_v'] > offset) for c in checks if c['polarity'] != 0)
    delays = [r[6] for r in rows if r[6] > 0]
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], variant=ctx['offset_fixture']['variant'],
                  offset_v=offset, bracket_v=[lower, upper], resolution_v=upper - lower,
                  guard_bad=int(last[0][9]), unresolved=int(last[0][10]), checks=checks, checks_consistent=consistent,
                  raw_delay_s=dict(min=min(delays), max=max(delays)) if delays else None, cycles=len(rows),
                  fixture=ctx['offset_fixture'])
    with open(out + '/result.json', 'w') as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    analyze(a.source_run_dir or a.run_dir, a.output_dir)
