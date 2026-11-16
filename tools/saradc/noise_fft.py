"""Prepare current physical SAR continuous noisy FFT and its observer preflight."""
import argparse
import hashlib
import json
from pathlib import Path
from . import views
from .__main__ import read

ROOT = Path(__file__).resolve().parents[2]


def prepare(run_id, pilot=False):
    from .__main__ import engine
    engine().valid_id(run_id)
    frames, warmup, count = (8, 0, 8) if pilot else (1032, 8, 1024)
    stop = 59e-9+frames*100e-9
    blobs = views.build('current', ROOT, {})
    adopted = read('results/design/reset_data_or_adoption_20261115.json')['source_sha256']
    assert all(hashlib.sha256(blobs[k]).hexdigest() == h for k, h in adopted.items())
    blobs['tb.scs'] = (ROOT/'tb/top/fft/tb.scs').read_bytes()
    blobs['library_include.scs'] = (ROOT/'tb/common/platform/library_include.scs').read_bytes()
    for dest, source in [('sar8_fft_monitor.va','tb/common/veriloga/sar8_fft_monitor.va'),
                         ('noise_fft_reduce.py','tools/saradc/measure/noise_fft_reduce.py'),
                         ('dynamic_reduce.py','tools/saradc/measure/dynamic_reduce.py'),
                         ('native_stream.py','tools/saradc/measure/native_stream.py')]:
        blobs[dest] = (ROOT/source).read_bytes()
    test = (ROOT/'tb/top/fft/test.scs').read_text(encoding='utf-8')
    test = test.replace(' XDUT.XREF.CAP_CLK', '').replace('r4_perf_monitor','sar8_fft_monitor')
    old = 'tran_perf tran stop=103259n maxstep=10p errpreset=moderate lteratio=10 strobeperiod=10p strobeoutput=strobeonly'
    assert test.count(old) == 1
    low = 2e6 if pilot else 1e4
    test = test.replace(old, 'tran_perf tran stop=%.12g maxstep=10p errpreset=moderate lteratio=10 strobeperiod=10p strobeoutput=strobeonly noisefmin=%.12g noisefmax=2G noiseseed=101 noisescale=1 saveclock=1800 savefile="tran_noise.state"' % (stop, low))
    assert 'CAP_CLK' not in test
    blobs['test.scs'] = test.encode()
    context = read('tb/top/fft/context.json')
    context.update(run_id=run_id, label='current-resetor', frames=frames, warmup=warmup,
                   samples=count, stop_s=stop, period_s=1e-7, pilot=pilot,
                   noise=True, noisefmin_hz=low, noisefmax_hz=2e9, noiseseed=101, noisescale=1,
                   noise_model_section='noise_worst', noise_scope='All enabled device models and four external 50 ohm resistors; ideal sources noiseless',
                   noise_bandwidth_convergence='not_established',
                   observer_capture_clock='absent; legacy field is zero',
                   design_id=read('specs/arch.json')['design_id'],
                   dut_sha256=hashlib.sha256(blobs['dut.scs']).hexdigest(),
                   source_hashes={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()},
                   checkpoint_scope='Periodic save enabled; no recovery or stitched output authorized by this recipe; noisy recovery equivalence unverified')
    context.pop('solver_reference', None)
    blobs['context.json'] = (json.dumps(context,indent=2)+'\n').encode()
    dest = ROOT/'work/decks'/run_id
    recipe = dict(schema_version=1, run_id=run_id, design_id=context['design_id'], entry='test.scs',
                  analyzer='noise_fft_reduce.py', expected_stop_s=stop,
                  inputs=[dict(name=k, source=(dest/k).relative_to(ROOT).as_posix(), sha256=hashlib.sha256(v).hexdigest()) for k,v in blobs.items()],
                  resources=dict(threads=4, simulation_rss_mib=1024, simulation_virtual_mib=8192,
                                 analysis_rss_mib=256, analysis_virtual_mib=1024,
                                 max_output_mib=1024 if pilot else 16384,
                                 simulation_wall_seconds=7200 if pilot else 345600,
                                 analysis_wall_seconds=600 if pilot else 14400, queue_timeout_seconds=86400),
                  spectre_args=['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],
                  summary_signals=context['signals'], test_conditions=context,
                  qualification_scope='Observer/protocol preflight only; no FFT/noise qualification' if pilot else 'Continuous current-design TT 1024-point transient-noise FFT; single seed and unconverged noise bandwidth; no MC/PEX/full-terminal qualification')
    blobs['recipe.yaml'] = (json.dumps(recipe,indent=2)+'\n').encode()
    for name, data in blobs.items():
        path = dest/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Frozen input collision: '+str(path))
    for name, data in blobs.items():
        path = dest/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    return (dest/'recipe.yaml').relative_to(ROOT).as_posix()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-id',required=True)
    p.add_argument('--pilot',action='store_true')
    a = p.parse_args()
    print(prepare(a.run_id,a.pilot))
