"""Summarize collected native PT results without loading raw waveforms."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parents[1]
records=[]
for tag in ['tt','ff-cold','ff-hot','ss-cold','ss-hot']:
    for multi in [4,8]:
        run=f'cmpdesign-pt09-a{multi}-{tag}-v1';p=W/'results'/run/'result.json'
        if not p.exists():continue
        d=json.loads(p.read_text());cfg=json.loads((W/'testbenches'/run/'measure.json').read_text())
        assert d['source_run_id']==run and d['native_state']['zero_error_footer']
        cs=list(d['contexts'].values());assert len(cs)==2 and all(len(c['rows'])==32 and len(c['terminal_pairs'])==90 for c in cs)
        sim=json.loads((p.parent/'simulation.state.json').read_text());ana=json.loads((p.parent/'analysis.state.json').read_text())
        assert sim['status']==ana['status']=='complete' and sim['exit_code']==ana['exit_code']==0
        assert sim['peak_rss_bytes']<=1024*2**20 and ana['peak_rss_bytes']<=256*2**20
        h=d['contexts']['A4_held']
        worst=max(((v['peak_V'],ctx,k,v) for ctx,c in d['contexts'].items() for k,v in c['terminal_pairs'].items()),key=lambda x:x[0])
        records.append(dict(run_id=run,tag=tag,multi=multi,temp=cfg['temperature_c'],corner=cfg['corner'],
          peak_V=worst[0],worst_context=worst[1],worst_pair=worst[2],worst_time_ns=worst[3]['time_s']*1e9,
          worst_pair_overlimit_ps=worst[3]['time_above_s']*1e12,
          fail_pair_count=sum(len(c['stress_fail_pairs']) for c in cs),
          correct=sum(sum(x['decision_good'] for x in c['rows']) for c in cs),
          resets=sum(sum(x['reset_good'] for x in c['rows']) for c in cs),
          decision_ps=max(c['max_decision_s'] for c in cs)*1e12,
          reset_from_fall_start_ps=(max(c['max_reset_s'] for c in cs)+250e-12)*1e12,
          held_power_uW=h['mean_comparator_supply_W']*1e6,
          diff_kick_mV=max(x['full_edge_diff_kick_V'] for x in h['rows'])*1e3,
          cm_kick_mV=max(x['full_edge_cm_kick_V'] for x in h['rows'])*1e3,
          internal_reset_mV=max(x['internal_reset_max_error_V'] or 0 for x in h['rows'])*1e3,
          residual_mV=h['max_residual_V']*1e3,
          node_overshoot_mV=(max(v['peak_V'] for v in h['phase_node_peaks'].values())-.9)*1e3,
          resources=dict(sim_seconds=sim['elapsed_seconds'],sim_rss_MiB=sim['peak_rss_bytes']/2**20,analysis_seconds=ana['elapsed_seconds'],analysis_rss_MiB=ana['peak_rss_bytes']/2**20),
          screens={k:all(c['screens'][k] for c in cs) for k in h['screens']},native=d['native_state']))
out=W/'results/cmpdesign-pt09-summary';out.mkdir(exist_ok=True)
(out/'summary.json').write_text(json.dumps(records,indent=2)+'\n')
if not records:raise SystemExit('No collected results yet')
lines=['# 比较器：0.9 V 下的 PT 验证','',f'已回收 **{len(records)}/10** 个案例。'+('全部完成。' if len(records)==10 else '其余未完成，以下仅列已完成证据。'),'',
'两版 M2/M4 分别为4/8份，M3/M5、M8/M9均为2份，其余1份；每份W100nm、L30nm、nf1。',
'输入历史、输出6.1fF/侧、保持电容1.28pF/侧、时钟上升200ps/下降500ps不变。每点400ns，直接驱动/保持输入各32次判决。外部源理想。',
'','| PT | 倍数 | 最坏端差 V | 正确判决/复位 | 最慢判决 ps | 输出复位 ps | 功率 µW | 筛查 |','|---|---:|---:|---|---:|---:|---:|---|']
for r in records:
    fail=[k for k,v in r['screens'].items() if not v]
    lines.append(f"|{r['corner'].upper()} / {r['temp']}°C|{r['multi']}|{r['peak_V']:.6f}|{r['correct']}/64；{r['resets']}/64|{r['decision_ps']:.2f}|{r['reset_from_fall_start_ps']:.2f}|{r['held_power_uW']:.3f}|{', '.join(fail) if fail else '通过'}|")
lines+=['','端压上限仍为0.99V；判决≤1ns，输出复位按50%下降沿后0.5ns、保持差模残差≤0.703125mV、供电功率≤100µW。表中判决相对上升50%，复位相对实际下降开始。功率仅保持输入比较器的供电积分平均，不含理想输入/时钟或ADC其他模块。','',
'| PT | 倍数 | 内部上冲 mV（相对0.9V） | 差模反冲 mV | 共模反冲 mV | 内部复位残差 mV | 超限端对数 |',
'|---|---:|---:|---:|---:|---:|---:|']
for r in records:lines.append(f"|{r['corner'].upper()} / {r['temp']}°C|{r['multi']}|{r['node_overshoot_mV']:.3f}|{r['diff_kick_mV']:.4f}|{r['cm_kick_mV']:.4f}|{r['internal_reset_mV']:.4f}|{r['fail_pair_count']}|")
lines+=['','内部上冲取既有评估/复位事件窗口；所有MOS六种端差的电气筛查覆盖全程原生采样。反冲覆盖整个时钟上升至复位开始；内部复位残差测于下降50%后0.5ns。','',
'![PT对比](figures/pt09_summary.png)','',
'## 核验与范围','',
'每项均检查原生零错误退出、400ns终点、180个端对（15管×6端对×2输入模式）。CMI/SFE日志仍保留，原生日志通过不等于电气合格。',
'Spectre 21.1 X CX；实际单线程、reltol=1e−7、vabstol=10nV、iabstol=10fA、maxstep=20ps、gear2only。各运行精确设置保存在结构化汇总。',
'候选不是整机/OA基线；原0.81–0.99V供电要求不变。未包含噪声、失配、PEX，也未接真实SAR接收器。本批通过不能覆盖全部输入共模、最短复位历史或整机PVT。','',
'首个4倍TT的冻结measure.json保留了旧candidates描述字段；实际DUT与来源字节一致，pt09_provenance及recipe准确标识本次组合尺寸，分析器不读取该旧字段。其余案例注册前已纠正该描述。','',
'[结构化指标及原生设置](results/cmpdesign-pt09-summary/summary.json) · [原4倍FF/0.99V](EDGE_COMBO.md) · [原8倍FF/0.99V](COMBO_A8.md)','']
for r in records:
    lines.append(f"- `{r['run_id']}`：[原生结果](results/{r['run_id']}/result.json)，告警 {', '.join(r['native']['warning_codes']) or '无'}。")
if len(records)==10:
    allpass=all(all(r['screens'].values()) for r in records)
    lines.insert(3, '\n**这两个组合尺寸在所测0.9V的五个PT点均通过本模块筛查。**' if allpass else '\n**存在未通过项，不能宣布全部通过；见表中失败分类。**')
    lines+=['','## 与原0.99V FF热角对照','',
      '| M2/M4倍数 | 0.99V最坏端差 | 0.9V最坏端差 |','|---|---:|---:|']
    for multi,oldrun in [(4,'cmpdesign-edge-b2i2-ff-hot-v1'),(8,'cmpdesign-combo-a8-ff-hot-v1')]:
        old=json.loads((W/'results'/oldrun/'result.json').read_text())
        oldpeak=max(c['peak_terminal_V'] for c in old['contexts'].values())
        r=next(x for x in records if x['tag']=='ff-hot' and x['multi']==multi)
        lines.append(f"|{multi}|{oldpeak:.6f}V|{r['peak_V']:.6f}V|")
    lines+=['','降低供电留下了端压裕量，并不表示寄生耦合消失，也不能据此认为0.99V问题已修复。']
(W/'PT_09V.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
fig,axs=plt.subplots(1,3,figsize=(12.6,3.8),layout='constrained')
tags=['tt','ff-cold','ff-hot','ss-cold','ss-hot'];labels=['TT\n27°C','FF\n−40°C','FF\n125°C','SS\n−40°C','SS\n125°C']
for ax,key,title,ylabel in zip(axs,['peak_V','decision_ps','held_power_uW'],['Maximum terminal voltage','Slowest decision','Comparator supply power'],['V','ps','µW']):
    for multi,color in [(4,'#2878b5'),(8,'#dd8452')]:
        rr=[r for r in records if r['multi']==multi]
        ax.plot([tags.index(r['tag']) for r in rr],[r[key] for r in rr],'o-',color=color,label=f'M2/M4 ×{multi}')
    ax.set_xticks(range(5),labels);ax.set_title(title);ax.set_ylabel(ylabel);ax.grid(alpha=.2)
axs[0].axhline(.99,color='#bb3333',ls='--',label='0.99 V limit');axs[0].legend(fontsize=8)
fig.suptitle(f'0.9 V | 200/500 ps clock edges | 6.1 fF/output | {len(records)}/10 cases',fontsize=12)
(W/'figures').mkdir(exist_ok=True);fig.savefig(W/'figures/pt09_summary.png',dpi=180);plt.close(fig)
print(json.dumps([{k:r[k] for k in ['run_id','peak_V','correct','resets','decision_ps','screens']} for r in records],indent=2))
