"""Compare isolated CDAC edge/reset experiments using collected native metrics."""
import csv, gzip, json, shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'verification/manual_adc/cdac_edge_v1'
KEYS=['b10','s50','s100','r500']
LABELS={'b10':'10 ps baseline','s50':'50 ps sample','s100':'100 ps sample','r500':'Reset 500 ps earlier'}
COLORS={'b10':'#4a5568','s50':'#287cad','s100':'#d68b20','r500':'#208269'}


def read_case(key):
    run='manual8-cdac-edge-'+key+'-tt-v1'
    col=ROOT/'output/managed_execution/runs'/run/'collected'
    r=json.loads((col/'derived/result.json').read_text())
    shutil.copyfile(col/'derived/result.json',BASE/key/'results.json')
    with gzip.open(col/'derived/reset_native.csv.gz','rt') as f:
        rows=list(csv.DictReader(f))
    z={k:np.array([float(row[k]) for row in rows]) for k in rows[0]}
    return run,r,z


def baseline_check(r):
    old=json.loads((ROOT/'verification/manual_adc/cdac_isolation_v1/results.json').read_text())
    e={'same_codes':[x['actual'] for x in old['captures']]==[x['actual'] for x in r['captures']],
       'dm_error_change_V':max(abs(x['dm_error_V']-y['dm_error_V']) for x,y in zip(old['comparisons'],r['comparisons'])),
       'terminal_peak_change_V':abs(old['summary']['max_terminal_V']-r['summary']['max_terminal_V']),
       'compare_timing_change_s':max(abs(x['time_s']-y['time_s']) for x,y in zip(old['comparisons'],r['comparisons'])),
       'sampling_midpoint_error_s':max(r['sample_timing_validation'].values())}
    e['pass']=e['same_codes'] and e['dm_error_change_V']<1e-6 and e['terminal_peak_change_V']<1e-3 and e['compare_timing_change_s']<1e-12 and e['sampling_midpoint_error_s']<1e-12
    return e


def main():
    data={k:read_case(k) for k in KEYS}
    equivalence=baseline_check(data['b10'][1])
    if not equivalence['pass']:raise ValueError('Baseline equivalence failed: '+str(equivalence))
    summary={}
    clock_baseline=data['b10'][1]['timing_events']['clks']
    for k,(run,r,z) in data.items():
        worst=max(r['terminal_pairs'],key=lambda x:x['peak_V'])
        bottoms={n:e for n,e in r['node_extrema'].items() if '.xd.net' in n}
        lowest=min(bottoms,key=lambda n:bottoms[n]['min_V'])
        durations=[q['duration_over_s'] for q in r['terminal_pairs']]
        # Check the exported native window independently against full-run extrema.
        b=z['xadc.xn.xd.net1'];native_window_peak=float(np.max(np.abs(z['refp']-b)))
        same_pair=next(q for q in r['terminal_pairs'] if q['device']=='XADC.XN.XD.M12' and q['pair']=='DS')
        assert native_window_peak<=same_pair['peak_V']+1e-12
        clock_error=max(abs(a-b) for direction in ['rising','falling'] for a,b in zip(clock_baseline[direction],r['timing_events']['clks'][direction]))
        assert clock_error<1e-12
        reset_advance=[]
        if k=='r500':
            resets=r['timing_events']['ref_rst']['rising']
            assert len(resets)==len(clock_baseline['rising'])
            reset_advance=[a-b for a,b in zip(clock_baseline['rising'],resets)]
            assert max(abs(x-500e-12) for x in reset_advance)<1e-12
        summary[k]={'run_id':run,'checks':r['checks'],'summary':r['summary'],
            'bottom_min_V':bottoms[lowest]['min_V'],'bottom_node':lowest,'bottom_min_s':bottoms[lowest]['min_s'],
            'worst_terminal':worst,'maximum_pair_duration_over_s':max(durations),
            'settling_pass_count':sum(q['settled_by_2ns'] for q in r['segments']),
            'max_settling_s':max(q['settling_time_upper_s'] or 0 for q in r['segments']),
            'codes':[q['actual'] for q in r['captures']],
            'sample_timing_validation':r['sample_timing_validation'],
            'external_clock_change_s':clock_error,'measured_reset_advance_s':reset_advance,
            'CMI_codes':r['CMI_codes'],'zoom_M12_peak_V':native_window_peak}
    (BASE/'comparison.json').write_text(json.dumps({'baseline_equivalence':equivalence,'cases':summary},indent=2)+'\n')
    figdir=BASE/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    env='TT / 0.9 V / 27 C / 10 MS/s | Same 28 native ref MOS and ideal 1.28 pF/side\nIdeal supplies, inputs, comparator and SAR; sampler Ron=1 ohm; closing edge unchanged'
    fig,axes=plt.subplots(4,2,figsize=(13,10),layout='constrained')
    for col,keys in enumerate([KEYS[:3],['b10','r500']]):
        for k in keys:
            _,r,z=data[k];tx=(z['time']-110e-9)*1e12;color=COLORS[k]
            axes[0,col].plot(tx,z['xadc.xn.sample_frac'],color=color,label=LABELS[k])
            axes[1,col].plot(tx,z['xadc.topn'],color=color)
            bottom_names=[n for n in z if '.xd.net' in n]
            axes[2,col].plot(tx,np.min(np.array([z[n] for n in bottom_names]),axis=0),color=color)
            z['0']=np.zeros_like(tx)
            stress=np.max(np.array([np.abs(z[q['nodes'][0]]-z[q['nodes'][1]]) for q in r['terminal_pairs']]),axis=0)
            axes[3,col].plot(tx,stress,color=color)
            if col==1:
                axes[0,col].plot(tx,z['xadc.dn_1']/.9,color=color,ls='--',lw=1,label=LABELS[k]+' ref gate')
        if col==0:
            z=data['b10'][2]
            axes[0,col].plot((z['time']-110e-9)*1e12,z['xadc.dn_1']/.9,'k--',lw=1,label='Ref gate (same in all 3)')
        axes[0,col].legend(fontsize=7,ncol=2,loc='upper left')
        axes[0,col].set_title('Sampling rise only; midpoint fixed' if col==0 else 'Reference reset only; sampling unchanged')
        for row,label in enumerate(['On fraction / gate norm.','N top plate (V)','Lowest bottom, P+N (V)','Max terminal, 28 MOS (V)']):
            axes[row,col].set_ylabel(label)
            axes[row,col].set_xlim((-60,160) if col==0 else (-560,160))
            axes[row,col].grid(alpha=.2)
        axes[2,col].axhline(-.09,color='#bd3030',ls=':',label='-90 mV boundary')
        axes[3,col].axhline(.99,color='#bd3030',ls=':',label='0.99 V limit')
        axes[3,col].legend(fontsize=8)
        axes[3,col].set_xlabel('Time relative to 110 ns (ps)')
    fig.suptitle('CDAC reset / sampling interaction — full native time points\n'+env,fontsize=11)
    fig.savefig(figdir/'waveforms.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(2,1,figsize=(10,7),layout='constrained')
    for i,k in enumerate(KEYS):
        r=data[k][1]
        errors=[max(abs(q['dm_error_V']) for q in r['comparisons'] if q['frame']==f)*1e6 for f in range(8)]
        ax[0].plot(range(8),errors,'o-',color=COLORS[k],label=LABELS[k],ms=4)
    ax[0].set_xticks(range(8),[str(x) for x in summary['b10']['codes']]);ax[0].set_xlabel('Input code center')
    ax[0].set_ylabel('Max compare error (uV)');ax[0].legend(ncol=2,fontsize=8)
    ax[0].text(.03,.08,'Error allocation: 703.125 uV (outside zoom)',transform=ax[0].transAxes,fontsize=9)
    vals=[summary[k]['summary']['max_terminal_V'] for k in KEYS]
    ax[1].bar(range(4),vals,color=[COLORS[k] for k in KEYS]);ax[1].axhline(.99,color='#bd3030',ls='--',label='0.99 V limit')
    ax[1].set_ylim(min(.9,min(vals)-.02),max(vals)+.02)
    for i,v in enumerate(vals):ax[1].text(i,v+.0015,'%.6f V'%v,ha='center',fontsize=9)
    ax[1].set_xticks(range(4),[LABELS[k] for k in KEYS]);ax[1].set_ylabel('Full-run worst terminal (V)');ax[1].legend(fontsize=8)
    for a in ax:a.grid(axis='y',alpha=.2)
    fig.suptitle('Full 820 ns checks — includes moved reset events\n'+env,fontsize=11)
    fig.savefig(figdir/'metrics.png',dpi=160);plt.close(fig)
    lines=['# CDAC接通边沿与提前复位：单变量短测','',
        '**结论：放缓采样接通到50/100 ps消除了本轮TT端压超限；仅提前参考复位500 ps反而加重64C支路下冲。四组功能与精度均通过，电气结论不同。**','',
        '条件：TT、0.9 V、27°C、10 MS/s，820 ns、8帧；原参考MOS尺寸、电容和外部时钟不变。电容理想，采样/比较器/SAR均为行为模型，无噪声、失配或PEX。',
        '', '采样接通电导50%保持10.030 ns + n×100 ns，关闭电导50%保持49.980 ns + n×100 ns；外部采样关闭沿50%为49.975 ns + n×100 ns。10/50/100 ps为0–100%接通过渡长度，关闭过渡始终10 ps。展宽接通沿必然改变开始/结束时刻，本实验保持中点定义的采样窗口。提前复位组仅在9.525 ns + n×100 ns清除参考控制位，比原复位早500 ps，上一帧raw码及输出捕获保留。',
        '', '| 对照 | 全时域底板最低(mV) | 最大端压(V) | 最长单对端压超限(ps) | 比较差模误差(µV) | 建立段通过 | 码字 |',
        '|---|---:|---:|---:|---:|---|---|']
    for k in KEYS:
        q=summary[k];lines.append('| %s | %.3f | %.6f | %.3f | %.3f | %d/56 | %s |'%(LABELS[k],q['bottom_min_V']*1e3,q['summary']['max_terminal_V'],q['maximum_pair_duration_over_s']*1e12,q['summary']['max_compare_dm_error_V']*1e6,q['settling_pass_count'],'8/8正确' if q['checks']['codes'] else '未通过'))
    lines+=['','建立要求：控制50%后2 ns内进入并保持±0.1 LSB（703.125 µV），直到下一更新命令或采样/参考复位开始。峰值及超限时间取全部原生点；波形图保留窗口内全部原生点。最长单对端压超限为该端对全程累计超限时间，不是所有器件时长相加。',
        '', '四组最大比较差模误差均约4.979 µV、共模误差约1.253 µV；转换21.235 ns，56次切换建立上界约27.962 ps（本轮强理想驱动/理想电容条件）。外部CLKS、采样电导接通50%和关闭50%均由原生波形核对一致；提前复位量实测500 ps。',
        '', '![单变量波形](figures/waveforms.png)','', '![误差与全时域端压](figures/metrics.png)', '', '## 最坏点与原生告警','']
    for k in KEYS:
        q=summary[k];w=q['worst_terminal'];lines.append('- **%s**：最坏%s %s，%.6f V @ %.6f ns；最低底板%s @ %.6f ns；原生%s。'%(LABELS[k],w['device'],w['pair'],w['peak_V'],w['time_s']*1e9,q['bottom_node'],q['bottom_min_s']*1e9,','.join(q['CMI_codes']) or '无CMI告警'))
    lines+=['','## 为什么提前复位反而更差','',
        '基线在重新采样前，N顶板约0.4553 V；提前复位先把低位底板恢复到高参考，采样器仍关闭，电荷守恒将N顶板恢复到上一帧采样值约0.89824 V。当前新输入却是0.001758 V。随后相同10 ps/1 Ω采样器接通，顶板需要下降约0.8965 V，约为基线0.4535 V的两倍。',
        '', '已经恢复到0.9 V的低位底板获得了负向摆动余量，因此原M12峰值在该窗口降到0.91114 V；但64C底板仍接低参考，其低参考NMOS导通也不能提供零阻抗。更大的顶板快速下降将net7拉到−180.15 mV，使M0端压达到1.08015 V。最坏点仍在110.029 ns重新采样时，而不是109.525 ns提前复位沿。这组结果否定了“仅提前复位即可解决本例”的建议，不能采用它作为修复。',
        '', '50/100 ps组保持接通中点，降低充放电速度；在本组有限阻抗参考开关下，下冲分别缩小到−46.65/−34.34 mV。100 ps全程最坏端压已转移到转换时M12栅漏，0.93980 V。它们支持优先研究受控采样接通速度；不等于已证明任意输入跃变、PVT或真实Bootstrap都安全。下一步应以真实采样开关的导通变化验证，暂不改参考开关尺寸或推广提前复位。',
        '', '## 证据与边界','',
        '新增10 ps组用于验证拆分接通/关闭沿后的测试台等价性，原基线和结果保持。等价检查：'+json.dumps(equivalence,ensure_ascii=False)+'。',
        '', '运行与输入见[manifest.json](manifest.json)，逐项结果见[comparison.json](comparison.json)。四组共用完全相同的MOS/电容、比较器、SAR和采样模型代码，仅测试参数/参考复位激励不同。实际Spectre设置及所有CMI保留在各managed运行日志；没有修改OA、尺寸、供电或采用新基线。',
        '', '四例实际Spectre X CX、单线程、tran reltol=1e-7、errpreset=conservative_sigglobal、gear2only、maxstep20 ps；原生零错误完成。SFE-1131（PDK重复scalefactor声明）与VACOMP-2435（旧环境变量）告警仍保留，50/100 ps仅表示无CMI端压告警，不是零告警。',
        '', '供能是理想源负载，不代表真实时钟/参考缓冲器功耗；通过本轮端压筛查也不代表PVT、真实驱动或整机已合格。']
    (BASE/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'equivalence':equivalence,'cases':summary},indent=2))


if __name__=='__main__':main()
