"""Post-layout comparator mismatch MC: the schematic 200-seed fixture (tb/blocks/comparator) unchanged
except that the inline sar_strongarm_t28 is replaced by a native RC extraction.

Usage: make_mc.py PHYSICAL_ID SEED [SEED ...] [--schematic]
Run identities: comp-v8-mc-s<seed> (extraction) or comp-v8-mcsch-s<seed> (schematic packaging check).
The same seed does not draw the same per-device values in the two netlists (instance names differ),
so the comparison is between distributions, not seed pairs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from Layout.project import evidence  # noqa: E402
from Layout.tools.simulation.prepare_full_sim import pull  # noqa: E402

HERE = Path(__file__).resolve().parent
PORTS = ['CLK', 'OUTN', 'OUTP', 'VDD', 'VINN', 'VINP', 'VSS']
BASE_RUN = 'sar8mc-comp-s4101-v2'
SOURCES = {'test.scs': 'tb/blocks/comparator/test.scs', 'context.json': 'tb/blocks/comparator/context.json',
           'native_stream.py': 'tools/saradc/measure/native_stream.py',
           'library_include.scs': 'tb/common/platform/library_include.scs',
           'comp_search.va': 'tb/common/veriloga/comp_search.va',
           'native_summary.py': 'tools/saradc/managed/native_summary.py'}
# Input-pair fingers of the extraction (gates on VINP/VINN), for the analyzer's mismatch evidence.
INPUT_DEVICES = r'XX(?:3|5|12|14)\\?/M0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def swap(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Fixture changed: ' + old[:60])
    return text.replace(old, new)


def analyzer():
    text = (ROOT / 'tools/saradc/measure/block_reduce.py').read_text(encoding='utf-8')
    text = swap(text, "            elif 'MNIN' in name.upper():",
                "            elif 'MNIN' in name.upper() or re.search(INPUT_DEVICES, name):")
    text = swap(text, 'from native_stream import samples\n',
                'from native_stream import samples\nINPUT_DEVICES = %r\n' % INPUT_DEVICES)
    return text.encode()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('physical_id')
    ap.add_argument('seeds', nargs='+', type=int)
    ap.add_argument('--schematic', action='store_true')
    a = ap.parse_args()
    import yaml
    reg = yaml.safe_load((ROOT / 'work/state/runs' / (BASE_RUN + '.yaml')).read_text(encoding='utf-8'))['recipe']
    want = {f['name']: f['sha256'] for f in reg['files']}
    blobs0 = {n: (ROOT / p).read_bytes() for n, p in SOURCES.items()}
    reference = (ROOT / 'tools/saradc/measure/block_reduce.py').read_bytes()
    for n, b in list(blobs0.items()) + [('block_reduce.py', reference)]:
        if sha(b) != want[n]:
            raise ValueError('Schematic MC input changed since the 200-seed baseline: ' + n)
    remote = evidence(a.physical_id)
    manifest = json.loads(pull(remote + '/manifest.json'))
    if manifest['case'] != 'comparator' or manifest['checks']['lvs']['verdict'] != 'CORRECT':
        raise ValueError('Need comparator evidence with LVS CORRECT')
    pex = {}
    if not a.schematic:
        expected = {'extracted.scs': manifest['checks']['pex']['sha256'], **manifest['checks']['pex']['companion_sha256']}
        for name, digest in expected.items():
            blob = pull(remote + '/pex/' + name)
            if sha(blob) != digest:
                raise ValueError('Extraction bytes changed: ' + name)
            pex[name] = blob
        joined = re.sub(r'\\\s*\n\s*', ' ', pex['extracted.scs'].decode())
        pins = re.search(r'(?mi)^subckt\s+' + re.escape(manifest['top']) + r'\s*\(([^)]+)\)', joined)[1].split()
        if sorted(pins) != sorted(PORTS):
            raise ValueError('PEX interface mismatch')
        renamed, count = re.subn(r'(?m)^(subckt|ends)\s+' + re.escape(manifest['top']) + r'\b',
                                 r'\1 comparator_extracted', pex['extracted.scs'].decode())
        if count != 2:
            raise ValueError('Unexpected extracted definition count')
        pex['extracted.scs'] = renamed.encode()
        pex['comparator_pex.scs'] = ('simulator lang=spectre\ninclude "extracted.scs"\n'
                                     'subckt sar_strongarm_t28 (' + ' '.join(PORTS) + ')\n'
                                     'XPEX (' + ' '.join(pins) + ') comparator_extracted\n'
                                     'ends sar_strongarm_t28\n').encode()
        pex['block_reduce.py'] = analyzer()
    for seed in a.seeds:
        rid = 'comp-v8-%s-s%d' % ('mcsch' if a.schematic else 'mc', seed)
        dest = ROOT / 'work/layout' / rid
        if dest.exists():
            raise ValueError('Identity already prepared: ' + rid)
        # The managed runner adds its own native_summary.py (hash-checked above).
        blobs = {n: b for n, b in blobs0.items() if n != 'native_summary.py'}
        blobs['block_reduce.py'] = reference
        deck = blobs['test.scs'].decode()
        deck = swap(deck, 'seed=4101 ', 'seed=%d ' % seed)
        signals = list(reg['summary_signals'])
        if not a.schematic:
            deck, count = re.subn(r'(?ms)^subckt sar_strongarm_t28 .*?^ends sar_strongarm_t28(\r?\n)',
                                  r'include "comparator_pex.scs"\1', deck)
            if count != 1:
                raise ValueError('Expected one inline comparator definition')
            # The extraction has no schematic internal-node names; the analyzer does not read them.
            deck = swap(deck, 'save OP ON PR NR CLK VINP VINN XCMP.X XCMP.Y XCMP.TAIL', 'save OP ON PR NR CLK VINP VINN')
            signals = [s for s in signals if not s.startswith('xcmp.')]
            blobs.update(pex)
        blobs['test.scs'] = deck.encode()
        context = json.loads(blobs['context.json'])
        context.update(run_id=rid, seed=seed, baseline_fixture=BASE_RUN,
                       comparator='schematic (packaging check)' if a.schematic else 'native RC extraction',
                       physical_evidence=a.physical_id, gds_sha256=manifest['gds']['sha256'],
                       interconnect_rc=manifest.get('interconnect_rc'),
                       extracted_original_sha256=None if a.schematic else
                       {'extracted.scs': manifest['checks']['pex']['sha256'], **manifest['checks']['pex']['companion_sha256']},
                       input_device_pattern=None if a.schematic else INPUT_DEVICES)
        scope = ('TT 0.9V 27C comparator mismatch MC seed %d, schematic 200-seed fixture with the comparator %s; '
                 'distribution comparison only (draws are not paired across netlists); no noise or PVT'
                 % (seed, 'schematic (packaging check)' if a.schematic else 'RC extraction ' + a.physical_id))
        context['scope'] = scope
        blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
        dest.mkdir(parents=True)
        for name, data in blobs.items():
            (dest / name).write_bytes(data)
        recipe = dict(schema_version=1, run_id=rid, design_id='sar_strongarm_t28_layout_mc', entry='test.scs',
                      analyzer='block_reduce.py',
                      inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(d))
                              for n, d in blobs.items()],
                      resources=reg['resources'], spectre_args=reg['spectre_args'], summary_signals=signals,
                      expected_stop_s=reg['expected_stop_s'], qualification_scope=scope, test_conditions=context)
        (dest / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(rid)


if __name__ == '__main__':
    main()
