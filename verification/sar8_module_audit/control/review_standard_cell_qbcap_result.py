"""Compact completed QB-cap q2 comparison; failed license attempt stays factual."""
import json
import os

import numpy as np
import yaml

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected, values
from review_standard_cell_rb_result import snapshot

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN/'standard_cell_qbcap_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {
    'MID multi2':('sar8audit-ctrl-stdcell-resetnand-ff-v1','7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d'),
    'MID multi1':('sar8audit-ctrl-stdcell-qbcap-ff-q2','ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0')}
FAILED = 'sar8audit-ctrl-stdcell-qbcap-ff-v1'
FAILED_HASH = 'e51627eebe5435844411e185bfd80f38eb3a2ded3796abf95bdfd4c955c5a7ee'


def retained_attempt():
    def record(run,h):
        item=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
        if item['recipe_hash']!=h or base.digest(json.dumps(item['recipe'],sort_keys=True,separators=(',',':')).encode())!=h:
            raise ValueError('Managed recipe identity differs')
        return item['recipe']
    old=record(FAILED,FAILED_HASH);new=record(*RUNS['MID multi1'])
    differences=[k for k in sorted(set(old)|set(new)) if old.get(k)!=new.get(k)]
    if differences!=['run_id']:
        raise ValueError('q2 electrical inputs/settings changed from failed v1')
    submitted_old=yaml.safe_load((ROOT/'management/recipes'/(FAILED+'.yaml')).read_text())
    submitted_new=yaml.safe_load((ROOT/'management/recipes'/(RUNS['MID multi1'][0]+'.yaml')).read_text())
    submitted_differences=[k for k in sorted(set(submitted_old)|set(submitted_new))
                           if submitted_old.get(k)!=submitted_new.get(k)]
    if submitted_differences!=['retry_provenance','run_id']:
        raise ValueError('Submitted q2 provenance differences changed')
    files=collected(FAILED);state=json.loads(files['simulation.state.json'])
    if (len(files)!=3 or sum(len(b) for b in files.values())!=6023 or state['status']!='failed'
            or state['exit_code']!=2 or b'SPECTRE-209' not in files['spectre.out']
            or state.get('native',{}).get('native_analysis_pass')):
        raise ValueError('Original license failure is not preserved as expected')
    return dict(run=FAILED,recipe_sha256=FAILED_HASH,receipt_files=3,receipt_bytes=6023,
        failed_stage='license checkout before circuit parsing',code='SPECTRE-209',exit_code=2,
        electrical_result_available=False,actual_q2=RUNS['MID multi1'][0],
        normalized_execution_recipe_differences=differences,submitted_recipe_differences=submitted_differences,
        retry_provenance=submitted_new['retry_provenance'],declared_electrical_inputs_identical=25)


def main():
    data={tag:read_current_run(*ids) for tag,ids in RUNS.items()}
    reference=json.loads((OWN/'standard_cell_qbcap_v1/source_storage_reference.json').read_bytes())
    report=dict(scope='FF0.99V/-40C only XCLOCK.X003.CMID multi2->1; same first-event history',
        retained_license_failure=retained_attempt(),cases={},whole_ADC_qualified=False,circuit_repair_claim=False)
    physical={}
    for tag,(table,names,r,m,proof) in data.items():
        if tag=='MID multi2':
            if (reference['source_run'],reference['source_recipe_sha256'],reference['source_proof'])!=(*RUNS[tag],proof):
                raise ValueError('Frozen multi2 storage reference differs from baseline')
            storage=reference['storage']
        else:
            storage=r['QB_storage_observations']
        raw=collected(RUNS[tag][0]);sim=json.loads(raw['simulation.state.json'])
        screen={}
        for path,item in m['standard_cell_experiment']['observed_mos'].items():
            for pair,label in item['six_pair_labels'].items():
                screen[path+'_'+pair]=r['full_history_voltage_stress'][label]
        if len(screen)!=606:
            raise ValueError('Physical pair coverage differs')
        physical[tag]=screen
        report['cases'][tag]=dict(proof=proof,storage=storage,reset=r['reset_stage_observations'],
            node_extrema={s:r['voltage_and_current_extrema'][P+s] for s in
                ['clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q','live','x020.n']},
            snapshots={s+'_'+d:snapshot(table,names,m,s,d) for s,d in
                [('clock_reset','max'),('clock_reset','min'),('xclock.rb','min'),('xclock.rb','max')]},
            native_library_current_ports=sum(len(v['actual']) for v in r['standard_cell_native_current_bindings'].values()),
            physical_failed_pairs=sum(v['over_limit_native_points']>0 for v in screen.values()),
            KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            five_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_source_energy'].items()},
            seven_boundary_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_boundary_source_energy'].items()},
            R0_absorbed_j=r['full_history_resistor_energy']['absorbed_j'],
            native_effective_settings=sim['native']['effective_settings'])
    a,b=report['cases'].values()
    if (a['native_effective_settings']!=b['native_effective_settings'] or b['native_library_current_ports']!=72
            or a['storage']['actual_native_capacitor_multi']!=2 or b['storage']['actual_native_capacitor_multi']!=1):
        raise ValueError('Effective settings, native binding or actual capacitance multiplicity differ')
    old,new=physical.values()
    if old.keys()!=new.keys():
        raise ValueError('Actual physical pair endpoints changed')
    report['physical_pair_changes']=dict(
        entered={k:v for k,v in new.items() if v['over_limit_native_points'] and not old[k]['over_limit_native_points']},
        cleared={k:v for k,v in old.items() if v['over_limit_native_points'] and not new[k]['over_limit_native_points']})
    ae,be=a['node_extrema'],b['node_extrema']
    cap=lambda c:c['storage']['post_RB90_exchange']['ports']['CMID:1']['signed_into_device_c']
    report['change']=dict(QB_droop_reduction_fraction=1-(.99-be['xclock.qb']['min'])/(.99-ae['xclock.qb']['min']),
        QB_recovery_reduction_fraction=1-b['storage']['QB_minimum_to_within_1mV_s']/a['storage']['QB_minimum_to_within_1mV_s'],
        post_RB90_MID_charge_reduction_fraction=1-cap(b)/cap(a),
        VDD_net_work_reduction_fraction=1-b['five_source_energy_j']['VDD']/a['five_source_energy_j']['VDD'],
        reset_release_delay_delta_s=b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']-a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s'])
    report['next_priority_proposal']=dict(
        action='Propose only swapping the two series-NM gate controls in XCLOCK.X003: Q on output-adjacent upper NM, RB on lower NM. Preserve PM network, current multi1 CMID, every geometry/source/clock.',
        reason='Q stays near0 during the observed release. Current upper RB-driven NM continuously transfers charge from QB into MID while lower Q-driven NM is off-intended. Reassigning the held-low control to the output-adjacent device directly tests isolation of this observed path.',
        limits='SR set/reset operation and changed input loading/stress must still be measured; no region/channel claim or guarantee. Proposal only, no new circuit/package/run.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    figure(data);write_note(report)
    print(json.dumps(dict(change=report['change'],pair_changes={k:len(v) for k,v in report['physical_pair_changes'].items()},
        failure_counts={k:v['physical_failed_pairs'] for k,v in report['cases'].items()}),indent=2))


def figure(data):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'MID multi2':'#63778b','MID multi1':'#c76b2b'}
    fig,axes=plt.subplots(5,1,sharex=True,figsize=(10.5,10.3),layout='constrained')
    specs=[('xclock.qb','QB: smaller droop and shorter recovery',1.,'V'),
           ('xclock.x003.mid','Internal MID voltage',1.,'V'),
           ('xclock.x003.cmid:1','Native MID capacitor current',1e6,'uA'),
           ('xclock.rb','RB: initial undershoot remains',1.,'V'),
           ('clock_reset','CLOCK_RESET: original edge overshoot remains',1.,'V')]
    for ax,(node,title,scale,unit) in zip(axes,specs):
        for tag,(table,names,*_) in data.items():
            ax.plot(table[:,0]*1e9,values(table,names,P+node)*scale,color=colors[tag],lw=1.5,
                    ls='--' if tag=='MID multi2' else '-',label=tag)
        ax.set(title=title,ylabel=unit);ax.grid(alpha=.18)
        ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[0].axhline(.99,color='#888',lw=.8,ls=':');axes[0].set_ylim(.86,1.012)
    axes[1].set_ylim(.06,.7);axes[2].axhline(0,color='#888',lw=.8)
    axes[3].axhline(.99,color='#888',lw=.8,ls=':');axes[3].set_ylim(-.04,1.07)
    axes[4].axhline(.99,color='#888',lw=.8,ls=':');axes[4].set_ylim(-.035,1.07)
    axes[0].legend(fontsize=9,ncol=2,loc='lower right')
    for parent,node,bounds,position,offset,ylim in [
        (axes[3],'xclock.rb',(41.075,41.082),[.3,.28,.28,.57],0.,(-21,2)),
        (axes[3],'xclock.rb',(41.09,41.115),[.67,.20,.30,.58],.99,(-.2,5.2)),
        (axes[4],'clock_reset',(41.071,41.078),[.37,.24,.34,.59],.99,(-1,23))]:
        zoom=parent.inset_axes(position)
        for tag,(table,names,*_) in data.items():
            zoom.plot(table[:,0]*1e9,(values(table,names,P+node)-offset)*1e3,color=colors[tag],lw=1.1,
                      ls='--' if tag=='MID multi2' else '-')
        zoom.set(xlim=bounds,ylim=ylim,xticks=list(bounds));zoom.tick_params(labelsize=7)
        zoom.set_ylabel('mV' if not offset else 'mV above VDD',fontsize=7,labelpad=1)
        zoom.axhline(0,color='#888',lw=.6);zoom.grid(alpha=.15)
        zoom.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[-1].set(xlim=(41.065,41.24),xlabel='Original native time (ns); no alignment or fitted waveform')
    fig.suptitle('One MID capacitor change improves QB recovery; voltage stress remains',fontsize=13)
    fig.supxlabel('FF | 0.99 V | -40 C | only XCLOCK.X003.CMID multi2 to1 | same MOS, real loads and PWL\nIdeal external supply/clock | first event only | no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'parallel_waveforms.png',dpi=165);plt.close(fig)


def write_note(report):
    a,b=report['cases'].values();ae,be=a['node_extrema'],b['node_extrema']
    cap=lambda c:c['storage']['post_RB90_exchange']['ports']['CMID:1']['signed_into_device_c']*1e15
    lines=[
        '# MID电容减半：QB储荷恢复改善，瞬态端压尚未闭合','',
        '源为原RESET NAND版；唯一变化是`XCLOCK.X003.CMID multi2→1`，其余MOS、真实驱动/负载与11份PWL保持。',
        '两组FF/0.99V/−40°C、相同原生求解设置。multi2数据同时对齐冻结的`source_storage_reference.json`。','',
        '| 指标 | multi2基线 | multi1 q2 |','| --- | ---: | ---: |',
        '| QB最低值 | %.6fV | **%.6fV** |' % (ae['xclock.qb']['min'],be['xclock.qb']['min']),
        '| QB高电平下陷，参考0.99V | %.3fmV | **%.3fmV，减小%.2f%%** |' % ((.99-ae['xclock.qb']['min'])*1e3,(.99-be['xclock.qb']['min'])*1e3,report['change']['QB_droop_reduction_fraction']*100),
        '| QB低谷→持续恢复到±1mV¹ | %.3fps | **%.3fps** |' % (a['storage']['QB_minimum_to_within_1mV_s']*1e12,b['storage']['QB_minimum_to_within_1mV_s']*1e12),
        '| 各自RB90%%→QB恢复的MID净充电¹ | %.6ffC | **%.6ffC** |' % (cap(a),cap(b)),
        '| RB下冲 / 上冲，参考0/VDD | %.3f / +%.3fmV | %.3f / +%.3fmV |' % (ae['xclock.rb']['min']*1e3,(ae['xclock.rb']['max']-.99)*1e3,be['xclock.rb']['min']*1e3,(be['xclock.rb']['max']-.99)*1e3),
        '| CLOCK_RESET上冲，参考VDD | +%.3fmV | +%.3fmV |' % ((ae['clock_reset']['max']-.99)*1e3,(be['clock_reset']['max']-.99)*1e3),
        '| QB / SN上冲，参考VDD | +%.3f / +%.3fmV | +%.3f / +%.3fmV |' % tuple((e[n]['max']-.99)*1e3 for e in [ae,be] for n in ['xclock.qb','xclock.sn']),
        '| R下降→RB上升半轨延迟 | %.3fps | %.3fps |' % (a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12,b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12),
        '| VDD净供能，0..41.590786ns | %.7fpJ | **%.7fpJ** |' % (a['five_source_energy_j']['VDD']*1e12,b['five_source_energy_j']['VDD']*1e12),
        '| 物理超限对/606 | %d | **%d** |' % (a['physical_failed_pairs'],b['physical_failed_pairs']),'',
        '¹恢复是在本次窗口内不再离开0.99V±1mV；两组积分采用各自RB90%和恢复端点，不能把充电下降百分比当作固定偏置电容标定。',
        '实际电流直接使用原生返回值，没有再乘除2。','',
        '![原生同轴波形：QB、MID、电流、RB及RESET](parallel_waveforms.png)','',
        '**储荷路径得到验证。** 减半MID后，QB下陷减小%.2f%%、恢复缩短%.2f%%，MID后段充电由4.365降至1.907fC。' % (report['change']['QB_droop_reduction_fraction']*100,report['change']['QB_recovery_reduction_fraction']*100),
        'QB低谷时，上管MN0的VGS/VDS由0.654/0.546变为0.597/0.535V；下管MN1栅源仍接近0（−0.683mV）。',
        '新低谷上管总漏端从QB抽出223.538µA、源端向MID注入201.042µA，电容吸收183.568µA；PM1补回221.481µA。',
        '低谷后30ps，电容电流由原20.415µA降至7.790µA；上管仍从QB抽出9.345µA，PM1补回10.442µA。',
        '源/漏总端流、MID充电及恢复同时变化，支持真实储荷负担的因果贡献，不能仅解释为瞬间边沿耦合。','',
        '**尚未解决的部分。** RB下冲仍约−18.15mV，CLOCK_RESET上冲仍约+20.34mV；该电容不控制这些前沿的全部来源。',
        'RB回弹从+4.724降至+3.573mV，超过VDD+1mV的宽度从17.400降至11.680ps；',
        '但QB/SN的正向峰分别增加约0.125/0.108mV，表明更快内部响应仍可能加重短尖峰。',
        '245对超限的成员也未改变，原有微伏级尾部超限保留。当前仍较大的轨外幅度为LIVE−21.365、RESET+20.339、RB−18.149及X020.N+17.966mV。','',
        '五路源、七路理想边界源和R0功分别记录；VDD同窗口净供能减少4.36%，不是整周期ADC功耗。',
        '各阶段四端偏置/电流、独立端口功率及局部端口功在JSON中。没有region、Vth或沟道分量，不推断三极区或纯Cgd。',
        'QB仍高于半轨，未见错误CLOCK_Q翻转；这不代替完整复位/闭环验证。','',
        '**优先后续建议，仅提案。** 在当前multi1候选上，只交换`XCLOCK.X003`两串联NM的栅控位置：',
        '**Q控制靠QB的上管、RB控制靠地的下管**，保留PM网络、电容、尺寸和所有外部时序。',
        '本段Q保持低，目前却是RB驱动上管持续从QB向MID供电。把保持低的控制放到输出相邻管，',
        '可直接检验是否隔开这条已定位的储荷路径；比继续减电容或机械换库更有针对性。',
        '输入负担、RB返注、全部端压及完整SR复位/置位仍须验证，不预判通过。本轮不准备候选。','',
        '**两次运行的区别。** 原v1在许可证签出阶段SPECTRE-209退出，3文件/6,023B保留，未产生电气结果。',
        '实际结果来自q2；25项电气输入及solver不变，提交recipe的run_id和retry_provenance不同。q2为9文件/9,473,260B、6059点，',
        'SHA/大小、PASS/END和72个库端流已核对；CMI-2751..2755保留。','',
        '源9文件/9,448,118B。两组外部电源/时钟理想，无噪声/失配/PEX，均为41.590786ns首事件台，不判定整机/PVT合格。',
        '[完整对照、阶段电流/偏置/源功与失败记录](comparison.json)。q2 run `%s`，managed hash `%s`。' % RUNS['MID multi1'],
        '本轮无远端操作、新实验、OA修改、采纳、commit或push。','']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
