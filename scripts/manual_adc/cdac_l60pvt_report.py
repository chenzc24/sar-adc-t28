"""L60 cold settling and high-VDD stress; keep functional/electrical verdicts separate."""
import csv
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_l60pvt_v1'
CASES=[('ss030ref','manual8-cdac-s100-sscold-v1','SS / 0.90 V / -40 C / L30',.9),
       ('ff090ref','manual8-cdac-nl60-ffhot-v1','FF / 0.90 V / 125 C / L60',.9),
       ('ss090cold','manual8-cdac-l60-ss090cold-v1','SS / 0.90 V / -40 C / L60',.9),
       ('ss081cold_i1p','manual8-cdac-l60-ss081cold-i1p-v1','SS / 0.81 V / -40 C / L60 (Iabstol 1 pA)',.81),
       ('ff099cold','manual8-cdac-l60-ff099cold-v1','FF / 0.99 V / -40 C / L60',.99),
       ('ff099hot_retry','manual8-cdac-l60-ff099hot-v2','FF / 0.99 V / 125 C / L60',.99)]

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def window(path,lo,hi):
    rows=[]
    with gzip.open(path,'rt') as f:
        for row in csv.DictReader(f):
            t=float(row['time'])
            if t>hi:break
            if t>=lo:rows.append({k:float(v) for k,v in row.items()})
    assert rows,path
    z={k:np.array([q[k] for q in rows]) for k in rows[0]};z['0']=np.zeros_like(z['time'])
    return z

def main():
    manifest=read(B/'manifest.json');data={};summary={};validation={};pending=[]
    for key,run,label,vdd in CASES:
        col=R/'output/managed_execution/runs'/run/'collected'
        if not (col/'derived/result.json').exists():
            pending.append({'case':key,'run_id':run,'reason':'No completed collected analysis; do not infer electrical result.'})
            continue
        r=read(col/'derived/result.json');s=read(col/'simulation.state.json');a=read(col/'analysis.state.json');receipt=read(col/'collection_receipt.json')
        fresh=key in manifest['cases']
        if fresh:shutil.copyfile(col/'derived/result.json',B/key/'results.json')
        z=window(col/'derived/reset_native.csv.gz',109.4e-9,110.2e-9)
        pairs=r['terminal_pairs'];worst=max(pairs,key=lambda q:q['peak_V']);bottoms={k:q for k,q in r['node_extrema'].items() if '.xd.net' in k};bn=min(bottoms,key=lambda k:bottoms[k]['min_V'])
        z['terminal_max']=np.max(np.array([abs(z[q['nodes'][0]]-z[q['nodes'][1]]) for q in pairs]),axis=0)
        z['bottom_min']=np.min(np.array([z[k] for k in bottoms]),axis=0)
        timing=r['sample_timing_validation'];clock=r['timing_events']['clks']
        expected={'rising':[10.025e-9+i*100e-9 for i in range(9)],'falling':[49.975e-9+i*100e-9 for i in range(8)]}
        clockdelta=max(abs(x-y) for direction in expected for x,y in zip(clock[direction],expected[direction]))
        check={'native_complete':s['status']=='complete' and s['exit_code']==0 and s['native']['zero_error_footer'],
               'analysis_complete':a['status']=='complete' and a['exit_code']==0,
               'coverage':len(r['captures'])==8 and len(r['comparisons'])==64 and len(r['segments'])==56 and len(pairs)==168,
               'same_clock_times':clockdelta<1e-12 and all(len(clock[d])==len(expected[d]) for d in expected),'sample_midpoints':max(timing.values())<1e-12,
               'correct_vdd_reference':bool(np.max(abs(z['vdd']-vdd))<1e-10 and np.max(abs(z['refp']-.9))<1e-10 and np.max(abs(z['refn']))<1e-10),
               'same_criteria':r['criteria']==data['ss030ref'][0]['criteria'] if data else True,
               'expected_solver':all(v==data['ss030ref'][3]['native']['effective_settings'][k] for k,v in s['native']['effective_settings'].items() if not (key=='ss081cold_i1p' and k=='abstol(I)')) if data else True,
               'budget':s['peak_rss_bytes']<=1024*1024**2 and a['peak_rss_bytes']<=256*1024**2 and receipt['total_bytes']<=32*1024**2 and not receipt['skipped']}
        if fresh:
            check['frozen_files']=all(hashlib.sha256((B/key/f).read_bytes()).hexdigest()==h for f,h in manifest['cases'][key]['files'].items())
            base=R/'verification/manual_adc/cdac_nlength_v1/l60'
            check['unchanged_DUT_VA']=all((B/key/n).read_bytes()==(base/n).read_bytes() for n in ['cdac_core.scs','wrappers.scs','manual8_sample.va','manual8_cmp.va','manual8_sar.va'])
            spec=manifest['cases'][key]
            test=(B/key/'test.scs').read_text().replace('VVDD (VDD 0) vsource dc=%.2f'%vdd,'VVDD (VDD 0) vsource dc=.9').replace('val0=0 val1=%.2f delay'%vdd,'val0=0 val1=.9 delay').replace('temp=%d tnom=27'%spec['temperature_C'],'temp=125 tnom=27')
            if key=='ss081cold_i1p':test=test.replace('iabstol=1e-12','iabstol=1e-14')
            check['only_declared_fixture_changes']=test==(base/'test.scs').read_text()
            check['only_declared_model_section']=(B/key/'models.scs').read_text().replace('section='+spec['corner']+'macro_mos_moscap','section=ffmacro_mos_moscap')==(base/'models.scs').read_text()
        if key=='ss081cold_i1p':check['iabstol_explicit_1pA']=s['native']['effective_settings']['abstol(I)']=='1 pA'
        assert all(check.values()),(key,check)
        if fresh:check['current_KCL_1nA_diagnostic']=r['leakage']['kcl_screen_pass']
        data[key]=(r,z,col,s);validation[key]=check
        finite=[q['settling_time_upper_s'] for q in r['segments'] if q['settling_time_upper_s'] is not None]
        bad=[q for q in pairs if q['peak_V']>.99]
        q={'run_id':run,'label':label,'vdd_V':vdd,'reference_V':.9,'new_run':fresh,'short_test_pass':r['short_test_pass'],'checks':r['checks'],
           'max_compare_dm_V':r['summary']['max_compare_dm_error_V'],'max_compare_cm_V':r['summary']['max_compare_cm_error_V'],
           'settled':sum(q['settled_by_2ns'] for q in r['segments']),'unsettled':sum(q['settling_time_upper_s'] is None for q in r['segments']),
           'max_settling_upper_s':max(finite) if finite else None,'max_after2ns_error_V':max(q['max_abs_error_after_budget_V'] for q in r['segments']),
           'max_conversion_s':r['summary']['max_conversion_s'],'correct_codes':sum(q['actual']==q['expected'] for q in r['captures']),
           'codes':[q['actual'] for q in r['captures']],'bottom_min_V':bottoms[bn]['min_V'],'bottom_node':bn,'bottom_time_s':bottoms[bn]['min_s'],
           'worst_terminal':worst,'overlimit_pair_count':len(bad),'overlimit_devices':sorted(set(q['device'] for q in bad)),
           'overlimit_pairs':bad,'maximum_pair_accumulated_over_s':max(q['duration_over_s'] for q in pairs),
           'CMI_codes':r['CMI_codes'],'warnings':s['native']['warning_codes'],'native_settings':s['native']['effective_settings'],
           'simulation_s':s['elapsed_seconds'],'simulation_RSS_MiB':s['peak_rss_bytes']/1024**2,
           'analysis_s':a['elapsed_seconds'],'analysis_RSS_MiB':a['peak_rss_bytes']/1024**2,'collected_bytes':receipt['total_bytes'],
           'max_sampling_time_error_s':max(timing.values()),'clock_time_error_s':clockdelta}
        if 'leakage' in r:
            m=r['leakage']['steady'][0]['mean']
            q['steady_frame0']={name:m[name] for name in ['refp_draw_A','body_supply_draw_A','P64.rail_error_V','N64.rail_error_V','actual_dm_error_V','xadc.xp.xd.m1.ID','xadc.xn.xd.m0.ID']}
            q['native_KCL_A']=r['leakage']['largest_kcl_residual_A'];q['charge_closure_V']=max(abs(w['mean']['dm_reconstruction_residual_V']) for w in r['leakage']['steady'])
        if fresh:
            # Exact worst pair peak and contiguous overlimit pulse, native +/-300ps export.
            peakfile='reset_native.csv.gz' if 109.4e-9<=worst['time_s']<=110.2e-9 else 'branch_wave.csv.gz'
            # Independent fixed reset export is native even when Python2 mixed
            # list/tuple sorting dropped early intervals from the branch export.
            p=window(col/'derived'/peakfile,worst['time_s']-300e-12,worst['time_s']+300e-12)
            q['peak_export_file']=peakfile
            y=abs(p[worst['nodes'][0]]-p[worst['nodes'][1]]);idx=int(np.argmax(y));assert abs(y[idx]-worst['peak_V'])<1e-10
            q['worst_peak_node_voltages']={n:float(p[n][idx]) for n in set(worst['nodes']+['vdd','refp','clks','xadc.xn.sample_frac','xadc.xp.sample_frac'])}
            dev=next(d for d in r['leakage']['devices'] if d['path']==worst['device'])
            q['worst_peak_device_terminals_V']={n:float(p[n.lower()][idx]) for n in dev['terminals']}
            if y[idx]>.99:
                left=idx;right=idx
                while left>0 and y[left-1]>.99:left-=1
                while right<len(y)-1 and y[right+1]>.99:right+=1
                q['peak_pulse_truncated']=left==0 or right==len(y)-1
                if not q['peak_pulse_truncated']:
                    t=p['time'];cross=lambda i,j:t[i]+(.99-y[i])*(t[j]-t[i])/(y[j]-y[i])
                    q['peak_pulse_duration_s']=float(cross(right,right+1)-cross(left-1,left))
            currents=window(col/'derived/branch_wave.csv.gz',worst['time_s']-300e-12,worst['time_s']+300e-12)
            q['peak_neighborhood_exported_KCL_A']=max(float(np.max(abs(sum(currents[d['path'].lower()+':'+str(i)] for i in [1,2,3,4])))) for d in r['leakage']['devices'])
            q['current_peak_neighborhood_is_native']=any(lo<=worst['time_s']-300e-12 and hi>=worst['time_s']+300e-12 for lo,hi in r['current_export_native_windows_s'])
        q['KCL_1nA_diagnostic']=r.get('leakage',{}).get('kcl_screen_pass')
        summary[key]=q
    failure_col=R/'output/managed_execution/runs/manual8-cdac-l60-ss081cold-v1/collected'
    failure=read(failure_col/'simulation.state.json')
    save(B/'original_ss081_failure.json',{'run_id':'manual8-cdac-l60-ss081cold-v1','last_accepted_time_s':1.14929e-9,'first_sample_start_s':9.98e-9,'error':'SPECTRE-16927','electrical_verdict':'unknown; failed before first sample','simulation':failure})
    save(B/'pending.json',pending)
    save(B/'comparison.json',summary);save(B/'validation.json',validation)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    figdir=B/'figures';figdir.mkdir(exist_ok=True)
    env='L60 NMOS / fixed W, nf, multiplicity / 100 ps sampler rise / fixed sampling and reset times\nReference and input 0..0.9 V; native CDAC ref MOS, ideal caps and other blocks; 10 MS/s'
    fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
    for key,color in [('ss030ref','#888888'),('ss090cold','#246ac4'),('ss081cold_i1p','#d25328')]:
        if key not in data:continue
        r,z,col,s=data[key];q=summary[key]
        # Use the display wave for the conversion overview; metrics remain native.
        w=window(col/'derived/wave.csv.gz',53.5e-9,72e-9);t=w['time']*1e9
        axs[0].plot(t,w['xadc.topp']-w['xadc.topn'],label=q['label'],color=color)
        comp=[x for x in r['comparisons'] if x['frame']==0]
        axs[1].plot([x['time_s']*1e9 for x in comp],[x['dm_error_V']*1e6 for x in comp],'o--',color=color,ms=4)
        seg=[x for x in r['segments'] if x['frame']==0]
        axs[2].plot([x['start_s']*1e9 for x in seg],[x['settling_time_upper_s']*1e12 if x['settling_time_upper_s'] is not None else np.nan for x in seg],'o-',color=color)
    axs[0].set_ylabel('Top-plate differential (V)');axs[0].legend(fontsize=8)
    axs[1].set_ylabel('DM aperture error (uV)');axs[2].set_ylabel('Settling upper bound (ps)')
    axs[1].text(.02,.08,'Precision budget: +/-703.125 uV; nV-scale traces approach the 10 nV solver tolerance',transform=axs[1].transAxes,fontsize=8)
    axs[-1].set_xlabel('Time (ns), frame0 / code0; error at actual comparison apertures')
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle('SS -40 C settling: same size/timing; L30 grey curve is historical context\n'+env,fontsize=11)
    fig.savefig(figdir/'ss_settling.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(5,1,figsize=(12,11),sharex=True,layout='constrained')
    for key,color in [('ff090ref','#888888'),('ff099cold','#246ac4'),('ff099hot_retry','#d25328')]:
        if key not in data:continue
        r,z,col,s=data[key];t=(z['time']-110e-9)*1e12
        for ax,name in zip(axs,['xadc.xn.sample_frac','xadc.dn_5','xadc.topn','bottom_min','terminal_max']):ax.plot(t,z[name],color=color,label=summary[key]['label'])
    for ax,label in zip(axs,['Sample on fraction','N16C gate (V)','N top plate (V)','Lowest bottom (V)','Max MOS terminal (V)']):
        ax.set_ylabel(label);ax.grid(alpha=.2);ax.set_xlim(-100,180)
        ax.axvline(-20,color='#555555',ls=':',lw=.7);ax.axvline(25,color='#a5783c',ls=':',lw=.7)
    axs[0].legend(ncol=3,fontsize=8);axs[-1].axhline(.99,color='black',ls='--',label='0.99 V device screen');axs[-1].legend(fontsize=8)
    axs[-1].set_xlabel('Time relative to 110 ns (ps); all native samples in this reset/sampling window')
    fig.suptitle('High-VDD undershoot and terminal stress\n'+env,fontsize=11)
    fig.savefig(figdir/'highv_stress.png',dpi=160);plt.close(fig)
    lines=['# L60参考NMOS：SS建立与高供电端压','',
        '采用用户选择的60nm候选，W、nf、并联数、PMOS、输入、采样窗口和关闭沿均保持，OA未改。四组目标工况已获得完整结果：建立和码字均通过，0.99V的FF冷/热角端压失败。SS0.81V使用下述独立数值恢复案例，原始失败完整保留；历史两组仅作对照。','',
        '**边界：REFP/REFN固定0.9/0V，输入码中心和量程不变；VDD变化影响PMOS体端、理想数字栅控与CLKS幅度。并非把参考幅度也随电源缩放。**','',
        'CDAC参考开关晶体管级，电容每侧1.28pF理想；采样器Ron=1Ω、100ps接通电导、10ps关断，比较器/SAR/电源/输入理想。外部CLKS及参考栅控仍为50ps；接通中点10.030ns、关闭中点49.980ns，每100ns重复。未包含真实Bootstrap/数字驱动、噪声、失配或PEX。','',
        '| 测试 | 最大比较差模误差(µV) | 建立通过 | 正确码 | 最低底板(mV) | 最大端压(V) | CMI |',
        '|---|---:|---:|---:|---:|---:|---|']
    for key,run,label,vdd in CASES:
        if key not in summary:continue
        q=summary[key]
        lines.append('| %s%s | %.4f | %d/56 | %d/8 | %.3f | %.6f | %s |'%(label,'（历史）' if not q['new_run'] else '',q['max_compare_dm_V']*1e6,q['settled'],q['correct_codes'],q['bottom_min_V']*1e3,q['worst_terminal']['peak_V'],','.join(q['CMI_codes']) or '无'))
    lines+=['','精度预算保持0.1LSB=703.125µV，逐位建立2ns、转换50ns、器件六种端差0.99V上限。8个码中心为0、255、85、170、127、128、1、254；每组820ns、64次比较、56次更新。码字正确不能替代端压通过。接近几十nV的残差已接近本次10nV电压绝对容差，只说明远低于误差预算。','',
        '## SS冷角建立','',
        '![SS冷角](figures/ss_settling.png)','',
        '图中上行为差分顶板逐次逼近，中行为每次比较孔径残差，下行为各步进入并保持在0.1LSB内的时间上界（从该步栅极50%交叉起算，包含原生采样分辨率）。灰色是原L30，蓝色是L60的0.90V，橙色是0.81V数值恢复测试、电流绝对容差1pA。均为SS−40°C。','',
        '**原SS0.81V测试未完成**：SPECTRE-16927在1.14929ns中止，早于9.98ns首次采样；不能由此判定建立或码字失败。保留原始失败，独立恢复案例只把iabstol从10fA改为1pA（其余电路和时序不变），不混作相同容差结果。','']
    for key in ['ss090cold','ss081cold_i1p']:
        if key not in summary:continue
        q=summary[key]
        lines.append('- **%s**：建立%d/56，未收敛%d段，最慢已收敛段上界%.2fps；2ns后最大误差%.4fµV，最大比较误差%.4fµV；转换%.3fns，码字%s。'%(q['label'],q['settled'],q['unsettled'],q['max_settling_upper_s']*1e12,q['max_after2ns_error_V']*1e6,q['max_compare_dm_V']*1e6,q['max_conversion_s']*1e9,q['codes']))
    lines+=['','## 高供电下冲与端压','',
        '![高供电端压](figures/highv_stress.png)','',
        '图显示第2帧采样/参考复位窗口的全部原生点，参考线为固定0.99V上限；表中峰值覆盖全820ns，可能出现在其他帧或阶段。依次为采样接通比例、N侧16C栅控、顶板、14个底板的最小值、168种端差最大值。竖线−20ps为采样接通开始，+25ps为CLKS上升中点/参考复位请求；外部时序未改。','']
    for key in ['ff099cold','ff099hot_retry']:
        if key not in summary:continue
        q=summary[key];w=q['worst_terminal']
        lines.append('- **%s**：最坏`%s`的%s=%.9fV，发生于%.6fns，节点为`%s`；最低底板`%s`=%.3fmV@%.6fns。超限端差%d对、涉及%d管，码字%d/8。'%(q['label'],w['device'],w['pair'],w['peak_V'],w['time_s']*1e9,' / '.join(w['nodes']),q['bottom_node'],q['bottom_min_V']*1e3,q['bottom_time_s']*1e9,q['overlimit_pair_count'],len(q['overlimit_devices']),q['correct_codes']))
        if 'peak_pulse_duration_s' in q:lines.append('  峰值所在连续超限脉冲约%.2fps；全程该端差累计超限%.2fps，二者不是同一指标。'%(q['peak_pulse_duration_s']*1e12,w['duration_over_s']*1e12))
        if q.get('peak_pulse_truncated'):lines.append('  当前±300ps局部窗口未包住完整连续超限脉冲，未报告截断脉宽；全程累计时间保留。')
        if not q['KCL_1nA_diagnostic']:lines.append('  原生电流KCL最大残差%.3fnA，未通过原1nA诊断阈值；保留此数值限制，电流分解不用于更细的漏电量化结论。'% (q['native_KCL_A']*1e9))
    if 'ff099cold' in summary:
        lines+=['',
            '**冷角主峰的时序来源已定位**：109.980ns采样开始接通，109.991811ns出现最深下冲；此时采样电导只接通11.81%，N16C栅极仍为0.989997V，110.025ns参考复位请求尚未发生。顶板从上一轮转换电平快速移向新输入，通过CDAC电容拖低底板，而NMOS导通通路尚有有限阻抗。最坏PMOS M5为关断状态，其漏端−31.792mV、体端0.99V，所以|VDB|=1.021792V；源端仍为0.9V，|VDS|约0.931792V。这里主要超限来自体端/高栅极相对负底板的端差，不是漏源已经达到1.02V。稍后的参考复位另有次峰，不能与首峰合并归因。',
            '',
            '因此，60nm减少FF热角静态漏电的收益保留，SS0.90V建立仍有余量；但提高供电使高电平端位于0.99V限制边界，现有下冲仍会形成超限。不能把码字正确解释为端压合格，也不能靠只加长NMOS认定过压已修复。下一步应针对采样重新接通时的底板保持/电压裕量处理，保持本次未改的尺寸和时序作为证据基线；本任务没有自动实施新的修复。']
    lines+=['','## 测量与复现','',
        '新分析器以VDD/2识别逻辑电平与事件，1%/99%门限也随VDD；参考目标仍为0.9V，误差/可靠性预算保持。旧固定0.45V门限分析器和历史结果未改。新阈值签名在0.81/0.90/0.99V验证，全部时钟及采样中点读回核对。','',
        'DUT和三个VA模型逐字节一致，仅仿真电源/外部时钟幅度、MOS模型section和温度变化（SS恢复另有明确容差变更）。全程指标使用原生点。发现电流波形扩展导出在Python2对list/tuple混合排序时遗漏部分早期窗口：不影响全程峰值/KCL计算；110ns附近电压图及最坏峰值使用独立reset_native原生导出核验，未把100ps显示抽点当作峰值证据。其他峰值按实际覆盖选择导出并核对。共享历史文件、OA及PDK均未改。','',
        'Spectre21.1 X CX、1线程；实际reltol1e-7、vabstol10nV、gear2only、maxstep20ps；原组iabstol10fA，明确标注的SS0.81V恢复组1pA，保留所有告警。','']
    for key,run,label,vdd in CASES:
        if key not in manifest['cases'] or key not in summary:continue
        q=summary[key]
        lines.append('- `%s`：仿真%.2fs/%.2fMiB；分析%.2fs/%.2fMiB；回收%.2fMiB；告警%s。'%(run,q['simulation_s'],q['simulation_RSS_MiB'],q['analysis_s'],q['analysis_RSS_MiB'],q['collected_bytes']/1024**2,','.join(q['warnings']) or '无'))
    lines+=['',
        '资源处理：账户48GiB限额中的大部分占用是文件缓存。经用户授权，对5个已结束运行的原始波形执行定向缓存释放，账户占用降低约2.02GiB；文件尺寸/修改时间不变，没有删除波形、终止Virtuoso或修改资源门槛。FF热角原v1在Spectre启动前明确排队超时；保留拒绝记录，在内存恢复后使用同电路/同求解设置的v2运行，未重复执行已完成仿真。']
    if pending:
        lines+=['','## 尚未回收完成','']+[f"- `{p['run_id']}`：未获得完整结果；见[pending.json](pending.json)，不作通过判断。" for p in pending]
    lines+=['','[完整数值和失败项](comparison.json) · [输入身份](manifest.json) · [测量验证](validation.json) · [SS原失败](original_ss081_failure.json)','',
        '这仍是CDAC模块的8帧筛查，未做全码/FFT或整机PVT验收；没有将候选同步至OA或采用新的整机基线。']
    (B/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:{x:q[x] for x in ['short_test_pass','max_compare_dm_V','settled','correct_codes','bottom_min_V','worst_terminal','CMI_codes']} for k,q in summary.items()},indent=2))

if __name__=='__main__':main()
