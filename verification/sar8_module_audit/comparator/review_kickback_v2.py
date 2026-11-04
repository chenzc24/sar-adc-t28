"""Local SHA-bound phase analysis/figure; frozen inputs and remote stay untouched."""
from __future__ import annotations
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'output/managed_execution/runs/sar8audit-comp-kickback-tt-v2/collected'
DEST=HERE/'results/kickback_v2'


def sha(blob):return hashlib.sha256(blob).hexdigest()


def peak_record(t,v,indices):
    if not len(indices):raise ValueError('Missing native phase coverage')
    low=int(indices[np.argmin(v[indices])]);high=int(indices[np.argmax(v[indices])])
    greatest=low if abs(v[low])>=abs(v[high]) else high
    return dict(min_v=float(v[low]),min_time_s=float(t[low]),max_v=float(v[high]),max_time_s=float(t[high]),
                max_abs_v=float(abs(v[greatest])),signed_at_max_abs_v=float(v[greatest]),max_abs_time_s=float(t[greatest]))


def main():
    receipt=json.loads((SOURCE/'collection_receipt.json').read_bytes());total=0
    if receipt.get('skipped'):raise ValueError('Incomplete collection')
    for item in receipt['files']:
        blob=(SOURCE/item['name']).read_bytes()
        if sha(blob)!=item['sha256'] or len(blob)!=item['bytes']:raise ValueError('Collected file differs: '+item['name'])
        total+=len(blob)
    if total!=receipt['total_bytes']:raise ValueError('Collection size mismatch')
    result_blob=(SOURCE/'derived/result.json').read_bytes();r=json.loads(result_blob)
    state=json.loads((SOURCE/'simulation.state.json').read_bytes())
    analysis=json.loads((SOURCE/'analysis.state.json').read_bytes())
    if state['status']!='complete' or analysis['status']!='complete' or not state['native']['zero_error_footer'] or not state['native']['native_analysis_pass']:
        raise ValueError('Native/managed completion not verified')
    log=(SOURCE/'spectre.out').read_bytes()
    if log!=(SOURCE/'derived/spectre.original.log').read_bytes() or sha(log)!=r['original_simulator_log_sha256']:
        raise ValueError('Original log hash mismatch')
    logtext=log.decode('ascii')
    if ('allpub' in logtext or 'SPECTRE-8281' in logtext or
        not re.search(r'save\s+45\s+\(current\)',logtext) or
        not re.search(r'save\s+36\s+\(voltage\)',logtext)):
        raise ValueError('Exact save acceptance missing')
    accepted=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',logtext)[1])
    packed=(SOURCE/'derived'/r['waveform']['file']).read_bytes()
    if sha(packed)!=r['waveform']['sha256']:raise ValueError('Compressed native table hash mismatch')
    blob=gzip.decompress(packed)
    if sha(blob)!=r['waveform']['uncompressed_sha256']:raise ValueError('Native table hash mismatch')
    columns=r['waveform']['columns'];x=np.frombuffer(blob,dtype='<f8').reshape((-1,len(columns)))
    if len(x)!=accepted+1 or len(x)!=r['native_points'] or not np.isfinite(x).all():raise ValueError('Native row count/value mismatch')
    col=lambda name:x[:,columns.index(name)]
    t=x[:,0]
    if t[0]!=0 or t[-1]!=260e-9 or not np.all(np.diff(t)>0):raise ValueError('Native endpoint/time ordering mismatch')
    da=col('topp_a')-col('topn_a');db=col('topp_b')-col('topn_b')
    ca=(col('topp_a')+col('topn_a'))*.5;cb=(col('topp_b')+col('topn_b'))*.5
    records=[];first_delta=None
    for case in r['cycles']:
        c=case['configuration'];start=c['start_s'];fall=start+12e-9;end=c['clock_fall_end_s']
        pre=int(np.searchsorted(t,start,side='right')-1)
        diff=(da-db)-(da[pre]-db[pre]);cm=(ca-cb)-(ca[pre]-cb[pre])
        if c['index']==0:first_delta=(diff,cm)
        if len(case['writes'])!=1 or case['DATA_matches_nominal_at_each_write']!=[True] or not case['late_D0_matches_nominal']:
            raise ValueError('Expected six diagnostic decisions were not reproduced')
        write=case['writes'][0]['estimated_half_vdd_time_s']
        wi=int(np.searchsorted(t,write))
        phases={}
        for name,lo,hi in [('before_write',start,write),('high_after_write',write,fall),
                           ('clock_fall',fall,end),('post_reset',end,c['next_acquire_s'])]:
            indices=np.flatnonzero((t>=lo)&(t<hi))
            phases[name]=dict(requested_interval_s=[lo,hi],native_interval_s=[float(t[indices[0]]),float(t[indices[-1]])],
                native_points=len(indices),differential_A_minus_reset=peak_record(t,diff,indices),
                common_mode_A_minus_reset=peak_record(t,cm,indices))
        mask=(t>=start)&(t<=end)
        for name,reported in case['gate_charge_C'].items():
            integrated=float(np.trapezoid(col(name)[mask],t[mask]))
            if abs(integrated-reported)>1e-24:raise ValueError('Native gate-charge integral differs')
        record=dict(index=c['index'],nominal_input_diff_v=c['target_diff_v'],
            actual_precompare_diff_v=float(da[pre]),actual_precompare_cm_v=float(ca[pre]),
            precompare_target_error_v=float(da[pre]-c['target_diff_v']),
            reset_ready90=case['pre_compare']['reset_all_above_90pct'],initializer_v=float(col('cinit')[pre]),
            expected_bit=c['expected_DATA'],observed_DATA_bit=case['writes'][0]['DATA_bit'],late_D0_bit=case['late_D0_bit'],
            write_delay_s=case['write_delay_from_clock_half_s'][0],raw_resolution_delay_s=case['raw_resolution_delay_native_s'],
            write_estimated_time_s=write,first_native_after_write_s=float(t[wi]),
            input_diff_at_first_native_after_write_v=float(da[wi]),input_cm_at_first_native_after_write_v=float(ca[wi]),
            differential_disturbance_after_write_v=float(diff[wi]),common_mode_disturbance_after_write_v=float(cm[wi]),
            phases=phases,gate_charge_to_clock_fall_end_C=case['gate_charge_C'])
        records.append(record)
    kcl={}
    for node,item in r['node_kcl'].items():
        maximum=float(np.abs(col('kcl:'+node)).max())
        if abs(maximum-item['max_abs_a'])>1e-20:raise ValueError('KCL peak differs from all-native table')
        incident=item.get('incident_at_max_a',{})
        if incident and abs(abs(sum(incident.values()))-maximum)>1e-18:raise ValueError('Incident terminal-current sum differs')
        kcl[node]=dict(max_abs_a=maximum,time_s=item['time_s'],
            incident_l1_at_max_a=sum(abs(v) for v in incident.values()))
    summary=dict(run_id='sar8audit-comp-kickback-tt-v2',registered_recipe_sha256='033415e34b80fa7ed2bb8d4f2baf1a0582ca7e6772f5a1a118d3dabc79302db2',
        generated_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        provenance=dict(collection_receipt_sha256=sha((SOURCE/'collection_receipt.json').read_bytes()),files=len(receipt['files']),bytes=total,
            result_sha256=sha(result_blob),native_log_sha256=sha(log),wave_compressed_sha256=sha(packed),wave_uncompressed_sha256=sha(blob),
            raw_native_sha256_from_managed_analyzer=r['raw_sha256'],raw_native_downloaded=False),
        native=dict(points=len(x),accepted_steps=accepted,stop_s=float(t[-1]),max_gap_s=float(np.diff(t).max()),
            saved_voltages=36,saved_currents=45,zero_error_footer=True,warnings=r['native_warning_codes'],
            effective_settings=r['native_effective_settings'],version=r['simulator_version']),
        six_expected_writes_correct=True,extra_reset_arm_write_events=sum(e['kind']=='reset_arm_write' for e in r['events']),
        selected_MOS_pairs=len(r['mos_pair_extrema']),selected_pair_exceedances=r['mos_screen_exceeded_records'],
        screening_scope=r['mos_pair_scope'],node_kcl=kcl,cycles=records,boundaries=r['boundaries'],
        acceptance_pass=None,qualification='Only six deterministic TT inputs under fixed ideal bottoms and temporary initialization; no ADC qualification',
        next_single_variable=dict(action='Omit only the44--58.1ns reinitialization pulse on both arms',
            fixed='All devices, references, compare clocks/endpoints, input-source targets and numerical settings',
            reason='First two inputs share the positive target. The second decision then tests retained charge after a previous comparison/reset without re-clamping TOP.',
            status='recommendation_only_not_prepared_or_dispatched'))
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    figure(t,col,da,first_delta,records[0],DEST/'timing_phases.png')
    report(summary,DEST/'report.md')
    print('KICKBACK_LOCAL_REVIEW',DEST,'native_rows',len(x),'complete_collection_bytes',total)


def figure(t,col,da,deltas,first,path):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.16})
    fig,ax=plt.subplots(6,2,figsize=(12,12),sharex='col',sharey='row',gridspec_kw={'hspace':.17,'wspace':.1})
    diff,cm=deltas
    windows=[(19.9,22.8),(31.9,34.05)]
    colors=['#156582','#cf5a32']
    for j,(lo,hi) in enumerate(windows):
        sel=(t*1e9>=lo)&(t*1e9<=hi);ns=t[sel]*1e9
        ax[0,j].plot(ns,col('cmp_clk')[sel],color=colors[0],lw=1.5)
        ax[0,j].set_ylim(-.06,.98)
        ax[1,j].plot(ns,da[sel]*1e3,color=colors[0],label='Held input differential')
        ax[1,j].axhline(first['nominal_input_diff_v']*1e3,color='#777777',ls='--',lw=1,label='Initial target')
        ax[1,j].set_ylim(1.34,2.11)
        ax[2,j].plot(ns,cm[sel]*1e3,color='#71478a',label='Evaluate minus reset')
        ax[2,j].axhline(0,color='#777777',ls='--',lw=.8);ax[2,j].set_ylim(-9.3,.6)
        for side,color in [('p',colors[0]),('n',colors[1])]:
            ax[3,j].plot(ns,col('xactive.xcomp.mnin'+side+':2')[sel]*1e6,color=color,label='Input '+side.upper(),lw=1.2)
            ax[4,j].plot(ns,col('xactive.comp_'+side)[sel],color=color,label='COMP_'+side.upper(),lw=1.2)
        ax[3,j].axhline(0,color='#777777',lw=.7)
        ax[5,j].plot(ns,col('xactive.xctrl.phi_w')[sel],color='#2f8052',lw=1.5)
        ax[5,j].set_ylim(-.06,.98);ax[5,j].set_xlim(lo,hi);ax[5,j].set_xlabel('Time (ns)')
        edge=20 if j==0 else 32
        for axes in ax[:,j]:axes.axvspan(edge,edge+.1,color='#7f91a1',alpha=.12)
    visible=((t*1e9>=windows[0][0])&(t*1e9<=windows[0][1]))|((t*1e9>=windows[1][0])&(t*1e9<=windows[1][1]))
    gate_values=np.concatenate([col('xactive.xcomp.mnin'+side+':2')[visible]*1e6 for side in ['p','n']])
    output_values=np.concatenate([col('xactive.comp_'+side)[visible] for side in ['p','n']])
    gate_pad=(gate_values.max()-gate_values.min())*.08
    for j in range(2):
        ax[3,j].set_ylim(gate_values.min()-gate_pad,gate_values.max()+gate_pad)
        ax[4,j].set_ylim(min(-.06,float(output_values.min())-.04),max(1.,float(output_values.max())+.06))
    labels=['Compare CLK (V)','Top differential (mV)','CM change A − reset (mV)',
            'Input gate current (µA)','Comparator outputs (V)','Actual write pulse (V)']
    for axes,label in zip(ax[:,0],labels):axes.set_ylabel(label)
    ax[0,0].set_title('Decision: clock rise and first write',loc='left',fontsize=11)
    ax[0,1].set_title('Reset: clock fall and recovery',loc='left',fontsize=11)
    for row in [1,2,3,4]:ax[row,0].legend(loc='best',fontsize=7,framealpha=.8)
    write=first['write_estimated_time_s']*1e9
    for axes in ax[:,0]:axes.axvline(write,color='#2f8052',ls=':',lw=1)
    ax[0,0].text(write+.025,.13,'Write',color='#2f8052',fontsize=8)
    for j,phase in [(0,'before_write'),(1,'post_reset')]:
        rec=first['phases'][phase]['differential_A_minus_reset'];at=rec['max_abs_time_s'];i=int(np.argmin(np.abs(t-at)))
        ax[1,j].plot(at*1e9,da[i]*1e3,'o',color='#b34832',ms=3)
        ax[1,j].annotate('%+.3f mV'% (rec['signed_at_max_abs_v']*1e3),
            xy=(at*1e9,da[i]*1e3),xytext=(7,8),textcoords='offset points',fontsize=8,color='#a53c29')
    at=first['first_native_after_write_s'];i=int(np.argmin(np.abs(t-at)))
    ax[2,0].plot(at*1e9,cm[i]*1e3,'o',color='#71478a',ms=3)
    ax[2,0].annotate('%.3f mV at write'%(cm[i]*1e3),xy=(at*1e9,cm[i]*1e3),
        xytext=(-8,13),textcoords='offset points',ha='right',fontsize=8,color='#71478a')
    fig.suptitle('Held-CDAC comparator: first +0.25 LSB decision and reset',fontsize=14,y=.985)
    fig.text(.5,.958,'TT · 0.9 V · 27°C · frozen N4/rx2 · T28 MOM bank, 256 units per side · original native samples',ha='center',fontsize=9)
    fig.text(.5,.018,'Fixed ideal bottom rails and clock; initialization disconnected at18.1ns. No transient noise, mismatch or PEX.\n'
        'Gate current is positive from TOP into the input MOS. Shading marks the unchanged0.1ns clock ramps.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.105,right=.985,top=.93,bottom=.075)
    fig.savefig(path,dpi=170);plt.close(fig)


def report(s,path):
    records=s['cycles'];p=lambda phase,field:max(c['phases'][phase][field]['max_abs_v'] for c in records)
    rows=['| 次序 | 比较前差模 (mV) | 写码 | 写入延迟 (ns) |', '| --- | ---: | ---: | ---: |']
    rows += ['| %d | %+.3f | %d | %.3f |'%(c['index']+1,c['actual_precompare_diff_v']*1e3,c['observed_DATA_bit'],c['write_delay_s']*1e9) for c in records]
    first=records[0];wlo=min(c['write_delay_s'] for c in records)*1e9;whi=max(c['write_delay_s'] for c in records)*1e9
    doc=f'''# 比较器接实际 CDAC 电容：TT 结果

六次 ±0.25 LSB 比较均以正确极性写入D0，写入延迟 **{wlo:.3f}–{whi:.3f} ns**。
本次确认的是固定底板、理想时钟下的比较器诊断；尚不能据此判定整机合格。

![判决与复位分相位波形](timing_phases.png)

## 结果怎么看

1. **判决期已有反冲。** 写入前差模 A−reset 最大约 **{p('before_write','differential_A_minus_reset')*1e3:.3f} mV**，
   相当于0.0405 LSB，约为本次1.758mV初始差模的16.2%。首次写入时输入差模约
   {first['input_diff_at_first_native_after_write_v']*1e3:.3f}mV，仍保持正确极性。
2. **共模下降不是复位后才发生。** 首次写入前共模已下降约
   **{first['common_mode_disturbance_after_write_v']*1e3:.3f} mV**；复位沿附近最深约−8.781mV，之后逐步恢复。
   两侧输入管从顶板抽取相近电荷，与共模下降一致；总端口电流尚未拆成Cgs/Cgd等内部成分。
3. **复位另有一次差模扰动。** 时钟下降后、下一次初始化前，最大差模 A−reset 约
   **{p('post_reset','differential_A_minus_reset')*1e3:.3f} mV**，大于判决期峰值。它在当前写入之后出现，
   不能直接称为当前码字错误；也不能忽略它对同一采样电荷后续比较的影响。

所有扰动均以各周期比较前的实际电压为基准，减去同一原生时间网格上的始终复位对照臂。
它们是顶板电压扰动，不是自动等效成ADC码字误差、offset或随机噪声。

{chr(10).join(rows)}

延迟从比较时钟0.5VDD上升交点到实际写入脉冲0.5VDD上升交点。DATA在该估计交点的值
与目标一致，晚期D0也一致；这不构成寄存器setup/hold签核。比较前差模偏离目标最多
小于0.01µV，两臂输入初始化接近一致；这是本次确定性数值检查，不是输入精度规格。

## 可信度与边界

- 10文件、11,855,029B的回收SHA全部复核；100,668个原生点对应100,667个接受步，覆盖0–260ns。
  保存项确认为36条电压、45条电流；v1的忽略保存项/allpub问题消失。
- 四个顶板节点最大KCL残差约{max(x['max_abs_a'] for x in s['node_kcl'].values())*1e12:.2f}pA；
  已核对全时段波形峰值、峰值处11项端电流求和及逐周期输入栅电荷积分。
- 228个N4/rx2选定端压检查无超限，范围不包含全部934个MOS。原生日志仍有7条warning，
  包括SPECTRE-16881初值求解、SFE-3031以及PDK/环境提示；随后完成原生PASS且0 errors。
  图中保留了COMP_P约1.017V的复位过冲；无CMI提示不等于全器件可靠性签核。
- 输入端负载为原始T28 MOM几何和倍率；底板、参考、电源与时钟理想。输入仅在初始化期通过
  理想10Ω支路建立，评估时完全断开。未包含真实参考开关/驱动、采样开关关断寄生、动态底板切换、
  瞬态噪声、失配或版图寄生。

## 下一项单变量验证

建议仅取消两臂 **44–58.1ns那一次重新初始化脉冲**，保持器件、参考、电源、比较时钟、端点
和输入源目标不变。前两次输入本来同为+0.25LSB；第二次比较将直接使用经历过一次比较/复位的
同一份保持电荷。检查第二次比较前残差、共模、码字和延迟，判断本次复位扰动是否带入下一次决策。
这比再次独立初始化更接近SAR一帧内重复比较的电荷历史，仍隔离参考驱动问题。
目前仅提出建议，未准备或提交新仿真。

数值与完整散列见同目录summary.json；原始v2输入包保持冻结。
'''
    path.write_text(doc,encoding='utf-8')


if __name__=='__main__':main()
