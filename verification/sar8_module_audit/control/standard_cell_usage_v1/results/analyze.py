"""Local verified native-current review; never connects or edits frozen inputs."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import struct
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
USAGE=HERE.parent
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
sys.path.insert(0,str(USAGE))
from review_standard_cell_full_result import receipt_files
from review_standard_cell_storage_v2 import record
from evidence import edges


def dump(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def boundary(t,at):
    i=int(np.searchsorted(t,at))
    if i<len(t) and t[i]==at:return [float(t[i]),float(t[i])]
    if i==0 or i==len(t):raise ValueError('Integral boundary not bracketed')
    return [float(t[i-1]),float(t[i])]


def integrate(t,values,start,stop):
    grid=np.r_[start,t[(t>start)&(t<stop)],stop]
    samples=np.interp(grid,t,values)
    return float(np.trapezoid(samples,grid))


def load(case):
    run='sar8audit-ctrl-usage-'+case+'-gzip-v1'
    folder=ROOT/'output/managed_execution/runs'/run/'collected'
    rec=record(run);source=record('sar8audit-ctrl-usage-'+case+'-ff-v1')
    receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==rec['recipe_hash']
    state=json.loads(files['analysis.state.json'].read_bytes())
    assert state['status']=='complete' and state['exit_code']==0
    result=json.loads(files['derived/result.json'].read_bytes())
    assert result['analysis_kind']=='analysis_only_completed_source_streaming_gzip'
    assert result['source_recipe_hash']==source['recipe_hash']==rec['recipe']['source']['recipe_hash']
    assert result['simulation_started'] is False and result['source_raw_unchanged'] is True
    assert result['native_PSF_END'] and not result['missing_required_signals']
    for name,want in result['original_native_logs'].items():
        blob=files['derived/'+name].read_bytes()
        assert len(blob)==want['bytes'] and hashlib.sha256(blob).hexdigest()==want['sha256']
    cfg=json.loads((USAGE/case/'measurement.json').read_bytes())
    names=json.loads(files['derived/peak.columns.json'].read_bytes())['names']
    h=hashlib.sha256();size=0;rows=[];pack=struct.Struct('<'+'d'*len(names))
    # Retain only required plotting/charge columns, streaming the full decoded SHA.
    wanted=['time','vdd!','xdut.u19_ck','xdut.u19_d','xdut.xu19.rn','xdut.u19_q']
    wanted += ['xdut.xu19.xff.'+n for n in ['clkb','clkbb','mq','mq_x','net176','net184']]
    wanted += ['xdut.xu19.xff.mm'+str(m)+':'+str(j) for m in [64,65,66] for j in range(1,5)]
    terms=sorted({n for ts in cfg['kcl_terms'].values() for n in ts})
    wanted += [n for n in terms if n not in wanted]
    wanted += ['kcl:'+n.lower() for n in cfg['critical_kcl_nodes']]
    indices=[names.index(n) for n in wanted]
    with gzip.open(files['derived/peak.native.bin.gz'],'rb') as f:
        while True:
            blob=f.read(pack.size)
            if not blob:break
            assert len(blob)==pack.size
            h.update(blob);size+=len(blob);r=pack.unpack(blob);rows.append([r[i] for i in indices])
    assert dict(bytes=size,sha256=h.hexdigest())==result['returned_waveform']['uncompressed']
    a=np.asarray(rows);idx={n:i for i,n in enumerate(wanted)};t=a[:,0]
    assert len(t)==result['native_points']==result['diagnostic_points'] and np.isfinite(a).all()
    assert t[0]==0 and abs(t[-1]-20e-9)<1e-22 and np.all(np.diff(t)>0)
    for node,terms in cfg['kcl_terms'].items():
        total=np.zeros(len(t))
        for term in terms:total+=a[:,idx[term]]
        assert np.array_equal(total,a[:,idx['kcl:'+node.lower()]])
    proof=dict(run_id=run,managed_recipe_sha256=rec['recipe_hash'],source_run_id=source['recipe']['run_id'],
        source_recipe_sha256=source['recipe_hash'],raw_sha256=result['raw_sha256'],
        collection_receipt_sha256=hashlib.sha256((folder/'collection_receipt.json').read_bytes()).hexdigest(),
        all_collected_bytes_verified=True,decoded_bytes=size,decoded_sha256=h.hexdigest(),native_points=len(t),
        all_six_KCL_columns_exactly_recomputed=True,source_native_logs_verified=True)
    return cfg,result,a,idx,proof


def review(case):
    cfg,r,a,idx,proof=load(case);t=a[:,0]
    get=lambda n:a[:,idx[n]]
    prefix='xdut.xu19.xff.'
    vds=get(prefix+'mq_x')-get(prefix+'net176');k=int(np.argmax(abs(vds)))
    stat=r['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS']
    assert float(abs(vds[k]))==stat['max_abs_v'] and float(t[k])==stat['max_abs_time_s']
    columns={f'MM{m}_{role}':prefix+'mm'+str(m)+':'+str(j) for m in [64,65,66] for j,role in enumerate('DGSB',1)}
    snapshots=[]
    for label,at in [('MM64_peak',float(t[k])),('settled_front',5.06e-9),('middle_hold',5.5e-9),('late_hold',5.95e-9),('next_clock',6e-9)]:
        j=int(np.argmin(abs(t-at)))
        snapshots.append(dict(label=label,requested_time_s=at,actual_native_time_s=float(t[j]),
            nodes_v={n:float(get(prefix+n)[j]) for n in ['mq_x','net176','net184','clkbb','clkb','mq']},
            MM64_VDS_v=float(vds[j]),currents_a={n:float(get(p)[j]) for n,p in columns.items()}))
    charges=[]
    intervals=[('phase'+str(p['index']),p['start_s'],p['stop_s'],'original_command_phase') for p in cfg['storage']['DFF_phases']]
    intervals += [('fall_front',5e-9,5.06e-9,'diagnostic_subwindow'),('quiet_hold',5.06e-9,5.95e-9,'diagnostic_subwindow'),
                  ('hold_tail',5.95e-9,6e-9,'diagnostic_subwindow'),('next_rise',6e-9,6.05e-9,'diagnostic_subwindow')]
    for label,start,stop,kind in intervals:
        item=dict(label=label,kind=kind,start_s=start,stop_s=stop,start_native_bracket_s=boundary(t,start),stop_native_bracket_s=boundary(t,stop),
            charge_C={n:integrate(t,get(p),start,stop) for n,p in columns.items()},
            KCL_residual_charge_C={n:integrate(t,get('kcl:'+n.lower()),start,stop) for n in cfg['critical_kcl_nodes']})
        charges.append(item)
    half_edges={}
    for n in ['xdut.u19_ck',prefix+'clkbb',prefix+'mq']:
        v=get(n);hits=[]
        for j in np.flatnonzero((t>=4.98e-9)&(t<=5.06e-9)):
            if j and v[j-1]>.495>=v[j]:hits.append(float(t[j-1]+(.495-v[j-1])*(t[j]-t[j-1])/(v[j]-v[j-1])))
        assert len(hits)==1;half_edges[n]=hits[0]
    front=(t>=5e-9)&(t<=5.06e-9);fi=np.flatnonzero(front)
    peaks={}
    for name,path in columns.items():
        v=get(path);lo=fi[int(np.argmin(v[front]))];hi=fi[int(np.argmax(v[front]))]
        peaks[name]=dict(min_a=float(v[lo]),min_time_s=float(t[lo]),max_a=float(v[hi]),max_time_s=float(t[hi]))
    old=json.loads((OWN/'standard_cell_storage_v2/results/ff/summary.json').read_bytes())['MM64_focus']
    # Original all-context peak values are independently frozen in the joint export.
    reference=json.loads((OWN/'standard_cell_mm64_joint_v1/case_reference.json').read_bytes())
    reproduction=dict(original_peak_v=reference['pair_statistics']['XDUT.XU19.XFF.MM64_VDS']['max_abs_v'],original_peak_time_s=reference['MM64_VDS_peak_time_s'])
    reproduction.update(peak_difference_v=float(vds[k])-reproduction['original_peak_v'],peak_time_difference_s=float(t[k])-reproduction['original_peak_time_s'])
    reproduction['proposed_peak_time_reproduction_pass']=abs(reproduction['peak_difference_v'])<=.001 and abs(reproduction['peak_time_difference_s'])<=10e-12
    out=dict(case=case,proof=proof,reproduction=reproduction,MM64_peak=stat,snapshots=snapshots,front_current_extrema=peaks,
        fall_halfrail_times_s=half_edges,phase_charge_integrals=charges,KCL_native_extrema=r['node_kcl'],
        storage_observations=r['storage_observations'],physical_terminal_screen_pass=r['physical_terminal_screen_pass'],
        integral_policy='Trapezoid over every original native point; exact phase boundaries linearly bracketed. Signed current positive into device; charge is total terminal exchange, not intrinsic channel/Cgd decomposition.',
        current_decomposition=None,region=None,whole_ADC_qualified=None)
    out['actual_internal_edges']={node:edges(a,idx[node],.99) for node in ['xdut.u19_ck',prefix+'clkb',prefix+'clkbb',prefix+'mq']}
    dest=HERE/case;dest.mkdir(exist_ok=True)
    dump(dest/'current_analysis.json',out)
    with (dest/'phase_charges.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['label','kind','start_ns','stop_ns']+[n+'_fC' for n in columns]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for item in charges:w.writerow(dict(label=item['label'],kind=item['kind'],start_ns=item['start_s']*1e9,stop_ns=item['stop_s']*1e9,**{n+'_fC':q*1e15 for n,q in item['charge_C'].items()}))
    plot(dest,a,idx)
    print(case,'NATIVE_CURRENT_REVIEW_COMPLETE',len(t),json.dumps(reproduction,sort_keys=True))


def plot(dest,a,idx):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    p='xdut.xu19.xff.';t=a[:,0]*1e9
    fig,axes=plt.subplots(6,2,figsize=(13,13.5),sharex='col',layout='constrained')
    for column,(left,right) in enumerate([(4.995,5.06),(5.985,6.05)]):
        mask=(t>=left)&(t<=right);ts=t[mask]
        for name,label in [('xdut.u19_ck','CK'),(p+'clkbb','G64 = clkbb'),(p+'mq','G65 = mq')]:axes[0,column].plot(ts,a[mask,idx[name]],label=label)
        for name,label in [('net176','net176 = S64 / D65'),('net184','net184 = S65 / D66')]:axes[1,column].plot(ts,a[mask,idx[p+name]]*1e3,label=label)
        vds=a[mask,idx[p+'mq_x']]-a[mask,idx[p+'net176']]
        axes[2,column].plot(ts,vds,color='#c7433b',label='MM64 VDS');axes[2,column].axhline(.99,color='#555555',ls='--',lw=1,label='0.99 V screen')
        for row,m in enumerate([64,65,66],3):
            for port,role in enumerate('DGSB',1):axes[row,column].plot(ts,a[mask,idx[p+'mm'+str(m)+':'+str(port)]]*1e6,label=role)
        for row,unit in enumerate(['Gate (V)','Node (mV)','VDS (V)','MM64 I (uA)','MM65 I (uA)','MM66 I (uA)']):
            axes[row,column].set_ylabel(unit);axes[row,column].grid(alpha=.18);axes[row,column].set_xlim(left,right)
            if row!=2:axes[row,column].axhline(0,color='#888888',lw=.6)
            axes[row,column].legend(loc='best',ncol=2,fontsize=8,framealpha=.8)
        axes[0,column].set_title('5 ns: clock fall and undershoot' if column==0 else '6 ns: next clock and recovery')
        axes[-1,column].set_xlabel('Original time (ns)')
    fig.suptitle('Native DFF baseline: terminal currents at the two clock events',fontsize=14)
    fig.supxlabel('FF | 0.99 V | -40 C | native DFCNQD1 + original first-hop load | ideal supply/commands | no noise, mismatch or PEX\nTotal terminal currents: positive into device; intrinsic current split and region unavailable',fontsize=9)
    fig.savefig(dest/'event_currents.png',dpi=170);plt.close(fig)


if __name__=='__main__':review(sys.argv[1] if len(sys.argv)>1 else 'baseline')
