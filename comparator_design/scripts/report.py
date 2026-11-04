"""Render small curated plots from collected, decimated waveforms and native metrics."""
import csv,gzip,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write

ORDER=['B0','I4','T4','R2','O4','P4']
TT='cmpdesign-sizing-tt-measure-v2'
RUNS=[('TT / 0.90 V / 27 C',TT),('SS / 0.81 V / -40 C','cmpdesign-b0-i4-ss-cold-v1'),
      ('SS / 0.81 V / 125 C','cmpdesign-b0-i4-ss-hot-v1'),('FF / 0.99 V / -40 C','cmpdesign-b0-i4-ff-cold-v1'),
      ('FF / 0.99 V / 125 C','cmpdesign-b0-i4-ff-hot-v1')]
COLORS={'B0':'#325d88','I4':'#d07c2c'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})

def load(run):return json.loads((W/'results'/run/'result.json').read_text())
def wave(run,start,end):
    path=ROOT/'output/managed_execution/runs'/run/'collected/derived/wave.csv.gz'
    out={}
    with gzip.open(path,'rt') as f:
        for row in csv.DictReader(f):
            t=float(row['time'])*1e9
            if t<start:continue
            if t>end:break
            for k,v in row.items():out.setdefault(k,[]).append(float(v))
    return out
def style(ax):ax.grid(True,alpha=.16);ax.set_axisbelow(True)
def save(fig,name):
    (W/'figures').mkdir(exist_ok=True)
    fig.savefig(W/'figures'/name,bbox_inches='tight');plt.close(fig)

def write_report(tt,available):
    lines=['# 比较器首轮尺寸与风险点测试','',
           '工作目录：`comparator_design/`。拓扑沿用用户手搭15MOS比较器，OA未改。当前结果只属于独立比较器；尚未选定最终尺寸。','',
           '## 测试条件','',
           '- 比较器晶体管级；外部电源、输入、时钟均理想；SAR、Bootstrap和真实CDAC未实例化。',
           '- 输出每侧6.1fF，来自TT下8个DFQD1 D端加OR2D4输入的动态Q/ΔV测量（6.012–6.049fF）；这是负载代理，不是全PVT上界。',
           '- 输入分低阻直接驱动和1.28pF/侧预充后断源两类。每类32次比较，CM=0.45/0.675/0.453516V；差分含±0.25/0.5/1LSB和大信号历史，LSB=7.03125mV。',
           '- 每100ns安排8次比较；高电平1.5ns，组内低电平约2.5ns，时钟边沿50ps。输出正确80%/20%的时限1ns，输出复位低于20%的时限0.5ns。',
           '- 下面表格为保持输入结果；直接驱动结果另存各run的result.json。残余扰动在下降沿开始前测量，峰值在评价阶段计算；复位反冲另见波形，未混入残余预算。',
           '- 模型、网表、激励、候选尺寸、保存节点和运行身份均在testbenches/、recipes/与results/。Spectre 21.1.0.509，CX、gear2only，实际reltol=1e-7、vabstol=10nV、iabstol=10fA、maxstep=20ps；小电路原生禁用多线程。','',
           '## TT尺寸对比','',
           'W/L参数保留100nm/30nm、nf=1，通过multi并联调宽；输入对4倍即等效总W=0.4µm。完整分组表见README.md。','',
           '| 候选 | 最慢判决 / ps | 最慢输出复位 / ps | 最大残余差模 / mV | 最大端压差 / V | 比较器供电均值 / µW |',
           '|---|---:|---:|---:|---:|---:|']
    for k in ORDER:
        r=tt['contexts'][k+'_held']
        lines.append(f"| {k} | {r['max_decision_s']*1e12:.2f} | {r['max_reset_s']*1e12:.2f} | {r['max_residual_V']*1e3:.5f} | {r['peak_terminal_V']:.6f} | {r['mean_comparator_supply_W']*1e6:.3f} |")
    lines += ['', 'TT六组在本轮32次判决及所列筛查中通过。原尺寸已经满足速度目标；增加输入对提高速度，也使残余输入扰动增大。暂以B0与I4作后续对照，没有证据支持直接选择最大尺寸。',
              '', '功耗是比较器自身电源在400ns内的平均供能，不含接收逻辑及输入源。TT测试台12个比较器共用理想时钟源的净供能均值为 %.4fµW；不是单个比较器时钟功耗。'%(tt['shared_testbench_clock_mean_W']*1e6),
              '', '![TT尺寸权衡](figures/tt_size_tradeoff.png)','', '![判决与复位波形](figures/tt_decision_waveform.png)','',
              '## 五风险点','',f'已回收 {len(available)}/5 个条件；每个条件比较B0/I4、直接/保持两种输入。MOS工艺角变化，理想R/C不带工艺变化。', '',
              '| 条件 | 候选 | 最慢判决 / ns | 最慢复位 / ns | 残余差模 / mV | 最大端压差 / V | 筛查结果 |',
              '|---|---|---:|---:|---:|---:|---|']
    for label,run,data in available:
        for k in ['B0','I4']:
            r=data['contexts'][k+'_held'];failed=[n for n,ok in r['screens'].items() if not ok]
            lines.append(f"| {label} | {k} | {r['max_decision_s']*1e9:.4f} | {r['max_reset_s']*1e9:.4f} | {r['max_residual_V']*1e3:.5f} | {r['peak_terminal_V']:.6f} | {','.join(failed) if failed else '本轮筛查通过'} |")
    if len(available)>1:lines+=['','![风险点对比](figures/five_point_screen.png)']
    fails=[]
    for label,run,data in available:
        warnings=data['native_state']['warning_codes']
        fails.append(f'- `{run}`：原生告警 `{", ".join(warnings)}`；全部端压差与超限持续时间保存在result.json。')
    if any(not r['screens']['terminal'] for _,_,d in available for r in d['contexts'].values()):
        lines+=['','**端压仍有未通过项，不能宣布比较器PVT合格。** FF冷、热角的原尺寸和I4都未通过端压筛查，功能、速度、输出复位和本轮残余预算通过。',
                '', '最大事件发生在比较时钟下降、进入复位的阶段：原先较高的LP/LN短暂高于0.99V，影响输出N管M12/M14的栅体/栅源端压，以及共用该节点的再生N管。输入对放大4倍仅稍降峰值，没有消除这一问题。',
                '', '原生日志和逐点端压确认这是独立比较器自身也能复现的问题，无须SAR标准单元存在。相邻内部节点复位上升与过冲同时发生，符合器件寄生电容耦合的解释；具体各支路贡献仍需电流或单变量实验区分，尚不能唯一归因于某一只晶体管。',
                '', '最坏端压图由独立analysis-only导出窗口内全部原生点，并核对峰值与完整扫描一致；其他展示图为约20ps抽点。',
                '', '![最坏端压事件](figures/worst_terminal_waveform.png)']
    lines+=['','## 原生日志与证据','']+fails+[
        '', '`cmpdesign-load-tt-v1`真实接收器负载测量仍有CMI-2751，属于接收标准单元内部端压；本轮等效电容测试没有解决它。SFE-1131是模型scalefactor重复设置告警，日志原样保留。',
        '', 'TT测量采用`cmpdesign-sizing-tt-measure-v2`，绑定已经完成的`cmpdesign-sizing-tt-v1`原始波形；只修正测量窗口和时间上界，没有重复仿真。原始v1测量保留，以v2为本报告依据。',
        '', '判决时间从时钟50%上升到最后一次不满足阈值之后的第一个持续正确原生点；评价窗口在下降沿开始前结束。复位按同样方式统计。按15个器件外部D/G/S/B引脚的六对端压逐原生点检查，0.99V为当前诊断筛查阈值；原生CMI补充模型内部端压检查，日志原样保留并另报越限时间。',
        '', '## 仍需完成','',
        '1. 结合FF超限的具体节点与阶段决定下一项单变量修改，功能正确不能替代端压通过。',
        '2. 补短复位时间、细小输入门限扫描与全共模轨迹。当前正负大信号历史测试不等于已证明0.05LSB记忆误差。',
        '3. 噪声、随机失配和失调预算尚未验证；小尺寸是否够用，必须由这些结果判断。',
        '4. 接回真实标准单元接收接口，再与理想其他模块组成闭环；本轮没有包含数字逻辑的反向耦合或CDAC逐位电荷重分配。',
        '', '不采用新整机基线，不改OA，不commit/push。后续继续在本目录工作。','']
    write(W/'RESULTS.md','\n'.join(lines))

def main():
    x=load(TT);ctx=x['contexts']
    fig,axs=plt.subplots(2,2,figsize=(10,6.8),layout='constrained')
    fields=[('max_decision_s',1e12,'Worst decision delay (ps)','Goal <= 1000 ps'),('max_reset_s',1e12,'Worst output reset (ps)','Goal <= 500 ps'),
            ('max_residual_V',1e3,'Held-input residual before reset (mV)','Provisional budget <= 0.703 mV'),
            ('mean_comparator_supply_W',1e6,'Comparator supply mean power (uW)','8 comparisons / 100 ns; clock excluded')]
    for ax,(field,scale,label,note) in zip(axs.flat,fields):
        vals=[ctx[k+'_held'][field]*scale for k in ORDER]
        ax.bar(ORDER,vals,color=[COLORS.get(k,'#8297a9') for k in ORDER]);ax.set_ylabel(label);style(ax)
        for i,v in enumerate(vals):ax.text(i,v,f'{v:.3g}',ha='center',va='bottom',fontsize=9)
        ax.set_ylim(0,max(vals)*1.27);ax.set_title(note,fontsize=10)
    fig.suptitle('Comparator sizing | TT, 0.90 V, 27 C\n15-MOS DUT; ideal sources/clock; 1.28 pF held inputs; 6.1 fF/output; no noise/mismatch/PEX',fontsize=11)
    save(fig,'tt_size_tradeoff.png')

    v=wave(TT,53.85,55.85);t=[z*1e9-54 for z in v['time']]
    fig,axs=plt.subplots(4,1,figsize=(9,8),sharex=True,layout='constrained')
    axs[0].plot(t,v['ck'],color='#455b66');axs[0].set_ylabel('Clock (V)')
    for ax,k in zip(axs[1:3],['B0','I4']):
        ax.plot(t,v[('OP'+k+'_held').lower()],label='OUT+');ax.plot(t,v[('ON'+k+'_held').lower()],label='OUT-',color='#d07c2c')
        ax.axhline(.72,color='gray',ls=':',lw=.8);ax.axhline(.18,color='gray',ls=':',lw=.8)
        ax.set_ylabel(k+' output (V)');ax.legend(loc='center right',ncol=2)
    for k in ['B0','I4']:
        dm=[(p-n-.0017578125)*1e3 for p,n in zip(v[('P'+k+'_held').lower()],v[('N'+k+'_held').lower()])]
        axs[3].plot(t,dm,label=k,color=COLORS[k])
    axs[3].set_ylabel('Input delta (mV)');axs[3].set_xlabel('Time from evaluation edge start (ns)');axs[3].legend(ncol=2)
    for ax in axs:
        ax.axvspan(0,1.5,color='#e1edf5',alpha=.5);ax.axvline(1.5,ls='--',color='gray',lw=.8);style(ax)
    axs[0].set_title('Evaluate (shaded); reset starts at 1.5 ns. Input delta is relative to applied +0.25 LSB.',fontsize=10)
    fig.suptitle('Representative decision and reset | TT, 0.90 V, 27 C\nCM = 0.45 V; +1.7578 mV input; ideal 50 ps clock; held 1.28 pF/side; 6.1 fF/output\n15-MOS DUT; no SAR logic, noise, mismatch or PEX',fontsize=11)
    save(fig,'tt_decision_waveform.png')

    available=[(label,run,load(run)) for label,run in RUNS if (W/'results'/run/'result.json').exists()]
    table=[]
    for label,run,data in available:
        for k in ['B0','I4']:
            r=data['contexts'][k+'_held']
            table.append({'condition':label,'run':run,'candidate':k,'decision_ns':r['max_decision_s']*1e9,
                          'reset_ns':r['max_reset_s']*1e9,'residual_mV':r['max_residual_V']*1e3,'terminal_V':r['peak_terminal_V'],
                          'power_uW':r['mean_comparator_supply_W']*1e6,'screens':r['screens']})
    write(W/'results/summary.json',json.dumps({'tt_measurement':TT,'risk_points_complete':len(available),'rows':table},indent=2)+'\n')
    if len(available)>1:
        fig,axs=plt.subplots(1,3,figsize=(12,4.6),layout='constrained')
        labels=[a[0].replace(' / ','\n') for a in available]
        for ax,(field,scale,ylabel,limit) in zip(axs,[('max_decision_s',1e9,'Decision delay (ns)',1),('max_residual_V',1e3,'Held residual (mV)',.703125),('peak_terminal_V',1,'Max terminal difference (V)',.99)]):
            for k in ['B0','I4']:
                vals=[d['contexts'][k+'_held'][field]*scale for _,_,d in available]
                ax.plot(range(len(labels)),vals,'o-',color=COLORS[k],label=k)
            ax.axhline(limit,ls='--',color='#b74444',lw=1,label='Screen limit');ax.set_xticks(range(len(labels)),labels,fontsize=8);ax.set_ylabel(ylabel);style(ax)
        axs[0].legend(fontsize=8)
        fig.suptitle('Five-point MOS process / supply / temperature screen\nIsolated 15-MOS comparator; fixed 0.9 V reference range; ideal stimuli; 6.1 fF/output; no noise/mismatch/PEX',fontsize=11)
        save(fig,'five_point_screen.png')
        worst=max([(r['peak_terminal_V'],label,run,k,data) for label,run,data in available for k,r in data['contexts'].items() if k.endswith('_held')],key=lambda a:a[0])
        peak,label,run,key,data=worst
        if peak>.99:
            pair,entry=max(data['contexts'][key]['terminal_pairs'].items(),key=lambda a:a[1]['peak_V'])
            native=data.get('source_run_id',run)
            cfg=json.loads((W/'testbenches'/native/'measure.json').read_text())
            context=next(c for c in cfg['contexts'] if c['name']==key)
            device,pins=pair.split(':');dev=next(d for d in context['devices'] if d['name']==device)
            nodes=[dev['nodes']['DGSB'.index(p)].lower() for p in pins]
            zoom_selection=W/'results/zoom_selection.json';zoom_run=run;full_native=False
            if zoom_selection.exists():
                sel=json.loads(zoom_selection.read_text())
                if sel['source_run_id']==native and (W/'results'/sel['run_id']/'result.json').exists():
                    zoom_run=sel['run_id'];full_native=True
            center=entry['time_s']*1e9;wv=wave(zoom_run,center-.35,center+.55);tt=[z*1e9 for z in wv['time']]
            values=[[0.]*len(tt) if node=='0' else wv[node] for node in nodes]
            fig,axs=plt.subplots(4,1,figsize=(9,8.5),sharex=True,layout='constrained')
            axs[0].plot(tt,wv['ck'],color='#455b66');axs[0].set_ylabel('Clock (V)')
            for node,vals in zip(nodes,values):axs[1].plot(tt,vals,label=node)
            axs[1].axhline(cfg['vdd'],ls=':',color='gray');axs[1].set_ylabel('Terminal voltage (V)');axs[1].legend(fontsize=8)
            for node in ['lp','ln','net1','net2']:
                axs[2].plot(tt,wv['x'+key.lower()+'.'+node],label=node)
            axs[2].set_ylabel('Internal nodes (V)');axs[2].legend(fontsize=8,ncol=4)
            axs[3].plot(tt,[abs(a-b) for a,b in zip(*values)],color='#b74444',label='|V'+pins+'|')
            axs[3].axhline(.99,ls='--',color='gray',label='0.99 V screen');axs[3].set_ylabel('Terminal difference (V)');axs[3].legend(fontsize=8)
            for ax in axs:style(ax);ax.axvline(center,ls=':',color='gray')
            axs[3].set_xlabel('Simulation time (ns)')
            sample_label='ALL native samples in window' if full_native else 'Decimated preview; peak not resolved'
            fig.suptitle(f'Largest observed comparator stress: {key}, {device}, V{pins}\n{label}; native peak = {peak:.6f} V; 1.28 pF/side; 6.1 fF/output\nIdeal sources and 50 ps clock; no SAR logic, noise, mismatch or PEX\n{sample_label}',fontsize=11)
            save(fig,'worst_terminal_waveform.png')
    print(json.dumps({'risk_points_complete':len(available),'rows':table},indent=2))
    write_report(x,available)

if __name__=='__main__':main()
