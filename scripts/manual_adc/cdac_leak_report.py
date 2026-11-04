"""Curated leakage attribution from saved native terminal currents and charge balance."""
import csv
import gzip
import json
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_leak_ffhot_v1'
RUN='manual8-cdac-leak-ffhot-v1'

def main():
    col=R/'output/managed_execution/runs'/RUN/'collected'
    r=json.loads((col/'derived/result.json').read_text())
    old=json.loads((R/'verification/manual_adc/cdac_100ps_corners_v1/ffhot/results.json').read_text())
    leak=r['leakage'];branches=leak['branches'];means=leak['steady'];m=means[0]['mean']
    shutil.copyfile(col/'derived/result.json',B/'results.json')
    eq={'codes_equal':[q['actual'] for q in r['captures']]==[q['actual'] for q in old['captures']],
        'max_compare_error_delta_V':max(abs(x['dm_error_V']-y['dm_error_V']) for x,y in zip(r['comparisons'],old['comparisons'])),
        'max_compare_time_delta_s':max(abs(x['time_s']-y['time_s']) for x,y in zip(r['comparisons'],old['comparisons'])),
        'max_terminal_delta_V':abs(r['summary']['max_terminal_V']-old['summary']['max_terminal_V'])}
    eq['pass']=eq['codes_equal'] and eq['max_compare_error_delta_V']<1e-6 and eq['max_compare_time_delta_s']<1e-12 and eq['max_terminal_delta_V']<1e-3
    assert eq['pass'],eq
    rows=[]
    for window in means:
        q=window['mean']
        for b in branches:
            key=b['side']+str(b['weight']);p=b['pmos'].lower();n=b['nmos'].lower()
            high=q[key+'.high_state']>.5;off=n if high else p;on=p if high else n
            onI=q[on+'.ID'];drop=abs(q[key+'.rail_error_V'])
            rows.append({'frame':window['frame'],'code':window['code'],'branch':key,'weight':b['weight'],
                         'high_state':high,'pmos':b['pmos'],'nmos':b['nmos'],
                         'off_device':off,'off_ID_A':q[off+'.ID'],'off_IS_A':q[off+'.IS'],
                         'off_IG_A':q[off+'.IG'],'off_IB_A':q[off+'.IB'],'off_VGS_V':q[off+'.VGS'],
                         'off_VDS_V':q[off+'.VDS'],'gate_V':q[key+'.gate_V'],
                         'bottom_V':q[key+'.bottom_V'],'rail_error_V':q[key+'.rail_error_V'],
                         'initial_rail_error_V':q[key+'.initial_rail_error_V'],
                         'dm_contribution_V':q[key+'.dm_contribution_V'],
                         'refp_draw_A':q[key+'.refp_draw_A'],'refn_receive_A':q[key+'.refn_receive_A'],
                         'off_ID_per_C_A':q[off+'.ID']/b['weight'],
                         'effective_on_ohm':drop/abs(onI) if abs(onI)>1e-15 else None})
    f0=[q for q in rows if q['frame']==0]
    largest=dict(max(f0,key=lambda q:abs(q['off_ID_A'])))
    largest['fraction_of_refp_draw']=largest['refp_draw_A']/m['refp_draw_A']
    maxclosure=max(abs(q['mean']['dm_reconstruction_residual_V']) for q in means)
    assert leak['kcl_screen_pass'],leak['largest_kcl_residual_A']
    validation={'source_equivalence':eq,'max_kcl_residual_A':leak['largest_kcl_residual_A'],
                'kcl_screen_pass':leak['kcl_screen_pass'],'max_charge_reconstruction_residual_V':maxclosure,
                'charge_reconstruction_pass':maxclosure<1e-6,'all_8_windows':len(means)==8,
                'branch_rows':len(rows),'largest_frame0_leak':largest}
    assert validation['charge_reconstruction_pass'],validation
    (B/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    (B/'branch_table.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (B/'branch_table.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

    # Bounded native window: only frame0/1 final updates and frame0 held state.
    with gzip.open(col/'derived/branch_wave.csv.gz','rt') as f:
        wave=[row for row in csv.DictReader(f) if 50e-9<=float(row['time'])<=100e-9]
    z={k:np.array([float(row[k]) for row in wave]) for k in wave[0]}
    cfg=json.loads((B/'measure.json').read_text());held=r['frames'][0]['held_input_V']
    ideal=[np.full_like(z['time'],held[0]),np.full_like(z['time'],held[1])]
    for b in branches:
        side=0 if b['side']=='P' else 1
        rail=np.where(z[b['gate'].lower()]<.45,.9,0.)
        initial=.9 if b['bit']!=7 else 0.
        ideal[side]+=(rail-initial)*b['weight']/128.
    dm=(z['xadc.topp']-z['xadc.topn']-ideal[0]+ideal[1])*1e6
    figs=B/'figures';figs.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    env='FF / 0.9 V / 125 C / 10 MS/s | 100 ps sampler rise | unchanged reference MOS sizes\nNative CDAC ref MOS; ideal caps, sampler, comparator, SAR, supplies and inputs'
    fig,axs=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    labels=[q['branch'] for q in f0];colors=['#246ac4' if q['branch'].startswith('P') else '#d25328' for q in f0]
    fields=[('off_ID_A',1e6,'OFF-device drain current (uA)'),('rail_error_V',1e6,'Bottom error from selected rail (uV)'),('dm_contribution_V',1e6,'Contribution to differential residual (uV)')]
    for ax,(field,scale,label) in zip(axs,fields):
        vals=[q[field]*scale for q in f0]
        bars=ax.bar(range(14),vals,color=colors)
        ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=7)
        ax.set_xticks(range(14),labels);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
        ax.margins(y=.22)
    axs[-1].set_xlabel('Side + capacitance weight (1C ... 64C); frame0, code0, time-weighted75–95ns')
    fig.suptitle('Leakage load, DC rail error and charge-weighted residual are different quantities\n'+env,fontsize=11)
    fig.savefig(figs/'branch_attribution.png',dpi=160);plt.close(fig)

    fig,axs=plt.subplots(4,1,figsize=(12,10),sharex=True,layout='constrained')
    t=z['time']*1e9;p=largest['pmos'].lower();n=largest['nmos'].lower()
    branch=next(b for b in branches if b['side']+str(b['weight'])==largest['branch'])
    axs[0].plot(t,z['xadc.cmpck'],color='#657180',label='CMPCK')
    axs[0].plot(t,z[branch['gate'].lower()]+1.2,color='#246ac4',label=largest['branch']+' gate (+1.2 V offset)')
    axs[0].plot(t,z['xadc.dn_1']+2.4,color='#d25328',label='N1C gate (+2.4 V offset)')
    axs[0].set_ylabel('Control traces (V)');axs[0].legend(ncol=3,fontsize=8,loc='upper right')
    high=z[branch['gate'].lower()]<.45
    axs[1].plot(t,np.where(high,z[n+':1']*1e6,np.nan),label='OFF NMOS drain',color='#d25328')
    axs[1].plot(t,np.where(high,-z[n+':3']*1e6,np.nan),'--',label='OFF NMOS source (sign reversed)',color='#18866b')
    axs[1].plot(t,np.where(high,z[p+':3']*1e6,np.nan),':',label='ON PMOS source',color='#246ac4')
    axs[1].set_ylabel(largest['branch']+' current (uA)');axs[1].legend(fontsize=8,ncol=3)
    axs[1].set_ylim(-20,abs(largest['off_ID_A'])*1e6*1.45)
    axs[1].text(.02,.04,'Switching peaks outside the DC-current zoom; full peaks retained in results.json',transform=axs[1].transAxes,fontsize=8)
    axs[2].plot(t,np.where(high,(z['refp']-z[branch['bottom'].lower()])*1e6,np.nan),color='#246ac4',label='REFP - '+largest['branch']+' bottom (high-reference state)')
    axs[2].set_ylabel('DC drop zoom (uV)');axs[2].set_ylim(-30,abs(largest['rail_error_V'])*1e6*1.5);axs[2].legend(fontsize=8)
    comparisons=[q for q in r['comparisons'] if q['frame']==0]
    axs[3].plot([q['time_s']*1e9 for q in comparisons],[q['dm_error_V']*1e6 for q in comparisons], 'o--',color='#d25328',label='At each comparison aperture (8 measured points)')
    axs[3].plot(t,np.where(t>72,dm,np.nan),color='#d25328',label='After conversion: persistent residual')
    axs[3].axhline(-703.125,color='black',ls='--',label='-0.1 LSB')
    axs[3].set_ylabel('DM residual (uV)');axs[3].set_ylim(-800,50);axs[3].legend(fontsize=8)
    axs[-1].set_xlabel('Time (ns); frame0, input code0; SAR completes at about71.21ns')
    for ax in axs:ax.grid(alpha=.2);ax.set_xlim(50,100)
    fig.suptitle('Persistent OFF-NMOS current produces an ON-PMOS voltage drop\n'+env,fontsize=11)
    fig.savefig(figs/'waveforms.png',dpi=160);plt.close(fig)

    report=['# FF热角：参考支路漏电与静态残差', '',
            '本轮只补保存电流，尺寸、拓扑、模型、时序和激励均未改变。FF、0.9 V、125°C，100 ps采样电导接通、10 MS/s、820 ns、8个代表码；参考开关管级，其余模块及电容理想。', '',
            '## 结论与主电流路径', '',
            '码0转换完成后的75–95 ns，最大的关断支路为 **%s（%s）**：漏极电流%.3f µA，占高参考输出约%.2f%%。其VGS=%.3g V，VDS=%.6f V，栅极已经到关断电平。'%(largest['branch'],largest['off_device'],largest['off_ID_A']*1e6,largest['fraction_of_refp_draw']*100,largest['off_VGS_V'],largest['off_VDS_V']), '',
            '路径为 **REFP → 导通PMOS → 底板 → 已关断NMOS → REFN**。同一支路PMOS的有限导通电阻使底板低于理想高参考。关断不等于零电流，测量结果需要结合下面的源/体/栅分量判断。', '',
            '最大支路关断NMOS：ID=%.3f µA、IS=%.3f µA、IG=%.3f nA、IB=%.3f nA；有效导通PMOS压降%.3f µV，对应压降/漏极电流约%.3f Ω。'%(largest['off_ID_A']*1e6,largest['off_IS_A']*1e6,largest['off_IG_A']*1e9,largest['off_IB_A']*1e9,abs(largest['rail_error_V'])*1e6,largest['effective_on_ohm']), '',
            'ID与IS相抵且栅/体电流远小于ID，说明主要电流在漏源之间，不能归因于栅极未到低电平或由体电流主导。FF高温、L=30 nm的关断NMOS漏源泄漏符合这些结果；这里没有分解PDK内部亚阈值/DIBL/GIDL等模型项，不给出未经测量的微观比例。', '',
            '![电流与残差波形](figures/waveforms.png)', '',
            '## 哪些支路贡献最大', '',
            '下表为码0、75–95 ns的时间加权均值。“残差贡献”按相对采样关闭时的底板误差变化计算，不能直接把最终底板偏差当成ADC误差。P/N表示差分两侧。', '',
            '| 支路 | 关断管 | 关断ID(µA) | 每C的ID(µA) | 底板偏离目标(µV) | 差模残差贡献(µV) |',
            '|---|---|---:|---:|---:|---:|']
    for q in f0:
        report.append('| %s | %s | %.3f | %.3f | %.3f | %.3f |'%(q['branch'],q['off_device'].split('.')[-1],q['off_ID_A']*1e6,q['off_ID_per_C_A']*1e6,q['rail_error_V']*1e6,q['dm_contribution_V']*1e6))
    report+=['', '![支路分解](figures/branch_attribution.png)', '',
             '高参考状态的NMOS漏极电流约6.231 µA/C，随并联数成比例增长；低参考状态的关断PMOS约0.04062 µA/C，约小153倍。主要问题是一整类L=30 nm的关断NMOS漏源泄漏，64C支路只是按尺寸放大后的最大负载。码255时P/N角色交换，完整8帧见[branch_table.csv](branch_table.csv)。', '',
             '注意P侧1C–32C虽持续耗流，却几乎不贡献本帧新增残差：它们采样时和转换后都处于高参考状态，压降变化接近零。相反，P64C从低切到高贡献约−358.22 µV；N侧1C–32C从高切到低合计约−352.62 µV，其中N32C约−179.11 µV。必须比较前后状态，而不能仅按最终漏电大小给残差排序。', '',
             '## 电荷守恒如何解释残差', '',
             '`单侧顶板误差 = 采样关闭时顶板误差 + Σ(Ci/Ctotal) × [当前底板偏离理想参考 − 采样关闭时底板偏离理想参考]`', '',
             '用实际支路电压重建，码0测得差模残差%.3f µV，重建%.3f µV；全部8帧最大重建差%.3f nV。这把底板压降与顶板残差定量连起来，而非仅凭电流峰值推测。'%(m['actual_dm_error_V']*1e6,m['predicted_dm_error_V']*1e6,maxclosure*1e9), '',
             '| 输入码 | 参考持续输出(µA) | 实测差模残差(µV) | 电荷重建(µV) |', '|---|---:|---:|---:|']
    for q in means:
        v=q['mean'];report.append('| %d | %.3f | %.3f | %.3f |'%(q['code'],v['refp_draw_A']*1e6,v['actual_dm_error_V']*1e6,v['predicted_dm_error_V']*1e6))
    report+=['', '高参考实际底板约0.899289516 V，低参考实际底板约0.000005959 V，两档间距约0.899283558 V，比理想0.9 V少0.716442 mV（约0.0796%）。本例主要表现为有效DAC参考跨度缩小，不等于已经测得ENOB下降或缺码。误差在比较结束后仍维持，继续等待不会消除这一静态分量。上一轮FF热角0.710855 mV残差略超0.703125 mV预算、8码仍正确的结论保留；本轮不是修复或规格放宽。', '',
             '## 下一步与证据边界', '',
             '优先针对关断NMOS的漏源泄漏评估沟道长度，保持W/并联数/时序不动做单变量比较，同时测Ron、低参考建立速度和端压。扩大PMOS可能降低压降，但不解决参考持续耗流；单纯延后比较也不解决稳态误差。本轮未执行尺寸修改。', '',
             '28个MOS四端、14个底板节点和两条参考轨电流守恒均已核对；最大全时域KCL残差%.3g A。电流正方向定义为流入器件端口，原生端口1/2/3/4对应D/G/S/B，包含瞬态位移电流，稳定保持区间才用于漏电归因。'%leak['largest_kcl_residual_A'], '',
             '保存信号扩展后的[等价与重建核对](validation.json)、[完整测量](results.json)、[输入散列](manifest.json)及[所有支路数据](branch_table.json)可追溯到`'+RUN+'`。原始日志/波形保留在managed运行目录；无OA或PDK修改，无新基线采用。']
    sim=json.loads((col/'simulation.state.json').read_text());ana=json.loads((col/'analysis.state.json').read_text())
    receipt=json.loads((col/'collection_receipt.json').read_text())
    report+=['', '原尺寸保持：参考NMOS W=1 µm、L=30 nm、nf=10；PMOS W=3 µm、L=100 nm、nf=10；multi按1C至64C为2至128。以上为网表参数，未重解释PDK的每指宽度语义。', '',
             '只增加100个保存电流信号；原生零错误，原SFE-1131/VACOMP-2435告警保留，无CMI。实际Spectre21.1 X CX单线程，reltol=1e-7、gear2only、maxstep20 ps，与源运行一致。仿真%.2f s/RSS%.2f MiB，分析%.2f s/RSS%.2f MiB，回收%.2f MiB。'%(sim['elapsed_seconds'],sim['peak_rss_bytes']/1024**2,ana['elapsed_seconds'],ana['peak_rss_bytes']/1024**2,receipt['total_bytes']/1024**2), '',
             '波形图控制信号为便于阅读分别纵向错开，偏移量标在图例；电流/压降展示选高参考后的DC量级，切换尖峰可能超出纵轴，原始峰值完整保留。残差圆点是实际8个比较时刻，虚线仅连接标记；比较完成后用保持波形显示持续残差，避免将切换期间理想目标跳变误认为稳定误差。']
    (B/'README.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps(validation,indent=2))

if __name__=='__main__':main()
