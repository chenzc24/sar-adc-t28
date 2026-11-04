"""Local receipt-verified FF/SS storage report; never connects or simulates."""
from __future__ import annotations
import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct

import numpy as np
import yaml

import prepare_standard_cell_full as prepare
from review_standard_cell_full_result import receipt_files,verify_wave,summarize

OWN,ROOT=prepare.OWN,prepare.ROOT
OUT=OWN/'standard_cell_storage_v2/results'
FAST=OWN/'standard_cell_storage_fastanalysis_v1'
CASES={'ff':('sar8audit-ctrl-storage-ff-v2-fastanalysis-v1',FAST),
       'ss':('sar8audit-ctrl-storage-ss-v2q1-fastanalysis-v1',FAST/'ss_v2q1')}


def read(path):
    with Path(path).open(encoding='utf-8') as f:return json.load(f)


def identity(path):
    h=hashlib.sha256();size=0
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())


def canonical(recipe):
    return hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def record(run):
    x=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
    if canonical(x['recipe'])!=x['recipe_hash']:raise ValueError('Canonical managed recipe changed')
    for item in x['recipe']['files']:
        if identity(ROOT/item['source'])!=dict(bytes=item['bytes'],sha256=item['sha256']):
            raise ValueError('Frozen registered input changed: '+item['name'])
    return x


def load(tag):
    run,package=CASES[tag];rec=record(run);source_id=rec['recipe']['source']['run_id'];src=record(source_id)
    if rec['recipe'].get('kind')!='analysis_only' or rec['recipe']['source']['recipe_hash']!=src['recipe_hash']:
        raise ValueError('Analysis-only source identity differs')
    freeze=read(package/'freeze.json')
    if identity(package/'recipe.suggested.yaml')['sha256']!=freeze['recipe_file_sha256']:
        raise ValueError('Frozen authored analysis recipe differs')
    folder=ROOT/'output/managed_execution/runs'/run/'collected';receipt,files=receipt_files(folder)
    if receipt['status']['registered']['recipe_hash']!=rec['recipe_hash']:raise ValueError('Wrong collected managed run')
    state=read(files['analysis.state.json'])
    if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Source analysis not complete')
    r=read(files['derived/result.json']);prov=read(files['source_provenance.json'])
    if (r['analysis_kind']!='analysis_only_exact_completed_source_reuse' or r['simulation_started'] is not False
            or not r['source_raw_unchanged'] or not r['native_PSF_END'] or r['missing_required_signals']):
        raise ValueError('Invalid completed-source reuse/native END evidence')
    if r['source_run_id']!=source_id or r['source_recipe_hash']!=src['recipe_hash']:
        raise ValueError('Result source binding differs')
    for key in ['run_id','recipe_hash','simulation_state_sha256']:
        if r['source_provenance'][key]!=prov[key]:raise ValueError('Managed source provenance differs')
    src_files={x['name']:x for x in src['recipe']['files']}
    cfg=read(ROOT/src_files['measurement.json']['source'])
    if r['measurement_sha256']!=src_files['measurement.json']['sha256']:raise ValueError('Wrong measurement hash')
    if set(cfg['voltage_saves'])|set(cfg['current_saves']) and not {n.lower() for n in cfg['voltage_saves']+cfg['current_saves']}<=set(r['trace_bindings']):
        raise ValueError('Required native voltage/current bindings missing')
    if r['KCL_coverage']['status']!='unmeasured' or r['KCL_coverage']['whole_fixture_KCL_pass'] is not None or r['node_kcl']:
        raise ValueError('Unexpected complete KCL claim')
    for name,key in [('source_spectre.out','source_spectre.out'),('source_logStatus','source_logStatus')]:
        if identity(files['derived/'+name])!=r['original_native_logs'][key]:raise ValueError('Original native log identity differs')
    log=files['derived/source_spectre.out'].read_text()
    if not re.search(r'\b0 errors\b',log) or not re.search(r'\btran_first\s+PASS\b',files['derived/source_logStatus'].read_text()):
        raise ValueError('Original source zero-error footer/transient PASS absent')
    columns=read(files['derived/peak.columns.json'])
    wave=verify_wave(files['derived/peak.native.bin.gz'],columns,r,cfg)
    proof=dict(analysis_run=run,managed_analysis_recipe_sha256=rec['recipe_hash'],
        authored_analysis_recipe_file_sha256=freeze['recipe_file_sha256'],native_source_run=source_id,
        source_managed_recipe_sha256=src['recipe_hash'],source_simulation_state_sha256=prov['simulation_state_sha256'],
        receipt_sha256=identity(folder/'collection_receipt.json')['sha256'],receipt_bytes=receipt['total_bytes'],
        receipt_files=len(files),analysis_elapsed_s=state['elapsed_seconds'],analysis_peak_RSS_bytes=state['peak_rss_bytes'],
        original_native_footer_and_PASS=True,source_raw_sha256=r['raw_sha256'],wave=wave,
        fake_simulation=False,all_registered_and_received_hashes_verified=True)
    return r,cfg,proof,files,columns,log


def origin_maps(cfg):
    targets={o['name']:o for o in cfg['storage']['observers']}
    loads=read(OWN/'standard_cell_full_v1/load_boundaries.json')['boundaries']
    roots={b['replica']:b for b in loads};result={}
    for path,dev in cfg['observed_mos'].items():
        target=re.match(r'^XDUT\.X(U\d{2})\.',path)
        load=next((b for p,b in roots.items() if path.startswith(p+'.')),None)
        if target:
            o=targets[target[1]];suffix=path[len('XDUT.X'+target[1]):]
            group='DFF target' if o['kind']=='DFF' else 'SR target'
            detail='native library body' if '.XFF.' in path else 'reset adapter' if '.XRESET.' in path else 'SR gate network'
            result[path]=dict(group=group,detail=detail,fixture_instance=path,
                candidate_instance=o['source_instance']+suffix,context=target[1],test_only=False)
        elif load:
            group='RC delay/clear' if load['complete_RC_block_retained'] else 'DFF fanout' if load['source_master']=='sar8p_dffr' else 'Combinational fanout'
            result[path]=dict(group=group,detail='retained charge-clear MOS' if not dev['library'] else 'native library input load',
                fixture_instance=path,candidate_instance=load['source_load_instance']+path[len(load['replica']):],
                context=load['target'],test_only=False)
        elif re.match(r'^XDUT\.X[CDRS]U\d{2}\.',path):
            result[path]=dict(group='Test input driver',detail='independent CK/D/RST or R/S conditioner',
                fixture_instance=path,candidate_instance=None,context=None,test_only=True)
        else:raise ValueError('Unclassified actual MOS: '+path)
    # Check proposed full-candidate instance names, without claiming identical
    # boundary voltages or downstream loading between fixture and full ADC.
    candidate=(OWN/'standard_cell_full_v1/full_adc/dut.scs').read_text()
    cells=prepare.base.cells(candidate)
    native,_=prepare.expand_library(candidate,'sar_adc8_join_r4',read(OWN/'standard_cell_full_v1/library_probe.json'),
                                   {p:p for p in prepare.header(cells['sar_adc8_join_r4'])})
    for path,o in result.items():
        if o['candidate_instance'] is not None and o['candidate_instance'] not in native:
            raise ValueError('Candidate instance mapping does not exist: '+o['candidate_instance'])
    return result


def classify(r,cfg,origins):
    groups={};rows=[]
    for label,pair in r['full_history_voltage_stress'].items():
        path,terminal=label.rsplit('_',1);o=origins[path]
        g=groups.setdefault(o['group'],dict(pairs=0,strict_gt0=0,diagnostic_gt1mV=0,worst_excess_v=0.))
        excess=pair['max_abs_v']-pair['limit_abs_v'];strict=excess>0
        if strict!=bool(pair['over_limit_native_points']):raise ValueError('Native strict-screen count inconsistency')
        g['pairs']+=1;g['strict_gt0']+=int(strict);g['diagnostic_gt1mV']+=int(excess>1e-3)
        g['worst_excess_v']=max(g['worst_excess_v'],excess)
        if strict:
            rows.append(dict(**o,pair=terminal,model=cfg['observed_mos'][path]['model'],
                native_library=cfg['observed_mos'][path]['library'],limit_v=pair['limit_abs_v'],
                peak_abs_v=pair['max_abs_v'],excess_v=excess,diagnostic_gt1mV=excess>1e-3,
                peak_time_s=pair['max_abs_time_s'],first_over_s=pair['first_over_limit_s'],
                last_over_s=pair['last_over_limit_s'],over_native_points=pair['over_limit_native_points'],
                positive_node=cfg['stress_voltage_pairs'][label]['positive_node'],
                negative_node=cfg['stress_voltage_pairs'][label]['negative_node']))
    rows.sort(key=lambda x:x['excess_v'],reverse=True)
    if sum(g['pairs'] for g in groups.values())!=11220:raise ValueError('Physical coverage incomplete')
    return groups,rows


def selected_wave(path,columns,r,cfg):
    observers=cfg['storage']['observers'];wanted=['time','vdd!','ff_ck','ff_d','ff_rst','sr_r','sr_s']
    for o in observers:
        for key in (['Q','QB','R','S'] if o['kind']=='SR' else ['Q']):wanted.append(o[key].lower())
        if o['name']=='U19':wanted += [o[k].lower() for k in ['CK','D','RST','CDN']]
    wanted=list(dict.fromkeys(wanted));indices=[columns['names'].index(n) for n in wanted]
    table=np.empty((r['diagnostic_points'],len(wanted)),dtype='<f8');pack=struct.Struct('<'+'d'*len(columns['names']))
    with gzip.open(path,'rb') as f:
        i=0
        while True:
            blob=f.read(pack.size)
            if not blob:break
            row=pack.unpack(blob);table[i,:]=[row[j] for j in indices];i+=1
    if i!=len(table):raise ValueError('Plot extraction count differs')
    return table,wanted


def focus(r,cfg,table,names):
    dev='XDUT.XU19.XFF.MM64';pair=r['full_history_voltage_stress'][dev+'_VDS'];t=pair['max_abs_time_s']
    hits=np.flatnonzero(table[:,0]==t)
    if len(hits)!=1:raise ValueError('Worst-event original timestamp not in returned wave')
    row=table[int(hits[0])];o=next(o for o in cfg['storage']['observers'] if o['name']=='U19')
    values={key:float(row[names.index(o[key].lower())]) for key in ['CK','D','RST','CDN','Q']}
    phase=next(p for p in cfg['storage']['DFF_phases'] if p['start_s']<=t<p['stop_s'])
    previous=cfg['storage']['DFF_phases'][max(0,phase['index']-1)]
    direction=(1 if phase['CK'] else -1) if phase['CK']!=previous['CK'] else None
    ck=[e for e in r['storage_observations']['events'][o['CK'].lower()] if e['direction']==direction
        and phase['start_s']-.1e-9<e['time_s']<phase['start_s']+.3e-9] if direction else []
    return dict(instance=dev,candidate_instance='XDUT.XREF.XSTORE6.XFF.MM64',pair='VDS',
        max_abs_v=pair['max_abs_v'],time_s=t,excess_v=pair['max_abs_v']-pair['limit_abs_v'],
        physical_nodes=dict(zip(['D','G','S','B'],cfg['observed_mos'][dev]['nodes'])),
        exact_joint_D_v=None,exact_joint_S_v=None,exact_joint_G_v=None,exact_B_v=0.,
        joint_node_status='D/S/G internal histories absent from135 returned voltage columns; unknown pending source-bound targeted export. Independent node extrema are not combined.',
        exact_returned_inputs_at_peak_v=values,phase=phase,actual_phase_CK_edge=ck,actual_phase_CK_direction=direction,
        first_over_native_s=pair['first_over_limit_s'],last_over_native_s=pair['last_over_limit_s'],
        duration_status='First/last native witnesses are not continuous duration; target export will integrate joint waveform threshold crossings.')


def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        if rows:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        else:f.write('No records.\n')


def plots(dest,tag,r,cfg,data,names,groups,focus_record):
    os.environ.setdefault('MPLCONFIGDIR',str(OUT/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    t=data[:,0]*1e9;vdd=float(data[0,names.index('vdd!')])
    get=lambda n:data[:,names.index(n.lower())]
    obs={o['name']:o for o in cfg['storage']['observers']};dff=obs['U19']
    expected=lambda phases:np.array([next((p['Q'] for p in phases if p['start_s']<=x<p['stop_s']),phases[-1]['Q']) for x in data[:,0]])*vdd
    footer='%s %.2f V / -40 C | T28 native library SPICE | ideal supply/commands | no noise, mismatch, PEX | immediate input load only'%(tag.upper(),vdd)
    fig,axes=plt.subplots(4,2,sharex=True,figsize=(12,8.3),layout='constrained')
    for row,key in enumerate(['R','S','Q','QB']):
        ax=axes[row,0]
        for name,color,label in [('U00','#326b9c','clock SR'),('U17','#c36b30','request SR')]:
            ax.plot(t,get(obs[name][key]),lw=1.1,color=color,label=label)
        if key in ['Q','QB']:
            target=expected(cfg['storage']['SR_phases']);target=target if key=='Q' else vdd-target
            ax.plot(t,target,'--',lw=.85,color='#444444',label='contract')
        ax.set_ylabel('SR '+key+' (V)')
    axes[0,0].legend(fontsize=8,ncol=2,loc='upper right');axes[2,0].legend(fontsize=8,ncol=3,loc='upper right')
    for row,key in enumerate(['CK','D','RST','Q']):
        ax=axes[row,1]
        if key=='Q':
            for o in cfg['storage']['observers']:
                if o['kind']=='DFF':ax.plot(t,get(o['Q']),color='#aab3bb',alpha=.22,lw=.65)
            ax.plot(t,expected(cfg['storage']['DFF_phases']),'--',color='#444444',lw=.85,label='contract')
        ax.plot(t,get(dff[key]),color='#c36b30',lw=1.1,label='U19 actual')
        ax.set_ylabel('DFF '+key+' (V)');ax.axvline(13,color='#8b8991',ls=':',lw=.75)
    axes[3,1].legend(fontsize=8,ncol=2,loc='upper right')
    for ax in axes.flat:ax.set_xlim(0,20);ax.set_ylim(-.08,vdd+.12);ax.grid(alpha=.18)
    axes[-1,0].set_xlabel('Original time (ns)');axes[-1,1].set_xlabel('Original time (ns)')
    fig.suptitle(tag.upper()+': SR and DFF native timing versus state contract',fontsize=14)
    fig.supxlabel(footer,fontsize=8);fig.savefig(dest/'timing.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(5,2,sharex='col',figsize=(11.5,8.5),layout='constrained')
    peak_ns=focus_record['time_s']*1e9
    for col,(start,stop,title) in enumerate([(peak_ns-.05,peak_ns+.05,'MM64 maximum VDS event'),(12.98,13.10,'Clock rise + reset assertion')]):
        for row,key in enumerate(['CK','D','RST','CDN','Q']):
            ax=axes[row,col];ax.plot(t,get(dff[key]),color='#326b9c',lw=1.3)
            if key=='Q':ax.plot(t,expected(cfg['storage']['DFF_phases']),color='#444444',ls='--',lw=1,label='phase contract')
            if col==0:ax.axvline(focus_record['time_s']*1e9,color='#b34c4c',ls=':',lw=.9)
            ax.set(xlim=(start,stop),ylim=(-.07,vdd+.09),ylabel=key+' (V)');ax.grid(alpha=.2)
        axes[0,col].set_title(title,fontsize=11);axes[-1,col].set_xlabel('Original time (ns)')
    fig.suptitle(tag.upper()+': U19 inputs and Q around the two review events',fontsize=13)
    fig.supxlabel(footer+'\nRed marker: simultaneous |VDS|=%.6f V; internal D/S waveforms not in this return'%focus_record['max_abs_v'],fontsize=8)
    fig.savefig(dest/'event_zoom.png',dpi=175);plt.close(fig)
    labels=list(groups);x=np.arange(len(labels));fig,axes=plt.subplots(1,2,figsize=(12,4.9),layout='constrained')
    axes[0].barh(x-.16,[groups[k]['strict_gt0'] for k in labels],height=.30,label='strict excess > 0',color='#9b5555')
    axes[0].barh(x+.16,[groups[k]['diagnostic_gt1mV'] for k in labels],height=.30,label='diagnostic excess > 1 mV',color='#366e98')
    axes[0].set(yticks=x,yticklabels=labels,xlabel='Simultaneous terminal pairs',title='Counts; limit remains 0.99 V');axes[0].legend(fontsize=8)
    axes[1].barh(x,[groups[k]['worst_excess_v']*1e3 for k in labels],color='#9b5555')
    axes[1].set(yticks=x,yticklabels=labels,xlabel='Worst excess above 0.99 V (mV)',title='Amplitude by actual instance class')
    axes[0].set_xlim(0,max(1,max(g['strict_gt0'] for g in groups.values())*1.2))
    axes[1].set_xlim(0,max(.001,max(g['worst_excess_v']*1e3 for g in groups.values())*1.2))
    if not any(g['strict_gt0'] for g in groups.values()):
        for ax in axes:
            for yy in x:ax.text(0,yy,'  0',va='center',fontsize=9)
    for ax in axes:ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle(tag.upper()+(': physical terminal screening fails' if any(g['strict_gt0'] for g in groups.values()) else ': no terminal pair exceeds 0.99 V'),fontsize=13)
    fig.supxlabel(footer+'\nCounts include correlated pairs and replicated contexts; not independent failure mechanisms.',fontsize=8)
    fig.savefig(dest/'terminal_classes.png',dpi=180);plt.close(fig)


def review(tag,refresh=False):
    dest=OUT/tag
    if dest.exists() and not refresh:raise ValueError('Preserve completed review: '+str(dest))
    r,cfg,proof,files,columns,log=load(tag)
    summary,phases,_=summarize(r,cfg);origins=origin_maps(cfg);groups,terminal=classify(r,cfg,origins)
    wave,names=selected_wave(files['derived/peak.native.bin.gz'],columns,r,cfg)
    event=focus(r,cfg,wave,names);dest.mkdir(parents=True,exist_ok=refresh)
    total=len(terminal);large=sum(x['diagnostic_gt1mV'] for x in terminal)
    source_work={k:dict(net_delivered_j=v['net_delivered_j'],average_net_source_power_w=v['net_delivered_j']/20e-9,
                       peak_instantaneous_power_w=v['max_power_w']) for k,v in r['full_history_source_energy'].items()}
    peak_label=max(r['full_history_voltage_stress'],key=lambda k:r['full_history_voltage_stress'][k]['max_abs_v'])
    peak=r['full_history_voltage_stress'][peak_label]
    report=dict(proof=proof,summary=summary,physical_classes=groups,
        all_pair_peak=dict(label=peak_label,voltage_v=peak['max_abs_v'],time_s=peak['max_abs_time_s']),
        strict_failed_pairs=total,diagnostic_excess_gt1mV_pairs=large,
        diagnostic_excess_gt100mV_pairs=sum(x['excess_v']>.1 for x in terminal),
        terminal_instance_mapping_verified=True,MM64_focus=event,power=source_work,
        current_coverage=r['terminal_current_coverage'],KCL_coverage=r['KCL_coverage'],
        no_model_region_or_channel_current_inference=True,whole_ADC_qualified=None,
        source_fixture='Original core-reference baseline storage fixture; full source candidate includes real Rgate/CDAC but this isolated fixture truncates subsequent outputs.',
        warning_note='First MM45 CMI line at0.990003ns shows rounded Vgs=-990.001mV; not t=0 and not full-history worst. Native log suppresses repeated warnings.',
        MM45_comparison=dict(instance='XDUT.XU25.XFF.MM45',pair='VGS',
            native_log_first_warning_time_rounded_s=.990003e-9,native_log_first_voltage_rounded_v=-.990001,
            full_history=r['full_history_voltage_stress']['XDUT.XU25.XFF.MM45_VGS']),
        MM64_joint_D_S_G_unknown=True)
    (dest/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    write_csv(dest/'phases.csv',phases);write_csv(dest/'terminal_failures.csv',terminal)
    write_csv(dest/'terminal_classes.csv',[dict(group=k,**v) for k,v in groups.items()])
    plots(dest,tag,r,cfg,wave,names,groups,event)
    return report


def combined():
    cases={k:read(OUT/k/'summary.json') if (OUT/k/'summary.json').exists() else None for k in CASES}
    dual=cases['ff'] is not None and cases['ss'] is not None
    lines=['# 标准存储模块：FF／SS结果','',
        '**当前结论：两角26个上下文状态检查通过；FF端压筛查未通过，SS无0.99V端对超限。仍是存储模块烟测，不是整机通过。**' if dual else '**当前结论：FF的26个上下文状态检查通过，端压筛查未通过。SS结果待回收。**','',
        '| 项目 | FF 0.99V／−40°C | SS 0.81V／−40°C |','| --- | --- | --- |']
    def cell(case,key):
        if case is None:return '待回收'
        if key=='points':return str(case['proof']['wave']['rows'])
        if key=='holds':
            gs=case['summary']['stable_holds'];return '%d／%d通过'%(sum(g['hold_pass_phases'] for g in gs.values()),sum(sum(g[k] for k in ['hold_pass_phases','hold_fail_phases','hold_unknown_phases']) for g in gs.values()))
        if key=='Q':return str(sum(g['extra_or_missing_Q_pattern_phases'] for g in case['summary']['stable_holds'].values()))
        if key=='strict':return '%d／11220'%case['strict_failed_pairs']
        if key=='diag':return str(case['diagnostic_excess_gt1mV_pairs'])
        if key=='peak':return '%.6f V'%case['all_pair_peak']['voltage_v']
        if key=='power':return '%.3f µW'% (case['power']['VVDD']['average_net_source_power_w']*1e6)
        if key=='delay':
            d=case['summary']['delays'];return '%.3f–%.3f ps'%(d['min_signed_s']*1e12,d['max_signed_s']*1e12)
    for label,key in [('完整原生点','points'),('稳定保持阶段','holds'),('额外／缺失Q沿阶段','Q'),('实际引脚→Q范围','delay'),('严格超限端对（超额>0）','strict'),('超额>1mV端对（仅诊断）','diag'),('最坏端压','peak'),('测试台VVDD净供能／20ns','power')]:
        lines.append('| %s | %s | %s |'%(label,cell(cases['ff'],key),cell(cases['ss'],key)))
    ff=cases['ff']
    if ff:
        ev=ff['MM64_focus'];delay=ff['summary']['delays'];values=ev['exact_returned_inputs_at_peak_v']
        lines += ['', '## FF：功能与电气应力分开看','',
          '两个SR、24个DFF的502个保持阶段全部满足本台10/90%VDD观察带；每阶段预期Q沿均匹配，复位重叠阶段未出现额外半轨Q翻转。此结论不替代任意偏斜、setup/hold或recovery/removal表征。',
          '', '实际引脚→Q共有%d次预期转换，测得%d次；带符号延迟%.3f–%.3fps，缺失／歧义%d次。交点为原生相邻点间线性估计，保留原始括区。'%(
             delay['expected_transitions'],delay['measured'],delay['min_signed_s']*1e12,delay['max_signed_s']*1e12,delay['missing_or_ambiguous']),
          '', '![FF原生时序](ff/timing.png)','',
          '最坏为测试实例`XDUT.XU19.XFF.MM64`的VDS=%.9fV，时刻%.9fns；对应完整候选`XDUT.XREF.XSTORE6.XFF.MM64`。它是库DFCNQD1内部N管，不是外部参考开关，也不是本台的理想输入源。'%(ev['max_abs_v'],ev['time_s']*1e9),
          '', '该时刻属于phase5：CK下降、D=0、RST=0、Q应保持1。原生同刻实际CK/D/RST/CDN/Q依次为'+', '.join('%.9gV'%values[k] for k in ['CK','D','RST','CDN','Q'])+'。',
          '', '**MM64同刻D/S/G电压尚未知。** 它们不在135路返回电压中；B为原理图接地0V。全历史mq_x最大值和net176最小值发生在不同时间，不用于补造同刻VDS。父任务另行安排小型联合节点导出。',
          '', '![FF事件放大](ff/event_zoom.png)','',
          '原生日志首批MM45 Vgs告警出现在约0.990003ns，显示−990.001mV，约1µV超额是日志舍入值。它不是DC初值，也不是全历史最大值。当前7596对严格超限中7348对超额>1mV，99对>100mV，不能概括为只有数值边界告警；1mV仅用于分组，0.99V筛查从未放宽。',
          '同一`XU25.XFF.MM45`的全历史|VGS|最大为%.9fV，发生于%.9fns；需与日志首条告警区分。'%(ff['MM45_comparison']['full_history']['max_abs_v'],ff['MM45_comparison']['full_history']['max_abs_time_s']*1e9),
          '', '![FF端压分类](ff/terminal_classes.png)','',
          '逐器件归属、对应候选实例和同时刻端对见[端压明细](ff/terminal_failures.csv)；本台激励driver单列，不能误标为完整ADC原实例。重复端对及复制上下文不等同独立失效机制。',
          '', '## 功耗与证据范围','',
          '测试台VVDD在20ns净交付%.6fpJ，除以时长为%.3fµW；瞬时峰值%.3fmW。它包含并行的26个存储上下文、76个负载副本及驱动，不能当作单个ADC功耗或与整机1mW指标直接比较。六路独立理想命令／条件源的功单列保存在[数值报告](ff/summary.json)，不混作器件耗散。'%(
              ff['power']['VVDD']['net_delivered_j']*1e12,ff['power']['VVDD']['average_net_source_power_w']*1e6,ff['power']['VVDD']['peak_instantaneous_power_w']*1e3),
          '', '当前只有89路选定端流；其余7466路及完整KCL明确未知。MM64本身电流未保存，因此尚不能把内部动态过冲唯一归为沟道、电荷注入或漏电。',
          '', '结果支持标准门存储网络在此激励下完成预期状态转换，同时暴露FF边沿附近的内部端压问题。下一步需补联合节点证据并核对实际输入slew、截断输出负载与库表征范围；不能由该台直接推断库不可靠或整次标准化失败。',
          '', '测试环境：T28原样标准单元SPICE；FF0.99V／−40°C；理想外部供电／命令；无瞬态噪声、失配、PEX；仅真实第一级扇出／RC输入负载，后级输出截断。实际日志设置gear2only、maxstep10ps、reltol100e−09、V/I abstol10nV/100fA。',
          '', 'FF由完整原生仿真复用分析得到：30060点、native PASS及零错误footer、原始日志／输入／回收SHA和gzip逐字节身份已核对；并非重新或伪造仿真。']
    if cases['ss']:
        ss=cases['ss'];lines += ['', '## SS：相同序列、保留本角结果','',
            'SS完整%d点，502个保持阶段通过、额外Q沿阶段0，0／11220对严格超限，原生CMI=%s。最大端压%.9fV；这与FF的0.99V供电恰处筛查上限不同，不能把SS无告警外推为FF可靠性通过。'%(
                ss['proof']['wave']['rows'],ss['summary']['native_CMI_present'],ss['all_pair_peak']['voltage_v']),
            '', '![SS原生时序](ss/timing.png)','',
            '[SS逐相位检查](ss/phases.csv) · [SS数值与源证明](ss/summary.json) · [SS端压分类](ss/terminal_classes.png)',
            '', '两角原生波形与阈值定义相同，电源／模型按本角设置；当前未包含TT、PVT全覆盖、失配、噪声和真实SAR闭环。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return cases


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['ff','ss'],required=True);ap.add_argument('--refresh-existing',action='store_true');a=ap.parse_args()
    r=review(a.case,a.refresh_existing);combined()
    print(json.dumps(dict(case=a.case,report=(OUT/'README.md').as_posix(),holds=r['summary']['stable_holds'],
        strict_pairs=r['strict_failed_pairs'],diagnostic_gt1mV=r['diagnostic_excess_gt1mV_pairs'],
        classes=r['physical_classes'],delays=r['summary']['delays'],focus=r['MM64_focus'],
        supply=r['power']['VVDD']),indent=2))


if __name__=='__main__':main()
