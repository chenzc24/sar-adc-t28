"""Locate two overshoot classes using collected full-native zooms. No circuit mutation."""
import csv,gzip,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

CASES=[dict(name='reset',zoom='cmpdesign-worst-terminal-zoom-v1',source='cmpdesign-b0-i4-ff-hot-v1',
            context='B0_held',node='xb0_held.ln',edge_ns=155.5,corner='FF / 0.99 V / 125 C',desc='B0: reset-edge LN overshoot'),
       dict(name='start',zoom='cmpdesign-start-overshoot-zoom-v1',source='cmpdesign-b0-i4-ff-cold-v1',
            context='I4_held',node='xi4_held.net2',edge_ns=354.,corner='FF / 0.99 V / -40 C',desc='I4: evaluation-edge net2 overshoot')]

def crossing(a,b,node,threshold):
    return a['time']+(threshold-a[node])*(b['time']-a['time'])/(b[node]-a[node])

def measure(rows,node,threshold=.99):
    i=max(range(len(rows)),key=lambda k:rows[k][node]);left=right=i
    while left>0 and rows[left][node]>threshold:left-=1
    while right<len(rows)-1 and rows[right][node]>threshold:right+=1
    if rows[left][node]>threshold or rows[right][node]>threshold:raise ValueError('censored pulse')
    start=crossing(rows[left],rows[left+1],node,threshold);end=crossing(rows[right-1],rows[right],node,threshold)
    return dict(node=node,peak_V=rows[i][node],peak_time_ns=rows[i]['time']*1e9,
                threshold_V=threshold,cross_up_ns=start*1e9,cross_down_ns=end*1e9,pulse_width_ps=(end-start)*1e12,
                peak_sample=rows[i],crossing_method='Linear interpolation of bracketing native points; only the lobe containing the peak')

def main():
    dest=W/'results/overshoot_location';dest.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(3,2,figsize=(12,8),layout='constrained');evidence=[]
    for col,c in enumerate(CASES):
        zoom=json.loads((W/'results'/c['zoom']/'result.json').read_text());assert zoom['peak_verified'] and not zoom['decimation']
        source=ROOT/'output/managed_execution/runs'/c['zoom']/'collected/derived/wave.csv.gz'
        with gzip.open(source,'rt') as f:rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
        result=measure(rows,c['node']);assert abs(result['peak_V']-zoom['peak_V'])<1e-9
        result.update({k:c[k] for k in ['source','zoom','context','edge_ns','corner']})
        result['peak_after_edge_start_ps']=(result['peak_time_ns']-c['edge_ns'])*1000
        result['native_source_csv']=str(source.relative_to(ROOT));evidence.append(result)
        keys=['time','ck','ip','in']+['x'+c['context'].lower()+'.'+n for n in ['lp','ln','net1','net2','net3']]
        with open(dest/(c['name']+'_native.csv'),'w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows({k:r[k] for k in keys} for r in rows)
        shown=[r for r in rows if -20 <= (r['time']*1e9-c['edge_ns'])*1000 <= 130]
        time=[(r['time']*1e9-c['edge_ns'])*1000 for r in shown]
        axs[0,col].plot(time,[r['ck'] for r in shown],color='#475a69')
        axs[0,col].set_title(c['desc']+'\n'+c['corner'],fontsize=11);axs[0,col].set_ylabel('Clock (V)')
        prefix='x'+c['context'].lower()+'.'
        for n in ['lp','ln','net1','net2']:
            axs[1,col].plot(time,[r[prefix+n] for r in shown],label=n,lw=1.3)
        axs[1,col].axhline(.99,ls=':',color='gray');axs[1,col].set_ylabel('Internal nodes (V)');axs[1,col].legend(ncol=4,fontsize=8,loc='lower right')
        axs[2,col].plot(time,[(r[c['node']]-.99)*1000 for r in shown],color='#b8403f')
        axs[2,col].axhline(0,ls='--',color='gray');axs[2,col].set_ylabel(c['node'].split('.')[-1]+' minus VDD (mV)')
        peak_t=result['peak_after_edge_start_ps'];peak_mv=(result['peak_V']-.99)*1000
        axs[2,col].plot([peak_t],[peak_mv],'o',color='#b8403f',ms=4)
        axs[2,col].annotate(f'{peak_mv:.2f} mV\n{result["peak_time_ns"]:.6f} ns',xy=(peak_t,peak_mv),xytext=(62,peak_mv*.65),arrowprops={'arrowstyle':'->','color':'#555'},fontsize=9)
        lo=(result['cross_up_ns']-c['edge_ns'])*1000;hi=(result['cross_down_ns']-c['edge_ns'])*1000
        axs[2,col].axvspan(lo,hi,color='#d8a0a0',alpha=.22)
        axs[2,col].set_xlabel(f'Time from {c["edge_ns"]:.3f} ns edge start (ps)\nAbove 0.99 V: {result["pulse_width_ps"]:.2f} ps')
        for ax in axs[:,col]:
            ax.axvline(0,color='gray',ls=':',lw=.8);ax.axvline(50,color='gray',ls=':',lw=.8);ax.grid(alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('Two comparator overshoot events: reset vs evaluation start\nFull native samples; 15-MOS DUT; ideal input/supply/50 ps clock; Cs = 1.28 pF/side; CL = 6.1 fF/output\nNo SAR standard cells, noise, mismatch or PEX; waveforms reprocessed from completed runs',fontsize=11)
    fig.savefig(W/'figures/overshoot_location.png',dpi=150,bbox_inches='tight');plt.close(fig)
    table=[]
    for tag in ['ff-cold','ff-hot']:
        data=json.loads((W/'results'/('cmpdesign-b0-i4-'+tag+'-v1')/'result.json').read_text())
        for key in ['B0_held','I4_held']:
            for node,pair in [('LP','M12:GB'),('LN','M14:GB'),('net1','M8:DB'),('net2','M9:DB')]:
                value=data['contexts'][key]['terminal_pairs'][pair]
                table.append(dict(condition=tag,context=key,node=node,pair=pair,peak_V=value['peak_V'],time_ns=value['time_s']*1e9,total_above_ns=value['time_above_s']*1e9))
    write(dest/'measurements.json',json.dumps({'events':evidence,'full_run_peaks':table,'new_simulations':False},indent=2)+'\n')
    print(json.dumps({'events':[{k:v for k,v in e.items() if k!='peak_sample'} for e in evidence]},indent=2))

if __name__=='__main__':main()
