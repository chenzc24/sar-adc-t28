"""Paired endpoint statistics on the signed thresholds of the original B samples."""
import csv
import json
from pathlib import Path
import numpy as np
from prepare import ROOT, DEST, PHYSICAL, GROUPS

def measurement(seed, group):
    if seed in (4121,4124):
        run='sar8phys-s%d-%s-v1'%(seed,GROUPS[group])
        path=PHYSICAL/'results'/run/'result.json'
    else:
        run='sar8rg30-s%d-%s-v1'%(seed,group)
        path=DEST/'results'/run/'measurement.json'
    d=json.loads(path.read_text())
    assert d['context']['seed']==seed and d['sample_mapping']['identical'] and d['native_data_valid']
    assert d['sample_mapping']['native_rows']==(89 if group=='base' else 87)
    if not d['threshold_valid']:
        raise ValueError('Unresolved threshold: '+run)
    lo,hi=np.array(d['held_threshold_interval_v'])*1000
    assert 0<hi-lo<.126 and abs((hi+lo)/2-d['held_offset_midpoint_v']*1000)<1e-8
    return (hi+lo)/2, (hi-lo)/2

def main():
    seeds=list(range(4101,4131))
    samples=np.array([[measurement(seed,g) for g in GROUPS] for seed in seeds])
    x=samples[:,:,0];hw=samples[:,:,1]
    sd=x.std(axis=0,ddof=1)
    # Resample whole seed triplets, keeping their correlation across conditions.
    ix=np.random.default_rng(1104).integers(0,len(seeds),size=(20000,len(seeds)))
    boot=x[ix].std(axis=1,ddof=1)
    gap=sd[2]-sd[1]
    ci=np.quantile(boot[:,2]-boot[:,1],[.025,.975])
    loo=[]
    for i in range(len(seeds)):
        s=np.delete(x,i,axis=0).std(axis=0,ddof=1);loo.append(s[2]-s[1])
    info=dict(samples=30,seeds=seeds,groups=list(GROUPS),mean_mV=x.mean(axis=0).tolist(),
              sample_sd_mV=sd.tolist(),sd_reductions_mV=(sd[0]-sd[1:]).tolist(),
              sd_p_off_minus_n_off_mV=float(gap),paired_bootstrap95_mV=ci.tolist(),
              leave_one_out_gap_mV=loo,half_bracket_sd_bound_mV=(np.linalg.norm(hw,axis=0)/np.sqrt(29)).tolist())
    (DEST/'stats.json').write_text(json.dumps(info,indent=2)+'\n')
    with (DEST/'samples.csv').open('w',newline='') as f:
        out=csv.writer(f);out.writerow(['seed','input_off_mV','input_N_off_mV','input_P_off_mV'])
        out.writerows([[seed,*row] for seed,row in zip(seeds,x)])
    msg='''# 再生支路失配分组对照，30 个配对种子

建议优先调整交叉耦合 NMOS 对 MNLATN/MNLATP。在输入对失配已关闭的条件下，
关闭再生 NMOS 的失配对总体门限离散的改善更大，逐颗剔除后排序一致。

保持 B 版 1 µm 输入管和真实 CDAC 保持接口。三组均关闭输入对失配，
并对每颗样本核对其余器件的原生随机参数。统计对象为带符号的保持输入门限。

| 条件 | 门限均值 (mV) | 门限样本标准差 (mV) |
|---|---:|---:|
'''
    for label,mean,dev in zip(['对照','再关闭再生 NMOS','再关闭再生 PMOS'],x.mean(axis=0),sd):
        msg+=f'| {label} | {mean:.3f} | {dev:.3f} |\n'
    msg+=f'''
关闭 NMOS、PMOS 分别使标准差降低 {sd[0]-sd[1]:.3f} mV 和 {sd[0]-sd[2]:.3f} mV。
两组残余标准差之差（PMOS 关闭减 NMOS 关闭）为 {gap:+.3f} mV，
按种子配对重抽样的 95% 百分位区间为 [{ci[0]:+.3f}, {ci[1]:+.3f}] mV。
逐次去掉一颗种子的差值范围为 [{min(loo):+.3f}, {max(loo):+.3f}] mV。
单个门限搜索分辨率约 0.125 mV。这是 TT 的模块失配诊断。

[逐种子门限](samples.csv) · [统计结果](stats.json)
'''
    (DEST/'README.md').write_text(msg,encoding='utf-8')
    print('Report written:', DEST/'README.md')
if __name__=='__main__':main()
