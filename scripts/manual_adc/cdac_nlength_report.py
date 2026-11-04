"""Compare frozen FF-hot length-only candidates with the completed L30 source."""
import csv
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_nlength_v1'
RUNS={30:'manual8-cdac-leak-ffhot-v1',60:'manual8-cdac-nl60-ffhot-v1',90:'manual8-cdac-nl90-ffhot-v1'}
COLORS=['#d25328','#246ac4','#18866b']

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def main():
    data={};summary={};validation={};branchrows=[]
    for length,run in RUNS.items():
        col=R/'output/managed_execution/runs'/run/'collected'
        r=read(col/'derived/result.json');s=read(col/'simulation.state.json');a=read(col/'analysis.state.json');receipt=read(col/'collection_receipt.json')
        if length!=30:shutil.copyfile(col/'derived/result.json',B/('l'+str(length))/'results.json')
        # Only retain a bounded first-frame window; raw PSF stays on server.
        wave=[]
        with gzip.open(col/'derived/branch_wave.csv.gz','rt') as f:
            for q in csv.DictReader(f):
                t=float(q['time'])
                if t>96e-9:break
                if t>=52e-9:wave.append({k:float(v) for k,v in q.items()})
        z={k:np.array([q[k] for q in wave]) for k in wave[0]}
        m=r['leakage']['steady'][0]['mean'];branches=r['leakage']['branches']
        for w in r['leakage']['steady']:
            q=w['mean']
            for b in branches:
                key=b['side']+str(b['weight']);high=q[key+'.high_state']>.5
                off=(b['nmos'] if high else b['pmos']).lower()
                branchrows.append(dict(length_nm=length,frame=w['frame'],code=w['code'],branch=key,high_state=high,
                    off_ID_A=q[off+'.ID'],off_IS_A=q[off+'.IS'],off_IG_A=q[off+'.IG'],off_IB_A=q[off+'.IB'],
                    off_VGS_V=q[off+'.VGS'],rail_error_V=q[key+'.rail_error_V'],dm_contribution_V=q[key+'.dm_contribution_V']))
        worst=max(r['terminal_pairs'],key=lambda q:q['peak_V'])
        bottoms={k:q for k,q in r['node_extrema'].items() if '.xd.net' in k}
        lowname=min(bottoms,key=lambda k:bottoms[k]['min_V'])
        settled=[q['settling_time_upper_s'] for q in r['segments'] if q['settling_time_upper_s'] is not None]
        ref=r['timing_events']['clks']
        clock_delta=0 if length==30 else max(abs(x-y) for d in ['rising','falling'] for x,y in zip(ref[d],data[30][0]['timing_events']['clks'][d]))
        # Independent four-port KCL over the exported bounded native/display window.
        kcl=max(float(np.max(abs(sum(z[dev['path'].lower()+':'+str(i)] for i in [1,2,3,4])))) for dev in r['leakage']['devices'])
        v={'native_success':s['status']=='complete' and s['exit_code']==0 and s['native']['zero_error_footer'],
           'analysis_success':a['status']=='complete' and a['exit_code']==0,
           'measurement_coverage':len(r['captures'])==8 and len(r['comparisons'])==64 and len(r['segments'])==56 and len(r['leakage']['steady'])==8 and len(r['terminal_pairs'])==168,
           'native_kcl':r['leakage']['kcl_screen_pass'],'independent_export_kcl':kcl<1e-9,
           'charge_reconstruction':max(abs(q['mean']['dm_reconstruction_residual_V']) for q in r['leakage']['steady'])<1e-6,
           'clock_fixed':clock_delta<1e-12,'sampling_fixed':max(r['sample_timing_validation'].values())<1e-12,
           'supply_fixed':bool(max(np.max(abs(z['refp']-.9)),np.max(abs(z['vdd']-.9)),np.max(abs(z['refn'])))<1e-10),
           'solver_fixed':length==30 or s['native']['effective_settings']==data[30][3]['native']['effective_settings'],
           'resources':s['peak_rss_bytes']<=1024*1024**2 and a['peak_rss_bytes']<=256*1024**2 and receipt['total_bytes']<=32*1024**2 and not receipt['skipped']}
        assert all(v.values()),(length,v)
        validation[length]={'checks':v,'independent_KCL_A':kcl,'clock_delta_s':clock_delta}
        summary[length]={'length_nm':length,'run_id':run,'short_test_pass':r['short_test_pass'],'checks':r['checks'],
            'off_P64_nmos_A':m['xadc.xp.xd.m1.ID'],'refp_steady_A':m['refp_draw_A'],
            'refp_steady_power_W':.9*m['refp_draw_A'],
            'high_drop_V':-m['P64.rail_error_V'],'low_offset_V':m['N64.rail_error_V'],
            'P64_pmos_effective_on_ohm':abs(m['P64.rail_error_V']/m['xadc.xp.xd.m0.ID']),
            'N64_nmos_effective_on_ohm':abs(m['N64.rail_error_V']/m['xadc.xn.xd.m1.ID']),
            'steady_dm_V':m['actual_dm_error_V'],'max_compare_dm_V':r['summary']['max_compare_dm_error_V'],
            'max_compare_cm_V':r['summary']['max_compare_cm_error_V'],
            'settled_count':sum(q['settled_by_2ns'] for q in r['segments']),
            'unsettled_count':sum(q['settling_time_upper_s'] is None for q in r['segments']),
            'max_settled_upper_s':max(settled),'max_after_2ns_error_V':max(q['max_abs_error_after_budget_V'] for q in r['segments']),
            'codes':[q['actual'] for q in r['captures']],'correct_count':sum(q['actual']==q['expected'] for q in r['captures']),
            'bottom_min_V':bottoms[lowname]['min_V'],'bottom_node':lowname,'worst_terminal':worst,
            'CMI_codes':r['CMI_codes'],'warnings':s['native']['warning_codes'],'native_settings':s['native']['effective_settings'],
            'reference_average_power_W':r['summary']['refp_net_power_W'],
            'gate_positive_power_W':r['summary']['gate_positive_power_W'],
            'max_conversion_s':r['summary']['max_conversion_s'],
            'native_KCL_A':r['leakage']['largest_kcl_residual_A'],
            'max_charge_reconstruction_error_V':max(abs(q['mean']['dm_reconstruction_residual_V']) for q in r['leakage']['steady']),
            'simulation_seconds':s['elapsed_seconds'],'analysis_seconds':a['elapsed_seconds'],
            'simulation_RSS_MiB':s['peak_rss_bytes']/1024**2,'analysis_RSS_MiB':a['peak_rss_bytes']/1024**2,'collected_bytes':receipt['total_bytes']}
        data[length]=(r,z,col,s)
    manifest=read(B/'manifest.json')
    for case in manifest['cases']:
        folder=B/('l'+str(case['length_nm']))
        assert all(hashlib.sha256((folder/k).read_bytes()).hexdigest()==v for k,v in case['files'].items())
    save(B/'comparison.json',summary);save(B/'validation.json',validation);save(B/'branch_table.json',branchrows)
    figdir=B/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    env='FF / 0.9 V / 125 C / 10 MS/s / 100 ps sampler turn-on; fixed W, nf, multiplicity and timing\nNative CDAC reference MOS; ideal capacitors, sampler, comparator, SAR and external sources'
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    fields=[('off_P64_nmos_A',1e6,'P64C OFF NMOS drain current (uA)'),('high_drop_V',1e6,'P64C high-reference DC drop (uV)'),('max_compare_dm_V',1e6,'Worst DM error at comparison (uV)'),('settled_count',1,'Steps within 0.1 LSB at 2 ns (of 56)')]
    for i,(field,scale,title) in enumerate(fields):
        ax=axs.flat[i];vals=[summary[L][field]*scale for L in RUNS]
        bars=ax.bar(range(3),vals,color=COLORS);ax.bar_label(bars,fmt='%.3f' if i<3 else '%.0f',padding=3,fontsize=9)
        ax.set_xticks(range(3),['L = %d nm'%L for L in RUNS]);ax.set_title(title,fontsize=10);ax.grid(axis='y',alpha=.2)
        ax.set_ylim(0,max(max(vals)*1.25,1))
        if i==2:ax.axhline(703.125,color='black',ls='--',lw=1,label='703.125 uV limit');ax.legend(fontsize=8)
    fig.suptitle('Reference NMOS length: leakage, precision and settling\n'+env,fontsize=11)
    fig.savefig(figdir/'metrics.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
    for (L,(r,z,col,s)),color in zip(data.items(),COLORS):
        t=z['time']*1e9;high=z['xadc.dn_7']<.45;label='L = %d nm'%L
        axs[0].plot(t,np.where(high,z['xadc.xp.xd.m1:1']*1e6,np.nan),color=color,label=label)
        axs[1].plot(t,np.where(high,(z['refp']-z['xadc.xp.xd.net7'])*1e6,np.nan),color=color,label=label)
        q=[q for q in r['comparisons'] if q['frame']==0]
        axs[2].plot([q['time_s']*1e9 for q in q],[q['dm_error_V']*1e6 for q in q],'o--',color=color,label=label,ms=4)
    axs[0].set_ylim(-20,520);axs[0].set_ylabel('OFF NMOS current (uA)');axs[0].legend(ncol=3)
    axs[0].text(.02,.60,'DC zoom; transition spikes clipped (full native maxima retained).',transform=axs[0].transAxes,fontsize=8)
    axs[1].set_ylim(-40,900);axs[1].set_ylabel('High-rail DC drop (uV)')
    axs[2].axhline(-703.125,color='black',ls=':',label='-0.1 LSB');axs[2].set_ylabel('DM aperture error (uV)');axs[2].legend(ncol=4,fontsize=8)
    axs[-1].set_xlabel('Time (ns), frame0 / input code0; markers are actual comparator apertures')
    for ax in axs:ax.set_xlim(52,96);ax.grid(alpha=.2)
    fig.suptitle('Leakage reduction and persistent residual — same input / clocks\n'+env,fontsize=11)
    fig.savefig(figdir/'waveforms.png',dpi=160);plt.close(fig)
    # Final N1C transition, native samples in the 64–72ns export window.
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True,layout='constrained')
    for (L,(r,z,col,s)),color in zip(data.items(),COLORS):
        seg=next(q for q in r['segments'] if q['frame']==0 and q['changed_positions']==[7]);start=seg['start_s']
        sel=(z['time']>=start-60e-12)&(z['time']<=start+600e-12);t=(z['time'][sel]-start)*1e12
        axs[0].plot(t,z['xadc.dn_1'][sel],color=color,label='L = %d nm'%L)
        axs[1].plot(t,z['xadc.xn.xd.net1'][sel]*1e3,color=color)
        axs[2].plot(t,z['xadc.xn.xd.net1'][sel]*1e6,color=color)
    axs[0].set_ylabel('N1C gate (V)');axs[0].legend(ncol=3)
    axs[1].set_ylabel('N1C bottom (mV)')
    axs[2].set_ylabel('Low-rail tail (uV)');axs[2].set_ylim(-20,180)
    axs[-1].set_xlabel('Time from each measured gate 50% rising crossing (ps); native points')
    for ax in axs:ax.set_xlim(-60,600);ax.grid(alpha=.2)
    fig.suptitle('Cost of longer NMOS: low-reference switching and residual floor\n'+env,fontsize=11)
    fig.savefig(figdir/'settling.png',dpi=160);plt.close(fig)
    lines=['# FF热角：参考开关 NMOS 长度扫描','',
        '**60nm、90nm均通过本轮8帧短测；30nm仍有静态残差超预算。60nm已把最大比较误差从710.9µV降至66.1µV，90nm进一步降至27.7µV。**','',
        '仅将两侧14个参考NMOS的L从30nm改为60/90nm。W=1µm、nf=10、multi=2/4/8/16/32/64/128固定；PMOS仍为W=3µm、L=100nm、nf=10及原并联数。拓扑、输入、100ps采样接通过渡和全部其他时序不变，OA未改。','',
        '测试为FF、0.9V、125°C、10MS/s，双侧各1.28pF理想电容；参考开关晶体管级，采样器、比较器、SAR及外部电源/输入理想。8帧820ns，输入码中心为0、255、85、170、127、128、1、254。L30复用已完成电流测量，不重复仿真。','',
        '100ps指理想采样器电导接通时间；外部CLKS与参考栅控仍为50ps，采样接通中点10.030ns、关闭中点49.980ns，每100ns重复。采样器Ron=1Ω；未加入真实Bootstrap、栅驱动、噪声、失配或PEX。','',
        '## 结果','',
        '| NMOS L | P64C关断漏电(µA) | 高参考静态压降(µV) | 低参考静态偏移(µV) | 最大比较差模误差(µV) | 建立通过 | 正确码 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for L,q in summary.items():
        lines.append('| %dnm | %.3f | %.3f | %.3f | %.3f | %d/56 | %d/8 |'%(L,q['off_P64_nmos_A']*1e6,q['high_drop_V']*1e6,q['low_offset_V']*1e6,q['max_compare_dm_V']*1e6,q['settled_count'],q['correct_count']))
    lines+=['','静态列取码0转换结束后75–95ns时间加权平均；高参考为P64C，低参考为N64C。比较误差取全部64个实际比较孔径。建立标准保持为2ns内进入并保持在0.1LSB=703.125µV；L30的8段因静态残差未进入预算，不能把其他已通过段的短建立时间当成全部通过。','',
        '![指标比较](figures/metrics.png)','',
        '| NMOS L | 总高参考静态电流(µA) | 高参考保持功率(µW) | N64C有效导通电阻(Ω) | 最大端压(V) | 最低底板(mV) | 最慢已建立段上界(ps) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for L,q in summary.items():
        lines.append('| %dnm | %.3f | %.3f | %.4f | %.6f | %.3f | %.2f |'%(L,q['refp_steady_A']*1e6,q['refp_steady_power_W']*1e6,q['N64_nmos_effective_on_ohm'],q['worst_terminal']['peak_V'],q['bottom_min_V']*1e3,q['max_settled_upper_s']*1e12))
    lines+=['','有效导通电阻以静态压降/该导通支路漏极电流计算，反映当前工作点，不是独立扫VDS提取的通用Ron。参考保持功率只计0.9V参考源；不是整机功耗。端压取28管全部六种端差，共168对，筛查上限0.99V。','',
        '## 原因与取舍','',
        'L30已确认的路径是REFP → 导通PMOS → 底板 → 关断NMOS → REFN。保持W、并联数及PMOS不变，增加NMOS长度后，下面两个效应需要一起看：','',
        '- 高参考状态：关断NMOS漏电减少，流过PMOS的电流及底板压降下降。',
        '- 低参考状态：导通NMOS电阻增大，而关断PMOS漏电仍在，底板正偏移和动态建立代价可能增加。','']
    for L in [60,90]:
        q=summary[L];base=summary[30]
        lines.append('%dnm：P64C关断漏电较30nm降低%.2f倍，高参考静态压降降低%.2f倍；N64C有效导通电阻变为原来的%.3f倍。全部短测项%s。'%(L,base['off_P64_nmos_A']/q['off_P64_nmos_A'],base['high_drop_V']/q['high_drop_V'],q['N64_nmos_effective_on_ohm']/base['N64_nmos_effective_on_ohm'],'通过' if q['short_test_pass'] else '仍有未通过项（见comparison.json）'))
    lines+=['','代价也已出现：最低底板从−32.38mV加深至−42.07/−51.54mV，最大端压从0.93993V升至0.94207/0.95154V；均低于本轮0.99V筛查线且无CMI，但不能忽略趋势。新增两组的最坏端压出现在采样/参考复位阶段，与转换结束后的静态漏电不是同一个指标。','',
        '60nm已足以解决当前热角精度超预算，可作为优先验证候选；90nm保留为更低漏电备选。下一步应在SS冷角检查低参考建立，并在高供电端核对下冲/端压，再定尺寸。本轮不直接采用新基线，也不能据此宣布整机PVT通过。']
    lines+=['','![漏电及比较残差波形](figures/waveforms.png)','',
        '上两行是高参考选通后的电流和压降局部量程，切换尖峰被裁出显示范围；原生峰值保留在results.json。下行是实际比较孔径的误差点，不把切换瞬态目标跳变当作已建立误差。','',
        '![低参考切换与恢复](figures/settling.png)','',
        '该图比较码0最后一次N1C高→低参考切换，使用64–72ns保存的全部原生点。横轴对齐各自实际栅极50%交叉时刻；最后一行放大低参考残差，不能仅凭前一行波形看似重合就认为Ron未变化。','',
        '## 边界与验证','',
        'PDK只读核对：三个L均在模型列举的短沟道长度中。W=1µm由nf=10分为每指100nm，shrink0.9后模型宽90nm；三个长度均有匹配模型范围（90nm位于分段边界，列出两侧匹配，不擅自宣称实际选中哪个bin）。见legality.json。','',
        '这是L单变量电气对照：原导出扩散/LDE参数保持不变，尚未做PCell回调重算、版图DRC或OA同步。不能把模型可计算解释为物理版图已合法。','',
        '输入manifest逐文件散列及L-only反向替换核对通过；模型/激励/PMOS/采样/码序列/测量阈值一致。原生28管端口、14底板及参考源KCL由既有流式分析计算，本轮另对导出局部窗口核对四端电流和。静态电荷重建与实测差模残差的差异保留于comparison.json。','',
        'Spectre21.1 X CX，1线程，实际tran reltol=1e-7、vabstol10nV、iabstol10fA、gear2only、maxstep20ps。不同L使用同一求解设置与分析器，没有降低精度。原生日志、资源和精确运行身份：','']
    for L,q in summary.items():
        lines.append('- L%d：`%s`；CMI：%s；告警：%s；仿真%.2fs/%.2fMiB，分析%.2fs/%.2fMiB，回收%.2fMiB。'%(L,q['run_id'],','.join(q['CMI_codes']) or '无',','.join(q['warnings']) or '无',q['simulation_seconds'],q['simulation_RSS_MiB'],q['analysis_seconds'],q['analysis_RSS_MiB'],q['collected_bytes']/1024**2))
    lines+=['','[比较数值](comparison.json) · [验证](validation.json) · [全部支路及8帧静态结果](branch_table.json) · [输入身份](manifest.json)','',
        '本轮仅FF/0.9V/125°C、8个代表输入；未测新的全码/FFT或全电压PVT。未采用新基线、未改OA，旧结果及原始波形保留。']
    (B/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
