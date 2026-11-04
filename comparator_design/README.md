# 比较器设计工作区

从2026-10-27起，本轮比较器尺寸、TB、脚本、数据与图统一放在这里。来源是用户手搭SAR_ADC_T28_manual的15MOS拓扑；原OA和其他设计分支不修改。

## 文件入口

- [PLAN.md](PLAN.md)：指标、模块边界和验证顺序。
- [RESULTS.md](RESULTS.md)：本轮实测结果、波形及未完成项。
- [OVERSHOOT.md](OVERSHOOT.md)：过冲节点、精确时间、原生CSV与原因分析。
- [CURRENT_ATTRIBUTION.md](CURRENT_ATTRIBUTION.md)：支路电流证据、归因修正与分组尺寸方案。
- [PRECHARGE_A2.md](PRECHARGE_A2.md)：M2/M4=2倍的首个FF热角实测点，过冲与复位波形对比。
- [PRECHARGE_A124.md](PRECHARGE_A124.md)：M2/M4=1/2/4倍完整对比，复位改善与启动过冲的权衡。
- [PRECHARGE_A4B124.md](PRECHARGE_A4B124.md)：固定M2/M4=4倍，M3/M5=1/2/4倍实测，两类过冲均恶化。
- [PRECHARGE_WIDTH_LIMIT.md](PRECHARGE_WIDTH_LIMIT.md)：M3/M5现有100nm已到当前模型支持下界，未提交域外缩宽扫描。
- [PRECHARGE_LENGTH.md](PRECHARGE_LENGTH.md)：固定W100nm，L30/60/90nm对比；长L改善LP/LN复位上冲，却恶化启动及下一输入更新扰动。
- [INPUT8.md](INPUT8.md)：M8/M9输入对4→8倍；复位上冲降低，但启动过冲和输入反冲恶化，不采用8倍。
- [CLOCK_RISE.md](CLOCK_RISE.md)：固定A4及50%时刻，只扫上升沿50/100/200ps；启动削峰有效，越限变宽，复位与输入反冲基本不变。
- [CLOCK_FALL.md](CLOCK_FALL.md)：固定上升200ps，下降50/100/200ps；复位削峰约33%，主脉冲变宽，判决不变，端压仍失败。
- [CLOCK_500.md](CLOCK_500.md)：上升/下降扩至500ps；进一步削峰但展宽，全程最坏转为下一输入更新的net2，下降500ps另出现小幅复位上冲。
- [EDGE_CURRENT.md](EDGE_CURRENT.md)：固定200/500ps，分开定位输入更新的M9漏端动态注入与复位的M6/M7源端耦合，含三张电流/电荷波形及尺寸方案。
- [EDGE_SIZES.md](EDGE_SIZES.md)：固定200/500ps，两组独立尺寸实测；预充加倍改善net1/net2却恶化LP/LN，输入对减半降低馈通但未消除全程端压瓶颈。
- [EDGE_COMBO.md](EDGE_COMBO.md)：组合M3/M5×2与M8/M9×2，输入更新上冲降至0.901mV，但LP/LN复位仍4.494mV，含四组叠图。
- [COMBO_LATCH_CURRENT.md](COMBO_LATCH_CURRENT.md)：固定组合版，两侧各七支路及端电荷实测确认交叉耦合动态注入、M2/M4主要回拉；含三图和针对性尺寸建议。
- [COMBO_A8.md](COMBO_A8.md)：组合版M2/M4从4倍到8倍；LP/LN复位上冲减半，但启动上冲、判决延迟和功耗增加，含四类事件对比图。
- `baseline/`：冻结的原15MOS网表、原生模型引用及SHA；不是标准库/PDK模型内容副本。
- `scripts/`：生成、托管执行、流式测量与绘图；全项目最多两个重任务并行。
- `testbenches/`：每个实验的独立冻结输入。
- `recipes/`：managed配方；项目基础设施仍在management/runs登记。
- `results/`：每项结果、原生日志和证据位置；完整波形保留在项目服务器SSD。
- `figures/`：精选波形与对比图。

## 当前测试边界

比较器是真实15MOS电路；供电、输入源、比较时钟理想。两种输入模式同时测试：低阻直接驱动用于速度/极性；理想开关预充后断开的1.28pF/侧用于保持节点反冲。输入电压由合法共模/差模组合给出。

每100ns安排8次比较，每次高1.5ns、低2.5ns，50ps时钟边沿。32次比较覆盖CM0.45/0.675/0.453516V、小差分±0.25/0.5/1LSB、合法大差分及强正/强负前次判决。当前并非0.5ns最短复位历史试验，也未扫失调门限、噪声和失配。

## 接收负载

`cmpdesign-load-tt-v1`按每侧8个原生DFQD1的D端+一个OR2D4输入测得动态Q/ΔV约6.012–6.049fF（50/200ps边沿，DFF时钟低）。尺寸筛选使用6.1fF/输出，**不是空载**。该值包含测试状态下的耦合，不能视为完整非线性输入阻抗或所有PVT下的上界。

真实接收FF的CMI告警仍保留在负载实验日志；尺寸筛选用等效电容隔离比较器，不把该告警当成已经修复。真实接口的端压、时序与反向耦合另验。

## 首轮尺寸分组

所有MOS保持原W=100nm、L=30nm、nf=1及junction参数，表内为multi倍数，因此每组等效并联宽度=0.1µm×multi。这样既不改变拓扑，也不猜测PDK几何参数；不是修改标准库内部晶体管。

| 候选 | 输入对 | 尾管 | 再生N/P | 预充P | 输出N/P |
|---|---:|---:|---:|---:|---:|
| B0原版 | 1 | 1 | 1/1 | 1 | 1/1 |
| I4 | 4 | 1 | 1/1 | 1 | 1/1 |
| T4 | 4 | 4 | 1/1 | 1 | 1/1 |
| R2 | 4 | 4 | 2/2 | 1 | 1/1 |
| O4 | 4 | 4 | 2/2 | 1 | 4/8 |
| P4 | 4 | 4 | 2/2 | 4 | 4/8 |

相邻候选只改变一个功能组（再生组/输出组内N、P一起设定），用于区分输入、再生、驱动和复位的影响。没有以小信号判决正确代替噪声/失配验收。

## 运行

在项目根目录使用项目Python：

```powershell
.venv/Scripts/python.exe comparator_design/scripts/build_sizing.py
.venv/Scripts/python.exe comparator_design/scripts/run.py cmpdesign-sizing-tt-v1
```

已有run ID绑定已冻结输入，后续修改需新ID。不要将再次执行构建命令误认为可覆盖已提交实验。日常新增候选使用`build_sizing.py --run <新ID> --candidates <候选名> --corner <tt/ss/ff> --vdd <电压> --temp <温度>`；测量修正使用绑定既有完成源的analysis-only。`report.py`更新结果表与图。

当前结果和后续选择由本目录RESULTS.md更新；未采用新的ADC/OA基线，不commit/push。
