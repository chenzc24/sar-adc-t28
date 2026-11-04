"""Attribute saved original SS path; no new circuit simulation."""
import gzip,hashlib,importlib.util,json,os,sys,textwrap
from pathlib import Path
import numpy as np
OWN=Path(__file__).resolve().parent;REF=OWN.parent;ROOT=REF.parents[2]
PATH=['xdut.l0','xdut.pre','xdut.gnna','xdut.gnnb','xdut.gnndrv','xdut.gnn0']


def main():
    spec=importlib.util.spec_from_file_location('verified_original_SS_ports',REF/'standard_cell_ss_nonoverlap_v1/analyze.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    verified=mod.load();r=verified['r'];cfg=verified['cfg']
    e=next(q for q in r['native_exports'] if q['file']=='cell.native.f64le.gz');cols=e['columns']
    assert set(PATH)<=set(cols)
    indices=[cols.index(n) for n in ['time','vdd!']+PATH];w=np.empty((10956,len(indices)),dtype='<f8')
    folder=ROOT/'output/managed_execution/runs'/mod.RUN/'collected/derived';stride=8*len(cols);count=0;h=hashlib.sha256()
    with gzip.open(folder/e['file'],'rb') as f:
        while True:
            raw=f.read(stride*128)
            if not raw:break
            h.update(raw);q=np.frombuffer(raw,dtype='<f8').reshape(-1,len(cols));w[count:count+len(q)]=q[:,indices];count+=len(q)
    assert count==10956 and h.hexdigest()==e['uncompressed_sha256']
    events={}
    for phase,a,b in [('turn_low_ref_off',42.995e-9,47.995e-9),('turn_low_ref_on',47.995e-9,52e-9)]:
        found={}
        for i,n in enumerate(PATH):
            edges=[x for x in r['half_vdd_events'][n] if a<=x['estimated_time_s']<b]
            assert len(edges)==1;x=edges[0];t=x['estimated_time_s']
            k=int(np.searchsorted(w[:,0],x['after_time_s']));assert abs(w[k,0]-x['after_time_s'])<1e-18
            y0=w[k-1,i+2]-.5*w[k-1,1];y1=w[k,i+2]-.5*w[k,1]
            estimate=w[k-1,0]-y0*(w[k,0]-w[k-1,0])/(y1-y0)
            assert abs(estimate-t)<1e-18
            found[n]=x
        delay=[found[v]['estimated_time_s']-found[u]['estimated_time_s'] for u,v in zip(PATH[:-1],PATH[1:])]
        total=found[PATH[-1]]['estimated_time_s']-found[PATH[0]]['estimated_time_s']
        assert abs(sum(delay)-total)<1e-21
        events[phase]=dict(actual_halfVDD_events=found,segment_names=['X025','IO_A','IO_B','IO_C','Rgate_to_real_gate'],
            segment_delays_s=delay,total_L0_to_GNN0_s=total,three_IO_sum_s=sum(delay[1:4]),
            three_IO_fraction_of_total=sum(delay[1:4])/total,Rgate_fraction_of_total=delay[4]/total,
            removed_A_B_old_delay_s=sum(delay[1:3]),not_a_transistor_on_off_boundary=True)
    old_gap=r['cell_measurements']['actual_control_events']['select_high']['N_signed_off_to_on_gap_s']
    ev=events['turn_low_ref_off'];data=dict(source=verified['source'],path=PATH,phases=events,
        old_select_high_N_halfVDD_gap_s=old_gap,
        conditional_gap_if_only_old_A_B_delay_removed_s=old_gap+ev['removed_A_B_old_delay_s'],
        prediction_warning='Bookkeeping only. Final IO input slew/drain trajectory and X025 kickback change; this is not predicted conduction safety or a frozen timing budget.',
        decision='Stage count dominates SS path; prepare only one unchanged-final-stage IO3-to-IO1 contrast.',acceptance_pass=None)
    (OWN/'baseline_attribution.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    plot(w)
    print('SS_GNN_PATH_ATTRIBUTED',[(k,[round(v*1e12,6) for v in q['segment_delays_s']]) for k,q in events.items()],
        'conditional gap ps',data['conditional_gap_if_only_old_A_B_delay_removed_s']*1e12)


def plot(w):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(6,2,figsize=(10.5,7.5),layout='constrained',sharex='col')
    for j,(a,b,title) in enumerate([(43.0,43.6,'Low reference turns off'),(48.2,48.8,'Low reference turns on')]):
        t=w[:,0]*1e9;q=(t>=a)&(t<=b)
        for i,n in enumerate(PATH):
            ax=axes[i,j];ax.plot(t[q],w[q,i+2],lw=1.3,color='#176fa6');ax.axhline(.405,ls=':',color='#aaa',lw=.7)
            ax.set(ylim=(-.20,1.05),xlim=(a,b),ylabel=n.split('.')[-1].upper()+' (V)');ax.set_yticks([0,.81]);ax.grid(alpha=.13)
            ax.ticklabel_format(useOffset=False,axis='x');ax.spines[['top','right']].set_visible(False)
        axes[0,j].set_title(title,fontsize=11);axes[-1,j].set_xlabel('Native time (ns)')
    fig.suptitle('SS GNN path: three IO stages dominate the delay',fontsize=13)
    fig.supxlabel(textwrap.fill('Original standard-cell bit0 fixture: SS / VDD 0.81 V / -40 C, VREFP 0.9 V / VREFN 0 V; complete physical load, ideal CODE/rails/clock, comparator reset. Dashed 0.405 V is a timing diagnostic, not channel threshold. Native timestamps; no time alignment.',140),fontsize=8)
    fig.savefig(OWN/'baseline_GNN_stage_timing.png',dpi=165);plt.close(fig)


if __name__=='__main__':main()
