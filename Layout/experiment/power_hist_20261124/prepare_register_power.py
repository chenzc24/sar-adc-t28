"""Build 10 MS/s register replays for the nine previously measured Stage 6 operating cases."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from statistics import median


PERIOD_NS = 100
ORIGIN_NS = 59
CASES = ('verify', 'extreme', 'carry')
VDDIO = {'tt': 1.8, 'ssc': 1.62, 'ffh': 1.98}
PAD_RUN = 'sar8-handoff-ffh-board-ss8-b'


def checked_inputs(run):
    recipe = json.loads((run / 'recipe.json').read_bytes())
    files = {row['name']: row['sha256'] for row in recipe['files']}

    def get(name):
        data = (run / 'inputs' / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != files[name]:
            raise ValueError('Frozen input changed: ' + name)
        return data

    return get


def frames_for(runs, corner, case):
    revision = 'b' if corner == 'tt' and case != 'extreme' else 'a'
    run = runs / ('sar8-s6f-%s-%s-%s' % (corner, case, revision))
    raw = (run / 'collected/derived/result.json').read_bytes()
    receipt = json.loads((run / 'collected/collection_receipt.json').read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if not any(row['name'] == 'derived/result.json' and row['sha256'] == digest for row in receipt['files']):
        raise ValueError('Core result receipt differs')
    result = json.loads(raw)
    if not result['all_pass'] or len(result['frames']) != 8:
        raise ValueError('Incomplete functional source')
    return run, result['frames'], digest


def schedule(corner, runs):
    swings = [[(0., 0)] for _ in range(8)]
    plan = []
    previous = 0
    frame_number = 0
    for case in CASES:
        run, frames, digest = frames_for(runs, corner, case)
        scored = frames[1:]
        plan.append(dict(case=case, parent=run.name, parent_result_sha256=digest,
                         codes=[f['code98'] for f in scored],
                         measure_begin_ns=ORIGIN_NS + (frame_number+3)*PERIOD_NS))
        # Prime Q with the previous word of the repeating seven-code sequence.
        # Each measured cycle includes its Q capture and the next input word.
        for f in [frames[0], frames[-1]] + scored + [scored[0]]:
            if f['code90'] != f['code98'] or len(f['writes']) != 8:
                raise ValueError('Core word is unstable or missing a write')
            opened = next(edge['ns'] for edge in f['track'] if edge['up'])
            early = [t for t in f['public'] if .5 < t < 5.]
            clear = median(early) if early else opened + .12
            if not 1.25 <= clear <= 2.5:
                raise ValueError('Unexpected Core reset phase')
            start = ORIGIN_NS + frame_number * PERIOD_NS
            word = f['code98']
            for bit, swings_and_bit in enumerate(swings):
                if previous & 1 << bit:
                    swings_and_bit.append((start + clear, 0))
                if word & 1 << bit:
                    write = f['writes'][7-bit]['ns']
                    hits = [t for t in f['public'] if -.02 <= t-write <= .45]
                    if len(hits) != 1:
                        raise ValueError('Expected one observed threshold crossing for each high bit')
                    swings_and_bit.append((start + hits[0], 1))
            previous = word
            frame_number += 1
    return plan, swings, ORIGIN_NS + frame_number*PERIOD_NS + 5


def pwl(bit, events, vdd, slew_ns):
    prev = 0
    points = ['0 0']
    for t, value in events[1:]:
        points.append('%.8fn %.6g %.8fn %.6g' % (t-slew_ns/2, prev*vdd, t+slew_ns/2, value*vdd))
        prev = value
    return 'VBIT%d (D%d 0) vsource type=pwl wave=[%s]' % (bit, bit, ' '.join(points))


def prepare(corner, stage6, output, revision='a'):
    stage6_runs = stage6 / 'work/output/managed_execution/runs'
    pad_run = output / 'work/output/managed_execution/runs' / PAD_RUN
    pad_inputs = checked_inputs(pad_run)
    parent, _, _ = frames_for(stage6_runs, corner, 'verify')
    core_inputs = checked_inputs(parent)
    context = json.loads(core_inputs('context.json'))
    vdd, io = context['vdd_v'], VDDIO[corner]
    expected_vdd = {'tt': .90, 'ssc': .81, 'ffh': .99}[corner]
    if vdd != expected_vdd or context['period_s'] != 100e-9:
        raise ValueError('Unexpected replay supply or timing')
    prefix = core_inputs('test.scs').decode('ascii').split('include "dut.scs"', 1)[0].rstrip()
    source = pad_inputs('test.scs').decode('ascii')
    peripheral = source[source.index('simulatorOptions options'):source.index('VSAMPLE (SAMPLE_SRC')].rstrip()
    peripheral, n = re.subn(r'\btemp=125\b', 'temp=%d' % context['temperature_c'], peripheral)
    peripheral, m = re.subn(r'(VVDDIO_SRC \(VDDIO_BRD 0\) vsource dc=)1\.98\b', r'\g<1>'+str(io), peripheral)
    if n != 1 or m != 1:
        raise ValueError('Unexpected output deck temperature or VDDIO source')
    cases, waveforms, stop = schedule(corner, stage6_runs)
    slew_ns = .10
    clock = 'VSAMPLE (SAMPLE_SRC 0) vsource type=pulse val0=0 val1=%g delay=60n rise=100p fall=100p width=44.9n period=100n' % io
    trace = ['XOUT.DVDD_J', 'XOUT.DVDD_REG', 'VSS_CHIP', 'XOUT.CK_REG'] + ['XOUT.Q%d' % bit for bit in range(8)]
    grid = 'tran_short tran stop=%dn maxstep=10p errpreset=moderate lteratio=10 strobeperiod=5p strobeoutput=strobeonly' % stop
    netlist = '\n'.join([prefix, peripheral, clock] + [pwl(i, w, vdd, slew_ns) for i, w in enumerate(waveforms)]
                        + [grid, 'save '+ ' '.join(trace), ''])
    path_data = pad_inputs('sar8_output_path.scs')
    r = re.search(rb'(?m)^RDVDD_REG \(DVDD_J DVDD_REG\) resistor r=(\S+)$', path_data)
    if not r or float(r[1]) != 16.1:
        raise ValueError('Register current must cross the expected sole supply resistor')
    if not re.fullmatch(r'[a-z][a-z0-9]{0,7}', revision):
        raise ValueError('Invalid replay revision')
    rid = 'sar8-handoff-%s-regbranch-pwr-%s' % (corner, revision)
    plan = dict(run=rid, corner=corner, vdd_v=vdd, vddio_v=io, temperature_c=context['temperature_c'],
                period_ns=PERIOD_NS, stop_ns=stop, output_fixture=PAD_RUN, board_load_pf=15.,
                register_feed_ohm=float(r[1]), prescribed_slew_ps=slew_ns*1000,
                stimulus='Native Stage 6 codes and observed rising threshold timing. Grouped measured reset timing and prescribed edge slew. Each case is primed to repeat its seven scored words.', cases=cases)
    blobs = {'test.scs': netlist.encode('ascii'), 'sar8_output_path.scs': path_data,
             'library_include.scs': core_inputs('library_include.scs'),
             'replay.json': (json.dumps(plan, indent=2)+'\n').encode('ascii'),
             'measure_register_power.py': Path(__file__).with_name('measure_register_power.py').read_bytes()}
    for name in ('output_register.scs', 'native_stream.py'):
        blobs[name] = pad_inputs(name)
    folder = output / 'work/decks' / rid
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name, data in blobs.items():
        target = folder / name
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Existing replay input differs: ' + name)
        target.write_bytes(data)
        files.append(dict(name=name,source=target.relative_to(output).as_posix(),sha256=hashlib.sha256(data).hexdigest()))
    board_recipe = json.loads((pad_run / 'recipe.json').read_bytes())
    resources = dict(board_recipe['resources'], max_output_mib=1536, analysis_wall_seconds=1800)
    spec = dict(run_id=rid, design_id='sar8_register_pin_power_'+corner, entry='test.scs',
                analyzer='measure_register_power.py',inputs=files,resources=resources,
                spectre_args=board_recipe['spectre_args'],summary_signals=['xout.ck_reg','xout.dvdd_reg'],
                expected_stop_s=stop*1e-9,test_conditions=plan,
                qualification_scope='Register-branch supply power with the extracted output chain and matched Stage 6 code activity')
    path = folder / 'recipe.json'
    path.write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    return path


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('corner', choices=VDDIO)
    cli.add_argument('stage6', type=Path)
    cli.add_argument('runner', type=Path)
    cli.add_argument('--revision', default='a')
    args = cli.parse_args()
    print(prepare(args.corner, args.stage6.resolve(), args.runner.resolve(), args.revision))
