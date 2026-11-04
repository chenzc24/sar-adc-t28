"""Review recovered charge-history cases only; no simulation/raw reanalysis."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=HERE/'results/history_charge_v1'
CASES={'negative_to_positive':'sar8audit-comp-history-neg-pos-tt-v1','positive_to_negative':'sar8audit-comp-history-pos-neg-tt-v1'}
BLUE='#176b86';ORANGE='#c55b33';GREEN='#258363';GRAY='#7a8086'


def sha(b):return hashlib.sha256(b).hexdigest()


def load(case):
    run=CASES[case];p=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt=json.loads((p/'collection_receipt.json').read_bytes())
    if receipt.get('skipped'):raise ValueError('Incomplete collection')
    for f in receipt['files']:
        b=(p/f['name']).read_bytes()
        if len(b)!=f['bytes'] or sha(b)!=f['sha256']:raise ValueError('Receipt mismatch: '+f['name'])
    for phase in ['simulation','analysis']:
        state=json.loads((p/(phase+'.state.json')).read_bytes())
        if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Incomplete '+phase)
        if phase=='simulation' and not all(state['native'][n] for n in ['native_analysis_pass','zero_error_footer']):raise ValueError('Native success missing')
    r=json.loads((p/'derived/result.json').read_bytes());cfg_path=HERE/'generated/history_charge_v1'/case/'measurement.json'
    cfg=json.loads(cfg_path.read_bytes())
    if r['measurement_sha256']!=sha(cfg_path.read_bytes()) or r['history_case']!=cfg['history_case']:raise ValueError('Frozen history/config differs')
    managed=json.loads((p.parent/'recipe.json').read_bytes())
    managed_hash=sha(json.dumps(managed,sort_keys=True,separators=(',',':')).encode('ascii'))
    log=(p/'spectre.out').read_bytes()
    if log!=(p/'derived/spectre.original.log').read_bytes() or sha(log)!=r['original_simulator_log_sha256']:raise ValueError('Native log differs')
    n=int(re.search(rb'Number of accepted tran steps\s*=\s*(\d+)',log)[1])+1
    if n!=r['native_points'] or not r['two_full_native_passes_match']:raise ValueError('Full native measurements missing')
    if not r['protocol_eight_pass'] or not r['history_assessment_valid'] or r['token_sequence']!=list(range(7,-1,-1)):raise ValueError('History protocol differs')
    if r['event_counts']!=dict(clock=8,clock_fall=8,write=8,update=8,reset=8):raise ValueError('Event counts differ')
    if (r['selected_mos_count'],r['selected_mos_pair_count'])!=(165,990) or r['selected_mos_screen_exceeded_records']<0 or r['full_mos_screen_complete'] or r['full_mos_screen_exceeded_records'] is not None:raise ValueError('Stress count/scope differs')
    w=r['waveform'];compressed=(p/'derived'/w['file']).read_bytes()
    if sha(compressed)!=w['sha256']:raise ValueError('Export gzip differs')
    raw=gzip.decompress(compressed)
    if sha(raw)!=w['uncompressed_sha256']:raise ValueError('Export native rows differ')
    x=np.frombuffer(raw,dtype='<f8').reshape((-1,len(w['columns'])))
    if len(x)!=w['rows'] or len(w['columns'])!=60 or x[0,0]!=0 or x[-1,0]!=100e-9 or not np.all(np.diff(x[:,0])>0) or not np.isfinite(x).all() or not w['all_requested_witnesses_exported']:raise ValueError('Incomplete sampled export')
    h=r['history_stimulus']
    for t in [r['cycles'][0]['pre_compare']['time_s'],h['first_motion_native']['time_s'],h['first_plateau_native']['time_s'],h['second_actual_precompare']['time_s']]:
        if not np.any(x[:,0]==t):raise ValueError('Required native witness absent from display export')
    q=h['second_actual_precompare']
    if abs(q['input_diff_v']-(q['absolute_TOPP_v']-q['absolute_TOPN_v']))>1e-15:raise ValueError('Absolute second input mismatch')
    return dict(case=case,run=run,r=r,x=x,cols=w['columns'],cfg=cfg,
        provenance=dict(collection_files=len(receipt['files']),collection_bytes=receipt['total_bytes'],managed_recipe_sha256=managed_hash,
            result_sha256=sha((p/'derived/result.json').read_bytes()),export_sha256=w['sha256'],export_rows_sha256=w['uncompressed_sha256'],
            frozen_measurement_sha256=r['measurement_sha256'],all_native_metrics=True,two_raw_passes_match=True))


def summary(item):
    r=item['r'];h=r['history_stimulus'];q=h['second_actual_precompare'];end=h['first_plateau_native']
    enddiff=end['TOPP_v']-end['TOPN_v'];endcm=(end['TOPP_v']+end['TOPN_v'])*.5;target=h['nominal_second_diff_v']
    c0,c1=r['cycles'][:2]
    return dict(case=item['case'],provenance=item['provenance'],native_points=r['native_points'],export_rows=r['waveform']['rows'],export_policy=r['waveform'],
        actual_first_pre_diff_v=c0['pre_compare']['input_diff_v'],nominal_second_diff_v=target,
        actual_second_pre_TOPP_v=q['absolute_TOPP_v'],actual_second_pre_TOPN_v=q['absolute_TOPN_v'],actual_second_pre_diff_v=q['input_diff_v'],actual_second_pre_CM_v=q['input_cm_v'],
        actual_second_in_LSB=q['input_diff_v']/item['cfg']['history_case']['LSB_v'],target_difference_v=q['input_diff_v']-target,
        first_plateau_native_time_s=end['time_s'],first_plateau_diff_v=enddiff,first_plateau_CM_v=endcm,
        first_plateau_target_difference_v=enddiff-target,postplateau_to_precompare_diff_change_v=q['input_diff_v']-enddiff,
        postplateau_to_precompare_CM_change_v=q['input_cm_v']-endcm,postplateau_to_precompare_time_s=q['time_s']-end['time_s'],
        second_write_delay_s=c1['write_delay_from_clock_half_s'][0],first_write_delay_s=c0['write_delay_from_clock_half_s'][0],
        native_events=r['event_counts'],protocol_eight_pass=r['protocol_eight_pass'],history_assessment_valid=r['history_assessment_valid'],
        stimulus=h,selected_mos_count=165,selected_mos_pair_count=990,selected_mos_screen_exceeded_records=r['selected_mos_screen_exceeded_records'],
        full_mos_screen_complete=False,full_mos_screen_exceeded_records=None,native_warning_codes=r['native_warning_codes'],
        interpretation='Nominal charge target minus physical TOP input is not a comparator threshold/offset measurement. No normalization or intrinsic-C attribution.')


def plotting():
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15})
    return plt


def get(item,name):return item['x'][:,item['cols'].index(name)]


def decision_figure(item,stats,dest,plt):
    r=item['r'];x=item['x'];roles=item['cfg']['roles'];fig,ax=plt.subplots(4,2,figsize=(12.5,9),sharex='col')
    t=x[:,0];dm=(get(item,'topp')-get(item,'topn'))*1e3
    for j,c in enumerate(r['cycles'][:2]):
        rise=c['clock_rise_half_s'];fall=(c['clock_fall_half_s']-rise)*1e9;time=(t-rise)*1e9
        high=fall+.60;mask=(time>=-.12)&(time<=high)
        values=[get(item,roles['clock']),dm,get(item,'xdut.comp_p')-get(item,'xdut.comp_n'),get(item,roles['write'])]
        for row,v in enumerate(values):ax[row,j].plot(time[mask],v[mask],color=BLUE,lw=1.25)
        target=item['cfg']['history_case']['nominal_diff_by_cycle_v'][j]*1e3
        ax[1,j].axhline(target,color=GRAY,ls='--',lw=.9)
        pre=c['pre_compare'];pt=(pre['time_s']-rise)*1e9;actual=pre['input_diff_v']*1e3
        ax[1,j].plot(pt,actual,'o',color=ORANGE,ms=4)
        ax[1,j].set_title('actual pre: %+.6f mV'%actual,loc='right',color=ORANGE,fontsize=8,pad=3)
        wt=(c['writes'][0]['time_s']-rise)*1e9
        for a in ax[:,j]:a.axvline(wt,color=BLUE,ls=':',lw=.8);a.axvline(fall,color=GRAY,ls='--',lw=.8);a.set_xlim(-.12,high)
        for row in [0,3]:ax[row,j].set_ylim(-.06,1.01)
        ax[2,j].axhline(0,color=GRAY,lw=.7)
        ax[0,j].set_title('First b7: large %s, write %d'%('negative' if c['expected_DATA']==0 else 'positive',c['writes'][0]['DATA_bit']) if j==0 else 'Second b6: measured small input, write %d'%c['writes'][0]['DATA_bit'],loc='left',fontsize=11)
        ax[-1,j].set_xlabel('Time from this CLK half-level rise (ns)')
    for i,label in enumerate(['Compare CLK (V)','TOPP − TOPN (mV)','COMP_P − COMP_N (V)','Write PHI_W (V)']):ax[i,0].set_ylabel(label)
    fig.suptitle('Native feedback accepts the opposite-polarity small residual',fontsize=14,y=.99)
    fig.text(.5,.948,'TT · 0.9 V · 27°C · real T28 MOM load · one bottom-plate charge step · TOP never re-clamped',ha='center',fontsize=9)
    fig.text(.5,.018,'Sampled native display: stride 8 + witnesses; all numerical records use every native point. Each column has its own CLK time origin.\n'
        'Dashed input line: nominal charge target. Vertical blue: write half-rise; gray: CLK half-fall. Static D=0 alone does not prove a write.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.10,right=.98,top=.90,bottom=.10,hspace=.25,wspace=.24)
    fig.savefig(dest/'first_second_decisions.png',dpi=170,bbox_inches='tight',pad_inches=.12);plt.close(fig)


def charge_figure(item,stats,dest,plt):
    r=item['r'];h=r['history_stimulus'];t=item['x'][:,0]*1e9;q=h['second_actual_precompare'];plateau=h['first_plateau_native']
    step0=h['events']['first_armed_clock_fall10']['time_s']*1e9+.9;step1=plateau['time_s']*1e9;pre=q['time_s']*1e9
    lo=r['cycles'][0]['pre_compare']['time_s']*1e9-.05
    fig,ax=plt.subplots(4,2,figsize=(12.6,10),sharex='col')
    dm=(get(item,'topp')-get(item,'topn'))*1e3;cm=((get(item,'topp')+get(item,'topn'))*.5-.45)*1e3
    windows=[(lo,pre+.015),(step1-.005,pre+.015)]
    for j,(left,right) in enumerate(windows):
        mask=(t>=(left if j==0 else step1))&(t<=pre)
        for n,color,label in [('bot_p',BLUE,'P bit bottoms'),('bot_n',ORANGE,'N bit bottoms')]:ax[0,j].plot(t[mask],(get(item,n)[mask]-.45)*1e3,color=color,lw=1.15,label=label)
        ax[1,j].plot(t[mask],dm[mask],color=BLUE,lw=1.2);ax[1,j].axhline(h['nominal_second_diff_v']*1e3,color=GRAY,ls='--',lw=.8)
        ax[2,j].plot(t[mask],cm[mask],color=BLUE,lw=1.2);ax[2,j].axhline(0,color=GRAY,ls='--',lw=.8)
        for n,color,label in [('xdut.xcomp.mninp:2',BLUE,'Input P gate port'),('xdut.xcomp.mninn:2',ORANGE,'Input N gate port')]:ax[3,j].plot(t[mask],get(item,n)[mask]*1e6,color=color,lw=1.1,label=label)
        for a in ax[:,j]:
            a.axvspan(step0,step1,color=ORANGE,alpha=.07,lw=0);a.axvline(step1,color=GREEN,ls=':',lw=.9)
            a.set_xlim(left,right)
        ax[1,j].plot(pre,q['input_diff_v']*1e3,'o',color=ORANGE,ms=4)
        ax[-1,j].set_xlabel('Absolute time (ns)')
    for row,label in enumerate(['Bottom offset from 450 mV (mV)','TOPP − TOPN (mV)','TOP common-mode −450 mV (mV)','Input gate-port current (µA)']):ax[row,0].set_ylabel(label)
    ax[0,0].legend(loc='upper left',fontsize=8);ax[3,0].legend(loc='lower right',fontsize=8)
    ax[0,0].set_title('First decision → reset → controlled charge step',loc='left',fontsize=11)
    ax[0,1].set_title('Plateau → next CLK≤0.1VDD witness; TOP floating',loc='left',fontsize=10)
    ax[1,1].text(.97,.75,'target difference: %+.3f µV'%((q['input_diff_v']-h['nominal_second_diff_v'])*1e6),transform=ax[1,1].transAxes,ha='right',va='top',fontsize=8,color=ORANGE)
    fig.suptitle('The small-input target difference is present in TOP before the decision',fontsize=14,y=.99)
    fig.text(.5,.95,'TT · 0.9 V · 27°C · fixed dummy rails · equal/opposite bit-bottom step · no ideal TOP source after 18.1 ns',ha='center',fontsize=9)
    fig.text(.5,.018,'Display is sampled native rows (stride 8 + event/extrema/recovery witnesses); all markers/metrics use full-native records.\n'
        'Orange: programmed bottom transition; green: plateau. Right ends at CLK≤0.1VDD witness; final point may include the next CLK ramp.\n'
        'Gate-current curves are display data, not a new phase-integrated charge extraction. Target difference is not comparator offset.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.11,right=.98,top=.90,bottom=.11,hspace=.25,wspace=.25)
    fig.savefig(dest/'charge_and_recovery.png',dpi=170);plt.close(fig)


def report(item,a,dest,paired_complete=False):
    r=item['r'];h=r['history_stimulus'];q=h['second_actual_precompare'];c0,c1=r['cycles'][:2]
    motion=h['first_motion_native'];plateau=h['first_plateau_native']
    name='负大残差→正小残差' if item['case']=='negative_to_positive' else '正大残差→负小残差'
    paired_note='成对汇总见[对称历史报告](../paired_report.md)，各组仍使用原样实际输入。' if paired_complete else '对称组尚未合并。到达后比较实际小残差、共模、相位和写入延迟；输入残差的正负不对称仍不能直接叫作比较器offset。'
    text=f'''# {name}：单组记录

**在声明的TT测试台中，前次相反判决没有阻止第二次小输入正确写入。** 首轮实际差模{a['actual_first_pre_diff_v']*1e3:+.6f}mV；第二次实际输入为{a['actual_second_pre_diff_v']*1e3:+.6f}mV（{a['actual_second_in_LSB']:+.6f}LSB），共模{a['actual_second_pre_CM_v']*1e3:.6f}mV。第二次写入延迟{a['second_write_delay_s']*1e9:.6f}ns，极性与实际输入一致。八次写入/更新/复位、token7→0和D历史均正确。

![两次相反判决](first_second_decisions.png)

## 目标差异出现在哪里

| 原生见证 | 时刻/ns | 实际差模/mV | 共模/mV |
| --- | ---: | ---: | ---: |
| 首轮比较前 | {c0['pre_compare']['time_s']*1e9:.6f} | {c0['pre_compare']['input_diff_v']*1e3:+.6f} | {c0['pre_compare']['input_cm_v']*1e3:.6f} |
| 首次检测到阶跃运动，进度{motion['progress']*100:.4f}% | {motion['time_s']*1e9:.6f} | {(motion['TOPP_v']-motion['TOPN_v'])*1e3:+.6f} | {(motion['TOPP_v']+motion['TOPN_v'])*500:.6f} |
| 底板首次达到最终平台 | {plateau['time_s']*1e9:.6f} | {a['first_plateau_diff_v']*1e3:+.6f} | {a['first_plateau_CM_v']*1e3:.6f} |
| 第二次比较前 | {q['time_s']*1e9:.6f} | {a['actual_second_pre_diff_v']*1e3:+.6f} | {a['actual_second_pre_CM_v']*1e3:.6f} |

![电荷搬运与浮置恢复](charge_and_recovery.png)

实际底板为{q['actual_bottom_P_v']*1e3:.6f}/{q['actual_bottom_N_v']*1e3:.6f}mV，符合程序的等量反向阶跃；以255/256名义电容比独立计算，目标仍为{q['independent_ideal_diff_at_actual_bottoms_v']*1e3:+.6f}mV、450mV共模。第二次实际差模与名义目标相差**{a['target_difference_v']*1e6:+.3f}µV**。

偏差在阶跃平台时已经有{a['first_plateau_target_difference_v']*1e6:+.3f}µV；此后底板保持常值的{a['postplateau_to_precompare_time_s']*1e9:.6f}ns内，差模又变化{a['postplateau_to_precompare_diff_change_v']*1e6:+.3f}µV。输入在第二次判决前已经直接呈现这个电压差异，**这不是一次比较器翻转阈值/offset测量**。

名义计算仅含MOM权重比，实际还含输入门端电荷、寄生和前轮反冲恢复。仅由这些端点不能把偏差定量分给某个电容或晶体管，也没有逐原生点的独立窗口电荷积分。约200µV只相当于58.0078mV名义大阶跃的约0.344%，在相减形成小残差时会明显放大相对偏差；不能据此提取0.344%的输入电容或补偿输入。

## 相位和范围

首轮内部reset90在{c0['first_reset_ready_native']['time_s']*1e9:.6f}ns出现，早于阶跃；底板在{plateau['time_s']*1e9:.6f}ns进入平台，早于第二次比较前见证。移动阶段CLK/PHI_W/PHI_U最大值分别{h['during_motion_max_v']['clock']*1e6:.3f}/{h['during_motion_max_v']['write']*1e6:.3f}/{h['during_motion_max_v']['update']*1e6:.3f}µV，SAMPLE_INT为0。初始化控制始终关闭，平台后的初始化支路最大电流{h['initializer_current_after_step_max_abs_a']:.3e}A。TOP没有被理想源重新钳位。

这是1457MOS、18个真实MOM及既有接收链的条件测试，参考首级输出仍采用32节点有限切口；底板阶跃为TB受控电荷刺激。外部SAMPLE_INT关闭沿和器件/RC未改。没有PVT、噪声、失配或全ADC精度结论。165MOS/990项选定端压为{r['selected_mos_screen_exceeded_records']}超限；**完整1457MOS/8742项波形筛查未完成，完整超限数为null**。原生CMI和全部日志保留。

指标使用全部{r['native_points']:,}原生点；图使用{r['waveform']['rows']:,}展示点（每{r['waveform']['baseline_native_index_stride']}个原生点加{r['waveform']['witness_time_count']}个见证时刻）。完整导出0–100ns，图内裁剪范围按横轴；没有从取样曲线重新计算指标。比较前快照定义为最后一个CLK≤0.1VDD的点，下一时钟边沿可能已经耦合到输入；它不是“时钟完全静止”的保证。延迟不能直接与此前实际输入不同的固定+0.25LSB结果解释为纯历史效应。

{paired_note}
'''
    (dest/'report.md').write_text(text,encoding='utf-8')


def components(item,a):
    r=item['r'];h=r['history_stimulus'];x=item['x'];t=x[:,0]
    bp,bn=get(item,'bot_p'),get(item,'bot_n');motion=h['first_motion_native']['time_s']
    choices=np.flatnonzero((t<motion)&(np.abs(bp-.45)<=1e-12)&(np.abs(bn-.45)<=1e-12))
    if not len(choices):raise ValueError('No exported pre-motion native witness')
    j=int(choices[-1]);end=h['first_plateau_native'];k=np.flatnonzero(t==end['time_s'])
    if len(k)!=1:raise ValueError('Native plateau witness absent')
    k=int(k[0]);A=float(get(item,'topp')[j]-get(item,'topn')[j]);B=a['first_plateau_diff_v'];C=a['actual_second_pre_diff_v']
    nominal0=h['nominal_initial_diff_v'];nominal1=h['nominal_second_diff_v']
    nominal_step=255./256.*float((bp[k]-bp[j])-(bn[k]-bn[j]))
    pre=A-nominal0;during=(B-A)-nominal_step;after=C-B;drive=nominal_step-(nominal1-nominal0)
    if abs(pre+during+after+drive-(C-nominal1))>1e-15:raise ValueError('Voltage ledger does not close')
    return dict(A=dict(time_s=float(t[j]),diff_v=A,cm_v=float((get(item,'topp')[j]+get(item,'topn')[j])*.5),
            bottom_P_v=float(bp[j]),bottom_N_v=float(bn[j]),gap_to_first_motion_s=float(motion-t[j]),
            selection='Last EXPORTED original-native row with bit bottoms still450mV before first detected motion; not guaranteed last accepted raw point'),
        B=dict(time_s=end['time_s'],diff_v=B,cm_v=a['first_plateau_CM_v'],source='Full-native first-plateau witness'),
        C=dict(time_s=h['second_actual_precompare']['time_s'],diff_v=C,cm_v=a['actual_second_pre_CM_v'],source='Full-native CLK<=0.1VDD precompare witness'),
        initial_setpoint_error_v=a['actual_first_pre_diff_v']-nominal0,postfirst_to_A_change_v=A-a['actual_first_pre_diff_v'],
        pre_step_state_term_v=pre,actual_A_to_B_transfer_v=B-A,nominal_A_to_B_transfer_v=nominal_step,
        A_to_B_net_transfer_difference_v=during,B_to_C_recovery_v=after,drive_realization_remainder_v=drive,total_target_difference_v=C-nominal1,
        method='Signed voltage endpoint bookkeeping. During term includes continuing state recovery/input gate charge during the A-to-B window; no isolated C or phase-charge integral.',
        phase_charge_integrals_computed=False,capacitance_ratio_extracted=False,comparator_offset_measured=False)


def paired_decisions(items,plt):
    fig,ax=plt.subplots(4,2,figsize=(12.5,9),sharex='col')
    for j,(item,a) in enumerate(items):
        r=item['r'];c=r['cycles'][1];roles=item['cfg']['roles'];t=(item['x'][:,0]-c['clock_rise_half_s'])*1e9
        mask=(t>=-.12)&(t<=2.95);color=BLUE if j==0 else ORANGE
        signals=[get(item,roles['clock']),(get(item,'topp')-get(item,'topn'))*1e3,
            get(item,'xdut.comp_p')-get(item,'xdut.comp_n'),get(item,roles['write'])]
        for row,v in enumerate(signals):ax[row,j].plot(t[mask],v[mask],color=color,lw=1.25);ax[row,j].set_xlim(-.12,2.95)
        pre=c['pre_compare'];px=(pre['time_s']-c['clock_rise_half_s'])*1e9
        ax[1,j].axhline(a['nominal_second_diff_v']*1e3,color=GRAY,ls='--',lw=.8)
        ax[1,j].plot(px,a['actual_second_pre_diff_v']*1e3,'o',color=GREEN,ms=4)
        ax[1,j].set_title('actual pre: %+.6f mV'%(a['actual_second_pre_diff_v']*1e3),loc='right',fontsize=8,pad=3)
        wt=a['second_write_delay_s']*1e9;fall=(c['clock_fall_half_s']-c['clock_rise_half_s'])*1e9
        for p in ax[:,j]:p.axvline(wt,color=color,ls=':',lw=.8);p.axvline(fall,color=GRAY,ls='--',lw=.8)
        for row in [0,3]:ax[row,j].set_ylim(-.06,1.02)
        ax[2,j].set_ylim(-1.02,1.02);ax[2,j].axhline(0,color=GRAY,lw=.7)
        ax[3,j].text(.03,.9,'CLK→write %.3f ns'%wt,transform=ax[3,j].transAxes,fontsize=9)
        ax[0,j].set_title('Negative history → small positive' if item['case']=='negative_to_positive' else 'Positive history → small negative',loc='left',fontsize=11)
        ax[-1,j].set_xlabel('Time from second CLK half-rise (ns)')
    for row,label in enumerate(['Compare CLK (V)','Actual TOPP − TOPN (mV)','COMP_P − COMP_N (V)','Write PHI_W (V)']):ax[row,0].set_ylabel(label)
    fig.suptitle('Both opposite histories produce the correct next small-input write',fontsize=14,y=.99)
    fig.text(.5,.947,'TT · 0.9 V · 27°C · native feedback and T28 MOM load · actual voltages shown without sign/amplitude normalization',ha='center',fontsize=9)
    fig.text(.5,.018,'Sampled native display: stride 8 + event/extrema/recovery witnesses; event intervals and marker values use full-native records.\n'
        'Dashed input line: nominal charge target. Write delay includes comparator, receiver and valid/write paths; it is not an offset measurement.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.10,right=.98,top=.90,bottom=.10,hspace=.25,wspace=.24)
    fig.savefig(OUT/'paired_second_decisions.png',dpi=170);plt.close(fig)


def paired_components(items,ledger,plt):
    fig,ax=plt.subplots(3,2,figsize=(12.5,9.5))
    for j,((item,a),b) in enumerate(zip(items,ledger)):
        x=item['x'];t=(x[:,0]-b['B']['time_s'])*1e9;end=(b['C']['time_s']-b['B']['time_s'])*1e9
        mask=(t>=-.27)&(t<=end);color=BLUE if j==0 else ORANGE
        for node,c,label in [('bot_p',BLUE,'P bottoms'),('bot_n',ORANGE,'N bottoms')]:ax[0,j].plot(t[mask],(get(item,node)[mask]-.45)*1e3,color=c,lw=1.15,label=label)
        ax[0,j].axvspan(-.2,0,color=GRAY,alpha=.07,lw=0);ax[0,j].axvline(0,color=GREEN,ls=':',lw=.8)
        ax[0,j].set_xlim(-.27,end+.03);ax[0,j].set_xlabel('Time from first plateau B (ns)')
        values=np.array([b['pre_step_state_term_v'],b['A_to_B_net_transfer_difference_v'],b['B_to_C_recovery_v'],b['total_target_difference_v']])*1e6
        ax[1,j].bar(range(4),values,color=[BLUE,ORANGE,GREEN,GRAY],width=.65)
        ax[1,j].axhline(0,color=GRAY,lw=.7);ax[1,j].set_ylim(-330,330)
        ax[1,j].set_xticks(range(4),['Pre A','A→B','B→C','Total'])
        for n,v in enumerate(values):ax[1,j].annotate('%+.2f'%v,(n,v),xytext=(0,5 if v>=0 else -5),textcoords='offset points',ha='center',va='bottom' if v>=0 else 'top',fontsize=8)
        ax[1,j].set_xlabel('Voltage bookkeeping, not phase-charge integration')
        mask=(t>=0)&(t<=end);diff=get(item,'topp')-get(item,'topn')
        ax[2,j].plot(t[mask],(diff[mask]-a['nominal_second_diff_v'])*1e6,color=color,lw=1.2)
        ax[2,j].plot([0,end],[(b['B']['diff_v']-a['nominal_second_diff_v'])*1e6,(b['C']['diff_v']-a['nominal_second_diff_v'])*1e6],'o',color=GREEN,ms=4)
        ax[2,j].set_xlim(-.02,end+.03);ax[2,j].set_xlabel('Time from plateau B to precompare C (ns)')
        ax[0,j].set_title('Negative → positive' if item['case']=='negative_to_positive' else 'Positive → negative',loc='left',fontsize=11)
    for row,label in enumerate(['Bottom offset from 450 mV (mV)','Signed gap terms (µV)','After plateau: DM−target (µV)']):ax[row,0].set_ylabel(label)
    ax[0,0].legend(loc='lower right',fontsize=8)
    fig.suptitle('Pre-step state, net charge-transfer window and post-step recovery are distinct',fontsize=13,y=.99)
    fig.text(.5,.947,'A: last exported baseline-bottom native row · B: first plateau · C: second precompare CLK≤0.1VDD witness',ha='center',fontsize=9)
    fig.text(.5,.018,'Waveforms are stride-8 native export + witnesses. A is a sampled endpoint; its gap to first motion is reported (about 1.4–1.5 ps).\n'
        'B/C are full-native witnesses. A→B includes state recovery and input charge effects; bars do not isolate a capacitor, memory or offset.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.11,right=.98,top=.90,bottom=.095,hspace=.37,wspace=.24)
    fig.savefig(OUT/'paired_charge_components.png',dpi=170);plt.close(fig)


def paired(items,plt):
    if len(items)!=2:return
    ledger=[components(item,a) for item,a in items];paired_decisions(items,plt);paired_components(items,ledger,plt)
    text='''# 对称判决历史：两方向均完成，约200µV是输入电荷目标差异

**结论限于这个TT条件测试台：** 两组都在前次相反大残差判决后，对实际约±0.221585LSB的小输入正确写入；各有八次写入/更新/复位。实际TOP未重新钳位，也未按名义0.25LSB归一化。

![第二次判决成对波形](paired_second_decisions.png)

| 历史 | 实际第二次差模/mV | 共模/mV | CLK→写入/ns | 实际−名义目标/µV |
| --- | ---: | ---: | ---: | ---: |
'''
    for item,a in items:text+=f"| {'负→正' if item['case']=='negative_to_positive' else '正→负'} | {a['actual_second_pre_diff_v']*1e3:+.6f} | {a['actual_second_pre_CM_v']*1e3:.6f} | {a['second_write_delay_s']*1e9:.6f} | {a['target_difference_v']*1e6:+.3f} |\n"
    text+='''
实际小残差大小近似镜像；这不等于offset或history memory为零。两次写入延迟相差约7.63ps，包含比较器、接收与有效/写入链；没有按段量分或做阈值搜索，不能归为纯比较器阈值/再生差异。

## 用已有点区分三个阶段

![电荷阶段分解](paired_charge_components.png)

A取“首次运动前，底板仍为450mV的最后一个**已导出原生点**”；B是全原生记录的首个平台点；C是第二次比较前CLK≤0.1VDD的全原生见证。A不是声称的最后一个求解点，选点到首次运动相隔约1.4–1.5ps。

    C−名义小目标 = (A−名义大目标) + [(B−A)−名义步进] + (C−B)

实际底板实现与名义步进的剩余差仅为浮点舍入量，保留在JSON账目中。以下是端点电压账目，不是逐原生点相位电荷积分。

| 历史 | 阶跃前状态 A−初始目标/µV | A→B净转移偏差/µV | 平台后恢复 B→C/µV | 合计目标差/µV |
| --- | ---: | ---: | ---: | ---: |
'''
    for (item,a),b in zip(items,ledger):text+=f"| {'负→正' if item['case']=='negative_to_positive' else '正→负'} | {b['pre_step_state_term_v']*1e6:+.2f} | {b['A_to_B_net_transfer_difference_v']*1e6:+.2f} | {b['B_to_C_recovery_v']*1e6:+.2f} | {b['total_target_difference_v']*1e6:+.3f} |\n"
    text+='''
- **阶跃前项**包含初始设定偏差、首轮反冲与复位后电气恢复，不能单独称作memory。初始设定误差本身只有约±0.246µV。
- **A→B项**是实际端点电压变化与仅MOM权重预测的差。其间输入门电荷及既有恢复仍在变化，不能把整项等同纯电容耦合损失。
- **B→C项**是底板恒定后的实际恢复，约±4.32µV；末端见证也可能包含下一CLK边沿的早期耦合。

A→B实际差模转移分别约+57.731231/−57.731219mV，MOM权重的名义步进为±58.007813mV。这里称“端点有效转移”，不把它当成已经提取的静态电容比。

表格额外数字仅供复核，不代表亚容差的物理精度；子项也会随A的选点时刻改变。

| 历史 | A时刻/ns；距首次运动/ps | A差模/mV | B差模/mV | C差模/mV | A/B/C共模/mV |
| --- | --- | ---: | ---: | ---: | --- |
'''
    for (item,a),b in zip(items,ledger):text+=f"| {'负→正' if item['case']=='negative_to_positive' else '正→负'} | {b['A']['time_s']*1e9:.6f}；{b['A']['gap_to_first_motion_s']*1e12:.3f} | {b['A']['diff_v']*1e3:+.6f} | {b['B']['diff_v']*1e3:+.6f} | {b['C']['diff_v']*1e3:+.6f} | {b['A']['cm_v']*1e3:.6f} / {b['B']['cm_v']*1e3:.6f} / {b['C']['cm_v']*1e3:.6f} |\n"
    text+='''
因此，约200µV不能全归为history memory或offset。它已经体现在判决前的模拟TOP电压中。比较器阈值需要在已知实际输入、可比共模/历史条件下单独测量；本次只证明这两个实际小输入被正确接收。

## 边界与证据

TT、0.9V、27°C；1457MOS/18个原生MOM，原生异步反馈；TB仅监听事件并驱动位电容底板，dummy固定、TOP初始化后浮置。32个参考首级输出仍是有限切口。无PVT、失配、瞬态噪声或全ADC精度结论。

两组均为165MOS/990项选定端压0超限；完整1457MOS/8742项波形筛查仍未完成，完整超限数为null。原生CMI、日志与原始波形均保留；未追加仿真。

数值判决/端压指标使用各组全部原生点。图为stride8加事件/极值/恢复见证；端点账目明确使用A/B/C，未从取样电流重新提取电荷。各组原生日志、receipt与导出gzip/行SHA均复核。原始冻结包未改。
'''
    text+='\n'
    for item,a in items:
        text+=f"- {'负→正' if item['case']=='negative_to_positive' else '正→负'}：{a['native_points']:,}原生点，{a['export_rows']:,}展示行，{a['export_policy']['witness_time_count']}个见证时刻。\n"
    (OUT/'paired_report.md').write_text(text,encoding='utf-8')
    record=dict(cases=[a for item,a in items],voltage_components=ledger,endpoint_bookkeeping_only=True,
        phase_charge_integrals_computed=False,comparator_offset_measured=False,capacitance_ratio_extracted=False,
        actual_input_not_normalized=True,write_delay_difference_s=items[1][1]['second_write_delay_s']-items[0][1]['second_write_delay_s'])
    (OUT/'paired_summary.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cases',nargs='+',choices=list(CASES),default=['negative_to_positive']);args=parser.parse_args()
    plt=plotting();items=[]
    for case in args.cases:
        item=load(case);a=summary(item);dest=OUT/case;dest.mkdir(parents=True,exist_ok=True)
        (dest/'summary.json').write_text(json.dumps(a,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        decision_figure(item,a,dest,plt);charge_figure(item,a,dest,plt);report(item,a,dest,paired_complete=len(args.cases)==2);items.append((item,a))
        print('LOCAL_HISTORY_REVIEW',case,'native/export',a['native_points'],a['export_rows'],'second_actual_mV',a['actual_second_pre_diff_v']*1e3)
    paired(items,plt)


if __name__=='__main__':main()
