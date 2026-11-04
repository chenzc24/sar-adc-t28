"""Bound completed small native exports to frozen GPP implementation comparison."""
import argparse,csv,gzip,hashlib,json,os,re
from pathlib import Path
import numpy as np
from analyze_real_pre import load_real
from compare_io_cell import HERE,ROOT,digest,error_bounds

OUT=HERE/'generated/gpp_single_io_comparison'
HASHES={'ffcold':'f75375b04ba9631de7d93636fb5323717ec57046cc6da0068688e56b22bfb3b0',
        'sscold':'1933f7950fcca2fa5e96c9b9cf03205a5bad25d117a042d7be37ce95b9c72317'}


def load_new(corner):
    name='sar8audit-gpp-singleio-'+corner;folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert receipt['status']['registered']['recipe_hash']==HASHES[corner] and not receipt['skipped'] and len(receipt['files'])==11
    for item in receipt['files']:
        path=folder/item['name'];assert path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
    assert receipt['total_bytes']==sum(x['bytes'] for x in receipt['files'])
    assert receipt['total_bytes']=={'ffcold':6013768,'sscold':5992515}[corner]
    cfgpath=HERE/'generated/gpp_single_io_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text())
    for x in json.loads((cfgpath.parent/'recipe_proposal.json').read_text())['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());state=json.loads((folder/'simulation.state.json').read_text())
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['measurement_sha256']==digest(cfgpath)
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==462 and r['native_PSF_END']
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');path=folder/'derived'/e['file']
    assert digest(path)==e['sha256'];raw=gzip.decompress(path.read_bytes())
    assert len(raw)==e['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256']
    w=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']))
    assert w.shape==(r['native_points'],132) and w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    assert r['native_points']=={'ffcold':8844,'sscold':8346}[corner]
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(e['columns'])},
                receipt_bytes=receipt['total_bytes'],result_sha256=digest(folder/'derived/result.json'),managed_recipe_sha256=HASHES[corner])


def summarize(d,corner,variant):
    r,m=d['result'],d['result']['cell_measurements'];rows=[];groups={}
    for p in d['cfg']['selected_mos_pair_screens']:
        n=p['instance'];key=n+':'+p['terminal'];x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
        group='X025' if '.X025.' in n else 'GPP' if re.fullmatch(r'XDUT.GPP(?:[ABC]|I)[NP]',n) else 'GNN_ABC' if re.fullmatch(r'XDUT.GNN[ABC][NP]',n) else 'physical_load'
        rows.append(dict(corner=corner,variant=variant,group=group,pair=key,model=p['model'],screen_V=p['screen_v'],abs_peak_V=peak,excess_V=peak-p['screen_v']))
    for group in ['GPP','X025','GNN_ABC','physical_load']:
        q=[x for x in rows if x['group']==group];worst=max(q,key=lambda x:x['excess_V'])
        groups[group]=dict(records=len(q),strict_exceed=sum(x['excess_V']>0 for x in q),exceed_over1mV=sum(x['excess_V']>.001 for x in q),
                           worst_pair=worst['pair'],worst_abs_peak_V=worst['abs_peak_V'],worst_excess_mV=worst['excess_V']*1e3)
    peak_events={};w,c=d['w'],d['c']
    devices=['xdut.gppin','xdut.gppip'] if variant=='single_IO' else ['xdut.gppcn','xdut.gppcp']
    for label,kind in [('early_negative','min'),('early_positive','max')]:
        x=r['voltage_and_current_extrema']['xdut.gppdrv'];time=x[kind+'_time_s'];idx=int(np.argmin(abs(w[:,0]-time)));assert abs(w[idx,0]-time)<1e-18
        dev={n:{str(j):float(w[idx,c[n+':'+str(j)]]) for j in [1,2,3,4]} for n in devices}
        rg=float(w[idx,c['xdut.rgpp0:1']]);res=sum(x['1'] for x in dev.values())+rg
        peak_events[label]=dict(time_s=time,L0_V=float(w[idx,c['l0']]),GPPDRV_V=x[kind],GPP0_V=float(w[idx,c['xdut.gpp0']]),
                               incident_total_DGSB_A=dev,Rgate_incident_A=rg,KCL_residual_A=res,
                               note='Early input-edge disturbance of the old output level, before the intended inversion completes; native total ports do not identify intrinsic capacitance/channel fractions.')
    body=[x for x in m['body_forward_polarity'] if re.match(r'XDUT.GPP(?:[ABC]|I)[NP]:',x['pair'])]
    worstbody=max(body,key=lambda x:x['signed_forward_max_V'])
    energies=m['restored_stage_direct_VDD_energy_J'];gpp=sum(v for n,v in energies.items() if n.startswith('GPP'))
    return dict(run=d['run'],result_sha256=d['result_sha256'],native_points=r['native_points'],groups=groups,
        native_effective_settings=r['native_effective_settings'],native_warning_codes=r['native_warning_codes'],
        timing={n:{k:v for k,v in q.items() if k!='native_edge_witnesses'} for n,q in m['actual_stage_timing'].items()},
        halfVDD_gaps={n:q['signed_halfVDD_control_gap_s'] for n,q in m['actual_same_side_control_gaps'].items()},
        rails=m['supply_rail_excursions'],correct_ON_settling=m['correct_ON_settling'],
        off_gap={n:error_bounds(w,c,n,ref,46.995e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]},
        input_loads=m['real_PRE_and_L0_loads'],source_work=m['source_and_internal_work'],stage_direct_VDD_energy_J=energies,
        GPP_direct_VDD_energy_J=gpp,fixture_direct_VDD_energy_J=m['ideal_VDD_energy_J'],
        GPP_body_max_forward=worstbody,GPP_peak_events=peak_events,
        opposed_total_reference_current=m['opposed_reference_terminal_current'],
        max_absolute_KCL_residual_A=max(x['max_abs_a'] for x in r['node_kcl'].values())),rows


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    corners=list(waves);colors={'old':'#6c7076','single_IO':'#126da1'};styles={'old':'--','single_IO':'-'}
    fig,axes=plt.subplots(4,len(corners),figsize=(6.3*len(corners),9),layout='constrained',squeeze=False)
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c']
            for i,(node,edge,stop) in enumerate([('xdut.pre',48,35),('xdut.gppdrv',43,180),('xdut.gppdrv',48,180),('xdut.gpp0',48,450)]):
                t=(w[:,0]-edge*1e-9)*1e12;s=(t>=-22)&(t<=stop)
                axes[i,j].plot(t[s],w[s,c[node]],color=colors[variant],ls=styles[variant],lw=1.4,label='Old: 3 core stages' if variant=='old' else 'New: 1 IO stage')
            if variant=='single_IO':
                axes[3,j].plot(t[s],w[s,c['xdut.gnn0']],color='#bd6631',ls=':',lw=1.3,label='GNN0 (unchanged branch)')
        rail=.99 if corner=='ffcold' else .81
        for i in range(4):
            for level in [0,rail]:axes[i,j].axhline(level,color='#999',ls=':',lw=.7)
        for i,(label,edge,stop) in enumerate([('PRE / X025 (V)',48,35),('GPPDRV (V)',43,180),('GPPDRV (V)',48,180),('Reference gates (V)',48,450)]):
            ax=axes[i,j];ax.set(xlim=(-22,stop),ylabel=label,xlabel=f'Time from L0 midpoint at {edge} ns (ps)');ax.axvline(0,color='#aaa',lw=.7);ax.grid(alpha=.17);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
    axes[0,0].legend(fontsize=8,loc='upper right');axes[3,0].legend(fontsize=8,loc='lower right')
    fig.suptitle('Single IO GPP: larger edge kicks; X025 remains unchanged',fontsize=13)
    fig.supxlabel('Real X025 + GNN ABC IO + physical CDAC/reference/Bootstrap; ideal L0/rails; comparator held reset\nNo edge alignment; horizontal dotted lines = 0/VDD, not IO rating. No noise, mismatch or PEX.',fontsize=8)
    fig.savefig(OUT/'GPP_single_IO_edges.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,len(corners),figsize=(6.3*len(corners),8),layout='constrained',squeeze=False)
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9
            for node,style,label in [('xdut.gnn0','-','GNN0'),('xdut.gpp0','--','GPP0')]:
                if variant=='single_IO':axes[0,j].plot(t,w[:,c[node]],style,lw=1.3,label=label)
            for i,(a,b,selecthigh) in enumerate([(44.005,46.995,True),(48.005,50,False)],1):
                s=(t>=a)&(t<b)
                for node,ref,style in [('xdut.xcdac.bn0','vrefp' if selecthigh else 'vrefn','-'),('xdut.xcdac.bp0','vrefn' if selecthigh else 'vrefp','--')]:
                    y=(w[:,c[node]]-w[:,c[ref]])*1e3
                    axes[i,j].plot(t[s],y[s],color=colors[variant],ls=style,lw=1.25,alpha=.9,label=('Old' if variant=='old' else 'New')+' '+('BN0' if node.endswith('bn0') else 'BP0'))
        axes[0,j].set(xlim=(42.95,49.35),ylabel='Actual load gates (V)');axes[0,j].legend(fontsize=8,loc='center right')
        axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
        for i,window in [(1,(44.005,46.995)),(2,(48.005,50))]:
            ax=axes[i,j];ax.set(xlim=window,ylabel='Bottom - selected ref (mV)');ax.set_yscale('symlog',linthresh=1)
            ax.axhspan(-1,1,color='#258578',alpha=.11);ax.axhline(0,color='#888',lw=.6);ax.legend(fontsize=7,ncol=2,loc='upper right')
        for ax in axes[:,j]:ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x');ax.set_xlabel('Native time (ns)')
    fig.suptitle('Correct ON windows: high selection, then low selection',fontsize=13)
    fig.supxlabel('Same physical-load fixture and external commands; top = new actual gates, lower rows = old/new errors\nReference follows actual VREFP/VREFN; green +/-1 mV is diagnostic only. Error axes are symmetric-log.',fontsize=8)
    fig.savefig(OUT/'GPP_single_IO_settling.png',dpi=165);plt.close(fig)


def report(data):
    lines=['# GPP 单级 IO 对照：实际结果','',
        '三段核心反相器改为一对 IO 管，其余 140 条器件记录、Rgate、负载、模型设置与外部时序不变。器件数及寄生同时改变；本结果只评价该驱动块实现，不归因于某一只管。','',
        '测试：FF 0.99 V／SS 0.81 V，均 −40°C，52 ns；真实 X025、GNN ABC、CDAC／参考／Bootstrap 负载，理想 L0／电源，比较器保持复位；无噪声、失配或 PEX。','',
        '| 角落 | GPP 端压超限记录：旧→新 | GPPDRV 最小／最大 V：旧→新 | X025 最大端压 V：旧→新 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['old'],pair['single_IO'];ga,gb=a['groups']['GPP'],b['groups']['GPP'];ra,rb=a['rails']['xdut.gppdrv'],b['rails']['xdut.gppdrv']
        lines.append(f"| {corner} | {ga['strict_exceed']}/{ga['records']} → {gb['strict_exceed']}/{gb['records']} | {ra['min']:.6f}/{ra['max']:.6f} → {rb['min']:.6f}/{rb['max']:.6f} | {a['groups']['X025']['worst_abs_peak_V']:.6f} → {b['groups']['X025']['worst_abs_peak_V']:.6f} |")
    lines+=['','核心门限 0.99 V，IO 暂用 1.98 V 筛查。**GPP 筛查改善不代表尖峰变小**：新输出更偏离电源轨；FF 的 X025 残余与比较器负载微伏级严格超限仍需单独报告，原生 CMI 保留。','']
    for corner,pair in data.items():
        a,b=pair['old'],pair['single_IO'];ra,rb=a['rails']['xdut.gpp0'],b['rails']['xdut.gpp0'];body=b['GPP_body_max_forward']
        lines.append(f"- {corner}：实际参考栅 GPP0 最小／最大 {ra['min']:.6f}/{ra['max']:.6f} → {rb['min']:.6f}/{rb['max']:.6f} V；GNN0 最小仍为 {b['rails']['xdut.gnn0']['min']*1e3:.3f} mV。新 GPP 最大体结正向极性 {body['signed_forward_max_V']*1e3:.3f} mV，对应 bulk 总电流 {body['body_current_at_forward_peak_A']*1e6:.3f} µA；不能据此直接认定二极管导通或其电流比例。")
    lines+=['', '![边沿及实际栅极](generated/gpp_single_io_comparison/GPP_single_IO_edges.png)','',
        '48 ns 的 L0 上升期间，GPPDRV 在完成下降前先正向抬升；43 ns 的下降期间则先负向下冲。它们是原有输出电平受到输入边沿扰动，不能当成最终静态电平。原生 D/G/S/B 与 Rgate 电流及 KCL 支持局部动态电荷交换，但不提供内禀 Cgd、沟道与结电流分量。原三级链的中间级已删除，直接 IO 输入的负载与响应也同时改变。','',
        '| 角落 | GNN 比 GPP 滞后 ps，关低／开低：旧→新 | 最晚低参考 ±1 mV 建立 ns：旧→新 | L0 边沿绝对电荷 fC，关低／开低：旧→新 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        def skew(d):return '/'.join(f"{d['timing'][s]['GNN_after_GPP_control_skew_s']*1e12:.2f}" for s in ['disable_low','enable_low'])
        def on(d):
            v=[x['remained_inside_from_native_s'] for x in d['correct_ON_settling']['low_after_turnon'].values()]
            return '未建立' if any(x is None for x in v) else f'{max(v)*1e9:.6f}'
        def charge(d):return '/'.join(f"{d['input_loads']['L0_shared']['event_charge'][s]['absolute_C']*1e15:.3f}" for s in ['disable_low','enable_low'])
        a,b=pair['old'],pair['single_IO'];lines.append(f'| {corner} | {skew(a)} → {skew(b)} | {on(a)} → {on(b)} | {charge(a)} → {charge(b)} |')
    lines+=['','时序均以实际电压的半 VDD 交点计，无内部波形对齐；正间隔不等于证明无同时导通。GNN 路径基本不变，分支差缩小来自 GPP 变慢；SS 的关低／开低延迟分别增加约 40／48 ps，不能称为整体提速。建立误差逐侧比较当前选中参考，只在正确 ON 窗口判定；46.995–47.995 ns 关断间隙的残差另存 JSON，不作 ON 建立失败。','',
        '![正确 ON 窗口](generated/gpp_single_io_comparison/GPP_single_IO_settling.png)','',
        '| 角落 | GPP 直接 VDD 能量 fJ：旧→新 | L0 理想源净供能 fJ：旧→新 |',
        '| --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['old'],pair['single_IO'];lines.append(f"| {corner} | {a['GPP_direct_VDD_energy_J']*1e15:.3f} → {b['GPP_direct_VDD_energy_J']*1e15:.3f} | {a['source_work']['L0_net_delivered_J']*1e15:.3f} → {b['source_work']['L0_net_delivered_J']*1e15:.3f} |")
    lines+=['','以上均为 0–52 ns 该测试台的端口能量。L0 供能、内部 PRE 传递与 VDD 端口能量分别计量，不相加作整机功耗结论；实际 L0 驱动尚未接入，其负载变重不能被理想源掩盖。','',
        '结论：单级 IO 为 GPP 提供端压筛查余量，负载最晚建立约推迟 4 ps，但边沿扰动和输入负载更大。X025、GNN 的下冲、真实 BBM 接口及整机验证仍未闭环；本次不采用新基线，也不生成下一候选。','',
        '## 可复核记录','',
        '全部来源回执、逐文件 SHA/大小、冻结输入 SHA、原生 PASS/PSF_END、单调原生时间戳与导出散列均核对。旧版每角 498 项、新版 474 项；完整记录见 `generated/gpp_single_io_comparison/terminal_pairs.csv`，数值及当前告警见同目录 `comparison.json`。','']
    for corner,pair in data.items():
        for variant,d in pair.items():lines.append(f"- `{d['run']}`：{d['native_points']} 个原生点，result SHA256 `{d['result_sha256']}`。")
    (HERE/'gpp_single_io_findings.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze(corners):
    OUT.mkdir(exist_ok=True);waves={};data={};rows=[]
    for corner in corners:
        waves[corner]={'old':load_real(corner),'single_IO':load_new(corner)};data[corner]={}
        for variant,d in waves[corner].items():
            summary,q=summarize(d,corner,variant);data[corner][variant]=summary;rows.extend(q)
        assert data[corner]['old']['native_effective_settings']==data[corner]['single_IO']['native_effective_settings']
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,
        scope='One GPP implementation comparison only; ideal L0, unchanged actual X025/ABC/physical load; no complete-chain acceptance'),indent=2)+'\n')
    figures(waves);report(data)
    print('GPP_SINGLE_IO_COMPARISON_READY',corners,'terminal records',len(rows))
    for c,pair in data.items():print(c,{v:d['groups'] for v,d in pair.items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--corners',nargs='+',choices=list(HASHES),default=list(HASHES));args=parser.parse_args();analyze(args.corners)
