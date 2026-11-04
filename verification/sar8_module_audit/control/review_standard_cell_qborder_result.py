"""Compact first-event QB gate-order comparison, preserving SR qualification gaps."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected, values

OWN,ROOT=base.OWN,base.ROOT
OUT=OWN/'standard_cell_qborder_v1/results'
P='xdut.xctrl.xtim.'
RUNS={
    'RB upper':('sar8audit-ctrl-stdcell-qbcap-ff-q2','ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0'),
    'Q upper':('sar8audit-ctrl-stdcell-qborder-ff-v1','c933758028b599adad5e3ab700a3e610424c2ab10133ccbaa33ead845fd87ce4')}


def main():
    data={tag:read_current_run(*ids) for tag,ids in RUNS.items()}
    reference=json.loads((OWN/'standard_cell_qborder_v1/source_observation_reference.json').read_bytes())
    report=dict(scope='FF0.99V/-40C first sample-close/reset-release; only X003 two NM gate controls swapped, same multi1 MID',
        whole_ADC_qualified=False,full_SR_set_reset_qualified=False,cases={})
    physical={}
    for tag,(table,names,r,m,proof) in data.items():
        if tag=='RB upper':
            if (reference['source_run'],reference['source_recipe_sha256'],reference['source_proof'])!=(*RUNS[tag],proof):
                raise ValueError('Complete-Q-fanout source reference provenance differs')
            gate_loads=dict(RB=reference['RB_gate_loads'],Q=reference['Q_gate_loads'])
        else:
            gate_loads=dict(RB=r['reset_stage_observations']['nodes']['RB'],Q=r['reset_stage_observations']['nodes']['CLOCK_Q'])
            for label,node in [('RB','XDUT.XCTRL.XTIM.XCLOCK.RB'),('CLOCK_Q','XDUT.XCTRL.XTIM.CLOCK_Q')]:
                actual=r['gate_order_native_gate_bindings'][label]
                if len(actual)!=4 or any(v['actual_node']!=node or v['actual'] not in names for v in actual.values()):
                    raise ValueError('Actual four-gate RB/Q native bindings differ')
        screen={}
        for path,item in m['standard_cell_experiment']['observed_mos'].items():
            for pair,label in item['six_pair_labels'].items():
                screen[path+'_'+pair]=dict(instance=path,pair=pair,endpoints=m['stress_voltage_pairs'][label],
                                         **r['full_history_voltage_stress'][label])
        if len(screen)!=606:
            raise ValueError('Expected606 actual device/pair records')
        physical[tag]=screen
        raw=collected(RUNS[tag][0]);sim=json.loads(raw['simulation.state.json'])
        ext={s:r['voltage_and_current_extrema'][P+s] for s in
             ['clock_reset','xclock.rb','xclock.qb','xclock.sn','xclock.x003.mid','clock_q','live','x020.n']}
        storage=r['QB_storage_observations'];q=ext['xclock.qb']
        metric=dict(minimum_inside_1mV_band=(abs(q['min']-.99)<=.001),
            minimum_time_s=q['min_time_s'],positive_peak_after_minimum=(q['max_time_s']>q['min_time_s'] and q['max']>.991),
            stable_time_s=storage['phases']['within_1mV_until_stop']['time_s']
                if storage['phases']['within_1mV_until_stop'] is not None else None)
        report['cases'][tag]=dict(proof=proof,node_extrema=ext,storage=storage,QB_metric_interpretation=metric,
            gate_loads=gate_loads,reset=r['reset_stage_observations'],coverage=r.get('gate_order_coverage'),
            actual_gate_bindings=r.get('gate_order_native_gate_bindings'),
            natural_initial_voltages_v={s:r['initial_values'][P+s] for s in
                ['clock_reset','xclock.rb','xclock.qb','xclock.sn','xclock.x003.mid','clock_q']},
            source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_source_energy'].items()},
            boundary_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_boundary_source_energy'].items()},
            R0_absorbed_j=r['full_history_resistor_energy']['absorbed_j'],
            physical_failed_pairs=sum(s['over_limit_native_points']>0 for s in screen.values()),
            native_library_current_ports=sum(len(v['actual']) for v in r['standard_cell_native_current_bindings'].values()),
            KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            native_effective_settings=sim['native']['effective_settings'])
    a,b=report['cases'].values();old,new=physical.values()
    if old.keys()!=new.keys() or a['native_effective_settings']!=b['native_effective_settings'] or b['native_library_current_ports']!=72:
        raise ValueError('Pair identity, settings or72 current bindings differ')
    report['physical_pair_changes']=dict(
        entered={k:dict(source=old[k],candidate=v,exceedance_v=v['max_abs_v']-.99) for k,v in new.items()
                 if v['over_limit_native_points'] and not old[k]['over_limit_native_points']},
        cleared={k:dict(source=v,candidate=new[k],exceedance_v=v['max_abs_v']-.99) for k,v in old.items()
                 if v['over_limit_native_points'] and not new[k]['over_limit_native_points']},
        interpretation='Actual same-instance pairs; MN0/MN1 gate nodes changed, so endpoint identity is recorded per case. Tiny results retained, no relaxed0.99V threshold.')
    report['change']=dict(
        negative_QB_droop_reduction_fraction=1-(.99-b['node_extrema']['xclock.qb']['min'])/(.99-a['node_extrema']['xclock.qb']['min']),
        VDD_net_work_reduction_fraction=1-b['source_energy_j']['VDD']/a['source_energy_j']['VDD'],
        RB_gate_exchange_increase_fraction=b['gate_loads']['RB']['event_exchange']['total_into_gate_devices_c']/a['gate_loads']['RB']['event_exchange']['total_into_gate_devices_c']-1.,
        reset_release_delta_s=b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']-a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s'])
    report['next_priority_validation']=dict(
        action='One dedicated loaded SR transient validation: reset/hold -> release -> set/hold -> reset from Qhigh/hold, retaining this candidate, real input drivers/fanout and unchanged ADC timing.',
        purpose='Verify full set and reset operation, reset priority and whether MID charge burden has moved to the opposite direction. First-event Qlow observations are not both-direction functional evidence.',
        observe='Q/QB/MID/RB state transitions, input load/charge, both-direction delay, all physical terminal stress and source work.',
        proposal_only=True,no_new_package_or_remote_job=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    figure(data);write_note(report)
    print(json.dumps(dict(change=report['change'],entered=len(report['physical_pair_changes']['entered']),
        cleared=len(report['physical_pair_changes']['cleared']),new_QB_metric=b['QB_metric_interpretation']),indent=2))


def figure(data):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'RB upper':'#63778b','Q upper':'#c76b2b'}
    fig,axes=plt.subplots(5,1,sharex=True,figsize=(10.5,10.3),layout='constrained')
    specs=[('xclock.qb','QB high-level deviation; green band = +/-1 mV',1e3,.99,'mV'),
           ('xclock.x003.mid','MID charges in baseline; discharges with Q upper',1.,0.,'V'),
           ('xclock.x003.cmid:1','Native MID current: positive charges, negative discharges',1e6,0.,'uA'),
           ('xclock.rb','RB: early undershoot remains',1.,0.,'V'),
           ('clock_reset','CLOCK_RESET: original edge overshoot remains',1.,0.,'V')]
    for ax,(node,title,scale,offset,unit) in zip(axes,specs):
        for tag,(table,names,*_) in data.items():
            ax.plot(table[:,0]*1e9,(values(table,names,P+node)-offset)*scale,color=colors[tag],lw=1.5,
                    ls='--' if tag=='RB upper' else '-',label=tag)
        ax.set(title=title,ylabel=unit);ax.grid(alpha=.18)
        ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[0].axhspan(-1,1,color='#a6c6ae',alpha=.22);axes[0].axhline(0,color='#888',ls=':',lw=.8)
    axes[0].set_ylim(-80,16);axes[0].legend(ncol=2,fontsize=9,loc='lower right')
    axes[1].set_ylim(-.02,.73);axes[2].axhline(0,color='#888',lw=.8)
    for ax in axes[3:]:
        ax.axhline(.99,color='#888',ls=':',lw=.8);ax.set_ylim(-.04,1.07)
    for parent,node,bounds,position,offset,ylim in [
        (axes[3],'xclock.rb',(41.075,41.082),[.31,.28,.28,.57],0.,(-21,2)),
        (axes[3],'xclock.rb',(41.09,41.12),[.67,.20,.30,.58],.99,(-.2,4.2)),
        (axes[4],'clock_reset',(41.071,41.078),[.37,.24,.34,.59],.99,(-1,23))]:
        zoom=parent.inset_axes(position)
        for tag,(table,names,*_) in data.items():
            zoom.plot(table[:,0]*1e9,(values(table,names,P+node)-offset)*1e3,color=colors[tag],lw=1.1,
                      ls='--' if tag=='RB upper' else '-')
        zoom.set(xlim=bounds,ylim=ylim,xticks=list(bounds));zoom.tick_params(labelsize=7)
        zoom.set_ylabel('mV' if not offset else 'mV above VDD',fontsize=7,labelpad=1)
        zoom.axhline(0,color='#888',lw=.6);zoom.grid(alpha=.15)
        zoom.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[-1].set(xlim=(41.065,41.18),xlabel='Original native time (ns); no waveform alignment or fitting')
    fig.suptitle('QB gate order greatly reduces droop; full SR cycle remains untested',fontsize=13)
    fig.supxlabel('FF | 0.99 V | -40 C | only X003 NM gates swapped | same PM, MID multi1 and PWL\nIdeal external supply/clock | first reset-release event | no Q transition or complete set/reset test | no noise/mismatch/PEX',fontsize=8)
    fig.savefig(OUT/'parallel_waveforms.png',dpi=165);plt.close(fig)


def write_note(report):
    a,b=report['cases'].values();ae,be=a['node_extrema'],b['node_extrema']
    charge=lambda c:c['storage']['post_RB90_exchange']['ports']['CMID:1']['signed_into_device_c']*1e15
    lines=[
        '# Q上／RB下：大幅减小QB下陷，完整SR功能仍未验证','',
        '对照为qbcap-q2的RB上／Q下；唯一变化是`XCLOCK.X003`两个NM栅控互换。PM、MID multi1、尺寸、真实负载及11份PWL保持。',
        '两组FF/0.99V/−40°C、同一首个采样关闭/复位释放窗口和原生求解设置。','',
        '| 指标 | RB上基线 | Q上候选 |','| --- | ---: | ---: |',
        '| QB最低值 | %.6fV | **%.6fV** |' % (ae['xclock.qb']['min'],be['xclock.qb']['min']),
        '| QB负向下陷，参考0.99V | %.3fmV | **%.3fmV** |' % ((.99-ae['xclock.qb']['min'])*1e3,(.99-be['xclock.qb']['min'])*1e3),
        '| QB正向尖峰，参考VDD | +%.3fmV | **+%.3fmV** |' % ((ae['xclock.qb']['max']-.99)*1e3,(be['xclock.qb']['max']-.99)*1e3),
        '| 最低值→此后始终±1mV¹ | %.3fps | **%.3fps** |' % (a['storage']['QB_minimum_to_within_1mV_s']*1e12,b['storage']['QB_minimum_to_within_1mV_s']*1e12),
        '| 各自RB90%%→稳定的MID净电荷² | +%.6ffC | **%.6ffC** |' % (charge(a),charge(b)),
        '| RB下冲 / 上冲，参考0/VDD | %.3f / +%.3fmV | %.3f mV / **+%.3fµV** |' % (ae['xclock.rb']['min']*1e3,(ae['xclock.rb']['max']-.99)*1e3,be['xclock.rb']['min']*1e3,(be['xclock.rb']['max']-.99)*1e6),
        '| RESET上冲，参考VDD | +%.3fmV | +%.3fmV |' % ((ae['clock_reset']['max']-.99)*1e3,(be['clock_reset']['max']-.99)*1e3),
        '| R下降→RB上升半轨延迟 | %.3fps | %.3fps |' % (a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12,b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12),
        '| VDD净供能，0..41.590786ns | %.7fpJ | %.7fpJ |' % (a['source_energy_j']['VDD']*1e12,b['source_energy_j']['VDD']*1e12),
        '| 物理端压超限对/606 | 245 | **237** |','',
        '¹新QB最低点0.989612V已经在±1mV内；随后仍有+10.185mV正峰，41.094366ns才持续回到带内。',
        '**16.442ps主要包含这个正峰的衰减，不能全称为负向下陷恢复时间。**旧70.734ps则包含实际的负向恢复。',
        '²两组各取自己的RB90%与稳定端点，积分窗不同；新值为放电，绝对端流交换同为0.153834fC，不是正负抵消制造的小值。','',
        '![QB、MID、电流及RB/RESET同轴对照](parallel_waveforms.png)','',
        '**路径改变。** 原RB驱动上管在RB90%时VGS约0.637V，持续由QB向MID供电。',
        '改为Q驱动上管后，同相位上管VGS/VDS约−0.034/0.963V，漏端总流−0.540µA；',
        'RB控制的下管VGS约0.892V、漏端抽走74.478µA，MID电容电流−67.150µA，主要转为向地放电。',
        'MID不再从约0.085V充到高电平，而是短暂到0.096V后降到接近0；这与目标储荷路径被隔开的解释一致。',
        '记录的是四端偏置与总端流，仍不作region、沟道/Cgd分解或长沟道公式推断。','',
        '**门负担不是消失。** RB的四栅门净交换2.224668→2.594256fC（增加16.61%），峰值323.230→328.206µA；',
        'Q完整四栅负担净交换−0.098514→+0.014329fC，最大绝对瞬态门流4.768→2.749µA。',
        '已核对实际RB接`X003.MN1`、Q接`MN0`及其余PM/buffer门，KCL按新节点连接求和；没有拿旧门电流套新拓扑。','',
        '**237对的变化组成。** 同一器件/端对比较是消失12、新增4，净减8；两管的栅端点本次已变，JSON保留两组实际端点。',
        '消失的12对为：原MN0 VGB的3.573mV超幅；8对2.278–49.726µV尾部超幅；另3对原超幅仅0.0647µV。',
        '新增4对均在X003：下管MN1的VGS/VGB各2.006µV、VGD为0.324µV；上管MN0的VDS为33.901µV。',
        '所有微小值及CMI均保留，筛查上限仍0.99V。当前大幅超限仍有LIVE−21.368、RESET+20.340、RB−18.074、X020.N+17.966mV，',
        'QB/SN正峰仍约+10.185/+11.345mV，**没有全部修好**。','',
        '**自然初态与功能边界。** 两组QB初始都约0.989999956V、Q约2.13µV；MID自然初值84.519/84.419mV，未强行对齐。',
        '初态只作观测，不能证明经过完整置位/复位。当前没有CLOCK_SET上升、Q翻转或从Q高开始的reset断言。',
        '五路源、七路理想边界源和R0功分别保存，VDD净供能不是完整ADC功耗。','',
        '**下一项最有价值的验证。** 做一次独立、带真实驱动和扇出的SR完整时序：reset/保持→释放→set/保持→从Q高复位/保持，',
        '同时观察Q/QB/MID/RB、双向延迟、输入负担与全部端压，并验证复位优先级。',
        '先确认栅位交换没有把储荷问题转移到另一方向，再继续修剩余尖峰。本轮只建议，不准备新包或启动远端。','',
        '候选9文件/9,440,613B、6051点，基线9文件/9,473,260B；SHA/大小、输入身份、PASS/END和72库端流均核对。',
        '全部节点最大KCL残差约3.94pA。外部电源/时钟理想，无噪声/失配/PEX；未判定完整SR、PVT或整机合格。',
        '[完整端对变化、偏置/电流/源功与门负担](comparison.json)。run `%s`，managed hash `%s`。' % RUNS['Q upper'],
        '本轮无远端操作、OA修改、新实验、共享计划/日志修改、采纳、commit或push。','']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
