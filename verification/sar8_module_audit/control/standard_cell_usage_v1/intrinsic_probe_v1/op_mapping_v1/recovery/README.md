# MM65 OP 解析修复：按 Instance 划分，不按 Model 猜归属

**原零字段是解析错误，MM65 实际暴露 98 个 OP 字段。** 新解析器与一个绑定已完成运行的 metadata-only analysis 包已准备；未重新仿真、修改原结果或重读 PSF 波形。

## 实际格式揭示的问题

原程序遇到任意层次路径就重新设置实例归属，端口节点名会把目标块关闭。它还将 Model 行的路径视为实例路径，并丢掉纯数字后缀；相邻实例也引用该模型名，存在错读邻管数据的风险。

本次明确边界为：

| 类型 | 原生文件实际内容 |
| --- | --- |
| Instance 标题 | 第 5002 行：`XDUT.XU19.XFF.MM65 of nch_mac` |
| Model 标识 | 第 5003 行：`XDUT.XU19.XFF.MM65.nch.35`；完整保留，不当实例别名。 |
| OP 范围 | 第 5002–5107 行；98 个唯一字段名。 |
| 端口映射 | primitive=`tmibsimbulk`，D/G/S/B=`net176/mq/net184/0`，与 SPI 相符。 |
| 两个已读字段 | `ids = 850.088 aA`；`id = 323.622 fA`。只记录原名、原值和显式单位。 |

因此，之前从正则结果推断的 `.MM65.nch` **不能作为已确认的展开实例别名**；它来自被截断的 Model 标识。首次格式样本中的前一个电流块也不能归给 MM65；最终核对只使用明确的 Instance 块。

这些静态 OP 值没有绑定 5 ns、5.5 ns 或 5.95 ns，不能用来解释那个保持阶段。TMI 的本征电流定义、反向 VDS 符号与缩放仍未核定，字段可读不等于物理定义已确认。

## 修复和检查

[read_info_v2.py](read_info_v2.py) 只让明确的 Instance 标题开启／关闭 OP 块，Model 与节点名均不能改变归属；不同真实实例保持独立。单位直接按原生输出记录，支持本次实际出现的 aA、fA 等标记，不从字段名补单位。仅保留 ids/id 数值文本，其他字段只回收名称、单位和行号，不返回几何值。

一个针对性检查使用真实格式小块及明确标记的相邻实例哨兵，验证 14 个实际字段、完整 Model 数字后缀、节点路径不关闭作用域，以及四端映射。它不假装已在本地重解析全部 98 个字段单位。证据：[target_scope_v2.json](target_scope_v2.json)、[actual_format_check.json](actual_format_check.json)。

第一次范围查询因手抄的 OP SHA 有误而被拒绝；已改从验证过的证据自动取值，失败回执保留。该失败不是原始文件变化的证据。所有只读查询只涉及两份精确文件，未经过 CIW、扫描目录或创建远端文件。

## 唯一待执行的恢复包

建议 run：`sar8audit-ctrl-mm65-opmap-recovery-v1`。绑定源运行 `sar8audit-ctrl-mm65-opmapping-ff-v1`、managed `d6ea2862…3006a8`，核对源状态、17 项输入、原结果及信息文件身份。新输出只恢复 OP／端口元数据，并引用原有功能／应力摘要；不重新解析完整波形，也不覆盖空字段结果。

最终 recipe SHA：`81beb7387451c2aa3d63c31390059e8213b129711d9c30f33190e648570114f7`。

[建议 recipe](recipe.suggested.yaml) · [freeze](freeze.json) · [manifest](manifest.json) · [source binding](source_binding.json) · [本地验证](validation.json)

原运行仍是 22772 个原生点、348 端对中 256 对失败，hold／Q 模式通过，MM64 最大 VDS 约 1.105789 V。上述结论没有因解析修复而改变。恢复包由主会话 managed 提交，本会话未执行新分析、native、提交或 push。
