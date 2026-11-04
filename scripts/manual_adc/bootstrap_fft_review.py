"""Actual-code coherent FFT, independent ADCtoolbox comparison and report."""
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import adctoolbox

R=Path(__file__).resolve().parents[2]
OUT=R/'verification/manual_adc/bootstrap_fft_v1'

def spectrum(codes,k):
    x=np.asarray(codes,float);n=len(x);assert n==1024
    x-=x.mean()
    p=abs(np.fft.rfft(x))**2/n**2;p[1:-1]*=2
    assert abs(p.sum()-np.mean(x*x))<1e-9
    signal=p[k];rest=p.copy();rest[[0,k]]=0
    sn=float(10*np.log10(signal/rest.sum()));sf=float(10*np.log10(signal/rest.max()))
    tb=adctoolbox.analyze_spectrum(x,fs=1e7,max_scale_range=(-128,128),win_type='rectangular',side_bin=0,create_plot=False)
    assert abs(sn-float(tb['sndr_dbc']))<1e-7
    assert abs(sf-float(tb['sfdr_dbc']))<1e-7
    # Check the fundamental independently by direct complex projection.
    direct=2*abs(np.dot(x,np.exp(-2j*np.pi*k*np.arange(n)/n))/n)**2
    assert abs(direct/signal-1)<1e-10
    return dict(sndr_dB=sn,sfdr_dBc=sf,enob_bits=(sn-1.76)/6.02,
        enob_pass=bool((sn-1.76)/6.02>=7),sndr_pass=sn>=43.9,
        spectrum_dBc=(10*np.log10(np.maximum(p/signal,1e-30))).tolist(),
        spur_bin=int(np.argmax(rest)),toolbox_sndr_dBc=float(tb['sndr_dbc']),toolbox_sfdr_dBc=float(tb['sfdr_dbc']),
        toolbox_version=importlib.metadata.version('adctoolbox'),parseval_pass=True)

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());results=[];pending=[]
    for run in manifest['runs']:
        if run['label'].startswith('pilot'):continue
        p=R/'output/managed_execution/runs'/run['run_id']/'collected/derived/result.json'
        if not p.exists():pending.append(run['run_id']);continue
        z=json.loads(p.read_text());cfg=z['config'];w=cfg['warmup']
        assert z['native_state']['zero_error_footer'] and z['checks']['strobe_code_agreement'],z['checks']
        actual=z['rows']['0'][w:];ideal=z['rows']['1'][w:];assert len(actual)==len(ideal)==1024
        codes=[x['code'] for x in actual];icodes=[x['code'] for x in ideal]
        t=np.array([x['close_s'] for x in actual]);h=np.array([x['held_diff_V'] for x in actual]);f=cfg['frequency_Hz']
        mat=np.column_stack([np.ones(1024),np.sin(2*np.pi*f*t),np.cos(2*np.pi*f*t)])
        b=np.linalg.lstsq(mat,h,rcond=None)[0];res=h-mat@b
        fit=dict(lag_ps=float(-np.arctan2(b[2],b[1])/(2*np.pi*f)*1e12),gain_error_percent=float((np.hypot(b[1],b[2])/(.9*10**(-1/20))-1)*100),
                 offset_uV=float(b[0]*1e6),residual_rms_uV=float(np.sqrt(np.mean(res**2))*1e6),residual_peak_uV=float(max(abs(res))*1e6))
        results.append(dict(run_id=run['run_id'],config=cfg,metrics=spectrum(codes,cfg['k']),ideal_metrics=spectrum(icodes,cfg['k']),
            fit=fit,codes=codes,ideal_codes=icodes,code_delta_max=int(max(abs(np.array(codes)-icodes))),checks=z['checks'],native=z['native_state']))
    results.sort(key=lambda z:(z['config']['k'],z['config']['corner']))
    summary=dict(complete=len(results)==6,results=results,pending=pending,
        scope='Unchanged6um native Bootstrap + ideal behavioral remaining ADC; no transient noise, mismatch or parasitics',
        acceptance=dict(ENOB_min_bits=7,SNDR_min_dB=43.9,SFDR_threshold=None,SFDR_note='No separate 8-bit SFDR limit found; measured, not assigned a pass'))
    (OUT/'results.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    if results:
        available=sorted(set(z['config']['k'] for z in results))
        fig,axes=plt.subplots(len(available),1,figsize=(10,3*len(available)+1),sharex=True,squeeze=False)
        for ax,k in zip(axes[:,0],available):
            for z in results:
                if z['config']['k']!=k:continue
                c=z['config']['corner'];m=z['metrics']
                ax.plot(np.arange(513)*10/1024,m['spectrum_dBc'],lw=.85,alpha=.85,color={'ss':'#d65f28','tt':'#2675ad'}[c],label='%s: SNDR %.2f dB, SFDR %.2f dBc, ENOB %.3f'%(c.upper(),m['sndr_dB'],m['sfdr_dBc'],m['enob_bits']))
            ax.set_title('Input %.6f MHz | k=%d | rectangular FFT, 1024 codes'%(10*k/1024,k),fontsize=10)
            ax.set_ylim(-120,5);ax.set_ylabel('dBc');ax.grid(alpha=.2)
            if ax.lines:ax.legend(fontsize=8,loc='lower left')
        axes[-1,0].set_xlabel('Frequency (MHz)')
        fig.suptitle('M0 total 6 um | 10 MS/s | -1 dBFS | SS 0.81 V -40 C / TT 0.9 V 27 C\nBootstrap MOS; other blocks ideal VA; no noise/mismatch/PEX | Completed %d/6'%len(results),fontsize=11)
        fig.tight_layout(rect=(0,0,1,.88 if len(available)==1 else .94));fig.savefig(figdir/'spectra.png',dpi=170);plt.close(fig)
        fig,axes=plt.subplots(1,3,figsize=(12,3.7))
        for c in ['tt','ss']:
            zz=[z for z in results if z['config']['corner']==c]
            for ax,key,label in zip(axes,['sndr_dB','sfdr_dBc','enob_bits'],['SNDR (dB)','SFDR (dBc)','ENOB (bit)']):
                if zz:ax.plot([z['config']['frequency_Hz']/1e6 for z in zz],[z['metrics'][key] for z in zz],'o-',color={'ss':'#d65f28','tt':'#2675ad'}[c],label=c.upper())
                ax.set_ylabel(label);ax.set_xlabel('Input frequency (MHz)');ax.set_xlim(0,5);ax.grid(alpha=.2)
        axes[0].axhline(43.9,color='k',ls='--',lw=1,label='Target');axes[2].axhline(7,color='k',ls='--',lw=1)
        axes[0].legend();fig.suptitle('6 um Bootstrap hybrid | 1024 codes | TT / SS cold | SFDR has no separate limit',fontsize=11)
        fig.tight_layout();fig.savefig(figdir/'frequency_metrics.png',dpi=170);plt.close(fig)
    lines=['# 6 um Bootstrap：TT / SS冷角频谱','',('六组完成。' if not pending else '批次进行中；已完成%d/6组，未完成项不填指标。'%len(results)),
        '', '测试范围：仅Bootstrap晶体管级，其余ADC模块为理想VA。参考0.9 V、输入共模0.45 V、差分满幅1.8 V、输入−1 dBFS；10 MS/s。TT 0.9 V/27°C，SS 0.81 V/−40°C。MOS尺寸、110 ns首时钟及采样窗口/关闭沿保持不变。',
        '', '每组32帧预热，再取连续1024个实际输出码。矩形窗、去DC、谐波计入SNDR；不做相位/增益校正，不做−1 dBFS满幅补偿。ENOB=(SNDR−1.76)/6.02。目标ENOB≥7（SNDR≥43.90 dB）；未找到独立8-bit SFDR门槛，因此只报告SFDR测量值。',
        '', '| 工况 | 输入MHz | SNDR dB | SFDR dBc | ENOB bit | ENOB目标 | 理想对照ENOB |','|---|---:|---:|---:|---:|---|---:|']
    for z in results:
        c=z['config'];m=z['metrics'];lines.append('|%s|%.6f|%.3f|%.3f|%.4f|%s|%.4f|'%(c['corner'].upper(),c['frequency_Hz']/1e6,m['sndr_dB'],m['sfdr_dBc'],m['enob_bits'],'通过' if m['enob_pass'] else '未通过',z['ideal_metrics']['enob_bits']))
    high=next((z for z in results if z['config']['corner']=='ss' and z['config']['k']==461),None)
    if high:
        m=high['metrics'];ideal=high['ideal_metrics']
        lines+=['','当前判断：SS冷角4.502 MHz的6 um采样器在本混合测试台下'+('达到' if m['enob_pass'] else '未达到')+'7 bit目标，SNDR余量%.3f dB；相对同组全理想对照SNDR下降%.3f dB、SFDR下降%.3f dB。全理想对照不是TT晶体管结果。'%(m['sndr_dB']-43.9,ideal['sndr_dB']-m['sndr_dB'],ideal['sfdr_dBc']-m['sfdr_dBc']),
            '保持6 um继续完成TT与各频点比较；现有结果不支持仅因同关闭沿码差就增宽。'+('其余五组未齐，尚不能给出完整频段结论。' if pending else '完整工况判断以全部六组表格和逐帧检查为准。')]
    if results:lines+=['','![频谱](figures/spectra.png)','', '![随频率变化](figures/frequency_metrics.png)']
    lines+=['','保持电压的相位/增益拟合仅用于解释，与输出码FFT独立：','', '|工况|输入MHz|等效滞后ps|增益偏差%|拟合残差RMS µV|同关闭沿最大码差|','|---|---:|---:|---:|---:|---:|']
    for z in results:
        c=z['config'];f=z['fit'];lines.append('|%s|%.6f|%.2f|%.5f|%.2f|%d|'%(c['corner'].upper(),c['frequency_Hz']/1e6,f['lag_ps'],f['gain_error_percent'],f['residual_rms_uV'],z['code_delta_max']))
    lines+=['','原生Spectre X CX，单线程，conservative/maxstep50 ps；每帧连续事件观测8次比较/1次完成/无FAULT，1 ns保存波形独立核对输出码。ADCtoolbox与直接FFT交叉检查，另核对Parseval能量和基波直接投影。',
        '', '边界：本试验不验证真实比较器、SAR逻辑、参考驱动、噪声、失配或版图寄生。1 ns保存间隔不能用于尖峰最大值签核；完整原生CMI日志保留。通过本试验不代表整机PVT合格。',
        '', '未完成运行：'+(', '.join(pending) if pending else '无'),'']
    for z in results:
        lines+=['- '+z['run_id']+'：检查='+json.dumps(z['checks'])+'；原生警告='+str(z['native'].get('warning_codes',[]))+'；实际设置='+str(z['native'].get('effective_settings',{}))]
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(complete=summary['complete'],completed=len(results),pending=pending)))

if __name__=='__main__':main()
