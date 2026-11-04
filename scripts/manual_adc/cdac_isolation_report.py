"""Create bounded local plots and a concise report from collected native metrics."""
import csv, gzip, hashlib, json, shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cdac_isolation_plot_reset import plot_reset

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'verification/manual_adc/cdac_isolation_v1'
RUN='manual8-cdac-isolation-tt-review-v3'
COL=ROOT/'output/managed_execution/runs'/RUN/'collected'


def main():
    r=json.loads((COL/'derived/result.json').read_text())
    shutil.copyfile(ROOT/'output/managed_execution/runs/manual8-cdac-isolation-tt-v1/collected/derived/result.json',BASE/'results_original_window.json')
    shutil.copyfile(ROOT/'output/managed_execution/runs/manual8-cdac-isolation-tt-review-v2/collected/derived/result.json',BASE/'results_1percent_window.json')
    shutil.copyfile(COL/'derived/result.json',BASE/'results.json')
    wanted=['clks','xadc.cmpck','xadc.topp','xadc.topn','ideal_topp','ideal_topn','dm_error','cm_error','vrefp:1','vrefn:1']
    with gzip.open(COL/'derived/wave.csv.gz','rt') as f:
        header=f.readline().strip().split(',');indices=[header.index(k) for k in ['time']+wanted]
        a=np.loadtxt(f,delimiter=',',usecols=indices)
    d={k:a[:,i] for i,k in enumerate(['time']+wanted)};t=d['time']*1e9
    figdir=BASE/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    environment='TT / 0.9 V / 27 C | 28 native reference MOS; ideal capacitors 1.28 pF/side\nIdeal supplies/input; behavioral sampler, comparator and SAR; 50 ps control edges'
    j=3;lo=100*j+49;hi=100*j+74
    fig,ax=plt.subplots(4,1,figsize=(10,9),sharex=True,layout='constrained')
    ax[0].plot(t,d['clks']+1.2,label='Sample (+1.2 V)');ax[0].plot(t,d['xadc.cmpck'],label='Compare')
    ax[0].set_ylabel('Clock (V)');ax[0].legend(ncol=2,loc='upper right',fontsize=8)
    dm=d['xadc.topp']-d['xadc.topn'];cm=.5*(d['xadc.topp']+d['xadc.topn'])
    target_dm=d['ideal_topp']-d['ideal_topn'];target_cm=.5*(d['ideal_topp']+d['ideal_topn'])
    ax[1].plot(t,dm,label='Native CDAC',lw=1.5);ax[1].plot(t,target_dm,'--',label='Charge oracle',lw=1)
    ax[1].set_ylabel('Top differential (V)');ax[1].legend(fontsize=8,ncol=2)
    ax[2].plot(t,cm,label='Native CDAC');ax[2].plot(t,target_cm,'--',label='Charge oracle')
    ax[2].set_ylabel('Top common mode (V)');ax[2].legend(fontsize=8,ncol=2)
    # Show measured errors at actual compare instants, avoiding switching spikes
    # obscuring the settled accuracy. No offset/gain fitting.
    rows=[x for x in r['comparisons'] if x['frame']==j]
    ax[3].plot([q['time_s']*1e9 for q in rows],[q['dm_error_V']*1e6 for q in rows],'o-',label='Differential error at compare')
    lim=r['criteria']['step_dm_limit_V']*1e3
    ax[3].text(.02,.9,'Allocation: +/-703.125 uV (outside zoom)',transform=ax[3].transAxes,fontsize=8)
    ax[3].set_ylabel('Settled error (uV)');ax[3].set_xlabel('Time (ns)');ax[3].legend(fontsize=8)
    for x in ax:x.set_xlim(lo,hi);x.grid(alpha=.2)
    fig.suptitle('CDAC isolated conversion — code center 170\n'+environment,fontsize=11)
    fig.savefig(figdir/'conversion.png',dpi=165);plt.close(fig)
    fig,ax=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    for idx,expected in enumerate([c['expected'] for c in r['captures']]):
        rows=[q for q in r['comparisons'] if q['frame']==idx]
        ax[0].plot(range(8),[q['dm_error_V']*1e6 for q in rows],'o-',ms=3,label=str(expected))
    ax[0].text(.02,.05,'Allocation: +/-703.125 uV (outside zoom)',transform=ax[0].transAxes,fontsize=8)
    ax[0].set_xlabel('Decision index (0 = sign / MSB)');ax[0].set_ylabel('DM error (uV)');ax[0].legend(title='Input code center',ncol=8,fontsize=8)
    worst={}
    for q in r['terminal_pairs']:
        if q['device'] not in worst or q['peak_V']>worst[q['device']]['peak_V']:worst[q['device']]=q
    values=list(worst.values());ax[1].bar(range(len(values)),[q['peak_V'] for q in values],color=['#cf4a3c' if q['peak_V']>.99 else '#4285a5' for q in values])
    ax[1].set_ylim(.88,1.005)
    ax[1].axhline(.99,color='r',ls='--',label='0.99 V terminal screen')
    ax[1].set_xticks(range(len(values)),[q['device'].replace('XADC.X','').replace('.XD.','/') for q in values],rotation=65,fontsize=7)
    ax[1].set_ylabel('Worst terminal pair (V)');ax[1].legend(fontsize=8)
    mask=(t>=lo)&(t<=hi)
    ax[2].plot(t[mask],-d['vrefp:1'][mask]*1e3,label='High reference delivered current')
    ax[2].plot(t[mask],-d['vrefn:1'][mask]*1e3,label='Low reference delivered current')
    ax[2].set_xlabel('Time (ns)');ax[2].set_ylabel('Reference current (mA)');ax[2].legend(fontsize=8)
    for x in ax:x.grid(alpha=.2)
    fig.suptitle('CDAC accuracy, terminal stress and reference load\n'+environment,fontsize=11)
    fig.savefig(figdir/'metrics.png',dpi=165);plt.close(fig)
    plot_reset(COL,figdir,environment)
    checks=r['checks'];s=r['summary'];cr=r['criteria']
    settle=[q['settling_time_upper_s'] for q in r['segments'] if q['settling_time_upper_s'] is not None]
    maxsettle=max(settle)*1e9 if settle else float('nan')
    init=[next(c for c in r['comparisons'] if c['frame']==j) for j in range(8)]
    incremental=max(abs(c['dm_error_V']-init[c['frame']]['dm_error_V']) for c in r['comparisons'])
    def yn(k):return '通过' if checks[k] else '**未通过**'
    text='''# CDAC晶体管参考开关隔离短测

结论：**%s**。这是TT短测，不是PVT、全码或实际电容阵列资格验证。

## 测试边界

- 真实部分：原手搭CDAC两侧共28只参考MOS，W/L/nf/multi保持不变。
- 电容：原网表理想10 fF单位电容，每侧128 C=1.28 pF；未替换成PDK MOM，未含失配/PEX。
- 理想部分：电源、参考、输入源；采样开关使用Ron=1 Ω、无注入行为模型；比较器无失调/噪声/反冲；SAR用行为模型，控制输出50 ps/1 Ω。这里的“理想”不等于零边沿/零导通电阻。
- TT、0.9 V、27°C；100 ns周期，原外部采样窗口及关闭沿保留；参考控制更新后等待2 ns。
- 820 ns、8帧码中心0/255/85/170/127/128/1/254，首位跨接向上、其余同侧向下。

## 指标与结果

0.1 LSB及0.05 LSB是本轮预先规定的模块诊断分配，不是宣称已完成整机误差预算。LSB=7.03125 mV。

| 项目 | 本轮目标 | 实测 | 结果 |
|---|---|---|---|
| 输出码 | 8个码中心均正确 | %s | %s |
| 比较/更新次数 | 每帧8次比较、7次参考更新 | %s / %s | %s |
| 比较时差模误差 | ≤0.703125 mV | 最大%.6f mV | %s |
| 比较时共模误差 | ≤0.703125 mV | 最大%.6f mV | %s |
| 每步建立 | 2 ns后误差≤0.1 LSB并保持到下一切换 | %d/56段通过；已建立段最慢上界%.4f ns | %s |
| 首次比较前保持漂移 | ≤0.351563 mV | 最大%.6f mV | %s |
| 转换完成 | 采样关闭后≤50 ns | 最长%.4f ns | %s |
| MOS端压 | 六组端压均≤0.99 V | 最大%.6f V；28管×6组全时域 | %s |
| 原生CMI | 不出现 | %s | %s |

误差基准来自采样关闭时输入电压与电容电荷守恒，逐次使用实际参考控制状态；没有去除失调、增益或做拟合。初次比较的最大差模偏差为%.6f mV；扣除此项后，后续切换新增偏差最大%.6f mV，仅用于分解，不替代上述绝对误差判定。

![转换时序、差模与共模](figures/conversion.png)

![八帧误差、端压和参考负载](figures/metrics.png)

转换/指标图中连续曲线按20 ps间隔导出用于显示；所有峰值、端压及建立检查使用全部原生时间点。比较时误差点按实际比较时钟50%%交叉插值。

## 复位/采样边界的端压问题

最坏点位于第二帧重新采样：110.029226 ns，N侧1C底板约−97.691 mV，连接0.9 V高参考的PMOS M12因此出现|VDS|与|VBD|约0.997691 V，超过0.99 V约7.691 mV；线性插值估计超限累计约5.04 ps。N侧1C至32C共六条高参考PMOS支路出现同类超限。原生CMI-2751/2755也记录到此事件。

输入在100 ns从码中心0切换到255，N输入下降；110.025 ns采样时钟过50%%后，行为采样器以10 ps接通，参考控制同时用50 ps边沿复位。波形显示顶板先下降、底板被电容耦合向下拉，而参考复位尚未完成。这定位了采样接通与参考恢复重叠的边界；是否主要由采样强度还是复位先后支配，仍需单变量对照。它不来自本次已理想化的数字标准单元或比较器内部。

![原生时间点复位下冲](figures/reset_stress.png)

建立测量已纠正：上一状态的检查止于下一次DAC更新命令时刻，由原生比较器有效输出50%%交叉加既定50 ps捕获、100 ps更新延时确定；仍要求本次栅极50%%后2 ns内建立。用下一栅极的50%%或1%%交叉作为旧状态终点，都会把下一次切换的耦合混入上一段。两版中间分析分别保存在results_original_window.json、results_1percent_window.json；电路、阈值和原始波形未改变。

建议下一轮保持外部采样窗口与关闭沿，单独提前参考复位，观察上述下冲是否消失；本轮没有修改拓扑或尺寸。

## 参考与驱动负载

- 高参考全820 ns净供能平均功率：%.3f µW；包含启动、复位及这组输入。
- 高参考电流绝对峰值：%.3f mA；低参考：%.3f mA。
- 参考MOS栅端正向供能对应平均：%.3f µW；是理想驱动面对的负载，不是标准单元实现功耗。
- 电源/参考可以吸收返回能量；净供能不能直接等同真实参考缓冲器功耗。当前没有给未知参考缓冲器虚构电流/功耗上限。

## 文件与限制

- 测试台：[test.scs](test.scs)；原生核心：[cdac_core.scs](cdac_core.scs)；边界：[wrappers.scs](wrappers.scs)。
- 预设指标：[measure.json](measure.json)；完整数据：[results.json](results.json)；来源：[provenance.json](provenance.json)。
- 仿真源：`manual8-cdac-isolation-tt-v1`；仅测量复核：`%s`，原始波形留在服务器；模型、采样器和控制器没有改成新基线，OA未变。
- Spectre X CX，1线程；原生日志记录tran reltol=1e-7、errpreset=conservative_sigglobal，vabstol=1e-8、iabstol=1e-14，maxstep=20 ps；过冲附近自适应时间点远小于20 ps。
- 未覆盖PVT、参考非零阻抗、真实数字驱动、Bootstrap、真实比较器反冲、物理电容失配/寄生、全码DNL/INL及FFT。码字正确不能覆盖端压或建立失败。
''' % ('当前边界下全部短测指标通过' if r['short_test_pass'] else '存在未通过项，见表',
         ', '.join(str(q['actual']) for q in r['captures']),yn('codes'),
         '8次' if checks['eight_comparisons'] else '异常','7次' if checks['seven_updates'] else '异常',
         '通过' if checks['eight_comparisons'] and checks['seven_updates'] else '**未通过**',
         s['max_compare_dm_error_V']*1e3,yn('comparison_dm_error'),s['max_compare_cm_error_V']*1e3,yn('comparison_cm_error'),
         sum(q['settled_by_2ns'] for q in r['segments']),maxsettle,yn('settling_2ns'),s['max_held_drift_V']*1e3,yn('held_drift'),
         s['max_conversion_s']*1e9,yn('conversion_time'),s['max_terminal_V'],yn('terminal_voltage'),
         ', '.join(r['CMI_codes']) or '未出现',yn('no_native_CMI'),
         max(abs(q['dm_error_V']) for q in init)*1e3,incremental*1e3,
         s['refp_net_power_W']*1e6,r['reference_peak_current']['vrefp:1']['abs_A']*1e3,
         r['reference_peak_current']['vrefn:1']['abs_A']*1e3,s['gate_positive_power_W']*1e6,RUN)
    (BASE/'README.md').write_text(text,encoding='utf-8')
    print(json.dumps({'checks':checks,'summary':s,'incremental_dm_error_V':incremental,'max_settling_ns':maxsettle},indent=2))


if __name__=='__main__':main()
