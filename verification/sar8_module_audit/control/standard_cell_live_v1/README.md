# X001 LIVE级标准单元替换包

**主会话已完成原生仿真、分析及回收；过压仍未闭合。**
run ID：`sar8audit-ctrl-stdcell-live-ff-v1`，managed hash：
`a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226`。
精简对照见[一张表、一张波形与下一项建议](results/README.md)；22份冻结输入保持不变。

## 变更清单

- 源为已完成的**MN1＋R0版**，`sar8audit-ctrl-stdcell-r0-ff-v1`，managed hash
  `f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a`。
- 仅将`X001`整级AND改为原样foundry `ND2D1BWP12T30P140 + INVD1BWP12T30P140`。
  外部仍为`LIVE = SN & ACTIVE`；SN→A1、ACTIVE→A2，NAND输出N→INV输入，INV输出→LIVE。
  包装端口仍为`A B VDD VSS Y`。SN保留输出相邻上管的输入位置。
- 旧级6只MOS及`X001.X000.CMID`随整级实现退出，**不是单管因果实验**。
  CMID原为`cfmom_2t nr=8 lr=2.5u w=50n s=50n stm=1 spm=3 multi=2 mismatchflag=1`。
  旧MID节点退出，新库内部节点为`X001.X000.net10`，未将旧电容移接到库内部。
- 其余123个叶器件/源不变，包括X020标准门、原生串R0和实际RC/SR负载。
  共用INV定义未改；11份PWL、非save仿真deck、外部采样窗口/关闭沿和求解设置逐字节相同。
  原foundry SPICE只读include，不复制正文或修改尺寸。

## 测量清单

- 101MOS/17无源；**62V、436I、61节点KCL、606物理端压对＋3旧别名**，0.99V门限不变。
  新LIVE库管6只、原X020库管6只、其他核心89只分别报告。
- 十二库MOS实际`:1..4`共48个端流请求，按已验证库实例名映射。
  新层级仍须在首次原生运行确认；必需轨迹缺失即失败，不补零或自动猜名。
- 分别测SN、ACTIVE的本级栅端加载、级内N的加载：峰值、带符号事件净电荷/端功、
  原生边沿和KCL；同时保存LIVE、X020.N、Q1、QUIET及后续时钟路径。
  旧版对应负载已按相同端口语义只读归约，见[source_load_reference.json](source_load_reference.json)。
- 原五路源净供能、另七路**已存在**的理想PWL边界功、R0吸收能量分别记账；
  没有新增电源。源R0旧报告仅汇总五路完整历史功，额外七路旧全历史值不补零推测。
  所有交换量限于条件首事件台，不作整周期ADC功耗。
- 历史重现误差字段仅作诊断，不是本方案验收门禁；不声明完整建立、复位、PVT或整机合格。

## 配方与身份

[recipe.suggested.yaml](recipe.suggested.yaml)：FF/0.99V/−40°C，原Spectre X CX设置；
1线程、仿真RSS1GiB/900s、分析256MiB/600s，原生输出1GiB、派生二进制30MiB/回收32MiB。
截止点保持41.5907856506ns，无噪声、失配或PEX。

22份声明输入共**4,626,037B**；配方文件SHA：
`fba7d02e16245a7cf52ff058f6cd716dd4df77f2425e265b199615619cf28870`。
逐项哈希及明确移除清单见[freeze.json](freeze.json)、[change_manifest.json](change_manifest.json)。

[test_standard_cell_live.py](../test_standard_cell_live.py)的一次最小验证已通过：
精确整级边界/供电与输入映射、其余叶器件一致、MID退出/新节点端流覆盖、源PWL/deck一致、
原生负载积分与缺项硬失败、五源/七边界/R0能量分账。合成数据只验证测量代码。
生成器：[prepare_standard_cell_live.py](../prepare_standard_cell_live.py)；
分析器：[standard_cell_live_analyze.py](../standard_cell_live_analyze.py)。
