"""Local receipt-verified comparison of unchanged-source and X020 library case."""
import json
import os
import re

import numpy as np
import yaml

import prepare_first_event as base
from review_both_result import read_current_run
from review_first_event_v1 import integrate_native

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN/'standard_cell_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {
    'original': ('sar8audit-ctrl-snload-both-v1','66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c'),
    'standard': ('sar8audit-ctrl-stdcell-ff-v1','593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20'),
}
COLORS = {'original':'#63778b','standard':'#c76b2b'}


def collected(run):
    folder = ROOT/'output/managed_execution/runs'/run/'collected'
    receipt = json.loads((folder/'collection_receipt.json').read_bytes())
    if receipt['skipped']:
        raise ValueError('Incomplete receipt')
    data = {}
    for item in receipt['files']:
        name = item['name']
        if name.startswith(('/','\\')) or '..' in name.replace('\\','/').split('/'):
            raise ValueError('Unsafe receipt member')
        p = folder/name
        if not p.exists() or base.digest(p.read_bytes())!=item['sha256']:
            p = p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        blob = p.read_bytes()
        if len(blob)!=item['bytes'] or base.digest(blob)!=item['sha256']:
            raise ValueError('Receipt SHA/size mismatch')
        data[name] = blob
    if sum(len(b) for b in data.values())!=receipt['total_bytes']:
        raise ValueError('Receipt byte total mismatch')
    return data


def original_energy(original):
    run = 'sar8audit-ctrl-both-stress-v1'
    expected = '21e0940f7afc08f8d054056ca7f3f5eb70e4fdeb054909716780e11e131c82d0'
    data = collected(run)
    record = yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
    recipe = record['recipe']
    if (record['recipe_hash']!=expected or
            base.digest(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode())!=expected):
        raise ValueError('Completed reanalysis identity differs')
    for item in recipe['files']:
        if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:
            raise ValueError('Reanalysis input changed')
    state = json.loads(data['analysis.state.json'])
    r = json.loads(data['derived/result.json'])
    provenance = json.loads(data['derived/source_readonly_provenance.json'])
    if (state['status']!='complete' or state['exit_code']!=0 or r['simulation_started']
            or not r['source_completed_simulation_verified'] or not r['source_END_scanned']
            or r['source_run_id']!=RUNS['original'][0] or r['source_recipe_hash']!=RUNS['original'][1]
            or r['raw_sha256']!=original['raw_sha256']
            or not provenance['source_readonly_checks_pass']
            or provenance['raw_stat_before']!=provenance['raw_stat_after']):
        raise ValueError('Completed reanalysis source/end/read-only evidence differs')
    return r['full_history_source_energy'],dict(run=run,recipe_sha256=expected,
        receipt_files=len(data),receipt_bytes=sum(len(b) for b in data.values()),source_raw_sha256=r['raw_sha256'])


def values(table,names,node):
    return np.zeros(len(table)) if node=='0' else table[:,names.index(node.lower())]


def duration(t,v,limit):
    """Piecewise-linear crossing estimate on actual native samples, not resampling."""
    intervals = []
    for i in range(len(t)-1):
        x,y = float(v[i]),float(v[i+1])
        cuts = [0.,1.]
        if x!=y:
            cuts += [(z-x)/(y-x) for z in [-limit,limit] if 0<(z-x)/(y-x)<1]
        cuts.sort()
        for a,z in zip(cuts,cuts[1:]):
            if abs(x+(y-x)*.5*(a+z))<=limit:
                continue
            start,end = float(t[i]+a*(t[i+1]-t[i])),float(t[i]+z*(t[i+1]-t[i]))
            peak = max(abs(x+(y-x)*a),abs(x+(y-x)*z))
            if intervals and abs(start-intervals[-1]['stop_s'])<1e-22:
                intervals[-1].update(stop_s=end,stop_native_bracket_s=[float(t[i]),float(t[i+1])],
                    sampled_peak_abs_v=max(peak,intervals[-1]['sampled_peak_abs_v']))
            else:
                intervals.append(dict(start_s=start,stop_s=end,
                    sampled_peak_abs_v=peak,
                    start_native_bracket_s=[float(t[i]),float(t[i+1])],stop_native_bracket_s=[float(t[i]),float(t[i+1])]))
    return dict(limit_abs_v=limit,total_linear_crossing_s=sum(d['stop_s']-d['start_s'] for d in intervals),
        longest_linear_crossing_s=max([d['stop_s']-d['start_s'] for d in intervals]+[0.]),
        intervals=intervals,native_over_limit_points=int((np.abs(v)>limit).sum()),
        scope_start_s=float(t[0]),scope_stop_s=float(t[-1]),
        policy='Native sample crossings interpolated linearly; brackets retained. Not full-history duration if crossing lies outside exported diagnostic window.')


def charge(table,names,terms,start,stop):
    tt,q = integrate_native(table[:,0],table[:,[names.index(n) for n in terms]],start,stop)
    return dict(requested_start_s=start,requested_stop_s=stop,first_native_s=float(tt[0]),last_native_s=float(tt[-1]),
        into_node_c=dict(zip(terms,map(float,q[-1]))),sum_all_terminal_exchange_c=float(q[-1].sum()),
        convention='Minus native trapezoid terminal integral; positive into node. KCL sum is not additional node stored charge.')


def snapshot(table,names,m,node,at):
    row = int(np.flatnonzero(table[:,0]==at)[0])
    terms = m['kcl_terms'][node]
    return dict(time_s=float(at),node=node,
        voltages_v={n:float(values(table,names,n)[row]) for n in
            [P+'live',P+'q1',P+'x020.n',P+'x020.x000.net10',P+'quiet',P+'x001.n']},
        currents_positive_out_a={s:float(table[row,names.index(s)]) for s in terms},
        KCL_sum_a=sum(float(table[row,names.index(s)]) for s in terms))


def main():
    assert abs(duration(np.array([0.,1.,2.]),np.array([0.,2.,0.]),1.)['total_linear_crossing_s']-1)<1e-12
    assert abs(duration(np.array([0.,1.]),np.array([2.,-2.]),1.)['total_linear_crossing_s']-.5)<1e-12
    data = {k:read_current_run(*v) for k,v in RUNS.items()}
    energy,energy_proof = original_energy(data['original'][2])
    report = dict(scope='FF0.99V/-40C native first-event conditional fixture only',cases={},
        original_energy_proof=energy_proof,qualification_pass=False,
        no_remote_operations=True,source_artifacts_unchanged=True,
        duration_policy='Only native diagnostic window40.8..41.59078565ns is available locally. Full-history extrema/first-last over witnesses are separate. Durations are bracketed linear estimates, not resampled traces.',
        numerical_band_policy='Exact0.99V screen unchanged. Amplitude bands describe size only; reltol is not a global waveform error bound. Repeated pairs such as VGS/VGB may be the same physical event.',
        implementation_policy='Whole unit changes foundry geometry/parasitics/stack and removes explicit old CMID; no single mechanism is isolated by old-vs-library replacement.')
    all_logs = {}
    for tag,(table,names,r,m,proof) in data.items():
        raw = collected(RUNS[tag][0])
        sim = json.loads(raw['simulation.state.json'])
        log = raw['spectre.out'].decode('utf-8',errors='replace')
        warnings = [line.strip() for line in log.splitlines() if 'WARNING (CMI-' in line]
        cmi_times = []
        warning_at = None
        for line in log.splitlines():
            match = re.search(r'Warning from spectre at time = ([0-9.eE+-]+) (ns|ps|us|ms|s)',line)
            if match:
                warning_at = float(match[1])*{'ns':1e-9,'ps':1e-12,'us':1e-6,'ms':1e-3,'s':1.}[match[2]]
            if 'WARNING (CMI-' in line:
                cmi_times.append(dict(time_s=warning_at,line=line.strip()))
        all_logs[tag] = warnings
        case = dict(proof=proof,initial_VDD_power_w=-r['initial_values']['vdd!']*r['initial_values']['vvdd:1'],
            native_effective_settings=sim['native']['effective_settings'],
            all_KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            simulation_seconds=sim['elapsed_seconds'],simulation_peak_rss_bytes=sim['peak_rss_bytes'],
            node_metrics={},source_energy=energy if tag=='original' else r['full_history_source_energy'],
            CMI=dict(codes=[s for s in proof['native_warning_codes'] if s.startswith('CMI')],
                displayed_lines=warnings,displayed_records=cmi_times,first_displayed_time_s=cmi_times[0]['time_s'],
                suppressed_warning_count=int(re.search(r'(\d+) warnings suppressed',log)[1]),
                limitation='Max5 warnings per code suppresses later instances. Printed microvolt early warnings are not the maximum stress; no absence-of-log pass inferred.'))
        for suffix in ['live','q1','x020.n','quiet','quiet_d','clock_reset','clock_q','xclock.rb','xd_quiet_d.rc0','xd_quiet_d.rc1']:
            node = P+suffix
            v = values(table,names,node)
            case['node_metrics'][suffix] = dict(full_history_extrema=r['voltage_and_current_extrema'][node],
                end_voltage_v=float(v[-1]),above_positive_rail=duration(table[:,0],v,.99),
                meaningful_rail_excursion=duration(table[:,0],v,.991),
                negative_excursion_1mV=duration(table[:,0],np.minimum(v,0),.001))
            maximum_at = r['voltage_and_current_extrema'][node]['max_time_s']
            case['node_metrics'][suffix]['positive_peak_rail_episode'] = next((d for d in
                case['node_metrics'][suffix]['above_positive_rail']['intervals'] if d['start_s']<=maximum_at<=d['stop_s']),None)
        close = base.edge_time(table[:,0],values(table,names,'xdut.sample_int'),.99,False)[0]
        case['sample_close_s'] = close
        case['edges'] = {}
        for node in ['xdut.sample_int',P+'live',P+'x020.n',P+'quiet',P+'quiet_d',P+'clock_q','xdut.cmp_clk']:
            case['edges'][node] = dict(rise_s=base.edge_time(table[:,0],values(table,names,node),.99,True),
                fall_s=base.edge_time(table[:,0],values(table,names,node),.99,False))
        case['QUIET_after_close_s'] = case['edges'][P+'quiet']['rise_s'][0]-close
        case['LIVE_after_close_s'] = case['edges'][P+'live']['rise_s'][0]-close
        if tag=='standard':
            case['NAND_stack_internal_initial_v'] = r['initial_values'][P+'x020.x000.net10']
            watched = m['standard_cell_experiment']['observed_mos']
            groups = {}
            for group in ['standard_cell','retained_core']:
                rows = []
                for instance,item in watched.items():
                    if item['group']!=group: continue
                    for pair,label in item['six_pair_labels'].items():
                        stress = r['full_history_voltage_stress'][label]
                        cfg = m['stress_voltage_pairs'][label]
                        rows.append(dict(instance=instance,pair=pair,full_history=stress,
                            positive_node=cfg['positive_node'],negative_node=cfg['negative_node'],
                            excess_v=max(0.,stress['max_abs_v']-.99)))
                rows.sort(key=lambda v:v['excess_v'],reverse=True)
                # All36 library pairs; worst pair per retained device for durations.
                selected = rows if group=='standard_cell' else list({v['instance']:v for v in reversed(rows)}.values())
                selected.sort(key=lambda v:v['excess_v'],reverse=True)
                if group!='standard_cell': selected=selected[:20]
                for item in selected:
                    v = values(table,names,item['positive_node'])-values(table,names,item['negative_node'])
                    item['window_duration'] = duration(table[:,0],v,.99)
                    item['duration_above_limit_plus1mV'] = duration(table[:,0],v,.991)
                    # Guard full/global vs local mismatch rather than invent coverage.
                    full = item['full_history']
                    item['all_reported_over_limit_witnesses_inside_window'] = bool(not full['over_limit_native_points'] or (
                        full['first_over_limit_s']>=table[0,0] and full['last_over_limit_s']<=table[-1,0]))
                    if (item['all_reported_over_limit_witnesses_inside_window'] and
                            item['window_duration']['native_over_limit_points']!=full['over_limit_native_points']):
                        raise ValueError('Local duration over-limit sample count differs from full-history proof')
                bounds = [0.,1.1e-7,1e-6,1e-3,1e-2,float('inf')]
                bands = [sum(a<v['excess_v']<=z for v in rows) for a,z in zip(bounds,bounds[1:])]
                groups[group] = dict(MOS=len({v['instance'] for v in rows}),pairs=len(rows),
                    failed_pairs=sum(v['excess_v']>0 for v in rows),
                    amplitude_bands=dict(zip(['0..0.11uV','0.11..1uV','1uV..1mV','1..10mV','above10mV'],bands)),
                    worst_pair=rows[0],selected_pair_details=selected)
            case['groups'] = groups
            snaps = {}
            for event,node in [('LIVE_minimum','LIVE'),('N_peak','X020.N'),('QUIET_minimum','QUIET'),('Q1_peak','Q1')]:
                v = values(table,names,P+node)
                i = int(v.argmin() if 'minimum' in event else v.argmax())
                snaps[event] = snapshot(table,names,m,'XDUT.XCTRL.XTIM.'+node,table[i,0])
            case['causal_snapshots'] = snaps
            case['LIVE_charge_to_minimum'] = charge(table,names,m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE'],41.075e-9,snaps['LIVE_minimum']['time_s'])
            case['QUIET_charge_to_minimum'] = charge(table,names,m['kcl_terms']['XDUT.XCTRL.XTIM.QUIET'],41.084e-9,snaps['QUIET_minimum']['time_s'])
            terms = m['kcl_terms']['XDUT.XCTRL.XTIM.X020.N']
            case['native_current_bindings'] = r['standard_cell_native_current_bindings']
        else:
            case['NAND_stack_internal_initial_v'] = r['initial_values'][P+'x020.x000.mid']
            terms = [P+s for s in ['x020.x000.mp1:1','x020.x000.mp0:1','x020.x000.mn0:1','x020.x001.mp:2','x020.x001.mn:2']]
        case['N_exchange_to_own_peak'] = charge(table,names,terms,41.079e-9,r['peak_snapshot']['time_s'])
        case['N_exchange_common_stop'] = charge(table,names,terms,41.079e-9,data['standard'][2]['peak_snapshot']['time_s'])
        for item in case['source_energy'].values():
            if item['first_time_s']!=0 or item['last_time_s']!=m['source_history_stop_s']:
                raise ValueError('Energy interval mismatch')
        case['five_source_net_work_j'] = sum(v['net_delivered_j'] for v in case['source_energy'].values())
        report['cases'][tag] = case
    a,b = report['cases']['original'],report['cases']['standard']
    if a['native_effective_settings']!=b['native_effective_settings']:
        raise ValueError('Native effective settings differ; explain before speed/electrical comparison')
    oldn,newn = [c['node_metrics']['x020.n']['full_history_extrema']['max'] for c in [a,b]]
    report['change'] = dict(N_peak_reduction_v=oldn-newn,N_overshoot_reduction_fraction=(oldn-newn)/(oldn-.99),
        QUIET_halfrail_advance_s=a['QUIET_after_close_s']-b['QUIET_after_close_s'],
        VDD_energy_reduction_fraction=1-b['source_energy']['VDD']['net_delivered_j']/a['source_energy']['VDD']['net_delivered_j'])
    report['next_single_variable'] = dict(
        action='Propose only: insert one existing PDK R0 primitive in series between actual LIVE driver and entire standard-NAND A1. Compare zero resistor versus one R0; keep standard cell internals/sizes, upstream devices, histories, sample window/closing edge and every other circuit unchanged.',
        hypothesis='Separate sensitivity to incident LIVE slew/negative feedthrough from whole-cell replacement; R isolates both A1 gate loads. It is not a guaranteed clamp or a whole-controller repair.',
        observe='Both sides of resistor, N, Q1 and QUIET over/undershoot; all changed-interface terminal pairs/KCL, native delay/slew, R0 loading and source work. Do not accept moving stress or truncating an edge.',
        not_submitted=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    (OUT/'native_CMI_excerpt.txt').write_text('\n\n'.join(k+'\n'+'\n'.join(v) for k,v in all_logs.items())+'\n',encoding='utf-8')
    figures(data,report)
    print(json.dumps(dict(change=report['change'],N_duration_ps={tag:c['node_metrics']['x020.n']['above_positive_rail']['total_linear_crossing_s']*1e12 for tag,c in report['cases'].items()},
        groups={k:{s:v[s] for s in ['MOS','pairs','failed_pairs','amplitude_bands']} for k,v in b['groups'].items()}),indent=2))


def figures(data,report):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    note = 'FF | 0.99 V | -40 C | native first event | ideal external supply/clock | no noise, mismatch or PEX'
    def lines(ax,node,scale=1.,offset=0.):
        for tag,(table,names,*_) in data.items():
            ax.plot(table[:,0]*1e9,(values(table,names,node)-offset)*scale,color=COLORS[tag],
                    ls='--' if tag=='original' else '-',lw=1.5,label=tag)
    def finish(fig,name,title):
        for ax in fig.axes:
            ax.grid(alpha=.18);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
        fig.suptitle(title,fontsize=13)
        fig.supxlabel(note,fontsize=8)
        fig.savefig(OUT/name,dpi=165);plt.close(fig)
    fig,axes = plt.subplots(4,1,sharex=True,figsize=(10,8.6),layout='constrained')
    for ax,node,title in zip(axes,['xdut.sample_int',P+'live',P+'x020.n',P+'quiet'],
        ['Sample closing waveform','LIVE: original upstream driver','N: NAND output','QUIET: inverter output and real load']):
        lines(ax,node);ax.axhline(0,color='#888',lw=.7);ax.axhline(.99,color='#888',lw=.8,ls=':')
        ax.axvline(report['cases']['standard']['sample_close_s']*1e9,color='#888',lw=.8,ls=':')
        ax.set(ylabel='V',title=title)
    axes[0].legend(ncol=2,loc='upper right')
    axes[2].set_ylim(-.03,1.13)
    for tag in data:
        v = report['cases'][tag]['node_metrics']['x020.n']['full_history_extrema']
        axes[2].plot(v['max_time_s']*1e9,v['max'],'o',ms=4,color=COLORS[tag])
        axes[2].annotate('%.2f mV above VDD'%((v['max']-.99)*1e3),
            (v['max_time_s']*1e9,v['max']),xytext=(75,-7 if tag=='original' else -30),
            textcoords='offset points',fontsize=9,color=COLORS[tag],arrowprops=dict(arrowstyle='-',color=COLORS[tag],lw=.7))
    axes[-1].set(xlim=(41.055,41.14),xlabel='Time (ns)')
    finish(fig,'timing_comparison.png','Whole-X020 replacement: smaller N peak, earlier QUIET')

    fig,axes = plt.subplots(2,2,figsize=(11,7),layout='constrained')
    lines(axes[0,0],P+'x020.n',1e3,.99)
    axes[0,0].set(title='N above positive rail',ylabel='N - VDD (mV)',xlim=(41.078,41.097),ylim=(-8,95))
    lines(axes[0,1],P+'live',1e3)
    axes[0,1].set(title='Incident LIVE: low-level detail',ylabel='LIVE (mV)',xlim=(41.076,41.085),ylim=(-32,5))
    t,n,r,m,_ = data['standard']
    def currents(ax,terms_by_label,window):
        for label,terms in terms_by_label.items():
            curve = -sum(values(t,n,s) for s in terms)*1e6
            ax.plot(t[:,0]*1e9,curve,label=label,lw=1.25)
        ax.set(xlim=window,ylabel='Into node (uA)',xlabel='Time (ns)');ax.legend(fontsize=8)
    currents(axes[1,0],{'NAND PM(A1) drain':[P+'x020.x000.mm1:1'],
        'Upper NM(A1) drain':[P+'x020.x000.mm4:1'],
        'Other PM(A2) drain':[P+'x020.x000.mm2:1'],
        'INV gate loads':[P+'x020.x001.mm0:2',P+'x020.x001.mm1:2']},(41.079,41.091))
    axes[1,0].set_title('Standard case: N terminal exchange')
    currents(axes[1,1],{'Original driver PM drain':[P+'x001.x001.mp:1'],
        'Original driver NM drain':[P+'x001.x001.mn:1'],
        'Library A1 gate loads':[P+'x020.x000.mm4:2',P+'x020.x000.mm1:2']},(41.076,41.08235))
    axes[1,1].set_title('Standard case: LIVE terminal exchange')
    axes[1,1].set_ylim(-20,20)
    for ax in axes.flat: ax.axhline(0,color='#777',lw=.7)
    axes[0,0].legend(fontsize=9);axes[0,1].legend(fontsize=9)
    finish(fig,'N_and_LIVE_exchange.png','N injection and upstream LIVE undershoot are distinct events')

    fig,axes = plt.subplots(2,2,figsize=(11,7),layout='constrained')
    lines(axes[0,0],P+'quiet',1e3)
    axes[0,0].set(title='QUIET: low-level detail',ylabel='QUIET (mV)',xlim=(41.081,41.098),ylim=(-30,6))
    terms = m['kcl_terms']['XDUT.XCTRL.XTIM.QUIET']
    inv = [P+'x020.x001.mm1:1',P+'x020.x001.mm0:1']
    currents(axes[0,1],{'INV NM total drain':[inv[0]],'INV PM total drain':[inv[1]],
        'All retained loads':[s for s in terms if s not in inv]},(41.084,41.0886))
    axes[0,1].set_title('Standard case: QUIET terminal exchange')
    axes[0,1].set_ylim(-25,40)
    for tag,(table,names,*_) in data.items():
        for node,offset,color,label in [('clock_reset',.99,'#7d668c','RESET - VDD'),('xclock.rb',0.,'#287c8e','RB')]:
            axes[1,0].plot(table[:,0]*1e9,(values(table,names,P+node)-offset)*1e3,
                color=color,ls='--' if tag=='original' else '-',lw=1.2,label=tag+' '+label)
    axes[1,0].set(title='Retained SR/reset: nearly unchanged excursions',ylabel='Rail excursion (mV)',xlim=(41.065,41.105),ylim=(-29,28),xlabel='Time (ns)')
    lines(axes[1,1],P+'xd_quiet_d.rc1',1e3,.99)
    axes[1,1].set(title='Retained RC1 interface',ylabel='RC1 - VDD (mV)',xlim=(41.08,41.2),xlabel='Time (ns)')
    for ax in axes.flat: ax.axhline(0,color='#777',lw=.7)
    axes[0,0].legend(fontsize=9);axes[1,0].legend(fontsize=7,ncol=2);axes[1,1].legend(fontsize=9)
    finish(fig,'remaining_interfaces.png','Output undershoot and retained interfaces remain to be resolved')


if __name__=='__main__':
    main()
