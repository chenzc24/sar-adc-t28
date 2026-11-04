"""Final frozen A/B spectra from managed, native-crosschecked 1024-code results."""
from pathlib import Path
import csv
import hashlib
import importlib.metadata
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from adctoolbox.spectrum import compute_spectrum

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'results/fft'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolbox_panel as panel

FS, N, K, LSB = 1e7, 1024, 461, 1.8 / 256
FIELDS = ['frame', 'code', 'compares', 'writes', 'updates', 'captures',
          'early_code', 'valid', 'rail_error_v', 'aperture_time_s',
          'aperture_source_v', 'held_diff_v', 'final_top_diff_v', 'conversion_s']


def polar_readable(ax, phase, level, labels=None):
    """Same phase data as the shared renderer, with separated harmonic labels."""
    floor = -100
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
    ax.set_ylim(0, 103)
    ax.set_rticks([20, 40, 60, 80, 100], labels=['−80', '−60', '−40', '−20', '0 dBc'])
    ax.tick_params(labelsize=8)
    ax.scatter(phase, np.maximum(level-floor, 0), s=7, color=panel.BLUE, alpha=.6)
    if labels is not None:
        for ph, lev, label in zip(phase, level, labels):
            if lev < floor:
                continue
            ax.plot([ph, ph], [0, lev-floor], color=panel.BLUE, lw=1)
            offset = {'H1':(5, 4), 'H3':(32, -22), 'H5':(32, 12)}.get(label,(20, 4))
            ax.annotate(label, (ph, lev-floor), xytext=offset, textcoords='offset points',
                        fontsize=9, arrowprops=dict(arrowstyle='-', color=panel.BLUE, lw=.6))


panel.polar = polar_readable


def save(path, data):
    path.write_text(json.dumps(panel.serial(data), indent=2, ensure_ascii=False,
                               allow_nan=False) + '\n', encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=True)
    results = {}
    for label in ['a', 'b']:
        run = 'sar8camp-' + label + '-tt-fft1024-mm-v1'
        source = ROOT / 'work/output/managed_execution/runs' / run / 'collected/derived/result.json'
        z = json.loads(source.read_text())
        receipt = json.loads((OUT / (label + '_collection.json')).read_text())
        assert not receipt['skipped']
        assert z['analysis_complete'] and z['native_decode_crosscheck'] and z['functional_pass']
        c = z['context']
        assert c['run_id'] == run and c['samples'] == N and c['bin'] == K
        assert c['warmup'] == 8 and c['frames'] == 1032
        rows = np.asarray(z['frames'], float)
        assert rows.shape == (1032, 14) and np.array_equal(rows[:, 0], np.arange(1032))
        assert np.all(rows[:, 2:6] == [8, 8, 8, 16]) and np.all(rows[:, 7] == 1)
        assert np.array_equal(rows[:, 1], rows[:, 6])
        codes = np.asarray(z['codes'], int)
        assert codes.shape == (N,) and np.array_equal(codes, rows[8:, 1])
        assert np.all((codes >= 0) & (codes <= 255))
        x = (codes + .5) * LSB - .9
        zero = x - x.mean()
        power = abs(np.fft.rfft(zero)) ** 2 / N ** 2
        power[1:-1] *= 2
        remainder = power.copy(); remainder[[0, K]] = 0
        sndr = float(10 * np.log10(power[K] / remainder.sum()))
        sfdr = float(10 * np.log10(power[K] / remainder.max()))
        tb = compute_spectrum(zero, fs=FS, max_scale_range=(-.9, .9),
                              win_type='rectangular', side_bin=0, max_harmonic=5, nf_method=3)
        metrics = tb['metrics']
        checks = dict(native_decode_crosscheck=True, all_1032_protocol_frames_pass=True,
                      parseval_error_v2=float(abs(power.sum() - np.mean(zero ** 2))),
                      managed_sndr_difference_db=abs(sndr-z['spectrum']['sndr_db']),
                      toolbox_sndr_difference_db=abs(sndr-metrics['sndr_dbc']),
                      toolbox_sfdr_difference_db=abs(sfdr-metrics['sfdr_dbc']))
        assert checks['parseval_error_v2'] < 1e-14
        assert max(checks[k] for k in ['managed_sndr_difference_db', 'toolbox_sndr_difference_db',
                                      'toolbox_sfdr_difference_db']) < 1e-8
        measured = rows[8:]
        t = measured[:, 9]
        matrix = np.column_stack([np.ones(N), np.sin(2*np.pi*FS*K/N*t), np.cos(2*np.pi*FS*K/N*t)])
        coeff = np.linalg.lstsq(matrix, x, rcond=None)[0]
        source_coeff = np.linalg.lstsq(matrix, measured[:, 10], rcond=None)[0]
        relative_phase = np.angle(complex(coeff[1], coeff[2]) /
                                  complex(source_coeff[1], source_coeff[2]))
        residual = x - matrix @ coeff
        amplitude = np.hypot(coeff[1], coeff[2])
        fit = dict(offset_mv=coeff[0]*1e3, amplitude_v=amplitude,
                   relative_input_amplitude_error_percent=(amplitude/(.9*10**(-1/20))-1)*100,
                   equivalent_phase_lag_ns=-relative_phase/(2*np.pi*FS*K/N)*1e9,
                   residual_rms_lsb=np.sqrt(np.mean(residual**2))/LSB,
                   residual_peak_lsb=np.max(abs(residual))/LSB,
                   note='Output sine phase relative to fitted applied-input samples at the same internal clock edges; stimulus initial phase removed. Not calibrated physical aperture or measured propagation delay.')
        warning = ('CMI device-terminal warnings remain; not electrically qualified.' if
                   any(w.startswith('CMI-') for w in z['warning_codes']) else
                   'No CMI warnings in this run; not reliability sign-off.')
        result = dict(run_id=run, dut_sha256=c['dut_sha256'], source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      codes=codes, metrics=metrics, sndr_db=sndr, sfdr_dbc=sfdr, enob_bits=(sndr-1.76)/6.02,
                      spectrum_dbc=10*np.log10(np.maximum(power/power[K], 1e-30)),
                      spur_bin=int(np.argmax(remainder)), fit=fit, checks=checks,
                      conversion_min_ns=float(measured[:, 13].min()*1e9),
                      conversion_max_ns=float(measured[:, 13].max()*1e9),
                      power_w=z['power_w'], power_core_plus_reference_w=z['power_core_plus_reference_w'],
                      power_qualification=z['power_qualification'], warning_codes=z['warning_codes'],
                      effective_settings=z['effective_settings'], native_points=z['native_points'], warning=warning)
        results[label] = result
        with (OUT/(label+'_codes.csv')).open('w', newline='') as f:
            w=csv.writer(f); w.writerow(FIELDS); w.writerows(measured)
        adapter = dict(dynamic_frames=[dict(zip(FIELDS, row)) for row in measured],
                       dynamic=z['spectrum'], source_run_id=run, source_sha256=result['source_sha256'])
        save(OUT/(label+'_panel_input.json'), adapter)
        panel.main(OUT/(label+'_panel_input.json'), OUT/(label+'_toolbox_panel.png'),
                   OUT/(label+'_toolbox_panel.json'), label='Frozen '+label.upper()+' SAR ADC', warning=warning)

    delta = results['b']['codes'] - results['a']['codes']
    summary = dict(toolbox_version=importlib.metadata.version('adctoolbox'), variants=results,
                   ab_different_codes=int(np.count_nonzero(delta)), ab_max_code_difference=int(max(abs(delta))),
                   b_minus_a_sndr_db=results['b']['sndr_db']-results['a']['sndr_db'],
                   b_minus_a_sfdr_db=results['b']['sfdr_dbc']-results['a']['sfdr_dbc'],
                   limits=['TT only; no transient noise, mismatch, jitter or PEX.',
                           'Ideal external input/reference/supply/clock sources.',
                           'MX reltol1e-6 trap; strict CX only short-test compared, not full-record equivalence.',
                           'Power uses 10ps strobe integration; convergence not established.',
                           'Residual vs value/phase does not measure static DNL/INL.',
                           'Functional timing and ENOB do not establish terminal-voltage reliability.'])
    save(OUT/'results.json', summary)
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, layout='constrained')
    frequencies = np.arange(N//2+1)*FS/N/1e6
    for ax, label, color in zip(axes, ['a','b'], ['#2563a6','#bd5534']):
        r=results[label]
        ax.plot(frequencies[1:], r['spectrum_dbc'][1:], lw=.8, color=color)
        ax.scatter([frequencies[K],frequencies[r['spur_bin']]], [0,-r['sfdr_dbc']], color=color,s=24)
        ax.set(ylabel='Power (dBc)', ylim=(-115,5), xlim=(0,5),
               title=f"{label.upper()} | SNDR {r['sndr_db']:.3f} dB | SFDR {r['sfdr_dbc']:.3f} dBc | ENOB {r['enob_bits']:.3f} bit")
        ax.grid(alpha=.2)
        ax.text(.02,.94, r['warning'],transform=ax.transAxes,va='top',fontsize=9)
    axes[-1].set_xlabel('Frequency (MHz)')
    fig.suptitle('Frozen A/B | Native 1024-code coherent FFT\nTT, 0.9 V, 27 C | Fs 10 MS/s | Fin 4.501953125 MHz | -1 dBFS | Rectangular window',fontsize=13)
    fig.supxlabel('8 warmup frames excluded | DC removed | No transient noise / mismatch / PEX | Spectre X MX, 4 threads',fontsize=9)
    fig.savefig(OUT/'ab_spectrum.png',dpi=170);fig.savefig(OUT/'ab_spectrum.svg');plt.close(fig)
    a,b=results['a'],results['b']
    lines=['# 冻结 A/B 版本：TT 1024点频谱', '',
           'A为自建数字门版本，B为相同模拟核心接原生数字标准单元版本。两版均为本次冻结网表的实际输出码，不引用旧R4指标。', '',
           'TT、0.9 V、27°C，10 MS/s，输入4.501953125 MHz、−1 dBFS；连续运行1032帧，排除前8帧后取1024点。矩形窗、去直流、基波bin461。', '',
           '|指标|A|B|','|---|---:|---:|']
    for title,key,scale,unit in [('SNDR','sndr_db',1,'dB'),('SFDR','sfdr_dbc',1,'dBc'),('ENOB','enob_bits',1,'bit'),
                               ('最大转换时间','conversion_max_ns',1,'ns'),('核心+参考功耗估计','power_core_plus_reference_w',1e6,'µW')]:
        lines.append(f'|{title}|{a[key]*scale:.6f} {unit}|{b[key]*scale:.6f} {unit}|')
    for title,key in [('SNR（排除H2–H5）','snr_dbc'),('THD（H2–H5）','thd_dbc')]:
        lines.append(f"|{title}|{a['metrics'][key]:.6f} dB|{b['metrics'][key]:.6f} dB|")
    lines += ['', f"B−A：SNDR {summary['b_minus_a_sndr_db']:+.6f} dB；SFDR {summary['b_minus_a_sfdr_db']:+.6f} dB。1024点中{summary['ab_different_codes']}个码不同，最大差{summary['ab_max_code_difference']} LSB；差异本身不等于错码。", '',
              '全部1032帧与原始波形独立解码一致；8次比较、8次写入、8次更新、16次捕获及稳定性标志均通过。频谱由原生分析器、NumPy和ADCtoolbox 0.9.1交叉核对；Parseval能量检查通过。ENOB=(SNDR−1.76)/6.02，未按−1 dBFS补偿。', '',
              '![A/B频谱](ab_spectrum.png)', '',
              '[A版12图](a_toolbox_panel.png) · [B版12图](b_toolbox_panel.png) · [数值与验证](results.json)', '',
              '## 告警与限制', '',
              '- A本次日志没有CMI；B保留CMI-2751至2755。两者均不因此认定可靠性合格。',
              '- 原生Spectre设置为MX、reltol=1e-6、trap、maxstep=10 ps、4线程；此前短测与CX对照不代表整个1024点记录已证明等精度。',
              '- 无瞬态噪声、失配、抖动或版图寄生，外部源理想。SNR中的残差含确定性量化及未排除失真，不能称为热噪声实测。',
              '- 功耗由10 ps保存点积分，未完成积分网格收敛；核心+参考不含理想输入源和时钟驱动，时钟项单列于results.json。',
              '- 12图中的残差是输出减正弦拟合；不是输入时钟边沿误差，不能代替全码DNL/INL。全码扫描仍在运行。', '',
              '## 运行身份', '', f"- A：`{a['run_id']}`，DUT SHA256 `{a['dut_sha256']}`。",f"- B：`{b['run_id']}`，DUT SHA256 `{b['dut_sha256']}`。",
              '- 回收文件及校验见a_collection.json、b_collection.json；完整输出码见a_codes.csv、b_codes.csv。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({label:{key:r[key] for key in ['sndr_db','sfdr_dbc','enob_bits','power_core_plus_reference_w','warning_codes']} for label,r in results.items()},indent=2))


if __name__ == '__main__':
    main()
