"""Local branch-charge attribution, native windows, voltage and current figures."""
import csv,gzip,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

RUN='cmpdesign-edge-current-a4-ff-hot-v1'
P='xa4_held.'
def integral(t,y,lo,hi):
    sel=(t>lo)&(t<hi)
    return float(np.trapezoid(np.r_[np.interp(lo,t,y),y[sel],np.interp(hi,t,y)],np.r_[lo,t[sel],hi]))
def read(path):
    with gzip.open(path,'rt') as f:r=list(csv.DictReader(f))
    return {k:np.array([float(x[k]) for x in r]) for k in r[0]}
def main():
    cfg=json.loads((W/'testbenches'/RUN/'measure.json').read_text())
    res=json.loads((W/'results'/RUN/'result.json').read_text())
    collected=ROOT/'output/managed_execution/runs'/RUN/'collected/derived'
    out=[]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    for w,r in zip(cfg['windows'],res['windows']):
        d=read(collected/(w['tag']+'.csv.gz'));t=d['time'];node=w['target'].lower();peak=r['peak_time_s'];edge=w['edge_s'];x=(t-edge)*1e12
        above=np.where((t<=peak)&(d[node]<=.99))[0]
        if len(above):
            j=above[-1];cross=float(t[j]+(t[j+1]-t[j])*(.99-d[node][j])/(d[node][j+1]-d[node][j]))
        else:cross=edge
        phases=[('edge_to_peak',edge,peak),('above_to_peak',cross,peak),('recovery',peak,min(peak+150e-12,t[-1]))]
        item=dict(tag=w['tag'],measurement=r,cross_s=cross,branches=[],op_checks=[],snapshots={})
        for at,label in [(edge,'edge'),(cross,'cross'),(peak,'peak')]:
            item['snapshots'][label]={n:float(np.interp(at,t,d[n])) for n in ['ck','pa4_held','na4_held',P+'net1',P+'net2',P+'net3',P+'lp',P+'ln']}
        for b in w['branches']:
            signal=b['signal'].lower();dev=P+b['device'].lower();terminal=b['terminal'];into=-d[signal]
            entry=dict(device=b['device'],terminal=terminal,peak_into_uA=float(into.max()*1e6),peak_out_uA=float(-into.min()*1e6),phase={})
            for label,lo,hi in phases:
                q=integral(t,into,lo,hi)
                a=dict(into_fC=q*1e15)
                qname=dev+':q'+terminal.lower()
                if qname in d:
                    dq=float(np.interp(hi,t,d[qname])-np.interp(lo,t,d[qname]))
                    a.update(raw_delta_Q_fC=dq*1e15)
                if terminal=='D' and dev+':id' in d:
                    op=integral(t,d[dev+':id'],lo,hi)
                    a.update(raw_id_into_fC=-op*1e15)
                    if qname in d:a['raw_id_q_reconstruction_error_fC']=(-q-op-dq)*1e15
                entry['phase'][label]=a
            item['branches'].append(entry)
        # Multi scaling and q-charge consistency must be verified before interpretation.
        for dev in cfg['devices']:
            path=P+dev['name'].lower()
            if path+':qd' not in d:continue
            for label,lo,hi in phases[:2]:
                qd=float(np.interp(hi,t,d[path+':qd'])-np.interp(lo,t,d[path+':qd']))
                qport=integral(t,d[path+':1'],lo,hi);qid=integral(t,d[path+':id'],lo,hi)
                qg=float(np.interp(hi,t,d[path+':qg'])-np.interp(lo,t,d[path+':qg']))
                qgate=integral(t,d[path+':2'],lo,hi)
                item['op_checks'].append(dict(device=dev['name'],phase=label,drain_terminal_fC=qport*1e15,id_fC=qid*1e15,delta_qd_fC=qd*1e15,drain_residual_fC=(qport-qid-qd)*1e15,gate_terminal_fC=qgate*1e15,delta_qg_fC=qg*1e15))
        out.append(item)
        fig,ax=plt.subplots(5,1,figsize=(10,12),sharex=True,layout='constrained')
        ax[0].plot(x,d['ck'],label='CLK');ax[0].plot(x,d['pa4_held'],label='VINP');ax[0].plot(x,d['na4_held'],label='VINN');ax[0].set_ylabel('Excitation (V)');ax[0].legend(ncol=3)
        for n in ['lp','ln','net3']:ax[1].plot(x,d[P+n],label=n)
        ax[1].set_ylabel('Internal nodes (V)');ax[1].legend(ncol=3)
        for n in ['net1','net2']:ax[2].plot(x,1e3*(d[P+n]-.99),label=n)
        ax[2].set_ylim(-12,8);ax[2].axhline(0,color='gray',ls=':');ax[2].set_ylabel('Node - VDD (mV)');ax[2].legend(ncol=2)
        for b in w['branches']:ax[3].plot(x,-d[b['signal'].lower()]*1e6,label=b['device']+'.'+b['terminal'])
        ax[3].set_ylabel('Into target node (uA)');ax[3].legend(ncol=3);ax[3].axhline(0,color='gray',ls=':')
        # Plot the relevant dynamic charge against measured terminal injection.
        dev,term,qfield=('m9','1','qd') if w['tag']=='input_net2' else (('m6','3','qs') if w['tag']=='reset_net1' else ('m7','3','qs'))
        start=edge if w['tag']=='input_net2' else cross
        mask=(t>=start)&(t<=peak+30e-12);tt=t[mask]
        charge=np.array([integral(t,-d[P+dev+':'+term],start,at) for at in tt])*1e15
        dyn=-(d[P+dev+':'+qfield][mask]-np.interp(start,t,d[P+dev+':'+qfield]))*1e15
        ax[4].plot((tt-edge)*1e12,charge,label=dev.upper()+' terminal integral',lw=2)
        ax[4].plot((tt-edge)*1e12,dyn,'--',label='-Delta '+qfield+' (raw model)')
        if w['tag']=='input_net2':
            conduction=np.array([integral(t,-d[P+dev+':id'],start,at) for at in tt])*1e15
            ax[4].plot((tt-edge)*1e12,conduction,label='-integral id')
        ax[4].set_ylabel('Injected charge (fC)');ax[4].legend(ncol=3);ax[4].axhline(0,color='gray',ls=':')
        for a in ax:
            a.axvline((peak-edge)*1e12,color='#bb4433',ls=':');a.axvspan((cross-edge)*1e12,(peak-edge)*1e12,alpha=.15,color='#719eba');a.grid(alpha=.15)
        ax[-1].set_xlabel('Time from %.3f ns %s (ps)'%(edge*1e9,'input update' if w['tag'].startswith('input') else 'fall start'))
        ax[-1].set_xlim(-30,250 if w['tag'].startswith('input') else 400)
        fig.suptitle('%s | peak %.6f V at %.6f ns\nA4 unchanged | FF, 0.99 V, 125 C | rise/fall 200/500 ps, fixed 50%%\nIdeal sources; held 1.28 pF/side, CL 6.1 fF; no real SAR / noise / mismatch / PEX\nTerminal current: + into node, - out; shaded interval: crossing VDD to peak'%(w['tag'],r['peak_V'],peak*1e9),fontsize=11)
        fig.savefig(W/'figures'/('edge_current_'+w['tag']+'.png'),dpi=150);plt.close(fig)
    write(W/'results/edge_current_attribution.json',json.dumps(out,indent=2)+'\n')
    for i in out:print(json.dumps({k:i[k] for k in ['tag','measurement','cross_s','snapshots','branches']},indent=2))
if __name__=='__main__':main()
