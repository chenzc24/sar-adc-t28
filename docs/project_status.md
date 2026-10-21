# SAR ADC 当前进度与文件导航

更新日期：2026-10-21。当前项目是 **8-bit、10 MS/s、0.9 V、全差分 flat CDAC、
顶板 Bootstrap 采样、异步 SAR 控制**。优先目标是把现有模块接成标称条件下
可运行的整机；PVT、随机失配和尺寸优化暂后置，但不把已发现的应力问题抹去。

**当前开发顶层仍为R3，已接入B参考栅控事件修复，保留0.1 ns恢复等待＋50 ps边沿。**
16个理想栅控实例改用独立 `sar8j_aligned_refgate_b`，原生管级拓扑、尺寸、
其他OA字段和既有求解精度不变。接口／网表核对及导入模型小单元回归通过，
已从本轮新OA导出完成下述24帧正弦短测，尚未完成全码性能。
见[B同步与前置验证方案](r3_b_oa_adoption.md)。

2026-10-21 08:59 已从新B OA导出启动单周期时域前置测试：500kHz、差分±0.8V、
10MS/s，4帧启动＋20帧观察，共24帧／实际2.4us，管级电路和精度不变。
仅这一组，不计算FFT或全码指标。配置 `config/r3_b_sine_period.yaml`，
运行与巡检数据在 `output/b_sine_period/`。现已完成计算、解析和波形审核：
24帧均为8次比较／写入／更新，最终读码稳定；20个观察点相对理想码最多
差1码，无大幅跳码。采样保持误差最大4.464649mV，14/20点超过原预算
1.7578125mV，故未通过。最差帧关断前1ns已落后源端4.717954mV，主要误差
在跟踪阶段已经形成。无CMI/LTE放宽告警，比较器输入对端电压最高0.898006V。
这些是单周期时域筛查，不是SNDR/ENOB或全器件签核。见
[B单周期结果与波形](b_sine_period.md)；计划为
`plan/2026-10-21-b-sine-one-period/plan.md`。未改变电路或自动追加实验。

现有波形的[误差分离](b_sine_decomposition.md)进一步得到：等效滞后1.781261ns，
增益偏差−0.025815%；去除直流和基波后的保持残差峰值8.260µV／RMS5.604µV。
关断前跟踪外推与保持值之差最大0.328mV，其中非基波残差峰值6.010µV。
这不是纯电荷注入的唯一测量，也不替换原始未通过的采样预算；未新增仿真或改电路。

2026-10-21已完成[主采样管W单变量短正弦扫描](b_sine_main_w.md)：1×复用上述
原生数据，2×/3×为独立原生网表；每组24帧、4帧启动＋20帧观察。只改两侧
Mmain的W及派生面积／周长，L、nf、拓扑、CDAC、外部时序和精度配置不变。
等效滞后1.781/0.882/0.574ns，保持增益偏差−0.0258/−0.0471/−0.0686%；
原始保持误差峰值4.465/2.242/1.519mV，超预算点14/10/0个。3×是本轮候选，
但关断总增量峰值0.328/0.460/0.624mV、保持非基波残差峰值8.260/13.835/
21.430µV均随W增加。2×有一次1759.41ns的LTE局部放宽，另两组没有。
三组24帧均8次比较／写入／更新且最终码稳定；这不是全码或PVT合格。
OA仍为主采样管1×；未采用候选或重开全码。计划与原始结果位于
`plan/2026-10-21-b-sine-main-w/`、`output/b_sine_main_w/`。

以下四组合龙数字为事件修复前R3的历史短测试结果，R1/R2也保留作历史对照。
顶层 `sar_adc8_join_r3`，测试台 `tb_sar_adc8_join_r3`，均在 `SAR_ADC_T28`。
16组理想参考栅控显式设置新时序，保留共享整字提交和100 ps非交叠；
原生拓扑、尺寸及参考50Ω＋4pF网络不变。保存OA两次独立导出均与已测试
候选一致，四组新APS合龙确认通过：码字14/14、241/241、14/241、241/14，
保持误差最大0.200474mV，全比较残差最大0.808021mV；参考管／比较器端电压
峰值0.944611／0.950686V，标称扫描低于0.99V。见[R3入口与复验](sar8_join_r3.md)。
这不是实际管级时钟／参考驱动实现，仍未完成PVT、失配、噪声或全器件签核。
旧R2报告保留当时的2ns／20ps及过压结果，不代表R3现状。

原R3的[全码静态与相干正弦动态测量](sar8_r3_performance.md)已中断，四个
原生进程和本地协调器均已退出，完整DNL、INL、SNDR、ENOB未生成。
这批使用修复前模型，不能代表B。`output/sar8_r3_performance/flow_status.json`
是未更新的阶段记录，不是运行心跳；本轮没有重启长任务，先讨论定向短验证。

**冻结R1完成了真实模拟链与原生异步控制器合龙，但未通过器件应力验收。**
顶层 `sar_adc8_join_r1`，测试台 `tb_sar_adc8_join_r1`；参考采用3×pass MOS及
理想栅压，保留真实Bootstrap/MOM/StrongARM/控制MOS。11次标称APS、22帧
码字和逐位时序正确，最大比较前误差0.8064mV；参考管端电压峰值1.2668V、
比较器输入峰值1.2500V，超过当前0.99V模型检查线。见
[冻结电路、文件入口和联合结果](sar8_join_r1.md)。这不是已合格整机。

本日后续控制更新：[精简异步SAR](sar8_simple_async.md)已替代旧多阶段握手
控制器作为选定方案。新顶层 `sar_logic_8b_async_simple`，仅采样相位及本地
比较/写入/更新，未增加EOC；21种原生cell、13个有界APS验证case，FF器件
应力及真实模拟链整合仍未通过。下方库存快照保持原清点时间点，不冒充已包含
这些新cell；新cell/端口以[专用清单](../verification/sar8_simple/cells.json)为准。

首组合龙候选已按用户选择整理为
[SAR8_JOIN_R0_3X_IDEAL_GATE](sar8_join_r0.md)：保留现有采样/比较器/精简
原生控制器，采用3×参考开关和理想栅压，并统一P/N映射及采样内中点恢复。
R0保留为当时的源版本冻结准备；其后已由上面的R1落地接口和统一顶层并完成
联合仿真。原始库存和单模块报告保留各自记录时间，不冒充最新联合验收。

## 1 项目到底在哪里

```text
本机 E:\bridge-Agent-T28\                 工具工作区，不是 ADC 仓库根目录
├─ projects\sar-adc-t28\                 本项目独立 Git 仓库
├─ virtuoso-bridge-lite\                 Virtuoso 连接/仿真工具仓库
├─ ADCToolbox\                           ADC 分析依赖，非自研 ADC 电路
└─ veriloga-skills\                      Verilog-A 技能来源仓库

远端 /home/chenzc_intern25/TSMC28/llm_IO/
└─ SAR_ADC_T28/                          Virtuoso OA 项目库
   └─ <cell>/<view>/                    schematic、symbol、veriloga 等
```

远端 technology 为 `tsmcN28`，桥接 profile 为 `t28_io`。
本次已在实际 CIW 中确认库路径、技术绑定、全部 cell/view 名单，另读回八个
关键顶层/模块。没有保存、重建、移动或删除任何原理图。

本地 Git 分支为 `exp/cdac-flat8-device`。清点对应的时间、源提交、实际数量
及顶层 master 清单见 [snapshot.json](inventory/2026-10-20/snapshot.json)。
原理图源数据在远端 OA；本地 `input.scs`、截图和 PSF 都不能替代 OA 原理图。

## 2 各阶段做到了哪里

| 阶段 | 已完成内容和方法性质 | 当前用途和后续 |
| --- | --- | --- |
| 基础设施 | 本地仓库/工作流；远端库绑定；native OA 导出、Spectre、结果解析 | 已可用；bridge 与 ADC 是两个仓库 |
| 理想算法 | Python 逐位 SAR；ADCToolbox 做静态/频谱分析；先 10-bit，后迁移 8-bit | 作为黄金参考，不是器件电路 |
| 误差预算 | 从 ENOB/SNDR 推导总预算，再工程分配采样、比较器、参考、jitter 等 | 已有 8-bit 默认预算；旧 10-bit 数值仍保留在历史资料 |
| 时钟行为级 | 理想/带事件随机误差的 Verilog-A，Spectre 静态/动态/时序 | 已完成同步基线；当前异步事件模型也已建立 |
| 器件与一阶模型 | T28 单管/MOM 表征；RC 采集/建立、gm/C 再生和 jitter 约束 | 已完成；不是一个完整放大器式的全 ADC 小信号模型 |
| 电气宏模型 | 显式 CDAC、电阻/继电器开关、有限参考、再生宏比较器、VA 闭环控制 | 10-bit 5+5 和 8-bit flat 都有；8-bit 是当前架构参考 |
| Bootstrap | 历史 core/隔离/延迟复位实验；后按用户 Canvas 拓扑映射 T28 1.8-V MOS | 当前 8-bit 使用独立 1-µm 主开关副本；标称采样已验证，非全角合格 |
| 器件 CDAC | T28 MOM 单元/512 独立单元阵列、原生参考开关/驱动、全码与动态诊断 | 三轨基线可复现；复位增强/双轨互补是独立候选，尚未取代它 |
| StrongARM | 11 个 T28 core MOS；速度、噪声、失配及 CDAC 接口测试 | 当前尺寸先作为整机集成起点，暂不因 PVT/失配继续优化 |
| 原生异步 SAR | 新21-cell采样初始化控制器；旧26-cell握手方案保留 | 两帧/代表码/快慢延时/SS/FF功能、打断/恢复及真实比较器接口已测；FF应力和真实采样/DAC整合未完成 |
| 完整器件级整机 | 两条部分集成线分别存在，见下一节 | 需要合并真实模拟链与原生异步控制，不是已完成整机验收 |
| 版图与签核 | 本次库清点没有 layout view；没有 DRC/LVS/PEX 闭环 | 尚未进入 |

早期阶段和历史结果不删除。它们是推导来源，不应被当成当前器件级实现。

## 3 两条部分集成线不能混为整机完成

| 可以打开的测试台 | 采样与 CDAC | 比较器 | SAR 控制 | 它证明什么 |
| --- | --- | --- | --- | --- |
| `tb_sar_macro_flat_8b` | 理想电容、有限 R/继电器电气模型 | gm/C 电气宏模型 | Verilog-A | 架构闭环与动态误差机制 |
| `tb_cdac8_nominal` | 原生 Bootstrap、PDK MOM、原生三轨参考开关 | 电气宏模型 | Verilog-A 固定位周期 | 模拟链的大扫描诊断，不是全原生 ADC |
| `tb_cdac8_nominal_sar` | 同上 | 真实 `sar_strongarm_t28` | Verilog-A 固定位周期 | 原生模拟链＋真实比较器接口 |
| `tb_cdac8_dr_strongarm` | 原生 Bootstrap、PDK MOM、原生双轨候选 | 真实 StrongARM | 另一套 Verilog-A 固定位周期 | 双轨候选诊断，不是异步整机 |
| `tb_sar8s_logic` | 理想 `sar8a_plant` | plant行为轨道 | 新精简原生异步控制器 | 新时序、直接工作码、P/N控制、采样打断/恢复 |
| `tb_sar8s_strongarm` | 理想 `sar8a_plant` 采样/DAC | 真实StrongARM | 新精简原生异步控制器 | 新本地时序与未修改比较器的代表码接口 |
| `tb_sar8a_logic` | 理想 `sar8a_plant` | plant 生成的行为轨道 | 原生异步控制器 | 控制握手、存储、故障/恢复 |
| `tb_sar8a_strongarm` | 理想 `sar8a_plant` 采样/DAC | 真实 StrongARM | 原生异步控制器 | 控制器与实际比较器握手 |

因此，`tb_cdac8_nominal_sar` 的“sar”不意味着控制器已是管级；
`tb_sar8a_strongarm` 的“strongarm”也不意味着已经接上真实 CDAC。
参考电源仍是理想源＋有限 R/C；异步保护延时中的 R/C 也是显式理想元件。
两者都不是已经做完了晶体管 reference buffer、PDK R/C 或 clock tree。

## 4 现在优先打开哪些 Virtuoso 文件

下面全部位于库 `SAR_ADC_T28`。先看 schematic；VA 控制器/plant 看 veriloga，
symbol 只是接口图形。完整逐项清单见 [所有 cell 与 view](inventory/2026-10-20/virtuoso_cells.md)。

| 目的 | 推荐 Cell | 对应本地入口 |
| --- | --- | --- |
| 看当前架构闭环 | `tb_sar_macro_flat_8b` | [8-bit 迁移报告](eight_bit_flat_migration.md)、`scripts/eight_bit/` |
| 看器件模拟链＋真实比较器 | `tb_cdac8_nominal_sar` | [器件 CDAC 报告](cdac_flat_8b_device.md)、`scripts/cdac8_device/` |
| 看异步控制器顶层 | `sar_logic_8b_async` | [异步实现报告](sar8_async_implementation.md)、`scripts/sar8_async/circuit.py` |
| 看异步控制＋真实比较器 | `tb_sar8a_strongarm` | `scripts/sar8_async/bench.py`、`verification/sar8_async/summary.json` |
| 看实际采样开关 | `sar_bootstrap_canvas_flat_8b` | [8-bit 开关尺寸与负载](eight_bit_flat_migration.md)、`scripts/eight_bit/build_oa.py` |
| 看比较器本体 | `sar_strongarm_t28` | [当前 8-bit 基线](strongarm8_baseline.md)、`scripts/strongarm8/` |
| 看 MOM 单元/实体阵列 | `cdac8_unit`、`cdac8_device` | `config/cdac_flat_8b_device.yaml`、`scripts/cdac8_device/oa.py` |
| 看确定性加速阵列 | `cdac8_device_nominal` | 同上；电容按 m 聚合，不能替代独立单元 MC |
| 看三轨参考开关 | `cdac8_ref_switch_b0`～`b7` | `scripts/cdac8_device/oa.py` |
| 看复位驱动实验 | `tb_cdac8_reset_strongarm`、`cdac8_reset_nominal` | [复位实验](cdac8_reset.md)、`scripts/cdac8_reset/` |
| 看双轨候选 | `tb_cdac8_dr_strongarm`、`cdac8_dr_nominal`、`cdac8_dr_sw_b0`～`b7` | [双轨候选](cdac8_dualrail.md)、`scripts/cdac8_dualrail/` |

### 异步控制器内部

`sar8a_frame` 管帧/参考所有权，`sar8a_cmp_if` 接收比较器轨道，
`sar8a_seq` 生成握手顺序，`sar8a_token8` 管 MSB→LSB 位序，
`sar8a_bit` 存工作位，`sar8a_out8` 锁存完整输出字，`sar8a_status`
管 BUSY/VALID/FAULT，`sar8a_bbm` 做参考非交叠。其余是组合门、DFF/SR
及 `sar8a_delay_*` 保护延时。先看这几个模块，不必从所有 leaf 门开始翻。

### 当前关键结果各属于什么层次

- 选用 MOM 单元约 4.004 fF，每侧 256Cu≈1.025 pF。这是当前器件候选，
  不是早期宏模型沿用的 Cu=6.86047 fF / 每侧 1.756 pF。
- 三轨模拟链 1024 点标称正弦曾得到 SNDR≈48.76 dB、ENOB≈7.81；
  该次使用宏比较器/VA 控制，不能算原生异步整机性能。
- StrongARM 标称小差分判决约 191 ps；固定码 CDAC 接口判决时差分
  kickback≈0.039 mV。物理噪声/失配结果另见比较器报告，按当前指示暂不优化。
- 原生异步控制器＋理想 plant 的代表测试 code145，VALID≈87.35 ns；
  换真实 StrongARM 的代表测试 VALID≈86.42 ns。它们不是全码原生动态验证。
- 双轨互补候选已有真实 T28 原理图和标称正确码，但仍有参考换轨/恢复过压。
  它**不是严格单调下切**，也未取代三轨基线。

## 5 本地文件怎么找

完整源文件逐项导航：[local_files.md](inventory/2026-10-20/local_files.md)。
可筛选表格：[local_files.csv](inventory/2026-10-20/local_files.csv)。
覆盖 Git 已跟踪及未忽略新文件，标明清点时 Git 状态、大小、SHA256。
环境、缓存和大规模原始仿真输出不混入源文件清单；本索引目录自身不递归列入。

| 目录或文件 | 放什么 | 现在主要看哪里 |
| --- | --- | --- |
| `config/` | 规格、预算、器件/测试合同 | `design_spec.yaml`、`cdac_flat_8b_device.yaml`、`strongarm8_baseline.yaml`、`sar8_async_impl.yaml` |
| `models/behavioral/` | Python 算法/事件模型 | `sar_adc.py`、`sar_async.py` |
| `models/veriloga/` | 行为 ADC、测试激励、旧 VA 控制器 | `sar_adc_ideal_8b.va`、`cdac8_controller.va`、`sar8a_plant.va`、`sar8a_monitor.va` |
| `scripts/eight_bit/` | 8-bit 迁移、宏模型、采样接口 | `build_oa.py`、`run_veriloga.py`、`run_electrical.py`、`analyze.py` |
| `scripts/cdac8_device/` | MOM、三轨 CDAC 创建/测试 | `oa.py`、`run.py`、`analyze.py`、`analyze_system.py` |
| `scripts/strongarm8/` | 不改尺寸的比较器测试 | `run.py`、`analyze.py`、`figures.py`；`offset_search.va` 仅为测试平台激励 |
| `scripts/sar8_async/` | 原生异步逻辑、导出、仿真/审核 | `circuit.py`、`oa.py`、`bench.py`、`suite.py`、`audit.py` |
| `scripts/cdac8_reset/` | 独立复位驱动候选 | 不要把 `oa_candidate.py` 自动当成主基线重建脚本 |
| `scripts/cdac8_dualrail/` | 双轨互补参考实验 | `oa.py`、`run.py`、`analyze.py`；候选而非已选最终架构 |
| `scripts/characterization/` | 从单管到旧 Bootstrap/StrongARM 的历史工具 | 很多脚本创建/修改 OA，不能按文件名随意全部执行 |
| `netlist/` | 本地手工维护/生成的回归入口 | `eight_bit/README.md`、`cdac8_device/README.md`；不是远端 OA 备份 |
| `verification/` | 定向测试和小型结果汇总 | `eight_bit/`、`cdac8_device/`、`strongarm8/`、`sar8_async/` |
| `docs/`、`docs/figures/` | 解释、结果图和审核资料 | 本页为总入口，按模块进入报告 |
| `docs/learning/` | 用户要求保存的推导经验 | `error-budget-allocation.md`、`veriloga-event-noise-injection.md` |
| `plan/` | 每次实验边界、执行状态 | `log.md` 是按时间的维护记录，不是当前主线目录 |
| `virtuoso/cell_manifest.yaml` | 计划和历史登记 | 不等于远端实际完整清单；差异见下一节 |
| `review/` | 离线交互审核界面源代码 | 冻结于历史 10-bit，不能当作当前 8-bit 全貌 |
| `output/` | 原始日志、导出网表、PSF、波形、每次结果 | 按任务目录找，不建议逐个 raw 文件浏览 |
| `virtuoso/exports/`、`virtuoso/snapshots/` | 下载的导出/快照 | 生成证据；不是可本机编辑的远端原理图 |
| `artifacts/` | GDS/CDL/PEX/报告的预留下载位置 | 目录存在不代表版图/签核已经完成 |

项目数值分析一般使用 `.venv/Scripts/python.exe`；bridge/OA 操作使用
`E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe`。
脚本中的旧环境命令属于当时记录，不能据其推断两套环境依赖完全一致。

### 仿真结果目录

主要看 `output/eight_bit_flat/`、`output/cdac8_device/`、
`output/strongarm8_baseline/`、`output/sar8_async_impl/`。
候选看 `output/cdac8_reset/` 和 `output/cdac8_dualrail/`。
旧 `bootstrap_*`、`strongarm_t28_*`、`electrical_macro_model*` 等保留为历史证据。
全部结果根目录见 [output_roots.csv](inventory/2026-10-20/output_roots.csv)。

这些目录里可能同时有成功、失败、被中断的仿真；应以绑定版本的报告、
case/hash 和 `result.ok` 为准，不能只按修改时间挑一份 PSF 称为“最新通过”。

### 历史资料从哪里追溯

| 历史线 | 原理图或本地入口 | 与现在的关系 |
| --- | --- | --- |
| 10-bit 理想/噪声模型 | `sar_adc_ideal_10b.va`、`docs/error_budget.md`、`output/behavioral_baseline/` | 原指标推导来源，不是 8-bit 当前电路 |
| 10-bit 5+5 宏模型 | `sar_cdac_macro_10b`、`tb_sar_macro_transient`；[宏模型报告](electrical_macro_model.md) | 历史可运行宏模型，无需重复按旧流程从头设计 |
| 第一版 core Bootstrap | `sar_bootstrap`、`tb_sar_bootstrap_transient`；[初版设计](bootstrap_driver_design.md) | 早期管级探索，有保持误差/应力问题 |
| 底板/钳位实验 | `sar_cdac_bottom_plate_*`、`tb_sar_bottom_plate_*`；[底板实验](bootstrap_bottom_plate_eval.md) | 历史对照，当前已回到顶板采样 |
| GMAIN 隔离、延迟复位、关断电荷 | [历史采样状态](sampling_architecture_status.md)、[全 CDAC 隔离](bootstrap_full_cdac_isolation.md)、`output/bootstrap_*` | 多项是网表级快速实验，不能假定每个实验名都有同名 OA cell |
| Canvas 原拓扑 0.5-µm 版本 | `sar_bootstrap_canvas_t28`、`sar_bootstrap_canvas_cdac_t28`；[原生映射报告](canvas_bootstrap_t28.md) | 用户原拓扑的 T28 实现/去独立 Cs 的副本；不是当前 1-µm flat 负载版本 |
| 8-bit 同步逻辑提案 | [同步逻辑旧提案](sar8_logic.md)、`netlist/dut/sar_logic_8b_canvas.cir` | Canvas/布尔级验证，被异步架构替代，不是当前原生控制器 |

Analog Canvas 和 `review/` 是审核入口，不是 T28 OA/PDK 仿真源文件。画布的
默认器件或理想门不等于实际 Virtuoso 电路；按对应报告核对映射和模型层次。

## 6 实际清单与命名陷阱

本次读回 **170 个实际 cell、159 个 schematic、114 个 symbol、11 个 veriloga**。
当前清点没有 layout 或 maestro view；很多仿真是 OA 导出后由 Spectre 脚本执行，
不应因此期待每个 cell 都有 ADE/Maestro 设置。

原登记表 143 条中有 15 条没有对应远端 cell；实际库有 42 个 cell 尚未登记。
这是登记差异，不等同于丢失设计。可查：

- [逐项实际 cell/view 清单](inventory/2026-10-20/virtuoso_cells.md)
- [带登记用途、状态与远端路径的 CSV](inventory/2026-10-20/virtuoso_cells.csv)
- [全部登记差异和清点时间](inventory/2026-10-20/snapshot.json)

尤其注意：

- `sar_adc_top`、`sar_clock_gen`、`sar_ref_buffer` 等仍是登记计划，远端不存在。
- 实际比较器名是 `sar_strongarm_t28`；不要打开计划名 `sar_comp_strongarm`。
- `sar_strongarm_t28_f2/f4` 是保留候选，不是当前比较器已自动升级的证明。
- `nominal` 表示确定性聚合电容加速版；不是“已经合格”的意思。
- `eval`、`diag`、`safephase`、`reset`、`dr` 经常是独立实验，不代表已选方案。
- `10b`/`5+5` 旧资料和当前 8-bit 的 LSB、噪声门限、阵列负载不能混用。
- `cdac10_dr_*` / `cdac10_dualrail_*` 是新进行中的 10-bit 单调方案实验，
  **不同于历史 10-bit 5+5，也不自动改变当前 `design_spec.yaml` 的 8-bit 默认**。
  其未提交源文件和远端对象在清单中单列；本次没有接管、完成或推广该实验。
- 清点期间还有参考恢复对比、异步两周期观察等并行草稿；CSV 的 `untracked`
  是清点状态，不能当作提交完成或验证通过。

### 清点期间的并行工作

| 工作 | 现场文件入口 | 此次清点的处理 |
| --- | --- | --- |
| 新 10-bit 单调双轨实验 | `config/cdac10_dualrail.yaml`、`scripts/cdac10_dualrail/`、`plan/2026-10-20-cdac10-dualrail/` | 已有远端独立 cell，源文件未提交；单列进行中，不归入旧 5+5 或当前 8-bit 基线 |
| 8-bit 参考恢复 A/B | `scripts/cdac8_dualrail/compare_restore.py`、`plan/2026-10-20-cdac8-restore-comparison/` | 独立对比；提交状态见快照，不据此自动推广候选 |
| 异步两周期关键节点图 | `scripts/sar8_async/two_cycles.py`、`docs/sar8_async_two_cycles.md` | 独立观测工作，仍是控制器＋理想 plant，不冒充真实 CDAC 联测 |

## 7 接下来沿哪条线继续

在不继续展开 PVT/失配优化的前提下，下一集成目标是：把保留的真实采样、
CDAC、StrongARM 接到 `sar_logic_8b_async`，完成标称条件的完整逐位转换。
应先明确采用哪一个参考切换候选及其 SEL/BASE 合同，不能把同步 VA 控制器
直接当作已验证的异步接口。

本次只建立导航与事实清单，没有选择新的 CDAC 算法、创建新的整机顶层、
修改现有电路或清理历史版本。后续需要归档/改名/Library Manager 分类时，
应另列方案后执行，避免破坏脚本引用和可复现实验。
