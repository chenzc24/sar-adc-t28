"""Completed real-interface pair: priority and native total-port attribution."""
import csv,gzip,hashlib,json,os,re
import numpy as np
from compare_io_cell import HERE,ROOT,digest,error_bounds
from compare_io_astage import load_ABC

OUT=HERE/'generated/real_pre_comparison'
CASES={'ffcold':('c9909243ed203316d852a034eb18d5552a4a631aa925158124f1377f5e4c969f',7253880,9237),
       'sscold':('0809de01ca6223f739f43ecc47f84111b0eb74ad6777968445763ffe109f7a42',7162427,8848)}


def load_real(corner):
    name='sar8audit-refcell-realpre-'+corner;folder=ROOT/'output/managed_execution/runs'/name/'collected';expected,size,count=CASES[corner]
    receipt=json.loads((folder/'collection_receipt.json').read_text());assert receipt['status']['registered']['recipe_hash']==expected and not receipt['skipped'] and len(receipt['files'])==11
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    assert receipt['total_bytes']==sum(x['bytes'] for x in receipt['files'])==size
    cfgpath=HERE/'generated/real_pre_v1'/corner/'measurement.json';cfg=json.loads(cfgpath.read_text());recipe=json.loads((cfgpath.parent/'recipe_proposal.json').read_text())
    for x in recipe['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    r=json.loads((folder/'derived/result.json').read_text());assert r['analysis_complete'] and r['acceptance_pass'] is None and r['measurement_sha256']==digest(cfgpath)
    state=json.loads((folder/'simulation.state.json').read_text());assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');data=gzip.decompress((folder/'derived'/e['file']).read_bytes());assert hashlib.sha256(data).hexdigest()==e['uncompressed_sha256']
    w=np.frombuffer(data,dtype='<f8').reshape(-1,len(e['columns']));assert w.shape==(count,152) and w[0,0]==0 and w[-1,0]==52e-9
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(e['columns'])},result_sha256=digest(folder/'derived/result.json'))


def leading(d,node,input_node,branches,window,devices):
    w,c=d['w'],d['c'];t=w[:,0];ids=np.flatnonzero((t>=window[0])&(t<=window[1]));error=w[:,c[node]]-w[:,c['vdd!']]
    peak=int(ids[np.argmax(error[ids])]);prior=ids[(ids<=peak)&(error[ids]<=0)];start=int(prior[-1]) if len(prior) else int(ids[0])
    selected=np.arange(start,peak+1);terms={name:sum(w[:,c[n]] for n in names) for name,names in branches.items()};residual=sum(terms.values())
    return dict(node=node,input_node=input_node,start_native_s=float(t[start]),start_error_V=float(error[start]),peak_native_s=float(t[peak]),peak_error_V=float(error[peak]),
        incident_currents_positive_into_components=True,
        leading_charge_C={n:float(np.trapezoid(y[selected],t[selected])) for n,y in terms.items()},
        peak_incident_A={n:float(y[peak]) for n,y in terms.items()},peak_input_V=float(w[peak,c[input_node]]),peak_output_V=float(w[peak,c[node]]),
        peak_DGSB_A={device:{str(pin):float(w[peak,c[device+':'+str(pin)]]) for pin in [1,2,3,4]} for device in devices},
        max_lobe_KCL_A=float(np.max(np.abs(residual[selected]))),charge_sum_C=float(np.trapezoid(residual[selected],t[selected])),
        interpretation='Signed total terminal currents establish local flow direction; no intrinsic Cgd/channel/diode fraction is identified.')


def recovery_audit(d):
    w,c=d['w'],d['c'];t=w[:,0];answer={};rail=d['result']['supply_V']
    for name,node,inp,input_high,output_high,devices in [
        ('X025','xdut.pre','l0',True,False,['xdut.x025.mn','xdut.x025.mp']),
        ('GPP_A','xdut.gppa','l0',True,False,['xdut.gppan','xdut.gppap']),
        ('GPP_B','xdut.gppb','xdut.gppa',False,True,['xdut.gppbn','xdut.gppbp']),
        ('GPP_C','xdut.gppdrv','xdut.gppb',True,False,['xdut.gppcn','xdut.gppcp'])]:
        interval=(t>=47.99e-9)&(t<=48.5e-9);ids=np.flatnonzero(interval);late=np.flatnonzero((t>=49.5e-9)&(t<=50.5e-9))
        def sustained(signal,target,threshold):
            bad=ids[np.abs(w[ids,c[signal]]-target)>threshold]
            first=None if len(bad) and bad[-1]==ids[-1] else int(bad[-1]+1) if len(bad) else int(ids[0])
            return dict(threshold_V=threshold,last_outside_s=None if not len(bad) else float(t[bad[-1]]),
                remained_inside_from_native_s=None if first is None else float(t[first]),
                diagnostic_only=True)
        error=w[:,c[node]]-(rail if output_high else 0.)
        answer[name]=dict(input_reached_final_within1percent=sustained(inp,rail if input_high else 0.,rail*.01),
            output_reached_final_within1mV=sustained(node,rail if output_high else 0.,.001),
            late_interval_s=[49.5e-9,50.5e-9],late_output_max_abs_error_V=float(np.max(np.abs(error[late]))),
            late_D_port_max_abs_A={dev:float(np.max(np.abs(w[late,c[dev+':1']]))) for dev in devices},
            scope='Post48ns command; native final-level persistence tested through48.5ns; late total-port window after load settling. Not channel-only or operating-region evidence.')
    return answer


def tail_current(d,node,branches):
    w,c=d['w'],d['c'];t=w[:,0];ids=np.flatnonzero((t>=48.02e-9)&(t<=48.2e-9));point=int(np.argmin(np.abs(t-48.04e-9)))
    y={name:sum(w[:,c[n]] for n in ns) for name,ns in branches.items()};residual=sum(y.values())
    return dict(interval_s=[float(t[ids[0]]),float(t[ids[-1]])],
        signed_charge_C={name:float(np.trapezoid(value[ids],t[ids])) for name,value in y.items()},
        native_48_04_witness=dict(time_s=float(t[point]),output_V=float(w[point,c[node]]),currents_A={name:float(value[point]) for name,value in y.items()}),
        max_KCL_A=float(np.max(np.abs(residual[ids]))),
        note='Post-input-edge total-port evidence; negative load current returns charge to driver output. Does not identify channel region or current fraction.')


def analyze():
    OUT.mkdir(exist_ok=True);data={};waves={};rows=[]
    for corner in ['ffcold','sscold']:
        d=load_real(corner);waves[corner]=d;r,cfg,w,c=d['result'],d['cfg'],d['w'],d['c'];m=r['cell_measurements'];groups={};local=[]
        for p in cfg['selected_mos_pair_screens']:
            key=p['instance']+':'+p['terminal'];x=r['selected_mos_pair_extrema'][key];value=max(abs(x['min']),abs(x['max']))
            group='X025' if '.X025.' in p['instance'] else ('GPP' if re.fullmatch(r'XDUT.GPP[ABC][NP]',p['instance']) else ('GNN_ABC' if re.fullmatch(r'XDUT.GNN[ABC][NP]',p['instance']) else 'physical_load'))
            row=dict(corner=corner,group=group,pair=key,model=p['model'],screen_V=p['screen_v'],abs_peak_V=value,excess_V=value-p['screen_v']);rows.append(row);local.append(row)
        for g in ['X025','GPP','GNN_ABC','physical_load']:
            q=[x for x in local if x['group']==g];worst=max(q,key=lambda x:x['excess_V'])
            groups[g]=dict(pair_records=len(q),strict_exceed_pairs=sum(x['excess_V']>0 for x in q),exceed_more_than1mV_pairs=sum(x['excess_V']>.001 for x in q),
                worst_pair=worst['pair'],worst_abs_peak_V=worst['abs_peak_V'],worst_excess_mV=worst['excess_V']*1e3)
        lobes={
            'X025_PRE':leading(d,'xdut.pre','l0',{'MN_D':['xdut.x025.mn:1'],'MP_D':['xdut.x025.mp:1'],'A_gate_load':['xdut.gnnan:2','xdut.gnnap:2']},
                (47.99e-9,48.015e-9),['xdut.x025.mn','xdut.x025.mp']),
            'GPP_C':leading(d,'xdut.gppdrv','xdut.gppb',{'MN_D':['xdut.gppcn:1'],'MP_D':['xdut.gppcp:1'],'Rgate_load':['xdut.rgpp0:1']},
                (47.995e-9,48.03e-9),['xdut.gppcn','xdut.gppcp'])}
        data[corner]=dict(run=d['run'],source_result_sha256=d['result_sha256'],native_points=r['native_points'],groups=groups,leading_lobes=lobes,
            stage_timing=m['actual_stage_timing'],same_side_control_gaps=m['actual_same_side_control_gaps'],
            post_edge_recovery_audit=recovery_audit(d),
            post_edge_load_feedback={
                'X025_PRE':tail_current(d,'xdut.pre',{'MN_D':['xdut.x025.mn:1'],'MP_D':['xdut.x025.mp:1'],'A_gates':['xdut.gnnan:2','xdut.gnnap:2']}),
                'GPP_C':tail_current(d,'xdut.gppdrv',{'MN_D':['xdut.gppcn:1'],'MP_D':['xdut.gppcp:1'],'Rgate':['xdut.rgpp0:1']})},
            opposed_total_reference_port_current=m['opposed_reference_terminal_current'],correct_ON_settling=m['correct_ON_settling'],
            actual_rail_excursions=m['supply_rail_excursions'],direct_VDD_stage_energy_J=m['restored_stage_direct_VDD_energy_J'],
            source_and_internal_work=m['source_and_internal_work'],input_loads=m['real_PRE_and_L0_loads'],
            body_forward_records=[x for x in m['body_forward_polarity'] if '.X025.' in x['pair'] or re.match(r'XDUT.GPP[ABC][NP]:',x['pair'])],
            off_gap={n:error_bounds(w,c,n,ref,46.995e-9,47.995e-9) for n,ref in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]},
            native_warning_codes=r['native_warning_codes'])
    with (OUT/'all498_pairs_by_corner.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(source_runs=data,acceptance_pass=None,ABC_regression_claim=False,physical_interface_was_previously_ideal=True,
        one_candidate_suggestion='Only replace bit0 GPP driver implementation (three identical core inverters) with one already native-validated IO inverter, same L0 inversion/Rgate/load/commands. Keep X025/ABC unchanged. This removes the dominant core GPP path without cascading three slow IO stages; remains a hypothesis, not a generated or qualified design.',
        limits='L0 still ideal; X025 FF residual remains unresolved by the proposed GPP-only change. No full digital-chain acceptance or new candidate package.')
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');figures(waves)
    print(json.dumps({n:{'groups':d['groups'],'lobes':d['leading_lobes']} for n,d in data.items()},indent=2))


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'));import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(4,2,figsize=(12,9),layout='constrained')
    for j,corner in enumerate(['ffcold','sscold']):
        d=waves[corner];old=load_ABC(corner);w,c=d['w'],d['c'];t=w[:,0]*1e9;window=(47.99,48.035 if j==0 else 48.055);s=(t>=window[0])&(t<=window[1]);rail=.99 if j==0 else .81
        for i,node in enumerate(['xdut.pre','xdut.gppa','xdut.gppb','xdut.gppdrv']):
            ax=axes[i,j];ax.plot(t[s],w[s,c[node]],lw=1.5,color='#236b9c',label='Restored physical path')
            if i in [0,3]:
                ow,oc=old['w'],old['c'];ot=ow[:,0]*1e9;ss=(ot>=window[0])&(ot<=window[1]);ax.plot(ot[ss],ow[ss,oc['pre' if i==0 else 'gppdrv']],color='#888',ls='--',lw=1.2,label='Previous ideal boundary')
            ax.axhline(0,color='#aaa',ls=':',lw=.7);ax.axhline(rail,color='#aaa',ls=':',lw=.7);ax.axvline(48,color='#aaa',ls=':',lw=.7)
            ax.set(xlim=window,ylim=(-.08,1.1 if j==0 else 1.02),ylabel=['PRE / X025 (V)','GPP A (V)','GPP B (V)','GPP C output (V)'][i]);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(['FF /0.99V /-40C','SS /0.81V /-40C'][j]);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(loc='lower left',fontsize=8);fig.suptitle('Restoring core X025/GPP exposes excursions hidden by ideal outputs',fontsize=13)
    fig.supxlabel('Unchanged ABC IO, physical CDAC/reference/Bootstrap; ideal L0 and external rails; comparator reset; no noise/mismatch/PEX\nGray:previous ideal PRE/GPPDRV only.0/VDD lines are rails, not qualification. No time alignment.',fontsize=8)
    fig.savefig(OUT/'real_PRE_GPP_cold_edges.png',dpi=170);plt.close(fig)
    d=waves['ffcold'];w,c=d['w'],d['c'];metrics=json.loads((OUT/'comparison.json').read_text())['source_runs']['ffcold']['leading_lobes']
    fig,axes=plt.subplots(3,2,figsize=(12,7),layout='constrained')
    for j,(name,node,inp,terms) in enumerate([
        ('X025_PRE','xdut.pre','l0',{'MN D':'xdut.x025.mn:1','MP D':'xdut.x025.mp:1','A gates':None}),
        ('GPP_C','xdut.gppdrv','xdut.gppb',{'MN D':'xdut.gppcn:1','MP D':'xdut.gppcp:1','Rgate':'xdut.rgpp0:1'})]):
        q=metrics[name];start=q['start_native_s']*1e9-.001;stop=q['peak_native_s']*1e9+.0005;t=w[:,0]*1e9;s=(t>=start)&(t<=stop)
        axes[0,j].plot(t[s],w[s,c[inp]],color='#258578',lw=1.4);axes[0,j].set_ylabel('Driver input (V)')
        axes[1,j].plot(t[s],(w[s,c[node]]-.99)*1e3,color='#236b9c',lw=1.5);axes[1,j].axhline(0,color='#888',lw=.8);axes[1,j].set_ylabel('Output - VDD (mV)')
        for (label,branch),color in zip(terms.items(),['#236b9c','#ce6432','#258578']):
            current=w[:,c[branch]] if branch else w[:,c['xdut.gnnan:2']]+w[:,c['xdut.gnnap:2']]
            axes[2,j].plot(t[s],current[s]*1e6,color=color,lw=1.2,label=label)
        axes[2,j].axhline(0,color='#888',lw=.8);axes[2,j].set_ylabel('Incident total current (uA)');axes[2,j].set_xlabel('Native time (ns)');axes[2,j].legend(fontsize=8)
        for ax in axes[:,j]:ax.set_xlim(start,stop);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(['Core X025 / PRE leading lobe','Core GPP C leading lobe'][j])
    fig.suptitle('FF: edge-local terminal-current redistribution at PRE and GPP C',fontsize=13)
    fig.supxlabel('Same real-load fixture, FF0.99V/-40C | signed current positive into each element; leading-lobe native samples\nPort-current balance shows flow direction, not intrinsic Cgd/channel/diode decomposition.',fontsize=8)
    fig.savefig(OUT/'FF_real_PRE_GPP_current_cause.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(4,2,figsize=(12,9),layout='constrained');colors={'ffcold':'#236b9c','sscold':'#ce6432'}
    for j,(node,load_branches,pull,downstream) in enumerate([
        ('xdut.pre',['xdut.gnnan:2','xdut.gnnap:2'],'xdut.x025.mn:1','xdut.gnna'),
        ('xdut.gppdrv',['xdut.rgpp0:1'],'xdut.gppcn:1','xdut.gpp0')]):
        for corner,d in waves.items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;s=(t>=48.02)&(t<=48.25);load=sum(w[:,c[b]] for b in load_branches)
            for i,y in enumerate([w[:,c[node]]*1e3,load*1e6,w[:,c[pull]]*1e6,w[:,c[downstream]]]):
                axes[i,j].plot(t[s],y[s],color=colors[corner],lw=1.4,label='FF0.99V' if corner=='ffcold' else 'SS0.81V')
        for i,label in enumerate(['Output low-level residual (mV)','Load port current (uA)','NMOS drain total current (uA)',
                                 'A output (V)' if j==0 else 'GPP0 reference gate (V)']):
            ax=axes[i,j];ax.set(xlim=(48.02,48.25),ylabel=label);ax.axhline(0,color='#888',lw=.7);ax.grid(alpha=.18);ax.ticklabel_format(useOffset=False,axis='x')
        axes[0,j].axhline(1,color='#258578',ls='--',lw=.8);axes[0,j].set_title(['X025 PRE: feedback from switching A','GPP C: feedback through Rgate/load'][j]);axes[-1,j].set_xlabel('Native time (ns)')
    axes[0,0].legend(fontsize=9);fig.suptitle('A post-edge tail exists: changing loads return charge while the driver sinks it',fontsize=13)
    fig.supxlabel('Same physical-load fixture; L0 source edge ends48.005ns, GPP B is within1% by~48.019ns\nTotal D/port currents include displacement; this is not a channel-only or triode-region diagnosis.',fontsize=8)
    fig.savefig(OUT/'post_edge_load_feedback.png',dpi=170);plt.close(fig)


if __name__=='__main__':analyze()
