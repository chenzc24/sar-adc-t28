from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts/sar8_campaign'))
import fft_report as shared
src=R/'output/managed_execution/runs/sar8noise-b-tt-fft1024-g2-s101-v1/collected/derived/result.json'
z=json.loads(src.read_text());assert z['functional_pass'] and z['native_decode_crosscheck']
out=R/'verification/sar8_noise/fft_final'
adapter=dict(dynamic_frames=[dict(zip(shared.FIELDS,row)) for row in z['frames'][8:]],dynamic=z['spectrum'],source_run_id=z['context']['run_id'],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
a=out/'b_noise_panel_input.json';a.write_text(json.dumps(adapter,indent=2))
p=R/'scripts/sar8_r4_performance/toolbox_panel.py'
code=p.read_text(encoding='utf-8').replace('no transient noise / mismatch / PVT sweep','transient noise: 2 GHz / 10 kHz / seed101; no mismatch / PEX').replace('No thermal-noise or jitter measurement: deterministic transient only.','Transient device noise enabled; residual also contains quantization and distortion. Single seed; bandwidth convergence unverified; no external clock jitter.')
scope={'__file__':str(p),'__name__':'noise_panel_renderer'}
exec(compile(code,str(p),'exec'),scope)
scope['polar']=shared.polar_readable
scope['main'](a,out/'b_noise_toolbox_panel.png',out/'b_noise_toolbox_panel.json',label='B SAR ADC + transient noise',warning='CMI terminal warnings remain; single seed, no bandwidth-convergence signoff.')
r=json.loads((out/'b_noise_toolbox_panel.json').read_text())
assert abs(r['spectrum']['sndr_dbc']-z['spectrum']['sndr_db'])<1e-8
assert abs(r['spectrum']['sfdr_dbc']-z['spectrum']['sfdr_db'])<1e-8
