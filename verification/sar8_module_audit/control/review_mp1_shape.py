"""Native both-versus-MP1shape response, terminal charge and measured cost."""
import json
import os
import numpy as np

import prepare_first_event as base
import review_first_event_v1 as integ
from review_both_result import read_current_run

OWN=base.OWN
OUT=OWN/'mp1_shape_v1/results'
P='xdut.xctrl.xtim.'


def main():
    rows={
        'both':read_current_run(),
        'MP1shape':read_current_run('sar8audit-ctrl-mp1shape-v1','8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a'),
    }
    def col(table,names,name):return table[:,names.index(name)]
    info={}
    for label,(a,n,r,m,proof) in rows.items():
        gate=P+'live' if label=='both' else P+'x020.x000.b_pm'
        vdd=col(a,n,'vdd!');g=col(a,n,gate);d=col(a,n,P+'x020.n')
        gstats=r['voltage_and_current_extrema'][gate]
        supply=r['voltage_and_current_extrema']['vdd!']
        if supply['min']!=.99 or supply['max']!=.99:raise ValueError('Constant-supply VSG derivation requires fixed0.99V')
        currents=m['kcl_terms']['XDUT.XCTRL.XTIM.X020.N']
        times,q=integ.integrate_native(a[:,0],np.column_stack([col(a,n,x) for x in currents]),41.04e-9,r['peak_snapshot']['time_s'])
        fulltime,fullq=integ.integrate_native(a[:,0],np.column_stack([col(a,n,x) for x in currents]),41.04e-9,41.12e-9)
        energies={}
        for branch in ['10','14']:
            for node in ['n','mid']:
                power=-col(a,n,P+'snload'+branch+'_'+node)*col(a,n,P+'vbias'+branch+'_'+node+':1')
                energies['BIAS'+branch+'_'+node.upper()]=float(np.sum(.5*(power[1:]+power[:-1])*np.diff(a[:,0])))
        vv=r['voltage_and_current_extrema']['vvdd:1']
        quiet=col(a,n,P+'quiet')
        info[label]=dict(proof=proof,N_peak_v=float(d.max()),N_overshoot_v=float(d.max()-.99),
            N_peak_time_s=r['peak_snapshot']['time_s'],gate_min_v=gstats['min'],gate_max_v=gstats['max'],
            MP1_VSG_global_max_v=.99-gstats['min'],
            MP1_VGD_diagnostic_min_v=float((g-d).min()),MP1_VGD_diagnostic_max_v=float((g-d).max()),
            MP1_VGD_global_conservative_bounds_v=[gstats['min']-r['voltage_and_current_extrema'][P+'x020.n']['max'],
                gstats['max']-r['voltage_and_current_extrema'][P+'x020.n']['min']],
            exact_full_history_VGD_requires_joint_reanalysis=True,
            LIVE_edges_s=r['native_edges_s'][P+'live'],QUIET_edges_s=r['native_edges_s'][P+'quiet'],
            QUIET_falling_edges_in_diagnostic_s=base.edge_time(a[:,0],quiet,.99,False),
            VDD_peak_delivered_current_a=-vv['min'],
            VDD_full_history_energy_available=False,
            bias_source_net_delivered_j=energies,bias_energy_window_s=[float(a[0,0]),float(a[-1,0])],
            prepeak_charge_into_N_c=dict(zip(currents,map(float,q[-1]))),
            prepeak_charge_window_s=[float(times[0]),float(times[-1])],
            full_event_charge_into_N_c=dict(zip(currents,map(float,fullq[-1]))))
        if 'vvdd:1' in n:
            power=-vdd*col(a,n,'vvdd:1')
            info[label]['VDD_diagnostic_net_delivered_j']=float(np.sum(.5*(power[1:]+power[:-1])*np.diff(a[:,0])))
            info[label]['VDD_diagnostic_energy_window_s']=[float(a[0,0]),float(a[-1,0])]
    comparison=dict(versions=info,overshoot_reduction_fraction=1-info['MP1shape']['N_overshoot_v']/info['both']['N_overshoot_v'],
        VDD_peak_current_increase_fraction=info['MP1shape']['VDD_peak_delivered_current_a']/info['both']['VDD_peak_delivered_current_a']-1,
        LIVE_shift_s=info['MP1shape']['LIVE_edges_s'][0]-info['both']['LIVE_edges_s'][0],
        QUIET_shift_s=info['MP1shape']['QUIET_edges_s'][0]-info['both']['QUIET_edges_s'][0],
        not_qualified=True,reason='Residual N overvoltage and MP1 VSG/VGD violations remain; no whole-ADC performance/power claim.',
        current_interpretation='Total terminal currents mix channel transport and device charge. More injected charge can coexist with lower N peak when the pulldown path conducts earlier.')
    OUT.mkdir(exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(comparison,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    styles={'both':dict(color='#255d83',lw=1.5),'MP1shape':dict(color='#d16b24',lw=1.25,ls='--')}
    fig,axes=plt.subplots(4,1,sharex=True,figsize=(10,9),layout='constrained')
    for label,(a,n,_,_,_) in rows.items():
        signals=[P+'live',P+'live' if label=='both' else P+'x020.x000.b_pm',P+'x020.n',P+'quiet']
        for index,(ax,signal) in enumerate(zip(axes,signals)):
            wave=col(a,n,signal)
            if index==2:wave=(wave-.99)*1e3
            ax.plot(a[:,0]*1e9,wave,label=label,**styles[label])
    for ax,title,ylabel in zip(axes,['LIVE','Actual MP1 gate','N above0.99V rail','QUIET'],['V','V','mV','V']):
        ax.set(title=title,ylabel=ylabel);ax.grid(alpha=.2)
    axes[2].axhline(0,color='#b84c48',ls=':',lw=.8)
    axes[2].set(ylim=(-10,100),title='Positive N overshoot detail')
    axes[0].legend(fontsize=8,ncol=2,loc='center right')
    axes[-1].set(xlim=(41.04,41.13),xlabel='Original time (ns); no alignment or fitting')
    fig.suptitle('MP1 gate shaping: N peak improves, residual stress remains',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | corrected SN-load fixture versus one-PDK-resistor MP1 branch\n'
                  'External supply/clock ideal; conditional diffusion bias replay; no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'timing_comparison.png',dpi=165);plt.close(fig)
    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8),layout='constrained')
    for label,(a,n,_,_,_) in rows.items():
        for ax,trace in zip(axes[:2],[P+'x020.x000.mp1:1',P+'x020.x000.mn0:1']):
            ax.plot(a[:,0]*1e9,col(a,n,trace)*1e6,label=label,**styles[label])
        times,q=integ.integrate_native(a[:,0],a[:,[n.index(P+'x020.x000.mp1:1')]],41.04e-9,41.12e-9)
        axes[2].plot(times*1e9,q[:,0]*1e15,**styles[label])
    for ax,title,ylabel in zip(axes,['MP1 drain: negative injects into N','MN0 drain: positive leaves N','MP1 net charge into N'],['uA','uA','fC']):
        ax.set(title=title,ylabel=ylabel);ax.grid(alpha=.2)
    axes[0].legend(fontsize=8,ncol=2,loc='best')
    axes[-1].set(xlim=(41.04,41.12),xlabel='Original time (ns)')
    fig.suptitle('Current and charge cost: terminal totals, not Cgd decomposition',fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | corrected conditional fixture, same source PWL/supply/sample edge\n'
                  'Native-grid integrals; local source currents do not qualify full-ADC power',fontsize=8)
    fig.savefig(OUT/'current_charge_comparison.png',dpi=165);plt.close(fig)
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':main()
