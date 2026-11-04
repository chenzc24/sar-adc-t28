"""Local completed fixed-pulse/hold2 result comparison; no circuit generation."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=HERE/'results/kickback_actual_tt_v1'
RUNS=['sar8audit-comp-hold2-tt-v1','sar8audit-comp-actual-tt-v1']


def sha(b):return hashlib.sha256(b).hexdigest()


def load(run):
    base=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt_blob=(base/'collection_receipt.json').read_bytes();receipt=json.loads(receipt_blob)
    if receipt.get('skipped') or receipt['status']['run_id']!=run:raise ValueError('Incomplete/wrong collection')
    for f in receipt['files']:
        b=(base/f['name']).read_bytes()
        if len(b)!=f['bytes'] or sha(b)!=f['sha256']:raise ValueError('Receipt differs: '+f['name'])
    b=(base/'derived/result.json').read_bytes();r=json.loads(b)
    for phase in ['simulation','analysis']:
        state=json.loads((base/(phase+'.state.json')).read_bytes())
        if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Managed/native run incomplete')
        if phase=='simulation' and not all(state['native'][k] for k in ['native_analysis_pass','zero_error_footer']):raise ValueError('Native success missing')
    log=(base/'spectre.out').read_bytes()
    if log!=(base/'derived/spectre.original.log').read_bytes() or sha(log)!=r['original_simulator_log_sha256']:raise ValueError('Original log differs')
    text=log.decode('ascii');accepted=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',text)[1])
    if 'allpub' in text or not re.search(r'save\s+45\s+\(current\)',text) or not re.search(r'save\s+36\s+\(voltage\)',text):raise ValueError('Requested saves not accepted')
    compressed=(base/'derived'/r['waveform']['file']).read_bytes()
    if sha(compressed)!=r['waveform']['sha256']:raise ValueError('Native gzip mismatch')
    raw=gzip.decompress(compressed)
    if sha(raw)!=r['waveform']['uncompressed_sha256']:raise ValueError('Native row hash mismatch')
    cols=r['waveform']['columns'];x=np.frombuffer(raw,dtype='<f8').reshape((-1,len(cols)))
    if len(x)!=accepted+1 or len(x)!=r['native_points'] or x[0,0]!=0 or x[-1,0]!=260e-9 or not np.all(np.diff(x[:,0])>0) or not np.isfinite(x).all():raise ValueError('Native time/value/count mismatch')
    return dict(run=run,r=r,x=x,cols=cols,provenance=dict(recipe_sha256=receipt['status']['registered']['recipe_hash'],
        files=len(receipt['files']),bytes=receipt['total_bytes'],receipt_sha256=sha(receipt_blob),result_sha256=sha(b),
        log_sha256=sha(log),native_gzip_sha256=sha(compressed),native_rows_sha256=sha(raw),
        native_rows=len(x),accepted_native_steps=accepted,raw_ascii_downloaded=False))


def cycle_record(item,index):
    r=item['r'];c=r['cycles'][index];cfg=c['configuration'];x=item['x'];cols=item['cols'];get=lambda n:x[:,cols.index(n)]
    fall=cfg.get('clock_fall_start_s',cfg['start_s']+12e-9)
    mask=(x[:,0]>=cfg['start_s'])&(x[:,0]<fall)
    values=get('xactive.comp_p')-get('xactive.comp_n');ix=np.flatnonzero(mask)[np.argmax(abs(values[mask]))]
    pre=c['pre_compare']['arms']['evaluate']
    return dict(index=index,scheduled_start_s=cfg['start_s'],fall_start_s=fall,fall_end_s=cfg['clock_fall_end_s'],
        actual_precompare_time_s=c['pre_compare']['time_s'],input_diff_v=pre['diff_v'],input_cm_v=pre['cm_v'],
        target_diff_error_v=c['pre_compare_target_error_v'],raw_resolution=c['raw_resolution'],
        max_abs_output_difference_before_reset_v=float(abs(values[ix])),output_peak_time_s=float(x[ix,0]),
        raw_observation_threshold_v=.45,write_count=len(c['writes']),
        before_reset_write_count=len(c.get('writes_before_reset',c['writes'])),
        write_delays_s=c['write_delay_from_clock_half_s'],late_D0_bit=c['late_D0_bit'],
        reset_levels90=c['pre_compare']['reset_all_above_90pct'],writes=c['writes'])


def main():
    items=[load(run) for run in RUNS];short=items[1]
    actual=[cycle_record(short,i) for i in range(6)]
    if any(c['write_count'] or c['raw_resolution'] is not None for c in actual[:2]):raise ValueError('Result differs from reported interrupted first pair')
    if short['r']['unassigned_write_events']:raise ValueError('Unexpected unassigned writes')
    if not all(short['r']['cycles'][i]['nominal_polarity_written_before_reset'] for i in range(2,6)):raise ValueError('Long-window controls differ')
    summary=dict(scope='Fixed measured-pulse short-reset/receiver diagnosis; not a complete asynchronous SAR result',
        provenance={item['run']:item['provenance'] for item in items},
        first_pair={item['run']:[cycle_record(item,i) for i in [0,1]] for item in items},
        actual_long_controls=actual[2:],actual_unassigned_writes=short['r']['unassigned_write_events'],
        warnings={item['run']:item['r']['native_warning_codes'] for item in items},
        selected_MOS_pairs={item['run']:dict(count=len(item['r']['mos_pair_extrema']),exceeded=item['r']['mos_screen_exceeded_records']) for item in items},
        timing_replay=short['r']['actual_interval_replay'],
        interpretation='First decision interrupted: second precompare residue is recovery from an interrupted evaluation, not after a valid first SAR conversion.',
        proposed_next='Restore original transistor completion/clock feedback and receiver loads; no new package or run prepared',acceptance_pass=None)
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    figure(items,DEST/'actual_vs_hold2.png')
    report(summary,DEST/'report.md')
    print('LOCAL_ACTUAL_PULSE_REVIEW',DEST,'native_rows',len(short['x']))


def figure(items,path):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.16})
    fig,ax=plt.subplots(6,2,figsize=(12,12),sharex='col',gridspec_kw={'hspace':.18,'wspace':.18})
    colors=['#156582','#c75a31'];labels=['hold2: long pulses','Fixed short pulses']
    for item,color,label in zip(items,colors,labels):
        t=item['x'][:,0];get=lambda n:item['x'][:,item['cols'].index(n)]
        second_clock=next(e['estimated_half_vdd_time_s'] for e in item['r']['events'] if e['kind']=='clock' and e['estimated_half_vdd_time_s']>item['r']['cycles'][1]['configuration']['start_s'])
        times=[t*1e9,(t-second_clock)*1e9]
        windows=[(19.9,22.8),(-.15,2.6)]
        signals=[get('cmp_clk'),(get('topp_a')-get('topn_a'))*1e3,
            ((get('topp_a')+get('topn_a'))*.5-.45)*1e3,
            get('xactive.comp_p')-get('xactive.comp_n'),get('xactive.xctrl.phi_w'),get('d0_a')]
        for j,(time,(lo,hi)) in enumerate(zip(times,windows)):
            mask=(time>=lo)&(time<=hi)
            for row,values in enumerate(signals):ax[row,j].plot(time[mask],values[mask],color=color,label=label,lw=1.25)
            ax[-1,j].set_xlim(lo,hi)
    for j in [0,1]:
        ax[1,j].axhline(1.7578125,color='#777777',ls='--',lw=.8)
        ax[2,j].axhline(0,color='#777777',ls='--',lw=.8)
        ax[3,j].axhline(.45,color='#777777',ls='--',lw=.9)
        for row in [0,4,5]:ax[row,j].set_ylim(-.07,.99)
    axes_labels=['Compare CLK (V)','Top differential (mV)','CM offset from 450 mV (mV)',
                 'COMP_P − COMP_N (V)','Actual write clock (V)','Stored D0 (V)']
    for row,label in enumerate(axes_labels):ax[row,0].set_ylabel(label)
    ax[3,1].set_ylabel('Output difference (V)')
    ax[0,0].legend(loc='best',fontsize=8)
    ax[0,0].set_title('First comparison: same 20 ns start',loc='left',fontsize=11)
    ax[0,1].set_title('Second: aligned to each clock half-level rise',loc='left',fontsize=11)
    ax[-1,0].set_xlabel('Absolute time (ns)');ax[-1,1].set_xlabel('Time from second CLK 0.5 VDD rise (ns)')
    edges=items[1]['r']['actual_interval_replay']['fixture_edges']
    starts=[edges['fall1_start_s']*1e9,(edges['fall2_start_s']-edges['rise2_half_s'])*1e9]
    for j,at in enumerate(starts):
        for axes in ax[:,j]:axes.axvline(at,color=colors[1],ls=':',lw=1)
        ax[0,j].text(at+.025,.12,'Forced reset',color=colors[1],fontsize=8)
    fig.suptitle('Fixed short pulses interrupt small-input completion',fontsize=14,y=.985)
    fig.text(.5,.958,'TT · 0.9 V · 27°C · N4/rx2 + native T28 MOM · +0.25 LSB held input · original native samples',ha='center',fontsize=9)
    fig.text(.5,.018,'Native half-level intervals replayed with 0.1 ns ideal ramps. Fixed bottom rails and ideal temporary initialization; no noise/mismatch/PEX.\n'
        'Right panel translates each native time axis only. No cross-run interpolation. Dashed 0.45 V line is an output observation threshold.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.105,right=.98,top=.93,bottom=.075)
    fig.savefig(path,dpi=170);plt.close(fig)


def report(s,path):
    h=s['first_pair'][RUNS[0]];a=s['first_pair'][RUNS[1]]
    text=f'''# 固定短脉冲：不是两次有效SAR转换

actual TT原生仿真与分析完成，但首两轮小输入均 **没有复位前写入**；后四轮长窗对照正确。
这说明借来的固定短脉冲不适合当前小输入完成路径，不能归因于真实异步逻辑失效。

![短脉冲与hold2对照](actual_vs_hold2.png)

| 观测 | hold2长脉冲 | actual固定短脉冲 |
| --- | ---: | ---: |
| 两次比较起点间隔 | 40ns | 3.955843ns |
| CLK半电平高宽 | 12ns / 12ns | 1.179357ns / 1.212701ns |
| 从CLK半电平上升到复位沿开始 | 11.95ns / 11.95ns | 1.129357ns / 1.162701ns |
| 复位前输出差观测条件 | 两轮均达到 | 两轮均未达到 |
| 复位前最大输出差 | 达到0.45V | {a[0]['max_abs_output_difference_before_reset_v']:.3f}V / {a[1]['max_abs_output_difference_before_reset_v']:.3f}V |
| 前两轮写入数 | 1 / 1 | 0 / 0 |
| 第二轮前差模 | {h[1]['input_diff_v']*1e3:.6f}mV | {a[1]['input_diff_v']*1e3:.6f}mV |
| 第二轮前目标差模残差 | {h[1]['target_diff_error_v']*1e6:+.3f}µV | {a[1]['target_diff_error_v']*1e6:+.3f}µV |
| 第二轮前共模 | {h[1]['input_cm_v']*1e3:.6f}mV | {a[1]['input_cm_v']*1e3:.6f}mV |

在hold2中，从CLK半电平上升到小输入接收写入约需1.61ns。actual在同一时间基准下，
约1.13/1.16ns就开始复位；此时本次0.45V输出差观测条件尚未满足，实际PHI_W也没有上升。
0.45V是分析用观测线，不是接收器的真实门限或电路中的完成反馈条件。
D0保留旧0，不应记为“成功写入了错误0”。没有窗口外写入，后四轮长窗写入均正确。

时钟间隔来自冻结N4/rx2整机TT第2帧bit6→bit5，当时约−362/−138mV的输入可更快完成。
完整异步电路原本由真实完成事件决定何时复位；本实验切断该反馈，固定重放脉冲。
因此实验暴露的是 **固定脉冲和小输入完成时间不匹配**，不是观察到整机异步控制主动提前复位。

首轮没有完成有效写入，所以第二轮前−0.874µV差模残差、449.582mV共模只描述
**中断求值后的恢复轨迹**。高宽和恢复间隔都变了，不能把与hold2的差异单独归为reset间隔效应，
也不能称为一次成功SAR决策后的保持误差。

## 数据和范围

10文件、10,970,767B的回收SHA及原生压缩/解压波形均复核；93,208点对应93,207个接受步，
完整覆盖260ns。保存36条电压、45条电流。原生0 errors、7 warnings保留；
228个N4/rx2选定端间检查无超限，不等于全部934个MOS或整机签核。
原生0.5VDD时序间隔仍由0.1ns理想边沿重放，底板/参考固定理想，初始化后输入浮置。
没有真实CDAC位更新、噪声、失配或版图寄生。

下一项只提出恢复原生完成反馈和接收负载的最小fixture方案，见feedback_fixture_plan.md。
本次未改尺寸、未扫时钟、未准备新包或提交远端。
'''
    path.write_text(text,encoding='utf-8')


if __name__=='__main__':main()
