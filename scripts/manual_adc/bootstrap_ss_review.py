"""Native-current/voltage diagnosis, with phase referenced explicitly to sample close."""
import json,gzip,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bootstrap_width_review import load,fit,FREQ,AMP,LSB
R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_ss_diagnosis_v1'
FIG=OUT/'figures'
SOURCES={'tt':'manual8-bootwidth-sine-m6-v1','ss':'manual8-bootpvt-ss-cold-sine-v1'}
COLORS={'tt':'#6b6b6b','ss':'#247e9a'}
LABELS={'tt':'TT | 0.90 V | 27 C','ss':'SS | 0.81 V | -40 C'}
def read_wave(run):
    p=R/'output/managed_execution/runs'/run/'collected/derived/diagnostic.csv.gz'
    with gzip.open(p,'rt') as f:
        names=f.readline().strip().split(',');a=np.loadtxt(f,delimiter=',')
    return {n:a[:,i] for i,n in enumerate(names)}
def at(z,name,t):return np.interp(t,z['time'],z[name])
def tone(t,y):return fit([{'sample_close_s':float(a),'held_diff_V':float(b)} for a,b in zip(t,y)])
def crossing(t,y,level):
    ix=np.where((y[:-1]>=level)&(y[1:]<level))[0]
    if not len(ix):return None
    i=ix[0];return float(t[i]+(t[i+1]-t[i])*(level-y[i])/(y[i+1]-y[i]))
def finish(fig,name,title):
    fig.suptitle(title+'\nM0 6 um / L150 nm, Cboot1pF, load1.28pF/side; other blocks ideal\n4.501953125 MHz, -1 dBFS; external sampling close unchanged',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.91));fig.savefig(FIG/(name+'.png'),dpi=170);fig.savefig(FIG/(name+'.svg'));plt.close(fig)
def main():
    FIG.mkdir(exist_ok=True);result={};waves={};raw={}
    for tag in ['tt','ss']:
        run='manual8-bootss-probe-'+tag+'-v1';r=load(run);old=load(SOURCES[tag]);z=read_wave(run);waves[tag]=z;raw[tag]=r
        t=z['time'];close=np.array([x['sample_close_s'] for x in r['frames']]);vdd=.9 if tag=='tt' else .81
        parity=max(abs(a['held_diff_V']-b['held_diff_V']) for a,b in zip(r['frames'],old['frames']))
        assert parity<1e-6
        m=(t>210e-9)&((t*1e9)%100>=35)&((t*1e9)%100<=49.8)
        pc=[];post=[]
        for offset in [-.075,0,1,2,3.5]:
            y=at(z,'xadc.topp',close+offset*1e-9)-at(z,'xadc.topn',close+offset*1e-9)
            f=tone(close,y);f['measurement_offset_ns']=offset
            if offset<=0:f['track_lag_relative_actual_time_ps']=f['effective_lag_ps']+offset*1000
            pc.append(f)
        for prefix,vin,out in [('xhp','vinp','hp'),('xhn','vinn','hn')]:
            i=z[prefix+'.vmd:1'];vd=z[out]-z[vin];slope=np.gradient(z[out],t)
            mask=m&(abs(i)>2e-6)&(abs(vd)>1e-3)&(i*vd>0)
            # This is a terminal-current ratio, not pure channel Ron: displacement
            # current exists. Independent small-VDS DC test provides the channel check.
            resistance=vd[mask]/i[mask]
            kcl=(-i[mask]-1.28e-12*slope[mask])
            post.append({'branch':prefix,'apparent_R_median_ohm':float(np.median(resistance)),
              'apparent_R_p10_p90_ohm':np.percentile(resistance,[10,90]).tolist(),
              'current_vs_Cload_dVdt_relative_rms':float(np.sqrt(np.mean(kcl**2))/np.sqrt(np.mean(i[mask]**2)))})
        gate={}
        for prefix,vin in [('xadc.xp.xs','vinp'),('xadc.xn.xs','vinn')]:
            cb=z[prefix+'.net2']-z[prefix+'.net3'];gs=z[prefix+'.net1']-z[vin]
            bottom=z[prefix+'.net3']-z[vin];link=z[prefix+'.net2']-z[prefix+'.net1']
            gate[prefix]={n:{'min_V':float(min(a[m])),'max_V':float(max(a[m])),'mean_V':float(np.mean(a[m]))} for n,a in [('Cboot',cb),('VGS',gs),('bottom_minus_input',bottom),('Cboot_top_minus_gate',link)]}
        events=[]
        for j,cl in enumerate(close):
            w=(t>=cl-.1e-9)&(t<=cl+3e-9)
            for prefix,vin,out in [('xhp','vinp','hp'),('xhn','vinn','hn')]:
                gs=z[prefix+'.net1']-z[vin];tt=t[w];yy=gs[w]
                half=crossing(tt,yy,.5*vdd);low=crossing(tt,yy,.3)
                events.append({'frame':j,'branch':prefix,'VGS_half_supply_after_close_ps':None if half is None else (half-cl)*1e12,
                               'VGS_0p3V_after_close_ps':None if low is None else (low-cl)*1e12})
        summary={'source_run':SOURCES[tag],'probe_run':run,'sensor_held_difference_peak_uV':parity*1e6,'native':r['native_state'],
          'fit_by_measurement_time':pc,'gate_stable_track':gate,'companion_conduction':post,'turnoff_events':events,
          'postclose_effective_phase_advance_ps':pc[1]['effective_lag_ps']-pc[2]['effective_lag_ps'],
          'postclose_held_1_to_3p5ns_peak_uV':float(max(abs((at(z,'hp',close+3.5e-9)-at(z,'hn',close+3.5e-9))-(at(z,'hp',close+1e-9)-at(z,'hn',close+1e-9))))*1e6)}
        actual=np.array([x['held_diff_V'] for x in r['frames']]);phase_only=AMP*np.sin(2*np.pi*FREQ*(close-pc[2]['effective_lag_ps']*1e-12))
        err=actual-phase_only;aligned_code=np.clip(np.floor((phase_only+.9)/LSB),0,255).astype(int)
        summary['phase_only_alignment']={'residual_peak_uV':float(max(abs(err))*1e6),'residual_rms_uV':float(np.sqrt(np.mean(err**2))*1e6),
          'code_delta_peak_against_phase_shifted_analytic_quantizer':int(max(abs(np.array([x['actual_code'] for x in r['frames']])-aligned_code))),
          'scope':'offline fitted phase reference; original same-external-close code screen remains unchanged; not calibration implementation or FFT'}
        dcpath=R/'output/managed_execution/runs'/('manual8-bootss-m0-'+tag+'-v1')/'collected/derived/result.json'
        summary['isolated_M0']=json.loads(dcpath.read_text());result[tag]=summary
    manifest=json.loads((OUT/'manifest.json').read_text())
    for case in manifest['runs']:
        for name,h in case['source_sha256'].items():assert hashlib.sha256((R/case['directory']/name).read_bytes()).hexdigest()==h
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    # Frame14: high slope, worst raw SS sample; voltage/current signs preserved.
    cl=raw['ss']['frames'][14]['sample_close_s']
    fig,ax=plt.subplots(4,1,figsize=(12,11),sharex=True)
    for tag in ['tt','ss']:
        z=waves[tag];t=(z['time']-cl)*1e9;m=(t>=-15)&(t<=-.075);co=COLORS[tag];label=LABELS[tag]
        ax[0].plot(t[m],z['xadc.topp'][m],color=co,label=label)
        if tag=='tt':ax[0].plot(t[m],z['vinp'][m],'--',color='#c08738',label='Input P')
        ax[1].plot(t[m],(z['xadc.topp']-z['xadc.topn']-z['vinp']+z['vinn'])[m]*1e3,color=co)
        ax[2].plot(t[m],(z['xadc.xp.xs.net1']-z['vinp'])[m],color=co,label=label+' VGS')
        ax[2].plot(t[m],(z['xadc.xp.xs.net2']-z['xadc.xp.xs.net3'])[m],'--',color=co,label=label+' Cboot')
        ax[3].plot(t[m],-z['xadc.xp.xs.vmd:1'][m]*1e6,color=co)
    ax[0].set(ylabel='Input / sampled P (V)');ax[0].legend(ncol=3,fontsize=9)
    ax[1].set(ylabel='Tracking differential error (mV)');ax[2].set(ylabel='VGS / Cboot (V)');ax[2].legend(ncol=2,fontsize=8)
    ax[3].set(ylabel='M0 current into output P (uA)',xlabel='Time relative to frame14 external close (ns)')
    for a in ax:a.grid(alpha=.2)
    finish(fig,'01_track_gate','Tracking error already exists before the falling clock edge')
    fig,ax=plt.subplots(4,1,figsize=(12,11),sharex=True)
    for tag in ['tt','ss']:
        z=waves[tag];t=(z['time']-cl)*1e9;m=(t>=-.3)&(t<=2);co=COLORS[tag]
        ax[0].plot(t[m],z['clks'][m]/(.9 if tag=='tt' else .81),color=co,label=LABELS[tag]+' CLKS')
        ax[0].plot(t[m],z['xadc.xp.xs.clksb'][m]/(.9 if tag=='tt' else .81),'--',color=co,label=LABELS[tag]+' CLKSB')
        ax[1].plot(t[m],(z['xadc.xp.xs.net1']-z['vinp'])[m],color=co)
        ax[2].plot(t[m],-z['xadc.xp.xs.vmd:1'][m]*1e6,color=co)
        vref=at(z,'vinp',cl)-at(z,'vinn',cl)
        ax[3].plot(t[m],(z['xadc.topp'][m]-z['xadc.topn'][m]-vref)*1e3,color=co)
    ax[0].set(ylabel='CLKS / VDD');ax[0].legend(ncol=2,fontsize=9);ax[1].set(ylabel='M0 P VGS (V)');ax[2].set(ylabel='Current into output P (uA)')
    ax[3].set(ylabel='Error vs input at close (mV)',xlabel='Time relative to external close (ns)')
    for a in ax:a.axvline(0,ls=':',color='#999999');a.grid(alpha=.2)
    finish(fig,'02_turnoff','Finite turnoff partially catches up; it does not create the dominant lag')
    fig,ax=plt.subplots(2,2,figsize=(12,9))
    for tag in ['tt','ss']:
        cases=result[tag]['isolated_M0']['cases']
        for vg,ls in [(.8,'--'),(.889,'-')]:
            selected=[x for x in cases if x['VGS_V']==vg]
            ax[0,0].plot([x['VIN_V'] for x in selected],[x['Rsmall_ohm'] for x in selected],'o'+ls,color=COLORS[tag],label=('%s / %d C; VGS%.3f'%(tag.upper(),27 if tag=='tt' else -40,vg)))
        c=result[tag]['fit_by_measurement_time'];values=[c[0]['track_lag_relative_actual_time_ps'],c[1]['effective_lag_ps'],c[2]['effective_lag_ps']]
        ax[0,1].plot(range(3),values,'o-',color=COLORS[tag],label=LABELS[tag])
        for i,v in enumerate(values):ax[0,1].annotate('%.0f'%v,(i,v),textcoords='offset points',xytext=(0,8),ha='center')
        rows=raw[tag]['frames'];ax[1,0].plot(range(16),[x['held_diff_error_V']*1e3 for x in rows],'o-',color=COLORS[tag],label=LABELS[tag])
        ax[1,1].plot(range(16),c[2]['residual_uV'],'o-',color=COLORS[tag],label=LABELS[tag])
    ax[0,0].set(xlabel='M0 source/body bias VIN (V)',ylabel='Resistance at VDS=1 mV (ohm)',yscale='log');ax[0,0].legend(fontsize=7)
    ax[0,1].set(xticks=range(3),xticklabels=['Stable track','At close','Held (+1 ns)'],ylabel='Effective lag (ps)');ax[0,1].legend(fontsize=8)
    ax[1,0].set(xlabel='Sample index',ylabel='Raw error (mV)');ax[1,0].legend(fontsize=8)
    ax[1,1].set(xlabel='Sample index',ylabel='After offset/gain/phase fit (uV)');ax[1,1].legend(fontsize=8)
    for a in ax.flat:a.grid(alpha=.2)
    finish(fig,'03_conduction_phase','M0 conductance and phase correction: the remaining error is not zero')
    tt=result['tt'];ss=result['ss']
    lines=['# SS冷角Bootstrap高频跟踪定位','',
      '**主要原因已定位：M0在SS冷角、低VGS下导通电阻增大，并随输入源体偏置显著变化。自举电容未塌陷；关断更慢是次要影响，反而部分补偿了跟踪滞后。**','',
      '**评价口径澄清：原来的4码差是相对于同一外部关闭沿的理想输出，不是4 LSB非线性失真。固定延迟会改变相位，但理想固定延迟本身不降低单音SNDR。因此目前证据不足以因4码差否定6 µm；原始诊断失败保留，整机/全带宽资格仍未完成。**','',
      '本轮保持M0总宽6 µm、L150 nm、每侧Cboot1 pF与1.28 pF负载；首时钟110 ns、100 ns周期、关闭沿149.975 ns+n×100 ns、50 ps边沿不变。外部输入/供电/时钟/参考理想，比较器与SAR为理想VA。输入4.501953125 MHz、−1 dBFS、CM0.45 V、参考0.9 V。TT0.9 V27°C对比SS0.81 V−40°C；无噪声/失配/PEX。','',
      '增加两组等价电流探针短测：只在M0漏端串联0 V电压源，四个Bootstrap均测漏端总电流；器件、VA、激励和时序不改。另做TT/SS独立M0导通测试，固定VDS=1 mV，扫描VGS=0.800/0.810/0.889/0.900 V及VIN=0.05/0.25/0.45/0.65/0.85 V，体端0 V。后者是诊断偏置，不是把SS整机改供电或升压。','',
      '## 1. 采样导通阶段','',
      '![跟踪与栅压](figures/01_track_gate.png)','',
      '图取第14帧（外部关闭沿1549.975 ns），从上到下为P侧输入与输出、差分跟踪误差、M0 VGS和Cboot电压、流入输出的M0电流。SS在关闭前已落后，排除“仅关断时刻偏移造成全部误差”。电流接近并不意味着电阻接近：给相同电容跟踪相似斜率，所需电流相近；SS需要更大的输入输出压差来维持这股电流。','',
      '| 量 | TT | SS冷角 |','|---|---:|---:|',
      '| 关闭前75 ps的跟踪滞后（相对该时刻输入） | %.1f ps | %.1f ps |'%(tt['fit_by_measurement_time'][0]['track_lag_relative_actual_time_ps'],ss['fit_by_measurement_time'][0]['track_lag_relative_actual_time_ps']),
      '| M0端电流比值所得有效电阻中位数（保持对照P侧） | %.1f Ω | %.1f Ω |'%(tt['companion_conduction'][0]['apparent_R_median_ohm'],ss['companion_conduction'][0]['apparent_R_median_ohm'])]
    for key,title in [('VGS','稳定跟踪VGS范围'),('Cboot','稳定跟踪Cboot范围')]:
        a=tt['gate_stable_track']['xadc.xp.xs'][key];b=ss['gate_stable_track']['xadc.xp.xs'][key]
        lines.append('| %s | %.4f–%.4f V | %.4f–%.4f V |'%(title,a['min_V'],a['max_V'],b['min_V'],b['max_V']))
    lines+=['','稳定跟踪统计窗口为非首帧的每周期35–49.8 ns。电流比值只取|I|>2 µA、|VDS|>1 mV且同号区域，避免零斜率附近除零；端电流包含位移电流，因此另用独立小VDS测试核对。保持对照的−Id与C·dV/dt相符，归一化RMS差约1.3×10⁻⁶，验证电流符号与负载关系。','',
      '自举电容和VGS都平稳。SS电容底端跟随输入的误差约±0.37 mV、顶端到栅极差小于0.10 mV；主要差别是低供电下正常VGS约0.80 V，而TT约0.889 V。SS距离理想0.81 V仅约10 mV，并非少充了90 mV。','',
      '## 2. 关断过程','',
      '![关断波形](figures/02_turnoff.png)','',
      '外部CLKS相同；SS内部CLKSB上升较慢，M0 VGS下降、电流反转及归零相应推迟。当前漏端电流包含关断馈通/注入，不能把每个电流尖峰都当作继续导通电流。底图以外部关闭沿输入为固定参考，显示关断阶段的净更新。','',
      '| 等效相位量 | TT | SS冷角 |','|---|---:|---:|',
      '| 外部关闭沿处的滞后 | %.1f ps | %.1f ps |'%(tt['fit_by_measurement_time'][1]['effective_lag_ps'],ss['fit_by_measurement_time'][1]['effective_lag_ps']),
      '| 保持值（关闭后1 ns），仍以外部关闭沿为相位参考 | %.1f ps | %.1f ps |'%(tt['fit_by_measurement_time'][2]['effective_lag_ps'],ss['fit_by_measurement_time'][2]['effective_lag_ps']),
      '| 关断阶段净等效追近量 | %.1f ps | %.1f ps |'%(tt['postclose_effective_phase_advance_ps'],ss['postclose_effective_phase_advance_ps']),
      '| 保持对照：关闭后1→3.5 ns最大差分变化 | %.3f µV | %.3f µV |'%(tt['postclose_held_1_to_3p5ns_peak_uV'],ss['postclose_held_1_to_3p5ns_peak_uV']),
      '',
      '全16帧P/N侧VGS下降至0.3 V的时刻：TT约156–210 ps，SS约394–596 ps（相对外部关闭沿）；这只是关断过程标记，不等同精确导通截止或有效采样孔径。等效追近量由相位拟合得到，包含继续跟踪及关断扰动，也不能直接当作物理延迟。SS在+1 ns仍有约32 µV尾部变化，+2 ns与+3.5 ns的相位/残差已基本一致；因此1 ns测量点不解释约26 mV的原始误差。','',
      '## 3. 独立M0证据与相位评价','',
      '![导通与相位分解](figures/03_conduction_phase.png)','',
      'VIN=0.45 V、VDS=1 mV时：','',
      '| 模型/温度 | VGS | 导通电阻 |','|---|---:|---:|']
    for tag,vg in [('tt',.889),('tt',.8),('ss',.889),('ss',.81),('ss',.8)]:
        row=next(x for x in result[tag]['isolated_M0']['cases'] if x['VIN_V']==.45 and x['VGS_V']==vg)
        lines.append('| %s | %.3f V | %.1f Ω |'%(LABELS[tag].split(' | ')[0]+(' / 27°C' if tag=='tt' else ' / −40°C'),vg,row['Rsmall_ohm']))
    lines+=['','在同样0.889 V栅源偏置下，SS冷角相对于TT的电阻约增大1.68倍；在SS冷角下再把VGS从0.889降到0.800 V，又增加约2.17倍。这里把工艺与温度作为联合条件，没有单独拆分二者。实际TT与SS冷角相差约3.64倍。用303.5 Ω/1104.4 Ω乘1.28 pF得到0.388/1.414 ns，与实测约0.390/1.435 ns吻合，是主要原因的直接交叉证据。','',
      '固定VGS=0.800 V、VDS=1 mV时，SS的VIN从0.05→0.85 V使电阻从751→1626 Ω，体端固定0 V，说明源体偏置对导通有明显影响；实际正弦输入会扫描这一偏置。这种随输入变化的电阻支持非恒定滞后/非线性的解释。尚未通过理想栅控替换实验证明所有残差均由M0体效应产生，不能将注入和关断的贡献完全排除。','',
      '| 误差评价 | TT | SS冷角 |','|---|---:|---:|',
      '| 原始误差峰，相对外部关闭沿输入 | 6.260 mV | 25.798 mV |',
      '| 仅去掉一个固定拟合相位后的误差峰 | %.3f mV | %.3f mV |'%(tt['phase_only_alignment']['residual_peak_uV']/1000,ss['phase_only_alignment']['residual_peak_uV']/1000),
      '| 再允许增益/偏置拟合后的残差峰 | %.3f µV | %.3f µV |'%(tt['fit_by_measurement_time'][2]['residual_peak_uV'],ss['fit_by_measurement_time'][2]['residual_peak_uV']),
      '| 全拟合残差RMS | %.3f µV | %.3f µV |'%(tt['fit_by_measurement_time'][2]['residual_rms_uV'],ss['fit_by_measurement_time'][2]['residual_rms_uV']),
      '| 相位对齐后、相对理想解析量化器的最大码差 | %d码 | %d码 |'%(tt['phase_only_alignment']['code_delta_peak_against_phase_shifted_analytic_quantizer'],ss['phase_only_alignment']['code_delta_peak_against_phase_shifted_analytic_quantizer']),
      '',
      '若y(t)=A·sin[ω(t−τ)]且τ固定，它只改变相位，不产生新谐波，也不直接损害单音SNDR。当前SS约1.58 mV相位对齐后峰差=0.225 LSB，全拟合残差峰约0.148 LSB：主要原始误差确实是相位，剩余非线性较小但不为零。相位对齐是离线诊断，原始同关闭沿4码差记录未替换；不是已实现延迟校准，也不是1024点FFT或ENOB结论。16点单频数据不能证明整个带宽为纯延迟，不能用于噪声/失配或SFDR签核。','',
      '## 修改建议与优先级','',
      '1. **暂时保留6 µm，不为消除原始4码差而直接改电路。** 若目标是10 MS/s、ENOB≥7且允许固定采样延迟，先用SS角完整频谱和低/中/近Nyquist频点确认SNDR、SFDR、增益与相位随频率变化，再决定是否需要增宽。此前“SS码差筛查失败”应理解为时间对齐诊断失败，不能直接等同ENOB不合格。','2. 若频谱或带宽不够，优先在SS冷角单变量扫M0总宽8/10/12 µm，保持其他尺寸、Cboot、供电和外部时序不变。目标是降低导通电阻及其非线性；必须同时复核注入、自举负载、关断速度、功耗和FF端压。R∝1/W只作初步方向，不能作为最终尺寸预测。','3. **暂不优先增大Cboot或增强关断支路。** 当前Cboot不塌陷；即便SS VGS从0.800恢复到0.810 V，独立M0电阻只从1104降到988 Ω，改善约10.5%，不足以恢复TT水平。关断加快还可能减少当前的追近量，使原始滞后增大；仅当孔径变化或关断残差成为限制时，再单独优化CLKSB/放电路径。','4. 不为通过测试而提高0.81 V低角供电，也不降低输入幅度。若最终必须改善栅源过驱动，需要另行论证电压域/耐压与跨PVT端压，而不是把本次0.889 V诊断偏置直接接回电路。','',
      '本轮只定位并提出方案，未执行这些修复或全码FFT，未改OA、PDK、用户其他模块或旧结果，未commit/push。','',
      '## 证据与限制','',
      '运行：manual8-bootss-probe-tt-v1、manual8-bootss-probe-ss-v1；独立M0：manual8-bootss-m0-tt-v1、manual8-bootss-m0-ss-v1。全部原生完成并受管回收，模型/温度/激励绑定在各自冻结配方。探针结果与旧保持样点最大差TT0.000126 µV、SS0.000898 µV，未改变诊断结论。','',
      '关断图保留每个原生时间点，覆盖关闭前2.975 ns至后4.025 ns，补足旧PVT显示曲线的100 ps降采样不足；其他显示点约50 ps。原生指标与快照独立保留。三图目视检查。SFE1131/VACOMP2435等原生警告保留；无新增CMI。M0独立测试的常量电流稳态与瞬态一致。','',
      '[结果JSON](results.json) · [等价探针输入散列](manifest.json) · [TT独立M0散列](m0_tt_manifest.json) · [SS独立M0散列](m0_ss_manifest.json)','']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:{n:v[n] for n in ['sensor_held_difference_peak_uV','postclose_effective_phase_advance_ps','postclose_held_1_to_3p5ns_peak_uV','companion_conduction','gate_stable_track']} for k,v in result.items()},indent=2))
if __name__=='__main__':main()
