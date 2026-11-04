"""Verified collected FF interface comparison; local native data only."""
import ast,csv,gzip,hashlib,json,os,re,sys,textwrap
from pathlib import Path
import numpy as np
import yaml
OUT=Path(__file__).resolve().parent;OPT=OUT.parent;BASE=OPT.parent;REF=BASE.parent;ROOT=REF.parents[2]


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(OUT/name).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')


def load(label):
    guard=label=='Guard'
    name='sar8audit-ref-hd-io-guard-ff-v1' if guard else 'sar8audit-ref-rc1-hd-x005-d1p25-ff-v1'
    pkg=(OPT/'candidate' if guard else BASE)/'ffcold'
    assert sha(pkg/'recipe_proposal.json')==('563a395e239d663a2299ba5a31189cf3039ebf2a548bdfed21d28f2a80926685' if guard else '5f416251a1f26ec288b2c980dbdd05c965fc56e6a6ca3659a1fdb788d29f5b3a')
    for q in read(pkg/'recipe_proposal.json')['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    reg=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text(encoding='utf-8'))
    assert reg['managed'] and reg['recipe']['run_id']==name
    expected='f4e063a683dcc65de7630b8f139f1a1c9d61a1c32e0fc10543924de7f1ce52d0' if guard else '24306072b56f9a60a0d2e73fa0619d797094ce81a7829cbb6c61b3d4c0e1a81d'
    assert reg['recipe_hash']==expected
    for q in reg['recipe']['files']:
        p=ROOT/q['source'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    folder=ROOT/'output/managed_execution/runs'/name/'collected';receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11 and receipt['total_bytes']==(28479798 if guard else 27718889)
    assert sum(q['bytes'] for q in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    assert receipt['status']['registered']['recipe_hash']==expected
    for q in receipt['files']:
        p=folder/q['name'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    cfg=read(pkg/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(666 if guard else 662)
    assert r['measurement_sha256']==sha(pkg/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==(463 if guard else 453)
    cat=cfg['terminal_current_catalog']
    affected_VDD=[b.lower() for b,x in cat.items() if x['node']=='VDD!' and
        (x['instance']=='XDUT.XBBM0.XD_HD.MP_CLEAR' or x['instance'].startswith('XDUT.XBBM0.XD_HD.X005.') or x['instance']=='XDUT.XBBM0.XD_HD.R_GUP1')]
    nand_VDD=[b.lower() for b,x in cat.items() if x['node']=='VDD!' and x['instance'].startswith('XDUT.XBBM0.X002.X000.XLIB.')]
    incident=[b.lower() for b,x in cat.items() if x['node'] in ['XDUT.XBBM0.HD','XDUT.XBBM0.XD_HD.RC1','XDUT.XBBM0.XD_HD.HD_RAW','XDUT.XBBM0.XD_HD.B','XDUT.XBBM0.X002.N']]
    wanted={'time','vvdd:1','vcode:1'}|set(cfg['diagnostic_voltage_columns'])|set(affected_VDD+nand_VDD+incident)
    assert wanted<=set(e['columns'])
    indices=[j for j,n in enumerate(e['columns']) if n in wanted];columns=[e['columns'][j] for j in indices]
    wave=np.empty((r['native_points'],len(indices)),dtype='<f8');stride=8*len(e['columns']);h=hashlib.sha256();count=total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            raw=f.read(stride*128)
            if not raw:break
            assert len(raw)%stride==0;h.update(raw);total+=len(raw)
            block=np.frombuffer(raw,dtype='<f8').reshape(-1,len(e['columns']))
            wave[count:count+len(block)]=block[:,indices];count+=len(block)
    assert count==(11373 if guard else 11422) and count==len(wave) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert wave[0,0]==0 and wave[-1,0]==52e-9 and np.all(np.diff(wave[:,0])>0)
    return dict(run=name,cfg=cfg,result=r,w=wave,c={n:j for j,n in enumerate(columns)},affected_VDD=affected_VDD,nand_VDD=nand_VDD,
        result_sha256=sha(folder/'derived/result.json'),managed_sha256=expected,receipt_bytes=receipt['total_bytes'],
        fixture_body='\n'.join(l for l in (pkg/'test.scs').read_text().splitlines() if not l.startswith('save ')))


def voltage(d,n):return 0. if n.lower()=='0' else d['w'][:,d['c'][n.lower()]]
def pair_wave(d,p):return voltage(d,p['nodes'][0])-voltage(d,p['nodes'][1])


def clipped_integral(t,y,a,b):
    assert t[0]<=a<b<=t[-1]
    inside=(t>a)&(t<b);tx=np.r_[a,t[inside],b];yy=np.r_[np.interp(a,t,y),y[inside],np.interp(b,t,y)]
    return float(np.trapezoid(yy,tx))


def snapshot(d,p):
    values=pair_wave(d,p);i=int(np.argmax(abs(values)));nodes=p['nodes'];w,c=d['w'],d['c']
    wanted={nodes[0],nodes[1],'XDUT.XBBM0.XD_HD.B','XDUT.XBBM0.XD_HD.RC0','XDUT.XBBM0.XD_HD.RC1','XDUT.XBBM0.HD','XDUT.XBBM0.X002.N','CODE'}
    incidence={}
    for n in ['XDUT.XBBM0.XD_HD.B','XDUT.XBBM0.X002.N']:
        branches=[b.lower() for b,x in d['cfg']['terminal_current_catalog'].items() if x['node']==n]
        assert set(branches)<=set(c)
        incidence[n]=dict(actual_port_current_A={b:float(w[i,c[b]]) for b in branches},
            KCL_A=float(sum(w[i,c[b]] for b in branches)))
    leading=None
    n=nodes[0]
    if n in incidence and w[i,c[n.lower()]]<0:
        previous=np.flatnonzero((np.arange(len(w))<=i)&(voltage(d,n)>=0))
        if len(previous):
            start=int(previous[-1]);branches=list(incidence[n]['actual_port_current_A'])
            charges={b:clipped_integral(w[:,0],w[:,c[b]],float(w[start,0]),float(w[i,0])) for b in branches}
            leading=dict(node=n,start_last_nonnegative_native_s=float(w[start,0]),peak_s=float(w[i,0]),
                start_V=float(w[start,c[n.lower()]]),peak_V=float(w[i,c[n.lower()]]),actual_port_charge_C=charges,KCL_charge_sum_C=sum(charges.values()))
    return dict(time_s=float(w[i,0]),signed_value_V=float(values[i]),abs_value_V=float(abs(values[i])),
        actual_pair=p,concurrent_V={n:0. if n=='0' else float(w[i,c[n.lower()]]) for n in sorted(wanted)},actual_node_incidence=incidence,
        negative_excursion_leading=leading)


def summarize(d,label):
    r=d['result'];m=r['cell_measurements'];cfg=d['cfg'];w,c=d['w'],d['c'];t=w[:,0]
    specs={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']};rows=[]
    for key,p in specs.items():
        v=pair_wave(d,p);x=r['selected_mos_pair_extrema'][key]
        assert (float(np.min(v)),float(np.max(v)))==(x['min'],x['max'])
        peak=max(abs(x['min']),abs(x['max']));duration=m['all_terminal_native_phase_time']['phases']['full']['pairs'][key]['absolute_above_limit_duration_s']
        rows.append(dict(variant=label,pair=key,model=p['model'],nodes=p['nodes'],screen_V=p['screen_v'],abs_peak_V=peak,
            strict=peak>p['screen_v'],above_limit_s=duration))
    assert len(rows)==(738 if label=='Guard' else 750)
    strict=sum(q['strict'] for q in rows)
    assert strict==m['all_terminal_native_phase_time']['phases']['full']['strict_native_pair_count']
    critical={}
    for key in ['XDUT.XBBM0.XD_HD.X002.XLIB.MM0:ds','XDUT.XBBM0.X002.X000.XLIB.MM2:ds','XDUT.XBBM0.X002.X000.XLIB.MM4:ds','XDUT.XBBM0.X004.X000.XLIB.MM4:gb']:
        critical[key]=snapshot(d,specs[key]);critical[key]['above_limit_s']=next(q['above_limit_s'] for q in rows if q['pair']==key)
    groups={}
    for name,prefix in [('receiver','XDUT.XBBM0.XD_HD.X005.'),('clear','XDUT.XBBM0.XD_HD.MP_CLEAR:')]:
        q=[x for x in rows if x['pair'].startswith(prefix)];peak=max(q,key=lambda x:x['abs_peak_V'])
        groups[name]=dict(pair_count=len(q),strict=sum(x['strict'] for x in q),worst=peak,peak_snapshot=snapshot(d,specs[peak['pair']]))
    power={}
    supply=voltage(d,'VDD!')
    signals={'interface':supply*sum(w[:,c[b]] for b in d['affected_VDD']),
        'NAND':supply*sum(w[:,c[b]] for b in d['nand_VDD']),
        'whole_fixture':-supply*w[:,c['vvdd:1']]}
    for p in cfg['static_windows']:
        a,b=p['start_s'],p['stop_s'];q={k+'_power_W':clipped_integral(t,v,a,b)/(b-a) for k,v in signals.items()}
        q.update(interval_s=[a,b],actual_interface_VDD_ports=d['affected_VDD'],actual_NAND_VDD_ports=d['nand_VDD'])
        mask=(t>=a)&(t<=b)
        q['levels_V']={n:[float(np.min(voltage(d,n)[mask])),float(np.max(voltage(d,n)[mask]))] for n in ['XDUT.XBBM0.HD','XDUT.XBBM0.X002.N','XDUT.H0','XDUT.L0']}
        if label=='Guard':
            native=m['interface_measurements']['static_windows'][p['name']]
            for k,x in [('interface','HD_interface_VDD_mean_power_W'),('NAND','native_NAND_VDD_mean_power_W'),('whole_fixture','total_VDD_mean_power_W')]:assert abs(q[k+'_power_W']-native[x])<1e-14
        power[p['name']]=q
    boundary={}
    for n,ref in [('XDUT.XCDAC.BN0','VREFP'),('XDUT.XCDAC.BP0','VREFN')]:
        errors=voltage(d,n)-voltage(d,ref);indices=np.flatnonzero((t>=47.995e-9)&(abs(errors)>.001))
        boundary[n]=dict(first_native_outside_old_1mV_after_next_CODE_s=None if not len(indices) else float(t[indices[0]]),
            old_target_error_at_that_sample_V=None if not len(indices) else float(errors[indices[0]]))
    return dict(run=d['run'],result_sha256=d['result_sha256'],managed_sha256=d['managed_sha256'],native_points=len(w),receipt_bytes=d['receipt_bytes'],
        actual_pair_count=len(rows),strict_actual_pairs=strict,groups=groups,critical=critical,static=power,
        RC1_extrema=r['voltage_and_current_extrema']['xdut.xbbm0.xd_hd.rc1'],HD_extrema=r['voltage_and_current_extrema']['xdut.xbbm0.hd'],
        reset=m['delay_leg_reset_diagnostics'],original_HD_rail_reset=m.get('original_full_swing_HD_reset_contract',m['delay_leg_reset_diagnostics']['HD']['nodes'].get('xdut.xbbm0.hd')),
        physical_settling=m['physical_command_phase_reference_settling'],legacy_actual_ON=m['actual_correct_ON_settling'],
        events=m['actual_control_events'],overlap=m['sampled_HL_mutual_exclusion'],warnings=r['native_warning_codes'],
        static_plateaus=m['static_plateaus'],next_command_boundary=boundary,
        H_L_halfVDD_events={n:r['half_vdd_events'].get(n,[]) for n in ['xdut.h0','xdut.l0']},acceptance_pass=None),rows,specs


def figures(waves,data):
    os.environ.setdefault('MPLCONFIGDIR',str(OUT/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#156f9e','#c55b35','#47935a'];styles={'D1P25':'--','Guard':'-'}
    fig,axes=plt.subplots(3,2,figsize=(12.5,8),layout='constrained')
    for j,(a,b,title) in enumerate([(42.99,43.45,'CODE rise'),(47.99,48.30,'CODE fall')]):
        for label,d in waves.items():
            t=d['w'][:,0]*1e9;q=(t>=a)&(t<=b)
            axes[0,j].plot(t[q],voltage(d,'XDUT.XBBM0.XD_HD.RC1')[q],styles[label],lw=1.3,label=label+' RC1',color=colors[0] if label=='Guard' else '#777')
            axes[1,j].plot(t[q],voltage(d,'XDUT.XBBM0.HD')[q],styles[label],lw=1.3,label=label+' HD',color=colors[0] if label=='Guard' else '#777')
            if label=='Guard':axes[1,j].plot(t[q],voltage(d,'XDUT.XBBM0.XD_HD.HD_RAW')[q],lw=1,color=colors[1],label='Guard HD_RAW')
            keys=['XDUT.XBBM0.XD_HD.X002.XLIB.MM0:ds','XDUT.XBBM0.X002.X000.XLIB.MM2:ds','XDUT.XBBM0.X002.X000.XLIB.MM4:ds']
            specs={p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']}
            for k,(key,name) in enumerate(zip(keys,['upstream X002 PMOS','H NAND PMOS','H NAND MM4'])):
                axes[2,j].plot(t[q],abs(pair_wave(d,specs[key])[q]),styles[label],lw=1.05,color=colors[k],label=name if label=='Guard' else None)
        for i,name in enumerate(['RC1 (V)','Output / input (V)','Actual |Vds| (V)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=name);ax.grid(alpha=.15);ax.ticklabel_format(useOffset=False,axis='x')
            ax.axhline(.99,color='#b23f36',ls=':',lw=.8);ax.legend(fontsize=7.5,ncol=2,loc='best')
        axes[2,j].set_ylim(.965,1.035);axes[2,j].set_xlabel('Native time (ns)');axes[0,j].set_title(title)
    fig.suptitle('HD interface: guarded input, remaining core stress',fontsize=13)
    fig.supxlabel(textwrap.fill('FF / 0.99 V / -40 C; dashed D1P25, solid IO + passive guard. Same native clocks/loads/solver; no time shift. Red dotted: 0.99 V core screen (RC1 now drives IO). Ideal CODE/rails/clock; comparator reset; other bits static; no noise/mismatch/PEX.',155),fontsize=8)
    fig.savefig(OUT/'interface_phase_comparison.png',dpi=165);plt.close(fig)
    d=waves['Guard'];g=data['Guard'];t=d['w'][:,0]*1e9
    boundary=47.995;legacy=g['legacy_actual_ON']['select_high']['stop_s']*1e9
    fig,axes=plt.subplots(2,2,figsize=(12,5.8),layout='constrained',gridspec_kw={'width_ratios':[1,1.3]})
    for j,(a,b) in enumerate([(43.3,48.11),(47.985,48.11)]):
        q=(t>=a)&(t<=b)
        for k,(n,label) in enumerate([('CODE','CODE'),('XDUT.GNP0','GNP0 (high ref)'),('XDUT.GPN0','GPN0 (low ref)')]):axes[0,j].plot(t[q],voltage(d,n)[q],lw=1.1,label=label,color=['#777',colors[0],colors[1]][k])
        for k,(n,ref,label) in enumerate([('XDUT.XCDAC.BN0','VREFP','BN0 - old VREFP'),('XDUT.XCDAC.BP0','VREFN','BP0 - old VREFN')]):axes[1,j].plot(t[q],(voltage(d,n)-voltage(d,ref))[q]*1e3,lw=1.25,label=label,color=colors[k])
        for i in range(2):
            ax=axes[i,j];ax.axvspan(boundary,legacy,color='#d36d48',alpha=.12)
            ax.axvline(boundary,color='#555',ls=':',lw=.9);ax.axvline(legacy,color='#a04f35',ls='--',lw=.9)
            ax.set_xlim(a,b);ax.grid(alpha=.15);ax.legend(fontsize=8,ncol=1,loc='upper left');ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_ylabel('Control (V)');axes[1,j].set_ylabel('Old target residual (mV)');axes[1,j].set_xlabel('Native time (ns)')
        axes[1,j].axhspan(-1,1,color='#77a980',alpha=.15);axes[1,j].set_ylim(-15,35)
    axes[0,0].set_title('Established before the next command')
    axes[0,1].set_title(f'New CODE starts {boundary:.3f} ns; old window ends {legacy:.5f} ns')
    fig.suptitle('Why the inherited high-state settling flag is false',fontsize=13)
    fig.supxlabel(textwrap.fill('Same Guard FF fixture. Shaded interval: next CODE action is already inside the inherited high-state window. Green band: +/-1 mV diagnostic; residuals deliberately retain the old reference target. Independent high-command window ends at 47.995 ns. No waveform or raw flag changed.',145),fontsize=8)
    fig.savefig(OUT/'settling_window_boundary.png',dpi=165);plt.close(fig)


def main():
    waves={name:load(name) for name in ['D1P25','Guard']}
    assert waves['D1P25']['fixture_body']==waves['Guard']['fixture_body']
    assert waves['D1P25']['result']['native_effective_settings']==waves['Guard']['result']['native_effective_settings']
    data={};rows=[];specs={}
    for name,d in waves.items():data[name],r,specs[name]=summarize(d,name);rows.extend(r)
    unchanged={key for key,p in specs['D1P25'].items() if key in specs['Guard'] and p==specs['Guard'][key]}
    assert len(unchanged)==720
    indexed={name:{r['pair']:r for r in rows if r['variant']==name} for name in waves}
    changes=[]
    for key in sorted(unchanged):
        a,b=indexed['D1P25'][key],indexed['Guard'][key]
        if a['strict']!=b['strict']:changes.append(dict(pair=key,status='added' if b['strict'] else 'resolved',D1P25=a,Guard=b))
    delta=dict(unchanged_physical_pairs=720,unchanged_pair_strict={name:sum(indexed[name][k]['strict'] for k in unchanged) for name in waves},
        actual_model_or_members_changed_pairs={name:len(specs[name])-720 for name in waves},status_changes=changes,
        interpretation='Only matching actual instance/model/node/screen tuples compared. Old 738 equivalent groups are not this new 738 physical-pair inventory.')
    save('comparison.json',dict(source_runs=data,delta=delta,acceptance_pass=None));save('unchanged_pair_status_changes.json',delta)
    with (OUT/'actual_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves,data)
    print('GUARD_ACTUAL_COMPARISON_READY',len(rows),{n:(q['strict_actual_pairs'],q['actual_pair_count']) for n,q in data.items()},delta['unchanged_pair_strict'],'changes',len(changes))


if __name__=='__main__':main()
