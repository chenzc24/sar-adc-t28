"""Compare completed local v2/hold2 native data; never change frozen inputs."""
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
DEST=HERE/'results/kickback_hold2_v1'
RUNS=['sar8audit-comp-kickback-tt-v2','sar8audit-comp-hold2-tt-v1']


def sha(b):return hashlib.sha256(b).hexdigest()


def load(run):
    base=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt_bytes=(base/'collection_receipt.json').read_bytes();receipt=json.loads(receipt_bytes)
    if receipt.get('skipped'):raise ValueError('Incomplete native collection')
    if receipt['status']['run_id']!=run:raise ValueError('Wrong collected run identity')
    total=0
    for item in receipt['files']:
        blob=(base/item['name']).read_bytes()
        if len(blob)!=item['bytes'] or sha(blob)!=item['sha256']:raise ValueError('Receipt mismatch: '+item['name'])
        total+=len(blob)
    if total!=receipt['total_bytes']:raise ValueError('Collection byte mismatch')
    raw_result=(base/'derived/result.json').read_bytes();r=json.loads(raw_result)
    simulation=json.loads((base/'simulation.state.json').read_bytes())
    analysis=json.loads((base/'analysis.state.json').read_bytes())
    if any(s['status']!='complete' or s['exit_code']!=0 for s in [simulation,analysis]):raise ValueError('Managed run incomplete')
    if not all(simulation['native'][k] for k in ['native_analysis_pass','zero_error_footer']):raise ValueError('Native completion not verified')
    log=(base/'spectre.out').read_bytes();text=log.decode('ascii')
    if log!=(base/'derived/spectre.original.log').read_bytes() or sha(log)!=r['original_simulator_log_sha256']:raise ValueError('Original log mismatch')
    if 'allpub' in text or not re.search(r'save\s+45\s+\(current\)',text) or not re.search(r'save\s+36\s+\(voltage\)',text):raise ValueError('Requested native saves not verified')
    accepted=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',text)[1])
    compressed=(base/'derived'/r['waveform']['file']).read_bytes()
    if sha(compressed)!=r['waveform']['sha256']:raise ValueError('Native gzip hash mismatch')
    blob=gzip.decompress(compressed)
    if sha(blob)!=r['waveform']['uncompressed_sha256']:raise ValueError('Uncompressed native hash mismatch')
    names=r['waveform']['columns'];x=np.frombuffer(blob,dtype='<f8').reshape((-1,len(names)))
    if len(x)!=r['native_points'] or len(x)!=accepted+1 or x[0,0]!=0 or x[-1,0]!=260e-9 or not np.all(np.diff(x[:,0])>0):raise ValueError('Native time/count mismatch')
    if not np.isfinite(x).all():raise ValueError('Nonfinite native waveform')
    for case in r['cycles']:
        if len(case['writes'])!=1 or case['DATA_matches_nominal_at_each_write']!=[True] or not case['late_D0_matches_nominal']:raise ValueError('Unexpected diagnostic decision')
        at=case['pre_compare']['time_s'];i=int(np.argmin(abs(x[:,0]-at)))
        for arm,suffix in [('evaluate','a'),('reset','b')]:
            vp=x[i,names.index('topp_'+suffix)];vn=x[i,names.index('topn_'+suffix)]
            observed=case['pre_compare']['arms'][arm]
            if abs(vp-vn-observed['diff_v'])>1e-15 or abs((vp+vn)*.5-observed['cm_v'])>1e-15:raise ValueError('Pre-compare metadata differs from native waveform')
    if sum(e['kind']=='write' for e in r['events'])!=6 or any(e['kind']=='reset_arm_write' for e in r['events']):
        raise ValueError('Unexpected accepted write outside the six comparisons')
    return dict(run=run,r=r,x=x,names=names,provenance=dict(files=len(receipt['files']),bytes=total,
        registered_recipe_sha256=receipt['status']['registered']['recipe_hash'],measurement_sha256=r['measurement_sha256'],
        receipt_sha256=sha(receipt_bytes),result_sha256=sha(raw_result),log_sha256=sha(log),
        waveform_sha256=r['waveform']['sha256'],waveform_uncompressed_sha256=r['waveform']['uncompressed_sha256'],
        accepted_native_steps=accepted,native_rows=len(x),raw_ascii_downloaded=False))


def second_record(item):
    c=item['r']['cycles'][1];pre=c['pre_compare'];v=pre['arms']['evaluate'];quiet=pre['arms']['reset']
    return dict(run=item['run'],precompare_native_time_s=pre['time_s'],diff_v=v['diff_v'],cm_v=v['cm_v'],
        target_diff_v=c['configuration']['target_diff_v'],target_cm_v=c['configuration']['target_cm_v'],
        target_diff_error_v=c['pre_compare_target_error_v'],target_cm_error_v=v['cm_v']-.45,
        evaluate_minus_reset_diff_v=v['diff_v']-quiet['diff_v'],evaluate_minus_reset_cm_v=v['cm_v']-quiet['cm_v'],
        initialized_native_time_s=c['initialized']['time_s'],after_release_native_time_s=c['after_release']['time_s'],
        initializer_v=pre['init_control_v'],reset90=pre['reset_all_above_90pct'],
        write_delay_s=c['write_delay_from_clock_half_s'][0],raw_resolution_delay_s=c['raw_resolution_delay_native_s'],
        observed_DATA=c['writes'][0]['DATA_bit'],late_D0=c['late_D0_bit'],write_count=len(c['writes']),
        DATA_matches_expected=c['DATA_matches_nominal_at_each_write'],
        writes=c['writes'])


def main():
    items=[load(run) for run in RUNS]
    old,new=[second_record(d) for d in items]
    # The first comparison is unchanged; record this causal control explicitly.
    c0=[d['r']['cycles'][0] for d in items]
    first_same=c0[0]['pre_compare']==c0[1]['pre_compare'] and c0[0]['writes']==c0[1]['writes']
    summary=dict(generated_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        provenance={d['run']:d['provenance'] for d in items},first_comparison_observations_identical=first_same,
        second_comparison=dict(v2=old,hold2=new,
            delta_diff_v=new['diff_v']-old['diff_v'],delta_cm_v=new['cm_v']-old['cm_v'],
            delta_write_delay_s=new['write_delay_s']-old['write_delay_s'],
            delta_raw_resolution_delay_s=new['raw_resolution_delay_s']-old['raw_resolution_delay_s']),
        timing=dict(compare_starts_s=[20e-9,60e-9],compare_spacing_s=40e-9,
            first_reset_complete_clock_edge_s=32.1e-9,next_compare_start_s=60e-9,
            reset_low_interval_before_compare2_s=27.9e-9,continuous_input_hold_s=[18.1e-9,84e-9],
            phases=[dict(name='First reset/hold',start_s=32.1e-9,end_s=60e-9),
                    dict(name='Second comparison including clock fall',start_s=60e-9,end_s=72.1e-9),
                    dict(name='Second reset/hold',start_s=72.1e-9,end_s=84e-9)]),
        six_correct_writes={d['run']:True for d in items},
        selected_MOS_pairs={d['run']:dict(records=len(d['r']['mos_pair_extrema']),exceeded=d['r']['mos_screen_exceeded_records']) for d in items},
        native_warnings={d['run']:d['r']['native_warning_codes'] for d in items},
        boundaries=items[1]['r']['boundaries'],acceptance_pass=None,
        next_suggestion='Reproduce two held-input comparisons at the existing ADC actual bit/reset cadence, at one fixed condition;40ns/27.9ns here cannot establish short-bit recovery. No new package or experiment prepared.')
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    figure(items,new,DEST/'hold2_comparison.png')
    report(summary,DEST/'report.md')
    print('LOCAL_HOLD2_COMPARISON',DEST,'hold2_collection_bytes',items[1]['provenance']['bytes'])


def figure(items,new,path):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.16})
    fig,ax=plt.subplots(5,2,figsize=(12,10.5),sharex='col',gridspec_kw={'hspace':.18,'wspace':.22})
    colors=['#156582','#c75a31'];labels=['v2: initialize again','hold2: retain charge']
    windows=[(43.8,60.),(59.9,62.5)]
    for item,color,label in zip(items,colors,labels):
        t=item['x'][:,0]*1e9;get=lambda n:item['x'][:,item['names'].index(n)]
        diff_error=(get('topp_a')-get('topn_a')-.0017578125)*1e6
        cm_error=((get('topp_a')+get('topn_a'))*.5-.45)*1e3
        for j,(lo,hi) in enumerate(windows):
            mask=(t>=lo)&(t<=hi);ts=t[mask]
            for row,node in [(0,'cmp_clk'),(1,'cinit'),(4,'xactive.xctrl.phi_w')]:
                ax[row,j].plot(ts,get(node)[mask],color=color,label=label,lw=1.3)
                ax[row,j].set_ylim(-.06,.98)
            ax[2,j].plot(ts,diff_error[mask],color=color,label=label,lw=1.3)
            ax[3,j].plot(ts,cm_error[mask],color=color,label=label,lw=1.3)
    for j,(lo,hi) in enumerate(windows):
        for row in [2,3]:ax[row,j].axhline(0,color='#777777',ls='--',lw=.8)
        for axes in ax[:,j]:axes.set_xlim(lo,hi)
        ax[-1,j].set_xlabel('Time (ns)')
    for row,label in enumerate(['Compare CLK (V)','Input initialization (V)','Differential error (µV)','CM offset from450mV (mV)','Accepted-write clock (V)']):
        ax[row,0].set_ylabel(label)
    ax[2,1].set_ylabel('Differential error (µV)')
    ax[3,1].set_ylabel('CM offset (mV)')
    ax[0,0].set_title('Hold before comparison 2: omitted initialization',loc='left',fontsize=10)
    ax[0,1].set_title('Second comparison and write',loc='left',fontsize=10)
    for axes in ax[:,0]:axes.axvspan(44,58.1,color='#c75a31',alpha=.07)
    for axes in ax[:,1]:axes.axvspan(60,60.1,color='#8292a0',alpha=.12)
    at=new['precompare_native_time_s']*1e9
    for row,value,unit in [(2,new['target_diff_error_v']*1e6,'µV'),(3,new['target_cm_error_v']*1e3,'mV')]:
        ax[row,0].plot(at,value,'o',color=colors[1],ms=3)
        ax[row,0].annotate('%+.3f %s'%(value,unit),xy=(at,value),xytext=(-8,10),
            ha='right',textcoords='offset points',color=colors[1],fontsize=8)
    ax[1,0].legend(loc='upper right',fontsize=8,framealpha=.85)
    fig.suptitle('Retained charge before the second decision',fontsize=14,y=.985)
    fig.text(.5,.955,'TT · 0.9 V · 27°C · frozen N4/rx2 + T28 MOM · +0.25 LSB target for both comparisons · native points per run',ha='center',fontsize=9)
    fig.text(.5,.02,'Compare starts20/60ns:40ns spacing,27.9ns low/reset interval before compare2. Fixed ideal bottom rails and clock.\n'
        'Initializer off18.1–84ns in hold2. No transient noise, mismatch or PEX. No interpolation between runs.',ha='center',fontsize=8,color='#555555')
    fig.subplots_adjust(left=.095,right=.98,top=.92,bottom=.085)
    fig.savefig(path,dpi=170);plt.close(fig)


def report(s,path):
    c=s['second_comparison'];a,b=c['v2'],c['hold2']
    rows=[('| 比较前差模 | %.6f mV | %.6f mV |'%(a['diff_v']*1e3,b['diff_v']*1e3)),
          ('| 相对+0.25LSB目标的差模残差 | %+.3f µV | %+.3f µV |'%(a['target_diff_error_v']*1e6,b['target_diff_error_v']*1e6)),
          ('| 比较前共模 | %.6f mV | %.6f mV |'%(a['cm_v']*1e3,b['cm_v']*1e3)),
          ('| 写入延迟（交点插值记录） | %.6f ns | %.6f ns |'%(a['write_delay_s']*1e9,b['write_delay_s']*1e9)),
          '| DATA / 晚期D0 | 1 / 1 | 1 / 1 |']
    text=f'''# 第二次比较继续使用保持电荷

取消44–58.1ns的第二次输入初始化后，第二次比较仍正确写入D0。
60ns比较前保留的差模残差为 **{b['target_diff_error_v']*1e6:+.3f}µV**，共模为
**{b['cm_v']*1e3:.3f}mV**。此前0.348mV复位差模峰值已大幅恢复；仍留下约0.300mV共模偏移。

![保持阶段与第二次判决对照](hold2_comparison.png)

| 第二次比较 | v2：重新初始化 | hold2：继续保持 |
| --- | ---: | ---: |
{chr(10).join(rows)}

相对v2，不再初始化使差模改变 **{c['delta_diff_v']*1e6:+.3f}µV**、共模改变
**{c['delta_cm_v']*1e3:+.3f}mV**。实际输入仍为正，第二次DATA和晚期D0均为1；
两组各六次比较均只有一次正确写入。写入延迟都约1.608ns，插值差仅
{c['delta_write_delay_s']*1e12:.3f}ps；未做数值收敛/统计验证，不据此判断速度变化。

## 时间与物理含义

- 比较器的时钟下降复位保留；取消的是输入重新初始化，不能理解为取消比较器复位。
- hold2在18.1ns断开初始化后持续保持到84ns。32.1–60ns是第一次复位/保持，
  60–72.1ns包含第二次比较，72.1–84ns是第二次复位/保持。
- 两次比较开始相隔 **40ns**；第一次时钟落稳到下一次比较有 **27.9ns**。
  本次证明的是这一较长恢复时间下的两次同极性比较，不能证明真实SAR较短bit间隔可接受，
  也不覆盖一帧连续8次比较或更接近零的输入。
- 第一次比较的输入和写入记录在两组中完全一致；差异出现在取消再初始化之后。
  这是电荷历史的单变量对照，不是完整ADC采样链验证。

## 数据与边界

两组完整receipt、原生日志及压缩/解压原生波形SHA均复核。hold2回收10文件、11,907,280B，
100,644个原生点对应100,643个接受步，完整覆盖260ns。保存36条电压和45条电流。
两组原生日志均为0 errors、7 warnings；保留SPECTRE-16881、SFE-3031和PDK/环境提示。
228个N4/rx2选定端压检查均无超限，范围不等于全部934个MOS。

底板/参考、电源、时钟仍理想，输入初始化为临时理想导通支路。未加入真实采样开关关断寄生、
参考动态切换、噪声、失配或版图寄生。上述结果不代表整机合格；acceptance_pass仍为空。

## 唯一后续建议

按已冻结合龙版本的 **实际bit时序与复位间隔**，复现一次不再初始化的连续两次比较，仍保持
固定底板和同一输入条件。先确认真实短间隔下第二次输入残留与判决，再讨论更大范围验证。
目前只提出建议，未新增包或仿真。

完整数值与散列见summary.json；原有v2和hold2输入包均未修改。
'''
    path.write_text(text,encoding='utf-8')


if __name__=='__main__':main()
