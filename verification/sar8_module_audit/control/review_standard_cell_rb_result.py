"""Compact native RB-INVD1 comparison, one table and one parallel figure."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected, values

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN/'standard_cell_rb_v1/results'
P = 'xdut.xctrl.xtim.'
TARGET = 'XDUT.XCTRL.XTIM.XCLOCK.X000'
RUNS = {
    'Original RB': ('sar8audit-ctrl-stdcell-live-ff-v1',
        'a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226'),
    'Library RB': ('sar8audit-ctrl-stdcell-rb-ff-v1',
        '745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4')}


def snapshot(table, names, cfg, node, direction):
    v = values(table,names,P+node)
    i = int(np.argmin(v) if direction=='min' else np.argmax(v))
    key = next(k for k in cfg['kcl_terms'] if k.lower()==P+node)
    currents = {s:float(table[i,names.index(s)]) for s in cfg['kcl_terms'][key]}
    return dict(time_s=float(table[i,0]),node=P+node,direction=direction,
        voltages_v={s:float(values(table,names,P+s)[i]) for s in
                    ['clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q']},
        positive_out_terminal_currents_a=currents,KCL_sum_a=sum(currents.values()))


def main():
    data = {tag:read_current_run(*ids) for tag,ids in RUNS.items()}
    reference = json.loads((OWN/'standard_cell_rb_v1/source_reset_reference.json').read_bytes())
    if (reference['source_run'],reference['source_recipe_sha256'])!=RUNS['Original RB']:
        raise ValueError('Source reset reference identity differs')
    report = dict(scope='FF0.99V/-40C first event; only XCLOCK.X000 reset INV replacement',
        implementation='Original2custom MOS ->2native INVD1 MOS, no explicit capacitor change; dimensions/intrinsic parasitics change together.',
        whole_ADC_qualified=False,circuit_repair_claim=False,cases={})
    for tag,(table,names,r,m,proof) in data.items():
        raw = collected(RUNS[tag][0]); sim = json.loads(raw['simulation.state.json'])
        analysis = json.loads(raw['analysis.state.json'])
        if tag=='Original RB':
            if reference['source_proof']!=proof:
                raise ValueError('Source reference provenance differs')
            reset = reference['reset']
        else:
            reset = r['reset_stage_observations']
            if len(r['standard_cell_native_current_bindings'])!=14:
                raise ValueError('Expected fourteen actual library MOS bindings')
        groups = {}; physical = []
        library = m['standard_cell_experiment']['library_mos']
        for path,item in m['standard_cell_experiment']['observed_mos'].items():
            group = 'RB_stage' if path.startswith(TARGET+'.') else 'existing_library' if path in library else 'other_core'
            g = groups.setdefault(group,dict(MOS=0,pairs=0,failed_pairs=0))
            g['MOS']+=1; g['pairs']+=6
            for suffix,label in item['six_pair_labels'].items():
                obs = r['full_history_voltage_stress'][label]
                g['failed_pairs']+=int(obs['over_limit_native_points']>0)
                physical.append(dict(instance=path,pair=suffix,**obs))
        if sum(g['pairs'] for g in groups.values())!=606:
            raise ValueError('Harmonized physical pair grouping differs')
        physical.sort(key=lambda s:s['max_abs_v'],reverse=True)
        quiet = [e['time_s'] for e in r['diagnostic_timing']['signals'][P+'quiet']['threshold_events']
                 if e['fraction']==.5 and e['direction']==1][0]
        node_extrema = {s:r['voltage_and_current_extrema'][P+s] for s in
            ['clock_reset','xclock.rb','xclock.qb','xclock.sn','clock_q','clock_set',
             'sn','live','x001.n','x020.n','quiet','xd_quiet_d.rc1']}
        excursions = []
        for node in m['voltage_saves']:
            if node=='VDD!':
                continue
            item = r['voltage_and_current_extrema'][node.lower()]
            negative,positive = max(0.,-item['min']),max(0.,item['max']-.99)
            if max(negative,positive)>.001:
                excursions.append(dict(node=node.lower(),amplitude_v=max(negative,positive),
                    direction='negative' if negative>=positive else 'positive',
                    time_s=item['min_time_s'] if negative>=positive else item['max_time_s']))
        excursions.sort(key=lambda s:s['amplitude_v'],reverse=True)
        report['cases'][tag] = dict(proof=proof,node_extrema=node_extrema,reset=reset,
            sample_close_s=r['diagnostic_timing']['sample_close_s'],
            QUIET_after_sample_close_s=quiet-r['diagnostic_timing']['sample_close_s'],
            snapshots={node+'_'+direction:snapshot(table,names,m,node,direction) for node,direction in
                [('xclock.rb','min'),('xclock.rb','max'),('clock_reset','max'),('xclock.qb','max')]},
            groups=groups,rail_excursions_ranked=excursions,largest_physical_pair_observations=physical[:12],
            source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_source_energy'].items()},
            boundary_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_boundary_source_energy'].items()},
            R0_absorbed_j=r['full_history_resistor_energy']['absorbed_j'],
            KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            native_library_current_ports=sum(len(v['actual']) for v in r['standard_cell_native_current_bindings'].values()),
            native_effective_settings=sim['native']['effective_settings'],
            simulation_seconds=sim['elapsed_seconds'],simulation_peak_rss_bytes=sim['peak_rss_bytes'],
            analysis_seconds=analysis['elapsed_seconds'],analysis_peak_rss_bytes=analysis['peak_rss_bytes'])
    old,new = report['cases'].values()
    if old['native_effective_settings']!=new['native_effective_settings']:
        raise ValueError('Native effective solver settings differ')
    for path in (OWN/'standard_cell_live_v1/pwl').glob('*.pwl'):
        if path.read_bytes()!=(OWN/'standard_cell_rb_v1/pwl'/path.name).read_bytes():
            raise ValueError('Preserved input PWL bytes differ')
    report['change'] = dict(
        RB_negative_amplitude_reduction_fraction=1-new['node_extrema']['xclock.rb']['min']/old['node_extrema']['xclock.rb']['min'],
        reset_release_delay_added_s=new['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']-old['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s'],
        native_sample_close_extraction_delta_s=new['sample_close_s']-old['sample_close_s'],
        VDD_net_work_reduction_fraction=1-new['source_energy_j']['VDD']/old['source_energy_j']['VDD'])
    report['next_experiment_recommendation'] = dict(target='XDUT.XCTRL.XTIM.X023.X002',
        action='Replace only original CLOCK_RESET output NAND with unchanged verified ND2D1BWP12T30P140; A1=AB,A2=BB. Preserve both real upstream inverters and library RB/SR loads, reset polarity/priority, external PWL and sampling edges.',
        reason='Largest remaining rail/physical stress is upstream CLOCK_RESET +24.622mV. Its falling edge also excites RB undershoot; test the source stage before more RB sizing.',
        confound='Whole four-MOS NAND plus explicit MID-cap implementation replacement; dimensions/parasitics/cap change together. Native core standard cell is not guaranteed SOA-safe.',
        no_package_or_remote_job_generated=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    figure(data)
    write_note(report)
    print(json.dumps(dict(change=report['change'],ranked_remaining=new['rail_excursions_ranked'][:7],
        groups={k:v['groups'] for k,v in report['cases'].items()}),indent=2))


def figure(data):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = {'Original RB':'#63778b','Library RB':'#c76b2b'}
    fig,axes = plt.subplots(5,1,sharex=True,figsize=(10.5,10.2),layout='constrained')
    specs = [('clock_reset','CLOCK_RESET: actual upstream driver','V',1.),
             ('xclock.rb','RB: reset-inverter output','V',1.),
             ('xclock.qb','SR QB: retained high-state disturbance','V',1.),
             ('xclock.sn','SR SN: retained high-state disturbance','V',1.),
             ('clock_q','CLOCK_Q: no halfrail clock edge observed','mV',1e3)]
    for ax,(node,title,unit,scale) in zip(axes,specs):
        for tag,(table,names,*_) in data.items():
            ax.plot(table[:,0]*1e9,values(table,names,P+node)*scale,color=colors[tag],
                    ls='--' if tag=='Original RB' else '-',lw=1.5,label=tag)
        ax.set(title=title,ylabel=unit);ax.grid(alpha=.18)
        ax.axhline((0. if node=='clock_q' else .99)*scale,color='#888',ls=':',lw=.8)
        ax.ticklabel_format(axis='x',style='plain',useOffset=False)
        ax.axvline(data['Library RB'][2]['diagnostic_timing']['sample_close_s']*1e9,color='#888',ls=':',lw=.8)
    axes[0].legend(ncol=2,fontsize=9,loc='lower right')
    axes[0].set_ylim(-.04,1.07);axes[1].set_ylim(-.05,1.07)
    axes[2].set_ylim(.86,1.015);axes[3].set_ylim(.987,1.008);axes[4].set_ylim(-6.1,4.8)
    axes[-1].set(xlim=(41.06,41.125),xlabel='Original native time (ns); dotted vertical = sample close')
    for parent,node,bounds,area,offset,ylim in [
        (axes[0],'clock_reset',(41.072,41.077),[.53,.29,.43,.57],.99,(-1,27)),
        (axes[1],'xclock.rb',(41.076,41.081),[.05,.40,.25,.50],0.,(-28,2)),
        (axes[1],'xclock.rb',(41.09,41.11),[.56,.20,.40,.58],.99,(-.2,5.4))]:
        zoom = parent.inset_axes(area)
        for tag,(table,names,*_) in data.items():
            zoom.plot(table[:,0]*1e9,(values(table,names,P+node)-offset)*1e3,color=colors[tag],
                      ls='--' if tag=='Original RB' else '-',lw=1.15)
        zoom.set(xlim=bounds,ylim=ylim,xticks=[bounds[0],bounds[1]])
        zoom.axhline(0,color='#888',lw=.6);zoom.grid(alpha=.15);zoom.tick_params(labelsize=7)
        zoom.set_ylabel('mV' if offset==0 else 'mV above VDD',fontsize=7,labelpad=1)
        zoom.ticklabel_format(axis='x',style='plain',useOffset=False)
    fig.suptitle('RB inverter replacement: smaller undershoot, larger rebound',fontsize=13)
    fig.supxlabel('FF | 0.99 V | -40 C | only XCLOCK.X000 changed | same PWL and real driver/SR loads\nIdeal external supply/clock | first event only | no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'parallel_waveforms.png',dpi=165);plt.close(fig)


def write_note(report):
    a,b = report['cases'].values(); ae,be = a['node_extrema'],b['node_extrema']
    def width(case,node,band):
        return case['reset']['excursion_widths']['nodes'][node][band]['cumulative_s']*1e12
    lines = [
        '# RB标准反相器：下冲改善，回弹和上游过压仍在',
        '',
        '只替换`XCLOCK.X000`两管反相器，无显式电容增删；其余127个实例、11份PWL和采样边沿不变。',
        '两组均为FF/0.99V/−40°C，真实CLOCK_RESET驱动和SR扇出保持。尺寸、固有寄生随整级改变。',
        '',
        '| 指标 | 原RB反相器 | 原生INVD1 |',
        '| --- | ---: | ---: |',
        '| RB最低值 | %.3fmV | **%.3fmV，幅度减小%.2f%%** |' % (ae['xclock.rb']['min']*1e3,be['xclock.rb']['min']*1e3,report['change']['RB_negative_amplitude_reduction_fraction']*100),
        '| RB低于−1mV累计宽度 | %.3fps | %.3fps |' % (width(a,'RB','below_minus_1mV'),width(b,'RB','below_minus_1mV')),
        '| RB上冲，参考VDD | +%.3fmV | **+%.3fmV** |' % ((ae['xclock.rb']['max']-.99)*1e3,(be['xclock.rb']['max']-.99)*1e3),
        '| RB超过VDD+1mV累计宽度 | %.3fps | **%.3fps，变宽** |' % (width(a,'RB','above_0p991_v'),width(b,'RB','above_0p991_v')),
        '| CLOCK_RESET上冲，参考VDD | +%.3fmV | **+%.3fmV** |' % ((ae['clock_reset']['max']-.99)*1e3,(be['clock_reset']['max']-.99)*1e3),
        '| CLOCK_RESET超过VDD+1mV累计宽度 | %.3fps | %.3fps |' % (width(a,'CLOCK_RESET','above_0p991_v'),width(b,'CLOCK_RESET','above_0p991_v')),
        '| SR QB / SN上冲，参考VDD | +%.3f / +%.3fmV | +%.3f / +%.3fmV |' % tuple((e[n]['max']-.99)*1e3 for e in [ae,be] for n in ['xclock.qb','xclock.sn']),
        '| SR QB高电平下陷，参考VDD | %.3fmV | %.3fmV |' % ((.99-ae['xclock.qb']['min'])*1e3,(.99-be['xclock.qb']['min'])*1e3),
        '| R下降→RB上升半轨延迟 | %.3fps | **%.3fps** |' % (a['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12,b['reset']['reset_release_R_fall_to_RB_rise'][0]['delay_s']*1e12),
        '| VDD净供能，0..41.590786ns | %.7fpJ | %.7fpJ |' % (a['source_energy_j']['VDD']*1e12,b['source_energy_j']['VDD']*1e12),
        '',
        '宽度按原生样点交叉估计；1mV仅描述脉冲，器件筛查仍为0.99V。237/606个物理端压对仍超限，',
        '新RB级为8/12对；不能因峰值改善判定合格。CLOCK_Q未越半轨，新的reset断言尚无观测。',
        '',
        '![同输入、原生时间的平行波形](parallel_waveforms.png)',
        '',
        '**端流来源。** RB低谷发生在41.078810ns，此时CLOCK_RESET仍为0.575647V。',
        '新INV的NM `MM1`总漏端从RB抽出19.006µA，PM `MM0`补回18.311µA，四个SR栅端合计补回0.695µA。',
        '到41.095793ns的RB回弹峰，QB已从下陷恢复，`X003.MN0/MP0`栅端合计注入10.470µA，INV漏端净抽走9.812µA，',
        '另一路SR栅负载抽走0.658µA。这支持“前沿输入耦合、随后真实SR负载回馈”的动态交换，',
        '总端流不能唯一拆成沟道/Cgd；两组各自极值也不是同偏置比较。全部节点最大KCL残差约3.937pA，56个库端流均已绑定。',
        '',
        '新级输入栅端负向电流峰值215.4→150.5µA，事件净交换−1.232→−0.756fC；',
        'CLOCK_RESET下降沿6.852→5.520ps，但RB上升沿5.271→6.957ps，释放延迟增加1.006ps。',
        '上游过冲未随输入负担减小而消失；其峰值处仍由原`X023.X002.MP0`总漏端注入约13.118µA。',
        '',
        '**剩余问题与阶段。** 按越出电源轨的幅度排序：①41.074778ns，高电平末端CLOCK_RESET **+24.622mV**；',
        '②41.081723ns，SN上升激励LIVE **−21.368mV**；③41.078810ns，复位释放前沿RB **−20.571mV**；',
        '④41.087198ns，LIVE传播到下一NAND时X020.N **+17.966mV**；⑤41.101422ns，QUIET激励的延迟链AB **+14.032mV**；',
        '⑥41.075975ns，SN激励的LIVE内节点X001.N **+12.512mV**；⑦RB上升期间SR QB/SN **+12.319/+11.749mV**。',
        '其中最大实际端压约1.014622V，落在CLOCK_RESET驱动NM漏/体及接收NM栅/源等端对。',
        '另一个较大的功能扰动是QB在41.091408ns下陷112.002mV；它仍为0.877998V，尚未越0.495V，需和端压超限区分。',
        '',
        '**下一项建议。** 仅将产生CLOCK_RESET的末级NAND `X023.X002`换成已验证原生`ND2D1`，',
        '保持`AB→A1、BB→A2`、两个前级INV、当前RB/SR负载和全部时序。',
        '它直接产生当前最大过压，下降沿又激励RB下冲，优先检查此源级比继续放大RB单管更有针对性。',
        '这是整NAND（原4MOS及MID电容）实现替换，须重新测上游输入负担、两侧过压和复位延迟；标准核心门也不保证自动满足端压限制。',
        '这里只提出实验，不生成下一级包。',
        '',
        '原始CMI-2751..2755保留。五路原有源、七路理想边界源与被动R0功分开，VDD净供能不是整周期ADC功耗。',
        '源9文件/9,416,094B，新9文件/9,487,824B，输入/回收SHA、PASS/END及实际求解设置已核对；新6065点。',
        '仍为理想外部电源/时钟、无噪声/失配/PEX的首事件台，不证明完整复位、PVT或ADC闭环合格。',
        '',
        '[完整数值与端流快照](comparison.json)。新run：`%s`，managed hash `%s`。' % RUNS['Library RB'],
        '本轮无远端操作、OA修改、采纳、commit或push。',
        '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
