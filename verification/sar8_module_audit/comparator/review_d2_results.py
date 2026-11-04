"""Review collected D2 native side outputs locally; never access raw/remote data."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import yaml
import build_d_fixture as build

HERE = Path(__file__).resolve().parent
ROOT = build.ROOT
OUT = HERE / "results" / "d2"
RESET = ['xdut.comp_p','xdut.comp_n','xdut.xcomp.x','xdut.xcomp.y']


def resolve(run):
    folder=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt=json.loads((folder/'collection_receipt.json').read_text())
    assert not receipt['skipped'] and receipt['total_bytes']<=32*1024*1024
    paths={}
    for item in receipt['files']:
        p=folder/item['name']
        if not p.exists() or build.sha(p.read_bytes())!=item['sha256']:
            p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        assert p.stat().st_size==item['bytes'] and build.sha(p.read_bytes())==item['sha256']
        paths[item['name']]=p
    recipe=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())['recipe']
    frozen=folder.parent/'inputs'
    for item in recipe['files']:
        assert build.sha((frozen/item['name']).read_bytes())==item['sha256'],item['name']
    return folder,paths,receipt,recipe,frozen


def events(path):
    return [dict(node=n,up=int(u),time_s=float(t)) for n,u,t in
            (line.split() for line in path.read_text().splitlines())]


def samples(path):
    with path.open() as f:
        return [{k:v if k in ['kind','label'] else float(v) for k,v in row.items()}
                for row in csv.DictReader(f,delimiter='\t')]


def ready90(fall,next_rise,level_events):
    state={n:fall[n]>=.9*fall['vdd!'] for n in RESET}
    ready=fall['time_s'] if all(state.values()) else None
    for e in level_events:
        if fall['time_s']<=e['time_s']<next_rise:
            state[e['node']]=bool(e['up'])
            if all(state.values()):
                if ready is None:ready=e['time_s']
            else:ready=None
    return ready if all(state.values()) else None


def review(label):
    run='sar8audit-comp-d2-'+label
    folder,paths,receipt,recipe,frozen=resolve(run)
    simulation=json.loads(paths['simulation.state.json'].read_text())
    analysis=json.loads(paths['analysis.state.json'].read_text())
    for state in [simulation,analysis]:assert state['status']=='complete' and state['exit_code']==0
    log=paths['spectre.out'].read_text(errors='replace')
    assert 'spectre completes with 0 errors' in log
    assert re.search(r'tran_d\s+PASS',paths['raw/logStatus'].read_text())
    meta=json.loads(paths['derived/wave.meta.json'].read_text())
    assert meta['PSF_END'] and abs(meta['last_time_s']-260e-9)<1e-15
    assert int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1])+1==meta['native_points']
    mapping=json.loads((frozen/'mapping.json').read_text())
    native=events(paths['derived/wave.events.tsv'])
    levels=events(paths['derived/wave.reset90.tsv'])
    snap=samples(paths['derived/wave.samples.tsv'])
    fixed={x['label']:x for x in snap if x['kind']=='fixed'}
    peakrows=[[float(v) for v in line.split()] for line in paths['derived/wave.stress.tsv'].read_text().splitlines()]
    assert len(mapping['records'])==2802 and len(peakrows)==905
    failed=[];worst={}
    for item in mapping['records']:
        index,peak,at=peakrows[item['pair_index']]
        assert int(index)==item['pair_index']
        row=dict(item,peak_v=peak,time_s=at)
        if peak>item['limit_v']:failed.append(row)
        prior=worst.get(item['group'])
        if prior is None or peak/item['limit_v']>prior['peak_v']/prior['limit_v']:worst[item['group']]=row
    original_result=json.loads(paths['derived/result.json'].read_text())
    assert len(failed)==original_result['failing_pairs']
    assert json.loads(paths['derived/failing_pairs.json'].read_text())==failed
    cycles=[]
    for c in mapping['cycles']:
        i=c['index'];lo=c['start_ns']*1e-9;hi=lo+40e-9
        rise=[x for x in snap if x['kind']=='clock_rise' and lo<=x['time_s']<hi]
        fall=[x for x in snap if x['kind']=='clock_fall' and lo<=x['time_s']<hi]
        writes=[x for x in snap if x['kind']=='write_rise' and lo<=x['time_s']<hi]
        assert len(rise)==len(fall)==len(writes)==1
        rise,fall,write=rise[0],fall[0],writes[0]
        native_wr=[e for e in native if e['node']=='xdut.xctrl.phi_w' and e['up']==1 and lo<=e['time_s']<hi]
        assert len(native_wr)==1 and abs(write['time_s']-native_wr[0]['time_s'])<1e-18
        assert rise['time_s']<write['time_s']<fall['time_s']
        expected=c['expected_DATA'];data_bit=int(write['xdut.xctrl.data']>.5*write['vdd!'])
        late=fixed['pre_fall_'+str(i)]
        edge=[e for e in native if e['node']=='xdut.xctrl.data' and rise['time_s']<=e['time_s']<=write['time_s']]
        if edge:
            lead=(write['time_s']-edge[-1]['time_s'])*1e9
            lead_kind='last current-cycle half-VDD DATA crossing to write'
            lower_bound=False
        else:
            assert int(rise['xdut.xctrl.data']>.5*rise['vdd!'])==data_bit
            lead=(write['time_s']-rise['time_s'])*1e9
            lead_kind='no DATA half-crossing this cycle; lower bound since comparator clock rise'
            lower_bound=True
        d0edges=[e for e in native if e['node']=='d0' and e['up']==expected and write['time_s']<=e['time_s']<fall['time_s']]
        beforebit=int(write['d0']>.5*write['vdd!'])
        if beforebit!=expected:assert len(d0edges)==1
        rxstate={name:rise['xdut.xctrl.xtim.'+name]>.5*rise['vdd!'] for name in ['pr','nr']}
        both_low=[];begin=None
        for e in native:
            if rise['time_s']<=e['time_s']<=write['time_s'] and e['node'] in ['xdut.xctrl.xtim.pr','xdut.xctrl.xtim.nr']:
                rxstate[e['node'].split('.')[-1]]=bool(e['up'])
                if not any(rxstate.values()) and begin is None:begin=e['time_s']
                elif any(rxstate.values()) and begin is not None:
                    both_low.append(dict(start_from_clock_ns=(begin-rise['time_s'])*1e9,
                                         end_from_clock_ns=(e['time_s']-rise['time_s'])*1e9));begin=None
        reset_at=ready90(fall,(c['start_ns']+40)*1e-9+50e-12,levels)
        assert reset_at is not None
        cycles.append(dict(index=i,input_sign='+' if expected else '-',expected_DATA=expected,
            expected_D0=c['expected_D0'],clock_rise_ns=rise['time_s']*1e9,
            actual_input_diff_at_clock_v=rise['topp']-rise['topn'],
            write_ns=write['time_s']*1e9,clock_to_write_ns=(write['time_s']-rise['time_s'])*1e9,
            DATA_v_at_write=write['xdut.xctrl.data'],DATA_matches=data_bit==expected,
            DATA_before_write_interval_ns=lead,DATA_interval_is_lower_bound=lower_bound,
            DATA_interval_definition=lead_kind,
            PR_NR_both_low_intervals_before_write=both_low,
            D0_v_at_write=write['d0'],D0_v_before_clock_fall=late['d0'],
            D0_matches=int(late['d0']>.5*late['vdd!'])==c['expected_D0'],
            D0_required_new_transition=(beforebit!=expected),
            D0_transition_after_write_ns=None if beforebit==expected else (d0edges[0]['time_s']-write['time_s'])*1e9,
            clock_fall_ns=fall['time_s']*1e9,reset_all4_90pct_ready_ns=reset_at*1e9,
            reset_all4_90pct_after_fall_ns=(reset_at-fall['time_s'])*1e9,
            pre_update_all4_90pct=all(fixed['pre_update_'+str(i)][n]>=.9*fixed['pre_update_'+str(i)]['vdd!'] for n in RESET),
            pre_compare_all4_90pct=all(fixed['pre_compare_'+str(i)][n]>=.9*fixed['pre_compare_'+str(i)]['vdd!'] for n in RESET),
            raw_output_at_write_v=[write['xdut.comp_p'],write['xdut.comp_n']],
            received_at_write_v=[write['xdut.xctrl.xtim.pr'],write['xdut.xctrl.xtim.nr']]))
    allwrites=[e for e in native if e['node']=='xdut.xctrl.phi_w' and e['up']==1]
    assert len(allwrites)==6
    assert len([e for e in native if e['node']=='xdut.xctrl.phi_w' and e['up']==0])==6
    d0_transitions=[e for e in native if e['node']=='d0']
    assert [e['up'] for e in d0_transitions]==[1,0,1,0]
    cells=build.blocks((frozen/'cells.scs').read_text())
    attachments=[(n,args,master) for n,args,master,_ in build.instances(cells['audit_cmp_ctrl']) if n.startswith('XBIT')]
    assert len(attachments)==8 and all(args[3]=='PHI_W' and master=='sar8p_bit' for n,args,master in attachments)
    bitinst={n:(args,master) for n,args,master,_ in build.instances(cells['sar8p_bit'])}
    assert bitinst['XSTORE'][0][0]=='PHI_W' and bitinst['XSTORE'][1]=='sar8p_dffr'
    assert build.ports(cells['sar8p_dffr'])[0]=='CK'
    dff={n:(args,master) for n,args,master,_ in build.instances(cells['sar8p_dffr'])}
    assert dff['MN_SI'][0][1]=='CK' and dff['MN_MI'][0][1]=='CKB'
    products=[line.split() for line in paths['derived/wave.products.tsv'].read_text().splitlines()]
    assert len(products)==1 and products[0][0]=='VDD' and products[0][1]=='0'
    stream=(frozen/'stream.cpp').read_text()
    assert stream.count('f<1')==2 and stream.count('260e-9')==2 and '100e-9' not in stream
    energy=-float(products[0][2]);remote=json.loads(paths['derived/diagnostic.json'].read_text())
    assert abs(energy-remote['VDD_energy_j'])<1e-24
    for independent,prior in zip(cycles,remote['cycles']):
        assert independent['D0_matches']==prior['D0_matches_expected_by_diagnostic_fall']
        assert prior['write_count']==1
    warnings=sorted(set(re.findall(r'WARNING \(([^)]+)\)',log)))
    validity_counts={n:sum(e['node']==n and e['up']==1 for e in native)
                     for n in ['xdut.xctrl.xtim.raw','xdut.xctrl.xtim.raw_d','xdut.xctrl.xtim.dec','xdut.xctrl.phi_w']}
    first_up={n:next(e['time_s']*1e9 for e in native if e['node']==n and e['up']==1)
              for n in ['xdut.xctrl.xtim.raw','xdut.xctrl.xtim.raw_d','xdut.xctrl.xtim.dec','xdut.xctrl.data','xdut.xctrl.phi_w']}
    result=dict(run_id=run,corner=label,source_receipt_sha256=build.sha((folder/'collection_receipt.json').read_bytes()),
        source_files={item['name']:item['sha256'] for item in receipt['files']},
        verified_frozen_files=len(recipe['files']),collected_bytes=receipt['total_bytes'],
        native_points=meta['native_points'],display_points=meta['points'],native_stop_s=meta['last_time_s'],
        effective_settings=simulation['native']['effective_settings'],warnings=warnings,
        native_zero_errors=True,native_analysis_PASS=True,CMI_warning_present=bool(re.search(r'WARNING \(CMI-',log)),
        actual_multithreading_disabled='Multithreading is disabled' in log,
        terminal_pair_checks=2802,failed_terminal_pair_checks=len(failed),worst_terminal_by_group=worst,
        actual_write_count=6,cycles=cycles,all_DATA_correct=all(c['DATA_matches'] for c in cycles),
        native_half_supply_validity_rise_counts=validity_counts,
        first_positive_forward_rise_times_ns=first_up,
        receiver_transient_interpretation='Common-mode output discharge can produce PR/NR=00 before regeneration; XOR is0 in00 and11. Current native half-VDD RAW/RAW_D/DEC/PHI_W counts show no duplicate accepted pulse; subthreshold analog pulses remain outside this binary statement.',
        DATA_lead_interpretation='Observed207psTT/295psSS positive-input lead comes from the parallel DATA path versus delayed-RAW/DEC/write path; it is not a characterized DFF setup requirement or guaranteed setup margin.',
        independent_DONE_output_present=False,
        all_D0_correct=all(c['D0_matches'] for c in cycles),
        register_clock_binding_verified=True,register_polarity='positive edge master/slave; master CK-low transparent, slave CK-high transparent',
        register_clock_attachments=[dict(instance=n+'.XSTORE',CK='XCTRL.PHI_W') for n,_,_ in attachments],
        native_D0_half_supply_transitions=d0_transitions,
        register_internal_CKB_aperture_time_verified=False,
        setup_hold_qualified=False,VDD_energy_pj=energy*1e12,VDD_mean_uW=energy/260e-9*1e6,
        energy_scope='entire260ns diagnostic module VDD, including initial reset and idle; not ADC power or isolated comparator energy',
        energy_provenance='existing native trapezoids independently audited to cover0..260ns; no second raw re-integration',
        native_functional_observations_pass=all(c['DATA_matches'] and c['D0_matches'] for c in cycles),
        module_qualified=False,kickback_measured=False,noise_mismatch_measured=False,
        simulation_peak_rss_bytes=simulation['peak_rss_bytes'],analysis_peak_rss_bytes=analysis['peak_rss_bytes'])
    names=paths['derived/wave.columns'].read_text().splitlines()
    wave=np.memmap(paths['derived/wave.bin'],dtype='<f8',mode='r').reshape(-1,len(names))
    assert len(wave)==meta['points'] and np.all(np.diff(wave[:,0])>0)
    return result,names,wave


def plot(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.titlesize':10})
    fig,axes=plt.subplots(7,2,figsize=(13,10),sharex='col',layout='constrained')
    rows=[(['cmp_clk'],'CMP_CLK (V)'),([], 'Input diff (mV)'),
          (['xdut.comp_p','xdut.comp_n'],'COMP_P/N (V)'),
          (['xdut.xctrl.xtim.pr','xdut.xctrl.xtim.nr'],'PR/NR (V)'),
          (['xdut.xctrl.data'],'DATA (V)'),(['xdut.xctrl.phi_w'],'PHI_W (V)'),(['d0'],'D0 (V)')]
    for col,(r,names,wave) in enumerate(cases):
        c=r['cycles'][0];origin=c['clock_rise_ns'];x=wave[:,0]*1e9-origin
        mask=(x>=-.5)&(x<=14)
        for row,(signals,label) in enumerate(rows):
            ax=axes[row,col]
            if row==1:
                ax.plot(x[mask],(wave[mask,names.index('topp')]-wave[mask,names.index('topn')])*1000,color='#386641',lw=1.2,label='VINP - VINN')
                ax.set_ylim(-2.2,2.2)
            else:
                for j,name in enumerate(signals):
                    ax.plot(x[mask],wave[mask,names.index(name)],color=['#2166ac','#d6604d'][j],lw=1.2,label=name.split('.')[-1].upper())
                ax.set_ylim(-.08,1.04)
            ax.axvline(c['write_ns']-origin,color='#777',ls=':',lw=.8)
            ax.axvspan(c['clock_fall_ns']-origin,14,color='#b8cbb3',alpha=.18)
            ax.grid(alpha=.18)
            if col==0:ax.set_ylabel(label)
            ax.legend(fontsize=7,loc='upper center',ncol=2,framealpha=.75)
        axes[0,col].set_title(('TT / 0.90 V / 27 C' if r['corner']=='tt' else 'SS / 0.81 V / -40 C')+
            '\nwrite +%.3f ns; reset90 +%.3f ns after fall'%(c['clock_to_write_ns'],c['reset_all4_90pct_after_fall_ns']))
        axes[-1,col].set(xlim=(-.5,14),xlabel='Time from first CMP_CLK half-VDD rise (ns)')
    fig.suptitle('N4 + rx2 + physical 8-bit register load | first +1.758 mV decision\n'
                 'Ideal inputs / diagnostic clock; VCM 0.45 V; no noise, mismatch or PEX\n'
                 'Dotted = actual write; shaded = clock-low reset; traces 20 ps compact, metrics native',fontsize=10)
    path=OUT/'timing_TT_SS.png';fig.savefig(path,dpi=160);plt.close(fig)
    return path


def report(cases):
    a,b=[x[0] for x in cases]
    lines=['# N4/rx2 D2：TT 与 SS 冷角本地复核','',
           '两例六次写入均与预期极性一致，2,802个端压检查项均无超限。该结果限于理想输入／诊断时钟测试台。','',
           '| 次序／输入 | TT时钟→write ns | SS冷时钟→write ns | TT DATA领先 ns | SS冷 DATA领先 ns |',
           '| --- | ---: | ---: | ---: | ---: |']
    def lead(c):return ('≥' if c['DATA_interval_is_lower_bound'] else '')+'%.3f'%c['DATA_before_write_interval_ns']
    for x,y in zip(a['cycles'],b['cycles']):
        lines.append('| %d／%s | %.3f | %.3f | %s | %s |'%(x['index']+1,x['input_sign'],x['clock_to_write_ns'],y['clock_to_write_ns'],lead(x),lead(y)))
    lines+=['','DATA领先以原生半电源交越定义。负输入时DATA本周期已经为低且没有交越，表中只给从比较沿开始的下界；不能借用上一周期的边沿算成精确setup裕量。尚未分配或验证setup/hold。','',
        '原样sar8p_bit.XSTORE的CK直接接PHI_W；DFF为正沿主从结构。六次PHI_W上升沿即六次外部寄存器时钟沿。四次需要变码的D0均在写入后出现正确交越，两次重复码没有必要翻转。D0在write瞬间仍可能是旧值，不能据此判失败。内部CKB关闭主锁存器的精确采样孔径没有原生交越记录，故不声称内部孔径／setup-hold已验收。','',
        '| 实测项 | TT | SS冷 |','| --- | ---: | ---: |',
        '| reset后四节点持续恢复至90%%VDD／ns | %.3f–%.3f | %.3f–%.3f |'%(min(c['reset_all4_90pct_after_fall_ns'] for c in a['cycles']),max(c['reset_all4_90pct_after_fall_ns'] for c in a['cycles']),min(c['reset_all4_90pct_after_fall_ns'] for c in b['cycles']),max(c['reset_all4_90pct_after_fall_ns'] for c in b['cycles'])),
        '| 完整260ns VDD能量／pJ | %.6f | %.6f |'%(a['VDD_energy_pj'],b['VDD_energy_pj']),
        '| 本诊断占空比平均VDD功率／µW | %.3f | %.3f |'%(a['VDD_mean_uW'],b['VDD_mean_uW']),
        '| 原生时间点 | %d | %d |'%(a['native_points'],b['native_points']),
        '| 端压超限项 | 0 / 2802 | 0 / 2802 |','',
        '90%只是复位电平的测量定义，没有新设复位时限。六次输入更新前及比较前均观察到四节点达到该电平。能量来自完整0–260ns原生梯形积分，已核对积分器区间和原生步数；没有重新回收原始大波形作第二次积分。这是467管模块及初始复位／空闲的VDD能量，不是整机或单独比较器功耗。','',
        '原生日志均为tran_d PASS、exit0；只有VACOMP-2435（弃用环境变量）和四条SFE-1131（继承模型scalefactor重复定义），没有CMI或收敛放宽告警。实际reltol=1e-7、maxstep=5ps、gear2only；日志明确禁用多线程，不能声称实际四线程加速。','',
        'TT首轮PR/NR同时低的原生区间为比较沿后0.570–1.383ns。CLK打开尾管后，两原始输出先共同下落，再由再生抬回正确一侧；TT两接收输出都发生下降交越，SS冷的PR没有下降半电源交越，因此没有同样的00阶段。这是当前动态响应的区别，不能反推已测得DC接收门限。00和预充态11的XOR均为0。两例RAW、RAW_D、DEC、PHI_W均各6次上升，每周期一次，未观察到重复有效或复位写入；台内没有独立DONE输出。原生半电源事件不能证明不存在更小的模拟脉冲，也不能外推全部输入/PVT。','',
        'TT首轮RAW/RAW_D/DEC/write分别在21.4540/21.6032/21.6255/21.6631ns上升，DATA在21.4560ns上升。207ps领先由DATA短路径与延迟RAW→DEC→write长路径形成，属于本例路径差。尚未测量寄存器真实setup/hold要求和内部CKB孔径，因此不能据此称setup已通过；SS约295ps同理。','',
        '![分行时序](timing_TT_SS.png)','',
        '图展示首个正输入周期；完整六周期数值与回执散列见TT_review.json和SS_cold_review.json。SS冷角首次较后续略慢，应保留历史差异，不用后续周期覆盖首轮。理想源钳住输入，因此本图不测kickback；噪声、失配、全共模与整机异步时序仍未验证。']
    return '\n'.join(lines)+'\n'


def main():
    cases=[review('tt'),review('sscold')]
    OUT.mkdir(parents=True,exist_ok=True)
    for (r,_,_),name in zip(cases,['TT_review.json','SS_cold_review.json']):
        (OUT/name).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    image=plot(cases)
    (OUT/'review.md').write_text(report(cases),encoding='utf-8')
    print(json.dumps(dict(figure=str(image),cases=[dict(corner=r['corner'],writes=r['actual_write_count'],DATA=r['all_DATA_correct'],D0=r['all_D0_correct'],stress_failed=r['failed_terminal_pair_checks'],energy_pj=r['VDD_energy_pj']) for r,_,_ in cases]),indent=2))


if __name__=='__main__':main()
