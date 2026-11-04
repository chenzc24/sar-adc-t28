# X020标准单元最小对照包

**主会话首跑与分析已完成，本地对照审阅完成，过压仍未闭合。** run ID：
`sar8audit-ctrl-stdcell-ff-v1`；managed recipe hash：
`593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20`。
主会话已再次核对外部foundry文件SHA/大小，以及配方和19份输入身份。
入口为[test.scs](test.scs)，配方为[recipe.suggested.yaml](recipe.suggested.yaml)。
包内全部声明输入、观察器及共享metadata保持冻结；本会话不另行提交。
原生兼容性与回收由主会话完成；结果和三张图见[对照报告](results/README.md)。
N超幅88.642→42.372mV；LIVE下冲25.612→28.512mV；尚未采用为新基线。

| 项目 | 冻结配置 |
| --- | --- |
| 工况 | FF、0.99V、−40°C；Spectre X CX、1线程 |
| 原版对照 | `sar8audit-ctrl-snload-both-v1`；完整源能量可引用已完成的`ctrl-both-stress-v1`重分析 |
| 唯一替换面 | X020整体NAND＋INV→`ND2D1BWP12T30P140`＋`INVD1BWP12T30P140`；LIVE接A1、Q1接A2 |
| 内部实现变化 | 原六MOS与CMID退出；库内六MOS原尺寸/原M前缀，不移接CMID到库内节点 |
| 保留 | 123个其余叶器件/源，含实际Q1/LIVE驱动、四只条件SN负载、RC/清零/SR、11份原生PWL |
| 时间 | 原采样窗口/关闭沿、模型section/容差/scale不变；0–41.5907856506ns，诊断窗40.8ns起 |
| 规模 | 101MOS、17个无源；61V、435I、60节点KCL；606物理端压对＋3个旧电压别名 |
| 资源 | 仿真RSS≤1024MiB/900s，分析≤256MiB/600s；原生输出≤1GiB，派生/回收沿用30/32MiB限制 |

外部SPICE原文件2,452,584B，SHA256：
`b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e`。
路径见[external_library.json](external_library.json)。只读原样include，使用SPICE模式，
随后恢复Spectre模式；没有复制库正文、修改模型或重新设定尺寸/scale。
19份声明输入共4,589,068B；配方文件SHA：
`1ca7c5ffb2b246ce8254f608453836b54c1286b2fd4d6bbefcf087daa3f3e681`。
逐项身份见[freeze.json](freeze.json)和[change_manifest.json](change_manifest.json)。

## 首次原生验证结果

PDK已核实`nch_mac/pch_mac`是inline subckt，端口1/2/3/4对应D/G/S/B。
首跑已验证这两单元的原样SPICE M调用和原生读入；未改foundry前缀或网表内容。

库内真实路径：NAND为`X020.X000.MM4/MM9/MM1/MM2`，INV为
`X020.X001.MM1/MM0`，前缀均为`XDUT.XCTRL.XTIM.`。
按现有mac惯例保存这些实例的`:1..4`端流。metadata已知其内部primitive名称，
没有假定嵌套primitive的原生探针路径，也没有同时保存两套端流而重复计入KCL。
六MOS的24个numeric端流均已原生绑定；实际TRACE名称保存在结果中，未补零或自动改名。

主会话在提交前需只读核对外部文件SHA/大小；分析器运行后再次核对。
[standard_cell_analyze.py](../standard_cell_analyze.py)的`--check-library`可单独核对
managed输入中的`external_library.json`，该操作只证明文件身份，不证明可仿真或无竞争修改。
没有额外的远端作业或绕过managed队列的启动器。

## 回收后比较什么

1. 原生PASS/END、实际模型/容差、所有CMI；六只库管和95只保留MOS分组筛查，均用核心0.99V。
2. Q1/LIVE→N→QUIET和后续资格/时钟路径：原生10/50/90%沿、半轨沿计数、已观测脉宽、末值。
   全保留交叉事件，不预先剔除毛刺；缺失边沿标为未观测，不给零延迟。完整建立是否满足预算仍待评估。
3. 上游反冲与RC0/RC1/AB、R0负载电流、六库管24端流及原生时间戳KCL。
   不将总端流直接命名为纯Cgd或沟道注入。
4. 相同0..END上的VVDD及四个理想偏置源有符号能量，分别报告；不是整周期ADC耗散功率。

旧对照没有新增606对端压的完整汇总，不能直接比较新旧失败数量；旧数据未保存的波形
也不能绘制重建曲线。先比较共同N/LIVE/QUIET指标、可用分支电流和同区间能量。
首事件窗口不足以验证完整比较/跨帧复位，条件扩散偏置重放也不等于完整SN反馈。
本包不产生SS、PVT、寿命或整机通过结论。

本地验证：一个针对性合成数据测试通过，核对精确替换/输入哈希、真实探针目录、
诊断窗之前的同时刻端压峰值、原生能量积分、缺失端流硬失败和外部文件身份失败。
合成数据不作为电路仿真结果。原版、IO V2及冻结观察器均未改动。
