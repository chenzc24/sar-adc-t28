"""Ideal OFF-gate and fixed-bias temperature controls; final measured figures."""
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from control import ROOT,OUT,VERIFY,read,dump,sha
from native import load
from dc_probe import DCNAMES

def main():
    rows={};waves={}
    for name in DCNAMES:
        folder=OUT/name;raw=folder/'native/test.raw/dc_leak.dc'
        receipt=read(folder/'receipt.json');hashes={k.replace('\\','/'):v for k,v in receipt['native_files'].items()}
        assert sha(raw)==hashes['test.raw/dc_leak.dc']
        log=(folder/'native/spectre.out').read_text();status=(folder/'native/test.raw/logStatus').read_text()
        assert 'spectre completes with 0 errors' in log and re.search(r'dc_leak\s+PASS',status)
        w=load(raw);delta=w['delta'];assert len(delta)==21 and abs(delta[10])<1e-12
        metrics={}
        for side in ['p','n']:
            for mode in ['actual','ideal']:
                label=mode+'_'+side;path='x'+label
                vectors={dev:[w[path+'.'+dev+':'+str(i)] for i in range(1,5)] for dev in ['mn_low','mp_high']}
                assert all(np.max(np.abs(sum(v)))<1e-10 for v in vectors.values())
                metrics[label]=dict(bottom_v=float(w['bot_'+label][10]),
                    gn_v=float(w['gn_'+label][10]),gp_v=float(w['gp_'+label][10]),
                    high_load_ua=float(vectors['mp_high'][2][10]*1e6),
                    low_return_ua=float(-vectors['mn_low'][2][10]*1e6),
                    terminals_ua={dev:[float(v[10]*1e6) for v in vs] for dev,vs in vectors.items()})
        row=dict(name=name,delta_v=delta.tolist(),at_delta0=metrics,psf_sha256=sha(raw),
            high_load_sweep_ua={mode+'_'+side:(w['x'+mode+'_'+side+'.mp_high:3']*1e6).tolist()
                              for side in ['p','n'] for mode in ['actual','ideal']},
            effective_settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1]
                                for k in ['reltol','abstol(V)','abstol(I)','temp']},
            CMI='WARNING (CMI-' in log)
        rows[name]=row;waves[name]=w
        dump(VERIFY/(name+'.json'),row)
        print(name,metrics)
    hot=read(VERIFY/'branches_ffhot.json');cold=read(VERIFY/'branches_ffcold.json')
    grouped={off:sum(x['high_rail_load_ua'] for x in hot['branches'] if x['off_device']==off)
             for off in ['MN_LOW','MP_HIGH']}
    gates={}
    for side in ['P','N']:
        br=next(x for x in hot['branches'] if x['side']==side and x['bit']==7)
        a=rows['pair_ffhot']['at_delta0']['actual_'+side.lower()]
        ideal=rows['pair_ffhot']['at_delta0']['ideal_'+side.lower()]
        assert abs(a['high_load_ua']-br['high_rail_load_ua'])<.002
        gates[side]=dict(off_device=br['off_device'],actual_ua=a['high_load_ua'],ideal_ua=ideal['high_load_ua'],
            improvement_pct=100*(1-ideal['high_load_ua']/a['high_load_ua']),
            fixed_bias_cold_ua=rows['pair_ffcold_fixedbias']['at_delta0']['actual_'+side.lower()]['high_load_ua'])
    result=dict(at_ns=130,reference_word=128,hot_source_ua=hot['source_current_p_ua'],cold_source_ua=cold['source_current_p_ua'],
        contribution_by_off_device_ua=grouped,contribution_pct={k:100*v/hot['source_current_p_ua'] for k,v in grouped.items()},
        representative_bit7_gate_controls=gates,
        interpretation='Steady reference load is predominantly D-S off-state current; proper rail OFF gates do not remove it. See operating_point.json for native channel/leakage components.',
        scope='32 reference MOS terminal currents at130ns, two native temperatures and four isolated pair replicas per DC sweep. No production fix implemented.',
        CMI_integrated={n:read(VERIFY/(n+'.json'))['CMI'] for n in ['branches_ffhot','branches_ffcold']})
    opfile=VERIFY/'operating_point.json'
    if opfile.exists():
        op=read(opfile)['devices']['Xactual_N.MN_LOW']
        assert op['vgs']<op['vth'] and abs(op['ids']/op['id'])>.999
        result['native_off_NMOS_evidence']=op
        result['interpretation']='Dominant short-channel OFF-state D-S current below threshold (subthreshold channel leakage), not missing rail-off drive. Native ids dominates; GIDL/body/gate terms are minor at this bias. Not a silicon measurement.'
    dump(VERIFY/'conclusion.json',result)
    fig,axs=plt.subplots(2,1,figsize=(10,7))
    bits=list(reversed(range(8)))
    nload=[sum(x['high_rail_load_ua'] for x in hot['branches'] if x['bit']==b and x['off_device']=='MN_LOW') for b in bits]
    pload=[sum(x['high_rail_load_ua'] for x in hot['branches'] if x['bit']==b and x['off_device']=='MP_HIGH') for b in bits]
    x=np.arange(8)
    axs[0].bar(x,nload,color='#007f83',label=f"NMOS OFF paths: {grouped['MN_LOW']:.2f} uA (87.7%)")
    axs[0].bar(x,pload,bottom=nload,color='#d58b36',label=f"PMOS OFF paths: {grouped['MP_HIGH']:.2f} uA (12.3%)")
    axs[0].set(xticks=x,xticklabels=[f'bit {b}' for b in bits],ylabel='High-reference load (uA)',ylim=(0,90))
    axs[0].legend(loc='upper right',fontsize=9)
    axs[0].set_title('Integrated ADC, 125 C at 130 ns: both differential sides combined',fontsize=11)
    for i,(n,p) in enumerate(zip(nload,pload)):axs[0].text(i,n+p+1,f'{n+p:.2f}',ha='center',fontsize=8)
    for name,mode,color,style,label in [('pair_ffhot','actual','#b34238','-', '125 C, measured OFF gate'),
            ('pair_ffhot','ideal','#007f83','--','125 C, ideal 0 V OFF gate'),
            ('pair_ffcold_fixedbias','actual','#526a97','-','-40 C, same measured-hot biases')]:
        r=rows[name];val=r['at_delta0'][mode+'_n']['high_load_ua']
        axs[1].semilogy(np.array(r['delta_v'])*1000,r['high_load_sweep_ua'][mode+'_n'],color=color,ls=style,
                       label=f'{label}: {val:.3f} uA at 0 mV')
    axs[1].axvline(0,color='gray',ls=':',lw=1)
    axs[1].set(xlabel='Added OFF-NMOS gate bias (mV); 0 = stated gate condition',ylabel='Bit-7 pair reference current (uA)',xlim=(-50,50))
    axs[1].legend(loc='center left',fontsize=8.5)
    axs[1].set_title('Exact XSN7 pair DC control: same VREFP/VREFN and body biases',fontsize=11)
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.suptitle('FF / 0.99 V | native T28, 2 um bootstrap, 3x core reference switches\n'
                 '50-ohm reference sources; no mismatch/noise/PEX; diagnostic only',fontsize=11)
    fig.tight_layout();dest=ROOT/'docs/figures/sar8_ref_load';dest.mkdir(parents=True,exist_ok=True)
    fig.savefig(dest/'branch_and_gate_controls.png',dpi=180);plt.close(fig)

if __name__=='__main__':main()
