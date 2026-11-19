"""Shared B specification, generated VA defaults and model cross-validation."""
import bisect
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import shutil

from design.behav.python.sar_adc import AnalogConfig,SarAdcModel

ROOT=Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generated():
    a=load('specs/arch.json');b=a['behavior_models'];t=b['default_timing']
    clock=a['external_clock'];cdac=a['blocks']['cdac'];boot=a['blocks']['bootstrap']
    comp=a['blocks']['comparator'];corners=load(a['verification']['corners'])
    header='// Generated from specs/arch.json by python -m tools.saradc behav generate.\n'
    header+='`ifndef SAR8_B_DEFAULTS\n`define SAR8_B_DEFAULTS\n'
    header+=''.join('`define B_%s %.17g\n'%(key.upper(),value) for key,value in t.items())
    header+='`endif\n'
    lsb=a['input']['lsb_v'];budget=a['error_budget'];ref=a['reference']
    gain=a['targets']['gain_error'];galloc=budget['gain_error_allocation'];lin=budget['layout_systematic_linearity_lsb']
    noise={k:budget[k]*lsb for k in ['sampling_noise_rms_lsb','comparator_noise_rms_lsb','reference_noise_rms_lsb','unmodeled_distortion_rms_lsb']}
    amplitude=ref['high_v']*10**(a['targets']['test_level_dbfs']/20)
    jitter=2*math.pi*budget['jitter_frequency_hz']*budget['jitter_rms_s']*amplitude/math.sqrt(2)
    quant=lsb/math.sqrt(12)
    rss=math.sqrt(quant**2+jitter**2+sum(x*x for x in noise.values()))
    projected=20*math.log10(amplitude/math.sqrt(2)/rss)
    timing_text = ('The SAR uses input-qualified native delay cells. The analog and boosted circuits remain transistor-level.'
                   if 'active_delay_cells' in a['blocks']['timing_reference'] else
                   'The SAR RC, clear transistor, and analog and boosted circuits remain transistor-level.')
    lines=['# SAR8 Design Specification','',
      'This page is generated from [specs/arch.json](../specs/arch.json). The current electrical implementation is `'+a['design_id']+'`. The behavioral models approximate the B algorithm and protocol. Use native measurements for the minimal reference and data-reset OR path delays. [Adoption and qualification record](../'+a['qualification']['adoption_record']+')','',
      '## Architecture and External Interface','',
      '- An 8-bit, 10 MS/s, fully differential asynchronous SAR with a flat binary CDAC. Each side connects 255 binary-weighted unit capacitors and one unit dummy to its top plate without a bridge capacitor.',
      '- Top-level port order is `'+' '.join(a['interface']['port_order'])+'`.',
      '- Digital outputs are D0..D7. SAMPLE high samples and resets the SAR. Its falling edge ends sampling and starts the autonomous eight-bit sequence. The interface has no external bit clock, BUSY, VALID, or EOC pin.',
      '- The code changes bit by bit during conversion. Read it after conversion and before the next sample. Positive differential voltage is VINP−VINN.','',
      '| Item | Definition |','| --- | --- |',
      '| Core supply | %g V nominal, %g–%g V verification range |'%(corners['tt']['vdd_v'],*a['supply_v']),
      '| References | VREFN=%g V and VREFP=%g V, independent of the core supply |'%(ref['low_v'],ref['high_v']),
      '| Input | %g V nominal common mode, %g..%g V differential, %g..%g V single-ended. Full common-mode range is unqualified. |'%(a['input']['nominal_common_mode_v'],*a['input']['differential_range_v'],*a['input']['single_ended_nominal_range_v']),
      '| Quantization | 256 codes, LSB=%.8f mV. Ideal boundaries are −0.9+k·LSB. Use the upper code at equality. |'%(lsb*1e3),
      '| Frame timing | %g ns total, with %g ns high for sampling and %g ns low for conversion. Start with %g ns low for precharge before normal cycling. |'%tuple(clock[k]*1e9 for k in ['period_s','high_s','conversion_allocation_s','initial_low_s']),
      '| Actual stimulus | Delay=%g ns, rise/fall=%g/%g ps, width=%g ns. The first falling-edge threshold crossing is at %g ns. |'%(clock['spectre_pulse_delay_s']*1e9,clock['source_rise_s']*1e12,clock['source_fall_s']*1e12,clock['spectre_pulse_width_s']*1e9,clock['first_falling_threshold_s']*1e9),
      '| Input source | Ideal source with %g Ω series resistance per pin |'%a['input']['source_resistance_ohm_per_pin'],
      '| Reference source | Ideal source with %g Ω series resistance and %g pF bypass per rail. The fixture drives the reference directly. |'%(ref['source_resistance_ohm_per_rail'],ref['decoupling_f_per_rail']*1e12),
      '| Output load | %g fF per bit. The comparator outputs and clock use native MOM model loads in pre-layout simulation only. |'%(a['loading']['digital_output_capacitance_f_each']*1e15),'',
      '## Corners','',
      '| Condition | MOS corner | Temperature (°C) | VDD (V) |','| --- | --- | ---: | ---: |']
    lines += ['| %s | %s | %g | %g |'%(name,c['mos'],c['temperature_c'],c['vdd_v']) for name,c in corners.items() if isinstance(c,dict)]
    lines += ['',
      'Read the frozen case includes for actual MOS, MOM, and passive model sections. The MOS corner name identifies MOS conditions. [Test identities](../specs/tests.json)','',
      '## Current Transistor Implementation','',
      '- Bootstrap uses %d parallel %g µm/%g nm `%s` main switches per channel and a native MOM capacitor with multi=%d.'%(boot['main_switch_parallel_devices'],boot['main_switch_w_m_each']*1e6,boot['main_switch_l_m']*1e9,boot['main_switch_model'],boot['bootstrap_capacitor']['multi']),
      '- The CDAC uses 18 `cfmom_2t` instances. The unit geometry is nr=8, lr=2 µm, w=s=50 nm, stm=1, and spm=3, with multi from 1 to 128. The N and P dummies connect to VREFN and VREFP, respectively. The prior low-frequency AC characterization of this unit geometry gave about 4.00407 fF per unit and 1.02504 pF per 256-unit side at its specified bias and frequency. The older 6.86047 fF comparison and the 512-independent-unit mismatch results apply to their original models.',
      '- Reference switches use L=%g nm, NMOS W=%g nm, PMOS W=%g nm, and multi=%d·2^bit.'%(cdac['reference_switch_l_m']*1e9,cdac['n_switch_w_m']*1e9,cdac['p_switch_w_m']*1e9,cdac['switch_multi_lsb_first'][0]),
      '- The %d-MOS StrongARM comparator uses input pairs of W=%g µm and L=%g nm, a tail width of %g µm, and N/P regeneration widths of %g/%g nm.'%(comp['MOS_count'],comp['input_pair_w_m']*1e6,comp['input_pair_l_m']*1e9,comp['tail_w_m']*1e6,comp['regeneration_n_w_m']*1e9,comp['regeneration_p_w_m']*1e9),
      '- The digital path uses native standard cells. '+timing_text+' The reference uses CODE, a shared PRESET, and true and complementary drive. The minimal reference removes the extra DFF/MUX, per-bit reset and capture, non-overlap generator, and series gate resistors.',
      '- Native standard-cell masters are `'+'`, `'.join(a['blocks']['standard_cells']['external_masters'])+'`.','',
      '## Timing Contract','',
      'The minimal design requires eight comparisons and writes per frame. Verify reference state from actual CODE, gate control, and per-bit bottom-plate settling. The current reference path has no capture events. A new sample cancels unfinished events at the established external timing. The 60 ns conversion allocation comes from the frame. The interface exposes no timeout pin. Frozen B and its behavioral model use their own contract of eight reference updates and 16 captures.',
      'The TT behavioral intervals below are medians of native edges across ten historical B frames. The low phase sets the conversion budget. The 20 ps output smoothing and arithmetic regularization are model settings. The compare-to-write interval covers the comparator and digital receive pipeline. The high phase is 40 ns, and internal gate waveforms determine the actual Bootstrap conduction window.','',
      '| Behavioral interval | Value (ns) |','| --- | ---: |']
    for key,value in t.items():
        if key.endswith('_s'):lines.append('| `%s` | %.9f |'%(key,value*1e9))
    lines += ['',
      'The model uses TT intervals. Use native per-bit closed-loop measurements for timing qualification, including SS, FF, and mismatch. The 0.75 ns comparator probe and the same-draw extended-hold comparison with a 0.25 LSB limit are module diagnostics. Use separate evidence for full-frame deadlines and device reliability.','',
      '## Performance Targets and Error Budget','',
      'Engineering targets are ENOB ≥7 bits (SNDR ≥43.9 dB) at −1 dBFS, monotonicity with no missing codes, absolute DNL and endpoint INL ≤1 LSB, and power ≤1 mW. Consult measured results for actual conditions and coverage. [Results](../results/README.md)','',
      '| Allocation | RMS (mV) |','| --- | ---: |','| Ideal quantization | %.6f |'%(quant*1e3)]
    lines += ['| `%s` | %.6f |'%(k,v*1e3) for k,v in noise.items()]
    lines += ['| Jitter of 20 ps at 4.5 MHz | %.6f |'%(jitter*1e3),
      '', 'The allocated RSS is %.6f mV. It projects SNDR of %.6f dB and ENOB of %.6f bits. Use measured spectra for the noise of a physical run.'%(rss*1e3,projected,(projected-1.76)/6.02),
      'The CDAC settling allocation is 0.25 LSB (%.7f mV). Report fixed gain, offset, and delay separately from random-noise RSS.'%(0.25*lsb*1e3),
      '', '### Full Scale and Gain Error','',
      'Nominal full scale is ±(VREFP−VREFN)=±%g V with ideal binary weights 2^i·LSB. Define k as the sum of measured effective bit weights divided by the sum of ideal weights. Actual full scale is ±%g·k V. The code-domain gain error is GE=1/k−1, positive when codes exceed the ideal. Reference −1 dBFS to nominal full scale. Endpoint INL and DNL exclude offset and gain.'%(ref['high_v']-ref['low_v'],ref['high_v']-ref['low_v']),
      '','| Gain error | Limit |','| --- | ---: |',
      '| TT | %g%% |'%(gain['max_tt']*100),'| Any corner | %g%% |'%(gain['max_any_corner']*100),
      '| Hard limit for an unclipped −1 dBFS sine | %g%% |'%(gain['hard_limit']*100),'',
      'At TT, allocate ≤%g%% to the CDAC including planned fill, ≤%g%% to top-level TOP routing and device layout, and %g%% to margin. Measure the CDAC share from standalone bit weights for the same extracted view. Use gain-normalized extracted weights to check layout systematic linearity, with |DNL|≤%g LSB and endpoint |INL|≤%g LSB. Leave the rest of the budget for mismatch, noise, and the comparator.'%(galloc['cdac_with_planned_fill']*100,galloc['top_level_top_wiring_and_device_layout']*100,galloc['margin']*100,lin['dnl_abs_max'],lin['inl_endpoint_abs_max']),
      'Accept the measured gain against these limits. Digital gain correction of the 8-bit output would merge or drop codes. The 0.9 V core level already sets the upper reference.',
      'For short ADC tests, compute the expected code as `clip(128+floor(Vin/(LSB·k)), 0, 255)`. Use k from an independent CDAC test of the same physical view, or k=1 for the schematic. The functional check allows ±%d code with `%s`. Evaluate gain, linearity, and dynamic performance against their own limits.'%(a['targets']['integrated_code_check']['tolerance_codes'],a['targets']['integrated_code_check']['tool']),
      '', '## Calibration, Statistics, and Open Items','',
      '- The current design is uncalibrated. Comparator extremes among 200 seeds describe the offsets observed in those samples. Calibration range, step size, and weight word length are open.',
      '- The historical 0.25 LSB offset allocation is a provisional residual target after correction. The current comparator offset is reported as measured.',
      '- The Monte Carlo specification defines the 200-seed module tests and the 50-seed closed-loop tests at each of SS cold and FF cold. Closed-loop local mismatch is enabled only in the comparator and CDAC. [Sampling scope](../specs/monte_carlo.json)',
      '- The B version has one TT transient-noise seed. Bandwidth and statistical convergence are open, as are full-circuit local mismatch, PEX, full common-mode range, calibration range and accuracy, power integration convergence, and terminal-voltage reliability. [Noise comparison](../results/noise/comparison.json)',
      '- Use the terminal-voltage rule for engineering acceptance. The five-point minimal-reference D2 trial passed the comparator screen at all five corners within its measurement scope. At FF cold, SAR storage device MM64 failed the Vds duration limit. Apply the rule to the adopted design and rely on separate evidence for reliability signoff. [Terminal-voltage rule](../specs/soa_rule.yaml) · [Per-device results](../results/soa/msb_drive_d2_trial_20261115.md)','',
      '## Behavioral Views and Cross-Checks','',
      'The Python and Verilog-A models share the specification and generated defaults. The default is noiseless. Both support effective bit weights, offset, finite settling, and a stalled comparator. [Python model](../design/behav/python/sar_adc.py) · [Verilog-A model](../design/behav/veriloga/sar_adc_b.va)',
      'Compare deterministic cases individually. The models use different random streams and model noise according to their respective distributions. Use transistor-level models for physical startup charging, kickback, native PDK Monte Carlo, terminal voltages, and power.',
      'See the model guide for view hierarchy, legacy review, and commands. [Behavioral model guide](../design/behav/README.md)','']
    return {'design/behav/veriloga/b_defaults.vh':header,'docs/specification.md':'\n'.join(lines)}


def generate():
    for name,text in generated().items():
        p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')


def check_generated():
    for name,text in generated().items():
        if not (ROOT/name).is_file() or (ROOT/name).read_text(encoding='utf-8')!=text:
            raise ValueError('Run behav generate; stale file: '+name)
    a=load('specs/arch.json');manifest=load('design/manifest.json')
    if a['interface']['port_order']!=manifest['subcircuits'][manifest['top']]['ports']:
        raise ValueError('System interface differs from the physical B top')
    defaults=a['behavior_models'].get('module_defaults',{})
    declarations={
        'sampler_ron_ohm':[('sampler.va','ron')],
        'off_resistance_ohm':[('sampler.va','roff')],
        'cdac_unit_c_f':[('cdac.va','unit_c')],
        'cdac_unit_ron_ohm':[('cdac.va','unit_ron')],
        'comparator_input_c_f':[('comparator.va','input_c')],
        'behavioral_output_r_ohm':[(p,'rout') for p in ['comparator.va','sar.va','reference.va']],
        'reference_deadtime_s':[('reference.va','deadtime_s')]}
    scales={'':1,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3}
    for key,rows in declarations.items():
        if key not in defaults:continue
        for filename,param in rows:
            source=(ROOT/'design/behav/veriloga'/filename).read_text(encoding='utf-8')
            tokens=re.findall(r'parameter real '+param+r'=([0-9.eE+-]+)([fpnumk]?)\s',source)
            if not tokens or any(not math.isclose(float(n)*scales[s],defaults[key],rel_tol=1e-12,abs_tol=1e-25) for n,s in tokens):
                raise ValueError('VA default differs from the declared model specification: '+filename+' '+param)
    return {'shared_spec':'specs/arch.json','generated_defaults_match':True,'physical_ports_match':True,'electrical_defaults_match':True}


def stimuli():
    m=SarAdcModel();lsb=m.spec.lsb
    values=[(-m.spec.vref+(k+.5)*lsb,'center') for k in range(256)]
    for k in range(1,256):
        boundary=-m.spec.vref+k*lsb
        values.extend((boundary+delta*lsb,'boundary') for delta in [-1e-6,0,1e-6])
    values.extend((v,'saturation') for v in [-1.1,-.9,0,.9,1.1])
    with (ROOT/'results/fft/b_codes.csv').open(encoding='utf-8') as stream:
        values.extend((float(r['aperture_source_v']),'native_fft_aperture') for r in csv.DictReader(stream))
    return values


SCENARIOS=[
    dict(name='nominal',analog={},timing={},va=''),
    dict(name='sampling_gain_offset',analog={'gain':.999,'sampling_offset_v':.0005},timing={},va='gain=0.999 sampling_offset_v=0.0005'),
    dict(name='positive_offset',analog={'comparator_offset_v':.0017578125},timing={},va='comparator_offset_v=0.0017578125'),
    dict(name='MSB_weight_error',analog={'weight_errors':(0,0,0,0,0,0,0,.01)},timing={},va='weight_error7=0.01'),
    dict(name='finite_DAC_settling',analog={'dac_tau_s':2e-9},timing={},va='dac_tau_s=2n'),
    dict(name='comparison_deadline',analog={},timing={'compare_to_write_s':9e-9},va='compare_to_write_s=9n'),
    dict(name='stuck_bit3',analog={'stuck_bit':3},timing={},va='stuck_bit=3'),
    dict(name='input_dependent_delay',analog={},timing={'comparator_tau_s':80e-12},va='comparator_tau_s=80p'),
]


def local_report():
    check_generated();m=SarAdcModel();values=stimuli()
    failures=[]
    for i,(v,_) in enumerate(values):
        r=m.convert(v)
        if not r.completed or r.code!=m.ideal_code(v) or r.counts!=(8,8,8,16):failures.append(i)
    static=load('results/static/results.json')['b']
    measured=static['midpoints_v']
    center_errors=[]
    for k in range(256):
        v=-.9+(k+.5)*m.spec.lsb
        if bisect.bisect_right(measured,v)!=k:center_errors.append(k)
    fft_rows=list(csv.DictReader((ROOT/'results/fft/b_codes.csv').open(encoding='utf-8')))
    dynamic_deltas=[m.ideal_code(float(r['aperture_source_v']))-int(float(r['code'])) for r in fft_rows]
    native=load('results/migration/original_short.json')['frames'];timing_errors=[];code_errors=[]
    for f in native:
        v=-.9+(f['expected_code']+.5)*m.spec.lsb
        result=m.convert(v)
        if result.code!=f['code_98']:code_errors.append(f['frame'])
        timing_errors.append(result.conversion_s*1e9-f['conversion_ns'])
    report=dict(python_oracle_pass=not failures and not center_errors and not code_errors,
        nominal_test_vectors=len(values),center_codes=256,transition_probes=255*3,
        saturation_probes=5,native_aperture_inputs=len(fft_rows),
        binary_SAR_vs_closed_form_failures=failures,
        measured_static_boundaries=dict(source='results/static/results.json',center_failures=center_errors),
        native_TT_short=dict(source='results/migration/original_short.json',code_failures=code_errors,
            model_minus_native_conversion_ns=timing_errors,max_abs_difference_ns=max(map(abs,timing_errors)),
            interpretation='Median phase model approximation, not exact transistor timing correlation'),
        native_dynamic_comparison=dict(source='results/fft/b_codes.csv',
            different_codes=sum(d!=0 for d in dynamic_deltas),max_abs_difference_lsb=max(map(abs,dynamic_deltas)),
            interpretation='Ideal quantization of measured source-at-aperture values; finite acquisition, offset, gain and phase are absent, so differences are retained'),
        spec_sha256=sha(ROOT/'specs/arch.json'),model_sha256=sha(ROOT/'design/behav/python/sar_adc.py'))
    out=ROOT/'results/behav';out.mkdir(parents=True,exist_ok=True)
    (out/'python_crosscheck.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not report['python_oracle_pass']:raise ValueError('Behavioral oracle discrepancy; see results/behav/python_crosscheck.json')
    return report


def prepare(run_id='sar8-modules-v3'):
    from .modular import prepare as prepare_modules
    check_generated()
    return prepare_modules(run_id)


def collect(run_id):
    from tools.saradc.__main__ import engine
    e=engine();status=e.phase('status',run_id)
    out=ROOT/'results/behav'
    state=ROOT/'work/state/behav'/run_id
    state.mkdir(parents=True,exist_ok=True)
    (state/'status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    if status['simulation'].get('status')!='complete' or status['analysis'].get('status')!='complete':
        raise ValueError('Native simulation and analysis must complete before publishing a verdict')
    transfer=e.collect(run_id)
    folder=ROOT/transfer['local_path']
    source=folder/'derived/result.json'
    result=json.loads(source.read_text(encoding='utf-8'))
    if result.get('module_validation'):
        from .modular import publish
        (out/'modules_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
        return publish(source,transfer,status)
    (out/'native_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    if not result.get('analysis_complete') or not result.get('python_VA_crosscheck_pass'):
        raise ValueError('Native behavioral crosscheck failed; retain the collected evidence')
    files={k.replace('\\','/'):v for k,v in result['context']['source_files'].items()}
    for name in ['design/behav/python/sar_adc.py','design/behav/veriloga/sar_adc_b.va',
                 'design/behav/veriloga/b_defaults.vh','tb/behav/observer.va']:
        if sha(ROOT/name)!=files[name]:raise ValueError('Current model source differs from the native run: '+name)
    snapshot_path=ROOT/'work/behav'/run_id/'source_spec.json'
    if not snapshot_path.is_file():
        if run_id!='sar8-behav-cross-v1':
            raise ValueError('The native run has no retained source specification')
        snapshot_path=ROOT/'results/behav/native_source_spec_v1.json'
    if sha(snapshot_path)!=files['specs/arch.json']:
        raise ValueError('Source specification snapshot differs from native registration')
    snapshot=json.loads(snapshot_path.read_text(encoding='utf-8'))
    current=load('specs/arch.json')
    if snapshot['behavior_models']['default_timing']!=current['behavior_models']['default_timing']:
        raise ValueError('Current timing parameters differ from the native source spec')
    for key in ['input','interface','reference','resolution_bits','external_clock']:
        if snapshot[key]!=current[key]:
            raise ValueError('Current behavioral contract differs from the native source spec: '+key)
    shutil.copyfile(source,out/'native_crosscheck.json')
    retained_snapshot=out/'native_source_spec.json'
    shutil.copyfile(snapshot_path,retained_snapshot)
    proof=dict(run_id=run_id,registered_recipe_hash=status['registered']['recipe_hash'],
               result_sha256=sha(source),collection=transfer,
               source_spec_snapshot=retained_snapshot.relative_to(ROOT).as_posix(),
               source_spec_sha256=sha(retained_snapshot),current_spec_sha256=sha(ROOT/'specs/arch.json'),
               current_parameter_and_source_identity=True,
               spec_difference='The exact native spec is retained; current input, interface, timing and model source identities are verified separately',
               native_warning_codes=result['warning_codes'])
    (out/'native_provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return dict(native_crosscheck_pass=True,frame_records=result['frame_records'],
                independent_pin_probes=result['independent_pin_probes'],max_time_error_s=result['max_time_error_s'])
