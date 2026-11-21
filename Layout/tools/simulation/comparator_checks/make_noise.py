"""Comparator input-referred noise fixture: the schematic MC fixture (tb/blocks/comparator/test.scs)
with nominal models instead of local MC, a noiseless stepped-input VA instead of the offset search,
and Spectre transient noise. Optionally the comparator is replaced by a native RC extraction.

Usage: make_noise.py PHYSICAL_ID CORNER FMAX_GHZ [--schematic] [--seed N]
Run identity: comp-v8-nz-<corner>-<rc|sch>-f<FMAX_GHZ>[-s<seed>]
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
LEVELS, PER_LEVEL, STEP_V, PERIOD = 9, 128, 0.0004, 5e-9
LSB_V, BUDGET_LSB = 0.9 * 2 / 256, 0.18


def sha(data):
    return hashlib.sha256(data).hexdigest()


def swap(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Fixture changed: ' + old[:70])
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('physical_id')
    ap.add_argument('corner', choices=['tt', 'ssc', 'ssh', 'ffc', 'ffh'])
    ap.add_argument('fmax_ghz', type=int)
    ap.add_argument('--schematic', action='store_true')
    ap.add_argument('--seed', type=int, default=301)
    ap.add_argument('--revision', default='', help='Identity suffix, e.g. b')
    a = ap.parse_args()
    corner = json.loads((ROOT / 'specs/corners.json').read_text(encoding='utf-8'))[a.corner]
    rid = 'comp-v8-nz-%s-%s-f%d%s%s' % (a.corner, 'sch' if a.schematic else 'rc', a.fmax_ghz,
                                         '' if a.seed == 301 else '-s%d' % a.seed,
                                         '-' + a.revision if a.revision else '')
    dest = ROOT / 'work/layout' / rid
    if dest.exists():
        raise ValueError('Identity already prepared: ' + rid)
    remote = evidence(a.physical_id)
    manifest = json.loads(pull(remote + '/manifest.json'))
    if manifest['case'] != 'comparator' or manifest['checks']['lvs']['verdict'] != 'CORRECT':
        raise ValueError('Need comparator evidence with LVS CORRECT')
    blobs = {'library_include.scs': (ROOT / 'tb/common/platform/library_include.scs').read_bytes(),
             'comp_noise.va': (HERE / 'comp_noise.va').read_bytes(),
             'noise_reduce.py': (HERE / 'noise_reduce.py').read_bytes()}
    deck = (ROOT / 'tb/blocks/comparator/test.scs').read_bytes().decode()
    vdd = '%g' % corner['vdd_v']
    deck = swap(deck, 'section=TTGlobalCorner_LocalMC_MOS_MOSCAP', 'section=%smacro_mos_moscap' % corner['mos'].lower())
    deck = swap(deck, 'section=TTGlobalCorner_LocalMC_MOM', 'section=tt_mom')
    deck = swap(deck, 'temp=27 tnom=27', 'temp=%d tnom=27' % corner['temperature_c'])
    deck = swap(deck, 'VVDD (SUP 0) vsource dc=0.9', 'VVDD (SUP 0) vsource dc=' + vdd)
    deck = swap(deck, 'VCLOCK (CLK 0) vsource type=pulse val0=0 val1=0.9 ', 'VCLOCK (CLK 0) vsource type=pulse val0=0 val1=%s ' % vdd)
    deck = swap(deck, 'XSEARCH (VINP VINN OP ON PR NR CLK SUP 0) sar8_mc_comp_search',
                'XNOISE (VINP VINN PR NR CLK SUP 0) sar8_comp_noise levels=%d per_level=%d step_v=%r'
                % (LEVELS, PER_LEVEL, STEP_V))
    deck = swap(deck, 'ahdl_include "comp_search.va"', 'ahdl_include "comp_noise.va"')
    stop = LEVELS * PER_LEVEL * PERIOD + 2e-9
    tran = ('comp_noise tran stop=%.6g maxstep=10p errpreset=moderate noisefmin=100k noisefmax=%dG '
            'noiseseed=%d noisescale=1 strobeperiod=100p strobeoutput=strobeonly' % (stop, a.fmax_ghz, a.seed))
    # Decisions come from the CMPNZ strobes in spectre.out; the waveform is only a coarse
    # record, so strobe-only output keeps it far below the output cap.
    deck, n = re.subn(r'(?ms)^mc montecarlo [^\r\n]*\{\s*^comp_tran tran [^\r\n]*\s*^\}', tran, deck)
    if n != 1:
        raise ValueError('Expected one montecarlo block')
    deck, n = re.subn(r'(?m)^save OP ON PR NR CLK VINP VINN XCMP\.X XCMP\.Y XCMP\.TAIL', 'save PR NR CLK VINP VINN', deck)
    if n != 1:
        raise ValueError('Expected one save statement')
    if not a.schematic:
        expected = {'extracted.scs': manifest['checks']['pex']['sha256'], **manifest['checks']['pex']['companion_sha256']}
        for name, digest in expected.items():
            blob = pull(remote + '/pex/' + name)
            if sha(blob) != digest:
                raise ValueError('Extraction bytes changed: ' + name)
            blobs[name] = blob
        joined = re.sub(r'\\\s*\n\s*', ' ', blobs['extracted.scs'].decode())
        pins = re.search(r'(?mi)^subckt\s+' + re.escape(manifest['top']) + r'\s*\(([^)]+)\)', joined)[1].split()
        if sorted(pins) != sorted(PORTS):
            raise ValueError('PEX interface mismatch')
        renamed, count = re.subn(r'(?m)^(subckt|ends)\s+' + re.escape(manifest['top']) + r'\b',
                                 r'\1 comparator_extracted', blobs['extracted.scs'].decode())
        if count != 2:
            raise ValueError('Unexpected extracted definition count')
        blobs['extracted.scs'] = renamed.encode()
        blobs['comparator_pex.scs'] = ('simulator lang=spectre\ninclude "extracted.scs"\n'
                                       'subckt sar_strongarm_t28 (' + ' '.join(PORTS) + ')\n'
                                       'XPEX (' + ' '.join(pins) + ') comparator_extracted\n'
                                       'ends sar_strongarm_t28\n').encode()
        deck, n = re.subn(r'(?ms)^subckt sar_strongarm_t28 .*?^ends sar_strongarm_t28(\r?\n)',
                          r'include "comparator_pex.scs"\1', deck)
        if n != 1:
            raise ValueError('Expected one inline comparator definition')
    blobs['test.scs'] = deck.encode()
    condition = '%s %gV %dC' % (corner['mos'], corner['vdd_v'], corner['temperature_c'])
    scope = ('%s comparator input-referred noise, %s; transient noise %d GHz, noise_worst model section, '
             'MOM sections TT; receiver loads of the MC fixture; ideal noiseless input and clock sources; '
             'nominal devices (no mismatch)' % (condition, 'schematic' if a.schematic else
                                                 'RC extraction ' + a.physical_id, a.fmax_ghz))
    context = dict(run_id=rid, family='comp_noise', corner=dict(corner, name=a.corner),
                   comparator='schematic' if a.schematic else 'native RC extraction',
                   physical_evidence=a.physical_id, gds_sha256=manifest['gds']['sha256'],
                   interconnect_rc=manifest.get('interconnect_rc'),
                   noise_fixture=dict(levels=LEVELS, per_level=PER_LEVEL, step_v=STEP_V, period_s=PERIOD,
                                      report_s=3.775e-9, cm_v=0.45, noisefmin_hz=1e5, noisefmax_hz=a.fmax_ghz * 1e9,
                                      noiseseed=a.seed, lsb_v=LSB_V, budget_lsb=BUDGET_LSB),
                   base_fixture='tb/blocks/comparator/test.scs', scope=scope)
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
    dest.mkdir(parents=True)
    for name, data in blobs.items():
        (dest / name).write_bytes(data)
    recipe = dict(schema_version=1, run_id=rid, design_id='sar_strongarm_t28_layout_noise', entry='test.scs',
                  analyzer='noise_reduce.py',
                  inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(d))
                          for n, d in blobs.items()],
                  resources=dict(threads=4, simulation_rss_mib=2048, simulation_virtual_mib=8192, analysis_rss_mib=256,
                                 analysis_virtual_mib=1024, max_output_mib=1024, simulation_wall_seconds=21600,
                                 analysis_wall_seconds=600, queue_timeout_seconds=86400),
                  spectre_args=['+preset=mx', '+mt=4', '-preset_override', '+lqtimeout', '60'],
                  summary_signals=['pr', 'nr', 'clk', 'vinp', 'vinn'], expected_stop_s=stop,
                  qualification_scope=scope, test_conditions=context)
    (dest / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(rid)


if __name__ == '__main__':
    main()
