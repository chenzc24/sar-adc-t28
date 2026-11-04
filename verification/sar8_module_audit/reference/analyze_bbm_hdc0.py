"""Same-axis HD C0 comparison; completed small native tables, no new simulations."""
import argparse,csv,gzip,json,os,re,textwrap
import hashlib
import numpy as np
from analyze_real_bbm import digest,window,HERE,ROOT

OUT=HERE/'generated/bbm_hdc0_comparison'
HASHES={'base':{'ffcold':'7559d2fd8cb85edf5034c7711babe6f653611d0b52bba9b122f2b1616b87820a','sscold':'6bea4e28904ad1adfd0ba8791fbe1f9caf5a6c80d15870218dab2c2ae39e89ec'},
        'x4':{'ffcold':'97c93bdf4a718ddce8129b348d98c442a71a689d8aa35e3bae909ce356153ef3','sscold':'0637635277e9c930917f811951e9de090ab01cdeee85810a60b573c4cf638973'}}


def load(variant,corner):
    name=('sar8audit-real-bbm-' if variant=='base' else 'sar8audit-bbm-hdc0x4-')+corner
    folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert not receipt['skipped'] and len(receipt['files'])==11 and receipt['status']['registered']['recipe_hash']==HASHES[variant][corner]
    for x in receipt['files']:
        path=folder/x['name'];assert path.stat().st_size==x['bytes'] and digest(path)==x['sha256']
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']
    if variant=='x4':assert receipt['total_bytes']=={'ffcold':22574580,'sscold':22387216}[corner]
    cfgpath=HERE/'generated'/('real_bbm_v1' if variant=='base' else 'bbm_hdc0_v1')/corner/'measurement.json';cfg=json.loads(cfgpath.read_text())
    for x in json.loads((cfgpath.parent/'recipe_proposal.json').read_text())['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());state=json.loads((folder/'simulation.state.json').read_text());m=r['cell_measurements']
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END'] and r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==656
    assert r['measurement_sha256']==digest(cfgpath) and state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');assert len(e['columns'])==376
    wanted=set(cfg['diagnostic_voltage_columns'])|{'time','vcode:1','vvdd:1','rrefp:1','rrefn:1'}
    for s in ['n','p']:wanted.update('xdut.xcdac.xs'+s+'0.'+k+':1' for k in ['mn_low','mp_high'])
    for leg in ['hd','ld']:wanted.update('xdut.xbbm0.xd_'+leg+'.mp_clear:'+str(j) for j in [1,2,3,4])
    wanted.update(m['CODE_source_and_input_load']['incident_load_branches'])
    assert wanted<=set(e['columns']);ids=[j for j,n in enumerate(e['columns']) if n in wanted];names=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');h=hashlib.sha256();count=0;stride=len(e['columns'])*8;size=0
    with gzip.open(folder/'derived'/e['file'],'rb') as stream:
        while True:
            raw=stream.read(stride*128)
            if not raw:break
            assert len(raw)%stride==0;h.update(raw);size+=len(raw);block=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']))
            w[count:count+len(block)]=block[:,ids];count+=len(block)
    assert count==r['native_points'] and size==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    if variant=='x4':assert count=={'ffcold':11421,'sscold':10861}[corner]
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(names)},result_sha256=digest(folder/'derived/result.json'),
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=HASHES[variant][corner],test_sha256=digest(cfgpath.parent/'test.scs'))


def duration(t,y,limit):
    total=0.
    for a,b,p,q in zip(t[:-1],t[1:],y[:-1],y[1:]):
        cuts=[0.,1.]
        if q!=p:
            cuts += [f for f in [(-limit-p)/(q-p),(limit-p)/(q-p)] if 0<f<1]
        cuts.sort()
        for x,z in zip(cuts[:-1],cuts[1:]):
            if abs(p+(q-p)*(x+z)*.5)>limit:total+=(b-a)*(z-x)
    return float(total)


def reset(d):
    w,c=d['w'],d['c'];answer={};supply=d['result']['supply_V']
    for leg,a,b,mid,inp in [('HD',48.005e-9,52e-9,48e-9,'code'),('LD',43.005e-9,47.995e-9,43e-9,'xdut.xbbm0.cb')]:
        ids=np.flatnonzero((w[:,0]>=a)&((w[:,0]<=b) if leg=='HD' else (w[:,0]<b)));events=[e for e in d['result']['half_vdd_events'].get(inp,[]) if e['direction']=='falling' and mid-20e-12<=e['estimated_time_s']<=b]
        edge=events[0]['estimated_time_s'] if len(events)==1 else None;nodes={}
        for node,target in [('xdut.xbbm0.xd_'+leg.lower()+'.rc0',0.),('xdut.xbbm0.xd_'+leg.lower()+'.rc1',supply),('xdut.xbbm0.'+leg.lower(),0.)]:
            y=w[ids,c[node]]-target;bad=np.flatnonzero(abs(y)>supply*.01);first=None if len(bad) and bad[-1]==len(ids)-1 else int(bad[-1]+1) if len(bad) else 0
            entry=None if first is None else float(w[ids[first],0]);nodes[node]=dict(entry_s=entry,final_error_V=float(y[-1]),
                delay_from_CODE_s=None if entry is None else entry-mid,delay_from_actual_input_s=None if entry is None or edge is None else entry-edge)
        answer[leg]=dict(actual_input_half_s=edge,nodes=nodes)
    return answer


def summarize(d,corner,variant):
    r,m,w,c=d['result'],d['result']['cell_measurements'],d['w'],d['c'];rows=[];groups={}
    for p in d['cfg']['selected_mos_pair_screens']:
        n=p['instance'];key=n+':'+p['terminal'];x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
        group='BBM' if n.startswith('XDUT.XBBM0.') else 'H_driver' if n.startswith('XDUT.X008.') or re.fullmatch(r'XDUT.G(?:NP|PN)[ABC][NP]',n) else 'X025' if '.X025.' in n else 'GNN_ABC_IO' if re.fullmatch(r'XDUT.GNN[ABC][NP]',n) else 'GPP_IO' if re.fullmatch(r'XDUT.GPPI[NP]',n) else 'physical_load'
        rows.append(dict(corner=corner,variant=variant,group=group,pair=key,model=p['model'],screen_V=p['screen_v'],abs_peak_V=peak,excess_V=peak-p['screen_v']))
    for name in sorted({x['group'] for x in rows}):
        q=[x for x in rows if x['group']==name];groups[name]=dict(records=len(q),strict_exceed=sum(x['excess_V']>0 for x in q),over1mV=sum(x['excess_V']>.001 for x in q),worst=max(q,key=lambda x:x['excess_V']))
    physical={phase:{n:window(d,n,ref,a,b,closed) for n,ref in pairs} for phase,a,b,closed,pairs in [
        ('high',43.005e-9,47.995e-9,False,[('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]),
        ('low',48.005e-9,52e-9,True,[('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')])]}
    resets=reset(d);stress={}
    for leg in ['hd','ld']:
        stem='xdut.xbbm0.xd_'+leg+'.';rc=w[:,c[stem+'rc1']];rail=w[:,c['vdd!']];y=w[:,c['xdut.xbbm0.'+leg]]
        stress[leg.upper()]=dict(RC1_extrema=m['supply_rail_excursions'][stem+'rc1'],
            X005_gd_peak_V=float(max(abs(rc-y))),X005_gd_above0p99_duration_s=duration(w[:,0],rc-y,.99),
            X005_gd_above0p991_duration_s=duration(w[:,0],rc-y,.991),
            MP_CLEAR_ds_peak_V=float(max(abs(rc-rail))),MP_CLEAR_ds_above0p99_duration_s=duration(w[:,0],rc-rail,.99),
            MP_CLEAR_body=m['body_forward_polarity'][next(j for j,x in enumerate(m['body_forward_polarity']) if x['pair']=='XDUT.XBBM0.XD_'+leg.upper()+'.MP_CLEAR:bd')],
            MP_CLEAR_D_charge=r['current_charge_trapezoids'][stem+'mp_clear:1'],MP_CLEAR_D_extrema=r['voltage_and_current_extrema'][stem+'mp_clear:1'])
    if variant=='x4':
        for phase,label in [('high','select_high'),('low','select_low')]:
            for n,x in physical[phase].items():
                q=m['physical_command_phase_reference_settling'][label]['nodes'][n]
                assert x['remained_inside_from_native_s']==q['remained_inside_from_native_s'] and x['diagnostic_established']==q['diagnostic_established']
        for leg,q in resets.items():
            for n,x in q['nodes'].items():assert x['entry_s']==m['delay_leg_reset_diagnostics'][leg]['nodes'][n]['remained_inside_from_native_s']
    return dict(run=d['run'],result_sha256=d['result_sha256'],native_points=d['native_points'],receipt_bytes=d['receipt_bytes'],
        managed_recipe_sha256=d['managed_recipe_sha256'],groups=groups,physical_phase_settling=physical,reset=resets,RC1_and_clear_stress=stress,
        control_events=m['actual_control_events'],sampled_HL=m['sampled_HL_mutual_exclusion'],opposed_reference_ports=m['opposed_total_reference_terminal_current'],
        legacy_halfVDD_windows=m['actual_correct_ON_settling'],CODE_source=m['CODE_source_and_input_load'],stage_energy_J=m['reference_control_direct_VDD_energy_J'],
        internal_work=m['internal_driver_load_work'],rails=m['supply_rail_excursions'],body=m['body_forward_polarity'],
        warnings=r['native_warning_codes'],native_settings=r['native_effective_settings'],acceptance_pass=None),rows


def figures(waves,data):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False});corners=list(waves);styles={'base':'--','x4':'-'}
    fig,axes=plt.subplots(4,len(corners),figsize=(6.4*len(corners),9),layout='constrained',squeeze=False)
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=42.98)&(t<=44.3);tag='C0x1' if variant=='base' else 'C0x4'
            for n,color,label in [('xdut.h0','#c76631','H'),('xdut.l0','#126da1','L')]:axes[0,j].plot(t[s],w[s,c[n]],styles[variant],color=color,lw=1.3,label=tag+' '+label)
            for n,color,label in [('xdut.gnn0','#126da1','GNN0'),('xdut.gnp0','#c76631','GNP0')]:axes[1,j].plot(t[s],w[s,c[n]],styles[variant],color=color,lw=1.3,label=tag+' '+label)
            for n,color,label in [('xdut.xcdac.xsn0.mn_low:1','#126da1','Low D'),('xdut.xcdac.xsn0.mp_high:1','#c76631','High D')]:axes[2,j].plot(t[s],w[s,c[n]]*1e6,styles[variant],color=color,lw=1.3,label=tag+' '+label)
            axes[3,j].plot(t[s],(w[s,c['xdut.xcdac.bn0']]-w[s,c['vrefp']])*1e3,styles[variant],color='#126da1',lw=1.3,label=tag+' BN0 - VREFP')
        for i,label in enumerate(['H/L (V)','Actual N-side gates (V)','Total drain current (uA)','High-reference error (mV)']):
            ax=axes[i,j];ax.set(xlim=(42.98,44.3),ylabel=label);ax.grid(alpha=.17);ax.legend(fontsize=7,ncol=2,loc='upper right')
        axes[1,j].axhline((.99 if corner=='ffcold' else .81)*.5,color='#999',ls=':',lw=.8);axes[3,j].set_yscale('symlog',linthresh=1);axes[3,j].axhspan(-1,1,color='#258578',alpha=.1)
        axes[0,j].set_title(('FF /0.99 V' if corner=='ffcold' else 'SS /0.81 V')+' /-40 C');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('HD C0 x1 versus x4: actual gate ordering and reference load',fontsize=13)
    footer='Complete bit0 BBM/real H driver, GNN ABC IO/single IO GPP, physical CDAC/reference/Bootstrap; other bits static\nSame ideal CODE/rails/sample clock; comparator reset; no noise/mismatch/PEX. No internal time alignment; 1 mV is diagnostic.'
    fig.supxlabel('\n'.join(textwrap.fill(line,width=85 if len(corners)==1 else 160) for line in footer.split('\n')),fontsize=8)
    fig.savefig(OUT/'HDC0_gate_current_settling.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,len(corners),figsize=(6.4*len(corners),8),layout='constrained',squeeze=False)
    for j,corner in enumerate(corners):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;tag='C0x1' if variant=='base' else 'C0x4';s=(t>=42.99)&(t<=43.45);color='#777' if variant=='base' else '#126da1'
            axes[0,j].plot(t[s],w[s,c['xdut.xbbm0.xd_hd.rc1']],styles[variant],color=color,lw=1.3,label=tag+' RC1')
            axes[1,j].plot(t[s],abs(w[s,c['xdut.xbbm0.xd_hd.rc1']]-w[s,c['xdut.xbbm0.hd']]),styles[variant],color=color,lw=1.3,label=tag+' |Vgd(X005)|')
            ss=(t>=47.99)&(t<=48.15)
            for n,col,label in [('xdut.xbbm0.xd_hd.rc0','#126da1','RC0'),('xdut.xbbm0.xd_hd.rc1','#c76631','RC1')]:axes[2,j].plot(t[ss],w[ss,c[n]],styles[variant],color=col,lw=1.3,label=tag+' '+label)
        axes[0,j].axhline(.99 if corner=='ffcold' else .81,color='#999',ls=':',lw=.8);axes[1,j].axhline(.99,color='#b75336',ls=':',lw=.8,label='0.99 V core screen')
        for i,label in enumerate(['HD RC1 (V)','HD X005 |Vgd| (V)','HD reset RC0/RC1 (V)']):
            ax=axes[i,j];ax.set_ylabel(label);ax.set_xlim((42.99,43.45) if i<2 else (47.99,48.15));ax.grid(alpha=.17);ax.legend(fontsize=7,ncol=2,loc='upper right');ax.ticklabel_format(useOffset=False,axis='x');ax.set_xlabel('Native time (ns)')
        axes[0,j].set_title(('FF /0.99 V' if corner=='ffcold' else 'SS /0.81 V')+' /-40 C')
    fig.suptitle('RC1 stress remains a separate issue; HD reset also changes',fontsize=13)
    footer='Same complete-BBM/physical-load fixtures and external timing; only HD C0 multi1->4\nNegative RC1 peaks and both clear branches are retained in the full numerical comparison, not inferred from settling.'
    fig.supxlabel('\n'.join(textwrap.fill(line,width=85 if len(corners)==1 else 160) for line in footer.split('\n')),fontsize=8)
    fig.savefig(OUT/'HDC0_RC1_stress_reset.png',dpi=165);plt.close(fig)


def report(data):
    lines=['# HD C0 ×4 对照','',
        '状态：'+('FF／SS两角已回收。' if set(data)=={'ffcold','sscold'} else '当前仅FF完成回收，SS原run尚待回执；下述结果不推断SS。'),'',
        'C0×4减小了SS的后级负间隔和相反参考总端流，但没有消除负间隔；FF端压超限仍在，过压持续时间与输入能量增加。这组旧诊断到此结案，不采用新基线，后续转入标准单元迁移。' if 'sscold' in data else 'FF先行结果只用于诊断，SS未回收前不推断其门控次序。','',
        '仅 HD 延迟腿 C0 的 MOM 并联数从1改为4。其余195条器件记录与完整测试台不变；不对齐内部边沿。完整 bit0 BBM／高端驱动、GNN ABC IO／单级 IO GPP、物理 CDAC／参考／Bootstrap，其他位静态；CODE／电源／采样时钟理想，比较器复位。FF 0.99 V／SS 0.81 V，−40°C，52 ns，无噪声、失配、PEX。','',
        '| 角落 | 高方向 BBM 间隔 ps：1→4 | N侧／P侧实际栅极间隔 ps：1→4 | 低方向 N侧／P侧 ps：1→4 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['base'],pair['x4'];fmt=lambda d,phase,k:f"{d['control_events'][phase][k]*1e12:.3f}"
        high=lambda d:'/'.join(fmt(d,'select_high',k) for k in ['N_signed_off_to_on_gap_s','P_signed_off_to_on_gap_s']);low=lambda d:'/'.join(fmt(d,'select_low',k) for k in ['N_signed_off_to_on_gap_s','P_signed_off_to_on_gap_s'])
        lines.append(f"| {corner} | {fmt(a,'select_high','BBM_signed_off_to_on_gap_s')} → {fmt(b,'select_high','BBM_signed_off_to_on_gap_s')} | {high(a)} → {high(b)} | {low(a)} → {low(b)} |")
    lines+=['','间隔来自真实负载栅极的半 VDD 交点，不是 MOS 导通阈值。相反方向的参考总 D 电流另作对照，包含位移电流，不能直接当作纯沟道直通。','',
        '![同轴门控和参考电流](generated/bbm_hdc0_comparison/HDC0_gate_current_settling.png)','',
        '| 角落 | N侧0–52 ns相反总D电流较小者峰值 µA：1→4 | 高状态持续进入1 mV：BN0／BP0 ns，1→4 | 低状态进入1 mV ns，1→4 |',
        '| --- | --- | --- | --- |']
    def entry(d,phase):return '/'.join('未建立' if x['remained_inside_from_native_s'] is None else f"{x['remained_inside_from_native_s']*1e9:.6f}" for x in d['physical_phase_settling'][phase].values())
    for corner,pair in data.items():
        a,b=pair['base'],pair['x4'];lines.append(f"| {corner} | {a['opposed_reference_ports']['N']['peak_min_opposed_abs_A']*1e6:.3f} → {b['opposed_reference_ports']['N']['peak_min_opposed_abs_A']*1e6:.3f} | {entry(a,'high')} → {entry(b,'high')} | {entry(a,'low')} → {entry(b,'low')} |")
    lines+=['','高建立只评价 [43.005,47.995) ns，低建立评价 [48.005,52] ns，误差均相对实际选中参考。原跨半 VDD 终点的高窗口保留为切换诊断，其 false 不再误称稳态高参考未建立。1 mV 是既有诊断值。','',
        '| 角落／腿 | RC1最小／最大 V：1→4 | X005最大绝对Vgd V：1→4 | MP_CLEAR最大绝对Vds V：1→4 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        for leg in ['HD','LD']:
            a,b=[pair[v]['RC1_and_clear_stress'][leg] for v in ['base','x4']];rc=lambda d:f"{d['RC1_extrema']['min']:.6f}/{d['RC1_extrema']['max']:.6f}"
            lines.append(f"| {corner}/{leg} | {rc(a)} → {rc(b)} | {a['X005_gd_peak_V']:.6f} → {b['X005_gd_peak_V']:.6f} | {a['MP_CLEAR_ds_peak_V']:.6f} → {b['MP_CLEAR_ds_peak_V']:.6f} |")
    lines+=['','表中两项 |V| 表示端压绝对值。MP_CLEAR源/体均接VDD，所列绝对Vds也等于绝对Vbd；两腿clear在FF的负向RC1阶段都仍超限。RC1正、负两相及两条腿的clear D/体端峰值与电荷均保留在JSON，不能只检查X005接收栅极。超过门限的持续时间采用原生点间线性插值估计，仅用于比较，不是寿命签核。','',
        '| 角落 | HD X005绝对Vgd >0.991 V 累计时长 ps：1→4 | BBM／H驱动／X025／负载严格超限项数：1→4 |',
        '| --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['base'],pair['x4'];counts=lambda d:'/'.join(str(d['groups'][n]['strict_exceed']) for n in ['BBM','H_driver','X025','physical_load'])
        lines.append(f"| {corner} | {a['RC1_and_clear_stress']['HD']['X005_gd_above0p991_duration_s']*1e12:.3f} → {b['RC1_and_clear_stress']['HD']['X005_gd_above0p991_duration_s']*1e12:.3f} | {counts(a)} → {counts(b)} |")
    lines+=['','全部738项仍按原门限筛查：核心0.99 V、IO暂用1.98 V；上表0.991 V只用于排除微伏级边界的时长比较，不放宽筛查。两版 GNN/GPP IO、完整逐端压及原生告警均在 JSON/CSV 中保留。','',
        '![RC1和复位同轴对比](generated/bbm_hdc0_comparison/HDC0_RC1_stress_reset.png)','',
        '| 角落 | HD整腿复位进入1%延迟 ps：1→4 | LD整腿复位延迟 ps：1→4 | BBM直接VDD能量 fJ：1→4 | CODE源净供能 fJ：1→4 |',
        '| --- | --- | --- | --- | --- |']
    def rt(d,leg):
        x=[q['delay_from_CODE_s'] for q in d['reset'][leg]['nodes'].values()];return '未完成' if any(v is None for v in x) else f'{max(x)*1e12:.3f}'
    for corner,pair in data.items():
        a,b=pair['base'],pair['x4'];lines.append(f"| {corner} | {rt(a,'HD')} → {rt(b,'HD')} | {rt(a,'LD')} → {rt(b,'LD')} | {a['stage_energy_J']['BBM']*1e15:.3f} → {b['stage_energy_J']['BBM']*1e15:.3f} | {a['CODE_source']['net_source_J']*1e15:.3f} → {b['CODE_source']['net_source_J']*1e15:.3f} |")
    lines+=['']
    for corner,pair in data.items():
        def charge(d):return '/'.join(f"{d['CODE_source']['event_charge'][n]['absolute_C']*1e15:.3f}" for n in ['select_high','select_low'])
        lines.append(f"- {corner} CODE上升／下降事件绝对电荷：{charge(pair['base'])} → {charge(pair['x4'])} fC。含R0充放电与栅端回流，不是固定线性输入电容。")
    lines+=['','复位定义为 RC0→0、RC1→VDD、腿输出→0 均进入1%并保持到本相位末；HD相位从48.005 ns开始，LD从43.005 ns开始。延迟表相对 CODE 中点，JSON另存实际腿输入交点参考。1%是诊断阈值；只能说明该52 ns测试内的复位，不替代连续转换验证。','',
        '能量为0–52 ns本台端口积分。增加 C0 会加重经R0连接的CODE负载；CODE源、VDD源与内部传递分别记录，不用这张静态其他位／比较器复位的测试台评价整机功耗。','',
        'FF说明增加C0实现了延后开启，但HD复位、CODE源供能及过压持续时间均有代价；峰值和严格超限没有消失。SS虽从−191.747 ps改善至−35.697 ps、相反总D电流峰值10.863→1.491 µA，仍不是正裕量或纯沟道无直通的证明。FF该全窗峰值约在48.320 ns的低方向，因此HD上升延迟对它基本没有影响。' if 'sscold' in data else 'FF说明增加C0实现了延后开启，但HD复位、CODE源供能及过压持续时间均有代价；SS未回收前不推断负间隔是否消除。','',
        '结论：该对照检验真实参考接口的延迟取舍。必须同时看后级次序、参考电流、建立、复位、输入负担及过压；增加延迟或得到正半 VDD 间隔均不能独自判为修复完成。RC1与clear支路仍需按实际端压判断，不采用新基线、不追加实验。后续按用户方向推进标准单元边界，见 [替换接口](standard_cell_boundary.md)。','',
        '## 证据','',
        '回执文件大小／SHA、冻结输入、原生PASS/PSF_END、完整单调时间及无损表散列核对；两版738项模型/门限按同名逐项对应。候选新增的物理建立/复位字段与独立原生曲线测量一致。原始结果和冻结输入未改。`comparison.json`为数值，`terminal_pairs.csv`为全部逐端压，图无时间平移。','']
    for corner,pair in data.items():
        for variant,d in pair.items():lines.append(f"- `{d['run']}`：{d['native_points']}点、{d['receipt_bytes']} B；result SHA256 `{d['result_sha256']}`；告警：{', '.join(d['warnings'])}。")
    (HERE/'bbm_hdc0_findings.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze(corners):
    OUT.mkdir(exist_ok=True);waves={};data={};rows=[]
    for corner in corners:
        waves[corner]={v:load(v,corner) for v in ['base','x4']};data[corner]={}
        assert waves[corner]['base']['test_sha256']==waves[corner]['x4']['test_sha256']
        specs=[{p['instance']+':'+p['terminal']:(p['model'],p['screen_v']) for p in waves[corner][v]['cfg']['selected_mos_pair_screens']} for v in ['base','x4']];assert specs[0]==specs[1] and len(specs[0])==738
        for variant,d in waves[corner].items():s,q=summarize(d,corner,variant);data[corner][variant]=s;rows.extend(q)
        assert data[corner]['base']['native_settings']==data[corner]['x4']['native_settings']
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,one_component_only=True),indent=2)+'\n');figures(waves,data);report(data)
    print('HDC0_COMPARISON_READY',corners,'terminal rows',len(rows))
    for corner,pair in data.items():print(corner,{v:dict(high_N_gap_ps=d['control_events']['select_high']['N_signed_off_to_on_gap_s']*1e12,strict_pairs=sum(x['strict_exceed'] for x in d['groups'].values())) for v,d in pair.items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--corners',nargs='+',choices=['ffcold','sscold'],default=['ffcold']);args=parser.parse_args();analyze(args.corners)
