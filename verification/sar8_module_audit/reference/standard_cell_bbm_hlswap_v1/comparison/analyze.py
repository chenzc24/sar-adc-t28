"""Collected H-only swap from L paired comparison; no remote or frozen edits."""
import csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
PACKAGE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PACKAGE));sys.path.append(str(PACKAGE.parent))
import numpy as np
import yaml
from analyze_real_bbm import digest,HERE,ROOT
import analyze_standard_cell_bbm_lswap as previous
import analyze_standard_cell_bbm as prior
from standard_cell_bbm_hlswap_analyze import above_duration
OUT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_bytes())


def load_hl():
    std=True;corner='ffcold';swapped=True
    name='sar8audit-ref-bbm-stdcell-hlswap-ff-v1'
    package=PACKAGE/'ffcold';proposal=package/'recipe_proposal.json'
    assert digest(proposal)=='739a937ac526501d15922f09de3babc87a4dc9270e9845a5731bfe50d26874e4'
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    assert registered['recipe_hash']=='d0020c7f2887144d28c373ad052a6f24e81d0d4af120993e2c1066b7c8f186f7'
    assert receipt['total_bytes']==26389195
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    cfg=read(package/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(652 if std else 656)
    assert r['measurement_sha256']==digest(package/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert len(r['selected_mos_pair_extrema'])==738
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==441
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
    assert count==11298 and count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def pair_duration(d,spec,a=0.,b=52e-9):
    ns=[n.lower() for n in spec['nodes']];c=d['c'];w=d['w']
    if any(n!='0' and n not in c for n in ns):return None
    y=(0. if ns[0]=='0' else w[:,c[ns[0]]])-(0. if ns[1]=='0' else w[:,c[ns[1]]])
    if np.isscalar(y):return (b-a) if abs(y)>spec['screen_v'] else 0.
    return sum(above_duration(t0,y0,t1,y1,spec['screen_v'],a,b)
        for t0,y0,t1,y1 in zip(w[:-1,0],y[:-1],w[1:,0],y[1:]))


def status_delta(waves):
    specs={v:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for v,d in waves.items()}
    assert specs['L'].keys()==specs['HL'].keys()
    changes=[];allpairs=[]
    for key in specs['L']:
        records=[]
        for label,d in waves.items():
            p=specs[label][key];x=d['result']['selected_mos_pair_extrema'][key];positive=abs(x['max'])>=abs(x['min'])
            peak=x['max'] if positive else x['min'];t=x['max_time_s'] if positive else x['min_time_s']
            records.append(dict(signed_peak_V=peak,abs_peak_V=abs(peak),time_s=t,
                phase=prior.phase(t),screen_V=p['screen_v'],strict_fail=abs(peak)>p['screen_v'],
                positive_node=p['nodes'][0],negative_node=p['nodes'][1]))
        a,b=records
        kind='added' if not a['strict_fail'] and b['strict_fail'] else 'resolved' if a['strict_fail'] and not b['strict_fail'] else 'still_fail' if b['strict_fail'] else 'still_clear'
        record=dict(pair=key,status=kind,L=a,HL=b)
        if kind in ['added','resolved']:
            record['L']['above_limit_s']=pair_duration(waves['L'],specs['L'][key])
            record['HL']['above_limit_s']=waves['HL']['result']['cell_measurements']['all_terminal_native_phase_time']['phases']['full']['pairs'][key]['absolute_above_limit_duration_s']
            changes.append(record)
        allpairs.append(record)
    assert len(allpairs)==738
    return changes,allpairs


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    styles={'L':'--','HL':'-'};colors=['#176fa6','#c65c2e']
    footer='FF / 0.99 V / -40 C. Dashed: frozen L-only swap; solid: H+L swap. Same52ns testbench, real CDAC/Bootstrap/IO/Rgate, ideal CODE/rails/clock, comparator reset; other bits static; no noise/mismatch/PEX. Native time, no shifts.'
    fig,axes=plt.subplots(4,2,figsize=(13,9),layout='constrained')
    for j,(a,b,phase) in enumerate([(42.99,43.3,'43 ns: H turn-on residual'),(47.99,48.3,'48 ns: H negative hold removed')]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=a)&(t<=b)
            for row,nodes,tags in [(0,['code','xdut.xbbm0.hd'],['CODE','HD']),
                (1,['xdut.xbbm0.x002.n','xdut.xbbm0.x002.x000.xlib.net10'],['H output','H stack'])]:
                for z,n in enumerate(nodes):axes[row,j].plot(t[q],w[q,c[n]],styles[label],color=colors[z],lw=1.25,label=tags[z] if label=='HL' else None)
            out=w[:,c['xdut.xbbm0.x002.n']];stack=w[:,c['xdut.xbbm0.x002.x000.xlib.net10']]
            axes[2,j].plot(t[q],out[q]-stack[q],styles[label],color='#777' if label=='L' else colors[0],lw=1.25,label=label)
            inst='XDUT.XBBM0.X002.X000.XLIB.MM4';g=d['cfg']['terminal_current_catalog'][inst+':2']['node'].lower()
            vg=w[:,c[g]]
            for z,(y,tag) in enumerate([(vg,'MM4 Vgb'),(vg-stack,'MM4 Vgs')]):
                axes[3,j].plot(t[q],y[q],styles[label],color=colors[z],lw=1.25,label=tag if label=='HL' else None)
        axes[0,j].set_title(phase)
        for i,y in enumerate(['CODE / HD (V)','H NAND D/S (V)','H MM4 Vds (V)','Actual H MM4 gate stress (V)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right')
            if i in [2,3]:
                ax.axhline(.99,color='#b75336',ls=':',lw=.8);ax.text(.01,.995,'0.99 V screen',transform=ax.get_yaxis_transform(),fontsize=7,color='#b75336')
        axes[-1,j].set_xlabel('Native time (ns)')
    zoom=axes[2,0].inset_axes([.56,.25,.41,.37])
    for label,d in waves.items():
        w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=43.085)&(t<=43.14)
        y=w[q,c['xdut.xbbm0.x002.n']]-w[q,c['xdut.xbbm0.x002.x000.xlib.net10']]
        zoom.plot(t[q],y,styles[label],color='#777' if label=='L' else colors[0],lw=1)
    zoom.axhline(.99,color='#b75336',ls=':',lw=.7);zoom.set(xlim=(43.085,43.14),ylim=(.987,.996),xticks=[43.09,43.13],yticks=[.99,.995])
    zoom.tick_params(labelsize=7);zoom.set_title('+2.332 mV at 43.114 ns',fontsize=7)
    fig.suptitle('H-only additional swap: phase-specific terminal evidence',fontsize=13)
    fig.supxlabel(textwrap.fill(footer,160),fontsize=8);fig.savefig(OUT/'H_phase_terminal_witness.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(5,2,figsize=(13,11),layout='constrained')
    for j,(a,b,high) in enumerate([(42.98,44.2,True),(47.98,49.2,False)]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=a)&(t<=b)
            for i,nodes in [(0,['xdut.h0','xdut.l0']),(1,['xdut.gnn0','xdut.gnp0']),(2,['xdut.gpp0','xdut.gpn0'])]:
                for z,n in enumerate(nodes):axes[i,j].plot(t[q],w[q,c[n]],styles[label],color=colors[z],lw=1.25,label=n.rsplit('.',1)[-1].upper() if label=='HL' else None)
            for z,m in enumerate(['mn_low','mp_high']):
                n='xdut.xcdac.xsn0.'+m+':1';axes[3,j].plot(t[q],w[q,c[n]]*1e6,styles[label],color=colors[z],lw=1.25,label=m+' D' if label=='HL' else None)
            for z,(n,r) in enumerate([('bn0','vrefp' if high else 'vrefn'),('bp0','vrefn' if high else 'vrefp')]):
                axes[4,j].plot(t[q],(w[q,c['xdut.xcdac.'+n]]-w[q,c[r]])*1e3,styles[label],color=colors[z],lw=1.25,label=n.upper()+' error' if label=='HL' else None)
        for i,y in enumerate(['H/L (V)','N-side gates (V)','P-side gates (V)','N-side total D (uA)','Reference error (mV)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right')
        for i in [1,2]:axes[i,j].axhline(.495,color='#999',ls=':',lw=.8)
        axes[4,j].set_yscale('symlog',linthresh=1);axes[4,j].axhspan(-1,1,color='#258578',alpha=.1)
        axes[0,j].set_title('High selection' if high else 'Low selection');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('Actual loaded gates, total reference currents and phase settling',fontsize=13)
    fig.supxlabel(textwrap.fill(footer,160),fontsize=8);fig.savefig(OUT/'reference_interface.png',dpi=165);plt.close(fig)


def f(x,scale=1,digits=3):return '未观测' if x is None else format(x*scale,'.'+str(digits)+'f')


def report(data,changes):
    a,b=data['L'],data['HL'];n=lambda d:d['phase_specific_NAND']['H']['phases']
    lines=['# H追加换序：与冻结L-swap配对','',
        '**48 ns的H内部负向浮置明显改善，但整台仍未通过端压检查。** H MM4在48 ns相位的最大Vds从1.105306降至0.684431 V；43 ns仍有0.992332 V，L侧仍有0.992307 V。严格超限由213变214，是新增6项、消失5项的净变化。','',
        '仅H NAND A1/A2由CODE/HD换为HD/CODE；L换序、其他190条叶记录、RC/clear、负载和52ns激励保持。FF0.99V/−40°C，CODE/电源/时钟理想，比较器复位、其他位静态；未含噪声、失配、PEX。','',
        '| H相位 | 内部栈节点最小/最大 V：L→HL | MM4最大Vds V：L→HL | 超0.99V累计ps：L→HL |',
        '| --- | --- | --- | --- |']
    for phase in ['CODE_rise','CODE_fall']:
        x,y=n(a)[phase],n(b)[phase]
        node=lambda z:f"{z['stack']['min_V']:.6f}/{z['stack']['max_V']:.6f}"
        lines.append(f"| {phase} | {node(x)} → {node(y)} | {x['MM4_Vds']['max_V']:.6f} → {y['MM4_Vds']['max_V']:.6f} | {x['MM4_Vds']['abs_above0p99_duration_s']*1e12:.3f} → {y['MM4_Vds']['abs_above0p99_duration_s']*1e12:.3f} |")
    lines+=['','两相位为[42.995,47.995)与[47.995,52]ns。表中旧版时长使用其完整原生诊断窗口，边界外未推断；新版全738项另有精确裁边的原生线性插值持续时间。时长仅用于比较，不作寿命签核。','',
        '![H同刻端压](H_phase_terminal_witness.png)','',
        '## 同刻证据与原因','']
    for phase in ['CODE_rise','CODE_fall']:
        w=n(b)[phase]['MM4_Vds']['coincident_DGSB']['maximum']
        lines.append(f"- {phase}：{w['time_s']*1e9:.6f}ns，D={w['D_V']:.6f}V、S={w['S_V']:.6f}V、G={w['G_V']:.6f}V、B=0，Vds={w['Vds_V']:.6f}V。")
    lines+=['','48ns双下降时，CODE控制靠地管先关、HD控制靠输出管后关，内部节点在短暂通路中先从输出充电，避免原长期负向浮置。43ns双上升时，内部节点先由靠地管放到地，输出仍接近VDD，后续开通扰动留下约2.332mV的Vds超限；这是另一阶段的残余。不能把输出/源节点在不同时刻的极值相减，也不能用大下冲的消失抵消小幅超限。','',
        'HD本身仍有RC/clear接口造成的过轨。换序把HD从原来的下管/另一PMOS输入接到上管MM4及MM1，端对的应力随真实端点重分配。新增6项中，MM1的gs/gb因源体同接VDD重复反映一个电压差；MM1/MM4的gd也共用门/输出节点。它们是6项实际筛查记录，不是6个独立故障。','',
        '## 新增与消失的严格超限','',
        '| 状态 | H NAND端对 | 峰值 V：L→HL | 峰值时间ns：L→HL | 峰值阶段：L→HL | 超0.99V累计ps：L→HL |',
        '| --- | --- | --- | --- | --- | --- |']
    for q in changes:
        x,y=q['L'],q['HL']
        lines.append(f"| {'新增' if q['status']=='added' else '消失'} | {q['pair'].split('.XLIB.')[1]} | {x['signed_peak_V']:.6f} → {y['signed_peak_V']:.6f} | {x['time_s']*1e9:.6f} → {y['time_s']*1e9:.6f} | {x['phase']} → {y['phase']} | {f(x['above_limit_s'],1e12)} → {f(y['above_limit_s'],1e12)} |")
    lines+=['','0.99V严格门限未放宽；全738项按各自冻结模型门限核对（IO1.98V）。持续时间来自原生点间线性插值。CSV同时保留换序前后真实正负端点。表中“消失”仅指该实际MOS端对不再严格超限，并非对应波形或耦合不存在。MM4:ds也没有被计作新增：旧版48ns全窗已超限，换序后43ns仍有小超限，所以其状态仍是fail。','',
        '超过门限1mV的项数保持197，并不与严格净增1项矛盾：MM9:gd由1.028991 V降至0.990001954 V，仍严格超约1.954 µV，却退出“超1mV”集合。因此严格集合新增6/消失5，超1mV集合新增6/消失6。微伏级边界保留记录，不据此作可靠性或数值稳健性通过判断。','',
        '## 参考接口和残余','',
        '| 方向 | BBM间隔ps：L→HL | N实际栅间隔ps：L→HL | P实际栅间隔ps：L→HL |',
        '| --- | --- | --- | --- |']
    for phase in ['select_high','select_low']:
        vals=[f(a['control_events'][phase][k],1e12)+' → '+f(b['control_events'][phase][k],1e12) for k in ['BBM_signed_off_to_on_gap_s','N_signed_off_to_on_gap_s','P_signed_off_to_on_gap_s']]
        lines.append('| '+phase+' | '+' | '.join(vals)+' |')
    lines+=['','![真实参考接口](reference_interface.png)','',
        '| 方向 | L版BN0/BP0进入1mV ns | HL版BN0/BP0 ns |',
        '| --- | --- | --- |']
    for phase in ['high','low']:
        vals=[' / '.join(f(x['remained_inside_from_native_s'],1e9,6) for x in d['physical_phase_settling'][phase].values()) for d in [a,b]]
        lines.append('| '+phase+' | '+' | '.join(vals)+' |')
    lines+=['','两方向参考均在各自相位内建立；两腿复位仍完成。半VDD交点仅是顺序诊断，参考总D电流含位移电流，不能称为纯沟道直通。','',
        '| 残余项 | L版 | HL版 |',
        '| --- | --- | --- |']
    for leg in ['HD','LD']:
        for key,desc in [('X005_gd_peak_V','X005最大绝对Vgd V'),('MP_CLEAR_ds_peak_V','MP_CLEAR最大绝对Vds V')]:
            lines.append('| '+leg+' '+desc+' | '+f(a['RC1_and_clear_stress'][leg][key],digits=6)+' | '+f(b['RC1_and_clear_stress'][leg][key],digits=6)+' |')
        rc=lambda d:'/'.join(f(d['RC1_and_clear_stress'][leg]['RC1_extrema'][k],digits=6) for k in ['min','max'])
        lines.append('| '+leg+' RC1 min/max V | '+rc(a)+' | '+rc(b)+' |')
    for leg in ['L','H']:
        get=lambda d:d['NAND_internal_diagnostics'][leg]['output_adjacent_absVds_peak_native_witness']['Vds_V']
        lines.append('| '+leg+' MM4全窗最大Vds V | '+f(get(a),digits=6)+' | '+f(get(b),digits=6)+' |')
    lines+=['','原生CMI告警仍在；严格端对213→214，超过模型门限1mV的项数'+str(a['over1mV'])+'→'+str(b['over1mV'])+'。RC/clear端压和L侧约2.307mV残余均未修复。','',
        '结论：两侧换序验证了内部浮置的连接机制，并未解决RC节点及其驱动信号的过轨和满供电端压余量。下一轮由主任务结合存储/驱动证据决定RC接口方案，本轮不追加候选或仿真。','',
        '## 证据','']
    for label,d in data.items():lines.append(f"- {d['run']}：{d['native_points']}点、{d['receipt_bytes']}B；result SHA256 {d['result_sha256']}；managed {d['managed_recipe_sha256']}。")
    lines+=['','两个回执无跳过，逐文件SHA/大小、冻结输入、PASS/END、652路电流初始化及完整单调原生时间校验通过；求解设置相同。HL派生流441列、L372列，仅测量投影不同，仿真保存项和test.scs相同。terminal_pairs.csv为1476条全端压记录；status_changes.json列出6新增/5消失，comparison.json保存数值和原生phase-time证据。无时间平移，无电路采用或整机合格结论。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze():
    waves={'L':previous.load_pair('swap'),'HL':load_hl()};mapping=prior.device_mapping();data={};rows=[]
    assert waves['L']['external_body']==waves['HL']['external_body']
    assert waves['L']['result']['native_effective_settings']==waves['HL']['result']['native_effective_settings']
    for label,d in waves.items():
        data[label],q=previous.summarize(d,label,mapping);rows.extend(q)
    native=waves['HL']['result']['cell_measurements']['all_terminal_native_phase_time']
    assert native['phases']['full']['strict_native_pair_count']==data['HL']['strict_exceed']==214
    assert all(len(q['pairs'])==738 for q in native['phases'].values())
    for key,q in native['phases']['full']['pairs'].items():
        r=waves['HL']['result']['selected_mos_pair_extrema'][key]
        assert q['min_V']==r['min'] and q['max_V']==r['max']
    changes,allpairs=status_delta(waves)
    assert sum(q['status']=='added' for q in changes)==6 and sum(q['status']=='resolved' for q in changes)==5
    assert len(rows)==1476
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,HL_all_terminal_phase_time=native,
        acceptance_pass=None,scope='FF H-only addition from frozen L; diagnostic only'),indent=2)+'\n',encoding='utf-8')
    (OUT/'status_changes.json').write_text(json.dumps(dict(changes=changes,all738_status=allpairs),indent=2)+'\n',encoding='utf-8')
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves);report(data,changes)
    print('HL_COMPARISON_READY',len(rows),'added6 resolved5', {k:q['strict_exceed'] for k,q in data.items()})


if __name__=='__main__':analyze()


