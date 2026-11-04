"""Collected HD analog clear R: compare all stress and native node charge."""
import csv,gzip,hashlib,importlib.util,json,os,sys,textwrap
from pathlib import Path
OWN=Path(__file__).resolve().parent.parent
REF=OWN.parent
sys.path.insert(0,str(OWN));sys.path.append(str(REF));sys.path.append(str(REF/'standard_cell_bbm_hlswap_v1'))
import numpy as np
import yaml
from analyze_real_bbm import digest,HERE,ROOT
import analyze_standard_cell_bbm_lswap as previous
import analyze_standard_cell_bbm as prior
from rc1_event_measure import measure
OUT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_bytes())


def load(label):
    std=True;corner='ffcold';candidate=label=='R'
    name='sar8audit-ref-rc1-hd-cleargater-ff-v1' if candidate else 'sar8audit-ref-bbm-stdcell-hlswap-ff-v1'
    package=(OWN if candidate else REF/'standard_cell_bbm_hlswap_v1')/'ffcold';proposal=package/'recipe_proposal.json'
    assert digest(proposal)==('3805b0f88e1face70a166ecc407746bb6ce41d86c6359eacc5634de5dfc3f32b' if candidate else '739a937ac526501d15922f09de3babc87a4dc9270e9845a5731bfe50d26874e4')
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    assert registered['recipe_hash']==('f99c95e1c92a40c8abbe26f5456f77c03793e496538994c5ef75a17660a21e2b' if candidate else 'd0020c7f2887144d28c373ad052a6f24e81d0d4af120993e2c1066b7c8f186f7')
    assert receipt['total_bytes']==(27685183 if candidate else 26389195)
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    cfg=read(package/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(654 if candidate else 652)
    assert r['measurement_sha256']==digest(package/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert len(r['selected_mos_pair_extrema'])==738
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==(445 if candidate else 441)
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
        wanted.update([stem+'c1:1',stem+'r1:1',stem+'r1:2',stem+'x005.xlib.mm1:2',stem+'x005.xlib.mm0:2'])
    wanted.update('kcl:xdut.xbbm0.xd_'+leg+'.rc1' for leg in ['hd','ld'])
    wanted.update(b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='XDUT.XBBM0.HD')
    for leg in ['hd','ld']:
        wanted.update('xdut.xbbm0.xd_'+leg+'.x005.xlib.'+mos+':'+str(j) for mos in ['mm0','mm1'] for j in [1,2,3,4])
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
    assert count==(11420 if candidate else 11298) and count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def phase_pair(d,key,phase):
    return d['result']['cell_measurements']['all_terminal_native_phase_time']['phases'][phase]['pairs'][key]


def snap(d,t):
    w,c=d['w'],d['c'];j=int(np.argmin(abs(w[:,0]-t)));assert abs(w[j,0]-t)<1e-18
    nodes=['xdut.xbbm0.xd_hd.rc1','xdut.xbbm0.hd','code','xdut.xbbm0.x002.n']
    vals={n:float(w[j,c[n]]) for n in nodes}
    currents={}
    for name,bs in {'X005_output_D':['xdut.xbbm0.xd_hd.x005.xlib.mm1:1','xdut.xbbm0.xd_hd.x005.xlib.mm0:1'],
                    'NAND_HD_input_G':['xdut.xbbm0.x002.x000.xlib.mm4:2','xdut.xbbm0.x002.x000.xlib.mm1:2']}.items():
        currents[name]=float(sum(w[j,c[b]] for b in bs))
    return dict(time_s=t,voltages_V=vals,receiver_Vgd_V=vals[nodes[0]]-vals[nodes[1]],
        HD_incident_current_A=currents,HD_sum_A=sum(currents.values()))


def hd_output_lobe(d):
    w,c=d['w'],d['c'];t=w[:,0];y=w[:,c['xdut.xbbm0.hd']]
    ids=np.flatnonzero((t>=47.995e-9)&(t<=48.15e-9));peak=int(ids[np.argmax(y[ids])])
    before=ids[ids<=peak];q=before[y[before]<=.99];start=int(q[-1]) if len(q) else None
    incident={b.lower() for b,x in d['cfg']['terminal_current_catalog'].items() if x['node']=='XDUT.XBBM0.HD'}
    groups={'X005_output_D':['xdut.xbbm0.xd_hd.x005.xlib.mm1:1','xdut.xbbm0.xd_hd.x005.xlib.mm0:1'],
        'NAND_HD_input_G':['xdut.xbbm0.x002.x000.xlib.mm4:2','xdut.xbbm0.x002.x000.xlib.mm1:2']}
    assert incident=={b for q in groups.values() for b in q}
    v={n:sum(w[:,c[b]] for b in bs) for n,bs in groups.items()}
    native=np.arange(start,peak+1) if start is not None else np.array([],dtype=int)
    return dict(peak=snap(d,float(t[peak])),leading_start_s=None if start is None else float(t[start]),
        leading_charge_C=None if start is None else {n:float(np.trapezoid(z[native],t[native])) for n,z in v.items()},
        leading_max_KCL_A=None if start is None else float(max(abs(sum(v.values())[native]))),
        current_groups=groups,
        interpretation='Complete four-port incidence of HD; negative NAND gate total current returns charge, positive X005 D total absorbs it. No intrinsic fractions inferred.')


def same_measurement(a,b,path=''):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a:same_measurement(a[key],b[key],path+'/'+key)
    elif isinstance(a,list):
        assert len(a)==len(b)
        for i,(x,y) in enumerate(zip(a,b)):same_measurement(x,y,path+'/'+str(i))
    elif isinstance(a,float):
        # Remote Python2/native arithmetic and local Python3 may sum in a
        # different order; tolerate only accumulation roundoff, not thresholds.
        absolute=1e-20 if 'KCL_A' in path else 1e-28 if ('charge' in path.lower() or path.endswith('signed_C')) else 1e-20
        assert abs(a-b)<=absolute+1e-12*max(abs(a),abs(b)),path
    else:assert a==b,path


def summarize(d,label,mapping):
    s,rows=previous.summarize(d,label,mapping)
    folder=ROOT/'output/managed_execution/runs'/d['run']/'collected/derived'
    events=measure(d['result'],d['cfg'],str(folder))
    if label=='R':same_measurement(events,d['result']['cell_measurements']['RC1_actual_native_event_charge'])
    s['RC1_events']=events
    key='XDUT.XBBM0.XD_HD.X005.XLIB.MM1:gd';x=d['result']['selected_mos_pair_extrema'][key]
    s['HD_X005_signed_gd']=dict(positive=snap(d,x['max_time_s']),negative=snap(d,x['min_time_s']),
        full_above_limit_s=phase_pair(d,key,'full')['absolute_above_limit_duration_s'],
        full_positive_peak_V=x['max'],full_negative_peak_V=x['min'])
    s['HD_output_backflow']=hd_output_lobe(d)
    s['HD_clear_ds_time_s']=phase_pair(d,'XDUT.XBBM0.XD_HD.MP_CLEAR:ds','full')['absolute_above_limit_duration_s']
    return s,rows


def changes(waves):
    answer=[]
    specs={v:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for v,d in waves.items()}
    for key,old in waves['HL']['result']['selected_mos_pair_extrema'].items():
        new=waves['R']['result']['selected_mos_pair_extrema'][key];a,b=specs['HL'][key],specs['R'][key]
        assert a['model']==b['model'] and a['screen_v']==b['screen_v']
        f0=max(abs(old['min']),abs(old['max']))>a['screen_v'];f1=max(abs(new['min']),abs(new['max']))>b['screen_v']
        if f0==f1:continue
        answer.append(dict(pair=key,status='added' if f1 else 'resolved',limit_V=b['screen_v'],
            original_nodes=a['nodes'],new_nodes=b['nodes'],original_extrema=old,new_extrema=new,
            original_duration_s=phase_pair(waves['HL'],key,'full')['absolute_above_limit_duration_s'],
            new_duration_s=phase_pair(waves['R'],key,'full')['absolute_above_limit_duration_s']))
    return answer


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#176fa6','#c65c2e'];styles={'HL':'--','R':'-'}
    footer='FF0.99V/-40C. Dashed: frozen HL baseline; solid: HD clear-gate R only. Same native logic, original RC and real loads; ideal CODE/rails/clock, comparator reset. Native time, no shifts. 0.99V screen unchanged.'
    fig,axes=plt.subplots(4,2,figsize=(13,10),layout='constrained')
    for j,(a,b,pos) in enumerate([(42.99,43.16,True),(47.99,48.08,False)]):
        for label,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=a)&(t<=b);st='xdut.xbbm0.xd_hd.'
            gate='code' if label=='HL' else st+'clear_g'
            for i,nodes,tags in [(0,[gate,'code'],['Actual clear gate','CODE']),
                                  (1,[st+'rc1','xdut.xbbm0.hd'],['RC1','X005 output HD'])]:
                for z,n in enumerate(nodes):
                    if i==0 and z==1 and label=='HL':continue
                    axes[i,j].plot(t[q],w[q,c[n]],styles[label] if z==0 or i==1 else ':',color=colors[z],lw=1.2,label=tags[z] if label=='R' else None)
            y=w[:,c[st+'rc1']]-w[:,c['xdut.xbbm0.hd']]
            axes[2,j].plot(t[q],abs(y[q]),styles[label],color='#777' if label=='HL' else colors[0],lw=1.3,label=label+' X005 |Vgd|')
            for z,bs in enumerate([[st+'mp_clear:1'],[st+'c1:1']]):
                val=sum(w[:,c[b]] for b in bs)*1e6
                axes[3,j].plot(t[q],val[q],styles[label],color=colors[z],lw=1.2,label=['clear D','C1'][z] if label=='R' else None)
        axes[0,j].set_title('HD release / positive RC1' if pos else 'HD reset / negative RC1')
        for i,y in enumerate(['Actual analog gate (V)','Receiver G / D (V)','Receiver |Vgd| (V)','Into component (uA)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=7,ncol=2,loc='upper right')
            if i==2:ax.axhline(.99,color='#b75336',ls=':',lw=.8)
        axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('Clear-gate R lowers RC1 amplitude but changes timing of receiver stress',fontsize=13)
    fig.supxlabel(textwrap.fill(footer,160),fontsize=8);fig.savefig(OUT/'RC1_receiver_two_phases.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,8),layout='constrained')
    for j,label in enumerate(['HL','R']):
        d=waves[label];w,c=d['w'],d['c'];t=w[:,0]*1e9;q=(t>=47.995)&(t<=48.02);st='xdut.xbbm0.xd_hd.'
        for z,n in enumerate([st+'rc1','xdut.xbbm0.hd','xdut.xbbm0.x002.n']):
            axes[0,j].plot(t[q],w[q,c[n]],color=['#176fa6','#c65c2e','#258578'][z],lw=1.2,label=['RC1','X005 output HD','H NAND output'][z])
        for z,(name,bs) in enumerate({'X005 output D':['xdut.xbbm0.xd_hd.x005.xlib.mm1:1','xdut.xbbm0.xd_hd.x005.xlib.mm0:1'],
                    'NAND input G':['xdut.xbbm0.x002.x000.xlib.mm4:2','xdut.xbbm0.x002.x000.xlib.mm1:2']}.items()):
            axes[1,j].plot(t[q],sum(w[q,c[b]] for b in bs)*1e6,color=colors[z],lw=1.2,label=name)
        axes[2,j].plot(t[q],abs(w[q,c[st+'rc1']]-w[q,c['xdut.xbbm0.hd']]),color=colors[0],lw=1.3,label='X005 |Vgd|')
        axes[2,j].axhline(.99,color='#b75336',ls=':',lw=.8,label='0.99 V screen')
        at=d['result']['selected_mos_pair_extrema']['XDUT.XBBM0.XD_HD.X005.XLIB.MM1:gd']['min_time_s']
        witness=snap(d,at);x=at*1e9;y=abs(witness['receiver_Vgd_V'])
        for i in range(3):axes[i,j].axvline(x,color='#999',ls=':',lw=.7)
        axes[2,j].scatter([x],[y],s=16,color=colors[0],zorder=3)
        axes[2,j].annotate(f'{y:.6f} V',xy=(x,y),xytext=(x+.006,.86),fontsize=8,
            arrowprops=dict(arrowstyle='->',color='#666',lw=.7))
        for i,y in enumerate(['Concurrent nodes (V)','Into component (uA)','Actual |Vgd| (V)']):
            ax=axes[i,j];ax.set(xlim=(47.995,48.02),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=8,ncol=2,loc='upper right');ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title('Frozen HL baseline' if label=='HL' else 'HD clear-gate R');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('Negative-phase Vgd: delayed RC1 reset overlaps NAND gate backflow into HD',fontsize=13)
    fig.supxlabel(textwrap.fill(footer+' Total-port KCL identifies charge exchange, not intrinsic current fractions.',160),fontsize=8)
    fig.savefig(OUT/'HD_negative_phase_backflow.png',dpi=165);plt.close(fig)


def f(x,scale=1,digits=3):return '未观测' if x is None else format(x*scale,'.'+str(digits)+'f')


def report(data,delta):
    a,b=data['HL'],data['R']
    lines=['# HD clear栅串阻：幅度改善与时间代价','',
        '**正峰和下冲幅度均改善，但没有通过端压验证。** HD RC1正峰1.061723→1.026241 V，下冲−19.953→−16.508 mV；接收X005的全窗最坏|Vgd|仍1.035538 V。该最坏值已从正相位转到负相位。clear的超限幅度减小，但超限时间变长，不能只看峰值。','',
        'FF0.99V/−40°C，只有HD.MP_CLEAR栅串入同R0几何电阻；LD及其他原电路、普通原生逻辑、电源、采样窗口/关闭沿和外部刺激不变。CODE/电源/时钟理想、比较器复位，其他位静态；未含噪声/失配/PEX。','',
        '| 指标 | HL基线 | HD串阻 |','| --- | --- | --- |']
    metrics=[
        ('HD RC1正峰 V',lambda d:d['RC1_and_clear_stress']['HD']['RC1_extrema']['max'],1),
        ('HD RC1负峰 mV',lambda d:d['RC1_and_clear_stress']['HD']['RC1_extrema']['min'],1e3),
        ('HD X005正向Vgd峰值 V',lambda d:d['HD_X005_signed_gd']['full_positive_peak_V'],1),
        ('HD X005负向Vgd峰值 V',lambda d:d['HD_X005_signed_gd']['full_negative_peak_V'],1),
        ('HD X005绝对Vgd超0.99V累计 ps',lambda d:d['HD_X005_signed_gd']['full_above_limit_s'],1e12),
        ('HD clear最大绝对Vds V',lambda d:d['RC1_and_clear_stress']['HD']['MP_CLEAR_ds_peak_V'],1),
        ('HD clear绝对Vds超0.99V时长 ps',lambda d:d['HD_clear_ds_time_s'],1e12)]
    for desc,get,scale in metrics:lines.append('| '+desc+' | '+f(get(a),scale,6 if scale==1 else 3)+' | '+f(get(b),scale,6 if scale==1 else 3)+' |')
    lines+=['','![两相位幅度与时序](RC1_receiver_two_phases.png)','',
        '## 为什么负相位的接收Vgd仍高','']
    for label,d in data.items():
        q=d['HD_X005_signed_gd']['negative'];v=q['voltages_V']
        lines.append(f"- {label}负向Vgd最坏：{q['time_s']*1e9:.6f}ns，同刻G=RC1={v['xdut.xbbm0.xd_hd.rc1']:.6f} V，D=HD={v['xdut.xbbm0.hd']:.6f} V，Vgd={q['receiver_Vgd_V']:.6f} V。")
    lines+=['','串阻延后了clear开启/RC1复位。HD各自输出峰值时，基线RC1已回升到0.471209V，新版本RC1却仍为−0.016214V。新版本最坏Vgd时，RC1约−16.37mV、HD约1.01917V，同刻形成−1.035538V。虽然RC1负峰和HD输出正峰都比各自基线小，**二者的时间重合更不利**。因此正向接收峰从1.061623降到1.026231V，负向接收峰却从−1.009186恶化到−1.035538V。','',
        'HD输出并非理想VDD钳位：CODE下降使H NAND输出上升，其HD输入总G端向HD节点回送电荷。HD的完整入射集合只有接收反相器两个D端与NAND两个G端；预算闭合，方向显示反相器正在吸收下游回流。','',
        '| HD上冲前沿 | X005两D端电荷 fC | H NAND两G端电荷 fC | 最大KCL残差 pA |','| --- | --- | --- | --- |']
    for label,d in data.items():
        q=d['HD_output_backflow'];c=q['leading_charge_C']
        lines.append(f"| {label} | {c['X005_output_D']*1e15:.6f} | {c['NAND_HD_input_G']*1e15:.6f} | {q['leading_max_KCL_A']*1e12:.3f} |")
    v=b['HD_X005_signed_gd']['negative']['HD_incident_current_A']
    lines+=['',f"新版本最坏负Vgd时刻，NAND输入G总电流={v['NAND_HD_input_G']*1e6:.3f}µA，X005输出D总电流={v['X005_output_D']*1e6:.3f}µA；电流正方向为流入器件。它定位到下游门端回流与有限输出钳位能力，不把总端口电流拆成纯本征Cgd或沟道份额。",'',
        '![负相位回流与同刻端压](HD_negative_phase_backflow.png)','',
        '## 电荷、复位与真实接口','',
        '| 事件 | clear D到峰值电荷fC：HL→串阻 | clear D越轨至首次回轨净电荷fC：HL→串阻 | C1 / R1 / 接收G到峰值电荷fC：HL→串阻 |','| --- | --- | --- | --- |']
    for name in ['HD_positive','HD_negative','LD_positive','LD_negative']:
        q0,q1=[d['RC1_events']['events'][name]['leading']['charge_C'] for d in [a,b]]
        whole=[d['RC1_events']['events'][name]['whole_excursion']['charge_C']['MP_CLEAR_D'] for d in [a,b]]
        charges=lambda q:'/'.join(f(q[k],1e15,6) for k in ['C1','R1','X005_native_gates'])
        lines.append('| '+name+' | '+f(q0['MP_CLEAR_D'],1e15,6)+' → '+f(q1['MP_CLEAR_D'],1e15,6)+' | '+f(whole[0],1e15,6)+' → '+f(whole[1],1e15,6)+' | '+charges(q0)+' → '+charges(q1)+' |')
    lines+=['','积分窗口按各自原生跨轨、峰值及首次回轨定义，未平移；区间时刻及KCL在JSON。到峰值前的正向送入电荷减少且R1分流增加，支持边沿缓和；不同长度的峰前积分不等于整个CODE相位总注入。回轨净值含流入/流出抵消。负向抽走电荷减少较小，不能推出持续时间缩短。','',
        '| 指标 | HL | 串阻 |','| --- | --- | --- |']
    for leg in ['HD','LD']:
        get=lambda d:max(q['delay_from_CODE_s'] for q in d['reset'][leg]['nodes'].values())
        lines.append('| '+leg+'整腿进入1%复位 ps | '+f(get(a),1e12)+' | '+f(get(b),1e12)+' |')
    for phase in ['select_high','select_low']:
        for side in ['N','P']:
            k=side+'_signed_off_to_on_gap_s'
            lines.append('| '+phase+' '+side+'实际栅间隔 ps | '+f(a['control_events'][phase][k],1e12)+' | '+f(b['control_events'][phase][k],1e12)+' |')
    for phase in ['high','low']:
        get=lambda d:' / '.join(f(q['remained_inside_from_native_s'],1e9,6) for q in d['physical_phase_settling'][phase].values())
        lines.append('| '+phase+' BN0/BP0进入1mV ns | '+get(a)+' | '+get(b)+' |')
    lines+=['','两腿复位和四个物理参考建立判据均true，但HD复位明显变慢。半VDD间隔只是顺序诊断，1mV/1%是既有测量值。新CLEAR_G在0..VDD范围内，不能据此判全部器件端压通过。','',
        '## 全窗738项与下一必要变量','']
    lines.append(f"严格超限{a['strict_exceed']}→{b['strict_exceed']}；超出各自门限1mV的项数{a['over1mV']}→{b['over1mV']}。")
    lines.append('')
    for q in delta:
        x=q['new_extrema'];positive=abs(x['max'])>=abs(x['min']);value=x['max'] if positive else x['min'];at=x['max_time_s'] if positive else x['min_time_s']
        lines.append(f"- {'新增' if q['status']=='added' else '消失'} {q['pair']}：峰值{value:.12f}V，{at*1e9:.9f}ns；门限{q['limit_V']}V，超限时长{q['original_duration_s']*1e12:.6f}→{q['new_duration_s']*1e12:.6f}ps。")
    lines+=['','新增clear gd属于亚微伏边界，必须保留严格计数，但不能与几十mV过轨等量解读。RC1/接收/clear的其他严格超限、原生CMI和既有NAND残余全部保留；本对照未采用为合格基线。','',
        '**建议仅考察一个后续变量：HD X005的原生库驱动档位。** 先核验库中存在的更强反相单元，保持本次串阻、其余电路和外部时序/负载不变，只换该标准单元master，检验其吸收NAND门端回流的能力。更强单元也会增加RC1输入负担，必须同时复核正负端压、建立/复位和实际栅顺序；并不保证0.99V无余量条件下通过。不继续只加大clear串阻，因为本轮已显示负相位重合与复位代价。这里只给建议，不假定具体库型号存在，不准备或启动新实验。','',
        '## 来源与限制','']
    for label,d in data.items():lines.append(f"- {d['run']}：{d['native_points']}点、{d['receipt_bytes']}B；result SHA256 {d['result_sha256']}；managed {d['managed_recipe_sha256']}。")
    lines+=['','回执无跳过；文件/冻结输入/原生流SHA、大小、PASS/END、652/654路电流初始化核验。全738项真实端点/门限及full/rise/fall持续时间保留，445列新增测量与原441列无时间平移；刺激及模型/solver相同，仅新增必要save。数值见comparison.json，逐端压1476行见terminal_pairs.csv，状态变更见status_changes.json。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze():
    waves={v:load(v) for v in ['HL','R']};assert waves['HL']['external_body']==waves['R']['external_body']
    assert waves['HL']['result']['native_effective_settings']==waves['R']['result']['native_effective_settings']
    mapping=prior.device_mapping();data={};rows=[]
    for v,d in waves.items():
        data[v],q=summarize(d,v,mapping);rows.extend(q)
        native=d['result']['cell_measurements']['all_terminal_native_phase_time']
        assert len(native['phases']['full']['pairs'])==738
        assert native['phases']['full']['strict_native_pair_count']==data[v]['strict_exceed']
    delta=changes(waves);assert len(rows)==1476
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None),indent=2)+'\n',encoding='utf-8')
    (OUT/'status_changes.json').write_text(json.dumps(dict(changes=delta),indent=2)+'\n',encoding='utf-8')
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves);report(data,delta)
    print('RC1_CLEAR_R_COMPARISON_READY',len(rows),{k:q['strict_exceed'] for k,q in data.items()},'status_changes',len(delta))


if __name__=='__main__':analyze()


