"""Compare the 100 ps fixed-voltage corner screen with its existing TT source."""
import csv
import gzip
import json
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'verification/manual_adc/cdac_100ps_corners_v1'
CASES = [('tt', 'TT 27 C', 27), ('ffcold', 'FF -40 C', -40),
         ('ffhot', 'FF 125 C', 125), ('sscold', 'SS -40 C', -40),
         ('sshot', 'SS 125 C', 125)]
COLORS = ['#657180', '#246ac4', '#d25328', '#18866b', '#9b54a6']

def load(key):
    run = 'manual8-cdac-edge-s100-tt-v1' if key == 'tt' else 'manual8-cdac-s100-'+key+'-v1'
    p = ROOT/'output/managed_execution/runs'/run/'collected'
    r = json.loads((p/'derived/result.json').read_text())
    if key != 'tt':
        shutil.copyfile(p/'derived/result.json', BASE/key/'results.json')
    with gzip.open(p/'derived/reset_native.csv.gz', 'rt') as f:
        rows = list(csv.DictReader(f))
    z = {k: np.array([float(row[k]) for row in rows]) for k in rows[0]}
    state = json.loads((p/'simulation.state.json').read_text())
    analysis = json.loads((p/'analysis.state.json').read_text())
    receipt = json.loads((p/'collection_receipt.json').read_text())
    return run, r, z, state, analysis, receipt, (p/'spectre.out').read_text(encoding='utf-8', errors='replace')

def main():
    data = {k: load(k) for k, _, _ in CASES}
    summary = {}
    clock = data['tt'][1]['timing_events']['clks']
    checks = {}
    for key, label, temp in CASES:
        run, r, z, s, a, receipt, log = data[key]
        worst = max(r['terminal_pairs'], key=lambda q: q['peak_V'])
        bottoms = {n: q for n, q in r['node_extrema'].items() if '.xd.net' in n}
        node = min(bottoms, key=lambda n: bottoms[n]['min_V'])
        clockerr = max(abs(x-y) for direction in ['rising', 'falling']
                       for x, y in zip(clock[direction], r['timing_events']['clks'][direction]))
        z['0'] = np.zeros_like(z['time'])
        stress = np.max(np.array([abs(z[q['nodes'][0]]-z[q['nodes'][1]]) for q in r['terminal_pairs']]), axis=0)
        z['all_terminal_peak'] = stress
        z['bottom_min'] = np.min(np.array([z[n] for n in bottoms]), axis=0)
        validation = {
            'native_complete': s['status'] == 'complete' and s['exit_code'] == 0 and s['native']['zero_error_footer'],
            'analysis_complete': a['status'] == 'complete' and a['exit_code'] == 0,
            'temperature_in_log': bool(re.search(r'temp\s*=\s*'+str(temp)+r'\s+C', log)),
            'same_native_accuracy_settings': s['native']['effective_settings'] == data['tt'][3]['native']['effective_settings'],
            'supply_and_reference_preserved': bool(np.max(abs(z['vdd']-.9)) < 1e-10 and np.max(abs(z['refp']-.9)) < 1e-10 and np.max(abs(z['refn'])) < 1e-10),
            'clock_preserved': clockerr < 1e-12,
            'sample_midpoints_preserved': max(r['sample_timing_validation'].values()) < 1e-12,
            'terminal_pairs_complete': len(r['terminal_pairs']) == 168,
            'zoom_stress_bounded_by_full_native': float(max(stress)) <= worst['peak_V']+1e-10,
            'zoom_bottom_bounded_by_full_native': float(min(z['bottom_min'])) >= bottoms[node]['min_V']-1e-10,
            'budget': s['peak_rss_bytes'] <= 1024*1024**2 and a['peak_rss_bytes'] <= 256*1024**2 and receipt['total_bytes'] <= 32*1024**2,
        }
        assert all(validation.values()), (key, validation)
        checks[key] = validation
        summary[key] = {
            'run_id': run, 'label': label, 'vdd_V': .9, 'temperature_c': temp,
            'short_test_pass': r['short_test_pass'], 'checks': r['checks'], 'summary': r['summary'],
            'bottom_min_V': bottoms[node]['min_V'], 'bottom_node': node, 'bottom_min_s': bottoms[node]['min_s'],
            'worst_terminal': worst, 'maximum_pair_duration_over_s': max(q['duration_over_s'] for q in r['terminal_pairs']),
            'settling_pass_count': sum(q['settled_by_2ns'] for q in r['segments']),
            'max_settling_upper_s': max(q['settling_time_upper_s'] or 0 for q in r['segments']),
            'unsettled_segment_count': sum(q['settling_time_upper_s'] is None for q in r['segments']),
            'correct_code_count': sum(q['actual'] == q['expected'] for q in r['captures']),
            'codes': [q['actual'] for q in r['captures']], 'comparisons': len(r['comparisons']),
            'clock_delta_s': clockerr, 'sample_timing_validation': r['sample_timing_validation'],
            'CMI_codes': r['CMI_codes'], 'native_settings': s['native'], 'native_points': r['native_points'],
            'simulation_seconds': s['elapsed_seconds'], 'simulation_peak_rss_MiB': s['peak_rss_bytes']/1024**2,
            'analysis_peak_rss_MiB': a['peak_rss_bytes']/1024**2, 'collected_bytes': receipt['total_bytes'],
            'zoom_terminal_max_V': float(max(stress)), 'zoom_bottom_min_V': float(min(z['bottom_min']))}
    (BASE/'comparison.json').write_text(json.dumps(summary, indent=2)+'\n')
    (BASE/'validation.json').write_text(json.dumps(checks, indent=2)+'\n')
    figdir = BASE/'figures'
    figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    env = ('0.9 V / 10 MS/s / 100 ps sampler conductance rise; midpoint and closing edge fixed\n'
           '28 native CDAC ref MOS; ideal 1.28 pF/side, supplies, sampler, comparator and SAR')
    fig, ax = plt.subplots(4, 1, figsize=(11, 10), sharex=True, layout='constrained')
    for (key, label, _), color in zip(CASES, COLORS):
        z = data[key][2]
        t = (z['time']-110e-9)*1e12
        for row, name in enumerate(['xadc.xn.sample_frac', 'xadc.topn', 'bottom_min', 'all_terminal_peak']):
            ax[row].plot(t, z[name], color=color, label=label, lw=1.3)
    for a, label in zip(ax, ['Sample on fraction', 'N top plate (V)', 'Lowest bottom (V)', 'Max MOS terminal (V)']):
        a.set_ylabel(label)
        a.grid(alpha=.2)
        a.set_xlim(-80, 200)
    ax[0].legend(ncol=5, fontsize=8)
    ax[2].axhline(-.09, color='black', ls=':', lw=1)
    ax[3].axhline(.99, color='#bd3030', ls='--', lw=1, label='0.99 V screen')
    ax[3].legend(fontsize=8)
    ax[-1].set_xlabel('Time relative to 110 ns (ps)')
    fig.suptitle('Sampling / reference-reset interaction — native-point zoom\n'+env, fontsize=11)
    fig.savefig(figdir/'waveforms.png', dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    labels = [label.replace(' ', '\n', 1) for _, label, _ in CASES]
    fields = [('bottom_min_V', 1e3, 'Full-run lowest bottom (mV)'),
              ('max_terminal_V', 1, 'Full-run max terminal (V)'),
              ('max_compare_dm_error_V', 1e6, 'Max comparison DM error (uV)'),
              ('settling_pass_count', 1, 'Steps passing 2 ns / 0.1 LSB check')]
    for index, (field, scale, title) in enumerate(fields):
        axis = ax.flat[index]
        values = [summary[key].get(field, summary[key]['summary'].get(field))*scale for key, _, _ in CASES]
        axis.bar(range(5), values, color=COLORS)
        axis.set_xticks(range(5), labels)
        axis.set_title(title, fontsize=11)
        axis.grid(axis='y', alpha=.2)
        axis.bar_label(axis.containers[0], fmt='%.0f' if index == 3 else '%.3f', padding=3, fontsize=9)
        if index == 0:
            axis.set_ylim(min(values)*1.3, 0)
        elif index == 1:
            axis.set_ylim(.9, max(1.01, max(values)+.02))
            axis.axhline(.99, color='#bd3030', ls='--', label='0.99 V')
            axis.legend(fontsize=8)
        elif index == 2:
            axis.set_ylim(0, max(values)*1.25 if max(values) > 0 else 1)
            axis.axhline(703.125, color='#bd3030', ls='--', label='703.125 uV limit')
            axis.legend(fontsize=8)
        else:
            axis.set_ylim(0, 67)
            axis.axhline(56, color='#bd3030', ls='--', lw=1)
    fig.suptitle('Full 820 ns / 8-frame corner screen\n'+env, fontsize=11)
    fig.savefig(figdir/'metrics.png', dpi=160)
    plt.close(fig)

    # Stream existing display data for persistent-error diagnosis, not native peaks.
    steady = {}
    columns = ['time', 'dm_error', 'vrefp:1', 'vrefn:1', 'refp', 'refn',
               'xadc.xp.xd.net1', 'xadc.xn.xd.net1', 'xadc.dp_1', 'xadc.dn_1', 'xadc.xp.sample_frac']
    for key in ['tt', 'ffhot']:
        p = ROOT/'output/managed_execution/runs'/summary[key]['run_id']/'collected/derived/wave.csv.gz'
        rows = []
        with gzip.open(p, 'rt') as f:
            for row in csv.DictReader(f):
                t = float(row['time'])
                if t > 100e-9:
                    break
                if 75e-9 <= t <= 100e-9:
                    rows.append({name: float(row[name]) for name in columns})
        assert rows
        steady[key] = {'first': rows[0], 'last': rows[-1], 'display_points': len(rows)}
        steady[key]['mean_refp_draw_A'] = sum(-r['vrefp:1'] for r in rows)/len(rows)
        steady[key]['mean_high_bottom_drop_V'] = sum(r['refp']-r['xadc.xp.xd.net1'] for r in rows)/len(rows)
    (BASE/'steady_diagnostic.json').write_text(json.dumps(steady, indent=2)+'\n')

    passed = [label for key, label, _ in CASES if summary[key]['short_test_pass']]
    failed = [label for key, label, _ in CASES if not summary[key]['short_test_pass']]
    lines = ['# CDAC 100 ps接通：极端工艺与温度短测', '',
             '通过本轮全部短测项：'+ '、'.join(passed)+'。未通过：'+('、'.join(failed) or '无')+'。', '',
             '**供电固定0.9 V；这是工艺/温度筛查，尚未覆盖0.81–0.99 V全供电范围，也不是整机PVT签核。**', '',
             '100 ps指理想采样器接通电导的0–100%过渡。外部CLKS仍为50 ps，参考栅控仍为50 ps；采样接通中点10.030 ns、关闭中点49.980 ns（均每100 ns重复）及参考复位时序不变。', '',
             '沿用原28个参考开关MOS及尺寸，双侧各1.28 pF理想电容。采样器Ron=1 Ω、比较器/SAR、电源和输入均理想；无噪声、失配、版图寄生。每角820 ns、8个代表输入码，不是256码全扫或FFT。TT复用上一轮已完成的s100，没有重跑。', '',
             '| 条件 | 最低底板(mV) | 最大端压(V) | 差模误差(µV) | 建立段 | 正确码 | CMI |',
             '|---|---:|---:|---:|---:|---:|---|']
    for key, label, _ in CASES:
        q = summary[key]
        lines.append('| %s | %.3f | %.6f | %.3f | %d/56 | %d/8 | %s |'%(
            label, q['bottom_min_V']*1e3, q['summary']['max_terminal_V'], q['summary']['max_compare_dm_error_V']*1e6,
            q['settling_pass_count'], q['correct_code_count'], ', '.join(q['CMI_codes']) or '无'))
    lines += ['', '指标取820 ns全部原生点。端压筛查上限0.99 V，检查28管的全部六种端差（168对）；比较差模/共模预算均0.1 LSB=703.125 µV，保持漂移预算0.05 LSB，逐位建立预算2 ns，转换预算50 ns。器件端差筛查不代替PDK可靠性签核。', '',
              '![全时域指标](figures/metrics.png)', '',
              '![采样与参考复位窗口](figures/waveforms.png)', '',
              '波形图显示第2帧重新采样局部窗口，表中最大值覆盖全部8帧；两者的最坏时刻可能不同。', '',
              '## 最坏点与精度', '']
    for key, label, _ in CASES:
        q = summary[key]; w = q['worst_terminal']
        lines.append('- **%s**：最坏%s %s，%.6f V @ %.6f ns；最低底板%s @ %.6f ns。共模误差%.3f µV，保持漂移%.3f µV，已进入预算段的建立上界%.3f ps（另有%d段未进入预算），转换%.3f ns。'%(
            label, w['device'], w['pair'], w['peak_V'], w['time_s']*1e9, q['bottom_node'], q['bottom_min_s']*1e9,
            q['summary']['max_compare_cm_error_V']*1e6, q['summary']['max_held_drift_V']*1e6,
            q['max_settling_upper_s']*1e12, q['unsettled_segment_count'], q['summary']['max_conversion_s']*1e9))
    lines += ['', '## FF热角残差', '',
              'FF 125°C的码0、255、1、254各有末两段未达到0.1 LSB误差预算，共8段失败；最大比较差模残差0.710855 mV，比0.703125 mV预算高7.73 µV，约1.1%。不能因8个码正确就判定全部通过，也不应把这种轻微超预算描述成严重功能失效。', '',
              '75–100 ns转换已结束、采样关闭且控制保持。TT/FF热角高参考持续输出电流分别为%.3f/%.3f µA；接高参考的P侧1C底板压降分别为%.3f/%.3f µV。理想参考端仍为0.9 V，该支路栅极接近0 V，残差没有随额外等待消失。'%(steady['tt']['mean_refp_draw_A']*1e6, steady['ffhot']['mean_refp_draw_A']*1e6, steady['tt']['mean_high_bottom_drop_V']*1e6, steady['ffhot']['mean_high_bottom_drop_V']*1e6), '',
              '这些证据更符合热角关断漏电与导通开关压降形成的静态误差，而不是需要再等一点的动态建立不足。具体漏电管及电流组成尚需支路漏极/体电流测量确认；本轮未改变尺寸。该保持阶段仅高参考源输出功率就约0.717 mW，也需要关注；它不是整机功耗测量。原始抽样值见[steady_diagnostic.json](steady_diagnostic.json)。下一步优先测FF热角参考支路静态电流，再决定是否调整关断管长度；不继续盲目放缓时钟。', '',
              '## 原生记录与复现', '',
              '只改变MOS模型section（ttmacro/ffmacro/ssmacro_mos_moscap）与温度；未使用的无源器件模型section保持原配置。输入逐文件SHA及差异检查见[manifest.json](manifest.json)。', '',
              '精确运行身份、原生设置、告警及资源见[comparison.json](comparison.json)，检查见[validation.json](validation.json)。各角完整测量保存在对应目录results.json，原始日志与波形保留于managed运行目录。', '']
    for key, label, _ in CASES:
        q = summary[key]
        lines.append('- %s：`%s`；%d原生点；告警%s；仿真%.2f s / %.1f MiB，分析%.1f MiB，回收%.2f MiB。'%(
            label, q['run_id'], q['native_points'], ', '.join(q['native_settings']['warning_codes']) or '无',
            q['simulation_seconds'], q['simulation_peak_rss_MiB'], q['analysis_peak_rss_MiB'], q['collected_bytes']/1024**2))
    lines += ['', 'Spectre 21.1 X CX，单线程；实际tran reltol=1e-7、vabstol=10 nV、iabstol=10 fA、gear2only、maxstep20 ps、conservative_sigglobal。SFE-1131为PDK重复scalefactor声明，VACOMP-2435为旧环境变量提示；无CMI不等于零告警。', '',
              '未改OA、拓扑、尺寸或旧数据，未采用新整机基线。当前证据仅覆盖给定理想边界及8帧；真实Bootstrap/栅驱动、供电极端、更多输入序列和整机性能需另测。']
    (BASE/'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k: {'pass': q['short_test_pass'], 'bottom_mV': q['bottom_min_V']*1e3,
                              'terminal_V': q['summary']['max_terminal_V'], 'dm_uV': q['summary']['max_compare_dm_error_V']*1e6,
                              'codes': q['correct_code_count'], 'settle': q['settling_pass_count'], 'CMI': q['CMI_codes']}
                      for k, q in summary.items()}, indent=2))

if __name__ == '__main__':
    main()
