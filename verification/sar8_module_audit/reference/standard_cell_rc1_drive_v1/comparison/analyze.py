"""Verified D1P25 versus frozen gate-R D1: native local comparison only."""
import ast,csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
OWN=Path(__file__).resolve().parent.parent
REF=OWN.parent
sys.path.append(str(REF))
import numpy as np
import yaml
from analyze_real_bbm import digest,ROOT
OUT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_bytes())


def load(label):
    std=True;corner='ffcold';candidate=label=='D1P25'
    name='sar8audit-ref-rc1-hd-x005-d1p25-ff-v1' if candidate else 'sar8audit-ref-rc1-hd-cleargater-ff-v1'
    package=(OWN if candidate else REF/'standard_cell_rc1_v1')/'ffcold';proposal=package/'recipe_proposal.json'
    assert digest(proposal)==('5f416251a1f26ec288b2c980dbdd05c965fc56e6a6ca3659a1fdb788d29f5b3a' if candidate else '3805b0f88e1face70a166ecc407746bb6ce41d86c6359eacc5634de5dfc3f32b')
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    assert registered['recipe_hash']==('24306072b56f9a60a0d2e73fa0619d797094ce81a7829cbb6c61b3d4c0e1a81d' if candidate else 'f99c95e1c92a40c8abbe26f5456f77c03793e496538994c5ef75a17660a21e2b')
    assert receipt['total_bytes']==(27718889 if candidate else 27685183)
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    cfg=read(package/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(662 if candidate else 654)
    assert r['measurement_sha256']==digest(package/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert len(r['selected_mos_pair_extrema'])==(750 if candidate else 738)
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==(453 if candidate else 445)
    # Project only diagnostic voltages and actual output/reference/clear currents.
    wanted=set(cfg['diagnostic_voltage_columns'])|{'time','vcode:1','vvdd:1','rrefp:1','rrefn:1'}
    wanted.update(r['cell_measurements']['CODE_source_and_input_load']['incident_load_branches'])
    for q in r['cell_measurements']['internal_driver_load_work'].values():
        wanted.update(q['source_port_branches']+q['load_port_branches'])
    for side in ['n','p']:
        wanted.update('xdut.xcdac.xs'+side+'0.'+m+':1' for m in ['mn_low','mp_high'])
    for leg in ['hd','ld']:
        wanted.update('xdut.xbbm0.xd_'+leg+'.mp_clear:'+str(j) for j in [1,2,3,4])
    wanted.update(b.lower() for b,x in cfg['terminal_current_catalog'].items()
                  if x['node'].lower() in ['xdut.xbbm0.cb','xdut.xbbm0.ld'])
    for leg in ['hd','ld']:
        stem='xdut.xbbm0.xd_'+leg+'.'
        wanted.update([stem+'c1:1',stem+'r1:1',stem+'r1:2',])
    wanted.update('kcl:xdut.xbbm0.xd_'+leg+'.rc1' for leg in ['hd','ld'])
    wanted.update(b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='XDUT.XBBM0.HD')
    for leg in ['hd','ld']:
        wanted.update(b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['instance'].startswith('XDUT.XBBM0.XD_'+leg.upper()+'.X005.XLIB.'))
    wanted.add('kcl:xdut.xbbm0.hd')
    assert wanted<=set(e['columns'])
    ids=[j for j,n in enumerate(e['columns']) if n in wanted];columns=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');stride=8*len(e['columns']);h=hashlib.sha256();count=total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            b=f.read(stride*128)
            if not b:break
            assert len(b)%stride==0;h.update(b);total+=len(b)
            q=np.frombuffer(b,dtype='<f8').reshape(-1,len(e['columns']))
            assert count+len(q)<=len(w)
            w[count:count+len(q)]=q[:,ids];count+=len(q)
    assert count==(11422 if candidate else 11420) and count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def snapshot(d,time):
    w,c=d['w'],d['c'];j=int(np.argmin(abs(w[:,0]-time)));assert abs(w[j,0]-time)<1e-18
    nodes=['xdut.xbbm0.xd_hd.rc1','xdut.xbbm0.hd','xdut.xbbm0.x002.n']
    voltages={n:float(w[j,c[n]]) for n in nodes}
    source=[b.lower() for b,x in d['cfg']['terminal_current_catalog'].items()
            if x['instance'].startswith('XDUT.XBBM0.XD_HD.X005.XLIB.') and x['port']==1]
    gate=[b.lower() for b,x in d['cfg']['terminal_current_catalog'].items()
          if x['node']=='XDUT.XBBM0.HD' and x['port']==2]
    incident={b.lower() for b,x in d['cfg']['terminal_current_catalog'].items() if x['node']=='XDUT.XBBM0.HD'}
    assert set(source+gate)==incident and len(gate)==2 and len(source) in [2,4]
    return dict(time_s=time,voltages_V=voltages,Vgd_V=voltages[nodes[0]]-voltages[nodes[1]],
        X005_output_D_A=float(sum(w[j,c[b]] for b in source)),
        NAND_HD_input_G_A=float(sum(w[j,c[b]] for b in gate)),
        actual_source_ports=source,actual_downstream_gate_ports=gate)


def summarize(d,label):
    r,m=d['result'],d['result']['cell_measurements']
    specs={p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']}
    physical=[]
    for key,p in specs.items():
        x=r['selected_mos_pair_extrema'][key];positive=abs(x['max'])>=abs(x['min'])
        peak=x['max'] if positive else x['min'];time=x['max_time_s'] if positive else x['min_time_s']
        physical.append(dict(variant=label,pair=key,model=p['model'],positive_node=p['nodes'][0],negative_node=p['nodes'][1],
            screen_V=p['screen_v'],signed_peak_V=peak,abs_peak_V=abs(peak),excess_V=abs(peak)-p['screen_v'],
            peak_time_s=time,strict_fail=abs(peak)>p['screen_v'],
            above_limit_s=m['all_terminal_native_phase_time']['phases']['full']['pairs'][key]['absolute_above_limit_duration_s']))
    raw=sum(p['strict_fail'] for p in physical)
    assert raw==m['all_terminal_native_phase_time']['phases']['full']['strict_native_pair_count']
    groups=d['cfg'].get('baseline_equivalent_terminal_groups',{key:[key] for key in specs})
    assert len(groups)==738 and set(p for q in groups.values() for p in q)==set(specs)
    equivalent={}
    for key,parts in groups.items():
        values=[r['selected_mos_pair_extrema'][p] for p in parts];p=specs[parts[0]]
        assert all((x['min'],x['max'])==(values[0]['min'],values[0]['max']) for x in values)
        peak=max(abs(values[0]['min']),abs(values[0]['max']))
        equivalent[key]=dict(actual_physical_members=parts,abs_peak_V=peak,screen_V=p['screen_v'],strict_fail=peak>p['screen_v'],
            above_limit_s=m['all_terminal_native_phase_time']['phases']['full']['pairs'][parts[0]]['absolute_above_limit_duration_s'])
    strict=sum(q['strict_fail'] for q in equivalent.values())
    if label=='D1P25':
        assert m['baseline_equivalent_terminal_counts']['full']['strict_equivalent_group_count']==strict
    nkeys=[key for key,p in specs.items() if p['instance'].startswith('XDUT.XBBM0.XD_HD.X005.XLIB.') and p['model']=='nch_mac' and p['terminal']=='gd']
    key=sorted(nkeys)[0];x=r['selected_mos_pair_extrema'][key];ns='xdut.xbbm0.xd_hd.rc1'
    clear='XDUT.XBBM0.XD_HD.MP_CLEAR:ds';clearx=r['selected_mos_pair_extrema'][clear]
    reset={}
    for leg,z in m['delay_leg_reset_diagnostics'].items():
        values=[p['delay_from_CODE_midpoint_s'] for p in z['nodes'].values()]
        reset[leg]=None if any(p is None for p in values) else max(values)
    gate=[b.lower() for b,z in d['cfg']['terminal_current_catalog'].items() if z['node']=='XDUT.XBBM0.HD' and z['port']==2]
    w,c=d['w'],d['c'];ids=np.flatnonzero((w[:,0]>=47.995e-9)&(w[:,0]<=52e-9))
    current=sum(w[ids,c[b]] for b in gate);j=int(np.argmin(current))
    return dict(run=d['run'],result_sha256=d['result_sha256'],managed_recipe_sha256=d['managed_recipe_sha256'],
        native_points=d['native_points'],receipt_bytes=d['receipt_bytes'],physical_pair_count=len(specs),
        strict_physical_pairs=raw,over1mV_physical_pairs=sum(p['excess_V']>.001 for p in physical),
        equivalent_group_count=738,strict_equivalent_groups=strict,
        over1mV_equivalent_groups=sum(q['abs_peak_V']-q['screen_V']>.001 for q in equivalent.values()),
        equivalent_groups=equivalent,
        RC1_extrema=r['voltage_and_current_extrema'][ns],HD_extrema=r['voltage_and_current_extrema']['xdut.xbbm0.hd'],
        receiver_actual_pair=key,receiver_positive_peak_V=x['max'],receiver_negative_peak_V=x['min'],
        positive=snapshot(d,x['max_time_s']),negative=snapshot(d,x['min_time_s']),
        receiver_above_limit_s=m['all_terminal_native_phase_time']['phases']['full']['pairs'][key]['absolute_above_limit_duration_s'],
        clear_abs_Vds_peak_V=max(abs(clearx['min']),abs(clearx['max'])),
        clear_above_limit_s=m['all_terminal_native_phase_time']['phases']['full']['pairs'][clear]['absolute_above_limit_duration_s'],
        reset_delay_s=reset,reference_settling=m['physical_command_phase_reference_settling'],
        actual_gate_events=m['actual_control_events'],RC1_events=m['RC1_actual_native_event_charge'],
        NAND_G_CODE_fall=dict(min_current_A=float(current[j]),time_s=float(w[ids[j],0]),
            signed_charge_C=float(np.trapezoid(current,w[ids,0])),native_interval_s=[float(w[ids[0],0]),float(w[ids[-1],0])]),
        warnings=r['native_warning_codes'],settings=r['native_effective_settings'],acceptance_pass=None),physical


def figures(waves,data):
    os.environ.setdefault('MPLCONFIGDIR',str(OUT/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    styles={'D1':'--','D1P25':'-'};colors=['#176fa6','#c65c2e']
    fig,axes=plt.subplots(3,2,figsize=(12.5,8),layout='constrained')
    for j,(a,b,pos) in enumerate([(42.99,43.15,True),(47.995,48.012,False)]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=a)&(t<=b)
            for z,n in enumerate(['xdut.xbbm0.xd_hd.rc1','xdut.xbbm0.hd']):
                axes[0,j].plot(t[q],w[q,c[n]],styles[label],color=colors[z],lw=1.25,label=['RC1','HD output'][z] if label=='D1P25' else None)
            axes[1,j].plot(t[q],abs(w[q,c['xdut.xbbm0.xd_hd.rc1']]-w[q,c['xdut.xbbm0.hd']]),styles[label],
                color='#777' if label=='D1' else colors[0],lw=1.25,label=label+' |Vgd|')
            gate=[b.lower() for b,x in d['cfg']['terminal_current_catalog'].items() if x['node']=='XDUT.XBBM0.HD' and x['port']==2]
            axes[2,j].plot(t[q],sum(w[q,c[b]] for b in gate)*1e6,styles[label],
                color='#777' if label=='D1' else colors[0],lw=1.25,label=label+' NAND input G')
        axes[1,j].axhline(.99,color='#b75336',ls=':',lw=.8)
        axes[0,j].set_title('Positive release' if pos else 'Negative reset / worst Vgd')
        for i,y in enumerate(['Concurrent G / D (V)','Actual |Vgd| (V)','Into NAND input (uA)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right');ax.ticklabel_format(useOffset=False,axis='x')
        axes[-1,j].set_xlabel('Native time (ns)')
    at=data['D1P25']['negative']['time_s']*1e9;y=abs(data['D1P25']['negative']['Vgd_V'])
    for i in range(3):axes[i,1].axvline(at,color='#999',ls=':',lw=.7)
    axes[1,1].scatter([at],[y],s=16,color=colors[0])
    axes[1,1].annotate(f'{y:.6f} V',xy=(at,y),xytext=(48.007,.9),fontsize=8,
        arrowprops=dict(arrowstyle='->',color='#666',lw=.7))
    fig.suptitle('Verified next native drive D1P25: lower peak, persistent timing overlap',fontsize=13)
    footer='FF0.99V/-40C. Dashed: D1 gate-R baseline; solid: D1P25 master only. Same clear R / LD / RC / real load, ideal CODE/rails/clock, comparator reset; no noise/mismatch/PEX. Native time, no shifts; red dotted0.99V screen.'
    fig.supxlabel(textwrap.fill(footer,155),fontsize=8)
    fig.savefig(OUT/'D1_D1P25_phase_comparison.png',dpi=165);plt.close(fig)


def f(x,scale=1,digits=3):return '未观测' if x is None else format(x*scale,'.'+str(digits)+'f')


def report(data,delta):
    a,b=data['D1'],data['D1P25']
    lines=['# HD X005：D1与D1P25配对','',
        '**更强原生档位降低峰值，但没有解除端压超限。** 最坏绝对Vgd从1.035538降至1.027665V；RC1正峰1.026241→1.025818V、负峰−16.508→−16.237mV。超限持续时间未改善，复位略慢，因此该版本不判通过。','',
        '仅HD.X005原生master改为已核验的INVD1P25；HD clear串阻、LD、其他193条叶记录和外部源/时序/采样窗口/关闭沿/负载不变。FF0.99V/−40°C，CODE/电源/时钟理想、比较器复位、其他位静态；无噪声、失配、PEX。','',
        '| 指标 | D1 | D1P25 |','| --- | --- | --- |']
    metrics=[('RC1正峰 V','RC1_extrema','max',1),('RC1负峰 mV','RC1_extrema','min',1e3),('HD输出正峰 V','HD_extrema','max',1)]
    for name,k,j,scale in metrics:lines.append('| '+name+' | '+f(a[k][j],scale,6 if scale==1 else 3)+' | '+f(b[k][j],scale,6 if scale==1 else 3)+' |')
    for name,key,scale in [('X005正向Vgd V','receiver_positive_peak_V',1),('X005负向Vgd V','receiver_negative_peak_V',1),
        ('X005绝对Vgd超0.99V累计 ps','receiver_above_limit_s',1e12),
        ('clear最大绝对Vds V','clear_abs_Vds_peak_V',1),('clear绝对Vds超0.99V累计 ps','clear_above_limit_s',1e12)]:
        lines.append('| '+name+' | '+f(a[key],scale,6 if scale==1 else 3)+' | '+f(b[key],scale,6 if scale==1 else 3)+' |')
    lines+=['','![两相位原生时间对照](D1_D1P25_phase_comparison.png)','',
        '## 最坏时刻仍是负RC1与正HD重合','']
    for label,d in data.items():
        q=d['negative'];v=q['voltages_V']
        lines.append(f"- {label}：{q['time_s']*1e9:.6f}ns，RC1={v['xdut.xbbm0.xd_hd.rc1']:.6f}V、HD={v['xdut.xbbm0.hd']:.6f}V，Vgd={q['Vgd_V']:.6f}V；NAND输入G总电流={q['NAND_HD_input_G_A']*1e6:.3f}µA，X005输出D总电流={q['X005_output_D_A']*1e6:.3f}µA。")
    lines+=['','电流正方向为流入器件。负NAND门端电流仍在向HD回送电荷，较强反相器吸收回流，使HD正峰下降；但RC1负窗和HD反冲依然重合，不能把更小的单节点峰值理解为安全端压。这里只比较实际总端口流向，不分解成纯沟道或本征Cgd电流。','',
        '## 实际器件数与公平计数','',
        '| 检查口径 | D1 | D1P25 |','| --- | --- | --- |',
        f"| 实际端对／严格超限 | {a['physical_pair_count']} / {a['strict_physical_pairs']} | {b['physical_pair_count']} / {b['strict_physical_pairs']} |",
        f"| 738等价组／严格超限 | 738 / {a['strict_equivalent_groups']} | 738 / {b['strict_equivalent_groups']} |",
        f"| 实际端对超门限1mV项数 | {a['over1mV_physical_pairs']} | {b['over1mV_physical_pairs']} |",
        f"| 等价组超门限1mV项数 | {a['over1mV_equivalent_groups']} | {b['over1mV_equivalent_groups']} |",'',
        'D1P25实际使用两N两P共四只MOS；并联成员共享经过核验的D/G/S/B节点、模型和门限，所以新增的并联筛查不是新增独立电压故障。750项物理端压/持续时间全部保留，738组只用于与基线对应比较。核心0.99V、IO1.98V门限未改。','']
    lines.append(f"等价组严格状态变化：新增{sum(q['status']=='added' for q in delta)}项、消失{sum(q['status']=='resolved' for q in delta)}项；详见status_changes.json。")
    lines+=['','## 时序、建立及方向判断','',
        '| 指标 | D1 | D1P25 |','| --- | --- | --- |']
    for leg in ['HD','LD']:lines.append('| '+leg+'整腿1%复位 ps | '+f(a['reset_delay_s'][leg],1e12)+' | '+f(b['reset_delay_s'][leg],1e12)+' |')
    for phase in ['select_high','select_low']:
        for side in ['N','P']:
            key=side+'_signed_off_to_on_gap_s'
            lines.append('| '+phase+' '+side+'实际栅间隔 ps | '+f(a['actual_gate_events'][phase][key],1e12)+' | '+f(b['actual_gate_events'][phase][key],1e12)+' |')
    for phase in ['select_high','select_low']:
        get=lambda d:' / '.join(f(x['remained_inside_from_native_s'],1e9,6) for x in d['reference_settling'][phase]['nodes'].values())
        lines.append('| '+phase+' BN0/BP0进入1mV ns | '+get(a)+' | '+get(b)+' |')
    lines+=['','两腿复位和四个物理参考建立窗口均完成；半VDD间隔只是控制顺序诊断。完成建立不代表切换期间无过压。原生CMI及其他RC/clear/逻辑残余保留，不推断SS/整机合格。','',
        '**方向判断：不继续把“提高驱动档位”当作完整修复主线。** 1.25倍档已显示HD峰值略降，但RC1输入负窗与回流仍重合，输入负担和复位代价也增加。下一方向应回到RC1复位路径与下游回流的接口边界，寻找能同时处理正向注入、负向恢复和输出端轨外电压的结构；先做边界分析再选一个变量，不继续自动扫驱动强度。本轮不新增候选或远端任务。','',
        '## 证据','']
    for label,d in data.items():lines.append(f"- {d['run']}：{d['native_points']}点、{d['receipt_bytes']}B；result SHA256 {d['result_sha256']}；managed {d['managed_recipe_sha256']}。")
    lines+=['','逐文件/输入/native流大小与SHA、PASS/END、654/662路电流初始化、全窗单调原生时间验证；solver和非save测试台一致。physical_terminal_pairs.csv保留1488条实际检查，comparison.json保留全部738组对应、四事件电荷/复位和同刻流向；状态变化不以缺失字段计零。输入和analyzer未修改。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze():
    waves={v:load(v) for v in ['D1','D1P25']}
    assert waves['D1']['external_body']==waves['D1P25']['external_body']
    assert waves['D1']['result']['native_effective_settings']==waves['D1P25']['result']['native_effective_settings']
    data={};rows=[]
    for label,d in waves.items():data[label],q=summarize(d,label);rows.extend(q)
    assert len(rows)==1488
    delta=[]
    for key,x in data['D1']['equivalent_groups'].items():
        y=data['D1P25']['equivalent_groups'][key]
        if x['strict_fail']!=y['strict_fail']:delta.append(dict(group=key,status='added' if y['strict_fail'] else 'resolved',D1=x,D1P25=y))
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None),indent=2)+'\n',encoding='utf-8')
    (OUT/'status_changes.json').write_text(json.dumps(dict(equivalent_changes=delta),indent=2)+'\n',encoding='utf-8')
    with (OUT/'physical_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves,data);report(data,delta)
    print('VERIFIED_DRIVE_COMPARISON_READY',len(rows),{k:(x['strict_physical_pairs'],x['strict_equivalent_groups']) for k,x in data.items()},'equivalent status changes',len(delta))


if __name__=='__main__':analyze()


