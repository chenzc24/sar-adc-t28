"""Compact waveform review; stress maxima remain native all-point measurements."""
import argparse,json,re,sys,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_stress_closure'))
from stream_analyze import edges,bottom_errors,sustained
VERIFY=ROOT/'verification/sar8_physical_repair'

def load(folder):
    meta=json.loads((folder/'wave.meta.json').read_text())
    names=(folder/'wave.columns').read_text().splitlines()
    assert len(names)==meta['columns']
    assert (folder/'wave.bin').stat().st_size==meta['points']*len(names)*8
    m=np.memmap(folder/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],len(names)))
    w={n:m[:,i] for i,n in enumerate(names)}
    assert np.all(np.diff(w['time'])>0)
    return m,w,w['time']*1e9,meta

def analyze(run):
    col=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt=json.loads((col/'collection_receipt.json').read_text())
    def collected(name):
        item=next(x for x in receipt['files'] if x['name']==name)
        p=col/name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
        return p
    d=col/'derived';result=json.loads((d/'result.json').read_text())
    failed=json.loads((d/'failing_pairs.json').read_text())
    result['excess_bins']={str(threshold):sum(r['peak_v']-r['limit_v']>threshold for r in failed)
                          for threshold in [1e-6,1e-3,.01]}
    sim=json.loads(collected('simulation.state.json').read_text())
    assert sim['status']=='complete'
    log=collected('spectre.out').read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    assert re.search(r'tran_perf\s+PASS',collected('raw/logStatus').read_text())
    m,w,t,meta=load(d)
    rows=[[float(v) for v in r.split(',')] for r in re.findall(r'R4MEAS,([^\r\n]+)',log)]
    assert [int(r[0]) for r in rows]==[0,1]
    frames=[];settling=[]
    diff=w['xdut.topp']-w['xdut.topn']
    for row in rows:
        i=int(row[0]);lo=i*100;hi=lo+100;target=[.81,-.81][i]
        code=sum(int(np.interp(hi-2,t,w['d%d'%b])>.495)*(1<<b) for b in range(8))
        assert code==int(row[1])
        counts=[]
        for n in ['xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u','xdut.xref.cap_clk']:
            e=edges(t,w[n]);counts.append(int(sum((e>lo)&(e<hi))))
        close=edges(t,w['xdut.seq_sample'],False);close=float(close[(close>lo)&(close<hi)][0])
        comp=edges(t,w['xdut.cmp_clk']);comp=comp[(comp>lo)&(comp<hi)]
        upd=edges(t,w['xdut.phi_u']);upd=upd[(upd>lo)&(upd<hi)]
        frames.append(dict(frame=i,code=code,expected=[243,12][i],counts=counts,
            monitor_valid=bool(row[7]),sample_close_ns=close,
            held_error_mv=(float(np.interp(lo+41.8,t,diff))-target)*1000,
            preclose_error_mv=(float(np.interp(close-.2,t,diff))-target)*1000))
        for j,u in enumerate(upd):
            later=comp[comp>u]
            if not len(later):continue
            end=float(later[0]-.01)
            ts,nom,local,_=bottom_errors(t,w,u,end)
            settling.append(dict(frame=i,update=j,nominal=sustained(ts,nom,u,end),
                local=sustained(ts,local,u,end)))
    extrema={}
    for line in (d/'wave.extrema.tsv').read_text().splitlines():
        n,*v=line.split();extrema[n]=list(map(float,v))
    bottom=min((extrema['xdut.xcdac.b%s%d'%(s,b)][0],s,b,
                extrema['xdut.xcdac.b%s%d'%(s,b)][1]*1e9) for s in ['p','n'] for b in range(8))
    result.update(run_id=run,frames=frames,settling_estimates=settling,
        waveform_qualification='10 ps minimum-spaced plotting export; timing/settling interpolated estimates, not final exact timing qualification',
        all_codes_pass=all(f['code']==f['expected'] for f in frames),
        all_event_counts_pass=all(f['counts']==[8,8,8,16] and f['monitor_valid'] for f in frames),
        bottom_min_v=bottom[0],bottom_min_node='B%s%d'%(bottom[1].upper(),bottom[2]),bottom_min_ns=bottom[3],
        GNN4_peak_v=extrema['xdut.gnn4'][2],GNN4_peak_ns=extrema['xdut.gnn4'][3]*1e9,
        BP7_min_v=extrema['xdut.xcdac.bp7'][0],BP3_min_v=extrema['xdut.xcdac.bp3'][0],
        native_CMI_present='WARNING (CMI-' in log,
        effective_settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1]
            for k in ['maxstep','reltol','abstol(V)','abstol(I)','method','temp']})
    (VERIFY/(run+'_analysis.json')).write_text(json.dumps(result,indent=2)+'\n')
    plot(run,w,t,extrema)
    print(json.dumps({k:result[k] for k in ['all_codes_pass','all_event_counts_pass','GNN4_peak_v','BP7_min_v','BP3_min_v','bottom_min_node','bottom_min_v','failing_pairs','groups','frames']},indent=2))

def plot(run,w,t,extrema):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    base=ROOT/'output/sar8_stress_closure/rg1_strict200_ff_m40/stream_v1'
    bm,bw,bt,_=load(base)
    rm,rw,rt,_=load(ROOT/'output/sar8_stress_closure/rg4_strict200_ff_m40/stream_v1')
    fig,axs=plt.subplots(3,1,figsize=(11,8.8),layout='constrained')
    settings=[('xdut.gnn4',171.9,173.6,'GNN4 (V)',.99),
        ('xdut.xcdac.bp7',144.05,145.05,'BP7 (mV)',0),
        ('xdut.xcdac.bp3',172,177,'BP3 (mV)',0)]
    for ax,(node,lo,hi,label,lim) in zip(axs,settings):
        scale=1 if node=='xdut.gnn4' else 1000
        for tx,wx,name,color in [(bt,bw,'Original baseline','#2864a0'),
            (rt,rw,'Historical Rgate/4','#9c9c9c'),(t,w,'Rgate/4 + MOM candidate','#cb543b')]:
            ids=(tx>=lo)&(tx<=hi)
            ax.plot(tx[ids],wx[node][ids]*scale,label=name,color=color,lw=1.5)
        if node=='xdut.gnn4':
            x,y=extrema[node][3]*1e9,extrema[node][2]
        else:x,y=extrema[node][1]*1e9,extrema[node][0]*scale
        if lo<=x<=hi:ax.scatter([x],[y],color='#cb543b',s=25,zorder=4,label='All-point extremum')
        ax.axhline(lim,color='#777777',ls=':',lw=1,label='Core limit' if lim else '0 V')
        ax.set(xlabel='Time (ns)',ylabel=label,xlim=(lo,hi))
        ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2,loc='best')
    axs[1].set_ylim(-80,100)
    axs[2].set_ylim(-80,100)
    fig.suptitle('FF / 0.99 V / -40 C | Native T28, Mmain 2 um, reference L 90 nm\n'
                 'Same sample clock and finite reference network | Candidate: Rgate/4 + 4.08 pF MOM total\n'
                 'Candidate lines: >=10 ps export; marked peaks: every native point',fontsize=10)
    folder=ROOT/'docs/figures/sar8_physical_repair';folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/(run+'.png'),dpi=180);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');analyze(p.parse_args().run)
