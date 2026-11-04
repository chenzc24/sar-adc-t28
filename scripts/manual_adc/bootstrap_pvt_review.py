"""Compare the selected 6 um Bootstrap across bounded extreme-corner short tests."""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from bootstrap_width_review import load, fit, worst_terminal, wave, LSB

R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_pvt_v1'
FIG=OUT/'figures'
CONDITIONS=[('tt',.9,27),('ss_cold',.81,-40),('ss_hot',.81,125),('ff_cold',.99,-40),('ff_hot',.99,125)]

def run_id(tag,case):
    return 'manual8-bootwidth-%s-m6-v1'%case if tag=='tt' else 'manual8-bootpvt-%s-%s-v1'%(tag.replace('_','-'),case)

def finish(fig,name,title):
    fig.suptitle(title+'\nM0 total 6 um | 10 MS/s | Bootstrap MOS; other blocks ideal behavioral\nVref=0.9 V, input CM=0.45 V; first clock 110 ns, closing edge 149.975 ns',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.90))
    fig.savefig(FIG/(name+'.png'),dpi=170)
    fig.savefig(FIG/(name+'.svg'))
    plt.close(fig)

def main():
    FIG.mkdir(exist_ok=True)
    summaries=[];raw={};validation=[]
    for tag,vdd,temp in CONDITIONS:
        dc,si=[load(run_id(tag,c)) for c in ['dc','sine']]
        raw[tag]=(dc,si)
        f=fit(si['frames']);d=dc['frames'];s=si['frames']
        checks={'dc':dc['checks'],'sine':dict(si['checks'],sine_fit_residual=f['residual_peak_uV']<=.25*LSB*1e6)}
        summary={'tag':tag,'vdd_V':vdd,'temperature_C':temp,'dc_run':dc['run_id'],'sine_run':si['run_id'],
          'checks':checks,'failed_checks':[c+':'+k for c,m in checks.items() for k,b in m.items() if not b],
          'first_precharge_min_V':min(r['frames'][0][k] for r in [dc,si] for k in ['precharge_P_V','precharge_N_V']),
          'all_precharge_min_fraction_VDD':min(row[k]/vdd for r in [dc,si] for row in r['frames'] for k in ['precharge_P_V','precharge_N_V']),
          'static_preclose_peak_mV':max(abs(x['preclose_diff_error_V']) for x in d)*1e3,
          'static_held_peak_mV':max(abs(x['held_diff_error_V']) for x in d)*1e3,
          'static_diff_turnoff_peak_mV':max(abs(x['turnoff_diff_change_V']) for x in d)*1e3,
          'static_single_end_step_range_mV':[fn(x[k]*1e3 for x in d for k in ['turnoff_P_change_V','turnoff_N_change_V']) for fn in [min,max]],
          'quiet_drift_peak_uV':max(abs(x['quiet_hold_drift_V']) for r in [dc,si] for x in r['frames'])*1e6,
          'feedthrough_peak_uV':max(abs(x['post_input_step_drift_V']) for r in [dc,si] for x in r['frames'])*1e6,
          'static_code_delta_peak':max(abs(x['code_delta']) for x in d),
          'sine_raw_error_peak_mV':max(abs(x['held_diff_error_V']) for x in s)*1e3,
          'sine_code_delta_peak':max(abs(x['code_delta']) for x in s),'sine_fit':f,'sine_fit_excluding_first':fit(s[1:]),
          'terminal_dc':worst_terminal(dc),'terminal_sine':worst_terminal(si),
          'sine_VDD_clock_uW':(si['power_W']['vdd']+si['power_W']['clock'])*1e6,'sine_input_uW':si['power_W']['input']*1e6,
          'native_dc':dc['native_state'],'native_sine':si['native_state'],
          'result_sha256':{c:r['result_sha256'] for c,r in [('dc',dc),('sine',si)]}}
        summaries.append(summary)
        for c,r in [('dc',dc),('sine',si)]:
            collected=R/'output/managed_execution/runs'/r['run_id']/'collected'
            native_log=(collected/'spectre.out').read_text(errors='replace')
            assert re.search(r'\btemp\s*=\s*'+re.escape(str(temp))+r'\s*C',native_log)
            state=json.loads((collected/'simulation.state.json').read_text())
            analysis=json.loads((collected/'analysis.state.json').read_text())
            assert len(r['frames'])==({'dc':8,'sine':16}[c])
            z=wave(r['run_id']);errs=[]
            for row in r['frames']:
                held=np.interp(row['sample_close_s']+1e-9,z['time'],z['xadc.topp']-z['xadc.topn'])
                errs.append(abs(held-row['held_diff_V']))
            # Keep the previous 0.1 uV display-agreement diagnostic visible.
            # SS can still be moving in the 100 ps display sampling interval;
            # reported measurements use the retained native snapshots instead.
            for row,snapshot in zip(r['frames'],r['snapshots']):
                h=snapshot['held']['values']
                assert abs(h['xadc.topp']-h['xadc.topn']-row['held_diff_V'])<1e-12
            for direction,first in [(True,110.025e-9),(False,149.975e-9)]:
                edges=[e[0] for e in r['edges']['clks'] if e[1]==direction]
                # Output is captured on the next sampling rise; the tail contains
                # one extra opening, but no extra completed sampling window.
                assert len(edges)==len(r['frames'])+(1 if direction else 0)
                assert all(abs(t-first-i*100e-9)<1e-14 for i,t in enumerate(edges))
            validation.append({'run_id':r['run_id'],'native_points':r['native_points'],'frame_count':len(r['frames']),
              'clock_edges_match':True,'wave_vs_native_held_max_error_V':max(errs),'display_agreement_within_original_0p1uV':bool(max(errs)<1e-7),'native_snapshot_consistency':True,'native_temperature_confirmed_C':temp,
              'simulation_elapsed_s':state.get('elapsed_seconds'),'simulation_peak_rss_bytes':state.get('peak_rss_bytes'),
              'analysis_peak_rss_bytes':analysis.get('peak_rss_bytes')})
    manifest=json.loads((OUT/'manifest.json').read_text())
    for case in manifest['runs']:
        for name,digest in case['source_sha256'].items():
            assert hashlib.sha256((R/case['directory']/name).read_bytes()).hexdigest()==digest
    result={'corners':summaries,'lsb_V':LSB,'scope':'8 DC + 16 sine frames per corner; TT reused. No noise, mismatch, PEX or FFT/ENOB. Static turnoff steps include injection/feedthrough. Single-frequency lag is not proven pure delay. Native CMI and conservative 1.98 V outer-terminal screen are not lifetime qualification.'}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'result_validation.json').write_text(json.dumps({'runs':validation,'frozen_inputs_unchanged':True},indent=2)+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    labels=['TT\n0.90 V\n27 C','SS cold\n0.81 V\n-40 C','SS hot\n0.81 V\n125 C','FF cold\n0.99 V\n-40 C','FF hot\n0.99 V\n125 C']
    colors=['#666666','#267d9b','#40a4a1','#c17b35','#b64b49'];xs=np.arange(5)
    fig,ax=plt.subplots(2,2,figsize=(12,9))
    metrics=[([x['static_held_peak_mV'] for x in summaries],'Static held differential error (mV)',.25*LSB*1e3),
      ([x['sine_fit']['effective_lag_ps'] for x in summaries],'Sine effective lag (ps)',None),
      ([x['sine_fit']['residual_peak_uV'] for x in summaries],'Sine fitted residual peak (uV)',.25*LSB*1e6),
      ([max(x['terminal_dc']['peak_V'],x['terminal_sine']['peak_V']) for x in summaries],'Maximum MOS terminal pair (V)',1.98)]
    for a,(ys,label,limit) in zip(ax.flat,metrics):
        a.bar(xs,ys,color=colors,width=.6)
        if limit is not None:a.axhline(limit,ls='--',color='#666666',label='Diagnostic screen');a.legend(fontsize=8)
        for i,y in enumerate(ys):a.annotate('%.3f'%y,(i,y),xytext=(0,5),textcoords='offset points',ha='center',fontsize=9)
        a.set(ylabel=label,xticks=xs,xticklabels=labels);a.margins(y=.2);a.grid(axis='y',alpha=.2)
    finish(fig,'01_corner_summary','Four risk corners compared with the selected TT candidate')
    fig,ax=plt.subplots(3,1,figsize=(12,10))
    for (tag,vdd,temp),color in zip(CONDITIONS,colors):
        r=raw[tag][0];z=wave(r['run_id']);t=z['time']*1e9;label='%s | %.2f V | %d C'%(tag.upper(),vdd,temp)
        m=t<=110.025
        ax[0].plot(t[m],((z['xadc.xp.xs.net2']-z['xadc.xp.xs.net3'])/vdd)[m],label=label,color=color)
        m=(t>=110)&(t<=151.5)
        err=(z['xadc.topp']-z['xadc.topn']-z['vinp']+z['vinn'])*1e3
        ax[1].plot(t[m],err[m],color=color)
        ax[2].plot(range(8),[x['turnoff_diff_change_V']*1e3 for x in r['frames']],'o-',label=label,color=color)
    ax[0].axhline(.95,ls='--',color='#777777');ax[0].set(ylabel='Cboot P / VDD',xlabel='Time after power ramp begins (ns)');ax[0].legend(ncol=2,fontsize=9)
    ax[1].set(ylabel='First-frame differential error (mV)',xlabel='Time (ns)',ylim=(-2,8));ax[1].axvline(149.975,ls=':',color='#777777');ax[1].text(.02,.9,'Early acquisition above 8 mV is clipped.',transform=ax[1].transAxes)
    ax[2].set(ylabel='Static differential turnoff step (mV)',xlabel='Static frame index')
    for a in ax:a.grid(alpha=.2)
    finish(fig,'02_startup_turnoff','Delayed startup, first-frame acquisition and static turnoff')
    fig,ax=plt.subplots(3,1,figsize=(12,10))
    for (tag,vdd,temp),color,summary in zip(CONDITIONS,colors,summaries):
        r=raw[tag][1];label='%s | %.2f V | %d C'%(tag.upper(),vdd,temp)
        ax[0].plot(range(16),[x['held_diff_error_V']*1e3 for x in r['frames']],'o-',color=color,label=label)
        ax[1].plot(range(16),summary['sine_fit']['residual_uV'],'o-',color=color)
        ax[2].plot(range(16),[x['code_delta'] for x in r['frames']],'o-',color=color)
    ax[0].set(ylabel='Raw sample error (mV)');ax[0].legend(ncol=3,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.02))
    ax[1].set(ylabel='After offset/gain/phase fit (uV)')
    ax[2].set(ylabel='Code minus matched ideal (LSB)',xlabel='Sine sample index (16 samples, no FFT/ENOB)');ax[2].axhline(1,ls='--',color='#777777');ax[2].axhline(-1,ls='--',color='#777777')
    for a in ax:a.grid(alpha=.2)
    finish(fig,'03_sine_error','4.501953125 MHz, -1 dBFS: raw error, fitted residual and code deviation')
    lines=['# 6 µm Bootstrap：极限工艺角短测','',
      '**结论：四个极限角的启动、静态采样和端压筛查均通过；SS冷、热角的高频码差分别达4码和3码，6 µm尚未全角合格。** SS冷角去掉首帧后仍约1.15 ns滞后，不能归为启动首帧问题。保持用户选择的6 µm候选，后续应优先定位SS动态跟踪，不把这轮结果直接推广到整机。','',
      '选用M0总宽6 µm（W=1 µm、multi=6、L=150 nm）；其余11管尺寸、12管拓扑、每侧1 pF自举电容保持不变。本页仅验证Bootstrap，比较器、SAR与参考切换均为理想行为模块，CDAC每侧等效1.28 pF。外部电源、输入、参考、时钟均为理想源。未修改OA或采用整机新基线。','',
      '电源1 ns上升；首个时钟110 ns开始，首次50%关闭沿149.975 ns，此后每100 ns重复，采样脉宽39.9 ns、边沿50 ps。参考固定0.9 V、输入共模0.45 V、差分满量程1.8 V，未随供电缩小。MOS宏角分别加载TT_18/SS_18/FF_18；其余被动模型段保持TT，测试电容为理想器件。','',
      '每角8个静态码中心＋16个4.501953125 MHz／−1 dBFS正弦样点；TT复用上一轮6 µm结果。LSB=7.03125 mV。','',
      '| 条件 | 静态保持误差峰 mV | 正弦原始误差峰 mV | 拟合滞后 ps | 拟合残差峰 µV | 最大码差 | 最大端压 V |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for x in summaries:
        lines.append('| %s / %.2f V / %d°C | %.3f | %.3f | %.1f | %.1f | %d | %.4f |'%(x['tag'],x['vdd_V'],x['temperature_C'],x['static_held_peak_mV'],x['sine_raw_error_peak_mV'],x['sine_fit']['effective_lag_ps'],x['sine_fit']['residual_peak_uV'],x['sine_code_delta_peak'],max(x['terminal_dc']['peak_V'],x['terminal_sine']['peak_V'])))
    lines+=['','![各角对比](figures/01_corner_summary.png)','','**保留的失败项**（阈值未放宽）：']
    for x in summaries:lines.append('- '+x['tag']+'：'+(', '.join(x['failed_checks']) if x['failed_checks'] else '本轮列出的诊断筛查均通过')+'。')
    lines+=['','静态保持误差在关闭沿后1 ns测量，相对关闭沿输入值；静态关断台阶取关闭前75 ps至关闭后1 ns，包含电荷注入与时钟馈通，不能只归于沟道注入。独立静态电容保持支路用于测量漂移，排除SAR正常电荷重分配。','',
      '正弦原始误差同样相对关闭沿输入值。拟合同时去掉偏置、增益和相位：残差小不等于原始采样精度通过；单频相位换算的滞后也不是已证明的纯延时。码差相对相同外部输入/时序的全理想对照。','',
      '![启动与关断](figures/02_startup_turnoff.png)','','| 条件 | 最小预充/VDD | 静态关闭前误差峰 mV | 静态差分关断台阶峰 mV | 保持漂移峰 µV | 输入更新馈通峰 µV |','|---|---:|---:|---:|---:|---:|']
    for x in summaries:lines.append('| %s | %.6f | %.6f | %.3f | %.3f | %.3f |'%(x['tag'],x['all_precharge_min_fraction_VDD'],x['static_preclose_peak_mV'],x['static_diff_turnoff_peak_mV'],x['quiet_drift_peak_uV'],x['feedthrough_peak_uV']))
    lines+=['','预充门槛为各角实际VDD的95%；静态关闭前误差≤0.1 LSB，保持误差≤0.25 LSB，漂移≤0.05 LSB，输入更新馈通≤0.25 LSB。低于数值容差的微小值不代表已验证该物理精度。','',
      '![高频误差](figures/03_sine_error.png)','','| 条件 | 拟合增益误差 % | 拟合偏置 µV | 去首帧滞后 ps | 去首帧残差峰 µV | VDD+时钟 µW | 输入源工作 µW |','|---|---:|---:|---:|---:|---:|---:|']
    for x in summaries:lines.append('| %s | %.5f | %.2f | %.1f | %.1f | %.3f | %.3f |'%(x['tag'],x['sine_fit']['gain_error_percent'],x['sine_fit']['offset_uV'],x['sine_fit_excluding_first']['effective_lag_ps'],x['sine_fit_excluding_first']['residual_peak_uV'],x['sine_VDD_clock_uW'],x['sine_input_uW']))
    lines+=['','功率取完整16个采样周期，不含最初供电启动能量；VDD与时钟功率只计被测Bootstrap，独立保持对照支路不计入。输入源工作单列，不是整机ADC功耗。','',
      '端压同时检查原生CMI与48个实例的六种外部MOS端压组合（包括独立保持支路），保守筛查值1.98 V。该筛查不是foundry寿命或SOA签核。','',
      '| 条件 / 测试 | 峰值 V | 时间 ns | 节点 | 对应器件/端对 |','|---|---:|---:|---|---|']
    for x in summaries:
        for case in ['dc','sine']:
            t=x['terminal_'+case]
            lines.append('| %s / %s | %.6f | %.6f | %s | %s |'%(x['tag'],case,t['peak_V'],t['peak_t_s']*1e9,', '.join(t['nodes']),'; '.join(d['path']+':'+d['pair'] for d in t['devices'])))
    lines+=['','Spectre21.1 X CX；实际reltol=1e−7、gear2only、maxstep=50 ps、vabstol=10 nV、iabstol=10 fA。电路较小，日志注明多线程关闭。原生告警与退出状态逐例保存在results.json；SFE-1131及VACOMP-2435未隐藏。所有测量使用完整原生时间点，显示波形才降采样。','',
      '本轮覆盖96个新增帧，另复用24个TT帧；不是完整PVT网格、全码扫描或FFT。未包含瞬态噪声、失配、PEX与真实比较器/SAR反冲。','',
      '显示波形校验：SS冷角100 ps降采样曲线在关闭后1 ns仍有弯曲，插值与原生测量最大相差6.361 µV，未达到原0.1 µV显示一致性目标，明确保留为未通过。表格全部取原生测量，并核对保存的原生快照；未用显示曲线重新算指标。其余条件该显示检查通过。','',
      '复现证据：[运行清单与输入散列](manifest.json) · [模型角核对](model_corner_check.json) · [数值与原生状态](results.json) · [逐帧边沿和波形校验](result_validation.json)。','']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps([{k:x[k] for k in ['tag','failed_checks','static_held_peak_mV','sine_raw_error_peak_mV','sine_code_delta_peak','sine_fit']} for x in summaries],indent=2))

if __name__=='__main__':main()

