# B版瞬态噪声短测

已提交3组独立managed案例，保持已测FFT的B冻结电路、4.501953125MHz/-1dBFS输入、低60ns/高40ns时钟、50ohm/4pF参考与5fF输出负载。40帧，前8帧预热，32帧仅诊断，不作相干FFT或最终ENOB。

- sar8noise-b-short-off-s101-v1：无噪声对照。
- sar8noise-b-short-g1-s101-v1：noisefmax=1GHz、noisefmin=1MHz、seed101、scale1。
- sar8noise-b-short-g2-s101-v1：仅将上限改为2GHz。

外部四个50ohm电阻显式isnoisy=yes，器件模型噪声纳入；理想电压源无附加噪声，外部时钟无抖动，无失配/PEX。内部MOS/电阻实际噪声取决于模型，后续通过结果差异确认。保留noise_worst模型section。低频拐点1MHz只适用于短记录诊断，不代表完整低频噪声。

截至 2026-10-29T16:50:28.551424+08:00 三组均running；两组含噪原生日志分别确认1/2GHz、1MHz、seed101。无噪对照已输出2帧。未完成分析，不能宣称功能或带宽收敛通过。提交无噪对照时SSH回执超时，随后直接读取原run状态确认已运行，没有重复提交。其他两组提交回执成功。resistor帮助读取超时，但无噪对照已通过实例解析进入瞬态；tran帮助已取得。

脚本reduce_short.py流式独立解码，核对40帧输出与事件计数，并保留顶板/输入采样值、实际噪声日志、CMI告警。最多4线程/1GiB每任务，共享7槽位不变；4个全码任务未修改。阶段下一步：完成后managed analyze/collect，比较同时间顶板差异和协议，再决定正式1024点带宽/种子设置；不自动以短测冒充最终频谱。


## 2026-10-29 19:55 回收结论

三组仿真与managed流式分析均exit0，40/40帧原生解码和observer完全一致，启动及正常帧8/8/8/16事件计数、码字稳定性、转换时间均通过短测检查。每组回收7个小文件约64kB，无raw下载；分析峰值约6.2MiB。实际噪声参数由原生日志确认。

| 条件 | 仿真耗时(min) | 最大转换时间(ns，40帧) | 正常32帧较无噪声码字变化 | 正常32帧保持差分电压差值RMS(µV) |
|---|---:|---:|---:|---:|
| off |25.20|29.35453|0|0|
| 1GHz |78.06|29.32371|2，均1LSB|86.37|
| 2GHz |96.99|29.34558|1，1LSB|77.98|

1GHz另有预热frame2变化183→184；正常frame13为152→151，frame28为16→17。2GHz正常frame15为82→81。这里是与无噪声对照的变化，不直接判为错码。内部采样关闭沿较off最大变化分别0.0746/0.1113ps，未发现握手/关断时序破坏。

差值RMS包含相同时间采样下的整个电路响应差异，并非整个ADC输入等效噪声；仅32帧、单seed101，2GHz较小不能解释为更低噪声或带宽已经收敛。1MHz低频设置也仅用于短测。保留所有CMI2751–2755及数值告警，功能通过不代表端压通过。无1024点含噪FFT或最终SNDR/ENOB结果，未提交长测。下一步补独立种子的带宽对照，再选正式1024点设置。

明细：[comparison.json](comparison.json)。原始分析：output/managed_execution/runs/sar8noise-b-short-{off,g1,g2}-s101-v1/collected/derived/result.json，身份及hash见各collection_receipt.json。


## B1024含噪声FFT已启动

时间：2026-10-29T20:04:08.769043+08:00。run_id：`sar8noise-b-tt-fft1024-g2-s101-v1`，managed simulation running；原生日志确认noisefmax=2GHz、noisefmin=10kHz、noiseseed=101，noisescale=1已冻结于输入。保留原1032帧（8预热+1024有效）、4.501953125MHz/-1dBFS、0.9V/27C、60ns低/40ns高、MX4线程、实际reltol1e-6/trap、maxstep/save10ps。DUT/library/监测器/原dynamic_reduce脚本SHA均与完成无噪FFT相同；仅新增噪声tran参数和四个外部电阻显式isnoisy=yes，不增加raw信号。

用户明确批准先启动此单种子长测；额外种子/带宽收敛尚未完成。资源预检通过，无清理或修改其他4个静态任务。约40小时仅为短测线性外推，尚非实测长跑ETA。

服务器有限完成后处理已运行：`campaigns/sar8-noise-20261029-b101`，只观察此run，完成后通过managed analyze启动流式分析并退出，不重复提交仿真或重试失败任务。自动产出derived/result.json、comparison.json、spectrum_comparison.svg，与冻结无噪B的原始分析结果对比。小结果后续collect回本地，SVG回收后需视觉检查。无需本机常开；没有恢复周期heartbeat。

对比范围：SNDR/SFDR/ENOB，1024码字差异（不自动判错码），1032帧握手/稳定检查，采样关闭沿、最大转换时间、功耗网格估计。保留原始警告和端压未验收状态。此时未完成，不存在含噪声长FFT指标。
