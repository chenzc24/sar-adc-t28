"""Read-only same-window comparison; no new circuit candidate or remote work."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=HERE/'generated/cinput_r1k_comparison'
PREFIX='xdut.xref.xdrv0.'
RUNS=['sar8audit-ref-current-v2-reduce1','sar8audit-ref-cinput-r1k-v1']


def read_run(run):
    path=ROOT/'output/managed_execution/runs'/run/'collected/derived'
    r=json.loads((path/'result.json').read_text());e=r['native_exports'][1]
    raw=gzip.decompress((path/e['file']).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256']
    w=np.frombuffer(raw,dtype='<f8').reshape((-1,len(e['columns'])))
    return r,w,{n:i for i,n in enumerate(e['columns'])}


def settling(r,w,c,command):
    t=w[:,0];out={}
    for n,target in [('xdut.xcdac.bn0','vrefp'),('xdut.xcdac.bp0','vrefn')]:
        err=w[:,c[n]]-w[:,c[target]];selected=t>=command
        bad=np.flatnonzero(selected & (np.abs(err)>.001))
        after=None if not len(bad) or bad[-1]+1==len(t) else int(bad[-1]+1)
        out[n]=dict(final_error_mV=float(err[-1]*1e3),
            last_outside_1mV_native_s=None if not len(bad) else float(t[bad[-1]]),
            first_remained_inside_1mV_native_s=None if after is None else float(t[after]),
            native_crossing_bracket_width_ps=None if after is None else float((t[after]-t[bad[-1]])*1e12),
            min_voltage_V=float(w[selected,c[n]].min()),max_voltage_V=float(w[selected,c[n]].max()))
    return dict(independent_command_time_s=command,expected_Q0=1,target='BN0->VREFP, BP0->VREFN from independent CODE243',
                tolerance_V=.001,diagnostic_only=True,observed_until_s=float(t[-1]),nodes=out)


def edge(r,n,direction):
    found=[e for e in r['half_vdd_events'][n] if e['direction']==direction and 65.19e-9<e['estimated_time_s']<65.6e-9]
    if len(found)!=1:raise ValueError('Expected exactly one matching local edge '+n)
    return found[0]


def screens(base,new,old_cfg,new_cfg,old_wave,new_wave):
    old_map={x['instance']+':'+x['terminal']:x for x in old_cfg['selected_mos_pair_screens']}
    new_map={x['instance']+':'+x['terminal']:x for x in new_cfg['selected_mos_pair_screens']}
    assert set(old_map)==set(new_map) and len(old_map)==228
    out=[];covered=0
    for name in sorted(old_map):
        a=base['selected_mos_pair_extrema'][name];b=new['selected_mos_pair_extrema'][name]
        aa=max(abs(a['min']),abs(a['max']));bb=max(abs(b['min']),abs(b['max']));limit=old_map[name]['screen_v']
        assert limit==new_map[name]['screen_v']
        row=dict(pair=name,model=new_map[name]['model'],limit_V=limit,
            base_nodes=' | '.join(old_map[name]['nodes']),R1k_nodes=' | '.join(new_map[name]['nodes']),
            base_min_V=a['min'],base_max_V=a['max'],base_min_time_ns=a['min_time_s']*1e9,base_max_time_ns=a['max_time_s']*1e9,
            R1k_min_V=b['min'],R1k_max_V=b['max'],R1k_min_time_ns=b['min_time_s']*1e9,R1k_max_time_ns=b['max_time_s']*1e9,
            base_abs_peak_V=aa,R1k_abs_peak_V=bb,change_abs_peak_mV=(bb-aa)*1e3,
            base_excess_mV=(aa-limit)*1e3,R1k_excess_mV=(bb-limit)*1e3,
            scope='Full native0..65.9965ns extrema, NOT only65ns window')
        local=[]
        for cfg_map,(w,c) in [(old_map,old_wave),(new_map,new_wave)]:
            nodes=[n.lower() for n in cfg_map[name]['nodes']]
            if all(n=='0' or n in c for n in nodes):
                value=[0. if n=='0' else w[:,c[n]] for n in nodes]
                pair=value[0]-value[1]
                local.append(float(np.max(np.abs(pair))))
            else:local.append(None)
        if None not in local:covered+=1
        row.update(fault_window_base_abs_V=local[0],fault_window_R1k_abs_V=local[1])
        out.append(row)
    with (OUT/'all_228_terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(out[0]));writer.writeheader();writer.writerows(out)
    return out,dict(full_history_pairs=228,fault_window_pair_coverage=covered,
        unavailable_fault_pairs_not_fabricated=228-covered,
        base_strict_exceed_pairs=sum(x['base_excess_mV']>0 for x in out),
        R1k_strict_exceed_pairs=sum(x['R1k_excess_mV']>0 for x in out),
        base_exceed_by_more_than1mV_pairs=sum(x['base_excess_mV']>1 for x in out),
        R1k_exceed_by_more_than1mV_pairs=sum(x['R1k_excess_mV']>1 for x in out),
        count_note='Counts are terminal-pair records, not transistor counts;1mV grouping is not relaxation of the screen limit',
        base_worst=max(out,key=lambda x:x['base_excess_mV'])['pair'],
        R1k_worst=max(out,key=lambda x:x['R1k_excess_mV'])['pair'],
        R1k_worst_excess_mV=max(x['R1k_excess_mV'] for x in out))


def compare():
    OUT.mkdir(parents=True,exist_ok=True)
    a,wa,ca=read_run(RUNS[0]);b,wb,cb=read_run(RUNS[1])
    old_cfg=json.loads((HERE/'generated/current_v2/measurement.json').read_text())
    new_cfg=json.loads((HERE/'generated/cinput_r1k_v1/measurement.json').read_text())
    assert a['native_effective_settings']==b['native_effective_settings']
    assert a['boundary_provenance']==b['boundary_provenance']
    common=[]
    for n in [PREFIX+'gnna',PREFIX+'gnnb',PREFIX+'gnndrv','xdut.gnn0']:
        x=a['source_peak_reproduction_diagnostic'][n];y=b['source_peak_reproduction_diagnostic'][n]
        rail=0. if n.endswith('gnnb') else .99
        common.append(dict(node=n,base_peak_V=x['measured_native_peak_v'],R1k_peak_V=y['measured_native_peak_v'],
            base_peak_ns=x['measured_native_time_s']*1e9,R1k_peak_ns=y['measured_native_time_s']*1e9,
            base_rail_excursion_mV=(x['measured_native_peak_v']-rail)*1e3,
            R1k_rail_excursion_mV=(y['measured_native_peak_v']-rail)*1e3,
            peak_change_mV=(y['measured_native_peak_v']-x['measured_native_peak_v'])*1e3,
            peak_time_change_ps=(y['measured_native_time_s']-x['measured_native_time_s'])*1e12))
    rows,screen_summary=screens(a,b,old_cfg,new_cfg,(wa,ca),(wb,cb))
    command=new_cfg['experiment']['load_diagnostic']['independent_command_time_s']
    rports={n:b['current_charge_trapezoids'][n] for n in [PREFIX+'r_cin:1',PREFIX+'r_cin:2']}
    old_gate_charge=sum(a['current_charge_trapezoids'][PREFIX+n+':2']['fault_signed_C'] for n in ['gnncn','gnncp'])
    new_gate_charge=sum(b['current_charge_trapezoids'][PREFIX+n+':2']['fault_signed_C'] for n in ['gnncn','gnncp'])
    tb=wb[:,0];i1=wb[:,cb[PREFIX+'r_cin:1']];i2=wb[:,cb[PREFIX+'r_cin:2']]
    ohm=wb[:,cb[PREFIX+'gnnb']]-wb[:,cb[PREFIX+'gnn_cg']]-1000*i1
    energy_a=-.99*a['current_charge_trapezoids']['vvdd:1']['signed_C']
    energy_b=-.99*b['current_charge_trapezoids']['vvdd:1']['signed_C']
    full_rec=b['native_exports'][0]
    full_path=ROOT/'output/managed_execution/runs'/RUNS[1]/'collected/derived'/full_rec['file']
    full_raw=gzip.decompress(full_path.read_bytes())
    assert hashlib.sha256(full_raw).hexdigest()==full_rec['uncompressed_sha256']
    full=np.frombuffer(full_raw,dtype='<f8').reshape((-1,len(full_rec['columns'])))
    fi={n:i for i,n in enumerate(full_rec['columns'])}
    full_i=full[:,fi[PREFIX+'r_cin:1']];full_j=full[:,fi[PREFIX+'r_cin:2']]
    delay={}
    for n,d in [(PREFIX+'gnnb','rising'),(PREFIX+'gnndrv','falling'),('xdut.gnn0','falling'),
                ('xdut.xcdac.bn0','rising'),('xdut.xcdac.bp0','falling')]:
        x=edge(a,n,d);y=edge(b,n,d)
        delay[n]=dict(base_ns=x['estimated_time_s']*1e9,R1k_ns=y['estimated_time_s']*1e9,
                      change_ps=(y['estimated_time_s']-x['estimated_time_s'])*1e12)
    gate_input={}
    for label,r,w,c in [('base',a,wa,ca),('R1k',b,wb,cb)]:
        gate_sum=w[:,c[PREFIX+'gnncn:2']]+w[:,c[PREFIX+'gnncp:2']]
        j=int(np.argmax(gate_sum));gate_input[label]=dict(max_positive_gate_sum_A=float(gate_sum[j]),at_s=float(w[j,0]))
    summary=dict(base_analysis=RUNS[0],R1k_run=RUNS[1],scope='Local FF-cold replayed-boundary block experiment only',
        same_fault_window_s=[64e-9,a['last_native_time_s']],no_peak_alignment_or_time_shift=True,
        native_effective_settings_equal=True,external_PWL_provenance_equal=True,
        same_window_peaks=common,half_vdd_delays=delay,
        global_GNN0=dict(base=a['voltage_and_current_extrema']['xdut.gnn0'],R1k=b['voltage_and_current_extrema']['xdut.gnn0'],
            note='Same~1.006636V global maximum at45.37973ns exists in BOTH. Do not compare it to the65ns local peaks.'),
        new_gate_fault_range_V=[float(wb[:,cb[PREFIX+'gnn_cg']].min()),float(wb[:,cb[PREFIX+'gnn_cg']].max())],
        current_gate_input=gate_input,R_port_charge_native=rports,
        R_fault_charge_sum_C=rports[PREFIX+'r_cin:1']['fault_signed_C']+rports[PREFIX+'r_cin:2']['fault_signed_C'],
        R_full_charge_sum_C=rports[PREFIX+'r_cin:1']['signed_C']+rports[PREFIX+'r_cin:2']['signed_C'],
        R_Ohm_law_max_residual_V=float(np.max(np.abs(ohm))),R_port_sum_max_A=float(np.max(np.abs(i1+i2))),
        baseline_Cgate_fault_net_charge_C=old_gate_charge,R1k_Cgate_fault_net_charge_C=new_gate_charge,
        R1k_R_to_gate_charge_residual_C=rports[PREFIX+'r_cin:1']['fault_signed_C']-new_gate_charge,
        R_fault_dissipated_J=float(np.trapezoid(1000*i1*i1,tb)),
        R_full_dissipated_J=float(np.trapezoid(1000*full_i*full_i,full[:,0])),
        R_full_port_sum_max_A=float(np.max(np.abs(full_i+full_j))),
        R_full_native_charge_port1_C=float(np.trapezoid(full_i,full[:,0])),
        R_full_native_charge_port2_C=float(np.trapezoid(full_j,full[:,0])),
        KCL=dict(base_full_max_A=max(x['max_abs_a'] for x in a['node_kcl'].values()),
                 R1k_full_max_A=max(x['max_abs_a'] for x in b['node_kcl'].values()),
                 base_fault_max_A=max(x['fault_max_abs_a'] for x in a['node_kcl'].values()),
                 R1k_fault_max_A=max(x['fault_max_abs_a'] for x in b['node_kcl'].values()),new_gate=b['node_kcl'][PREFIX+'gnn_cg']),
        terminal_screen_summary=screen_summary,
        settling=dict(base=settling(a,wa,ca,command),R1k=settling(b,wb,cb,command)),
        energy=dict(same_interval_s=[0,a['last_native_time_s']],base_VDD_J=energy_a,R1k_VDD_J=energy_b,
                    change_J=energy_b-energy_a,relative_change=(energy_b-energy_a)/energy_a,
                    note='Partial ideal-VDD energy almost unchanged; small difference is not meaningful power optimization or whole-ADC power qualification'),
        original_warning_summary=dict(base=a['original_simulator_log'],R1k=b['original_simulator_log']),
        candidate_adoption_supported=False,acceptance_pass=None,
        next_step='Characterize a1.8V-rated T28 inverter/driver cell with the actual downstream/Rgate/reference load over retained0.81..0.99V supply range, including SS0.81V cold risk. Establish delay/stress before a driver-chain replacement; do not continue blind shared-R increases. No new candidate generated.')
    (OUT/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    figures(a,b,wa,ca,wb,cb,rows,summary)
    print(json.dumps({k:summary[k] for k in ['same_window_peaks','half_vdd_delays','terminal_screen_summary','baseline_Cgate_fault_net_charge_C','R1k_Cgate_fault_net_charge_C','energy']},indent=2))


def figures(a,b,wa,ca,wb,cb,rows,summary):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    blue='#246b9c';orange='#d36b36';green='#228778'
    environment='T28 FF / 0.99 V / -40 C | core driver & comparator, IO reference switches, full CDAC | ideal external rails/clocks | no noise, mismatch or PEX'
    fig,axes=plt.subplots(4,1,figsize=(11,9),sharex=True,layout='constrained')
    specs=[(PREFIX+'gnna','GNNA - VDD (mV)',(-6,52),.99),(PREFIX+'gnnb','B / CG (mV)',(-52,6),0),
           (PREFIX+'gnndrv','GNNDRV - VDD (mV)',(-6,75),.99),('xdut.gnn0','GNN0 - VDD (mV)',(-.5,1.4),.99)]
    for ax,(n,label,limits,rail) in zip(axes,specs):
        for w,c,name,color in [(wa,ca,'Base',blue),(wb,cb,'R1k',orange)]:
            t=w[:,0]*1e9;sel=(t>=65.235)&(t<=65.258)
            ax.plot(t[sel],(w[sel,c[n]]-rail)*1e3,label=name,color=color,lw=1.4)
        if n==PREFIX+'gnnb':
            t=wb[:,0]*1e9;sel=(t>=65.235)&(t<=65.258)
            ax.plot(t[sel],wb[sel,cb[PREFIX+'gnn_cg']]*1e3,label='R1k new CG',color=green,ls='--',lw=1.3)
        ax.set_ylim(*limits);ax.set_ylabel(label);ax.axhline(0,color='#777',lw=.7);ax.grid(alpha=.18);ax.legend(fontsize=8,loc='upper left')
    axes[-1].set_xlabel('Native simulation time (ns)');axes[-1].set_xlim(65.235,65.258)
    fig.suptitle('Common-input R1k: same-window rail excursion comparison',fontsize=14)
    fig.supxlabel(environment+'\n'
                   'The~1.006636 V global GNN0 peak at45.37973 ns is outside this window and exists in both versions.',fontsize=8)
    fig.savefig(OUT/'r1k_same_window_voltage.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True,layout='constrained')
    for w,c,label,color in [(wa,ca,'Base: two C-stage gates',blue),(wb,cb,'R1k: two C-stage gates',orange)]:
        t=w[:,0]*1e9;sel=(t>=65.237)&(t<=65.253)
        current=w[:,c[PREFIX+'gnncn:2']]+w[:,c[PREFIX+'gnncp:2']]
        axes[0].plot(t[sel],current[sel]*1e6,label=label,color=color,lw=1.4)
    t=wb[:,0]*1e9;sel=(t>=65.237)&(t<=65.253)
    for n,label,color in [(PREFIX+'r_cin:1','R port1',orange),(PREFIX+'r_cin:2','R port2',green)]:
        axes[1].plot(t[sel],wb[sel,cb[n]]*1e6,label=label,color=color,lw=1.3)
    for w,c,n,label,color in [(wa,ca,'kcl:'+PREFIX+'gnndrv','Base C KCL',blue),
          (wb,cb,'kcl:'+PREFIX+'gnndrv','R1k C KCL',orange),(wb,cb,'kcl:'+PREFIX+'gnn_cg','R1k CG KCL',green)]:
        t=w[:,0]*1e9;sel=(t>=65.237)&(t<=65.253)
        axes[2].plot(t[sel],w[sel,c[n]]*1e12,label=label,color=color,lw=1)
    for ax,label in zip(axes,['Gate current (uA)','R port current (uA)','KCL residual (pA)']):
        ax.set_ylabel(label);ax.grid(alpha=.18);ax.axhline(0,color='#777',lw=.7);ax.legend(fontsize=8,loc='upper left')
    axes[-1].set_xlabel('Native simulation time (ns)');axes[-1].set_xlim(65.237,65.253)
    fig.suptitle('R1k reshapes the gate-charge pulse; six-node current balance remains closed',fontsize=13)
    fig.supxlabel(environment+'\nCurrents positive into components; equal/opposite R-port charges. D/G/S/B totals do not identify intrinsic channel/capacitance fractions.',fontsize=8)
    fig.savefig(OUT/'r1k_current_kcl.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
    for node,target,color,label in [('xdut.xcdac.bn0','vrefp',blue,'BN0'),('xdut.xcdac.bp0','vrefn',orange,'BP0')]:
        for w,c,style,suffix in [(wa,ca,'-','Base'),(wb,cb,'--','R1k')]:
            t=w[:,0]*1e9;sel=t>=65.58;e=np.abs(w[:,c[node]]-w[:,c[target]])*1e3
            axes[0].semilogy(t[sel],e[sel],style,color=color,label=label+' '+suffix,lw=1.3)
    axes[0].axhline(1,color='#777',ls=':',lw=1,label='1 mV diagnostic')
    axes[0].set(xlabel='Native simulation time (ns)',ylabel='Absolute reference settling error (mV)',title='Same-window load settling',xlim=(65.58,65.9965))
    axes[0].grid(alpha=.18);axes[0].legend(fontsize=8)
    keys=['GNNCN:ds','GNNAN:ds','GNNBP:ds','GNNCP:gs','GNPCN:ds','GPNCP:ds','GPPCP:ds']
    chosen=[next(x for x in rows if x['pair']=='XDUT.XREF.XDRV0.'+k) for k in keys]
    pos=np.arange(len(chosen))
    axes[1].barh(pos-.17,[x['base_excess_mV'] for x in chosen],height=.32,color=blue,label='Base')
    axes[1].barh(pos+.17,[x['R1k_excess_mV'] for x in chosen],height=.32,color=orange,label='R1k')
    axes[1].set_yticks(pos,keys);axes[1].invert_yaxis();axes[1].set_xlabel('Beyond 0.99 V screen (mV)');axes[1].set_title('Selected full-history terminal stress')
    axes[1].grid(axis='x',alpha=.18);axes[1].legend(fontsize=8)
    fig.suptitle('Settling is nearly unchanged; remaining stress is distributed across the driver',fontsize=13)
    fig.supxlabel(environment+'\nLeft:1 mV diagnostic. Right: full0..65.9965 ns extrema; all228 pair records in CSV. No whole-ADC pass.',fontsize=8)
    fig.savefig(OUT/'r1k_settling_stress.png',dpi=170);plt.close(fig)


if __name__=='__main__':compare()
