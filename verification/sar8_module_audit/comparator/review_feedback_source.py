"""Local completed-source result review and sampled-native timing figures."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np
import review_kickback_actual as earlier

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'results/feedback_v2_reduce1'
RUN='sar8audit-comp-feedback-v2-reduce1'
SOURCE='sar8audit-comp-feedback-tt-v2'
SOURCE_HASH='d56adca4380107296e7bd8aebe5fadd39f419aa579e8a0235bc53284b2b5cb90'
TARGET=.0017578125
BLUE='#166b86';ORANGE='#c55b33';GREEN='#258363';GRAY='#737980'


def sha(b):return hashlib.sha256(b).hexdigest()


def load():
    p=ROOT/'output/managed_execution/runs'/RUN/'collected'
    receipt=json.loads((p/'collection_receipt.json').read_bytes())
    if receipt.get('skipped') or receipt['total_bytes']!=7290320:raise ValueError('Incomplete/wrong result collection')
    for f in receipt['files']:
        b=(p/f['name']).read_bytes()
        if len(b)!=f['bytes'] or sha(b)!=f['sha256']:raise ValueError('Collection hash differs: '+f['name'])
    state=json.loads((p/'analysis.state.json').read_bytes())
    if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Analysis incomplete')
    r=json.loads((p/'derived/result.json').read_bytes())
    source=json.loads((p/'source_provenance.json').read_bytes())
    if source['run_id']!=SOURCE or source['recipe_hash']!=SOURCE_HASH or r['completed_source_recipe_hash']!=SOURCE_HASH:raise ValueError('Completed source binding differs')
    binding=HERE/'generated/feedback_v2_reduce_v1/source_binding.json'
    if r['source_binding_sha256']!=sha(binding.read_bytes()) or not r['two_full_native_passes_match'] or not r['source_raw_unchanged']:raise ValueError('Two-pass source integrity missing')
    if sha((p/'derived/spectre.original.log').read_bytes())!=r['original_simulator_log_sha256']:raise ValueError('Native log differs')
    log=(p/'derived/spectre.original.log').read_text(encoding='ascii')
    accepted=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1])
    if accepted+1!=r['native_points'] or r['native_points']!=156161:raise ValueError('Native point count differs')
    w=r['waveform'];b=(p/'derived'/w['file']).read_bytes()
    if sha(b)!=w['sha256']:raise ValueError('Complete export gzip hash differs')
    plain=gzip.decompress(b)
    if sha(plain)!=w['uncompressed_sha256']:raise ValueError('Export row hash differs')
    x=np.frombuffer(plain,dtype='<f8').reshape((-1,len(w['columns'])))
    if len(x)!=19924 or len(x)!=w['rows'] or not np.isfinite(x).all() or not np.all(np.diff(x[:,0])>0) or x[0,0]!=0 or x[-1,0]!=100e-9:raise ValueError('Export rows/time differ')
    if not w['all_requested_witnesses_exported'] or w['witness_time_count']!=475 or w['baseline_native_index_stride']!=8:raise ValueError('Sampled export policy differs')
    if r['event_counts']!=dict(clock=8,clock_fall=8,write=8,update=8,reset=8) or r['token_sequence']!=list(range(7,-1,-1)) or not r['protocol_eight_pass']:raise ValueError('Protocol differs')
    if r['selected_mos_pair_count']!=990 or r['selected_mos_screen_exceeded_records']!=0 or r['full_mos_screen_complete'] or r['full_mos_screen_exceeded_records'] is not None:raise ValueError('Stress scope differs')
    return r,x,w['columns'],dict(collection_bytes=receipt['total_bytes'],files=len(receipt['files']),result_sha256=sha((p/'derived/result.json').read_bytes()),
        export_sha256=w['sha256'],export_rows_sha256=w['uncompressed_sha256'],source_recipe_hash=SOURCE_HASH,
        source_binding_sha256=r['source_binding_sha256'],complete_analysis=True)


def records(r):
    rows=[]
    for c in r['cycles']:
        rise=c['clock_rise_half_s'];write=c['writes'][0]['time_s'];update=c['updates'][0]['time_s'];reset=c['resets'][0]['time_s']
        ready=c['first_reset_ready_native'];pre=c['pre_compare'];after=c['after_write_observation'];nxt=c['next_clock_rise_half_s']
        rows.append(dict(bit=c['token_bit'],clock_rise_ns=rise*1e9,write_delay_ns=(write-rise)*1e9,
            update_delay_ns=(update-rise)*1e9,clock_high_ns=c['native_clock_half_high_width_s']*1e9,
            write_to_reset_ns=(reset-write)*1e9,reset_to_clock_fall_ns=(c['clock_fall_half_s']-reset)*1e9,
            low_until_next_clock_ns=None if nxt is None else (nxt-c['clock_fall_half_s'])*1e9,
            reset90_delay_after_clock_fall_ns=(ready['time_s']-c['clock_fall_half_s'])*1e9,
            reset90_lead_before_next_clock_half_ns=None if nxt is None else (nxt-ready['time_s'])*1e9,
            pre_compare_native_time_ns=pre['time_s']*1e9,pre_diff_mV=pre['input_diff_v']*1e3,
            pre_diff_target_error_uV=(pre['input_diff_v']-TARGET)*1e6,pre_CM_mV=pre['input_cm_v']*1e3,
            reset90_diff_target_error_uV=(ready['input_diff_v']-TARGET)*1e6,reset90_CM_mV=ready['input_cm_v']*1e3,
            after_write_native_time_ns=after['time_s']*1e9,after_write_diff_target_error_uV=(after['input_diff_v']-TARGET)*1e6,
            after_write_CM_mV=after['input_cm_v']*1e3,after_write_boundary=c['after_write_observation_boundary'],
            correct_D_history=c['all_D_bits_match_token_history'],protocol_pass=c['protocol_pass']))
    return rows


def setup():
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15})
    return plt


def footer(fig,text,bottom=.085):
    fig.text(.5,.018,text,ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.105,right=.975,top=.90,bottom=bottom,hspace=.25,wspace=.25)


def comparison(r,x,cols,short,plt):
    fig,ax=plt.subplots(4,2,figsize=(12,8.7),sharex='col')
    get=lambda n:x[:,cols.index(n)];old=lambda n:short['x'][:,short['cols'].index(n)]
    short_cfg=short['r']['actual_interval_replay']['fixture_edges']
    for j in range(2):
        c=r['cycles'][j];rise=c['clock_rise_half_s']
        old_rise=short_cfg['rise%d_half_s'%(j+1)]
        native_time=(x[:,0]-rise)*1e9;old_time=(short['x'][:,0]-old_rise)*1e9
        values=[get('xdut.cmp_clk'),get('xdut.comp_p')-get('xdut.comp_n'),get('xdut.xctrl.data'),get('xdut.xctrl.phi_w')]
        prior=[old('cmp_clk'),old('xactive.comp_p')-old('xactive.comp_n'),old('xactive.xctrl.data'),old('xactive.xctrl.phi_w')]
        for time,signals,color,label in [(native_time,values,BLUE,'Native completion feedback'),(old_time,prior,ORANGE,'Borrowed fixed short pulse')]:
            mask=(time>=-.15)&(time<=3.15)
            for row,v in enumerate(signals):ax[row,j].plot(time[mask],v[mask],color=color,label=label,lw=1.25)
        forced=(short_cfg['fall%d_start_s'%(j+1)]-old_rise)*1e9
        native_reset=(c['resets'][0]['time_s']-rise)*1e9
        for a in ax[:,j]:
            a.axvline(forced,color=ORANGE,ls=':',lw=.8);a.axvline(native_reset,color=BLUE,ls=':',lw=.8)
            a.set_xlim(-.15,3.15)
        ax[1,j].axhline(.45,color=GRAY,ls='--',lw=.8)
        ax[0,j].set_title('First decision (native b7)' if j==0 else 'Second decision (native b6)',loc='left',fontsize=11)
        ax[-1,j].set_xlabel('Time from each CLK half-level rise (ns)')
    for row,label in enumerate(['Compare CLK (V)','COMP_P − COMP_N (V)','Receiver DATA (V)','Write PHI_W (V)']):
        ax[row,0].set_ylabel(label)
        for j in [0,1]:ax[row,j].set_ylim(-.06,1.01)
    ax[0,0].legend(loc='lower left',fontsize=8)
    fig.suptitle('Completion feedback allows the small-input write before reset',fontsize=14,y=.99)
    fig.text(.5,.947,'TT · 0.9 V · 27°C · N4/rx2 · initial +0.25 LSB, floating held input · fixed CDAC bottom rails',ha='center',fontsize=9)
    footer(fig,'Native: every 8th native row + event/extrema/recovery witnesses; fixed-pulse run: all native rows. Metrics use all native points.\n'
        'Each column aligns its own CLK half-rise. Dotted: forced-off start / native RESET half-rise. Dashed 0.45 V: observation only.\n'
        'Control and receiver-load boundaries differ between fixtures; this is a diagnostic comparison, not a single-variable speed measurement.',bottom=.12)
    fig.savefig(OUT/'feedback_vs_forced.png',dpi=170);plt.close(fig)


def bit_timing(r,x,cols,rows,plt):
    fig,ax=plt.subplots(4,2,figsize=(13,10),gridspec_kw={'width_ratios':[1.45,1]})
    t=x[:,0]*1e9;mask=(t>=22.3)&(t<=60.3);get=lambda n:x[:,cols.index(n)]
    for row,(node,label) in enumerate([('xdut.cmp_clk','Compare CLK'),('xdut.xctrl.phi_w','Write PHI_W'),('xdut.phi_u','Update PHI_U'),('xdut.xctrl.xtim.clock_reset','CLOCK_RESET')]):
        a=ax[row,0];a.plot(t[mask],get(node)[mask],color=BLUE,lw=1.05)
        a.set_ylim(-.06,1.05);a.set_xlim(22.3,60.3);a.set_ylabel(label+' (V)')
        for i,c in enumerate(r['cycles']):
            lo=c['clock_rise_half_s']*1e9;hi=(c['next_clock_rise_half_s'] or 60.1e-9)*1e9
            if i%2==0:a.axvspan(lo,hi,color=GRAY,alpha=.07,lw=0)
            if row==0:a.text((lo+hi)*.5,.98,'b'+str(c['token_bit']),ha='center',va='top',fontsize=8)
        if row<3:a.tick_params(labelbottom=False)
        else:a.set_xlabel('Absolute time (ns), displayed 22.3–60.3 ns')
    indices=np.arange(8)
    series=[('write_delay_ns','CLK rise → write (ns)'),('write_to_reset_ns','Write → RESET (ns)'),
        ('reset90_delay_after_clock_fall_ns','CLK fall → reset90 (ns)'),('reset90_lead_before_next_clock_half_ns','reset90 → next CLK (ns)')]
    limits=[(1.5,1.7),(.45,.55),(.5,.7),(2.0,2.35)]
    for row,(key,label) in enumerate(series):
        a=ax[row,1];v=np.array([np.nan if e[key] is None else e[key] for e in rows])
        a.plot(indices,v,'o-',color=BLUE,lw=1.2,ms=4);a.set_xlim(-.3,7.3);a.set_ylabel(label)
        a.set_ylim(*limits[row])
        a.set_xticks(indices,['b'+str(e['bit']) for e in rows]);a.tick_params(labelbottom=row==3)
        a.ticklabel_format(axis='y',style='plain',useOffset=False)
        if row==3:a.set_xlabel('Native token index (b0 has no next comparison)')
    ax[0,0].set_title('Eight native compare / write / update / reset pulses',loc='left',fontsize=11)
    ax[0,1].set_title('All-native event intervals',loc='left',fontsize=11)
    fig.suptitle('All eight token-indexed writes complete; reset follows each write',fontsize=14,y=.99)
    fig.text(.5,.953,'TT · 0.9 V · 27°C · initial +0.25 LSB, floating held input · fixed bottoms · finite reference-front output cut',ha='center',fontsize=9)
    footer(fig,'Waveforms: sampled native export (stride 8 + witnesses). Right-hand values: all 156,161 native points / native event brackets.\n'
        'reset90 is a 90% internal-level observation, not a qualified reset/setup/hold limit. Final b0 has no assigned next-clock lead.',bottom=.095)
    fig.savefig(OUT/'bit_write_reset.png',dpi=170);plt.close(fig)


def kickback(r,x,cols,plt):
    fig,ax=plt.subplots(3,2,figsize=(12.4,9.3),sharex='col');get=lambda n:x[:,cols.index(n)]
    diff=(get('topp')-get('topn'))*1e3;cm=((get('topp')+get('topn'))*.5-.45)*1e3
    for j in range(2):
        c=r['cycles'][j];rise=c['clock_rise_half_s'];time=(x[:,0]-rise)*1e9
        pre=c['after_write_observation'];pt=(pre['time_s']-rise)*1e9
        nxt=(c['next_clock_rise_half_s']-rise)*1e9;fall=(c['clock_fall_half_s']-rise)*1e9
        write=(c['writes'][0]['time_s']-rise)*1e9;ready=c['first_reset_ready_native'];rt=(ready['time_s']-rise)*1e9
        mask=(time>=-.15)&(time<=pt)
        ax[0,j].plot(time[mask],diff[mask],color=BLUE,lw=1.25)
        ax[1,j].plot(time[mask],cm[mask],color=BLUE,lw=1.25)
        for node,color,label in [('xdut.xcomp.mninp:2',BLUE,'Input P gate port'),('xdut.xcomp.mninn:2',ORANGE,'Input N gate port')]:
            ax[2,j].plot(time[mask],get(node)[mask]*1e6,color=color,lw=1.1,label=label)
        ax[0,j].axhline(TARGET*1e3,color=GRAY,ls='--',lw=.8);ax[1,j].axhline(0,color=GRAY,ls='--',lw=.8)
        for a in ax[:,j]:
            a.axvspan(0,fall,color=BLUE,alpha=.045,lw=0);a.axvspan(fall,pt,color=GRAY,alpha=.06,lw=0)
            a.axvline(write,color=BLUE,ls=':',lw=.8);a.axvline(fall,color=GRAY,ls='--',lw=.9)
            a.axvline(rt,color=GREEN,ls=':',lw=.9);a.set_xlim(-.15,nxt+.06)
        ax[0,j].plot([rt],[ready['input_diff_v']*1e3],'o',color=GREEN,ms=4)
        ax[0,j].annotate('%+.1f µV'%((ready['input_diff_v']-TARGET)*1e6),(rt,ready['input_diff_v']*1e3),xytext=(6,-22),textcoords='offset points',color=GREEN,fontsize=8)
        ax[0,j].plot([pt],[pre['input_diff_v']*1e3],'o',color=ORANGE,ms=4)
        ax[0,j].annotate('next pre: %+.3f µV'%((pre['input_diff_v']-TARGET)*1e6),(pt,pre['input_diff_v']*1e3),xytext=(-5,15),ha='right',textcoords='offset points',color=ORANGE,fontsize=8)
        ax[1,j].plot([pt],[(pre['input_cm_v']-.45)*1e3],'o',color=ORANGE,ms=4)
        ax[1,j].annotate('next pre: %.3f mV'%(pre['input_cm_v']*1e3),(pt,(pre['input_cm_v']-.45)*1e3),xytext=(-5,-22),ha='right',textcoords='offset points',color=ORANGE,fontsize=8)
        ax[0,j].set_title('b%d: evaluation and charge recovery'%c['token_bit'],loc='left',fontsize=11)
        ax[-1,j].set_xlabel('Time from this CLK half-level rise (ns)')
    for i,label in enumerate(['TOPP − TOPN (mV)','TOP common-mode −450 mV (mV)','Input gate-port current (µA)']):ax[i,0].set_ylabel(label)
    ax[2,0].legend(loc='lower right',fontsize=8)
    fig.suptitle('Internal reset readiness precedes full input-charge recovery',fontsize=14,y=.99)
    fig.text(.5,.95,'TT · 0.9 V · 27°C · native T28 MOM input · no input re-initialization between bits',ha='center',fontsize=9)
    footer(fig,'Sampled native export: stride 8 + witnesses. Marker values and event times use all-native records. Dashed targets: 1.7578125 mV / 450 mV.\n'
        'Vertical: write (blue), CLK half-fall (gray), internal reset90 (green). Blue shade: compare; gray shade: post-fall recovery.\n'
        'Trace ends at last native CLK ≤0.1 VDD before next compare. Held-charge recovery, not acquisition or final ADC error.',bottom=.12)
    fig.savefig(OUT/'top_kickback_recovery.png',dpi=170);plt.close(fig)


def report(r,rows,provenance):
    def span(key):
        v=[x[key] for x in rows if x[key] is not None];return min(v),max(v)
    text='''# 原生反馈：八次小输入判决完成

**结论限于本测试台：** TT、0.9V、27°C下，初始设定+0.25LSB（1.7578125mV）残差，18.1ns断开初始化后让MOM输入浮置保持，完成八次真实接收、写入、更新和复位；token依次为7→0，逐位D寄存器历史正确。D最终为全1是持续正残差的预期，不能当作ADC满量程码或全ADC精度结果。

## 为什么比人为短脉冲完整

![反馈与人为短脉冲](feedback_vs_forced.png)

旧诊断在CLK半电平上升后1.129/1.163ns就开始强制关断，没有产生PHI_W；关断后DATA短暂变高也不等于成功写入。恢复原生链后，接收有效信号经原生延时产生PHI_W，再经写入延时产生PHI_U，随后由CLOCK_RESET和SR触发时钟下降。写入正确性由后续原生D快照核对。
'''
    lo,hi=span('write_delay_ns');a,b=span('write_to_reset_ns');c,d=span('reset90_delay_after_clock_fall_ns');e,f=span('reset90_lead_before_next_clock_half_ns')
    text+=f'''
- CLK半电平上升→PHI_W半电平上升：**{lo:.3f}–{hi:.3f}ns**。
- PHI_W上升→CLOCK_RESET上升：**{a:.3f}–{b:.3f}ns**，随后CLK下降。
- CLK半电平下降→内部90%恢复：**{c:.3f}–{d:.3f}ns**；到下一CLK半电平上升还剩约**{e:.3f}–{f:.3f}ns**（末位没有下一次比较）。

这是原生接收/写入链触发复位的证据。新旧测试台的控制器、接收负载和时钟边沿也不同，因此不是严格单变量的速度比较。

该链仍含原生RC延时：PHI_U不是寄存器完成或参考建立的独立确认；QUIET加延时启动下一轮，也不检测TOP电荷是否恢复。

## 每位时序

![逐位写入和复位](bit_write_reset.png)

| bit | CLK→写入/ns | 写入→RESET/ns | CLK下降→reset90/ns | reset90→下一CLK/ns | 下一次比较前差模残留/µV |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for row in rows:
        lead='—' if row['reset90_lead_before_next_clock_half_ns'] is None else f"{row['reset90_lead_before_next_clock_half_ns']:.3f}"
        residue='末位无下一比较' if row['bit']==0 else f"{row['after_write_diff_target_error_uV']:+.3f}"
        text+=f"| {row['bit']} | {row['write_delay_ns']:.3f} | {row['write_to_reset_ns']:.3f} | {row['reset90_delay_after_clock_fall_ns']:.3f} | {lead} | {residue} |\n"
    text+='''
以上是观测事件间隔，不是已经签核的setup/hold或reset最小裕量。事件使用相邻原生点的0.5VDD交叉估计；reset90要求COMP_P/N、X/Y、PR/NR≥0.9VDD且RAW、DEC、CLK≤0.1VDD，它只是分析定义，并未作为控制检测器。下一比较前快照取最后一个CLK≤0.1VDD的原生点，该阈值也不是晶体管真正开始响应的边界。图中小于ps的差异不作物理速度结论。

## 顶板反冲与恢复

![顶板与输入栅电流](top_kickback_recovery.png)

比较期顶板共模明显下降，关断又产生输入栅端口电流和电荷恢复。这些动态并未消失。两路栅端口电流大体同向、同幅，对应以共模为主的反冲，关断反向电流对应回充；总端口电流不能直接拆成独立Cgd/Cgs贡献。两TOP节点的完整端口KCL最大残差约0.09pA。
'''
    first=rows[0];pre=rows[1]
    text+=f'''
第一轮内部达到reset90时，差模相对目标仍为**{first['reset90_diff_target_error_uV']:+.1f}µV**；下一次比较前已回到**{pre['pre_diff_target_error_uV']:+.3f}µV**，共模为**{pre['pre_CM_mV']:.3f}mV**。所以内部预充恢复不等于输入电荷完全恢复。图中的关断凹陷属于上一轮比较后的反冲/恢复，不是采样获取阶段的未建立，也不能直接换算成最终ADC误差。

## 条件与尚未证明的事

- 1457MOS测试台；18个原生CDAC MOM、固定底板/理想参考，临时初始化18.1ns后完全断开；仅SAMPLE_INT启动边界。
- 参考接收/捕获和BBM保留；32个参考驱动首级输出切口显式零外部扇出。没有真实参考切换和完整ADC负载耦合。
- 所选165MOS/990项端压无超限；其余1292MOS/7752项波形筛查未完成。原生CMI日志保留，不等于寿命签核。
- 本地VDD端口0–100ns能量为**{r['fixture_VDD_energy_j']*1e12:.6f}pJ**，包含本测试台控制/捕获负载，不能作为整机功耗结论。
- 无瞬态噪声、失配、PVT覆盖或版图寄生。原生日志的SFE-1131、VACOMP-2435和HOLD_P的Jacobian/DC提示均保留。

所有指标来自156,161个原生点。展示波形仅19,924行：每8个原生点取一行，并保留475个事件/极值/恢复见证时刻。完整导出范围0–100ns；图1按各自CLK沿对齐，图2裁出22.3–60.3ns，图3裁出首两轮比较与复位。图中连线只是显示连接，不是重新生成仿真数据。回收7文件/7,290,320B及gzip、解压行、绑定均复核；两遍原始数据SHA一致。

**下一项最必要验证：相反判决历史到小残差的恢复。** 在相同原生反馈/MOM负载下，用受控电荷变化构造“先负大差模、再正0.25LSB”及其对称历史，核对小输入极性、写入和复位恢复。这比连续八次同极性更能暴露上轮判决记忆；本次不建包或仿真。
'''
    (OUT/'report.md').write_text(text,encoding='utf-8')


def main():
    r,x,cols,provenance=load();short=earlier.load('sar8audit-comp-actual-tt-v1');rows=records(r)
    OUT.mkdir(parents=True,exist_ok=True)
    summary=dict(scope=r['scope'],provenance=provenance,native_points=r['native_points'],export=r['waveform'],
        protocol_eight_pass=r['protocol_eight_pass'],event_counts=r['event_counts'],per_bit=rows,
        node_kcl=r['node_kcl'],
        selected_mos_count=165,selected_mos_pairs=990,selected_mos_exceeded=0,full_mos_screen_complete=False,
        fixture_VDD_energy_j=r['fixture_VDD_energy_j'],native_warning_codes=r['native_warning_codes'],
        timing_and_recovery_definitions=r['measurement_methods'],old_forced_source=short['provenance'],
        comparison_limitation='Different control/output-load/clock boundaries; diagnostic sequencing comparison, not isolated speed improvement',
        acceptance_pass=None,next_validation='Opposite strong-decision history followed by small opposite residual, using controlled charge and native feedback')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    plt=setup();comparison(r,x,cols,short,plt);bit_timing(r,x,cols,rows,plt);kickback(r,x,cols,plt);report(r,rows,provenance)
    print('LOCAL_FEEDBACK_REVIEW',OUT,'protocol',r['protocol_eight_pass'],'figures3','native/export',r['native_points'],len(x))


if __name__=='__main__':main()
