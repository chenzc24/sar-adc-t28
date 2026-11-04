"""Bounded local review of native current windows, explicit node-current signs."""
import bisect,csv,gzip,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

def read(tag):
    run='cmpdesign-current-'+tag+'-v1'
    cfg=json.loads((W/'testbenches'/run/'measure.json').read_text());result=json.loads((W/'results'/run/'result.json').read_text())
    with gzip.open(ROOT/'output/managed_execution/runs'/run/'collected/derived/wave.csv.gz','rt') as f:
        data=list(csv.DictReader(f))
    return run,cfg,result,{k:np.array([float(r[k]) for r in data]) for k in data[0]}

def integral(t,y,lo,hi):
    inside=(t>lo)&(t<hi);tt=np.r_[lo,t[inside],hi];yy=np.r_[np.interp(lo,t,y),y[inside],np.interp(hi,t,y)]
    return float(np.trapezoid(yy,tt))

def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(4,2,figsize=(13,11),layout='constrained');all_results=[]
    for col,tag in enumerate(['reset','start']):
        run,cfg,res,d=read(tag);t=d['time'];edge=cfg['edge_s'];peak=res['peak_time_s'];x=(t-edge)*1e12
        target=cfg['target'].lower();node=target.split('.')[-1];prefix='x'+cfg['context'].lower()+'.'
        voltage=d[target];branch_data=[]
        for branch in cfg['branches']:
            signal=branch['signal'].lower();into=-d[signal]
            label=branch['device']+'.'+branch['terminal']
            b={'label':label,'signal':signal,'peak_injection_A':float(max(into)),'peak_extraction_A':float(-min(into)),
               'edge_to_peak_injected_C':integral(t,into,edge,peak),
               'peak_to_150ps_injected_C':integral(t,into,peak,edge+150e-12)}
            branch_data.append(b)
        branch_data.sort(key=lambda b:b['edge_to_peak_injected_C'],reverse=True)
        axs[0,col].plot(x,d['ck'],color='#495e70');axs[0,col].set_ylabel('Clock (V)')
        axs[0,col].set_title(f'{tag.upper()} | {cfg["context"]} | FF, 0.99 V, {cfg["temperature_c"]} C\nNative peak {res["peak_V"]:.6f} V at {peak*1e9:.6f} ns',fontsize=11)
        axs[1,col].plot(x,(voltage-.99)*1e3,color='#b4413d');axs[1,col].axhline(0,ls=':',color='gray');axs[1,col].set_ylabel(node+' minus VDD (mV)')
        for b in branch_data:axs[2,col].plot(x,-d[b['signal']]*1e6,label=b['label'],lw=1.2)
        axs[2,col].axhline(0,color='gray',ls=':');axs[2,col].set_ylabel('Into node (+) / out (-), uA');axs[2,col].legend(ncol=4,fontsize=8,loc='upper right')
        for ax in axs[:3,col]:
            ax.axvspan(0,(peak-edge)*1e12,color='#cadce5',alpha=.25);ax.axvline((peak-edge)*1e12,ls=':',color='gray');ax.set_xlim(-15,150);ax.grid(alpha=.15);ax.set_axisbelow(True)
        axs[2,col].set_xlabel('Time from %.3f ns edge start (ps)'%(edge*1e9))
        vals=[b['edge_to_peak_injected_C']*1e15 for b in branch_data]
        axs[3,col].bar([b['label'] for b in branch_data],vals,color=['#bc5c42' if v>0 else '#46799c' for v in vals])
        axs[3,col].axhline(0,color='gray',lw=.8);axs[3,col].set_ylabel('Net charge into node (fC)');axs[3,col].set_title('Integrated from clock edge start to voltage peak',fontsize=10);axs[3,col].grid(axis='y',alpha=.15);axs[3,col].set_axisbelow(True)
        # Treat OP names as raw observables; quantify their agreement before using decomposition.
        op_checks=[]
        for dev in cfg['devices']:
            path=prefix+dev['name'].lower();raw=path+':1'
            if path+':id' not in d:continue
            opid=d[path+':id'];idrain=d[raw]
            item={'device':dev['name'],'id_max_A':float(max(abs(opid))),'terminal_drain_max_A':float(max(abs(idrain)))}
            item['edge_to_peak_terminal_drain_C']=integral(t,idrain,edge,peak)
            item['edge_to_peak_op_id_C']=integral(t,opid,edge,peak)
            if path+':qd' in d:
                delta_qd=float(np.interp(peak,t,d[path+':qd'])-np.interp(edge,t,d[path+':qd']))
                item['edge_to_peak_delta_qd_C']=delta_qd
                item['integrated_drain_reconstruction_residual_C']=item['edge_to_peak_terminal_drain_C']-item['edge_to_peak_op_id_C']-delta_qd
                dq=np.gradient(d[path+':qd'],t)
                for scale in [1,4,-1,-4]:
                    item['rms_I_minus_scaled_id_plus_dqd_'+str(scale)]=float(np.sqrt(np.mean((idrain-scale*(opid+dq))**2)))
            if path+':igs' in d and path+':igd' in d and path+':igb' in d:
                leak=d[path+':igs']+d[path+':igd']+d[path+':igb'];ig=d[path+':2']
                item.update(gate_total_peak_A=float(max(abs(ig))),reported_gate_leak_sum_peak_A=float(max(abs(leak))))
            if path+':qg' in d:
                item['edge_to_peak_gate_terminal_C']=integral(t,d[path+':2'],edge,peak)
                item['edge_to_peak_delta_qg_C']=float(np.interp(peak,t,d[path+':qg'])-np.interp(edge,t,d[path+':qg']))
            op_checks.append(item)
        all_results.append(dict(run_id=run,configuration=cfg,measurement=res,branches=branch_data,op_diagnostics=op_checks))
    fig.suptitle('Comparator branch currents | unchanged transistor sizes, sources, clock and loads\nEvery native sample in each window; Cs = 1.28 pF/side, CL = 6.1 fF/output; no SAR cells / noise / mismatch / PEX\nPositive current injects the observed node; negative current extracts charge. D/G/S identify the measured device terminal.',fontsize=11)
    fig.savefig(W/'figures/overshoot_branch_currents.png',dpi=150,bbox_inches='tight');plt.close(fig)
    write(W/'results/current_attribution.json',json.dumps(all_results,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['run_id','branches','op_diagnostics']} for r in all_results],indent=2))

if __name__=='__main__':main()
