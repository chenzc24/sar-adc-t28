"""One compact RESET NAND comparison plus native QB charge/recovery evidence."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected, values, duration
from review_standard_cell_rb_result import snapshot

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN/'standard_cell_resetnand_v1/results'
P = 'xdut.xctrl.xtim.'
TARGET = 'XDUT.XCTRL.XTIM.X023.X002'
QB = 'XDUT.XCTRL.XTIM.XCLOCK.QB'
MID = 'XDUT.XCTRL.XTIM.XCLOCK.X003.MID'
NAND = 'XDUT.XCTRL.XTIM.XCLOCK.X003'
RUNS = {
    'Original NAND':('sar8audit-ctrl-stdcell-rb-ff-v1','745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4'),
    'Library NAND':('sar8audit-ctrl-stdcell-resetnand-ff-v1','7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d')}


def physical_roles(result, cfg):
    roles = dict(MN0='A1_NM',MN1='A2_NM',MP0='A1_PM',MP1='A2_PM',
                 MM4='A1_NM',MM9='A2_NM',MM1='A1_PM',MM2='A2_PM')
    observed = {}
    for path,item in cfg['standard_cell_experiment']['observed_mos'].items():
        stable = TARGET+'.ROLE_'+roles[path.rsplit('.',1)[1]] if path.startswith(TARGET+'.') else path
        for suffix,label in item['six_pair_labels'].items():
            observed[stable+'_'+suffix] = dict(instance=path,pair=suffix,label=label,
                endpoints=cfg['stress_voltage_pairs'][label],**result['full_history_voltage_stress'][label])
    if len(observed)!=606:
        raise ValueError('Physical role map must contain606 unique pairs')
    return observed


def qb_recovery(table, names, result, cfg):
    clock = result['reset_stage_observations']['nodes']['RB']
    t10 = next(e['time_s'] for e in clock['threshold_events'] if e['fraction']==.1 and e['direction']==1)
    t90 = next(e['time_s'] for e in clock['threshold_events'] if e['fraction']==.9 and e['direction']==1)
    qb = values(table,names,QB.lower()); imin = int(np.argmin(qb))
    stable = np.logical_and.accumulate((np.abs(qb-.99)<=.001)[::-1])[::-1]
    eligible = np.flatnonzero(stable & (np.arange(len(table))>=imin))
    recovery = int(eligible[0]) if len(eligible) else None
    indices = dict(before_RB_edge=int(np.flatnonzero(table[:,0]<=t10-1e-12)[-1]),
        RB_90_percent=int(np.flatnonzero(table[:,0]>=t90)[0]),QB_minimum=imin,
        recovery_30ps=int(np.flatnonzero(table[:,0]>=table[imin,0]+30e-12)[0]))
    if recovery is not None:
        indices['within_1mV_until_stop']=recovery
    phases = {}
    for label,i in indices.items():
        def volts(node):
            return 0. if node=='0' else float(values(table,names,node.lower())[i])
        devices = {}
        for name in ['MN0','MN1','MP0','MP1']:
            path = NAND+'.'+name
            d,g,s,b = [volts(n) for n in cfg['standard_cell_experiment']['observed_mos'][path]['nodes']]
            devices[name] = dict(D_v=d,G_v=g,S_v=s,B_v=b,VGS_v=g-s,VDS_v=d-s,VBS_v=b-s,
                native_total_terminal_currents_a={terminal:float(values(table,names,(path+':'+str(port)).lower())[i])
                    for terminal,port in [('D',1),('G',2),('S',3),('B',4)]},
                model_region_vth_and_channel_current_saved=False)
        phases[label] = dict(time_s=float(table[i,0]),QB_v=volts(QB),MID_v=volts(MID),
            RB_v=volts('XDUT.XCTRL.XTIM.XCLOCK.RB'),CLOCK_Q_v=volts('XDUT.XCTRL.XTIM.CLOCK_Q'),
            devices=devices,MID_cap_total_port_current_a=float(values(table,names,(NAND+'.CMID:1').lower())[i]),
            KCL_sum_a={node:sum(float(values(table,names,s)[i]) for s in cfg['kcl_terms'][node]) for node in [QB,MID]})
    integrals = None
    if recovery is not None:
        selected = np.flatnonzero((table[:,0]>=t90)&(table[:,0]<=table[recovery,0]))
        dt = np.diff(table[selected,0]); integrals = {}
        for suffix in ['MN0:1','MN0:2','MN0:3','MN0:4','MN1:1','MP1:1','CMID:1']:
            v = values(table,names,(NAND+'.'+suffix).lower())[selected]
            integrals[suffix] = dict(signed_into_device_c=float(np.sum(.5*(v[1:]+v[:-1])*dt)),
                absolute_terminal_exchange_c=float(np.sum(.5*(np.abs(v[1:])+np.abs(v[:-1]))*dt)))
        integrals = dict(first_native_s=float(table[selected[0],0]),last_native_s=float(table[selected[-1],0]),
                         native_points=len(selected),ports=integrals)
    return dict(RB_10_s=t10,RB_90_s=t90,phases=phases,post_RB90_exchange=integrals,
        QB_minimum_to_within_1mV_s=float(table[recovery,0]-table[imin,0]) if recovery is not None else None,
        evidence_scope='Native rows and total terminal currents only. Recovery means remaining within1mV of0.99V until this41.5908ns stop, not full-cycle acceptance. No region/Vth/channel/Cgd decomposition.')


def main():
    data = {tag:read_current_run(*ids) for tag,ids in RUNS.items()}
    reference = json.loads((OWN/'standard_cell_resetnand_v1/source_input_load_reference.json').read_bytes())
    report = dict(scope='FF0.99V/-40C only X023.X002 whole-NAND replacement; existing first-event data only',
        whole_ADC_qualified=False,circuit_repair_claim=False,cases={})
    mapped = {}
    for tag,(table,names,r,m,proof) in data.items():
        raw = collected(RUNS[tag][0]); sim = json.loads(raw['simulation.state.json'])
        if tag=='Original NAND':
            if (reference['source_run'],reference['source_recipe_sha256'],reference['source_proof'])!=(*RUNS[tag],proof):
                raise ValueError('Original input-load reference provenance differs')
            loading = reference['input_loads']
        else:
            loading = r['CLOCK_RESET_NAND_input_loading']
        mapped[tag] = physical_roles(r,m)
        observed = {s:r['voltage_and_current_extrema'][P+s] for s in
            ['clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q','live','x020.n','x023.ab','x023.bb']}
        report['cases'][tag] = dict(proof=proof,node_extrema=observed,reset=r['reset_stage_observations'],
            input_loading=loading,QB_recovery=qb_recovery(table,names,r,m),
            snapshots={s+'_'+d:snapshot(table,names,m,s,d) for s,d in
                [('clock_reset','max'),('clock_reset','min'),('xclock.rb','min'),('xclock.rb','max')]},
            physical_failed_pairs=sum(v['over_limit_native_points']>0 for v in mapped[tag].values()),
            native_library_current_ports=sum(len(v['actual']) for v in r['standard_cell_native_current_bindings'].values()),
            KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_source_energy'].items()},
            boundary_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_boundary_source_energy'].items()},
            R0_absorbed_j=r['full_history_resistor_energy']['absorbed_j'],
            native_effective_settings=sim['native']['effective_settings'])
    old,new = report['cases'].values()
    if old['native_effective_settings']!=new['native_effective_settings'] or new['native_library_current_ports']!=72:
        raise ValueError('Settings or72 native library current bindings differ')
    for path in (OWN/'standard_cell_rb_v1/pwl').glob('*.pwl'):
        if path.read_bytes()!=(OWN/'standard_cell_resetnand_v1/pwl'/path.name).read_bytes():
            raise ValueError('Preserved external PWL changed')
    a,b = mapped.values()
    if a.keys()!=b.keys():
        raise ValueError('Source/candidate physical role keys differ')
    entered = [k for k,v in b.items() if v['over_limit_native_points'] and not a[k]['over_limit_native_points']]
    cleared = [k for k,v in a.items() if v['over_limit_native_points'] and not b[k]['over_limit_native_points']]
    table,names,_,m,_ = data['Library NAND']
    def voltage(node):
        return np.zeros(len(table)) if node=='0' else values(table,names,node.lower())
    delta = {}
    for key in entered:
        item = b[key]; spec = item['endpoints']; v = voltage(spec['positive_node'])-voltage(spec['negative_node'])
        delta[key] = dict(source=a[key],candidate=item,
            exceedance_v=item['max_abs_v']-.99,duration=duration(table[:,0],v,.99))
    report['physical_pair_changes'] = dict(entered=delta,cleared={k:a[k] for k in cleared},
        source_failed=old['physical_failed_pairs'],candidate_failed=new['physical_failed_pairs'],
        policy='Four replaced NAND devices matched by A1/A2 NM/PM roles, not names. Tiny failures retained against exact0.99V; amplitude is not a waiver.')
    report['change'] = dict(CLOCK_RESET_positive_amplitude_reduction_fraction=1-(new['node_extrema']['clock_reset']['max']-.99)/(old['node_extrema']['clock_reset']['max']-.99),
        RB_negative_amplitude_reduction_fraction=1-new['node_extrema']['xclock.rb']['min']/old['node_extrema']['xclock.rb']['min'],
        reset_release_delay_added_s=new['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']-old['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s'])
    report['mechanism_and_next_test'] = dict(
        inference='QB disturbance includes persistent transfer from QB through upper NAND NM total D/S ports into the real MID capacitor, opposed by PM pull-up replenishment. It persists after RB90 and is not explained by edge-only gate feedthrough.',
        limitations='Total currents only; no saved region/Vth/channel component. Do not identify triode operation, amplifier overdrive recovery or pure Cgd. Lower off-intended NM transient drain current also includes displacement.',
        propose_only='Change only XCLOCK.X003.CMID native MOM multi2->1 at identical device geometry, all MOS/drivers/loads/PWL/timing unchanged; compare MID charge, QB minimum/recovery, RB return, input burden and all physical stress. No next gate/library sweep or package generated.',
        reason='Directly perturbs the observed downstream charge reservoir rather than mechanically replacing more logic. Less charge may trade against larger edge overshoot; no repair is presumed.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    figure(data,report); write_note(report)
    print(json.dumps(dict(change=report['change'],entered=len(entered),cleared=len(cleared),
        added_pair_excess_uV={k:v['exceedance_v']*1e6 for k,v in delta.items()},
        QB_recovery_ps={k:v['QB_recovery']['QB_minimum_to_within_1mV_s']*1e12 for k,v in report['cases'].items()},
        post_RB90_charge=new['QB_recovery']['post_RB90_exchange']),indent=2))


def figure(data,report):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = {'Original NAND':'#63778b','Library NAND':'#c76b2b'}
    fig,axes = plt.subplots(6,1,sharex=True,figsize=(10.5,12),layout='constrained')
    for ax,node,title in zip(axes[:4],['clock_reset','xclock.rb','xclock.qb','xclock.x003.mid'],
            ['CLOCK_RESET','RB','SR QB','SR NAND internal MID']):
        for tag,(table,names,*_) in data.items():
            ax.plot(table[:,0]*1e9,values(table,names,P+node),color=colors[tag],lw=1.5,
                    ls='--' if tag=='Original NAND' else '-',label=tag)
        ax.set(title=title,ylabel='V')
        if node!='xclock.x003.mid':
            ax.axhline(.99,color='#888',ls=':',lw=.8)
    table,names,r,_,_ = data['Library NAND']
    for suffix,sign,label,color in [('mn0:1',1,'Upper NM drain: out of QB','#336a9f'),
                                  ('mp1:1',-1,'PM pull-up: into QB','#c57b2e'),
                                  ('cmid:1',1,'MID capacitor: charging','#3c8c78')]:
        axes[4].plot(table[:,0]*1e9,sign*values(table,names,(NAND+'.'+suffix).lower())*1e6,color=color,lw=1.4,label=label)
    axes[4].set(title='Library-NAND case: native total terminal currents',ylabel='uA')
    axes[4].legend(fontsize=8,ncol=3,loc='upper right')
    rb=values(table,names,P+'xclock.rb'); qb=values(table,names,QB.lower()); mid=values(table,names,MID.lower())
    for v,label,color in [(rb-mid,'Upper NM VGS','#336a9f'),(qb-mid,'Upper NM VDS','#c57b2e'),
                          (values(table,names,P+'clock_q'),'Lower NM VGS','#637367')]:
        axes[5].plot(table[:,0]*1e9,v,label=label,color=color,lw=1.4)
    axes[5].set(title='Actual NAND bias; model region / Vth not saved',ylabel='V')
    axes[5].legend(fontsize=8,ncol=3,loc='upper right')
    axes[0].set_ylim(-.035,1.07); axes[1].set_ylim(-.04,1.07);axes[2].set_ylim(.86,1.015);axes[3].set_ylim(.06,.69)
    axes[0].legend(fontsize=9,ncol=2,loc='upper right')
    t90=report['cases']['Library NAND']['QB_recovery']['RB_90_s']*1e9
    for ax in axes:
        ax.grid(alpha=.18); ax.axvline(t90,color='#777',ls='--',lw=.8)
        ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[0].text(t90+.001,.82,'RB 90%',transform=axes[0].get_xaxis_transform(),fontsize=8)
    for ax,node,bounds,position,offset,ylim in [
        (axes[0],'clock_reset',(41.071,41.078),[.37,.25,.32,.58],.99,(-1,26)),
        (axes[1],'xclock.rb',(41.075,41.082),[.29,.28,.30,.59],0.,(-23,2)),
        (axes[1],'xclock.rb',(41.09,41.115),[.68,.18,.29,.59],.99,(-.2,5.5))]:
        inset=ax.inset_axes(position)
        for tag,(t,n,*_) in data.items():
            inset.plot(t[:,0]*1e9,(values(t,n,P+node)-offset)*1e3,color=colors[tag],lw=1.1,
                       ls='--' if tag=='Original NAND' else '-')
        inset.set(xlim=bounds,ylim=ylim,xticks=list(bounds))
        inset.set_ylabel('mV' if not offset else 'mV above VDD',fontsize=7,labelpad=1)
        inset.axhline(0,color='#888',lw=.6);inset.grid(alpha=.15);inset.tick_params(labelsize=7)
        inset.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[-1].set(xlim=(41.065,41.24),xlabel='Original native time (ns); dashed line: RB reaches 90%')
    fig.suptitle('RESET NAND replacement: edge peaks improve, QB charging tail remains',fontsize=13)
    fig.supxlabel('FF | 0.99 V | -40 C | only X023.X002 changed | real INV, RB and SR loads\nIdeal external supply/clock | native first event | no noise, mismatch or PEX | currents are total terminal currents',fontsize=8)
    fig.savefig(OUT/'parallel_waveforms.png',dpi=165);plt.close(fig)


def write_note(report):
    a,b=report['cases'].values();ae,be=a['node_extrema'],b['node_extrema']
    lines=[
        '# RESET NAND替换：前沿改善，QB充电恢复未解决','',
        '仅替换`X023.X002`，原4MOS及MID电容一起退出；AB/BB真实INV驱动、RB/SR负载和11份PWL不变。',
        'FF/0.99V/−40°C，同一首事件台。不是单管或单电容归因实验。','',
        '| 指标 | 原NAND | 原生ND2D1 |','| --- | ---: | ---: |',
        '| CLOCK_RESET峰值，参考VDD | +%.3fmV | **+%.3fmV，降低%.2f%%** |' % ((ae['clock_reset']['max']-.99)*1e3,(be['clock_reset']['max']-.99)*1e3,report['change']['CLOCK_RESET_positive_amplitude_reduction_fraction']*100),
        '| CLOCK_RESET最低值 | +%.3fµV | **%.3fµV** |' % (ae['clock_reset']['min']*1e6,be['clock_reset']['min']*1e6),
        '| RB最低值 | %.3fmV | **%.3fmV** |' % (ae['xclock.rb']['min']*1e3,be['xclock.rb']['min']*1e3),
        '| RB低于−1mV累计宽度 | %.3fps | **%.3fps，变宽** |' % (a['reset']['excursion_widths']['nodes']['RB']['below_minus_1mV']['cumulative_s']*1e12,b['reset']['excursion_widths']['nodes']['RB']['below_minus_1mV']['cumulative_s']*1e12),
        '| RB回弹，参考VDD | +%.3fmV | +%.3fmV |' % ((ae['xclock.rb']['max']-.99)*1e3,(be['xclock.rb']['max']-.99)*1e3),
        '| QB最低值 | %.6fV | %.6fV |' % (ae['xclock.qb']['min'],be['xclock.qb']['min']),
        '| QB低谷→回到VDD±1mV¹ | %.3fps | **%.3fps** |' % (a['QB_recovery']['QB_minimum_to_within_1mV_s']*1e12,b['QB_recovery']['QB_minimum_to_within_1mV_s']*1e12),
        '| R下降→RB上升半轨延迟 | %.3fps | %.3fps |' % (a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12,b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12),
        '| 物理超限对/606 | 237 | **245** |',
        '| VDD净供能，0..41.590786ns | %.7fpJ | %.7fpJ |' % (a['source_energy_j']['VDD']*1e12,b['source_energy_j']['VDD']*1e12),'',
        '¹原生样点首次回到±1mV且至本次结束未再离开；不是完整复位/闭环合格门限。CLOCK_Q仍无半轨沿。','',
        '**新增8对具体是什么。** 按A1/A2、NM/PM角色对齐旧新四管后，进入8对、清除0对：',
        '`XCLOCK.X000.MM0`的VGS/VGB两对、`X023.X002.MM1/MM2`的VDS/VDB四对，',
        '均因41.104090ns的CLOCK_RESET −83.280µV而最大超出83.280µV；',
        '`X023.X002.MM2`的VGD超44.030µV（41.104287ns），`MM4`的VGS超13.837µV（41.108219ns）。',
        '−83µV最低点，RB反相器两栅端合计抽走77.090nA，本级三个漏端补回77.090nA，显示尾部仍有实际门间电流交换。',
        '它们发生在低电平恢复尾部，不是新增8个20mV尖峰；也不能按幅度小就删除或判通过。精确0.99V门限及原生CMI均保留。','',
        '![同输入对照及QB内部充电、偏置](parallel_waveforms.png)','',
        '**两个不同时间尺度。** CLOCK_RESET上冲仍在41.074075ns；新NAND的A1 PM总漏端注入12.326µA，',
        'A1 NM抽走12.327µA，另一个PM及RB输入栅端补齐KCL。RB下冲发生在41.078367ns，',
        'INV NM总漏端抽走10.865µA、PM补回10.247µA、SR栅端补回0.619µA。此类短前沿交换仍在，标准门自带寄生也不是理想钳位器。','',
        'AB输入栅端峰值185.554→99.866µA，事件净交换1.615→0.756fC；BB对应32.002→16.940µA、0.176→0.092fC。',
        '上游负担减小不等于下游内部储荷过程已经消失。','',
        'QB则在RB跨过90%（41.087884ns）后继续下降，到41.091571ns最低0.877733V。',
        '前沿前上管VGS/VDS约**−0.067/0.907V**；',
        '在低谷，`XCLOCK.X003.MN0`上管VGS/VDS=**0.654/0.546V**，下管MN1 VGS=**−2.444mV**；',
        '上管总漏端从QB抽走**320.657µA**，源端向MID注入300.310µA，MID电容吸收**286.536µA**；',
        '保持高电平的PM1同时向QB补回319.969µA。MID已由前沿前约0.085V升至0.332V。','',
        '30ps后，MID为0.569V，上管VGS/VDS约**0.422/0.413V**，仍从QB抽走22.669µA，',
        '电容仍吸收20.415µA、PM1补回25.435µA。QB到41.223469ns才在本窗口内稳定回到±1mV。',
        'QB仍高于0.495V半轨，当前没有错误翻转证据；约132ps是局部恢复过程，不能直接当作错误码或整机失败的证明。',
        'RB90%之后到这个时点，MID电容净吸收**4.365fC**，对应上管源端提供4.572fC，差额由下管总漏端0.207fC平衡。',
        '这直接支持**内部MID充电、QB电荷共享及PM再充电恢复**，不能仅用瞬间栅漏耦合解释约132ps尾巴。','',
        '下冲前、低谷、恢复的四端偏置/电流都保存在JSON；未保存region、Vth或沟道电流分量。',
        '因此不把它直接称为教材中的放大器过驱恢复，也不宣称三极区、纯沟道或Cgd分解；下管的瞬态漏端流同样含位移分量，不能据此称作漏电。','',
        '**为什么仍有问题。** 本次源级替换减小了CLOCK_RESET上冲及RB下冲，未改动上述SR内部储荷节点，QB尾巴基本不变。',
        '0.99V供电已等于当前核心端压筛查上限，没有上冲余量；标准核心门不会消除本体寄生或真实负载回馈。',
        '当前较大的轨外扰动仍是LIVE −21.368mV、CLOCK_RESET +20.340mV、RB −18.144mV、X020.N +17.966mV。','',
        '**最有效的下一项辨因实验。** 只将`XCLOCK.X003.CMID`原生MOM的`multi=2→1`，',
        '所有MOS尺寸、驱动、负载、供电与时序不变；对比MID净充电、QB低谷/恢复及RB返注、全部端压。',
        '它直接扰动已观测到的储荷量，能检验充电负担对长尾的贡献，比继续逐门换库更有辨别力。',
        '减小电容也可能放大短时过冲，不能预设改善。本轮只提出实验，不生成候选。','',
        '72个库端流已原生绑定；全部节点最大KCL残差约3.937pA。源9文件/9,487,824B，新9文件/9,448,118B，',
        '输入与回收身份、PASS/END、实际求解设置已核对；新6058点。五路源、七路边界源与R0功分别保存，VDD净功不是整周期ADC功耗。',
        '外部电源/时钟理想，无噪声/失配/PEX；没有新reset断言或完整复位验证，不作PVT/整机合格结论。','',
        '[完整数值、8对清单、分阶段偏置及端流](comparison.json)。run `%s`，managed hash `%s`。' % RUNS['Library NAND'],
        '本轮无远端操作、OA修改、新候选、commit或push。','']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
