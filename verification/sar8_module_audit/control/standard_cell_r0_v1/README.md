# 标准NAND整个A1输入串R0：单变量包

**本地已冻结、focused test通过，未注册或提交远端。** 建议run ID：
`sar8audit-ctrl-stdcell-r0-ff-v1`，使用[recipe.suggested.yaml](recipe.suggested.yaml)。
源对照是已完成的`stdcell-ff-v1`，managed hash
`593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20`。

## 唯一改动

原版：实际LIVE驱动 → 标准NAND A1。

本例：实际LIVE驱动 → **X020.RINPUT** → **X020.A1_FILTER** → 标准NAND A1。

RINPUT使用原电路`XD_QUIET_D.R0`的原生PDK器件与完整参数：
`rupolym l=17.13u w=1u m=1 multi=(1)`。未用理想电阻代替。
A1的NMOS `X000.MM4`与PMOS `X000.MM1`两只栅端一起接到新节点；
库内部连线、尺寸、原M调用、Q1/A2、INV和上游驱动均保持。
其余127个叶器件/源不变，仅增加一只电阻，没有删除器件。
11份PWL及非save的仿真deck逐字节一致，外部采样窗口/关闭沿、模型section和求解设置不变。

## R0阻值证据

在源案例FF、0.99V、−40°C，原`R0`的41.4ns以后原生样点中：

| 项目 | 实测 |
| --- | ---: |
| 端压差/端流 | **9.791809–9.792118kΩ** |
| 压差范围 | 0.687801–0.775217V |
| 端1电流范围 | 70.2425–79.1674µA |
| 两端电流和的最大绝对值 | 3.58×10⁻¹⁸A |

截止时原生样点为41.5907856506ns：两端0.954542/0.266741V，电流±70.2425µA，
V/I=9791.8091Ω。原生`tt_res_bip_dio_disres`模型section和PDK scalefactor=0.9保持。
这是原R0在该工况/偏置下的V/I，**不是新串阻在快边沿下已经测出的固定阻值**。
完整来源、实际首尾样点和两端验证见[change_manifest.json](change_manifest.json)。

## 测量与解释

- 保存LIVE与A1_FILTER、RINPUT两端流，同时观察N/Q1/QUIET、RC/SR和既有所有节点。
- 共62V、437I、61节点KCL；保留全部606个物理端压对及3个旧别名，0.99V门限不变。
  两只A1器件的栅压屏幕跟随真实A1_FILTER节点；入射LIVE及原驱动仍被完整观察。
- 原生10/50/90%边沿分别测两侧，再测已有QUIET/时钟路径；缺失沿记未观测，不记零延迟。
  终值照实报告，未预设“建立完成”。窗口仍只有0–41.5907856506ns首事件。
- 相同0..END上分别报告五路理想源有符号净供能，以及RINPUT吸收能量
  `∫(V₁I₁+V₂I₂)dt`。电阻两端功不混入源能量之和，也不当整周期ADC功耗。
- 新RINPUT的V/I在原生诊断窗内直接测量；仅在|I₁|>1nA时作除法，避免0/0。
  这只是比值测量条件，未改变端压或KCL门限。总端流不拆成虚构Cgd/沟道分量。

RINPUT的`:1/:2`沿用已原生验证的同模型R0端流约定；新实例仍须由首次managed运行验证。
库六MOS四端流继续原样保存。任一必需轨迹缺失即失败，不自动改名或补零。
若N上冲降低但LIVE、Q1或其他管端应力加大，应报告为应力转移，不能认定修复。

## 复现与限制

[prepare_standard_cell_r0.py](../prepare_standard_cell_r0.py)生成包，
[standard_cell_r0_analyze.py](../standard_cell_r0_analyze.py)调用冻结观察器做原生流式分析。
建议资源保持1线程、仿真RSS1GiB/900s、分析256MiB/600s、原生输出1GiB，
派生二进制30MiB/回收32MiB；不增加并发或截短观测来凑通过。

[test_standard_cell_r0.py](../test_standard_cell_r0.py)的一个focused test已通过：
精确单R/双栅连接、源输入/11PWL一致、屏幕/KCL目录、合成两侧slew/延迟与V/I、
电阻吸收功及五路源功分账、缺失R端流硬失败。合成10kΩ数据只验证测量代码，不是电路结果。

20份声明输入共4,600,831B；配方文件SHA：
`7112adc127e913320ba1bcb284e0ac03a0b8e9f31ac241ec2d7576bce3dbfad1`。
逐项哈希见[freeze.json](freeze.json)。
这是耦合/边沿机制对照，不扩大其他门替换或扫描；不声明完整复位、PVT、寿命或整机合格。
