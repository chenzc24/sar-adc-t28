# SAR8 R3 全码静态和正弦动态测量

本轮测量对象是保存后的 `SAR_ADC_T28/sar_adc8_join_r3`，不是早期宏比较器或
理想DAC模型。保持R3拓扑、尺寸、100 ps恢复等待、50 ps参考边沿、100 ps
非交叠及原有输入／参考R/C网络不变。条件为TT／0.9 V／27°C，关闭失配和
瞬态噪声。因此得到的是确定性采样与转换性能，不包含物理噪声导致的退化。

完整结果尚未生成。当前真实运行状态见
`output/sar8_r3_performance/flow_status.json`；完成后读取同目录的
`report.md`、`summary.json`及 `figures/`。这些生成文件不会自动改写R3或
覆盖历史报告。本页保留测量定义和复现入口，不用理想计算值冒充实测指标。

## 原理图和数值精度

新导出网表已与R3保存清单逐子电路核对。测试台只改变输入源、分析、保存
以及加入测量节点；所有DUT子电路语句保持一致。新增Verilog-A是只读事件
计数监测器和由真实ADC输出反馈的输入二分搜索器，不替换任何ADC模块。

仍采用APS、conservative、reltol＝1e-5、vabstol＝1e-8、iabstol＝1e-13、
maxstep＝10 ps。只把输出改为1 ns间隔保存，求解器精度和最大步长没有放宽。
先用原R3正大输入的2帧全速波形作对照：精简输出的单／四线程版本读码均为
241，稳定顶板电压差均约1.61e-10 V，没有CMI或LTE。

静态测量台随后在666.99 ns的异步参考控制逻辑内部出现一次LTE临时放宽，
该帧比较次数和稳定读码仍通过。完整任务会保留这类警告并在汇总首页标出
相关case；带LTE放宽的指标仅为待精度复核的诊断值，不标成数值签核通过。

四线程试跑2帧耗时171 s，单线程312 s，因此完整批次采用每任务4线程、
最多4个任务并行。耗时主要在1543个原生MOS的瞬态求解；按短试跑外推，
完整测量是一天量级的任务，实际时间依码序、收敛和服务器负载变化。
本机运行器与SSH需保持可用，不能把输出抽样带来的文件缩小误认为求解完成。

## 全码静态

测量全部255个相邻码转换边界T1至T255。对每个边界，先分别测理想边界
±0.25 LSB的两个输入，要求输出分别为k−1和k，再做6次真实转换二分搜索。
最终区间宽度为1/128 LSB，约54.93 µV。初始夹界若失败，保留失败结果，
不把搜索结果当成有效边界，也不自动调整R3电路。

四个独立任务覆盖1–64、65–128、129–192、193–255；各有4帧预热。
输入只在旧转换结束后改变，之后保留原有40 ns获取时间。每个测量帧要求
原生比较时钟出现8个上升沿、90 ns与98 ns码字一致、98 ns时比较时钟为低，
且每位输出接近电源轨。监测器不直接观察内部写入／更新脉冲。

名义LSB为1.8 V／256＝7.03125 mV。内部码1–254的
`DNL[k]=(T[k+1]−T[k])/LSB−1`；饱和端码0、255的宽度不参与DNL。
完整相邻上下界输出同时检查所有256个码是否出现。

INL同时保留两种定义：相对名义理想边界的原始INL，以及去掉T1–T255端点
直线后的INL。后者采用实测端点LSB归一化，增益／首边界offset另列。
结果保留每个边界的上下限和DNL区间，不能把二分分辨率之外的小数位当成
物理准确度。这里测的是整机码转换位置，不是单独CDAC电压台阶。

## 正弦动态

连续输入全差分正弦，共1028帧；去掉前4帧，使用后1024点。
采样率10 MS/s，相干bin461，输入频率4.501953125 MHz；差分幅度为
−1 dBFS、峰值约0.802126 V，两端共模0.45 V。

使用未校正的实际输出码，矩形窗FFT，去除DC，把谐波保留在SNDR分母中。
主报告ENOB定义为 `(SNDR−1.76)/6.02`；ADCToolbox的结果作为独立交叉检查，
保存其版本和路径，不混用可能经过满幅归一化的ENOB。
不对输出做INL校准、增益拟合或相位修正来改善指标。

## 运行和证据入口

源配置为 `config/sar8_r3_performance.yaml`。
`scripts/integration/r3_performance.py`负责只读OA核对、新导出、测试台生成和
原生运行；`r3_performance_analyze.py`负责逐帧、边界、直接FFT与工具箱核对。
`r3_performance_flow.py`是一次性长任务：等待小规模验收结果，执行针对性
检查，随后提交完整批次，结束后自动离线分析并写出生成报告。
任何阶段失败会写入状态，不会宣称已有完整指标；没有定时通知或自动推送。

```powershell
# 以下为首次执行；已有case不可覆盖，flow不可重复启动。
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py preflight
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py pilot
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py run pilot_mt1_s0 pilot_mt4_s0
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py measure-smoke
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py run static_128_129_smoke_v3 sine_4_k1_smoke_v3
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance.py prepare-full
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/integration/r3_performance_flow.py
```

可重复的离线检查是项目Python下的
`-m unittest verification.integration.test_r3_performance -v`。
失败试跑、被替代的单线程测量台、全部原始网表、源文件快照、日志、PSF和
结果均留在 `output/sar8_r3_performance/`，不计作最终有效结果。
