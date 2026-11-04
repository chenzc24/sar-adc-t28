# 原LIVE下拉NM并联数1→2：单变量包

**主会话已完成q2仿真与回收，结果对照已整理；过压仍未闭合。**
原`sar8audit-ctrl-stdcell-r0-mn2-ff-v1`因内存余量等待超时被拒绝，未启动Spectre，记录保留。
实际结果为`sar8audit-ctrl-stdcell-r0-mn2-ff-q2`，managed hash：
`3b0e98474b6d0dc6e6a11484382c79e06d762e3a4d070c8134536097cedff31c`。
两次21份声明输入完全相同，原[recipe.suggested.yaml](recipe.suggested.yaml)及冻结输入保持不变。
详见[结果、三张图与原因分析](results/README.md)。源对照为已完成的R0案例，managed hash：
`f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a`。

## 电路只改一个参数

目标：`XDUT.XCTRL.XTIM.X001.X001.MN`，模型`nch_mac`。

| 参数 | 源R0案例 | 本候选 |
| --- | --- | --- |
| multi | 1 | **2** |
| 每单元W/L/nf | 500nm / 30nm / 1 | 相同 |
| 每单元扩散、寄生及其他实例参数 | 原参数 | 相同 |
| D/G/S/B | LIVE / X001.N / VSS / VSS | 相同 |

只沿目标层级生成四个私有祖先子电路，绝对实例/节点路径保持。
共用`sar8p_inv`原定义逐字节不变；没有把所有反相器一起加倍。
展平后仅该MN的multi不同，其余129个叶器件/源相同，无新增或删除叶器件。
PM、原生串R0、标准库、Q1与其他负载均保持。整个`test.scs`、11份PWL和外部库身份逐字节不变。
仍为101个MOS实例、18个无源；目标并联单元数变化由模型处理。

## X001.N负载怎么量化

新跑完整保留62V、437I、61节点KCL及606物理端压对＋3旧别名；0.99V门限不变。
无需新增理想驱动或拟合输入电容。

- 分别记录目标NM与原PM的原生栅端电流峰值、合计峰值和带符号积分。
  直接使用返回的总端流，**不再人工乘2**，也不预设新电流/负载恰为旧值两倍。
- 记录X001.N的全历史极值、原生10/50/90%沿、90–10%下降时间和完整支路KCL。
  将新增输入负载和LIVE输出保持一起比较。
- 在请求41.075ns至原截止点的原生样点上，分别计算两栅端净电荷交换与`∫V(X001.N)Igate dt`。
  输出实际首尾样点；不补造端点，不把端功叫成耗散功耗或把总栅流叫成纯Cgd。

已用同一归约函数对**源案例multi=1**作只读本地参考，见
[source_input_loading_reference.json](source_input_loading_reference.json)：

| 源R0案例中的参考量 | 实测 |
| --- | ---: |
| X001.N最大值 | **1.006273V，即高于VDD 16.273mV** |
| X001.N下降90–10% | 7.681ps |
| 目标NM栅端最负电流 | −73.892µA |
| 原PM栅端最负电流 | −156.914µA |
| 两栅端合计最负电流 | −214.104µA |
| 目标NM栅端净交换 | −0.39758fC |
| 原PM栅端净交换 | −0.84415fC |

电流正向为从X001.N进入MOS栅端；负号表示返回该节点。
上述电荷积分的实际区间为41.0750036–41.5907857ns。
这些是旧案例参考，**不是multi=2的新仿真结果**。

## 检验目的与判断边界

测试低电平恢复能力增强后，LIVE负向偏移能否缩小，同时保留过滤后A1/N的收益。
并联也会增加输入寄生，需同时观察X001.N、LIVE/A1/N/Q1/QUIET：
目标NM的输入VGS/VGB、原PM的输出VDS及上游NAND端压都在原屏幕中。
不能只压低LIVE而将应力移到X001.N，或只看峰值而忽略更宽的超限段。

标准门6MOS、改动NM1MOS、其他核心94MOS分组报告，合计仍为101MOS/606物理端压对。
保留全部CMI、原生边沿、末值和未观测状态，不预判建立完成。
五路源0..END净供能与R0吸收能量继续分账；输入栅端功只作局部交换量，不重复加作整机功耗。

## 本地验证与交付

[prepare_standard_cell_r0_mn2.py](../prepare_standard_cell_r0_mn2.py)生成，
[standard_cell_r0_mn2_analyze.py](../standard_cell_r0_mn2_analyze.py)调用三个冻结观察器。
[test_standard_cell_r0_mn2.py](../test_standard_cell_r0_mn2.py)的一个focused test已通过：
精确一实例multi变化/共享INV保护、端口及全部目录一致、原生总栅流不重复乘2、
带符号电荷/端功与KCL、原R0/五源能量分账，以及缺失目标栅流硬失败。
合成波形仅验证测量代码，不代表电路结果。

21份声明输入共4,615,577B；配方文件SHA：
`dc8aa9568234f6fda7d21f86333552ae8ad2257a541a038666f098a3b10dbcf9`。
完整变更及哈希见[change_manifest.json](change_manifest.json)、[freeze.json](freeze.json)。
建议资源沿用1线程、仿真1GiB/900s、分析256MiB/600s，原生输出1GiB、派生二进制30MiB/回收32MiB。
保持FF/0.99V/−40°C、原模型section/容差和采样窗口/关闭沿，不进行串阻扫描或其他门替换。
本包仅为首事件机制验证；q2已有新原生结果，未声明完整复位、PVT、寿命或ADC合格。
