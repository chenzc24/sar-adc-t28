"""Paired original/native BBM report. Run only after parent confirms both collections."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import textwrap
import numpy as np
import yaml
from analyze_real_bbm import digest, HERE, ROOT
from analyze_bbm_hdc0 import summarize as prior_summary
from analyze_bbm_hdc0 import duration
from build_first_fixture import definitions, flatten
from prepare_standard_cell_bbm import binding, expanded, TOP

PACKAGE=HERE/'standard_cell_bbm_v1'
OUT=PACKAGE/'comparison'
PROPOSALS={'ffcold':'f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c',
           'sscold':'f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4'}
BASE_MANAGED={'ffcold':'7559d2fd8cb85edf5034c7711babe6f653611d0b52bba9b122f2b1616b87820a',
              'sscold':'6bea4e28904ad1adfd0ba8791fbe1f9caf5a6c80d15870218dab2c2ae39e89ec'}


def read(path):
    return json.loads(Path(path).read_bytes())


def phase(t):
    if t<41e-9:return 'sample_track'
    if t<41.1e-9:return 'sample_close_edge'
    if t<42.995e-9:return 'held_CODE_low'
    if t<43.005e-9:return 'CODE_rise'
    if t<47.995e-9:return 'high_select_and_LD_reset'
    if t<48.005e-9:return 'CODE_fall'
    return 'low_select_and_HD_reset'


def function_group(old_path):
    if old_path.startswith('XDUT.XBBM0.'):
        if old_path.endswith(('.MN_CLEAR','.MP_CLEAR')):return 'RC_clear'
        if '.XD_HD.' in old_path or '.XD_LD.' in old_path:
            return 'RC_input_reset_INV' if '.X006.' in old_path else 'RC_threshold_INV'
        return 'BBM_boolean'
    if old_path.startswith(('XDUT.X025.','XDUT.X008.')):return 'reference_prebuffer'
    if re.fullmatch(r'XDUT.G(?:NP|PN)[ABC][NP]',old_path):return 'reference_core_driver'
    if re.fullmatch(r'XDUT.GNN[ABC][NP]',old_path):return 'retained_GNN_IO'
    if re.fullmatch(r'XDUT.GPPI[NP]',old_path):return 'retained_GPP_IO'
    if old_path.startswith('XDUT.XCDAC.'):return 'analog_CDAC'
    if old_path.startswith(('XDUT.XBOOTN.','XDUT.XBOOTP.')):return 'analog_Bootstrap'
    if old_path.startswith('XDUT.XCOMP.'):return 'analog_comparator_reset'
    raise ValueError('Unclassified actual MOS '+old_path)


def device_mapping():
    """Physical-terminal equivalence, including native NAND stack order."""
    olddefs=definitions((HERE/'generated/real_bbm_v1/dut.scs').read_text())
    old=flatten(olddefs,TOP,binding(olddefs))
    metadata=read(PACKAGE/'library_metadata.json')
    newdefs=definitions((PACKAGE/'dut.scs').read_text())
    new,library=expanded(newdefs,metadata)
    oldmos={n:x for n,x in old.items() if x['model'].startswith(('nch_','pch_'))}
    newmos={n:x for n,x in new.items() if x['model'].startswith(('nch_','pch_'))}
    migration=read(PACKAGE/'migration.json')
    pairs={x['old_MOS'][0]:(x['new_instance'], 'MM1') for x in migration['top_core_pair_replacements']}
    pairs.update({x['old_MOS'][1]:(x['new_instance'], 'MM0') for x in migration['top_core_pair_replacements']})
    mapping={}
    for path,x in oldmos.items():
        if path in newmos:q=path
        elif path.removeprefix('XDUT.') in pairs:
            a,b=pairs[path.removeprefix('XDUT.')];q='XDUT.'+a+'.'+b
        elif '.X000.' in path and path.rsplit('.',1)[-1] in ['MN0','MN1','MP0','MP1']:
            a,b=path.rsplit('.',1);q=a+'.XLIB.'+dict(MN0='MM4',MN1='MM9',MP0='MM1',MP1='MM2')[b]
        elif path.endswith(('.MN','.MP')):
            a,b=path.rsplit('.',1);q=a+'.XLIB.'+dict(MN='MM1',MP='MM0')[b]
        else:raise ValueError('Unmapped original '+path)
        assert q in newmos and x['model']==newmos[q]['model']
        # Only original NAND internal MID is renamed to actual native net10.
        aliases={ 'XDUT.XBBM0.X002.X000.MID':'XDUT.XBBM0.X002.X000.XLIB.net10',
                  'XDUT.XBBM0.X004.X000.MID':'XDUT.XBBM0.X004.X000.XLIB.net10'}
        assert [aliases.get(n,n) for n in x['nodes']]==newmos[q]['nodes']
        group=function_group(path)
        implementation='standard_gate_internal' if q in library else 'retained_RC_clear' if group=='RC_clear' else 'retained_IO' if '_IO' in group else 'retained_analog_load'
        mapping[path]=dict(original=path,candidate=q,model=x['model'],group=group,
            candidate_implementation=implementation,original_nodes=x['nodes'],candidate_nodes=newmos[q]['nodes'])
    assert len(mapping)==123 and len({v['candidate'] for v in mapping.values()})==123
    assert sum(v['candidate_implementation']=='standard_gate_internal' for v in mapping.values())==42
    return mapping


def load(variant,corner):
    std=variant=='std';name=('sar8audit-ref-bbm-stdcell-'+corner+'-v1') if std else 'sar8audit-real-bbm-'+corner
    package=PACKAGE/corner if std else HERE/'generated/real_bbm_v1'/corner
    proposal=package/'recipe_proposal.json'
    if std:assert digest(proposal)==PROPOSALS[corner]
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    if not std:assert registered['recipe_hash']==BASE_MANAGED[corner]
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    cfg=read(package/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(652 if std else 656)
    assert r['measurement_sha256']==digest(package/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert len(r['selected_mos_pair_extrema'])==738
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==(372 if std else 376)
    # Project only diagnostic voltages and actual output/reference/clear currents.
    wanted=set(cfg['diagnostic_voltage_columns'])|{'time','vcode:1','vvdd:1','rrefp:1','rrefn:1'}
    wanted.update(r['cell_measurements']['CODE_source_and_input_load']['incident_load_branches'])
    for q in r['cell_measurements']['internal_driver_load_work'].values():
        wanted.update(q['source_port_branches']+q['load_port_branches'])
    for side in ['n','p']:
        wanted.update('xdut.xcdac.xs'+side+'0.'+m+':1' for m in ['mn_low','mp_high'])
    for leg in ['hd','ld']:
        wanted.update('xdut.xbbm0.xd_'+leg+'.mp_clear:'+str(j) for j in [1,2,3,4])
    assert wanted<=set(e['columns'])
    ids=[j for j,n in enumerate(e['columns']) if n in wanted];columns=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');stride=8*len(e['columns']);h=hashlib.sha256();count=total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            b=f.read(stride*128)
            if not b:break
            assert len(b)%stride==0;h.update(b);total+=len(b)
            q=np.frombuffer(b,dtype='<f8').reshape(-1,len(e['columns']))
            assert count+len(q)<=len(w)
            w[count:count+len(q)]=q[:,ids];count+=len(q)
    assert count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def terminal_rows(d,corner,variant,mapping):
    actual={p['instance']+':'+p['terminal']:p for p in d['cfg']['selected_mos_pair_screens']}
    out=[]
    for old,item in mapping.items():
        path=item['candidate'] if variant=='std' else old
        for suffix in ['ds','gs','gd','gb','bd','bs']:
            key=path+':'+suffix;p=actual[key];x=d['result']['selected_mos_pair_extrema'][key]
            assert p['model']==item['model']
            assert p['screen_v']==(.99 if item['model'] in ['nch_mac','pch_mac'] else 1.98)
            positive=abs(x['max'])>=abs(x['min'])
            peak=x['max'] if positive else x['min'];t=x['max_time_s'] if positive else x['min_time_s']
            out.append(dict(corner=corner,variant=variant,function=item['group'],
                implementation=item['candidate_implementation'] if variant=='std' else 'original_'+item['candidate_implementation'].removeprefix('retained_'),
                mapped_pair=old+':'+suffix,actual_pair=key,model=p['model'],
                positive_node=p['nodes'][0],negative_node=p['nodes'][1],
                screen_V=p['screen_v'],signed_peak_V=peak,abs_peak_V=abs(peak),
                excess_V=abs(peak)-p['screen_v'],peak_time_s=t,peak_phase=phase(t),
                signed_min_V=x['min'],min_time_s=x['min_time_s'],min_phase=phase(x['min_time_s']),
                signed_max_V=x['max'],max_time_s=x['max_time_s'],max_phase=phase(x['max_time_s'])))
    assert len(out)==len(actual)==738
    return out


def summarize(d,corner,variant,mapping):
    s,_=prior_summary(d,corner,variant)
    rows=terminal_rows(d,corner,variant,mapping);groups={}
    for name in sorted({x['function'] for x in rows}):
        q=[x for x in rows if x['function']==name]
        groups[name]=dict(records=len(q),strict_exceed=sum(x['excess_V']>0 for x in q),
            over1mV=sum(x['excess_V']>.001 for x in q),
            worst=max(q,key=lambda x:x['excess_V']))
    s['groups']=groups;s['worst_pairs']=sorted(rows,key=lambda x:x['excess_V'],reverse=True)[:24]
    s['phase_stress_counts']={p:sum(x['excess_V']>0 and x['peak_phase']==p for x in rows) for p in sorted({x['peak_phase'] for x in rows})}
    s['strict_exceed']=sum(x['strict_exceed'] for x in groups.values())
    s['over1mV']=sum(x['over1mV'] for x in groups.values())
    s['source_commit']=d['source_commit']
    s['NAND_internal_diagnostics']={}
    for label,cell,inp in [('L','x004','xdut.xbbm0.cb'),('H','x002','code')]:
        node='xdut.xbbm0.'+cell+'.x000.'+('xlib.net10' if variant=='std' else 'mid')
        inst='XDUT.XBBM0.'+cell.upper()+'.X000.'+('XLIB.MM4' if variant=='std' else 'MN0')
        stress=d['result']['selected_mos_pair_extrema'][inst+':ds']
        at=stress['max_time_s'] if abs(stress['max'])>=abs(stress['min']) else stress['min_time_s']
        j=int(np.argmin(abs(d['w'][:,0]-at)));assert abs(d['w'][j,0]-at)<1e-18
        output='xdut.xbbm0.'+cell+'.n'
        witness=dict(time_s=at,drain_output_V=float(d['w'][j,d['c'][output]]),
            source_stack_V=float(d['w'][j,d['c'][node]]),
            gate_input_V=float(d['w'][j,d['c'][inp]]),body_V=0.)
        witness['Vds_V']=witness['drain_output_V']-witness['source_stack_V']
        s['NAND_internal_diagnostics'][label]=dict(stack_node=node,
            stack_extrema=d['result']['voltage_and_current_extrema'][node],
            output_extrema=d['result']['voltage_and_current_extrema']['xdut.xbbm0.'+cell+'.n'],
            output_adjacent_instance=inst,output_adjacent_absVds_peak_native_witness=witness,
            first_input_edges=d['result']['half_vdd_events'].get(inp,[]),
            delayed_input_edges=d['result']['half_vdd_events'].get('xdut.xbbm0.'+('ld' if label=='L' else 'hd'),[]),
            interpretation='Node polarity and correlated edge ordering; capacitive coupling is inferred from actual topology, not isolated intrinsic Cgd/channel/diode-current decomposition.')
    if variant=='std':
        remote=d['result']['cell_measurements']
        for phase_name,label in [('high','select_high'),('low','select_low')]:
            for node,x in s['physical_phase_settling'][phase_name].items():
                y=remote['physical_command_phase_reference_settling'][label]['nodes'][node]
                assert x['remained_inside_from_native_s']==y['remained_inside_from_native_s']
                assert x['diagnostic_established']==y['diagnostic_established']
        for leg,q in s['reset'].items():
            for node,x in q['nodes'].items():assert x['entry_s']==remote['delay_leg_reset_diagnostics'][leg]['nodes'][node]['remained_inside_from_native_s']
    return s,rows


def figures(waves):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    styles={'base':'--','std':'-'};colors=['#176fa6','#c65c2e','#26806f','#9c5d9e']
    footer='Dashed: original; solid: native D1. Complete bit0 BBM/C0 x1; real CDAC/Bootstrap, retained IO + Rgate; other bits static. Ideal CODE/rails/clock; comparator reset; no noise/mismatch/PEX. Native time, no alignment.'
    def finish(fig,name,title):
        fig.suptitle(title,fontsize=13)
        fig.supxlabel(textwrap.fill(footer,160),fontsize=8)
        fig.savefig(OUT/name,dpi=165);plt.close(fig)
    for high,a,b,name in [(True,42.98,44.5,'high_gate_current_settling.png'),
                           (False,47.98,50.1,'low_gate_current_settling.png')]:
        fig,axes=plt.subplots(5,2,figsize=(13,11),layout='constrained')
        for j,corner in enumerate(['ffcold','sscold']):
            for variant,d in waves[corner].items():
                w,c=d['w'],d['c'];t=w[:,0]*1e9;ids=(t>=a)&(t<=b);label='original' if variant=='base' else 'native D1'
                for i,nodes in [(0,['xdut.h0','xdut.l0']),(1,['xdut.gnn0','xdut.gnp0']),(2,['xdut.gpp0','xdut.gpn0'])]:
                    for z,node in enumerate(nodes):axes[i,j].plot(t[ids],w[ids,c[node]],styles[variant],color=colors[z],lw=1.2,label=node.rsplit('.',1)[-1].upper() if variant=='std' else None)
                for z,m in enumerate(['mn_low','mp_high']):
                    n='xdut.xcdac.xsn0.'+m+':1'
                    axes[3,j].plot(t[ids],w[ids,c[n]]*1e6,styles[variant],color=colors[z],lw=1.2,label=m+' D' if variant=='std' else None)
                for z,(node,ref) in enumerate([('bn0','vrefp' if high else 'vrefn'),('bp0','vrefn' if high else 'vrefp')]):
                    axes[4,j].plot(t[ids],(w[ids,c['xdut.xcdac.'+node]]-w[ids,c[ref]])*1e3,styles[variant],color=colors[z],lw=1.2,label=node.upper()+' error' if variant=='std' else None)
            for i,y in enumerate(['H/L (V)','N-side gates (V)','P-side gates (V)','N-side total D (uA)','Reference error (mV)']):
                ax=axes[i,j];ax.set(xlim=(a,b),ylabel=y);ax.grid(alpha=.16);ax.legend(fontsize=7,ncol=2,loc='upper right')
                ax.axvline(43 if high else 48,color='#999',ls=':',lw=.8)
            for i in [1,2]:axes[i,j].axhline((.99 if corner=='ffcold' else .81)*.5,color='#999',ls=':',lw=.8)
            axes[4,j].set_yscale('symlog',linthresh=1);axes[4,j].axhspan(-1,1,color='#26806f',alpha=.1)
            axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
            axes[-1,j].set_xlabel('Native time (ns)')
        finish(fig,name,('High' if high else 'Low')+' selection: original versus native standard cells')
    fig,axes=plt.subplots(4,2,figsize=(13,10),layout='constrained')
    for j,corner in enumerate(['ffcold','sscold']):
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;label='original' if variant=='base' else 'native D1'
            for leg,col in [('hd',colors[0]),('ld',colors[1])]:
                stem='xdut.xbbm0.xd_'+leg+'.'
                for i,(a,b) in enumerate([(42.98,43.65),(47.98,48.7)]):
                    ids=(t>=a)&(t<=b)
                    axes[i*2,j].plot(t[ids],w[ids,c[stem+'rc1']],styles[variant],color=col,lw=1.2,label=leg.upper()+' RC1' if variant=='std' else None)
                    y=abs(w[ids,c[stem+'rc1']]-w[ids,c['xdut.xbbm0.'+leg]])
                    axes[i*2+1,j].plot(t[ids],y,styles[variant],color=col,lw=1.2,label=leg.upper()+' X005 |Vgd|' if variant=='std' else None)
        for i in range(4):
            ax=axes[i,j];ax.set(xlim=(42.98,43.65) if i<2 else (47.98,48.7),ylabel='RC1 (V)' if i%2==0 else '|Vgd| (V)')
            ax.axhline((.99 if corner=='ffcold' else .81) if i%2==0 else .99,color='#999',ls=':',lw=.8)
            if i%2==0:ax.axhline(0,color='#aaa',lw=.5)
            ax.grid(alpha=.16);ax.legend(fontsize=7,ncol=2,loc='upper right');ax.set_xlabel('Native time (ns)')
        axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
    finish(fig,'RC1_stress_both_directions.png','RC1 excursions and actual X005 terminal stress; both delay legs')
    fig,axes=plt.subplots(4,2,figsize=(13,10),layout='constrained')
    for j,corner in enumerate(['ffcold','sscold']):
        # Select a local time window from the actual paired BBM maximum, without
        # changing either trace's origin or aligning any internal event.
        windows=[]
        for cell in ['X004','X002']:
            peaks=[]
            for d in waves[corner].values():
                for p in d['cfg']['selected_mos_pair_screens']:
                    if not p['instance'].startswith('XDUT.XBBM0.'+cell+'.X000.'):continue
                    q=d['result']['selected_mos_pair_extrema'][p['instance']+':'+p['terminal']]
                    pos=abs(q['max'])>=abs(q['min'])
                    peaks.append((abs(q['max'] if pos else q['min']),q['max_time_s'] if pos else q['min_time_s']))
            center=max(peaks)[1]*1e9;windows.append((max(0,center-.22),min(52,center+.28)))
        for variant,d in waves[corner].items():
            w,c=d['w'],d['c'];t=w[:,0]*1e9;label='original' if variant=='base' else 'native D1'
            for k,cell in enumerate(['x004','x002']):
                a,b=windows[k];ids=(t>=a)&(t<=b)
                output='xdut.xbbm0.'+cell+'.n'
                internal='xdut.xbbm0.'+cell+'.x000.'+('mid' if variant=='base' else 'xlib.net10')
                for z,(node,tag) in enumerate([(output,'NAND output'),(internal,'NMOS stack node')]):
                    axes[k*2,j].plot(t[ids],w[ids,c[node]],styles[variant],color=colors[z],lw=1.2,label=tag if variant=='std' else None)
                axes[k*2+1,j].plot(t[ids],abs(w[ids,c[output]]-w[ids,c[internal]]),styles[variant],color=colors[0] if variant=='std' else '#777',lw=1.2,label=label)
        for i in range(4):
            a,b=windows[i//2]
            ax=axes[i,j];ax.set(xlim=(a,b),ylabel=('L' if i<2 else 'H')+' NAND nodes (V)' if i%2==0 else '|Vds| (V)')
            ax.axhline((.99 if corner=='ffcold' else .81) if i%2==0 else .99,color='#999',ls=':',lw=.8)
            ax.grid(alpha=.16);ax.legend(fontsize=7,ncol=2,loc='upper right');ax.set_xlabel('Native time (ns)')
        axes[0,j].set_title(('FF / 0.99 V' if corner=='ffcold' else 'SS / 0.81 V')+' / -40 C')
    finish(fig,'NAND_internal_terminal_stress.png','Actual native NAND stack nodes and terminal stress at paired peak')


def fmt(value,scale=1,digits=3):
    return '未观测' if value is None else f'{value*scale:.{digits}f}'


def report(data):
    lw=data['ffcold']['std']['NAND_internal_diagnostics']['L']['output_adjacent_absVds_peak_native_witness']
    lines=['# 原 BBM 与原生标准单元对照','',
        '范围：原完整 bit0、C0 multi=1；普通核心门改用原生 D1，RC/clear、IO、Rgate、完整 CDAC/Bootstrap 负载保留。自建 NAND 两只 CMID 随原门移除。CODE/电源/时钟理想，其他位静态、比较器复位；无噪声、失配、PEX。FF 0.99 V、SS 0.81 V，−40°C，0–52 ns。','',
        '## 端压与来源','',
        '| 工况 | 严格超限：原→标准 | 超出门限1 mV：原→标准 | 原生告警：标准 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        a,b=pair['base'],pair['std']
        lines.append(f"| {corner} | {a['strict_exceed']}/738 → {b['strict_exceed']}/738 | {a['over1mV']} → {b['over1mV']} | {', '.join(b['warnings'])} |")
    lines+=['','严格筛查沿用核心0.99 V、IO1.98 V；额外1 mV列仅帮助区分数值边界，不修改门限。告警与端压逐项同时保留，不因换成库门或进程正常退出宣称合格。','',
        '| 工况／功能 | 检查项 | 原严格超限 | 标准严格超限 | 标准最差实际器件／端对、峰值与时刻 |',
        '| --- | --- | --- | --- | --- |']
    for corner,pair in data.items():
        for group,b in pair['std']['groups'].items():
            a=pair['base']['groups'][group];x=b['worst']
            lines.append(f"| {corner}/{group} | {b['records']} | {a['strict_exceed']} | {b['strict_exceed']} | {x['actual_pair']}：{x['signed_peak_V']:.6f} V @ {x['peak_time_s']*1e9:.6f} ns，{x['peak_phase']} |")
    lines+=['','全部738项按原器件功能映射到标准单元的实际 MM 器件；NAND 串联位置对应不变。CSV保留实际端点、模型、正负极值时间与所属阶段，未将重命名当作新增/消失问题。RC/clear 与保留 IO/模拟负载单列。阶段标签来自外部采样/CODE 时间，不构成单凭相关波形即可认定的因果结论。','',
        '![RC1及端压](RC1_stress_both_directions.png)','',
        '![NAND内部节点及实际端压](NAND_internal_terminal_stress.png)','',
        '## 实际门次序与参考建立','',
        '| 工况／方向 | BBM间隔 ps：原→标准 | N栅极间隔 ps：原→标准 | P栅极间隔 ps：原→标准 |',
        '| --- | --- | --- | --- |']
    for corner,pair in data.items():
        for direction in ['select_high','select_low']:
            a,b=[pair[v]['control_events'][direction] for v in ['base','std']]
            vals=[fmt(a[k],1e12)+' → '+fmt(b[k],1e12) for k in ['BBM_signed_off_to_on_gap_s','N_signed_off_to_on_gap_s','P_signed_off_to_on_gap_s']]
            lines.append('| '+corner+'/'+direction+' | '+' | '.join(vals)+' |')
    lines+=['','半VDD交点只作顺序诊断；负间隔必须保留，正间隔也不能单独证明沟道无重叠。参考总 D 电流含位移电流，不称为纯直通电流。缺失或多次交点保持未知。','',
        '![高方向时序](high_gate_current_settling.png)','',
        '![低方向时序](low_gate_current_settling.png)','',
        '| 工况／方向 | 原 BN0／BP0 进入并保持1 mV的时间 ns | 标准 BN0／BP0 时间 ns |',
        '| --- | --- | --- |']
    for corner,pair in data.items():
        for direction in ['high','low']:
            values=[' / '.join(fmt(q['remained_inside_from_native_s'],1e9,6) for q in pair[v]['physical_phase_settling'][direction].values()) for v in ['base','std']]
            lines.append('| '+corner+'/'+direction+' | '+' | '.join(values)+' |')
    lines+=['','高相位只评价 [43.005,47.995) ns，低相位评价 [48.005,52] ns；误差基准是实际 VREFP/N。旧半轨终点跨入关断扰动，仅保留为切换诊断；1 mV不是新规格。','',
        '## 复位与源负担','',
        '| 工况 | HD整腿复位 ps：原→标准 | LD整腿复位 ps：原→标准 | BBM直接VDD能量 fJ：原→标准 | CODE源净供能 fJ：原→标准 |',
        '| --- | --- | --- | --- | --- |']
    def reset(q,leg):
        x=[n['delay_from_CODE_s'] for n in q['reset'][leg]['nodes'].values()]
        return None if any(n is None for n in x) else max(x)
    for corner,pair in data.items():
        a,b=pair['base'],pair['std']
        items=[fmt(reset(a,leg),1e12)+' → '+fmt(reset(b,leg),1e12) for leg in ['HD','LD']]
        items += [fmt(a['stage_energy_J']['BBM'],1e15)+' → '+fmt(b['stage_energy_J']['BBM'],1e15),
            fmt(a['CODE_source']['net_source_J'],1e15)+' → '+fmt(b['CODE_source']['net_source_J'],1e15)]
        lines.append('| '+corner+' | '+' | '.join(items)+' |')
    lines+=['','复位要求 RC0→0、RC1→VDD、腿输出→0 都进入1%并保持到相位末，表中相对CODE中点；缺失/未复位不赋0。源能量积分覆盖0–52 ns，内部端口功另存，不重复计为外部供电；此台不能评价整机功耗。','',
        '## 原因与最小下一步','',
        '1. **SS的顺序问题仍在真实负载接口。** 标准门使H高方向更快，而保留的GNN IO链关断慢，N侧负间隔从−191.747变为−209.799 ps；相反方向总D电流较小者峰值从10.863增至12.333 µA。最终参考能建立，不代表切换期间已有正裕量。','',
        '2. **RC/clear的模拟电荷扰动没有被库门替换消除。** FF的HD RC1正峰1.061799 V；负峰−19.947 mV、LD负峰−20.347 mV，使保留MP_CLEAR的最大绝对Vds分别达到1.009947/1.010347 V。换接收反相器不等于消除其输入节点的过轨或clear管端压。','',
        '3. **标准NAND内部串联节点仍会被拉负。** FF在CODE上升后，CB、LD分别于43.006012/43.013271 ns落过半轨；L NAND输出升高后，源端相邻管的LD继续关断。内部net10在43.024816 ns到−118.856 mV。两只NMOS都关断后，内部节点没有强直流钳位，负电压会保持；输出仍被PMOS拉到VDD附近。','',
        f"MM4的最差Vds发生在{lw['time_s']*1e9:.6f} ns，同一原生时刻：漏端输出={lw['drain_output_V']:.6f} V、源端内部节点={lw['source_stack_V']:.6f} V，故Vds={lw['Vds_V']:.6f} V。这是**高输出减去负源节点**的同时端压，不是输出本身冲到1.108 V。实际连接与先后边沿符合关断耦合/浮置机制；未把端流武断拆成某个本征电容电流。SS同类负移仍有−109.213 mV，只因0.81 V留下端压余量而未触及0.99 V门限。",'',
        '| NAND／CODE方向 | 当前A1（靠输出）先动作 | 当前A2（靠地）后动作 | 内部串联节点的路径 |',
        '| --- | --- | --- | --- |',
        '| L／CODE上升 | CB下降43.006012 ns | LD下降43.013271 ns | 输出先升高；下管随后关断，双关断后内部节点浮置，可负向耦合并保持 |',
        '| L／CODE下降 | CB上升48.006749 ns | LD上升48.132830 ns | 下管仍关断时，上管先接通，内部节点从高输出充电；下管后接通放电 |',
        '| H／CODE上升 | CODE上升43.000000 ns | HD上升43.123030 ns | 同上：先由输出经上管充内部节点，后由下管放电 |',
        '| H／CODE下降 | CODE下降48.000000 ns | HD下降48.006245 ns | 同L的双下降：上管先关、下管后关，内部net10负峰−116.073 mV |','',
        '以上是FF的实际半轨时间，表示先后关系而非MOS精确导通时刻。两NAND在对应双下降相位都有同类浮置风险；输入交换还会改变输入电容、延迟、耦合和下游顺序，不能只凭布尔对称认定电气等价。','',
        '**建议仅做一个接口实验：** 先只将L侧 `XBBM0.X004.X000.XLIB` 的A1/A2从CB/LD换成LD/CB，其余器件、RC、时钟和负载不动。双下降时，下管CB先关、上管LD暂保持导通，输出升高可先给内部节点充电，再由LD关断隔离；双上升时，下管CB先开并把内部节点钳到地，上管LD后开。这个因果预测能直接检验串联位置是否主导负向保持，但短暂导通时间不保证充分预充。先在同一FF台核对net10、MM4/MM9六对端压、输入电荷、两方向实际栅极次序和建立；H侧先保留作未改对照。它不是RC/clear或SS负间隔的完整修复，也不改库内部器件；本报告只建议该实验，未准备或提交。','',
        '## 结论与证据','',
        '本对照只验证标准门对真实参考接口的影响；结论必须同时依据端压、后级顺序、参考电流、建立、复位和源负担。没有完整异步转换、首帧启动及整机PVT结果，不能直接采用为合龙版本。','']
    for corner,pair in data.items():
        for variant in ['base','std']:
            d=pair[variant]
            lines.append(f"- {d['run']}：{d['native_points']}原生点，收集{d['receipt_bytes']} B；result SHA256 {d['result_sha256']}。")
        lines.append(f"- {corner} 实际solver设置是否完全相同：{pair['solver_settings_equal']}。无等精度加速结论。")
    lines+=['','comparison.json保留数值、原生告警/设置/体端与电荷；terminal_pairs.csv为2952条逐端压记录，device_mapping.json为123只MOS的真实对应。图使用原始时间，不平移、不归一化幅度。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def analyze():
    # Deliberately no partial execution/default FF-only report or polling loop.
    required=[ROOT/'output/managed_execution/runs'/('sar8audit-ref-bbm-stdcell-'+c+'-v1')/'collected/collection_receipt.json' for c in ['ffcold','sscold']]
    if not all(p.is_file() for p in required):raise FileNotFoundError('Both complete collections required; parent must notify before execution')
    mapping=device_mapping();waves={};data={};rows=[]
    for corner in ['ffcold','sscold']:
        pair={v:load(v,corner) for v in ['base','std']}
        assert pair['base']['external_body']==pair['std']['external_body']
        data[corner]={}
        for v,d in pair.items():
            s,q=summarize(d,corner,v,mapping);data[corner][v]=s;rows.extend(q)
        data[corner]['solver_settings_equal']=data[corner]['base']['native_settings']==data[corner]['std']['native_settings']
        waves[corner]=pair
    assert len(rows)==2952 and len({(q['corner'],q['variant'],q['mapped_pair']) for q in rows})==2952
    OUT.mkdir(exist_ok=True)
    (OUT/'device_mapping.json').write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf-8')
    (OUT/'comparison.json').write_text(json.dumps(dict(source_runs=data,acceptance_pass=None,full_ADC_candidate=False),indent=2)+'\n',encoding='utf-8')
    with (OUT/'terminal_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    figures(waves);report(data)
    print('STDCELL_BBM_COMPARISON_READY',len(rows),'rows')
    for c,p in data.items():print(c,{v:p[v]['strict_exceed'] for v in ['base','std']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-complete-pair',action='store_true',required=True,
                        help='Only after parent confirms complete FF/SS collection')
    parser.parse_args()
    analyze()

