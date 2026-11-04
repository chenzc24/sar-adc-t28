"""Collected single L NAND pin-swap comparison. Local bounded streams only."""
import csv,gzip,hashlib,json,os,textwrap
import numpy as np
import yaml
from analyze_real_bbm import digest,HERE,ROOT
import analyze_standard_cell_bbm as prior
from analyze_bbm_hdc0 import duration
PACKAGE=HERE/'standard_cell_bbm_lswap_v1'
OUT=PACKAGE/'comparison'


def read(path):return json.loads(path.read_bytes())


def load_pair(label):
    std=True;corner='ffcold';swapped=label=='swap'
    name='sar8audit-ref-bbm-stdcell-lswap-ff-v1' if swapped else 'sar8audit-ref-bbm-stdcell-ffcold-v1'
    package=(PACKAGE if swapped else HERE/'standard_cell_bbm_v1')/'ffcold';proposal=package/'recipe_proposal.json'
    assert digest(proposal)==('6ea8073bf06e3ffea5863a8bf4b33c7c342d255a6d927b98affff40d4528ae02' if swapped else 'f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c')
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    assert registered['recipe_hash']==('2b62fa1e5f736c747ecc25f8573280df23276f5d6e69705b873865874b7bf99b' if swapped else 'a7b09f5868cf81605a7ad3ff8b2fb7696b36dca88b19ec7cd20f13a61e3e1e8b')
    assert receipt['total_bytes']==(21911695 if swapped else 21843637)
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
    assert len(e['columns'])==(372 if std else 376)
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
    assert count==(11278 if swapped else 11316) and count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def event_list(d,node):
    return [x for x in d['result']['half_vdd_events'].get(node,[]) if x['estimated_time_s']>=42.98e-9]


def local_stats(d,y,a,b,closed=False):
    t=d['w'][:,0];q=np.flatnonzero((t>=a)&((t<=b) if closed else (t<b)))
    assert len(q)>1
    lo=int(q[np.argmin(y[q])]);hi=int(q[np.argmax(y[q])])
    return dict(requested_s=[a,b],native_s=[float(t[q[0]]),float(t[q[-1]])],
        min_V=float(y[lo]),min_time_s=float(t[lo]),max_V=float(y[hi]),max_time_s=float(t[hi]),
        abs_above0p99_duration_s=duration(t[q],y[q],.99),indices=(lo,hi))


def details(d):
    answer={}
    w,c=d['w'],d['c']
    for leg,cell in [('L','x004'),('H','x002')]:
        stem='xdut.xbbm0.'+cell+'.x000.xlib.'
        output='xdut.xbbm0.'+cell+'.n';stack=stem+'net10'
        inst='XDUT.XBBM0.'+cell.upper()+'.X000.XLIB.MM4'
        gate=d['cfg']['terminal_current_catalog'][inst+':2']['node'].lower()
        groups={}
        for label,a,b,closed in [('CODE_rise',42.995e-9,47.995e-9,False),
                                   ('CODE_fall',47.995e-9,52e-9,True)]:
            groups[label]={}
            for name,y in [('output',w[:,c[output]]),('stack',w[:,c[stack]]),
                           ('MM4_Vds',w[:,c[output]]-w[:,c[stack]])]:
                q=local_stats(d,y,a,b,closed)
                witnesses={}
                for which,j in zip(['minimum','maximum'],q.pop('indices')):
                    witnesses[which]=dict(time_s=float(w[j,0]),D_V=float(w[j,c[output]]),
                        S_V=float(w[j,c[stack]]),G_V=float(w[j,c[gate]]),B_V=0.,
                        Vds_V=float(w[j,c[output]]-w[j,c[stack]]))
                q['coincident_DGSB']=witnesses;groups[label][name]=q
        answer[leg]=dict(actual_A1_node=gate,
            actual_A2_node=d['cfg']['terminal_current_catalog'][inst.removesuffix('MM4')+'MM9:2']['node'].lower(),
            A1_edges=event_list(d,gate),
            A2_edges=event_list(d,d['cfg']['terminal_current_catalog'][inst.removesuffix('MM4')+'MM9:2']['node'].lower()),
            phases=groups)
    answer['control_phase_reference_ports']={}
    for label,a,b in [('CODE_rise',42.98e-9,47.98e-9),('CODE_fall',47.98e-9,52e-9)]:
        ids=np.flatnonzero((w[:,0]>=a)&(w[:,0]<=b));t=w[ids,0];curr={}
        for side in ['n','p']:
            lo=w[ids,c['xdut.xcdac.xs'+side+'0.mn_low:1']]
            hi=w[ids,c['xdut.xcdac.xs'+side+'0.mp_high:1']]
            opposed=np.where(lo*hi<0,np.minimum(abs(lo),abs(hi)),0.)
            j=int(np.argmax(opposed))
            curr[side]=dict(opposed_total_D_min_peak_A=float(opposed[j]),peak_s=float(t[j]),
                opposed_total_D_min_abs_charge_C=float(np.trapezoid(opposed,t)),
                low_D_peak_abs_A=float(max(abs(lo))),high_D_peak_abs_A=float(max(abs(hi))))
        answer['control_phase_reference_ports'][label]=curr
    answer['CB_LD_actual_load_charge']={}
    for node,source_stem in [('xdut.xbbm0.cb','xdut.xbbm0.x000.xlib'),
                             ('xdut.xbbm0.ld','xdut.xbbm0.xd_ld.x005.xlib')]:
        source=[source_stem+'.mm1:1',source_stem+'.mm0:1']
        branches=[b.lower() for b,x in d['cfg']['terminal_current_catalog'].items()
                  if x['node'].lower()==node and b.lower() not in source]
        load=sum(w[:,c[b]] for b in branches)
        driver=sum(w[:,c[b]] for b in source)
        phases={}
        for label,a,b in [('CODE_rise',42.98e-9,47.98e-9),('CODE_fall',47.98e-9,52e-9)]:
            q=np.flatnonzero((w[:,0]>=a)&(w[:,0]<=b));t=w[q,0]
            phases[label]=dict(native_interval_s=[float(t[0]),float(t[-1])],
                signed_load_C=float(np.trapezoid(load[q],t)),
                absolute_net_load_C=float(np.trapezoid(abs(load[q]),t)),
                load_min_A=float(load[q].min()),load_max_A=float(load[q].max()))
        answer['CB_LD_actual_load_charge'][node]=dict(source_branches=source,
            load_branches=branches,max_KCL_A=float(max(abs(load+driver))),phases=phases,
            interpretation='Actual incident total-port load after excluding inverter output drains; not a fixed capacitor or intrinsic charge decomposition.')
    return answer


def summarize(d,label,mapping):
    s,rows=prior.summarize(d,'ffcold','std',mapping)
    for q in rows:q['variant']=label
    s['paired_label']=label;s['phase_specific_NAND']=details(d)
    # The reused standard comparison assumes original pin assignment in this
    # diagnostic. Correct the swapped G witness to actual native catalog.
    for leg,part in s['phase_specific_NAND'].items():
        if leg not in ['L','H']:continue
        q=s['NAND_internal_diagnostics'][leg];q['actual_A1_node']=part['actual_A1_node'];q['actual_A2_node']=part['actual_A2_node']
        q['first_input_edges']=part['A1_edges'];q['delayed_input_edges']=part['A2_edges']
        at=q['output_adjacent_absVds_peak_native_witness']['time_s']
        j=int(np.argmin(abs(d['w'][:,0]-at)))
        q['output_adjacent_absVds_peak_native_witness']['gate_input_V']=float(d['w'][j,d['c'][part['actual_A1_node']]])
    return s,rows


def plots(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    styles={'base':'--','swap':'-'};colors=['#176fa6','#c65c2e']
    footer='FF / 0.99 V / -40 C. Dashed: original native pin order; solid: L-only swap. C0 x1, real CDAC/Bootstrap + IO/Rgate; ideal CODE/rails/clock, comparator reset, other bits static; no noise/mismatch/PEX. Native time, no shifts.'
    fig,axes=plt.subplots(4,2,figsize=(13,9),layout='constrained')
    for j,(a,b,title) in enumerate([(42.99,43.3,'CODE rise: old negative stack hold'),
                                    (47.99,48.3,'CODE fall: residual transient')]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;ids=(t>=a)&(t<=b)
            for i,nodes in [(0,['xdut.xbbm0.cb','xdut.xbbm0.ld']),
                            (1,['xdut.xbbm0.x004.n','xdut.xbbm0.x004.x000.xlib.net10'])]:
                for z,n in enumerate(nodes):
                    tags=['CB','LD'] if i==0 else ['L NAND output','L stack node']
                    axes[i,j].plot(t[ids],w[ids,c[n]],styles[label],color=colors[z],lw=1.25,label=tags[z] if label=='swap' else None)
            for i,cell in [(2,'x004'),(3,'x002')]:
                out='xdut.xbbm0.'+cell+'.n';stack='xdut.xbbm0.'+cell+'.x000.xlib.net10'
                axes[i,j].plot(t[ids],w[ids,c[out]]-w[ids,c[stack]],styles[label],color='#777' if label=='base' else colors[0],lw=1.25,label='base' if label=='base' else 'L swap')
        for i,y in enumerate(['Actual CB/LD (V)','L NAND D/S nodes (V)','L MM4 Vds (V)','H MM4 Vds (V)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right')
            if i in [2,3]:
                ax.axhline(.99,color='#b75336',ls=':',lw=.8)
                ax.text(.01,.995,'0.99 V screen',transform=ax.get_yaxis_transform(),fontsize=7,color='#b75336')
        axes[0,j].set_title(title);axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('L NAND pin swap: separate 43 ns improvement from 48 ns residual',fontsize=13)
    zoom=axes[2,1].inset_axes([.59,.24,.38,.38])
    for label,d in waves.items():
        w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=48.095)&(t<=48.15)
        y=w[s,c['xdut.xbbm0.x004.n']]-w[s,c['xdut.xbbm0.x004.x000.xlib.net10']]
        zoom.plot(t[s],y,styles[label],color='#777' if label=='base' else colors[0],lw=1)
    zoom.axhline(.99,color='#b75336',ls=':',lw=.7)
    zoom.set(xlim=(48.095,48.15),ylim=(.987,.996),xticks=[48.10,48.14],yticks=[.99,.995])
    zoom.tick_params(labelsize=7);zoom.set_title('+2.307 mV at 48.123 ns',fontsize=7)
    fig.supxlabel(textwrap.fill(footer,160),fontsize=8)
    fig.savefig(OUT/'NAND_phase_specific_voltage.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(5,2,figsize=(13,11),layout='constrained')
    for j,(a,b,high) in enumerate([(42.98,44.2,True),(47.98,49.2,False)]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;ids=(t>=a)&(t<=b)
            for i,nodes in [(0,['xdut.h0','xdut.l0']),(1,['xdut.gnn0','xdut.gnp0']),
                              (2,['xdut.gpp0','xdut.gpn0'])]:
                for z,n in enumerate(nodes):
                    axes[i,j].plot(t[ids],w[ids,c[n]],styles[label],color=colors[z],lw=1.25,label=n.rsplit('.',1)[-1].upper() if label=='swap' else None)
            for z,m in enumerate(['mn_low','mp_high']):
                n='xdut.xcdac.xsn0.'+m+':1'
                axes[3,j].plot(t[ids],w[ids,c[n]]*1e6,styles[label],color=colors[z],lw=1.25,label=m+' D' if label=='swap' else None)
            for z,(n,r) in enumerate([('bn0','vrefp' if high else 'vrefn'),('bp0','vrefn' if high else 'vrefp')]):
                axes[4,j].plot(t[ids],(w[ids,c['xdut.xcdac.'+n]]-w[ids,c[r]])*1e3,styles[label],color=colors[z],lw=1.25,label=n.upper()+' error' if label=='swap' else None)
        for i,y in enumerate(['H/L (V)','N-side gates (V)','P-side gates (V)','N-side total D (uA)','Reference error (mV)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right')
        for i in [1,2]:axes[i,j].axhline(.495,color='#999',ls=':',lw=.8)
        axes[4,j].set_yscale('symlog',linthresh=1);axes[4,j].axhspan(-1,1,color='#258578',alpha=.1)
        axes[0,j].set_title('High selection' if high else 'Low selection');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('Real reference interface: both directions remain established',fontsize=13)
    fig.supxlabel(textwrap.fill(footer,160),fontsize=8)
    fig.savefig(OUT/'reference_order_current_settling.png',dpi=165);plt.close(fig)


def f(x,scale=1,digits=3):return '未观测' if x is None else format(x*scale,'.'+str(digits)+'f')


def report(data):
    a,b=data['base'],data['swap'];n=lambda d: d['phase_specific_NAND']['L']['phases']
    w=n(b)['CODE_fall']['MM4_Vds']['coincident_DGSB']['maximum']
    lines=['# L NAND 单只输入交换：FF 对照','',
        f"**43 ns的负向浮置明显改善，但没有全部合格。** L MM4原最大Vds=1.108483 V；交换后全窗最大为{w['Vds_V']:.6f} V，发生在另一相位{w['time_s']*1e9:.6f} ns。必须分开评价旧43 ns机制与新48 ns残余。",'',
        '只交换 L NAND A1/A2，H侧、其他190条叶记录、RC/clear、IO/Rgate及真实负载保持；52 ns测试台字节相同，FF 0.99 V/−40°C。CODE/电源/时钟理想，比较器复位、其他位静态；无噪声、失配、PEX。','',
        '| L侧相位 | 内部节点最小 V：原→交换 | 内部节点最大 V：原→交换 | MM4最大Vds V：原→交换 | 超0.99 V累计 ps：原→交换 |',
        '| --- | --- | --- | --- | --- |']
    for name in ['CODE_rise','CODE_fall']:
        x,y=n(a)[name],n(b)[name]
        vals=[f(x['stack']['min_V'],digits=6)+' → '+f(y['stack']['min_V'],digits=6),
              f(x['stack']['max_V'],digits=6)+' → '+f(y['stack']['max_V'],digits=6),
              f(x['MM4_Vds']['max_V'],digits=6)+' → '+f(y['MM4_Vds']['max_V'],digits=6),
              f(x['MM4_Vds']['abs_above0p99_duration_s'],1e12)+' → '+f(y['MM4_Vds']['abs_above0p99_duration_s'],1e12)]
        lines.append('| '+name+' | '+' | '.join(vals)+' |')
    lines+=['','相位分别为 [42.995,47.995) 与 [47.995,52] ns，使用原生同一时刻的D−S，不将不同时间的漏、源极值相减。持续时间为原生点间线性插值估计，不是寿命签核。','',
        '![NAND两相位](NAND_phase_specific_voltage.png)','',
        f"**残余发生于48 ns参考回切。** 在{w['time_s']*1e9:.6f} ns，D={w['D_V']:.6f} V、S={w['S_V']:.6f} V、G={w['G_V']:.6f} V、B=0，Vds={w['Vds_V']:.6f} V，仍超0.99 V约{(w['Vds_V']-.99)*1e3:.3f} mV；小幅超限持续时间由8.819增至34.328 ps。这不能被43 ns的改善抵消。",'',
        '| 功能 | 全部检查项 | 原严格超限 | 交换后严格超限 |',
        '| --- | --- | --- | --- |']
    for group,x in a['groups'].items():
        y=b['groups'][group];lines.append(f"| {group} | {x['records']} | {x['strict_exceed']} | {y['strict_exceed']} |")
    lines += [f"| **总计** | **738** | **{a['strict_exceed']}** | **{b['strict_exceed']}** |",'',
        f"超出各自门限1 mV的项数：{a['over1mV']} → {b['over1mV']}。严格计数逐项使用冻结目录中该器件的screen_v（核心0.99 V/IO1.98 V）与完整正负极值；738对名称一一对应。原生CMI告警仍在。完整实际节点、极值时刻、阶段和逐项变化保存在CSV。",'',
        '## 真实参考接口','',
        '| 方向 | BBM间隔 ps：原→交换 | N实际栅间隔 ps：原→交换 | P实际栅间隔 ps：原→交换 | N相反总D电流较小者峰值 µA：原→交换 |',
        '| --- | --- | --- | --- | --- |']
    for name,ph in [('select_high','CODE_rise'),('select_low','CODE_fall')]:
        vals=[f(a['control_events'][name][k],1e12)+' → '+f(b['control_events'][name][k],1e12) for k in ['BBM_signed_off_to_on_gap_s','N_signed_off_to_on_gap_s','P_signed_off_to_on_gap_s']]
        vals.append(f(a['phase_specific_NAND']['control_phase_reference_ports'][ph]['n']['opposed_total_D_min_peak_A'],1e6)+' → '+f(b['phase_specific_NAND']['control_phase_reference_ports'][ph]['n']['opposed_total_D_min_peak_A'],1e6))
        lines.append('| '+name+' | '+' | '.join(vals)+' |')
    lines+=['','半VDD顺序只是控制诊断；总D电流包含位移，不能称为纯沟道直通。','',
        '![真实参考接口](reference_order_current_settling.png)','',
        '| 方向 | 原BN0/BP0进入1mV ns | 交换后BN0/BP0 ns |',
        '| --- | --- | --- |']
    for phase in ['high','low']:
        vals=[' / '.join(f(q['remained_inside_from_native_s'],1e9,6) for q in d['physical_phase_settling'][phase].values()) for d in [a,b]]
        lines.append('| '+phase+' | '+' | '.join(vals)+' |')
    lines+=['','两版高相位均在下个CODE边沿开始前建立，低相位均在52 ns前建立。旧半轨窗口跨入切换，false只作切换诊断；1 mV不是新规格。','',
        '## H与RC对照、原因及下一步','',
        '| 对照项 | 原 | 交换后 |',
        '| --- | --- | --- |']
    for leg in ['HD','LD']:
        for key,desc in [('X005_gd_peak_V','X005最大绝对Vgd V'),('MP_CLEAR_ds_peak_V','MP_CLEAR最大绝对Vds V')]:
            lines.append('| '+leg+' '+desc+' | '+f(a['RC1_and_clear_stress'][leg][key],digits=6)+' | '+f(b['RC1_and_clear_stress'][leg][key],digits=6)+' |')
        for key in ['min','max']:
            lines.append('| '+leg+' RC1 '+key+' V | '+f(a['RC1_and_clear_stress'][leg]['RC1_extrema'][key],digits=6)+' | '+f(b['RC1_and_clear_stress'][leg]['RC1_extrema'][key],digits=6)+' |')
    for leg in ['L','H']:
        x,y=[d['NAND_internal_diagnostics'][leg]['output_adjacent_absVds_peak_native_witness'] for d in [a,b]]
        lines.append('| '+leg+' NAND MM4 全窗最大Vds V | '+f(x['Vds_V'],digits=6)+' | '+f(y['Vds_V'],digits=6)+' |')
    for leg in ['HD','LD']:
        def reset(d):
            vals=[q['delay_from_CODE_s'] for q in d['reset'][leg]['nodes'].values()]
            return None if any(q is None for q in vals) else max(vals)
        lines.append('| '+leg+'整腿复位1%延迟 ps | '+f(reset(a),1e12)+' | '+f(reset(b),1e12)+' |')
    lines.append('| CODE源净供能 fJ | '+f(a['CODE_source']['net_source_J'],1e15)+' | '+f(b['CODE_source']['net_source_J'],1e15)+' |')
    for node in ['xdut.xbbm0.cb','xdut.xbbm0.ld']:
        for phase in ['CODE_rise','CODE_fall']:
            x,y=[d['phase_specific_NAND']['CB_LD_actual_load_charge'][node]['phases'][phase] for d in [a,b]]
            lines.append('| '+node.rsplit('.',1)[-1].upper()+' '+phase+'净负载绝对电荷 fC | '+f(x['absolute_net_load_C'],1e15)+' | '+f(y['absolute_net_load_C'],1e15)+' |')
    lines+=['','电路参数不变不表示波形必须逐点不变：交换改变CB/LD的负载与输入耦合，可能经共享节点反馈；H侧仍作为未改拓扑对照。源电荷/分段电流/各源能量在JSON保留，内部端口功不重复计供电。','',
        '**机制判断：** 43 ns双下降时，交换让靠地CB先关、靠输出LD暂导通，内部节点可先从输出充电，避免原来长期负向浮置。这是输入串联位置影响端压的单变量证据。48 ns双上升则靠地CB先开、靠输出LD后开，内部节点已先放到地，因而接近VDD的漏端上冲/微小源端扰动仍可使Vds略超供电；实际同刻证据见上。H侧未交换，原48 ns内部负节点风险仍在，RC/clear过轨也不属于本次修复。','',
        '**下一最小实验建议：** 保持这版L交换和其余设置，只交换H NAND的A1/A2：CODE/HD→HD/CODE，在同一FF台验证H的48 ns负向浮置和全738项端压，同时保留L的2.307 mV残余为未解决项。先不叠加RC或驱动改动；该建议不是整机修复承诺，本轮未生成/提交新案例。','',
        '## 证据与限制','']
    for label,d in data.items():
        lines.append(f"- {d['run']}：{d['native_points']}点、{d['receipt_bytes']} B；result SHA256 {d['result_sha256']}；managed {d['managed_recipe_sha256']}。")
    lines+=['','原生PASS/PSF_END、652路电流初始化、11个回收文件大小/SHA和冻结输入逐项核验；两版实际求解设置相同。comparison.json保存完整量化，terminal_pairs.csv共1476条。只完成FF、单bit0理想边界对照，不能宣称SS/整机/功耗合格。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze():
    mapping=prior.device_mapping()
    waves={label:load_pair(label) for label in ['base','swap']}
    assert waves['base']['external_body']==waves['swap']['external_body']
    assert waves['base']['result']['native_effective_settings']==waves['swap']['result']['native_effective_settings']
    data={};rows=[]
    for label,d in waves.items():
        data[label],q=summarize(d,label,mapping);rows.extend(q)
    assert len(rows)==1476 and len({(x['variant'],x['mapped_pair']) for x in rows})==1476
    # Gate-pair nodes intentionally differ at exactly four actual native MOS.
    old={p['instance']+':'+p['terminal']:p for p in waves['base']['cfg']['selected_mos_pair_screens']}
    new={p['instance']+':'+p['terminal']:p for p in waves['swap']['cfg']['selected_mos_pair_screens']}
    assert set(old)==set(new) and sum(old[k]!=new[k] for k in old)==12
    OUT.mkdir(exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,
        scope='FF only; single L native NAND pin-order contrast, not ADC qualification'),indent=2)+'\n',encoding='utf-8')
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    plots(waves);report(data)
    print('L_SWAP_COMPARISON_READY',len(rows),{v:d['strict_exceed'] for v,d in data.items()})
    for v,d in data.items():print(v,{name:q['MM4_Vds']['max_V'] for name,q in d['phase_specific_NAND']['L']['phases'].items()})


if __name__=='__main__':analyze()


