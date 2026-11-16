"""Report the frozen current-OR continuous noisy FFT; no waveform reprocessing."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import hashlib
import importlib.metadata
import json
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from adctoolbox.spectrum import compute_spectrum

ROOT = Path(__file__).resolve().parents[3]
RUN = 'sar8-resetor-noise-tt-fft1024-s101-v1'
OUT = ROOT / 'results/noise/resetor_1024_20261116'
FIELDS = ['frame', 'code', 'compares', 'writes', 'updates', 'captures_absent_zero',
          'early_code', 'valid', 'rail_error_v', 'sample_int_fall_time_s',
          'input_at_sample_int_fall_v', 'held_diff_v', 'final_top_diff_v', 'conversion_s']


def serial(x):
    if isinstance(x, dict): return {k: serial(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)): return [serial(v) for v in x]
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    return x


def save(p, x):
    p.write_text(json.dumps(serial(x), indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_dir = ROOT / 'work/output/managed_execution/runs' / RUN
    source = run_dir / 'collected'
    raw = (source / 'derived/result.json').read_bytes()
    d = json.loads(raw); c = d['context']
    assert c['run_id'] == RUN and c['noise'] and not c['mismatch'] and not c['PEX']
    assert c['samples'] == 1024 and c['warmup'] == 8 and c['bin'] == 461
    assert d['analysis_complete'] and d['native_decode_crosscheck'] and d['functional_pass']
    assert not d['invalid_all_frames']
    rows = np.asarray(d['frames'], float); codes = np.asarray(d['codes'], int)
    assert rows.shape == (1032, 14) and codes.shape == (1024,)
    assert np.array_equal(rows[:, 0], np.arange(1032))
    assert np.all(rows[:, 2:6] == [8, 8, 8, 0]) and np.all(rows[:, 7] == 1)
    assert np.array_equal(rows[:, 1], rows[:, 6]) and np.array_equal(codes, rows[8:, 1])
    assert np.all((codes >= 0) & (codes <= 255))
    fs, n, k, lsb = 1e7, 1024, 461, 1.8/256
    x = -.9+(codes+.5)*lsb; centered = x-x.mean()
    power = np.abs(np.fft.rfft(centered))**2/n**2; power[1:-1] *= 2
    rest = power.copy(); rest[[0, k]] = 0
    harmonic_bins = np.array([min(h*k % n, n-h*k % n) for h in range(2, 6)])
    noise = rest.copy(); noise[harmonic_bins] = 0
    direct = dict(sndr_dbc=10*np.log10(power[k]/rest.sum()),
                  snr_dbc=10*np.log10(power[k]/noise.sum()),
                  sfdr_dbc=10*np.log10(power[k]/rest.max()),
                  thd_dbc=10*np.log10(power[harmonic_bins].sum()/power[k]))
    direct['enob'] = (direct['sndr_dbc']-1.76)/6.02
    tb = compute_spectrum(centered, fs=fs, max_scale_range=(-.9, .9),
                          win_type='rectangular', side_bin=0, max_harmonic=5, nf_method=3)
    metrics = tb['metrics']
    checks = {name+'_toolbox_difference': abs(value-metrics[name]) for name,value in direct.items()}
    checks.update(parseval_error_v2=abs(power.sum()-np.mean(centered**2)),
                  managed_sndr_difference_db=abs(direct['sndr_dbc']-d['spectrum']['sndr_db']),
                  managed_sfdr_difference_db=abs(direct['sfdr_dbc']-d['spectrum']['sfdr_db']))
    assert max(checks.values()) < 1e-8 and checks['parseval_error_v2'] < 1e-14
    phase = 2*np.pi*k*np.arange(n)/n
    matrix = np.column_stack([np.ones(n), np.sin(phase), np.cos(phase)])
    coef = np.linalg.lstsq(matrix, x, rcond=None)[0]; fitted=matrix@coef; residual=x-fitted
    assert abs(np.mean(residual**2)-rest.sum()) < 1e-14
    spur = int(np.argmax(rest)); freq=np.arange(n//2+1)*fs/n
    dbc = 10*np.log10(np.maximum(power/power[k], 1e-30))
    simulation=json.loads((source/'simulation.state.json').read_text())
    analysis=json.loads((source/'analysis.state.json').read_text())
    cst=timezone(timedelta(hours=8))
    summary=dict(run_id=RUN, design_id=c['design_id'], host='thu-song', context=c,
        source_result_sha256=hashlib.sha256(raw).hexdigest(),
        recipe_hash=json.loads((ROOT/'work/mc/noise_fft_latest_status.json').read_text())['registered']['recipe_hash'],
        metrics=metrics, independent_metrics=direct, verification=checks,
        toolbox_version=importlib.metadata.version('adctoolbox'),
        method=dict(samples=n,warmup=8,fs_hz=fs,fin_hz=fs*k/n,window='rectangular',dc_removed=True,
                    fundamental_bin=k,harmonic_orders=[2,3,4,5],harmonic_bins=harmonic_bins,side_bins=0,
                    frequency_resolution_hz=fs/n,record_duration_s=n/fs,
                    enob_formula='(SNDR_dBc - 1.76)/6.02; input -1 dBFS, no amplitude correction',
                    snr_scope='Excludes DC, fundamental and H2-H5 bins; includes quantization and modeled transient noise',
                    thd_scope='H2-H5 bin energy includes finite-record noise contribution'),
        functional_pass=True,all_frames=1032,steady_frames=1024,invalid_frames=[],
        conversion_min_ns=rows[:,13].min()*1e9,conversion_max_ns=rows[:,13].max()*1e9,
        worst_conversion_frame=int(rows[np.argmax(rows[:,13]),0]),
        code_min=codes.min(),code_max=codes.max(),
        fit=dict(dc_offset_mv=coef[0]*1e3,amplitude_v=np.hypot(coef[1],coef[2]),
                 residual_rms_lsb=np.sqrt(np.mean(residual**2))/lsb,
                 residual_peak_lsb=np.max(np.abs(residual))/lsb,
                 note='Output minus fixed-frequency fitted sine: combined quantization/noise/distortion, not isolated device noise'),
        strongest_spur=dict(bin=spur,frequency_hz=freq[spur],level_dbc=dbc[spur]),
        power_w=d['power_w'],power_core_plus_reference_w=d['power_core_plus_reference_w'],
        power_qualification=d['power_qualification'],warning_codes=d['warning_codes'],
        effective_settings=d['effective_settings'],electrical_verdict=d['electrical_verdict'],
        simulation_hours=simulation['elapsed_seconds']/3600,analysis_seconds=analysis['elapsed_seconds'],
        simulation_complete_cst=datetime.fromtimestamp(simulation['updated_epoch'],cst).isoformat(),
        analysis_complete_cst=datetime.fromtimestamp(analysis['updated_epoch'],cst).isoformat(),
        limitations=d['limitations']+['Harmonic-bin energies include noise; single-record THD is not isolated distortion',
          'Historical no-noise A/B FFT uses a different design, so differences cannot isolate this design noise penalty'])
    for name in ['spectre.out','simulation.state.json','analysis.state.json','collection_receipt.json']:
        shutil.copyfile(source/name, OUT/name)
    (OUT/'native_result.json').write_bytes(raw)
    shutil.copyfile(run_dir/'recipe.json', OUT/'recipe.json')
    save(OUT/'results.json',summary)
    with (OUT/'all_frames.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)
    with (OUT/'fft_codes.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['sample_index','source_frame','sample_int_fall_time_s','code','decoded_v','fit_v','residual_lsb'])
        w.writerows(zip(np.arange(n),rows[8:,0],rows[8:,9],codes,x,fitted,residual/lsb))
    with (OUT/'spectrum.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['bin','frequency_hz','power_v2','level_dbc'])
        w.writerows(zip(np.arange(len(freq)),freq,power,dbc))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(11,5.6),layout='constrained')
    ax.plot(freq[1:]/1e6,dbc[1:],color='#246493',lw=.85)
    ax.scatter([freq[k]/1e6,freq[spur]/1e6],[0,dbc[spur]],color=['#246493','#c14e3f'],s=30,zorder=4)
    ax.annotate('Fundamental', (freq[k]/1e6,0),xytext=(-75,-20),textcoords='offset points',fontsize=9)
    ax.annotate('Largest spur', (freq[spur]/1e6,dbc[spur]),xytext=(12,18),textcoords='offset points',fontsize=9,
                arrowprops=dict(arrowstyle='-',color='#c14e3f'))
    for h,b in zip(range(2,6),harmonic_bins):
        ax.scatter(freq[b]/1e6,dbc[b],s=20,facecolors='none',edgecolors='#af7332',zorder=3)
        ax.annotate('H'+str(h),(freq[b]/1e6,dbc[b]),xytext=(0,-13),textcoords='offset points',ha='center',fontsize=8)
    ax.set(xlim=(0,5),ylim=(-115,5),xlabel='Frequency (MHz)',ylabel='Power per FFT bin (dBc)',
           title='Current OR design | TT continuous transient-noise FFT\n10 MS/s · 4.501953125 MHz · 1024 samples · input −1 dBFS')
    ax.grid(alpha=.18)
    ax.text(.025,.965,'SNR  %.2f dB\nSNDR %.2f dB\nSFDR %.2f dBc\nTHD  %.2f dBc\nENOB %.3f bit'%(metrics['snr_dbc'],metrics['sndr_dbc'],metrics['sfdr_dbc'],metrics['thd_dbc'],metrics['enob']),
            transform=ax.transAxes,va='top',family='monospace',bbox=dict(facecolor='white',alpha=.9,edgecolor='#cccccc'))
    fig.savefig(OUT/'spectrum.png',dpi=180,facecolor='white');fig.savefig(OUT/'spectrum.svg');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,6),layout='constrained')
    axes[0].plot(np.arange(n),residual/lsb,lw=.55,color='#246493')
    axes[0].set(xlabel='Sample index',ylabel='Residual (LSB)',title='Decoded output minus fitted sine — quantization + noise + distortion')
    axes[1].plot(rows[:,0],rows[:,13]*1e9,lw=.7,color='#2d8268')
    axes[1].axvspan(-.5,7.5,color='#b8bfca',alpha=.3,label='8 warmup frames')
    axes[1].set(xlabel='Frame index (including warmup)',ylabel='Conversion time (ns)',title='1032/1032 protocol frames passed')
    for a in axes:a.grid(alpha=.18)
    axes[1].legend(loc='upper right');fig.savefig(OUT/'residual_timing.png',dpi=160,facecolor='white');plt.close(fig)
    print(json.dumps(serial({k:summary[k] for k in ['metrics','fit','strongest_spur','power_w','power_core_plus_reference_w','conversion_min_ns','conversion_max_ns','code_min','code_max','verification','simulation_complete_cst','analysis_complete_cst']}),indent=2))


if __name__=='__main__':main()
