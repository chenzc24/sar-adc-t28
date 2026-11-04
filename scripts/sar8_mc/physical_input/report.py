"""Curated retained-sample comparison, native waveform figures and limitations."""
import csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';F=V/'figures'
def load(run):
    p=V/'results'/run/'result.json';d=json.loads(p.read_text());receipt=json.loads((R/'output/managed_execution/runs'/run/'collected/collection_receipt.json').read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==next(x['sha256'] for x in receipt['files'] if x['name']=='derived/result.json')
    assert d['analysis_complete'] and d['native_data_valid'];return d
def main():
    data={}
    tags=['nominal','s4121','s4124']
    for tag in tags:
        for mode in ['stiff','hold']:
            run='sar8phys-'+tag+'-'+mode+'-v2';data[run]=load(run)
    extras=['sar8phys-nominal-guard-v3','sar8phys-s4121-noinputmm-v1','sar8phys-s4124-noinputmm-v1','sar8phys-nominal-hold-rt7-v1']+['sar8phys-'+t+'-w2-v1' for t in tags]
    for run in extras:data[run]=load(run)
    # The original exact-zero nominal stiff search is preserved as invalid;
    # the separate +/-62.5uV physical measurement supplies its finite bound.
    assert not data['sar8phys-nominal-stiff-v2']['threshold_valid']
    assert data['sar8phys-nominal-guard-v3']['threshold_valid']
    results={};rows=[]
    for tag in tags:
        stiff=data['sar8phys-nominal-guard-v3' if tag=='nominal' else 'sar8phys-'+tag+'-stiff-v2'];hold=data['sar8phys-'+tag+'-hold-v2'];wide=data['sar8phys-'+tag+'-w2-v1']
        group=data.get('sar8phys-'+tag+'-noinputmm-v1')
        for d in [hold,wide]+([group] if group else []):assert d['threshold_valid']
        lo=max(stiff['held_threshold_interval_v'][0],hold['held_threshold_interval_v'][0]);hi=min(stiff['held_threshold_interval_v'][1],hold['held_threshold_interval_v'][1])
        def speed(d):
            p=d['first_pulses'][12:];return {'max_receiver_delay_ns':max((x['receiver_delay_s'] or 0)*1e9 for x in p),'unresolved':sum(x['receiver_delay_s'] is None for x in p),
              'peak_diff_change_mv':max(x['peak_diff_change_v'] for x in p)*1000,'peak_cm_change_mv':max(x['peak_cm_change_v'] for x in p)*1000}
        def full_window_kick(d):
            tr=np.asarray(d['trace']);peaks=[]
            for frame in [0,11,14]:
                origin=d['context']['first_clock_rise_s']+frame*d['context']['period_s'];q=tr[abs(tr[:,0]-origin)<1.15e-9]
                peaks.append(float(np.max(abs(q[:,1]-q[:,2]-d['first_pulses'][frame]['pre_vdiff_v'])))*1000)
            return max(peaks)
        h=hold['held_offset_midpoint_v']*1000;w=wide['held_offset_midpoint_v']*1000
        results[tag]={'stiff_threshold_mv':stiff['held_offset_midpoint_v']*1000,'held_threshold_mv':h,'input_pair_nominal_threshold_mv':group['held_offset_midpoint_v']*1000 if group else None,
          'width2_threshold_mv':w,'abs_threshold_reduction_percent':100*(1-abs(w/h)) if tag!='nominal' else None,
          'stiff_held_intervals_overlap':lo<=hi,'held_scope':hold['context']['scope'],'base_speed':speed(hold),'width2_speed':speed(wide),
          'base_selected_full_diff_kick_mv':full_window_kick(hold),'width2_selected_full_diff_kick_mv':full_window_kick(wide),
          'full_diff_kick_scope':'Three stored native windows frames0/11/14, including clock-fall reset; not all176pulses',
          'physical_held_cm_v_range':hold['held_pre_cm_v_range'],'main_vgs_pre_max_v':max(max(x['main_vgs_p_pre_v'],x['main_vgs_n_pre_v']) for x in hold['first_pulses'])}
        rows.append([tag,results[tag]['stiff_threshold_mv'],h,results[tag]['input_pair_nominal_threshold_mv'],w,results[tag]['base_speed']['max_receiver_delay_ns'],results[tag]['width2_speed']['max_receiver_delay_ns']])
    tight=data['sar8phys-nominal-hold-rt7-v1'];base=data['sar8phys-nominal-hold-v2']
    accuracy={'only_changed':'reltol1e-6 to1e-7','base_held_interval_v':base['held_threshold_interval_v'],'tight_held_interval_v':tight['held_threshold_interval_v'],
      'source_search_intervals_identical':base['source_threshold_interval_v']==tight['source_threshold_interval_v'],
      'threshold_midpoint_difference_uv':(tight['held_offset_midpoint_v']-base['held_offset_midpoint_v'])*1e6,
      'max_paired_speed_delay_difference_ps':max(abs(a['receiver_delay_s']-b['receiver_delay_s'])*1e12 for a,b in zip(base['first_pulses'][12:],tight['first_pulses'][12:])),
      'base_warning_codes':base['warning_codes'],'tight_warning_codes':tight['warning_codes']}
    warning_summary={run:d['warning_codes'] for run,d in data.items()}
    summary={'samples':['nominal',4121,4124],'comparison':results,'accuracy_check':accuracy,'all_retained_sample_checks_pass':True,'warnings':warning_summary,
      'original_dut_unchanged_sha256':hashlib.sha256((R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs').read_bytes()).hexdigest(),
      'effective_held_clamp_ohm':1e12,'resistor_clipping_drift_bound_v':1/1e12*40e-9/1e-12,
      'candidate_adopted':False,'scope':'Three selected latent samples, nominal added physical front-end, fixed bottom word and recorded native clock burst; not full SAR/30candidate seed statistics or yield',
      'invalid_nominal_midpoint_search_retained':'sar8phys-nominal-stiff-v2; exact-zero noiseless unresolved, finite bound from nominal-guard-v3'}
    assert summary['original_dut_unchanged_sha256']=='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
    (V/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (V/'comparison.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['sample','stiff_threshold_mv','held_threshold_mv','input_pair_nominal_threshold_mv','width2_threshold_mv','base_max_speed_ns','width2_max_speed_ns']);w.writerows(rows)
    F.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25})
    fig,ax=plt.subplots(2,2,figsize=(11,8),layout='constrained');x=np.arange(3)
    for j,(key,label) in enumerate([('stiff_threshold_mv','Stiff control'),('held_threshold_mv','Native hold'),('width2_threshold_mv','Input W x2')]):
        ax[0,0].plot(x+(j-1)*.06,[results[t][key] for t in tags],'o-',label=label)
    ax[0,0].plot([1,2],[results[t]['input_pair_nominal_threshold_mv'] for t in tags[1:]],'s--',label='Input mismatch removed')
    ax[0,0].axhline(0,color='grey',lw=.8);ax[0,0].set(xticks=x,xticklabels=['Nominal','Seed 4121','Seed 4124'],ylabel='Effective held-input threshold (mV)',title='Preserved-sample offset comparison');ax[0,0].legend(fontsize=8)
    for j,(key,label) in enumerate([('base_speed','Native hold'),('width2_speed','Input W x2')]):
        ax[0,1].bar(x+(j-.5)*.3,[results[t][key]['max_receiver_delay_ns'] for t in tags],width=.3,label=label)
    ax[0,1].axhline(base['context']['threshold_window_s']*1e9,color='C3',ls='--',label='Read deadline');ax[0,1].set(xticks=x,xticklabels=['Nominal','4121','4124'],ylabel='Receiver delay (ns)',title='Worst of tested +/-0.1/0.25/1 LSB first pulses');ax[0,1].legend(fontsize=8)
    for j,(key,label) in enumerate([('base_selected_full_diff_kick_mv','Native hold'),('width2_selected_full_diff_kick_mv','Input W x2')]):
        ax[1,0].bar(x+(j-.5)*.3,[results[t][key]*1000 for t in tags],width=.3,label=label)
    ax[1,0].set(xticks=x,xticklabels=['Nominal','4121','4124'],ylabel='Peak held differential change (uV)',title='Three saved windows, including clock-fall/reset kick');ax[1,0].legend(fontsize=8)
    for tag in tags:
        a=data['sar8phys-'+tag+'-hold-v2'];b=data['sar8phys-'+tag+'-w2-v1']
        ax[1,1].plot(np.arange(1,11),[p['receiver_delay_s']*1e9 if p['receiver_delay_s'] is not None else np.nan for p in a['first_pulses'][12:]],'o-',label=tag+' base')
        ax[1,1].plot(np.arange(1,11),[p['receiver_delay_s']*1e9 if p['receiver_delay_s'] is not None else np.nan for p in b['first_pulses'][12:]],'s--',label=tag+' W2')
    ax[1,1].set(xlabel='Defined speed probe (same input sequence)',ylabel='Receiver delay (ns)',title='First-pulse delay at each tested overdrive');ax[1,1].legend(fontsize=7,ncol=2)
    fig.suptitle('B comparator: native hold interface and one-variable W2 candidate | TT, 0.9 V\nNominal + two selected extremes; not a new 30-seed distribution')
    fig.savefig(F/'comparison.png',dpi=180);fig.savefig(F/'comparison.svg');plt.close(fig)
    fig,ax=plt.subplots(4,1,figsize=(10,9),sharex=True,layout='constrained')
    for run,label in [('sar8phys-s4124-stiff-v2','Stiff'),('sar8phys-s4124-hold-v2','Native hold'),('sar8phys-s4124-w2-v1','Input W x2')]:
        d=data[run];tr=np.asarray(d['trace']);origin=d['context']['first_clock_rise_s']+14*d['context']['period_s'];tr=tr[abs(tr[:,0]-origin)<1.15e-9];tt=(tr[:,0]-origin)*1e12
        ax[0].plot(tt,tr[:,4],label=label);ax[1].plot(tt,(tr[:,1]-tr[:,2]-d['first_pulses'][14]['pre_vdiff_v'])*1e6,label=label)
        ax[2].plot(tt,tr[:,5]-tr[:,6],label=label);ax[3].plot(tt,tr[:,7]-tr[:,8],label=label)
    for a,y in zip(ax,['Comparator clock (V)','Held differential change (uV)','Raw OP - ON (V)','Receiver PR - NR (V)']):a.set_ylabel(y);a.axvline(0,color='grey',lw=.8)
    ax[0].legend(ncol=3,fontsize=9);ax[-1].set_xlabel('Time relative to first clock half-supply crossing (ps)');ax[-1].set_xlim(-180,1100)
    fig.suptitle('Seed 4124, defined -0.1 LSB probe relative to each measured threshold\nNative waveforms; fixed eight-pulse burst, not full asynchronous feedback')
    fig.savefig(F/'waveforms.png',dpi=180);fig.savefig(F/'waveforms.svg');plt.close(fig)
    text='''# 比较器真实保持输入复现与单变量候选

结论：真实保持输入没有消除原比较器失调，输入对是主要来源。合法W2候选使两个
极端样本幅度分别降低15.7%%／20.2%%，仍约±20.18mV（约2.87LSB），尚不足以采用。
已测速度探针最坏判决时间由%.3fns降至%.3fns；三个保存窗口内、包含复位沿的
差分反冲峰值由%.3fmV增至%.3fmV，存在明确权衡。后续应继续优化输入对有效面积
并定位其余支路，不能将这三组当作新30seed标准差或良率。

原冻结B保持不变。本轮保留名义、seed4121和seed4124的同一组随机参数，接入原生
Bootstrap、18个MOM和CDAC开关；输入/参考50Ω与参考4pF旁路保留。外部时钟仍为
先低60ns、高40ns；内部时钟重放整机实测八脉冲。首脉冲宽0.7855ns，下降沿前50ps
读判决。固定N侧低参考、P侧高参考底板字，新增前端为名义器件，未接完整SAR反馈。

| 样本 | 低阻对照门限 | 真实保持门限 | 仅去掉输入对失配 | 输入宽度×2 |
|---|---:|---:|---:|---:|
'''%(max(results[t]['base_speed']['max_receiver_delay_ns'] for t in tags),max(results[t]['width2_speed']['max_receiver_delay_ns'] for t in tags),
      max(results[t]['base_selected_full_diff_kick_mv'] for t in tags),max(results[t]['width2_selected_full_diff_kick_mv'] for t in tags))
    for tag in tags:
        q=results[tag];g='—' if q['input_pair_nominal_threshold_mv'] is None else '%.3f mV'%q['input_pair_nominal_threshold_mv']
        text+='| %s | %.3f mV | %.3f mV | %s | %.3f mV |\n'%(tag,q['stiff_threshold_mv'],q['held_threshold_mv'],g,q['width2_threshold_mv'])
    text+='''
原始极端样本接入保持输入后，门限与低阻对照区间重叠，差异小于0.125mV搜索
分辨率；有限保持/反冲没有消除数十mV失调。输入对名义化后幅度明显缩小，说明
输入对是主要来源，其余支路仍有残余。分组试验核对其余89行随机参数完全一致，
完整比较及W2候选核对91行完全一致；没有仅凭相同seed号假定同样本。

W2只改两只输入管的宽度1µm→2µm，L=30nm、nf/multi不变，扩散面积/周长/方块数
按该宽度派生。仅测试这三个选定样本，未重新测30seed标准差、PVT、完整ADC或功耗，
没有采用为基线。速度/反冲及具体改善量见summary.json；不能据三组宣布良率通过。

![比较结果](figures/comparison.png)

![原生波形](figures/waveforms.png)

名义低阻台恰好0V差分时，无噪声、对称电路未在判决窗内决出符号，原二分搜索
如实保留为无效门限。另用±62.5µV两帧均正确判决，将名义门限约束在该区间，
没有强行给0V指定输出。保持前主管VGS为负，源与顶板未被VA直接钳住。

数值复核只将名义保持台reltol从1e-6收紧到1e-7，其余不变。门限区间、速度差异
及真实告警见summary.json，所有原始LTE告警保留。CMI-2732在这里指诊断钳位电阻
1e18Ω被截为1e12Ω，并非端压告警；按实际1e12Ω解释，即使1V压差保持40ns、1pF
电容，泄漏漂移上界也仅0.04µV。原脚本限制继承导致的三个分析启动失败、网络
中断和初组源共模误设0.449V均保留；通过绑定原完成源补分析，未重跑这些仿真。

宽度4µm的三组尝试因超出模型Wmax=2.7001µm而在瞬态前被拒绝（CMI-2440），失败记录保留；本报告的有效候选为2µm。
完整运行身份和回收哈希见各results目录及collections文件。端压可靠性未签核。
'''
    (V/'README.md').write_text(text,encoding='utf-8');print(json.dumps(summary['comparison']));print(json.dumps(accuracy))
if __name__=='__main__':main()
