"""Full connected branch currents and separately integrated over-rail phase."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write
from review_edge_current import read,integral

RUN='cmpdesign-combo-latch-current-ff-hot-v2';P='xa4_held.'
def main():
    cfg=json.loads((W/'testbenches'/RUN/'measure.json').read_text());res=json.loads((W/'results'/RUN/'result.json').read_text())
    out=[];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    for w,r in zip(cfg['windows'],res['windows']):
        d=read(ROOT/'output/managed_execution/runs'/RUN/'collected/derived'/(w['tag']+'.csv.gz'))
        t=d['time'];node=w['target'].lower();peak=r['peak_time_s'];edge=w['edge_s'];i=int(np.argmax(d[node]));left=right=i
        while left>0 and d[node][left-1]>.99:left-=1
        while right+1<len(t) and d[node][right+1]>.99:right+=1
        assert left>0 and right+1<len(t)
        cross=float(t[left-1]+(t[left]-t[left-1])*(.99-d[node][left-1])/(d[node][left]-d[node][left-1]))
        end=float(t[right]+(t[right+1]-t[right])*(.99-d[node][right])/(d[node][right+1]-d[node][right]))
        phases=[('edge_to_peak',edge,peak),('above_to_peak',cross,peak),('recovery',peak,end)]
        item=dict(tag=w['tag'],measurement=r,source_peak_difference_V=r['peak_V']-w['source_pulse']['peak_V'],cross_s=cross,end_s=end,duration_s=end-cross,branches=[],snapshots={})
        for at,label in [(edge,'edge'),(cross,'cross'),(peak,'peak'),(end,'end')]:
            item['snapshots'][label]={n:float(np.interp(at,t,d[n])) for n in ['ck','pa4_held','na4_held']+[P+n for n in ['net1','net2','net3','lp','ln']]}
        for b in w['branches']:
            signal=b['signal'].lower();dev=P+b['device'].lower();terminal=b['terminal'];into=-d[signal]
            entry=dict(device=b['device'],terminal=terminal,peak_into_uA=float(into.max()*1e6),peak_out_uA=float(-into.min()*1e6),phase={})
            for label,lo,hi in phases:
                q=integral(t,into,lo,hi);a=dict(into_fC=q*1e15)
                qname=dev+':q'+terminal.lower()
                if qname in d:
                    dq=float(np.interp(hi,t,d[qname])-np.interp(lo,t,d[qname]));a['raw_delta_Q_fC']=dq*1e15
                if terminal=='D':
                    qid=integral(t,d[dev+':id'],lo,hi);a['raw_id_into_fC']=-qid*1e15
                    if qname in d:a['id_q_reconstruction_error_fC']=(-q-qid-dq)*1e15
                if terminal=='G':
                    leak=sum(d[dev+':'+f] for f in ['igs','igd','igb'])
                    a['raw_gate_leak_into_fC']=-integral(t,leak,lo,hi)*1e15
                    a['gate_Q_error_fC']=(-q-dq)*1e15
                    m=(t>=lo)&(t<=hi);a['gate_leak_peak_A']=float(np.max(abs(leak[m])))
                entry['phase'][label]=a
            item['branches'].append(entry)
        item['branches'].sort(key=lambda b:b['phase']['above_to_peak']['into_fC'],reverse=True)
        out.append(item)
        x=(t-w['fall50_s'])*1e12;fig,ax=plt.subplots(5,1,figsize=(11,12),layout='constrained')
        ax[0].plot(x,d['ck'],label='CLK');ax[0].plot(x,d['pa4_held'],label='VINP');ax[0].plot(x,d['na4_held'],label='VINN');ax[0].legend(ncol=3);ax[0].set_ylabel('External signals (V)')
        other='lp' if node.endswith('ln') else 'ln'
        for n in [other,'net1','net2','net3']:ax[1].plot(x,d[P+n],label=n.upper() if len(n)==2 else n)
        ax[1].legend(ncol=4);ax[1].set_ylabel('Internal recovery (V)')
        ax[2].plot(x,(d[node]-.99)*1e3,color='#b34237',label=node.split('.')[-1].upper());ax[2].axhline(0,color='gray',ls=':');ax[2].set_ylabel('Observed node - VDD (mV)');ax[2].set_ylim(-1,5.2);ax[2].legend()
        for b in item['branches']:ax[3].plot(x,-d[P+b['device'].lower()+':'+str('DGSB'.index(b['terminal'])+1)]*1e6,label=b['device']+'.'+b['terminal'])
        ax[3].axhline(0,color='gray',ls=':');ax[3].set_ylabel('Into node (+) / out (-), uA');ax[3].legend(ncol=4,fontsize=8);ax[3].set_xlabel('Time from fall50 = %.3f ns (ps)'%(w['fall50_s']*1e9))
        for a in ax[:4]:
            a.set_xlim(-300,250);a.axvline(0,color='gray',ls=':');a.axvline((peak-w['fall50_s'])*1e12,color='#b34237',ls=':');a.axvspan((cross-w['fall50_s'])*1e12,(peak-w['fall50_s'])*1e12,color='#c9d9e2',alpha=.45);a.grid(alpha=.15)
        labels=[b['device']+'.'+b['terminal'] for b in item['branches']];xx=np.arange(len(labels))
        for off,phase,color,label in [(-.18,'edge_to_peak','#8ca4b8','Fall start to peak'),(.18,'above_to_peak','#b87142','Cross VDD to peak')]:
            ax[4].bar(xx+off,[b['phase'][phase]['into_fC'] for b in item['branches']],width=.36,color=color,label=label)
        ax[4].set_xticks(xx,labels);ax[4].axhline(0,color='gray',lw=.8);ax[4].set_ylabel('Net charge into node (fC)');ax[4].legend();ax[4].grid(axis='y',alpha=.15)
        fig.suptitle('%s reset | %.6f V at %.6f ns | all seven connected terminal currents\nCombined sizes: M3/M5 & M8/M9 multi2; M2/M4 multi4 | rise/fall200/500ps fixed\nFF,0.99V,125C | ideal sources | hold1.28pF/side, output6.1fF | no SAR/noise/mismatch/PEX\nShaded: VDD crossing to peak; total terminal currents include displacement'%(node.split('.')[-1].upper(),r['peak_V'],peak*1e9),fontsize=10)
        fig.savefig(W/'figures'/('combo_latch_current_'+node.split('.')[-1]+'.png'),dpi=150);plt.close(fig)
    write(W/'results/combo_latch_attribution.json',json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
