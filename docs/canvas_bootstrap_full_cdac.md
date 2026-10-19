# Canvas 0.5 µm Bootstrap 接入完整 CDAC 的对比

日期：2026-10-19。结论：新方案在这次五点 TT 采样/保持测试中，最坏原始
差分保持误差为 **0.393871 mV**，原未隔离 Bootstrap 为 **1.535561 mV**，
降低 **74.35%**。新方案五点均在 ±0.439 mV 预算内，但最坏余量仅
45.13 µV；这不是 PVT、噪声、失配或完整 ADC 签核结论。

## 1. 比较对象与电路落地

| 项目 | 原方案 | 新方案 |
| --- | --- | --- |
| Bootstrap | 现有 `sar_bootstrap`，未隔离原型 | 用户 Canvas 拓扑，原生 T28 1.8-V 管 |
| 主开关 | MN11：W=250 nm、L=60 nm、multi=8 | Mmain：W=0.5 µm、L=150 nm、nf=multi=1 |
| 其余器件 | 原有核心管和电荷泵，不修改 | 其余 11 个 MOS 均 W=1 µm、L=150 nm |
| 自举电容 | CBOOT=200 fF，CP1=CP2=50 fF | Cboot=1 pF |
| 反相/复位 | 原有外部 PHIB 非重叠时序 | 原生两管反相器自行产生 CLKSB |
| 负载 | 完整差分 `sar_cdac_macro_10b` | 同一 cell 的独立副本，无额外 1-pF Cs |

新建 OA 对象，均在 `SAR_ADC_T28`：

- `sar_bootstrap_canvas_cdac_t28/{schematic,symbol}`：从已经选定的原生
  `sar_bootstrap_canvas_t28` 通过 OA API 复制，只删除单电容实验的 Cs
  及其悬空接地尾线。12 个 MOS、CDF 派生参数、自举电容和其余走线不变。
- `tb_bootstrap_canvas_full_cdac/schematic`：上下两路各一套完整差分 CDAC，
  各由 P/N 两个对应 Bootstrap 驱动。两路有独立输入源和 50 Ω 电阻，
  不会通过共享输入电阻互相干扰。

新反相器两个观察端各有 1 TΩ 监测终端，消除未终接输出的检查标记；
没有增加电容负载，也没有使用理想开关代替新 Bootstrap 内部 MOS。
两个新 schematic 的 Check & Save 标记均为零。

原 `sar_bootstrap`、单电容测试 cell、`sar_cdac_macro_10b` 及 PDK 不修改。
逐子电路比较确认：新 DUT 与原导出网表仅有名称/Cs 的预期差异，旧 DUT
及 CDAC 与历史导出完全相同。主比较的五个仿真均来自新测试台实际 OA
导出，仅设置输入设计变量、数值精度、保存项和 transient 分析。

这不是“只改 W 的同一电路”实验：器件耐压类别、拓扑、自举电容和内部
复位驱动均不同。因此不能将 74.35% 改善全部归因于 W=0.5 µm。

## 2. 统一条件及指标定义

- Spectre 21.1.0.509，基础 Spectre 模式，`t28_io`，TT，27 °C。
- Foundry 模型采用项目既有 embedded-usage include，sections：
  `pre_simu`、`noise_worst`、`ttmacro_mos_moscap`、`tt_res_bip_dio_disres`、
  `tt_mom`、`tt_ind_jvar`、`tt_r_metal`。`noise_worst` section 的存在不代表
  transient 已注入噪声；本次未启用 transient noise。
- VDD=0.9 V，VCM=0.45 V；VinP/N=VCM±Vdiff/2。
- Vdiff = −0.8、−0.4、0、+0.4、+0.8 V；205 ns 输入翻转，输入源每边 50 Ω。
- 10 MHz，PHI 在 211 ns 开始上升，250.1 ns 开始下降；100 ps 上/下沿。
- CDAC：差分 5+5 split，Cu=6.86047 fF，Cbridge=7.08177548 fF；
  每侧 MSB=31Cu，LSB 含 dummy=32Cu。底板/LSB 复位和参考选择仍是原有
  理想 relay 宏模型，不是已完成管级 CDAC。
- BASE、SEL0、SEL1、CLK_SAMPLE 和所有 reference 连接完全相同。
  VREFP/N 在此采样夹具均接 VCM；不执行逐位 SAR 转换，不连接比较器。
- 285 ns transient，maxstep=10 ps，reltol=1e-5，vabstol=1e-7 V，
  iabstol=1e-13 A，conservative。

定义：

`E(t) = [(TOPP(t) − TOPN(t)) − Vdiff_target] × 1000 mV/V`。

获取误差在 249.9 ns 测量；最终保持误差在 270 ns 测量。
全部为未经拟合、去增益、去 offset 或校准的原始电压误差。
零差分输入接近零是对称、无失配条件的结果，不是已验证零 offset。

主比较保留各方案原来的内部控制：旧 PHIB 的 50% 上升交越为 251.150 ns，
新 CLKSB 为约 250.2066 ns。这是明确的驱动差别，不称为相同内部时钟。
另做交越对齐的控制实验，见下节。

## 3. 五点结果

| Vdiff (V) | 原方案 Ehold (mV) | 新方案 Ehold (mV) | 新方案 ±0.439 mV |
| --- | --- | --- | --- |
| −0.8 | +1.535561 | +0.393871 | 通过 |
| −0.4 | +0.679080 | +0.203590 | 通过 |
| 0 | ≈0 | ≈0 | 通过，仅对称名义条件 |
| +0.4 | −0.679080 | −0.203590 | 通过 |
| +0.8 | −1.535561 | −0.393871 | 通过 |

原方案复现了历史约 −1.532023 mV 的结果，差约 3.54 µV（0.23%）；
这里是重新跑出的更严精度、只含顶板支路的数值，不直接挪用历史结果。
两套旧 DUT/CDAC 定义已确认与历史一致。

新方案在 +0.8 V 下 TOPP/TOPN 单端误差分别 −0.850361/−0.456490 mV，
两者相减才是 −0.393871 mV；保持共模约 0.4493466 V。不能把差分通过
误读为每一侧的单端误差都小于 0.439 mV。

新方案获取误差最大约 1.79 nV（此确定性 DC 平台的数值结果，不代表实际
电路能达到 nV 采样精度）。±0.8 V 输入跳变后约 218.96 ns 起留在
±0.439 mV 获取误差带内，距离最终关断还有约 31 ns。

## 4. 时序和保持区间

以 Vdiff=+0.8 V 为例：

| 事件 / 区间 | 时刻 (ns) | 如何理解 |
| --- | --- | --- |
| 获取检查 | 249.900 | 两组均已获取到目标 |
| PHI 下降 50% | 250.150 | 进入关断/底板浮置交接，不是最终保持读数 |
| 新 CLKSB 上升 50% | 250.2066 | 新反相器触发自举复位 |
| 旧 PHIB 上升 50% | 251.150 | 原方案的延迟复位 |
| BASE 上升 50% | 252.050 | CDAC 底板参考重新接通 |
| 参考交接基本建立 | 约 252.5–253 | 稳定保持误差可以比较 |
| 最终读数 | 270.000 | 新 −0.393871 mV，旧 −1.535561 mV |

250.15–252.5 ns 图中灰色区域是关断和参考交接，252.5 ns 后绿色区域
是已建立保持区。PHI 关断后到 BASE 接通前，底板和 split 内部节点的
状态会使 TOP 差分出现较大暂态：新方案在 252.0 ns 约偏 −355.25 mV，
BASE 接通后恢复到约 −0.394 mV。这个浮置阶段的电压偏移不能直接
当作最终丢失的采样电荷，也不能说 BASE 把所有残余误差都消除了。

260–280 ns 的差分漂移：原方案约 −0.992 µV，新方案在本模型下约
−0.000129 µV。后者的极小值只表示此无噪声、理想 CDAC 宏负载、名义
模型中的漏电漂移很小，不能外推为真实长时间保持性能。

结果图位于 `output/canvas_full_cdac/`：

- `held_error_comparison.png`：五点最终误差、零误差基准、±0.439 mV 带。
- `turnoff_timing.png`：控制、完整差分电压、mV 误差放大。mV 面板的超量程
  部分留空，完整暂态在上方电压面板；不把剪裁后的线当作真实电压。
- `hold_timing.png`：252.5–280 ns 稳定保持区，270 ns 标出实际读数。

## 5. 交叉验证与告警

1. ±0.8 V 将 maxstep 收紧至 5 ps、reltol 至 2e-6：旧方案最坏
   1.535665 mV，新方案 0.393902 mV；相对主比较变化分别约
   0.104 µV 和 0.032 µV，均小于 1 µV 验证限。
2. ±0.8 V 单独保留新支路再跑，避免旧方案告警的全局抑制掩盖新方案：
   新保持误差为 ±0.393877 mV，与主比较相差约 0.0063 µV。
   两次均零 CMI、零 suppressed warnings，保留四条模型 SFE-1131。
   这是删除旧顶层支路的明确派生诊断网表，不冒充原样完整 OA 比较网表。
3. 原方案的比较日志仍有核心管 SOA 过压告警（例如模型 0.99-V 限值）；
   +0.8 V 主运行打印 30 条 CMI，205705 条被抑制。精度通过不能使旧
   电路成为可靠性合格设计。
4. 新方案保存节点重建的 MOS 六种端间绝对电压峰值约 1.75435 V。
   这与名义 1.8-V 器件方向一致，但采样峰值/未报警均不等于 foundry
   寿命签核；仍需 PVT 和专门 SOA 验证。
5. 复位交越对齐的额外控制：把旧 PHIB 上升/下降的 50% 交越对齐新
   CLKSB，保留旧理想源的 100-ps 边沿形状，不声称整条驱动波形相同。
   这组五点结果如下；新方案的改善不是单靠提前约 0.94 ns 复位得到。
   这个实验只改旧 PHIB 源的 delay/width，不改 DUT/CDAC 或新增隔离器件；
   它是明确标识的刺激对照，而不是主比较原样 OA 导出的另一个版本。

| Vdiff (V) | 原方案，复位交越对齐后 (mV) | 新方案 (mV) |
| --- | --- | --- |
| −0.8 | +1.632060 | +0.393861 |
| −0.4 | +0.689412 | +0.203582 |
| 0 | ≈0 | ≈0 |
| +0.4 | −0.689413 | −0.203582 |
| +0.8 | −1.632036 | −0.393859 |

合计完成 14 次 result.ok transient：主比较 5 次、数值精度交叉验证
2 次、独立告警检查 2 次、复位交越对齐控制 5 次。最终重新导出的 OA
网表与主比较所用导出除生成时间外一致，三个只读依赖的前后读回完全相同。

## 6. 当前判断与下一步

此 0.5-µm Canvas 拓扑已值得保留为完整 CDAC 的管级采样开关候选。
它不含之前 GMAIN 隔离实验中的理想 steering/hold relay，但比较对象是
原未隔离方案，不是此前约 0.174-mV 的理想隔离上界或部分管级 TG 方案。

本次不重新调 W/L、Cboot，不改 Cu 或架构去追求过线。当前主要风险是
45-µV 余量偏小，以及依靠对称差分消除了一部分单端误差。下一步应先
对这个完整 CDAC 负载开展 PVT、获取时间/源阻抗/时钟边沿扫描，再决定
是否继续 W/L 和自举电容优化；随后验证失配、噪声及真实 CDAC 参考开关。

复现脚本：

```powershell
# 以下 create 仅用于目标 cell 尚不存在的全新环境；已有 cell 时会拒绝覆盖。
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/characterization/compare_canvas_full_cdac.py create
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/characterization/compare_canvas_full_cdac.py run
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/characterization/compare_canvas_full_cdac.py tight --vdiff -0.8 0.8
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/characterization/compare_canvas_full_cdac.py candidate-only --vdiff -0.8 0.8
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe scripts/characterization/compare_canvas_full_cdac.py matched-reset
.venv/Scripts/python.exe scripts/analysis/analyze_canvas_full_cdac.py
```

证据包括 `oa_netlist/input.scs`、`netlist_equivalence.json`、OA 前后读回、
每个运行的 source/deck SHA-256、独立 PSF 路径和 Spectre 日志，以及
`analysis_summary.json`。PDK 模型、完整网表和原始波形保留在 ignored output，
不提交到 Git。

主比较 OA 导出 SHA-256：
`c2ceea00335a0f7173202809199c9d9fa39c952933e60100daaf49e5d0daf3e5`。
