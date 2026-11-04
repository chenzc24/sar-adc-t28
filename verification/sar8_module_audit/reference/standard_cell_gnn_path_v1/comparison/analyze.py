"""Paired collected SS: original IO3 and unchanged-final-stage IO1."""
import csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
import numpy as np
import yaml
OWN=Path(__file__).resolve().parent;GNN=OWN.parent;REF=GNN.parent;ROOT=REF.parents[2]


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(OWN/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')


def load(label):
    one=label=='IO1';name='sar8audit-ref-gnn-io1-sscold-v1' if one else 'sar8audit-ref-bbm-stdcell-sscold-v1'
    pkg=(GNN/'candidate' if one else REF/'standard_cell_bbm_v1')/'sscold'
    proposal='7f75ed0953931628d7fdb2c0d72d34c5f510c8c551114e8abae0c583eef4fa88' if one else 'f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4'
    managed='e42eefcc60054ad08228cd02fc809d40fff746d2e2f52fc22540c74a5e4d4b0c' if one else '24f9e00fd4bd98704a43a6e3f5f367e7ea44810209313d366a8bae9417b9b770'
    assert sha(pkg/'recipe_proposal.json')==proposal
    for q in read(pkg/'recipe_proposal.json')['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    reg=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text(encoding='utf-8'))
    assert reg['managed'] and reg['recipe']['run_id']==name and reg['recipe_hash']==managed
    for q in reg['recipe']['files']:
        p=ROOT/q['source'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=read(folder/'collection_receipt.json')
    assert len(receipt['files'])==11 and not receipt['skipped'] and receipt['total_bytes']==(24264511 if one else 22126021)
    assert sum(q['bytes'] for q in receipt['files'])==receipt['total_bytes']<=32*1024*1024 and receipt['status']['registered']['recipe_hash']==managed
    for q in receipt['files']:
        p=folder/q['name'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    cfg=read(pkg/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert r['native_PSF_END'] and r['analysis_complete'] and r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(636 if one else 652)
    assert r['measurement_sha256']==sha(pkg/'measurement.json') and r['acceptance_pass'] is None
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert (r['native_points'],len(e['columns']))==((10464,421) if one else (10956,372))
    cat=cfg['terminal_current_catalog'];wanted={'time'}|set(cfg['diagnostic_voltage_columns'])
    wanted.update(b.lower() for b,x in cat.items() if x['instance'].startswith(('XDUT.GNN','XDUT.X025.XLIB.','XDUT.XCDAC.XSN0.','XDUT.XCDAC.XSP0.')))
    wanted.update(b.lower() for node in ['XDUT.PRE','XDUT.XCDAC.BN0','XDUT.XCDAC.BP0'] for b in cfg['kcl_terms'][node])
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
    assert len(pairs)==(714 if label=='IO1' else 738) and not any(q['strict'] for q in pairs.values())
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


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False})
    styles={'IO3':'--','IO1':'-'};colors={'N':'#176fa6','P':'#b76530'}
    fig,axes=plt.subplots(3,2,figsize=(11.5,7.8),layout='constrained')
    for j,(a,b,high,title) in enumerate([(42.98,44.1,True,'CODE rise / select high'),(47.98,49.5,False,'CODE fall / select low')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b)
            for color,node,ref,name in [('#176fa6','XDUT.GNN0','VREFN','N low Vgs'),('#b76530','XDUT.GNP0','VREFP','N high Vsg')]:
                y=v(d,node)-v(d,ref)
                if name.endswith('Vsg'):y=-y
                axes[0,j].plot(t[q],y[q],styles[label],color=color,lw=1.2,label=label+' '+name)
            for side in ['N','P']:
                stem='XDUT.XCDAC.XS'+side+'0.';metric=np.minimum(np.maximum(cur(d,stem+'MP_HIGH',3),0),np.maximum(-cur(d,stem+'MN_LOW',3),0))
                axes[1,j].plot(t[q],metric[q]*1e6,styles[label],color=colors[side],lw=1.3,label=label+' '+side+' source exchange')
                target='VREFP' if (side=='N')==high else 'VREFN'
                axes[2,j].plot(t[q],(v(d,'XDUT.XCDAC.B'+side+'0')-v(d,target))[q]*1e3,styles[label],color=colors[side],lw=1.2,label=label+' B'+side+'0')
        for i,ylabel in enumerate(['N-side actual control (V)','Source-port metric (uA)','Bottom - new target (mV)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylabel);ax.grid(alpha=.15);ax.ticklabel_format(useOffset=False,axis='x');ax.legend(fontsize=7,ncol=2,loc='best')
        axes[0,j].set_title(title);axes[1,j].set_yscale('symlog',linthresh=.01);axes[2,j].set_yscale('symlog',linthresh=1)
        axes[1,j].set_ylim(0,13 if j==0 else .055)
        axes[1,j].set_yticks([0,.01,.1,1,10] if j==0 else [0,.01,.03,.05])
        axes[1,j].set_yticklabels(['0','0.01','0.1','1','10'] if j==0 else ['0','0.01','0.03','0.05'])
        axes[2,j].axhspan(-1,1,color='#75a57c',alpha=.15);axes[2,j].set_xlabel('Native time (ns)')
    fig.suptitle('SS IO3 to IO1: loaded gate timing and reference-port exchange',fontsize=12.5)
    fig.supxlabel(textwrap.fill('SS / VDD 0.81 V / -40 C; VREFP 0.9 V, VREFN 0 V. Dashed IO3, solid IO1; same real loads/Rgate and source timing. Source-port metric includes displacement; no channel-overlap claim. Comparator reset, other bits static; ideal CODE/rails/clock; no noise/mismatch/PEX. No time alignment.',150),fontsize=7.5)
    fig.savefig(OWN/'SS_gate_source_settling_comparison.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10.8,5.5),layout='constrained')
    for j,(a,b,title) in enumerate([(43.0,43.65,'Low reference turns off'),(48.2,48.8,'Low reference turns on')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b)
            for i,n in enumerate(['XDUT.PRE','XDUT.GNNDRV']):axes[i,j].plot(t[q],v(d,n)[q],styles[label],lw=1.3,color='#176fa6' if label=='IO1' else '#888',label=label)
        for i,ylab in enumerate(['PRE, native X025 output (V)','GNNDRV, final IO output (V)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylab);ax.axhspan(0,.81,color='#78a27f',alpha=.08);ax.axhline(.81,ls=':',lw=.8,color='#888')
            ax.grid(alpha=.15);ax.legend(fontsize=8,loc='best');ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(title);axes[1,j].set_xlabel('Native time (ns)');axes[1,j].set_ylim(-.32,1.15)
    fig.suptitle('SS kickback: X025 and the retained final IO devices',fontsize=12.5)
    fig.supxlabel(textwrap.fill('Same SS fixture and absolute time. Green region: 0..0.81 V supply rails, not device stress limits. Actual core0.99 V / IO1.98 V terminal-pair screens retained; all selected pairs below their limits in this SS case. No supply-ramp startup or FF qualification.',140),fontsize=7.5)
    fig.savefig(OWN/'SS_PRE_final_IO_kickback.png',dpi=165);plt.close(fig)


def main():
    waves={name:load(name) for name in ['IO3','IO1']}
    assert waves['IO3']['body']==waves['IO1']['body']
    assert waves['IO3']['r']['native_effective_settings']==waves['IO1']['r']['native_effective_settings']
    data={name:summarize(d,name) for name,d in waves.items()}
    specs={name:{p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']} for name,d in waves.items()}
    common={k for k,x in specs['IO3'].items() if k in specs['IO1'] and x==specs['IO1'][k]}
    remapped=set(specs['IO3'])&set(specs['IO1'])-common;deleted=set(specs['IO3'])-set(specs['IO1'])
    assert (len(common),len(remapped),len(deleted))==(708,6,24)
    rows=[]
    for k in sorted(common):rows.append(dict(pair=k,model=specs['IO3'][k]['model'],nodes=specs['IO3'][k]['nodes'],screen_V=specs['IO3'][k]['screen_v'],
        IO3_peak_V=data['IO3']['actual_pairs'][k]['abs_peak_V'],IO1_peak_V=data['IO1']['actual_pairs'][k]['abs_peak_V'],
        IO3_strict=data['IO3']['actual_pairs'][k]['strict'],IO1_strict=data['IO1']['actual_pairs'][k]['strict']))
    save('comparison.json',dict(source_runs=data,exact_same_model_node_limit_pair_count=708,rewired_gate_pairs=sorted(remapped),removed_A_B_pairs=sorted(deleted),acceptance_pass=None))
    with (OWN/'same_actual_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves)
    print('SS_IO1_PAIRED',len(rows),{n:{p:round(q['total_L_to_GNN_s']*1e12,6) for p,q in d['path'].items()} for n,d in data.items()})
    for n,d in data.items():
        print(n,'PRE',d['PRE_extrema'],'DRV',d['GNNDRV_extrema'],'energy fJ',{k:v*1e15 for k,v in d['stage_direct_VDD_energy_J'].items()},'VDD fJ',d['external_VDD_energy_J']*1e15)
        print('settling', {phase:{node:x['remained_inside_from_native_s']*1e9 for node,x in q['nodes'].items()} for phase,q in d['settling'].items()})


if __name__=='__main__':main()
