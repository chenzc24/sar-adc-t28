"""Compare small recovered native metrics; never read full waveform arrays."""
import ast,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
V=R/'verification/sar8_campaign/recovery'
def main():
    results={k:json.loads((V/k/'result.json').read_text()) for k in ['a','b','cm','mm']}
    # Reuse reviewed comparison functions without importing POSIX coordinator.
    tree=ast.parse((R/'scripts/sar8_campaign/server_flow.py').read_text())
    keep=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['passed','solver_compare']]
    scope={};exec(compile(ast.Module(body=keep,type_ignores=[]),'comparison','exec'),scope)
    checks={k:scope['solver_compare'](results['b'],results[k]) for k in ['cm','mm']}
    rows=[]
    for a,b in zip(results['a']['frames'],results['b']['frames']):
        d=dict(frame=a['frame'],expected=a['expected_code'],a_code=a['code_98'],b_code=b['code_98'])
        for k in ['sample_int_close_s','seq_sample_close_s','external_close_s']:
            d[k+'_delta_ps']=(b[k][0]-a[k][0])*1e12
        for k in ['conversion_ns','preclose_error_source_v','preclose_error_pin_v']:
            d['a_'+k]=a[k];d['b_'+k]=b[k];d[k+'_delta']=b[k]-a[k]
        rows.append(d)
    ids=dict(a='sar8ab-phase60-a-tt-v1',b='sar8ab-phase60-b-tt-v1',cm='sar8camp-b-cm-bench-v1',mm='sar8camp-b-mm-bench-v1')
    elapsed={}
    for k,run in ids.items():
        p=subprocess.run([str(R/'.venv/Scripts/python.exe'),str(R/'scripts/management/project.py'),'run-status',run],capture_output=True,text=True,check=True,cwd=R)
        s=json.loads(p.stdout);(V/k/'source_status.json').write_text(json.dumps(s,indent=2)+'\n')
        elapsed[k]=s['simulation']['elapsed_seconds']
    for k,c in checks.items():c.update(elapsed_seconds=elapsed[k],speed_ratio=elapsed['b']/elapsed[k])
    summary=dict(functional_pass={k:scope['passed'](r) for k,r in results.items()},ab=rows,solver_checks=checks,elapsed_seconds=elapsed,electrical_verdict='deferred_not_qualified')
    (V/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(11,8),layout='constrained')
    for k,label in [('a','A: custom'),('b','B: standard cells'),('mm','B: MX')]:
        f=results[k]['frames'];x=[d['frame'] for d in f]
        for ax,key,scale in zip(axes,['code_98','preclose_error_source_v','conversion_ns'],[1,1e3,1]):
            ax.plot(x,[d[key]*scale for d in f],'.-',label=label)
    axes[0].plot(x,results['a']['context']['expected_codes'],'kx',label='Expected')
    for ax,y in zip(axes,['Output code','Pre-SEQ-close error (mV)','SEQ close to last update (ns)']):
        ax.set_ylabel(y);ax.grid(alpha=.25);ax.legend()
    axes[0].set_title('Low 60 ns / high 40 ns: frame 0 is the first valid conversion')
    axes[-1].set_xlabel('Frame');fig.savefig(V/'ab_solver_comparison.png',dpi=150);plt.close(fig)
    lines=['# A/B phase60 与 CX/MX 回收对比','',
           'A 为 Mmain2/L90 自建数字门冻结版，B 为相同模拟电路加标准单元数字逻辑。TT、0.9 V、27°C；初始低60 ns、高40 ns，周期100 ns。','',
           '|帧|目标|A|B|SAMPLE_INT B−A (ps)|SEQ_SAMPLE B−A (ps)|A转换 (ns)|B转换 (ns)|',
           '|---|---|---|---|---|---|---|---|']
    for d in rows:
        lines.append('|{frame}|{expected}|{a_code}|{b_code}|{sample_int_close_s_delta_ps:.3f}|{seq_sample_close_s_delta_ps:.3f}|{a_conversion_ns:.4f}|{b_conversion_ns:.4f}|'.format(**d))
    lines+=['','全部有效帧（含首帧）的码字、事件次序/计数和原生观察器交叉校验：`'+json.dumps(summary['functional_pass'])+'`。','',
            '|案例|仿真耗时(min)|相对B严格CX速度|实际reltol / method|数值诊断|','|---|---|---|---|---|']
    for k in results:
        s=results[k]['effective_settings'];ver='reference' if k in ['a','b'] else str(checks[k]['pass_diagnostic'])
        lines.append('|%s|%.3f|%.3fx|%s / %s|%s|'%(k,elapsed[k]/60,elapsed['b']/elapsed[k],s['reltol'],s['method'],ver))
    for k,c in checks.items():lines+=['',k+'诊断差异：`'+json.dumps(c['issues'])+'`。']
    lines+=['','![A/B与求解器对比](ab_solver_comparison.png)','',
        '四个新增 Bootstrap 内部保存名大小写错误，原生日志明确忽略，原分析因此退出。现以独立 analysis-only 运行重用原始波形，缺失内部电容电压记为 null；并未补造预充电内部波形。功能/时序所需原生信号完整。',
        '原高电平启动的 A/B 首帧均为2而非0；相位调整后首帧0及后续9帧均须单独检查。本测试是DC初始化，不含电源爬升/POR验证。',
        '建立诊断采用每位下次比较前实测DAC值为参考，不是理想DAC精度。求解器短测容差不等于全码/FFT精度证明；耗时包含服务器竞争。',
        '过压告警保留，本轮按用户要求不作电气合格判定；无噪声、失配或PEX。',
        '原有限接力程序因分析失败停止；后续执行状态另行记录，不由上述结果推断。']
    (V/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
