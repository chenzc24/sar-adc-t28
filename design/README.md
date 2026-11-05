# 电路

顶层为 [top/adc_top.scs](top/adc_top.scs)，master `sar_adc8_join_r4`。完整 include 入口为 [dut.scs](dut.scs)。端口、子电路归属和原始来源见 [manifest.json](manifest.json)。

| 模块 | 实现 |
| --- | --- |
| Bootstrap 采样 | [xtor/bootstrap/bootstrap.scs](xtor/bootstrap/bootstrap.scs) |
| 18 个 MOM 与分位参考开关 | [xtor/cdac/cdac.scs](xtor/cdac/cdac.scs) |
| 11 MOS StrongARM | [xtor/comparator/comparator.scs](xtor/comparator/comparator.scs) |
| 异步 SAR | [xtor/sar/sar.scs](xtor/sar/sar.scs) |
| 参考、非交叠与空闲控制 | [xtor/reference/reference.scs](xtor/reference/reference.scs) |
| RC 与握手延时 | [xtor/clock/delays.scs](xtor/clock/delays.scs) |
| 原生标准单元包装 | [xtor/common/standard_cells.scs](xtor/common/standard_cells.scs) |

[frozen/b/dut.scs](frozen/b/dut.scs) 是历史实测的字节级输入，供原案例复现。分模块视图保留其全部 49 个子电路；46 个从顶层可达，3 个辅助定义保留。既有结果的来源散列保持原值。

PDK 和原生标准库保存在服务器；各测试 deck 显式引用模型 section。

[RNL 原理图](../docs/schematics/README.md) 覆盖顶层、六个模块及其全部本地管级层次。绘图记录直接保存在上表源网表的 `// @RNL` 注释中，共用符号位于 [rnl/sar8.rnl](rnl/sar8.rnl)。官方查看器支持逐层进入、缩放、源网表和 SVG 导出；[离线页](../docs/schematics/index.html) 也可直接打开。展示入口和来源散列见 [rnl/manifest.json](rnl/manifest.json)。注释不改变 Spectre 电路，也不代表 OA 已同步。管级候选约定见 [xtor/README.md](xtor/README.md)。

与当前 B 接口和总规格对齐的 [VA/Python 行为视图](behav/README.md) 用于算法、误差参数和协议交叉验证。现有晶体管测量继续绑定原物理输入，行为视图的结论独立记录。
