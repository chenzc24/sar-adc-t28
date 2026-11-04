"""Source-bound SS actual switch-port evidence; no new simulation/on-off model."""
import csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
import numpy as np
import yaml
OWN=Path(__file__).resolve().parent;REF=OWN.parent;ROOT=REF.parents[2]
sys.path.append(str(REF))
from build_first_fixture import definitions
from prepare_standard_cell_bbm import expanded
RUN='sar8audit-ref-bbm-stdcell-sscold-v1'
MANAGED='24f9e00fd4bd98704a43a6e3f5f367e7ea44810209313d366a8bae9417b9b770'
PROPOSAL='f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4'
RESULT='c61c9a71f01e9485c455ec26e0424cfbd2847fae9e10d2d1618cdebb9be8615e'


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d):(OWN/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')


def load():
    pkg=REF/'standard_cell_bbm_v1';case=pkg/'sscold'
    assert sha(case/'recipe_proposal.json')==PROPOSAL
    for q in read(case/'recipe_proposal.json')['inputs']:assert sha(ROOT/q['source'])==q['sha256']
    reg=yaml.safe_load((ROOT/'management/runs'/(RUN+'.yaml')).read_text(encoding='utf-8'))
    assert reg['managed'] and reg['recipe_hash']==MANAGED and reg['recipe']['run_id']==RUN
    for q in reg['recipe']['files']:
        p=ROOT/q['source'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    folder=ROOT/'output/managed_execution/runs'/RUN/'collected';receipt=read(folder/'collection_receipt.json')
    assert len(receipt['files'])==11 and not receipt['skipped'] and receipt['total_bytes']==22126021
    assert sum(q['bytes'] for q in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    assert receipt['status']['registered']['recipe_hash']==MANAGED
    for q in receipt['files']:
        p=folder/q['name'];assert (p.stat().st_size,sha(p))==(q['bytes'],q['sha256'])
    assert sha(folder/'derived/result.json')==RESULT
    cfg=read(case/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['native_PSF_END'] and r['analysis_complete'] and r['acceptance_pass'] is None
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==652
    assert r['measurement_sha256']==sha(case/'measurement.json') and r['supply_V']==.81
    flat,library=expanded(definitions((pkg/'dut.scs').read_text()),read(pkg/'library_metadata.json'))
    switches={}
    for side,gates in [('N',['GNN0','GNP0']),('P',['GPN0','GPP0'])]:
        for kind,gate in zip(['MN_LOW','MP_HIGH'],gates):
            name='XDUT.XCDAC.XS'+side+'0.'+kind;part=flat[name]
            nodes=['XDUT.XCDAC.B'+side+'0','XDUT.'+gate,'VREFN' if kind=='MN_LOW' else 'VREFP','0' if kind=='MN_LOW' else 'VDD!']
            assert part['nodes']==nodes and part['model']==('nch_18_mac' if kind=='MN_LOW' else 'pch_18_mac')
            for j,node in enumerate(nodes,1):
                cat=cfg['terminal_current_catalog'][name+':'+str(j)]
                assert (cat['instance'],cat['port'],cat['node'],cat['model'])==(name,j,node,part['model'])
            switches[name]=dict(model=part['model'],declared_DGSB=nodes,project_parameter_sha256=hashlib.sha256(part['parameters'].encode()).hexdigest())
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==372 and e['rows']==10956
    wanted={'time','code','vdd!','vrefn','vrefp','rrefn:1','rrefp:1','xdut.h0','xdut.l0','xdut.topn','xdut.topp'}
    for name,x in switches.items():
        wanted.update(n.lower() for n in x['declared_DGSB'] if n!='0')
        wanted.update(name.lower()+':'+str(j) for j in [1,2,3,4])
    for n in ['XDUT.XCDAC.BN0','XDUT.XCDAC.BP0']:wanted.update(b.lower() for b in cfg['kcl_terms'][n])
    assert wanted<=set(e['columns'])
    ids=[i for i,n in enumerate(e['columns']) if n in wanted];cols=[e['columns'][i] for i in ids]
    w=np.empty((10956,len(ids)),dtype='<f8');stride=8*372;h=hashlib.sha256();count=total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            raw=f.read(stride*128)
            if not raw:break
            assert len(raw)%stride==0;h.update(raw);total+=len(raw)
            block=np.frombuffer(raw,dtype='<f8').reshape(-1,372);w[count:count+len(block)]=block[:,ids];count+=len(block)
    assert count==10956 and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(cfg=cfg,r=r,w=w,c={n:i for i,n in enumerate(cols)},switches=switches,
        source=dict(run=RUN,managed_recipe_sha256=MANAGED,proposal_sha256=PROPOSAL,result_sha256=RESULT,
            input_files=len(reg['recipe']['files']),collected_files=11,collected_bytes=22126021,native_points=10956,
            native_stream_uncompressed_sha256=e['uncompressed_sha256'],measurement_sha256=sha(case/'measurement.json'),
            dut_sha256=sha(pkg/'dut.scs'),original_report=(pkg/'comparison/report.md').relative_to(ROOT).as_posix(),
            no_new_run_or_remote_analysis=True))


def v(d,n):return np.zeros(len(d['w'])) if n=='0' else d['w'][:,d['c'][n.lower()]]
def current(d,n,port):return d['w'][:,d['c'][n.lower()+':'+str(port)]]


def integral(t,y,a,b):
    q=(t>a)&(t<b);x=np.r_[a,t[q],b];z=np.r_[np.interp(a,t,y),y[q],np.interp(b,t,y)]
    return float(np.trapezoid(z,x))


def device_snapshot(d,n,i):
    x=d['switches'][n];vv={p:float(v(d,node)[i]) for p,node in zip('DGSB',x['declared_DGSB'])}
    ii={p:float(current(d,n,j)[i]) for j,p in enumerate('DGSB',1)}
    return dict(instance=n,model=x['model'],native_time_s=float(d['w'][i,0]),DGSB_V=vv,DGSB_current_A=ii,
        declared_Vgs_V=vv['G']-vv['S'],declared_Vsg_V=vv['S']-vv['G'],Vgd_V=vv['G']-vv['D'],Vds_V=vv['D']-vv['S'],Vbs_V=vv['B']-vv['S'],
        total_terminal_KCL_A=sum(ii.values()),intrinsic_channel_current_A=None,channel_on_off='unknown')


def witness(d,side,i):
    nn='XDUT.XCDAC.XS'+side+'0.MN_LOW';pp='XDUT.XCDAC.XS'+side+'0.MP_HIGH'
    mn=device_snapshot(d,nn,i);mp=device_snapshot(d,pp,i)
    bot='XDUT.XCDAC.B'+side+'0';branches=d['cfg']['kcl_terms'][bot]
    actual={b:float(d['w'][i,d['c'][b.lower()]]) for b in branches}
    ds=mn['DGSB_current_A'];ps=mp['DGSB_current_A']
    return dict(native_time_s=float(d['w'][i,0]),bottom_V=float(v(d,bot)[i]),VREFN_V=float(v(d,'VREFN')[i]),VREFP_V=float(v(d,'VREFP')[i]),
        low=mn,high=mp,bottom_actual_incident_current_A=actual,bottom_KCL_A=sum(actual.values()),
        low_D_current_A=ds['D'],low_reference_source_out_A=-ds['S'],low_gate_out_A=-ds['G'],low_body_out_A=-ds['B'],
        low_source_out_over_D_ratio=None if ds['D']==0 else -ds['S']/ds['D'],
        reference_port_exchange_forward_A=min(max(ps['S'],0.),max(-ds['S'],0.)),
        interpretation='Signed total actual port partition. Source-out/D ratio is not a channel-current fraction; no Vth/conduction model inferred.')


def analyze(d):
    t=d['w'][:,0];sides={};rows=[]
    phases=[('select_high',42.995e-9,47.995e-9),('select_low',47.995e-9,52e-9)]
    for side in ['N','P']:
        n='XDUT.XCDAC.XS'+side+'0.MN_LOW';p='XDUT.XCDAC.XS'+side+'0.MP_HIGH'
        dn,dp=current(d,n,1),current(d,p,1);sn,sp=current(d,n,3),current(d,p,3)
        drain=np.where(dn*dp<0,np.minimum(abs(dn),abs(dp)),0.)
        source=np.minimum(np.maximum(sp,0),np.maximum(-sn,0))
        at=int(np.argmax(drain));old=d['r']['cell_measurements']['opposed_total_reference_terminal_current'][side]
        assert float(t[at])==old['time_s'] and float(drain[at])==old['peak_min_opposed_abs_A']
        entry=dict(existing_opposed_D_peak=witness(d,side,at),phase_metrics={})
        for phase,a,b in phases:
            q=np.flatnonzero((t>=a)&(t<(b) if phase=='select_high' else t<=b))
            j=int(q[np.argmax(source[q])]);k=int(q[np.argmax(drain[q])])
            entry['phase_metrics'][phase]=dict(interval_s=[a,b],source_exchange_peak_A=float(source[j]),source_exchange_peak=witness(d,side,j),
                opposed_D_peak_A=float(drain[k]),opposed_D_peak=witness(d,side,k),
                integrated_source_exchange_C=integral(t,source,a,b),integrated_opposed_D_diagnostic_C=integral(t,drain,a,b),
                exact_channel_overlap_duration_s=None,exact_channel_deadtime_s=None,
                positive_source_exchange_is_not_a_channel_conduction_classifier=True)
        for name in [n,p]:
            part=d['switches'][name];g,s=v(d,part['declared_DGSB'][1]),v(d,part['declared_DGSB'][2])
            for phase,a,b in phases:
                q=(t>=a)&(t<b if phase=='select_high' else t<=b);bias=g-s if name==n else s-g
                currents=[current(d,name,j) for j in [1,2,3,4]]
                rows.append(dict(instance=name,model=part['model'],phase=phase,control_bias='Vgs' if name==n else 'Vsg',
                    bias_min_V=float(np.min(bias[q])),bias_max_V=float(np.max(bias[q])),
                    source_current_min_A=float(np.min(currents[2][q])),source_current_max_A=float(np.max(currents[2][q])),
                    gate_current_abs_max_A=float(np.max(abs(currents[1][q]))),body_current_abs_max_A=float(np.max(abs(currents[3][q]))),
                    total_terminal_KCL_max_A=float(np.max(abs(sum(currents))[q])),channel_overlap_qualified='unknown'))
        sides[side]=entry
    bottom_kcl={}
    for node in ['XDUT.XCDAC.BN0','XDUT.XCDAC.BP0']:
        branches=d['cfg']['kcl_terms'][node];residual=sum(d['w'][:,d['c'][b.lower()]] for b in branches)
        bottom_kcl[node]=dict(actual_ports=branches,max_abs_A=float(np.max(abs(residual))))
    m=d['r']['cell_measurements']
    result=dict(source=d['source'],scope='Four active bit0 reference switches, original standard-cell SS cold fixture; other28 reference devices held static; no full ADC or new candidate',
        switches=d['switches'],side_evidence=sides,bottom_KCL=bottom_kcl,reused_halfVDD_events=m['actual_control_events'],
        reused_command_reference_settling=m['physical_command_phase_reference_settling'],
        warnings=d['r']['native_warning_codes'],effective_settings=d['r']['native_effective_settings'],
        missing_external_DGSB_ports=[],missing_internal_observables=['Verified macro internal primitive conduction current without displacement','Dynamic operating-point/channel-state information under actual Vgs,Vds,Vbs and SS cold model'],
        exact_channel_nonoverlap_qualified=None,fixed_Vth_assumed=False,acceptance_pass=None)
    save('evidence.json',result)
    with (OWN/'actual_switch_bias_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
        out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
    plot(d)
    print('SS_ACTUAL_SWITCH_EVIDENCE_READY',len(d['w']),'rows',len(rows),'KCL',bottom_kcl)
    for side,x in sides.items():
        print(side,'opposed_D_peak',x['existing_opposed_D_peak']['native_time_s']*1e9,
            'biases',x['existing_opposed_D_peak']['low']['declared_Vgs_V'],x['existing_opposed_D_peak']['high']['declared_Vsg_V'],
            'low D/source uA',x['existing_opposed_D_peak']['low_D_current_A']*1e6,x['existing_opposed_D_peak']['low_reference_source_out_A']*1e6,
            'phase source peaks uA',{k:z['source_exchange_peak_A']*1e6 for k,z in x['phase_metrics'].items()})


def plot(d):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False})
    colors={'N':'#176fa6','P':'#bd6730'};t=d['w'][:,0]*1e9
    fig,axes=plt.subplots(3,2,figsize=(11.5,7.8),layout='constrained')
    for j,(a,b,high,title) in enumerate([(42.98,44.1,True,'Select high: CODE rise'),(47.98,49.5,False,'Select low: CODE fall')]):
        q=(t>=a)&(t<=b)
        for side in ['N','P']:
            n='XDUT.XCDAC.XS'+side+'0.MN_LOW';p='XDUT.XCDAC.XS'+side+'0.MP_HIGH'
            npart,ppart=d['switches'][n],d['switches'][p]
            ng=v(d,npart['declared_DGSB'][1])-v(d,npart['declared_DGSB'][2])
            pg=v(d,ppart['declared_DGSB'][2])-v(d,ppart['declared_DGSB'][1])
            axes[0,j].plot(t[q],ng[q],color=colors[side],lw=1.2,label=side+' low NMOS Vgs')
            axes[0,j].plot(t[q],pg[q],color=colors[side],lw=1.1,ls='--',label=side+' high PMOS Vsg')
            dn,dp=current(d,n,1),current(d,p,1);sn,sp=current(d,n,3),current(d,p,3)
            drain=np.where(dn*dp<0,np.minimum(abs(dn),abs(dp)),0.)
            source=np.minimum(np.maximum(sp,0),np.maximum(-sn,0))
            axes[1,j].plot(t[q],source[q]*1e6,color=colors[side],lw=1.4,label=side+' source exchange')
            axes[1,j].plot(t[q],drain[q]*1e6,color=colors[side],ls='--',lw=1,label=side+' opposed D')
            node='XDUT.XCDAC.B'+side+'0';target='VREFP' if (side=='N')==high else 'VREFN'
            axes[2,j].plot(t[q],(v(d,node)-v(d,target))[q]*1e3,color=colors[side],lw=1.2,label='B'+side+'0 - '+target)
        for i,ylab in enumerate(['Actual control bias (V)','Total-port diagnostic (uA)','Bottom - new target (mV)']):
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=ylab);ax.grid(alpha=.16);ax.ticklabel_format(useOffset=False,axis='x')
            ax.legend(fontsize=7,ncol=1 if i==1 else 2,loc='upper right' if i==1 else 'best')
        axes[0,j].set_title(title);axes[2,j].set_xlabel('Native time (ns)')
        axes[2,j].set_yscale('symlog',linthresh=1);axes[2,j].axhspan(-1,1,color='#73a681',alpha=.15)
    fig.suptitle('SS: real switch biases and reference-port exchange',fontsize=12.5)
    fig.supxlabel(textwrap.fill('SS / VDD 0.81 V / -40 C; VREFP 0.9 V, VREFN 0 V. Original native standard-cell bit0 fixture; complete physical load, ideal CODE/rails/clock, comparator reset, other bits static. All D/G/S/B currents include displacement. No fixed Vth or channel on/off threshold; bottom green band is +/-1 mV diagnostic.',145),fontsize=7.5)
    fig.savefig(OWN/'actual_switch_bias_current_settling.png',dpi=165);plt.close(fig)


if __name__=='__main__':analyze(load())
