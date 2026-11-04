"""Full-BBM physical phase interpretation; frozen remote metrics stay read-only."""
import argparse,csv,gzip,hashlib,json,os,re
import numpy as np
from compare_io_cell import HERE,ROOT

OUT=HERE/'generated/real_bbm_comparison'
HASHES={'ffcold':'7559d2fd8cb85edf5034c7711babe6f653611d0b52bba9b122f2b1616b87820a',
        'sscold':'6bea4e28904ad1adfd0ba8791fbe1f9caf5a6c80d15870218dab2c2ae39e89ec'}


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load(corner):
    name='sar8audit-real-bbm-'+corner;folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert not receipt['skipped'] and len(receipt['files'])==11 and receipt['status']['registered']['recipe_hash']==HASHES[corner]
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    assert receipt['total_bytes']==sum(x['bytes'] for x in receipt['files'])
    assert receipt['total_bytes']=={'ffcold':22435355,'sscold':22627864}[corner]
    cfgpath=HERE/'generated/real_bbm_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text());recipe=json.loads((cfgpath.parent/'recipe_proposal.json').read_text())
    for x in recipe['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());state=json.loads((folder/'simulation.state.json').read_text())
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['measurement_sha256']==digest(cfgpath)
    assert r['selected_current_count']==656 and r['all_selected_currents_present_and_initialized'] and r['native_PSF_END']
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');assert len(e['columns'])==376
    wanted=set(cfg['diagnostic_voltage_columns'])|{'time','vcode:1','vvdd:1','rrefp:1','rrefn:1','vrefhigh:1','vreflow:1'}
    m=r['cell_measurements']
    for q in m['internal_driver_load_work'].values():wanted.update(q['source_port_branches']+q['load_port_branches'])
    wanted.update(m['CODE_source_and_input_load']['incident_load_branches'])
    for side in ['n','p']:wanted.update('xdut.xcdac.xs'+side+'0.'+n+':1' for n in ['mn_low','mp_high'])
    for leg in ['hd','ld']:
        stem='xdut.xbbm0.xd_'+leg+'.';wanted.update(stem+n for n in ['mp_clear:1','mp_clear:2','mp_clear:3','mp_clear:4','c1:1','r1:2','x005.mn:2','x005.mp:2'])
    assert wanted<=set(e['columns']);ids=[j for j,n in enumerate(e['columns']) if n in wanted];columns=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');h=hashlib.sha256();count=0;stride=8*len(e['columns']);total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as stream:
        while True:
            raw=stream.read(stride*128)
            if not raw:break
            assert len(raw)%stride==0;h.update(raw);total+=len(raw);a=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']))
            w[count:count+len(a)]=a[:,ids];count+=len(a)
    assert count==r['native_points'] and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    assert count=={'ffcold':11326,'sscold':10975}[corner]
    # Verify the independent phase boundary from the frozen PWL, not a gate threshold.
    line=next(x for x in (cfgpath.parent/'test.scs').read_text().splitlines() if x.startswith('VCODE '))
    points=[float(x) for x in re.search(r'wave=\[(.*?)\]',line)[1].split()]
    assert points[6]==47.995e-9 and points[8]==48.005e-9
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},result_sha256=digest(folder/'derived/result.json'),
        receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=HASHES[corner],selected_columns=len(columns))


def window(d,node,ref,a,b,closed=False):
    w,c=d['w'],d['c'];t=w[:,0];ids=np.flatnonzero((t>=a)&((t<=b) if closed else (t<b)));assert len(ids)>1
    y=w[ids,c[node]]-w[ids,c[ref]];bad=np.flatnonzero(abs(y)>.001)
    first=None if len(bad) and bad[-1]==len(ids)-1 else int(bad[-1]+1) if len(bad) else 0
    return dict(requested_interval_s=[a,b],last_boundary_included=closed,native_interval_s=[float(t[ids[0]]),float(t[ids[-1]])],
        min_error_V=float(y.min()),max_error_V=float(y.max()),final_error_V=float(y[-1]),
        last_outside_1mV_s=None if not len(bad) else float(t[ids[bad[-1]]]),
        remained_inside_from_native_s=None if first is None else float(t[ids[first]]),diagnostic_established=first is not None)


def currents(d,a,b):
    w,c=d['w'],d['c'];ids=np.flatnonzero((w[:,0]>=a)&(w[:,0]<b));assert len(ids)>1;t=w[ids,0]
    branches=['rrefp:1','rrefn:1','vrefhigh:1','vreflow:1','vcode:1','vvdd:1']
    q={n:dict(signed_charge_C=float(np.trapezoid(w[ids,c[n]],t)),min_A=float(w[ids,c[n]].min()),max_A=float(w[ids,c[n]].max())) for n in branches}
    for label,node,branch in [('CODE','code','vcode:1'),('VDD','vdd!','vvdd:1')]:q[label+'_delivered_work_J']=float(np.trapezoid(-w[ids,c[node]]*w[ids,c[branch]],t))
    return dict(requested_interval_s=[a,b],actual_native_interval_s=[float(t[0]),float(t[-1])],values=q,
        signs='Positive into named element. RREF port1 positive feeds the reference node; source port1 negative supplies current.')


def rc1_lobe(d,leg,a,b):
    w,c=d['w'],d['c'];t=w[:,0];stem='xdut.xbbm0.xd_'+leg+'.';node=stem+'rc1';rail=d['result']['supply_V'];ids=np.flatnonzero((t>=a)&(t<=b))
    peak=int(ids[np.argmax(w[ids,c[node]])]);before=ids[(ids<=peak)&(w[ids,c[node]]<=rail)];start=int(before[-1]) if len(before) else int(ids[0]);s=np.arange(start,peak+1)
    branches={'MP_CLEAR_D':[stem+'mp_clear:1'],'C1':[stem+'c1:1'],'R1':[stem+'r1:2'],'X005_gates':[stem+'x005.mn:2',stem+'x005.mp:2']}
    y={n:sum(w[:,c[k]] for k in bs) for n,bs in branches.items()}
    return dict(node=node,leading_native_interval_s=[float(t[start]),float(t[peak])],peak_V=float(w[peak,c[node]]),
        signed_port_charge_C={n:float(np.trapezoid(v[s],t[s])) for n,v in y.items()},peak_port_A={n:float(v[peak]) for n,v in y.items()},
        MP_CLEAR_peak_DGSB_A={str(j):float(w[peak,c[stem+'mp_clear:'+str(j)]]) for j in [1,2,3,4]},
        max_KCL_A=float(np.max(abs(sum(y.values())[s]))),note='Total-port charge only; no intrinsic Cgd/channel/diode decomposition.')


def analyze_case(d,corner):
    r,m,w,c=d['result'],d['result']['cell_measurements'],d['w'],d['c'];rows=[];groups={}
    prior_dir=ROOT/'output/managed_execution/runs'/('sar8audit-real-l0-'+corner)/'collected/derived';prior_result=json.loads((prior_dir/'result.json').read_text())
    prior_bound=json.loads((HERE/'generated/real_l0_comparison/comparison.json').read_text())['source_runs'][corner]['real_L0']
    assert digest(prior_dir/'result.json')==prior_bound['result_sha256']
    prior_cfg=json.loads((HERE/'generated/real_l0_v1'/corner/'measurement.json').read_text());assert digest(HERE/'generated/real_l0_v1'/corner/'measurement.json')==prior_result['measurement_sha256']
    prior_specs={p['instance']+':'+p['terminal']:p for p in prior_cfg['selected_mos_pair_screens']};mapped=set()
    for p in d['cfg']['selected_mos_pair_screens']:
        n=p['instance'];key=n+':'+p['terminal'];x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
        group='BBM' if n.startswith('XDUT.XBBM0.') else 'H_driver' if n.startswith('XDUT.X008.') or re.fullmatch(r'XDUT.G(?:NP|PN)[ABC][NP]',n) else 'X025' if '.X025.' in n else 'GNN_ABC_IO' if re.fullmatch(r'XDUT.GNN[ABC][NP]',n) else 'GPP_IO' if re.fullmatch(r'XDUT.GPPI[NP]',n) else 'physical_load'
        oldkey=key.replace('XDUT.XBBM0.X004.X001.','XDUT.L0SRC.');oldspec=prior_specs.get(oldkey);oldpeak=None
        if oldspec:
            assert (oldspec['model'],oldspec['screen_v'])==(p['model'],p['screen_v']);mapped.add(oldkey);xx=prior_result['selected_mos_pair_extrema'][oldkey];oldpeak=max(abs(xx['min']),abs(xx['max']))
        rows.append(dict(corner=corner,group=group,pair=key,model=p['model'],screen_V=p['screen_v'],min_V=x['min'],max_V=x['max'],excess_V=peak-p['screen_v'],
            provenance='retained_or_relocated' if oldspec else 'newly_restored',prior_pair=oldkey if oldspec else None,prior_abs_peak_V=oldpeak,prior_excess_V=None if oldpeak is None else oldpeak-p['screen_v']))
    assert mapped==set(prior_specs) and len(mapped)==486
    provenance={}
    for label in ['retained_or_relocated','newly_restored']:
        q=[x for x in rows if x['provenance']==label];provenance[label]=dict(records=len(q),current_strict_exceed=sum(x['excess_V']>0 for x in q),prior_strict_exceed=None if label=='newly_restored' else sum(x['prior_excess_V']>0 for x in q))
    for group in sorted({x['group'] for x in rows}):
        q=[x for x in rows if x['group']==group];worst=max(q,key=lambda x:x['excess_V']);groups[group]=dict(records=len(q),strict_exceed=sum(x['excess_V']>0 for x in q),over1mV=sum(x['excess_V']>.001 for x in q),worst=worst)
    high={n:window(d,n,ref,43.005e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
    low={n:window(d,n,ref,48.005e-9,52e-9,True) for n,ref in [('xdut.xcdac.bn0','vrefn'),('xdut.xcdac.bp0','vrefp')]}
    frozen=m['actual_correct_ON_settling']['select_high'];end=frozen['stop_s']
    disturbance={n:window(d,n,ref,47.995e-9,end,True) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
    quiet={n:window(d,n,ref,47e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]}
    witnesses={}
    for node in ['xdut.xcdac.bn0','xdut.xcdac.bp0']:
        x=r['voltage_and_current_extrema'][node];time=x['min_time_s'];idx=int(np.argmin(abs(w[:,0]-time)));assert abs(w[idx,0]-time)<1e-18
        cols=['code','xdut.h0','xdut.l0','xdut.gnn0','xdut.gnp0','xdut.gpn0','xdut.gpp0','vrefp','vrefn','rrefp:1','rrefn:1']
        cols += ['xdut.xcdac.xs'+s+'0.'+n+':1' for s in ['n','p'] for n in ['mn_low','mp_high']]
        witnesses[node]=dict(min_V=x['min'],time_s=time,actual_values={n:float(w[idx,c[n]]) for n in cols})
    return dict(run=d['run'],result_sha256=d['result_sha256'],managed_recipe_sha256=d['managed_recipe_sha256'],receipt_bytes=d['receipt_bytes'],native_points=r['native_points'],
        groups=groups,pair_provenance=provenance,prior_mapped_result_sha256=prior_bound['result_sha256'],command_stable_high=high,late_quiet_high=quiet,command_stable_low=low,post_CODE_pre_halfVDD_disturbance=disturbance,
        frozen_high_ON_metric_preserved=frozen,frozen_control_events=m['actual_control_events'],frozen_sampled_HL_overlap=m['sampled_HL_mutual_exclusion'],
        negative_bottom_witnesses=witnesses,RC1_charge_paths={'HD_CODE_rise':rc1_lobe(d,'hd',42.99e-9,43.02e-9),'LD_after_CODE_fall':rc1_lobe(d,'ld',47.99e-9,48.03e-9)},
        phase_source_flows={'quiet_high':currents(d,47e-9,47.995e-9),'CODE_to_first_half_off':currents(d,47.995e-9,end),
                            'reference_handoff':currents(d,end,m['actual_correct_ON_settling']['select_low']['start_native_control_estimate_s']),
                            'late_low':currents(d,51e-9,52e-9)},
        source_and_load_work=m['internal_driver_load_work'],CODE_source_work=m['CODE_source_and_input_load'],stage_energy_J=m['reference_control_direct_VDD_energy_J'],
        rails=m['supply_rail_excursions'],body_polarity=m['body_forward_polarity'],opposed_total_reference_ports=m['opposed_total_reference_terminal_current'],
        warnings=r['native_warning_codes'],native_settings=r['native_effective_settings'],acceptance_pass=None),rows


def figures(waves,data):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False});corners=list(waves)
    fig,axes=plt.subplots(4,len(corners),figsize=(6.4*len(corners),9),squeeze=False,layout='constrained')
    for j,corner in enumerate(corners):
        d=waves[corner];w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=42.9)&(t<=50.5)
        for n,color,style in [('code','#777','--'),('xdut.h0','#126da1','-'),('xdut.l0','#c76631','-')]:axes[0,j].plot(t[s],w[s,c[n]],style,color=color,lw=1.2,label=n.split('.')[-1].upper())
        for i,pair in [(1,['xdut.gnn0','xdut.gnp0']),(2,['xdut.gpn0','xdut.gpp0']),(3,['xdut.xcdac.bn0','xdut.xcdac.bp0'])]:
            for n,color in zip(pair,['#126da1','#c76631']):axes[i,j].plot(t[s],w[s,c[n]],color=color,lw=1.25,label=n.split('.')[-1].upper())
        axes[3,j].plot(t[s],w[s,c['vrefp']],':',color='#777',lw=.9,label='VREFP');axes[3,j].plot(t[s],w[s,c['vrefn']],':',color='#999',lw=.9,label='VREFN')
        for i,label in enumerate(['CODE / H / L (V)','N-side gates (V)','P-side gates (V)','Bottom / reference (V)']):
            ax=axes[i,j];ax.set(xlim=(42.9,50.5),ylabel=label);ax.grid(alpha=.16);ax.axvline(47.995,color='#999',ls=':',lw=.8);ax.legend(fontsize=8,ncol=2,loc='center right')
        axes[0,j].set_title(('FF /0.99 V' if corner=='ffcold' else 'SS /0.81 V')+' /-40 C');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('Complete bit0 BBM and real four-gate reference handoff',fontsize=13)
    fig.supxlabel('Original BBM + H driver; tested GNN ABC IO / single IO GPP; physical CDAC/reference/Bootstrap; other bits static\nIdeal CODE, rails and sampling clock; comparator reset; no noise/mismatch/PEX. Dotted 47.995 ns = next CODE edge begins.',fontsize=8)
    fig.savefig(OUT/'full_BBM_timing.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(4,len(corners),figsize=(6.4*len(corners),9),squeeze=False,layout='constrained')
    for j,corner in enumerate(corners):
        d=waves[corner];w,c=d['w'],d['c'];t=w[:,0]*1e9;half=data[corner]['frozen_high_ON_metric_preserved']['stop_s']*1e9;end=half+.045;s=(t>=47.97)&(t<=end)
        for n,color,style in [('code','#777','--'),('xdut.h0','#126da1','-')]:axes[0,j].plot(t[s],w[s,c[n]],style,color=color,lw=1.3,label=n.split('.')[-1].upper())
        for n,color in [('xdut.gnp0','#126da1'),('xdut.gpn0','#c76631')]:axes[1,j].plot(t[s],w[s,c[n]],color=color,lw=1.3,label=n.split('.')[-1].upper())
        for n,ref,color,label in [('xdut.xcdac.bn0','vrefp','#126da1','BN0 - VREFP'),('xdut.xcdac.bp0','vrefn','#c76631','BP0 - VREFN')]:axes[2,j].plot(t[s],(w[s,c[n]]-w[s,c[ref]])*1e3,color=color,lw=1.3,label=label)
        for n,color in [('rrefp:1','#126da1'),('rrefn:1','#c76631')]:axes[3,j].plot(t[s],w[s,c[n]]*1e6,color=color,lw=1.3,label=n.upper())
        for i,label in enumerate(['CODE / H (V)','High-reference gates (V)','Error to old high refs (mV)','Reference feed current (uA)']):
            ax=axes[i,j];ax.set(xlim=(47.97,end),ylabel=label);ax.axvspan(47.97,47.995,color='#238a72',alpha=.10);ax.axvspan(47.995,half,color='#777',alpha=.09)
            ax.axvline(47.995,color='#777',ls='--',lw=.8);ax.axvline(half,color='#bc5634',ls=':',lw=.9);ax.grid(alpha=.16);ax.legend(fontsize=8,loc='upper left');ax.ticklabel_format(useOffset=False,axis='x')
        for level in [-1,1]:axes[2,j].axhline(level,color='#238a72',ls=':',lw=.7)
        axes[0,j].set_title(('FF /0.99 V' if corner=='ffcold' else 'SS /0.81 V')+' /-40 C');axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('High-state end metric crossed into the next turnoff',fontsize=13)
    fig.supxlabel('Same full-BBM fixture | green = before CODE falls; gray = CODE edge to first high-gate halfVDD crossing\nErrors stay referenced to old high targets to expose switching disturbance, not stable-high settling failure.',fontsize=8)
    fig.savefig(OUT/'high_window_turnoff_disturbance.png',dpi=165);plt.close(fig)
    if set(corners)==set(HASHES):
        fig,axes=plt.subplots(3,2,figsize=(12.8,7.8),layout='constrained')
        d=waves['ffcold'];w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=42.99)&(t<=43.025);stem='xdut.xbbm0.xd_hd.'
        for n,color,label in [('code','#777','CODE / MP_CLEAR gate'),(stem+'rc1','#126da1','RC1')]:axes[0,0].plot(t[s],w[s,c[n]],color=color,lw=1.3,label=label)
        axes[0,0].axhline(.99,color='#b75336',ls=':',lw=.8);axes[1,0].plot(t[s],abs(w[s,c[stem+'rc1']]-w[s,c['xdut.xbbm0.hd']]),color='#126da1',label='|RC1 - HD| = |Vgd(X005)|')
        axes[1,0].axhline(.99,color='#b75336',ls='--',lw=.9,label='0.99 V core screen')
        for n,color,label in [(stem+'mp_clear:1','#b75336','MP_CLEAR D'),(stem+'c1:1','#126da1','C1'),(stem+'r1:2','#258578','R1')]:axes[2,0].plot(t[s],w[s,c[n]]*1e6,color=color,lw=1.2,label=label)
        for i,label in enumerate(['Gate / RC1 (V)','X005 gate-drain (V)','Incident total current (uA)']):axes[i,0].set(xlim=(42.99,43.025),ylabel=label);axes[i,0].legend(fontsize=8)
        axes[0,0].set_title('FF /0.99 V /-40 C: HD-leg RC1 kick');axes[-1,0].set_xlabel('Native time (ns)')
        d=waves['sscold'];w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=43.18)&(t<=44.05)
        ev=data['sscold']['frozen_control_events']['select_high']['native_halfVDD_witnesses'];a=ev['xdut.gnp0']['estimated_time_s']*1e9;b=ev['xdut.gnn0']['estimated_time_s']*1e9
        for n,color in [('xdut.gnn0','#126da1'),('xdut.gnp0','#c76631')]:axes[0,1].plot(t[s],w[s,c[n]],color=color,lw=1.3,label=n.split('.')[-1].upper())
        axes[0,1].axhline(.405,color='#777',ls=':',lw=.8,label='VDD/2')
        for n,color,label in [('xdut.xcdac.xsn0.mn_low:1','#126da1','Low switch D'),('xdut.xcdac.xsn0.mp_high:1','#c76631','High switch D')]:axes[1,1].plot(t[s],w[s,c[n]]*1e6,color=color,lw=1.3,label=label)
        for n,color,label in [('xdut.xcdac.bn0','#126da1','BN0'),('vrefp','#888','VREFP'),('vrefn','#bbb','VREFN')]:axes[2,1].plot(t[s],w[s,c[n]],color=color,lw=1.2,label=label)
        for i,label in enumerate(['N-side actual gates (V)','Total drain current (uA)','Bottom / reference (V)']):
            axes[i,1].set(xlim=(43.18,44.05),ylabel=label);axes[i,1].axvspan(a,b,color='#b75336',alpha=.12);axes[i,1].legend(fontsize=8)
        axes[0,1].set_title('SS /0.81 V /-40 C: N-side gap -191.747 ps');axes[-1,1].set_xlabel('Native time (ns)')
        for ax in axes.flat:ax.grid(alpha=.16);ax.ticklabel_format(useOffset=False,axis='x')
        fig.suptitle('Distinct remaining issues: FF RC1 overstress and SS driver-delay imbalance',fontsize=13)
        fig.supxlabel('Same complete bit0 BBM/real-load fixtures; ideal CODE/rails, comparator reset, no noise/mismatch/PEX\nShading = actual gate halfVDD ordering; total currents include displacement and do not isolate channel current.',fontsize=8)
        fig.savefig(OUT/'RC1_kick_and_SS_gate_overlap.png',dpi=165);plt.close(fig)


def report(data):
    lines=['# 完整 bit0 BBM：建立与切换扰动分开判读','',
        '**高状态末值的原 `false` 不能直接解释为“高参考未建立”。** 冻结分析窗口延伸到高端栅极半 VDD 交点，已经跨过下一次 CODE 下降。原 JSON 不改，下面新增以 CODE 开始下降前为终点的独立测量。','',
        '环境：完整原 bit0 BBM／高端驱动，GNN ABC IO、单级 IO GPP、原 X025、物理 CDAC／参考／Bootstrap，其他位静态；理想 CODE／电源／采样时钟，比较器复位。FF 0.99 V／SS 0.81 V，均 −40°C，52 ns；无噪声、失配、PEX。','',
        '| 角落 | CODE 边沿前持续进入 ±1 mV：BN0／BP0 ns | 边沿前最后误差：BN0／BP0 mV | 原窗口最后时刻 ns／原误差 mV |',
        '| --- | --- | --- | --- |']
    for corner,d in data.items():
        q=d['command_stable_high'];f=d['frozen_high_ON_metric_preserved'];a,b=q['xdut.xcdac.bn0'],q['xdut.xcdac.bp0']
        times='/'.join('未建立' if x['remained_inside_from_native_s'] is None else f"{x['remained_inside_from_native_s']*1e9:.6f}" for x in [a,b]);err='/'.join(f"{x['final_error_V']*1e3:+.9f}" for x in [a,b])
        fn=f['nodes'];lines.append(f"| {corner} | {times} | {err} | {fn['xdut.xcdac.bn0']['last_native_s']*1e9:.9f} / {fn['xdut.xcdac.bn0']['final_error_V']*1e3:+.3f}, {fn['xdut.xcdac.bp0']['final_error_V']*1e3:+.3f} |")
    lines+=['','独立高状态区间为 CODE 完成上升的 43.005 ns 到下次下降开始的 47.995 ns（终点不含）；逐侧误差比较实际 VREFP／VREFN。进入时间取最后一次超出 ±1 mV 后的首个原生点，并要求持续到区间末尾。1 mV 是原有诊断阈值，不替换 ADC 规格。','',
        '![完整时序](generated/real_bbm_comparison/full_BBM_timing.png)','',
        'CODE 在 47.995–48.005 ns 下降，实际 H 与高端栅压随即变化。关断期间的电容耦合／电荷再分配可以在半 VDD 交点之前改变底板；半 VDD 是时序读数，不能当作晶体管开始关断的物理边界。因此原末值应称为“下一切换过程中的旧参考残差”，不能归为稳态高状态建立误差。切换扰动是真实电压变化，也不能因修正测量窗口而宣称其不存在。','',
        '![窗口跨入关断阶段](generated/real_bbm_comparison/high_window_turnoff_disturbance.png)','',
        '| 角落 | BBM H/L 正间隔 ps，高／低 | N侧／P侧实际门控间隔 ps，高；低 | 低参考持续进入 ±1 mV ns，BN0／BP0 |',
        '| --- | --- | --- | --- |']
    for corner,d in data.items():
        ev=d['frozen_control_events'];h,l=ev['select_high'],ev['select_low'];lo=d['command_stable_low'];times='/'.join('未建立' if lo[n]['remained_inside_from_native_s'] is None else f"{lo[n]['remained_inside_from_native_s']*1e9:.6f}" for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0'])
        lines.append(f"| {corner} | {h['BBM_signed_off_to_on_gap_s']*1e12:.3f}/{l['BBM_signed_off_to_on_gap_s']*1e12:.3f} | {h['N_signed_off_to_on_gap_s']*1e12:.3f}/{h['P_signed_off_to_on_gap_s']*1e12:.3f}; {l['N_signed_off_to_on_gap_s']*1e12:.3f}/{l['P_signed_off_to_on_gap_s']*1e12:.3f} | {times} |")
    lines+=['','**SS 的 H/L 正间隔没有传递成 N 侧实际栅极正间隔。** GNP0 在 43.259313 ns 越过半 VDD，GNN0 到 43.451059 ns 才越过，次序相差 −191.747 ps：核心高端链较快，IO GNN 链较慢。同阶段 N 侧相反方向总 D 电流峰值的较小者约 10.863 µA，需保留并通风险；不能因最终电平建立或无 CMI 而忽略。','',
        'H/L 半 VDD 同高采样时长为零只说明该逻辑诊断没有重叠，不证明后级 MOS 无同时导通。反向参考端总电流及偏置原记录保留；总端口电流包含位移电流，不能单独定量当作沟道直通或漏电。','',
        'SS 的 BN0 负峰较小也不能直接当作改善：最低点时 GNN0 约0.836 V、GNP0约0.378 V，低端栅压尚未下降，和 FF 的交接条件不同。比较尖峰大小前必须同时看门控次序及支路电流。','',
        '| 角落 | BBM 超限 | 高端驱动超限 | X025 超限 | GNN／GPP IO 超限 |',
        '| --- | --- | --- | --- | --- |']
    for corner,d in data.items():
        g=d['groups'];fmt=lambda n:f"{g[n]['strict_exceed']}/{g[n]['records']}";lines.append(f"| {corner} | {fmt('BBM')} | {fmt('H_driver')} | {fmt('X025')} | {fmt('GNN_ABC_IO')} / {fmt('GPP_IO')} |")
    lines+=['','核心仍按 0.99 V、IO 暂按 1.98 V 筛查。不能把新台738项的失败数直接与旧台486项比较：先按同器件映射区分保留／迁移器件和新增恢复器件。','',
        '| 角落 | 同器件映射486项：旧→新超限 | 新恢复252项超限 |',
        '| --- | --- | --- |']
    for corner,d in data.items():
        p=d['pair_provenance'];a,b=p['retained_or_relocated'],p['newly_restored'];lines.append(f"| {corner} | {a['prior_strict_exceed']} → {a['current_strict_exceed']} | {b['current_strict_exceed']}/{b['records']} |")
    lines+=['','映射包括 L0SRC→原 BBM 输出对；相同模型／尺寸的器件仍受新边界和 H 负载时序影响，比较不是同一刺激下的器件改尺寸实验。建立正常不抵消端压失效；原生 CMI／其他告警及比较器负载微伏级严格超限保留。','',
        '![两个独立问题](generated/real_bbm_comparison/RC1_kick_and_SS_gate_overlap.png)','']
    for corner,d in data.items():
        for leg,q in d['RC1_charge_paths'].items():
            x=q['signed_port_charge_C'];lines.append(f"- {corner} {leg}：RC1 峰值 {q['peak_V']:.6f} V；前沿 MP_CLEAR D／C1／R1／X005 栅端电荷 {x['MP_CLEAR_D']*1e15:+.6f}/{x['C1']*1e15:+.6f}/{x['R1']*1e15:+.6f}/{x['X005_gates']*1e15:+.6f} fC。")
        for node,q in d['negative_bottom_witnesses'].items():lines.append(f"- {corner} {node.split('.')[-1].upper()} 最小 {q['min_V']*1e3:.3f} mV，发生在 {q['time_s']*1e9:.9f} ns。实际门压、参考轨和四条参考支路总电流在 JSON 的同点 witness 中保留。")
    lines+=['','RC1 峰值与该延迟腿 MP_CLEAR 关断边沿同期，随后施加到 X005 的栅端；FF 最坏 |Vgd|=1.062566 V。HD 前沿中 MP_CLEAR D 端净输出约0.436 fC，C1、X005 栅端与 R1 净吸收，支持该支路的动态耦合／电荷交换来源；不分解内禀 Cgd、沟道注入或结电流。底板负向峰出现在参考交接过程中：FF BN0 为43.186831 ns、BP0为48.196887 ns，SS 对应43.261501／48.340616 ns，均应与当时门压和电流一起看。','',
        '| 角落／阶段 | RREFP／RREFN 端口1积分 fC | CODE／VDD 理想源供能 fJ |',
        '| --- | --- | --- |']
    for corner,d in data.items():
        for name,q in d['phase_source_flows'].items():
            v=q['values'];lines.append(f"| {corner}/{name} | {v['rrefp:1']['signed_charge_C']*1e15:+.4f}/{v['rrefn:1']['signed_charge_C']*1e15:+.4f} | {v['CODE_delivered_work_J']*1e15:+.4f}/{v['VDD_delivered_work_J']*1e15:+.4f} |")
    lines+=['','RREF 端口1正值表示向参考轨供电，负值表示回流到源端。各阶段使用区间内原生点积分，确切首末点在 JSON。H/L/PRE 等内部传递与外部 CODE／VDD 供能分列，不叠加为整机功耗。此台其他位静态、比较器复位，不能由其能量评价 ADC 功耗指标。','',
        '结论：边沿前高／低参考能够建立，原高末值窗口跨阶段；真实未闭环项是 FF 核心端压、SS 后级门控次序以及参考交接扰动。CODE 上游仍理想，不采用新基线。','',
        '**下一项只建议一个单变量对照：HD 延迟腿 C0 的 MOM 并联数由1增至4。** 目的优先检验 SS 高端开启偏早能否通过实际 H 延迟修正；按当前半 VDD 次序，额外延后至少约192 ps 才能消除负间隔，电容变化带来多少延迟须实测。CODE、其他尺寸／电容及外部采样时序不变，不重新对齐内部边沿；同时观察复位、输入负载、高参考建立和端压。该对照不会自动修好 RC1 过压，此处仅提出建议，未生成或执行新候选。','',
        '## 证据','',
        '回执逐文件大小／SHA、冻结输入、原生 PASS／PSF_END、完整时间及无损表散列均核对。原始 JSON 与冻结分析器未修改。`comparison.json` 同时保存原窗口结果和新增物理分期，`terminal_pairs.csv` 保存每角738项端压。三张图使用原生时间，无内部对齐。','']
    for corner,d in data.items():lines.append(f"- `{d['run']}`：{d['native_points']} 点，{d['receipt_bytes']} B，result SHA256 `{d['result_sha256']}`；告警：{', '.join(d['warnings'])}。")
    (HERE/'real_bbm_findings.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze(corners):
    OUT.mkdir(exist_ok=True);waves={};data={};rows=[]
    for corner in corners:
        waves[corner]=load(corner);summary,q=analyze_case(waves[corner],corner);data[corner]=summary;rows.extend(q)
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,
        frozen_high_window_metric_not_overwritten=True,physical_high_end_before_CODE_fall_s=47.995e-9),indent=2)+'\n')
    figures(waves,data);report(data)
    print('FULL_BBM_PHYSICAL_PHASE_READY',corners,'terminal records',len(rows),'projected native columns',{c:d['selected_columns'] for c,d in waves.items()})
    for corner,d in data.items():print(corner,'high establishment',d['command_stable_high'],'groups',{n:(x['strict_exceed'],x['records']) for n,x in d['groups'].items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--corners',nargs='+',choices=list(HASHES),default=['ffcold']);args=parser.parse_args();analyze(args.corners)
