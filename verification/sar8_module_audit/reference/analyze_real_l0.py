"""Completed real-L0 source-stage diagnostic; only small collected native tables."""
import argparse,csv,gzip,hashlib,json,os,re
import numpy as np
from analyze_gpp_single_io import load_new as load_ideal
from analyze_real_pre import leading
from compare_io_cell import HERE,ROOT,digest,error_bounds

OUT=HERE/'generated/real_l0_comparison'
HASHES={'ffcold':'05a160866e5f9d0a2c8a870c1fdda9150735713fab975613e192848cb8cd4ac1',
        'sscold':'5a871ba335820094f7e7d7aa87e61b15aeae21dccdd1a057fdb333b0ba6f95a2'}


def load_real(corner):
    name='sar8audit-real-l0-'+corner;folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert not receipt['skipped'] and len(receipt['files'])==11 and receipt['status']['registered']['recipe_hash']==HASHES[corner]
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']
    assert receipt['total_bytes']=={'ffcold':6600138,'sscold':6490553}[corner]
    cfgpath=HERE/'generated/real_l0_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text())
    for x in json.loads((cfgpath.parent/'recipe_proposal.json').read_text())['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());state=json.loads((folder/'simulation.state.json').read_text())
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['measurement_sha256']==digest(cfgpath)
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==470 and r['native_PSF_END']
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');p=folder/'derived'/e['file'];assert digest(p)==e['sha256']
    raw=gzip.decompress(p.read_bytes());assert len(raw)==e['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256']
    w=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']))
    assert w.shape==(r['native_points'],142) and w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    assert r['native_points']=={'ffcold':8966,'sscold':8527}[corner]
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(e['columns'])},
        result_sha256=digest(folder/'derived/result.json'),managed_recipe_sha256=HASHES[corner],receipt_bytes=receipt['total_bytes'])


def summary(d,corner,variant):
    r,m=d['result'],d['result']['cell_measurements'];rows=[];groups={}
    for p in d['cfg']['selected_mos_pair_screens']:
        name=p['instance'];key=name+':'+p['terminal'];x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
        group='L0SRC' if '.L0SRC.' in name else 'X025' if '.X025.' in name else 'GPP' if re.fullmatch(r'XDUT.GPPI[NP]',name) else 'GNN_ABC' if re.fullmatch(r'XDUT.GNN[ABC][NP]',name) else 'physical_load'
        rows.append(dict(corner=corner,variant=variant,group=group,pair=key,model=p['model'],screen_V=p['screen_v'],min_V=x['min'],max_V=x['max'],excess_V=peak-p['screen_v']))
    for group in ['L0SRC','X025','GPP','GNN_ABC','physical_load']:
        q=[x for x in rows if x['group']==group]
        if not q:continue
        worst=max(q,key=lambda x:x['excess_V'])
        groups[group]=dict(records=len(q),strict_exceed=sum(x['excess_V']>0 for x in q),over1mV=sum(x['excess_V']>.001 for x in q),
            worst_pair=worst['pair'],worst_abs_V=max(abs(worst['min_V']),abs(worst['max_V'])),worst_excess_mV=worst['excess_V']*1e3)
    terminal_changes={k:x for k,x in r['selected_mos_pair_extrema'].items() if '.X025.' in k or '.L0SRC.' in k}
    out=dict(run=d['run'],result_sha256=d['result_sha256'],native_points=r['native_points'],groups=groups,
        terminal_changes=terminal_changes,rails=m['supply_rail_excursions'],native_warning_codes=r['native_warning_codes'],
        timing={n:{k:v for k,v in q.items() if k!='native_edge_witnesses'} for n,q in m['actual_stage_timing'].items()},
        halfVDD_control_gaps={n:x['signed_halfVDD_control_gap_s'] for n,x in m['actual_same_side_control_gaps'].items()},
        correct_ON_settling=m['correct_ON_settling'],input_loads=m['real_PRE_and_L0_loads'],
        source_and_internal_work=m['source_and_internal_work'],stage_direct_VDD_energy_J=m['restored_stage_direct_VDD_energy_J'],
        fixture_direct_VDD_energy_J=m['ideal_VDD_energy_J'],body_source_and_X025=[x for x in m['body_forward_polarity'] if '.L0SRC.' in x['pair'] or '.X025.' in x['pair']],
        actual_GPP_body=max((x for x in m['body_forward_polarity'] if re.fullmatch(r'XDUT.GPPI[NP]:b[ds]',x['pair'])),key=lambda x:x['signed_forward_max_V']),
        off_gap={n:error_bounds(d['w'],d['c'],n,ref,46.995e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]},
        native_effective_settings=r['native_effective_settings'])
    if variant=='real_L0':
        source_groups={'MN_D':['xdut.l0src.mn:1'],'MP_D':['xdut.l0src.mp:1'],
            'X025_gates':['xdut.x025.mn:2','xdut.x025.mp:2'],'GPP_IO_gates':['xdut.gppin:2','xdut.gppip:2']}
        out['source_leading_positive']=leading(d,'xdut.l0','l0n',source_groups,(42.99e-9,43.005e-9),['xdut.l0src.mn','xdut.l0src.mp'])
        out['PRE_leading_positive']=leading(d,'xdut.pre','xdut.l0',{'MN_D':['xdut.x025.mn:1'],'MP_D':['xdut.x025.mp:1'],
            'ABC_A_gates':['xdut.gnnan:2','xdut.gnnap:2']},(47.995e-9,48.02e-9),['xdut.x025.mn','xdut.x025.mp'])
        out['source_identity']=dict(managed_recipe_sha256=d['managed_recipe_sha256'],receipt_bytes=d['receipt_bytes'])
    return out,rows


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'ideal_L0':'#777b80','real_L0':'#126da1'};styles={'ideal_L0':'--','real_L0':'-'};corners=list(waves)
    fig,axes=plt.subplots(4,len(corners),figsize=(6.3*len(corners),9),squeeze=False,layout='constrained')
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];l0='l0' if variant=='ideal_L0' else 'xdut.l0'
            for i,(node,edge) in enumerate([(l0,43),(l0,48),('xdut.pre',48),('xdut.gppdrv',48)]):
                t=(w[:,0]-edge*1e-9)*1e12;stop=100 if corner=='ffcold' else 350;s=(t>=-15)&(t<=stop)
                axes[i,j].plot(t[s],w[s,c[node]],color=colors[variant],ls=styles[variant],lw=1.4,label='Previous: ideal L0' if variant=='ideal_L0' else 'Restored: real L0')
                axes[i,j].set(xlim=(-15,stop),xlabel=f'Time from input-command midpoint at {edge} ns (ps)')
        for i,label in enumerate(['L0 falling (V)','L0 rising (V)','PRE / X025 (V)','GPPDRV (V)']):
            ax=axes[i,j];ax.set_ylabel(label);ax.grid(alpha=.17);ax.axvline(0,color='#aaa',lw=.7)
            for rail in [0,.99 if corner=='ffcold' else .81]:ax.axhline(rail,color='#aaa',ls=':',lw=.7)
        axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
    axes[0,0].legend(fontsize=8,loc='center right');fig.suptitle('Real L0 source exposes another core-device interface',fontsize=13)
    fig.supxlabel('Same single-IO GPP, X025, ABC, physical CDAC/reference/Bootstrap; ideal N input/rails; comparator reset\nNo time alignment. Dotted horizontal lines = rails, not model ratings. No noise, mismatch or PEX.',fontsize=8)
    fig.savefig(OUT/'real_L0_voltage_comparison.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,len(corners),figsize=(6.3*len(corners),7),squeeze=False,layout='constrained')
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=(w[:,0]-48e-9)*1e12;stop=100 if corner=='ffcold' else 350;s=(t>=-15)&(t<=stop)
            arrays=[w[:,c['vl0:1']] if variant=='ideal_L0' else w[:,c['xdut.l0src.mn:1']]+w[:,c['xdut.l0src.mp:1']],
                w[:,c['xdut.x025.mn:2']]+w[:,c['xdut.x025.mp:2']],w[:,c['xdut.gppin:2']]+w[:,c['xdut.gppip:2']]]
            for i,y in enumerate(arrays):axes[i,j].plot(t[s],y[s]*1e6,color=colors[variant],ls=styles[variant],lw=1.3,label='Previous: ideal L0' if variant=='ideal_L0' else 'Restored: real L0')
        for i,label in enumerate(['L0 source incident current (uA)','X025 input gates (uA)','GPP IO input gates (uA)']):
            ax=axes[i,j];ax.set(xlim=(-15,stop),ylabel=label);ax.axhline(0,color='#999',lw=.7);ax.grid(alpha=.17)
        axes[-1,j].set_xlabel('Time from command midpoint at 48 ns (ps)');axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
    axes[0,0].legend(fontsize=8);fig.suptitle('L0 source and its complete four-gate load',fontsize=13)
    fig.supxlabel('Same real-load fixture | positive into element; source = old ideal-source port or new MN+MP drains\nThree rows sum to L0 KCL. Total ports include displacement; no channel/diode fractions are identified.',fontsize=8)
    fig.savefig(OUT/'real_L0_source_load_currents.png',dpi=165);plt.close(fig)


def report(data):
    complete=set(data)==set(HASHES)
    lines=['# 真实 L0 源级恢复：结果分析','',
        '状态：'+('FF／SS 双角结果已回收。' if complete else '仅 FF 已回收并核对；SS 原 run 排队／待回收，不据此推断 SS。'),'',
        '从已完成单级 IO GPP 版本恢复原 BBM 最后一级反相器，两只核心管，L0 全部四个实际栅极负载保留。X025、GPP IO、ABC、Rgate 与物理负载不变。理想边界仅移至前级 NAND 输出 N，不补偿延迟；尚非完整 BBM。','',
        '测试：FF 0.99 V／SS 0.81 V，−40°C，52 ns；外部采样窗口／关闭沿不变，比较器保持复位；理想 N 与电源，无噪声、失配、PEX。','',
        '| 角落 | 新增 L0SRC 超限 | X025 超限记录：旧→新 | X025 最大端压 V：旧→新 | GPP 超限：旧→新 |',
        '| --- | --- | --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['ideal_L0'],pair['real_L0'];s=b['groups']['L0SRC'];x,y=a['groups']['X025'],b['groups']['X025'];g,h=a['groups']['GPP'],b['groups']['GPP']
        lines.append(f"| {corner} | {s['strict_exceed']}/{s['records']} | {x['strict_exceed']}/{x['records']} → {y['strict_exceed']}/{y['records']} | {x['worst_abs_V']:.6f} → {y['worst_abs_V']:.6f} | {g['strict_exceed']}/{g['records']} → {h['strict_exceed']}/{h['records']} |")
    lines+=['','筛查采用原模型门限：核心 0.99 V，IO 暂用 1.98 V。新增源级实际端压不合格不能被 GPP 的 IO 余量掩盖；原生 CMI 与比较器负载的微伏级严格超限保留。','']
    for corner,pair in data.items():
        a,b=pair['ideal_L0'],pair['real_L0'];l=b['rails']['xdut.l0'];p=b['rails']['xdut.pre'];ga,gb=a['rails']['xdut.gppdrv'],b['rails']['xdut.gppdrv']
        lines.append(f"- {corner}：L0 {l['min']*1e3:.3f} mV 至 {l['max']:.6f} V；PRE {p['min']*1e3:.3f} mV 至 {p['max']:.6f} V。GPPDRV {ga['min']:.6f}/{ga['max']:.6f} → {gb['min']:.6f}/{gb['max']:.6f} V。")
    if 'sscold' in data:lines+=['','SS 的 486 项均未超限，原生无 CMI，仅保留 SFE-1131／VACOMP-2435；这与 0.81 V 供电有较大核心端压余量有关，不能解释为动态扰动消失。FF 总计 28/486 项严格超限：新增源级 6、X025 10、比较器负载 12；其中超过 1 mV 的为 14 项。']
    lines+=['','![源级与负载电压](generated/real_l0_comparison/real_L0_voltage_comparison.png)','',
        'FF 新增失效归属：L0SRC 的 ds／bd 因 L0 超出电源轨而超限，另有两条 gd 约 20.77 µV 的严格超限。原理想 L0 钳住了这些边界。L0 正向峰直接出现在 X025 NMOS 的 gs／gb，负向峰加重 PMOS 的 |gs|／|gb|；因此 X025 不再只是输出端超限。PRE 原有动态扰动也增大。这是恢复真实源级后暴露的接口问题，不是完整 BBM 修复通过。','',
        '![L0 源级与全部负载电流](generated/real_l0_comparison/real_L0_source_load_currents.png)','']
    for corner,pair in data.items():
        b=pair['real_L0'];l=b['source_leading_positive'];q=l['leading_charge_C']
        lines.append(f"- {corner}：L0 正向前沿 {l['start_native_s']*1e9:.9f}–{l['peak_native_s']*1e9:.9f} ns，源级 MN/P drain 积分 {q['MN_D']*1e15:+.6f}/{q['MP_D']*1e15:+.6f} fC，X025／GPP 栅端 {q['X025_gates']*1e15:+.6f}/{q['GPP_IO_gates']*1e15:+.6f} fC；最大 KCL 残差 {l['max_lobe_KCL_A']:.3g} A。")
    lines+=['','该正向前沿中，源级两条 D 端合计净输出电荷，X025／GPP 栅端净吸收；负载并非该区间的净注入者。电流符号均为流入各器件端口为正。前沿总端口流和电荷积分可区分交换方向；不能从总 D/G/S/B 电流推出内禀 Cgd 比例、沟道工作区或二极管电流比例。新 N 输入仍为理想源，未包含真实上游 NAND 的输出阻抗与反馈。','',
        '| 角落 | 新 N→L0 延迟 ps，关低／开低 | GNN 比 GPP 滞后 ps：旧→新 | 最晚低参考 ±1 mV 建立 ns：旧→新 |',
        '| --- | --- | --- | --- |']
    def on(d):
        values=[x['remained_inside_from_native_s'] for x in d['correct_ON_settling']['low_after_turnon'].values()]
        return '未建立' if any(x is None for x in values) else f'{max(values)*1e9:.6f}'
    def timing(d,key):return '/'.join(f"{d['timing'][s][key]*1e12:.3f}" for s in ['disable_low','enable_low'])
    for corner,pair in data.items():
        a,b=pair['ideal_L0'],pair['real_L0'];lines.append(f"| {corner} | {timing(b,'N_to_L0_s')} | {timing(a,'GNN_after_GPP_control_skew_s')} → {timing(b,'GNN_after_GPP_control_skew_s')} | {on(a)} → {on(b)} |")
    lines+=['','时序取实际半 VDD 交点，正控制间隔不证明无同时导通。建立误差逐侧比较当前选中参考，只在正确 ON 窗口判断；关断间隙另存 JSON。建立相近不能抵消端压失效。','',
        '| 角落 | 新 L0SRC 直接 VDD 能量 fJ | 理想边界源净功 fJ：旧 L0／新 N | 新内部 L0 输出→栅负载 fJ |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['ideal_L0'],pair['real_L0'];wa,wb=a['source_and_internal_work'],b['source_and_internal_work']
        lines.append(f"| {corner} | {b['stage_direct_VDD_energy_J']['L0_original_core_driver']*1e15:.3f} | {wa['L0_net_delivered_J']*1e15:.3f} / {wb['N_source_net_delivered_J']*1e15:.3f} | {wb['L0_net_delivered_J']*1e15:.3f} |")
    lines+=['','以上为 0–52 ns 本台端口能量。旧 L0 与新 N 是不同外部边界，不能直接据净功减少宣称节能；新增反相器消耗 VDD 能量。新 L0／PRE 工作属于内部传递，不能再作为外部电源相加，也不是 ADC 功耗结论。','',
        '结论：真实驱动恢复暴露了新增核心源级及 X025 输入端失效；GPP IO 筛查余量仍在，边沿扰动尚未解决。保持条件源与历史结果，不采用新基线、不新建候选，等待本轮已提交 SS 原 run。' if not complete else '结论：双角仅完成这个源级切片的诊断；核心驱动失效、边沿扰动及理想上游接口仍未闭环。不采用新基线，也不生成新候选。','',
        '**一个优先建议：补齐 N 的真实驱动契约。** 下一项应验证原上游 `XBBM0.X004.X000` NAND 的实际边沿和回灌，而不先同时更换 L0SRC／X025 或调整内部时序。这样才能判断当前理想 10 ps N 边沿对尖峰的影响，再确定核心源级与接收级的修复方向。此处仅提出建议，未准备新候选或仿真。','',
        '## 证据','',
        '逐文件回执 SHA／大小、冻结输入 SHA、原生 PASS／PSF_END、完整单调时间与无损导出散列已核对。完整端压记录为同目录 `generated/real_l0_comparison/terminal_pairs.csv`，数值、源级新增端压、体端、告警及积分保存在 `comparison.json`。','']
    for corner,pair in data.items():
        for variant,d in pair.items():lines.append(f"- `{d['run']}`：{d['native_points']} 点，result SHA256 `{d['result_sha256']}`。")
    (HERE/'real_l0_findings.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze(corners):
    OUT.mkdir(exist_ok=True);waves={};data={};rows=[]
    for corner in corners:
        waves[corner]={'ideal_L0':load_ideal(corner),'real_L0':load_real(corner)};data[corner]={}
        for variant,d in waves[corner].items():
            s,q=summary(d,corner,variant);data[corner][variant]=s;rows.extend(q)
        assert data[corner]['ideal_L0']['native_effective_settings']==data[corner]['real_L0']['native_effective_settings']
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,
        coverage='FF+SS completed' if set(corners)==set(HASHES) else 'FF only; SS not available'),indent=2)+'\n')
    figures(waves);report(data)
    print('REAL_L0_COMPARISON_READY',corners,'terminal records',len(rows))
    for corner,pair in data.items():print(corner,{v:d['groups'] for v,d in pair.items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--corners',nargs='+',choices=list(HASHES),default=['ffcold']);args=parser.parse_args();analyze(args.corners)
