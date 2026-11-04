"""Paired collected FF: exact source attribution, no new runs."""
import csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
import numpy as np
import yaml
OWN=Path(__file__).resolve().parent;GNN=OWN.parent;REF=GNN.parent;ROOT=REF.parents[2]


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(OWN/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')


def load(label):
    one=label=='IO1';name='sar8audit-ref-gnn-io1-ffcold-v1' if one else 'sar8audit-ref-bbm-stdcell-ffcold-v1'
    pkg=(GNN/'candidate' if one else REF/'standard_cell_bbm_v1')/'ffcold'
    proposal='f67e60b0ceab7a9205249aa46820d4abde98beba7bf6bebb95711886b2ba0bd7' if one else 'f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c'
    managed='e32ae97bcfe3022f58de068333ddeae1886752ba043e9f6df14cab3533f03e78' if one else 'a7b09f5868cf81605a7ad3ff8b2fb7696b36dca88b19ec7cd20f13a61e3e1e8b'
    assert sha(pkg/'recipe_proposal.json')==proposal
    for q in read(pkg/'recipe_proposal.json')['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    reg=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text(encoding='utf-8'))
    assert reg['managed'] and reg['recipe']['run_id']==name and reg['recipe_hash']==managed
    for q in reg['recipe']['files']:
        p=ROOT/q['source'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=read(folder/'collection_receipt.json')
    assert len(receipt['files'])==11 and not receipt['skipped'] and receipt['total_bytes']==(24662257 if one else 21843637)
    assert sum(q['bytes'] for q in receipt['files'])==receipt['total_bytes']<=32*1024*1024 and receipt['status']['registered']['recipe_hash']==managed
    for q in receipt['files']:
        p=folder/q['name'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    cfg=read(pkg/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert r['native_PSF_END'] and r['analysis_complete'] and r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(636 if one else 652)
    assert r['measurement_sha256']==sha(pkg/'measurement.json') and r['acceptance_pass'] is None
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert (r['native_points'],len(e['columns']))==((10889,421) if one else (11316,372))
    cat=cfg['terminal_current_catalog'];wanted={'time'}|set(cfg['diagnostic_voltage_columns'])
    wanted.update(b.lower() for b,x in cat.items() if x['instance'].startswith(('XDUT.GNN','XDUT.X025.XLIB.','XDUT.XCDAC.XSN0.','XDUT.XCDAC.XSP0.')))
    wanted.update(b.lower() for b,x in cat.items() if x['instance'].startswith('XDUT.XBBM0.X004.X001.XLIB.'))
    wanted.update(b.lower() for node in ['XDUT.PRE','XDUT.L0','XDUT.GNNDRV','XDUT.XBBM0.X004.N','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0'] for b in cfg['kcl_terms'][node])
    assert wanted<=set(e['columns'])
    ids=[j for j,n in enumerate(e['columns']) if n in wanted];cols=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');stride=8*len(e['columns']);count=total=0;h=hashlib.sha256()
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            raw=f.read(stride*128)
            if not raw:break
            assert len(raw)%stride==0;h.update(raw);total+=len(raw)
            q=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']));w[count:count+len(q)]=q[:,ids];count+=len(q)
    assert count==len(w) and h.hexdigest()==e['uncompressed_sha256'] and total==e['uncompressed_bytes']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(cfg=cfg,r=r,w=w,c={n:j for j,n in enumerate(cols)},run=name,result_sha256=sha(folder/'derived/result.json'),
        managed_sha256=managed,receipt_bytes=receipt['total_bytes'],
        body='\n'.join(l for l in (pkg/'test.scs').read_text().splitlines() if not l.startswith('save ')))


def v(d,n):return np.zeros(len(d['w'])) if n=='0' else d['w'][:,d['c'][n.lower()]]
def cur(d,n,j):return d['w'][:,d['c'][n.lower()+':'+str(j)]]
def integral(t,y,a,b):
    q=(t>a)&(t<b);x=np.r_[a,t[q],b];z=np.r_[np.interp(a,t,y),y[q],np.interp(b,t,y)]
    return float(np.trapezoid(z,x))


def summarize(d,label):
    r,m,cfg=d['r'],d['r']['cell_measurements'],d['cfg'];t=d['w'][:,0];c=d['c']
    path=['xdut.l0','xdut.pre']+([] if label=='IO1' else ['xdut.gnna','xdut.gnnb'])+['xdut.gnndrv','xdut.gnn0'];paths={}
    for name,a,b in [('off',42.995e-9,47.995e-9),('on',47.995e-9,52e-9)]:
        edges={}
        for n in path:
            q=[x for x in r['half_vdd_events'][n] if a<=x['estimated_time_s']<b];assert len(q)==1;edges[n]=q[0]
        paths[name]=dict(nodes=path,events=edges,total_L_to_GNN_s=edges[path[-1]]['estimated_time_s']-edges[path[0]]['estimated_time_s'],
            adjacent_delays_s=[edges[b]['estimated_time_s']-edges[a]['estimated_time_s'] for a,b in zip(path[:-1],path[1:])])
    sources={};switch_bias={}
    for phase,a,b in [('select_high',42.995e-9,47.995e-9),('select_low',47.995e-9,52e-9)]:
        indices=np.flatnonzero((t>=a)&(t<b if phase=='select_high' else t<=b));sources[phase]={};switch_bias[phase]={}
        for side in ['N','P']:
            stem='XDUT.XCDAC.XS'+side+'0.';sp=cur(d,stem+'MP_HIGH',3);sn=cur(d,stem+'MN_LOW',3)
            metric=np.minimum(np.maximum(sp,0),np.maximum(-sn,0));i=int(indices[np.argmax(metric[indices])])
            source=dict(peak_A=float(metric[i]),time_s=float(t[i]),native_metric_integral_C=integral(t,metric,a,b),
                low_Vgs_V=float((v(d,'XDUT.'+('GNN0' if side=='N' else 'GPN0'))-v(d,'VREFN'))[i]),
                high_Vsg_V=float((v(d,'VREFP')-v(d,'XDUT.'+('GNP0' if side=='N' else 'GPP0')))[i]),
                DGSB_current_A={dev:{p:float(cur(d,stem+dev,j)[i]) for j,p in enumerate('DGSB',1)} for dev in ['MN_LOW','MP_HIGH']})
            sources[phase][side]=source
            low_bias=v(d,'XDUT.'+('GNN0' if side=='N' else 'GPN0'))-v(d,'VREFN')
            high_bias=v(d,'VREFP')-v(d,'XDUT.'+('GNP0' if side=='N' else 'GPP0'))
            switch_bias[phase][side]=dict(low_declared_Vgs_range_V=[float(np.min(low_bias[indices])),float(np.max(low_bias[indices]))],
                high_declared_Vsg_range_V=[float(np.min(high_bias[indices])),float(np.max(high_bias[indices]))],no_Vth_classifier=True)
            if label=='IO1':
                native=m['GNN_single_IO_actual_measurements']['reference_port_phases'][phase]['source_exchange'][side]
                assert abs(source['peak_A']-native['peak_A'])<1e-18 and source['time_s']==native['peak']['time_s']
                assert abs(source['native_metric_integral_C']-native['native_metric_integral_C'])<1e-25
    specs={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']};pairs={}
    for key,p in specs.items():
        x=r['selected_mos_pair_extrema'][key];peak=max(abs(x['min']),abs(x['max']))
        pairs[key]=dict(model=p['model'],nodes=p['nodes'],screen_V=p['screen_v'],abs_peak_V=peak,strict=peak>p['screen_v'])
        if all(n=='0' or n.lower() in c for n in p['nodes']):
            wave=v(d,p['nodes'][0])-v(d,p['nodes'][1]);assert (float(np.min(wave)),float(np.max(wave)))==(x['min'],x['max'])
    assert len(pairs)==(714 if label=='IO1' else 738)
    targeted={}
    for inst in ['XDUT.GNNCN','XDUT.GNNCP','XDUT.X025.XLIB.MM1','XDUT.X025.XLIB.MM0']:
        key=max((k for k in pairs if k.startswith(inst+':')),key=lambda k:pairs[k]['abs_peak_V'])
        x=r['selected_mos_pair_extrema'][key];at=x['max_time_s'] if abs(x['max'])>=abs(x['min']) else x['min_time_s'];i=int(np.argmin(abs(t-at)))
        assert abs(t[i]-at)<1e-18
        cat=cfg['terminal_current_catalog'];nodes=[cat[inst+':'+str(j)]['node'] for j in [1,2,3,4]]
        targeted[inst]=dict(worst_pair=key,abs_peak_V=pairs[key]['abs_peak_V'],time_s=at,
            DGSB_V={p:float(v(d,n)[i]) for p,n in zip('DGSB',nodes)},DGSB_current_A={p:float(cur(d,inst,j)[i]) for j,p in enumerate('DGSB',1)})
    pre_load=[b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='XDUT.PRE' and x['port']==2]
    load=sum(d['w'][:,c[b]] for b in pre_load)
    pre=dict(actual_load_ports=pre_load,full_signed_C=integral(t,load,0.,52e-9),gate_internal_work_J=integral(t,load*v(d,'XDUT.PRE'),0.,52e-9),
        load_min_A=float(np.min(load)),load_max_A=float(np.max(load)))
    if label=='IO1':assert abs(pre['gate_internal_work_J']-m['GNN_single_IO_actual_measurements']['PRE_load_and_internal_work']['PRE_gate_load_internal_work_J'])<1e-23
    energy={}
    for stage,prefix in [('C','xdut.gnncp'),('X025','xdut.x025.xlib.mm0')]+([] if label=='IO1' else [('A','xdut.gnnap'),('B','xdut.gnnbp')]):
        energy[stage]=cfg['supply_V']*sum(r['current_charge_trapezoids'][prefix+':'+str(j)]['signed_C'] for j in [3,4])
    early=t<42.995e-9
    return dict(run=d['run'],result_sha256=d['result_sha256'],managed_sha256=d['managed_sha256'],native_points=len(t),receipt_bytes=d['receipt_bytes'],
        path=paths,source_exchange=sources,actual_switch_bias_by_phase=switch_bias,actual_pairs=pairs,targeted=targeted,PRE_load=pre,stage_direct_VDD_energy_J=energy,
        external_VDD_energy_J=m['ideal_VDD_energy_J'],external_CODE_source_net_J=m['CODE_source_and_input_load']['net_source_J'],
        PRE_extrema=r['voltage_and_current_extrema']['xdut.pre'],GNNDRV_extrema=r['voltage_and_current_extrema']['xdut.gnndrv'],
        events=m['actual_control_events'],settling=m['physical_command_phase_reference_settling'],reset=m['delay_leg_reset_diagnostics'],
        static=m['static_plateaus'],warnings=r['native_warning_codes'],settings=r['native_effective_settings'],
        startup=dict(H_L_events={n:[q for q in r['half_vdd_events'].get(n,[]) if q['estimated_time_s']<42.995e-9] for n in ['xdut.h0','xdut.l0']},
            GNN0_range_V=[float(np.min(v(d,'XDUT.GNN0')[early])),float(np.max(v(d,'XDUT.GNN0')[early]))],power_ramp_qualified=False),
        acceptance_pass=None)


def duration(t,y,limit):
    a,b=y[:-1],y[1:];dt=np.diff(t);active=(abs(a)>limit)|(abs(b)>limit)
    if not np.any(active):return 0.
    a,b,dt=a[active],b[active],dt[active];inside=np.zeros(len(a));moving=b!=a
    lo=(-limit-a[moving])/(b[moving]-a[moving]);hi=(limit-a[moving])/(b[moving]-a[moving])
    inside[moving]=np.maximum(0.,np.minimum(1.,np.maximum(lo,hi))-np.maximum(0.,np.minimum(lo,hi)))
    return float(np.sum(dt*(1-inside)))


def function_group(inst):
    if inst.startswith('XDUT.X025.'):return 'X025_PRE_core'
    if inst.startswith('XDUT.X008.'):return 'GPNPRE_core'
    if inst.startswith('XDUT.XSTD_'):return 'other_reference_core_buffers'
    if inst.startswith('XDUT.XBBM0.XD_'):
        leg='HD' if '.XD_HD.' in inst else 'LD'
        if inst.endswith(('.MN_CLEAR','.MP_CLEAR')):return leg+'_RC_clear'
        if '.X006.' in inst:return leg+'_reset_input_INV'
        if '.X002.' in inst:return leg+'_RC0_receiver'
        if '.X005.' in inst:return leg+'_RC1_receiver'
    if inst.startswith('XDUT.XBBM0.X004.'):return 'L_native_NAND_and_output_INV'
    if inst.startswith('XDUT.XBBM0.X002.'):return 'H_native_NAND_and_output_INV'
    if inst.startswith('XDUT.XBBM0.X000.'):return 'CODE_native_INV'
    if inst.startswith('XDUT.GNN'):return 'GNN_IO'
    if inst.startswith('XDUT.GPPI'):return 'GPP_IO'
    if inst.startswith('XDUT.XCDAC.'):return 'CDAC'
    if inst.startswith(('XDUT.XBOOTN.','XDUT.XBOOTP.')):return 'Bootstrap'
    if inst.startswith('XDUT.XCOMP.'):return 'comparator_reset'
    raise ValueError('Unclassified actual instance '+inst)


def node_snapshot(d,node,index):
    t=d['w'][:,0];at=float(t[index]);value=float(v(d,node)[index]);cfg=d['cfg'];c=d['c'];w=d['w']
    branches=cfg['kcl_terms'][node];assert set(b.lower() for b in branches)<=set(c)
    current={b:float(w[index,c[b.lower()]]) for b in branches}
    volts={n:float(v(d,n)[index]) for n in ['CODE','VDD!','XDUT.L0','XDUT.PRE','XDUT.GNNDRV','XDUT.GPPDRV','XDUT.XBBM0.X004.N']}
    rail=.99 if value>.99 else 0. if value<0 else None
    leading=None
    if rail is not None:
        ys=v(d,node);prior=np.flatnonzero((np.arange(len(t))<=index)&(ys<=rail if value>.99 else ys>=rail))
        if len(prior):
            first=int(prior[-1]);a=float(t[first]);charges={b:integral(t,w[:,c[b.lower()]],a,at) for b in branches}
            leading=dict(last_inside_rail_native_s=a,peak_s=at,actual_port_charge_C=charges,KCL_charge_sum_C=sum(charges.values()))
    return dict(time_s=at,node=node,voltage_V=value,concurrent_V=volts,actual_incident_port_current_A=current,
        node_KCL_A=sum(current.values()),leading_rail_excursion=leading)


def enrich(d,data):
    t=d['w'][:,0];cfg=d['cfg'];r=d['r'];specs={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']}
    groups={}
    for key,q in data['actual_pairs'].items():
        p=specs[key];x=r['selected_mos_pair_extrema'][key];q.update(min_V=x['min'],max_V=x['max'],min_time_s=x['min_time_s'],max_time_s=x['max_time_s'])
        saved=all(n=='0' or n.lower() in d['c'] for n in p['nodes']);q['native_pair_waveform_available']=saved
        q['above_limit_duration_s']=None if not saved else duration(t,v(d,p['nodes'][0])-v(d,p['nodes'][1]),p['screen_v'])
        q['function_group']=function_group(p['instance'])
        if saved and 'all_terminal_native_phase_time' in r['cell_measurements']:
            stored=r['cell_measurements']['all_terminal_native_phase_time']['phases']['full']['pairs'][key]['absolute_above_limit_duration_s']
            assert abs(q['above_limit_duration_s']-stored)<1e-21
        group=groups.setdefault(q['function_group'],dict(actual_pairs=0,strict_pairs=0,worst_pair=None,worst_abs_V=-1.))
        group['actual_pairs']+=1;group['strict_pairs']+=int(q['strict'])
        if q['abs_peak_V']>group['worst_abs_V']:group['worst_abs_V']=q['abs_peak_V'];group['worst_pair']=key
    data['groups']=groups;data['strict_actual_pairs']=sum(q['strict'] for q in data['actual_pairs'].values())
    assert data['strict_actual_pairs']==213
    data['node_events']={}
    for node in ['XDUT.L0','XDUT.PRE','XDUT.GNNDRV']:
        y=v(d,node);data['node_events'][node]={kind:node_snapshot(d,node,int(np.argmin(y) if kind=='min' else np.argmax(y))) for kind in ['min','max']}
    data['X025_pairs']={k:q for k,q in data['actual_pairs'].items() if k.startswith('XDUT.X025.')}
    data['initial_H_L_halfVDD_events']=data['startup']['H_L_events']
    data['X025_NMOS_DS_duration_by_screen_s']={str(limit):duration(t,v(d,'XDUT.PRE'),limit) for limit in [.99,.990001,.99001,.9901,.991,.995,1.]}
    data['channel_overlap_qualified']=None


def logic_reuse_evidence():
    sys.path.append(str(REF))
    from build_first_fixture import definitions,instances
    defs=definitions((GNN/'candidate/dut.scs').read_text())
    top={n:(ns,m,p) for n,ns,m,p in instances(defs['sar8_realpre_unit'])}
    bbm={n:(ns,m,p) for n,ns,m,p in instances(defs['sar8p_nonoverlap'])}
    andname=bbm['X004'][1];andr={n:(ns,m,p) for n,ns,m,p in instances(defs[andname])}
    assert top['X025'][0]==['L0','VDD','VSS','PRE'] and top['X025'][1]=='sar8p_inv'
    assert bbm['X004'][0]==['CB','LD','VDD','VSS','L']
    assert andr['X000'][0]==['A','B','VDD','VSS','N'] and andr['X001'][0]==['N','VDD','VSS','Y']
    return dict(owned_wrapper_wire='XDUT.XBBM0.X004.N',not_native_internal_stack_node=True,
        native_NAND_output_boolean='N_L=not(CB and LD)',current_L0_boolean='L0=not(N_L)',current_PRE_boolean='PRE=not(L0)=N_L',
        proposed_next_diagnostic='Use existing wrapper NAND output N_L as PRE-equivalent input to retained single GNN IO; remove redundant X025 only after explicit experiment authorization.',
        no_candidate_prepared=True,not_a_timing_or_electrical_equivalence_proof=True,
        necessary_checks=['N_L native NAND output/stack stress with added real IO input load','L0 shared GPP load and all native core pairs','Both handoffs/source-port exchange/reference settling at SS and FF'])


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False})
    styles={'IO3':'--','IO1':'-'};colors=['#176fa6','#b56332']
    fig,axes=plt.subplots(3,2,figsize=(11.5,7.8),layout='constrained')
    for j,(a,b,title) in enumerate([(43.0,43.12,'Select-high interface transition'),(48.13,48.23,'Select-low interface transition')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b);l0=v(d,'XDUT.L0');pre=v(d,'XDUT.PRE')
            for k,(y,n) in enumerate([(l0,'L0 = X025 gate'),(pre,'PRE = X025 drain')]):axes[0,j].plot(t[q],y[q],styles[label],color=colors[k],lw=1.1,label=n if label=='IO1' else None)
            for k,(y,n) in enumerate([(np.maximum(abs(l0),abs(l0-.99)),'max N/P |Vgs|'),(np.maximum(abs(pre),abs(pre-.99)),'max N/P |Vds|')]):axes[1,j].plot(t[q],y[q],styles[label],color=colors[k],lw=1.15,label=n if label=='IO1' else None)
            axes[2,j].plot(t[q],v(d,'XDUT.GNNDRV')[q],styles[label],color='#176fa6' if label=='IO1' else '#888',lw=1.2,label=label+' final IO output')
        for i,ylabel in enumerate(['Actual interface voltage (V)','X025 actual terminal envelope (V)','GNNDRV (V)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylabel);ax.grid(alpha=.15);ax.legend(fontsize=7,ncol=2,loc='best');ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(title);axes[1,j].set_ylim(.985,1.012);axes[1,j].axhline(.99,ls=':',lw=.9,color='#b44436')
        axes[2,j].set_ylim(-.33,1.39);axes[2,j].axhspan(0,.99,color='#789d7a',alpha=.08);axes[2,j].set_xlabel('Native time (ns)')
    fig.suptitle('FF: X025 stress peaks precede the larger final-IO peaks',fontsize=12.5)
    fig.supxlabel(textwrap.fill('FF / VDD 0.99 V / -40 C; dashed IO3, solid IO1. Same source timing/solver/physical load. X025 envelope is concurrent maximum over actual N/P pairs, not one invented device; red0.99 V core screen. Final IO uses1.98 V. Ideal CODE/rails/clock, comparator reset, other bits static; no noise/mismatch/PEX. No time alignment.',155),fontsize=7.5)
    fig.savefig(OWN/'FF_L0_PRE_IO_stress_timing.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(11.5,7.4),layout='constrained')
    for j,(a,b,high,title) in enumerate([(42.99,43.7,True,'CODE rise / select high'),(47.99,48.7,False,'CODE fall / select low')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b)
            for k,(y,n) in enumerate([(v(d,'XDUT.GNN0')-v(d,'VREFN'),'N low Vgs'),(v(d,'VREFP')-v(d,'XDUT.GNP0'),'N high Vsg')]):axes[0,j].plot(t[q],y[q],styles[label],lw=1.1,color=colors[k],label=label+' '+n)
            for side,k in [('N',0),('P',1)]:
                stem='XDUT.XCDAC.XS'+side+'0.';metric=np.minimum(np.maximum(cur(d,stem+'MP_HIGH',3),0),np.maximum(-cur(d,stem+'MN_LOW',3),0))
                axes[1,j].plot(t[q],metric[q]*1e6,styles[label],lw=1.2,color=colors[k],label=label+' '+side+' source')
                target='VREFP' if (side=='N')==high else 'VREFN'
                axes[2,j].plot(t[q],(v(d,'XDUT.XCDAC.B'+side+'0')-v(d,target))[q]*1e3,styles[label],lw=1.15,color=colors[k],label=label+' B'+side+'0')
        for i,ylabel in enumerate(['N-side source-referenced bias (V)','Source-port metric (uA)','Bottom - new target (mV)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylabel);ax.grid(alpha=.15);ax.legend(fontsize=7,ncol=2,loc='best');ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(title);axes[1,j].set_ylim(bottom=0);axes[2,j].set_yscale('symlog',linthresh=1);axes[2,j].axhspan(-1,1,color='#75a07b',alpha=.15);axes[2,j].set_xlabel('Native time (ns)')
    fig.suptitle('FF: loaded gates, reference-source exchange and establishment',fontsize=12.5)
    fig.supxlabel(textwrap.fill('Same FF fixture, VREFP0.9 V/VREFN0 V. All total D/G/S/B include displacement; source-port metric is not pure-channel overlap. Green band +/-1 mV diagnostic. Full command windows/initial history retained; no full ADC or power-ramp startup qualification.',150),fontsize=7.5)
    fig.savefig(OWN/'FF_gate_source_settling.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(4,2,figsize=(11.5,9.5),layout='constrained')
    for j,(a,b,title) in enumerate([(43.0,43.032,'Select high'),(48.13,48.165,'Select low')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b)
            for k,(node,name) in enumerate([('XDUT.L0','L0'),('XDUT.XBBM0.X004.N','N_L: native NAND output')]):
                axes[0,j].plot(t[q],v(d,node)[q],styles[label],color=colors[k],lw=1.1,label=name if label=='IO1' else None)
            l_driver=cur(d,'XDUT.XBBM0.X004.X001.XLIB.MM0',1)+cur(d,'XDUT.XBBM0.X004.X001.XLIB.MM1',1)
            l_load=cur(d,'XDUT.GPPIN',2)+cur(d,'XDUT.GPPIP',2)+cur(d,'XDUT.X025.XLIB.MM0',2)+cur(d,'XDUT.X025.XLIB.MM1',2)
            pre_driver=cur(d,'XDUT.X025.XLIB.MM0',1)+cur(d,'XDUT.X025.XLIB.MM1',1)
            pre_load=sum(d['w'][:,d['c'][b.lower()]] for b,x in d['cfg']['terminal_current_catalog'].items() if x['node']=='XDUT.PRE' and x['port']==2)
            for k,(y,name) in enumerate([(l_driver,'L0 inverter D ports'),(l_load,'Shared GPP + X025 gate ports')]):
                axes[1,j].plot(t[q],y[q]*1e6,styles[label],color=colors[k],lw=1.1,label=name if label=='IO1' else None)
            axes[2,j].plot(t[q],v(d,'XDUT.PRE')[q],styles[label],color=colors[0],lw=1.1,label='PRE' if label=='IO1' else None)
            axes[2,j].plot(t[q],v(d,'XDUT.GNNDRV')[q],styles[label],color=colors[1],lw=1.1,label='Final IO output' if label=='IO1' else None)
            for k,(y,name) in enumerate([(pre_driver,'X025 D ports'),(pre_load,'GNN input gate ports')]):
                axes[3,j].plot(t[q],y[q]*1e6,styles[label],color=colors[k],lw=1.1,label=name if label=='IO1' else None)
        for i,ylabel in enumerate(['L0 / N_L (V)','L0 incident port current (uA)','PRE / GNNDRV (V)','PRE incident port current (uA)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylabel);ax.grid(alpha=.15);ax.legend(fontsize=7,loc='best');ax.ticklabel_format(useOffset=False,axis='x')
            if i%2:ax.axhline(0,color='#777',lw=.6)
            else:
                ax.axhline(0,color='#777',lw=.6);ax.axhline(.99,color='#777',ls=':',lw=.6)
        axes[0,j].set_title(title);axes[3,j].set_xlabel('Native time (ns)')
    fig.suptitle('FF: upstream driver and actual shared load at each interface',fontsize=12.5)
    fig.supxlabel(textwrap.fill('FF / 0.99 V / -40 C. Dashed IO3, solid IO1; original absolute time. Current positive from node into device. Plotted sums include displacement and channel components; opposite KCL traces show exchange path, not isolated intrinsic capacitance. Actual CDAC/Bootstrap load; ideal CODE/rails/clock; comparator reset, other bits static; no noise/mismatch/PEX.',155),fontsize=7.5)
    fig.savefig(OWN/'FF_L0_PRE_branch_currents.png',dpi=165);plt.close(fig)


def main():
    waves={name:load(name) for name in ['IO3','IO1']}
    assert waves['IO3']['body']==waves['IO1']['body'] and waves['IO3']['r']['native_effective_settings']==waves['IO1']['r']['native_effective_settings']
    data={name:summarize(d,name) for name,d in waves.items()}
    for name,d in waves.items():enrich(d,data[name])
    specs={name:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for name,d in waves.items()}
    common={k for k,x in specs['IO3'].items() if k in specs['IO1'] and x==specs['IO1'][k]};remapped=set(specs['IO3'])&set(specs['IO1'])-common;deleted=set(specs['IO3'])-set(specs['IO1'])
    assert (len(common),len(remapped),len(deleted))==(708,6,24)
    changes=[];rows=[]
    for k in sorted(common):
        a,b=data['IO3']['actual_pairs'][k],data['IO1']['actual_pairs'][k]
        row=dict(pair=k,function_group=a['function_group'],model=a['model'],nodes=a['nodes'],screen_V=a['screen_V'],
            IO3_abs_peak_V=a['abs_peak_V'],IO1_abs_peak_V=b['abs_peak_V'],IO3_strict=a['strict'],IO1_strict=b['strict'],
            IO3_above_limit_s=a['above_limit_duration_s'],IO1_above_limit_s=b['above_limit_duration_s']);rows.append(row)
        if a['strict']!=b['strict']:changes.append(dict(pair=k,status='added' if b['strict'] else 'resolved',IO3=a,IO1=b))
    accounting=dict(exact_same_model_node_limit_pairs=708,exact_pair_status_changes=changes,
        unchanged_pair_failures={name:sum(data[name]['actual_pairs'][k]['strict'] for k in common) for name in waves},
        rewired_gate_pairs={k:{name:data[name]['actual_pairs'][k] for name in waves} for k in sorted(remapped)},
        deleted_A_B_pairs={k:data['IO3']['actual_pairs'][k] for k in sorted(deleted)})
    result=dict(source_runs=data,accounting=accounting,next_interface_recommendation=logic_reuse_evidence(),acceptance_pass=None)
    save('comparison.json',result);save('pair_status_accounting.json',accounting)
    with (OWN/'same_actual_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves)
    print('FF_IO1_PAIRED', {name:q['strict_actual_pairs'] for name,q in data.items()},'samepair changes',len(changes),'commonfail',accounting['unchanged_pair_failures'])
    for name,d in data.items():
        print(name,'groups',{g:(q['actual_pairs'],q['strict_pairs'],round(q['worst_abs_V'],9)) for g,q in d['groups'].items()})
        print('X025 ps',{k:round(v['above_limit_duration_s']*1e12,6) for k,v in d['X025_pairs'].items()})
        print('L0 high currents uA',{k:v*1e6 for k,v in d['node_events']['XDUT.L0']['max']['actual_incident_port_current_A'].items()})
        print('L0 leading charges fC',{k:v*1e15 for k,v in d['node_events']['XDUT.L0']['max']['leading_rail_excursion']['actual_port_charge_C'].items()})


if __name__=='__main__':main()

