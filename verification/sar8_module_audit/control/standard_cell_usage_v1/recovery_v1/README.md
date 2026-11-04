# DFF诊断导出恢复：只重做分析

**原基线Spectre已成功，失败来自未压缩导出的20MiB上限。** 原失败、部分输出和
完整PSF均保留；本包不重仿真、不改冻结电路／配置／原分析器。

改动仅为新分析任务中的直接流式gzip写入，以及状态／slew读取器的gzip读取。
全原生点、348个同时刻端对、基线73路／对照75路电流、六节点KCL和全部相位检查不变。
写入时同时累计完整解压字节数和SHA，再独立解码验证字节数／SHA及原生行数。
不会先落盘完整未压缩波形。

压缩波形仍硬限制20MiB；全部回收保持32MiB，分析RSS256MiB，单线程／300s。
`max_derived_binary_bytes`在新写入器中限制实际压缩文件字节，不裁剪解压数据。
解压后的逻辑数据量允许超过20MiB，实际压缩文件与总回收上限没有放大。

## 精确源绑定

| 分析配方 | 源仿真 | 激活条件 |
| --- | --- | --- |
| [基线恢复](baseline/recipe.suggested.yaml) | `sar8audit-ctrl-usage-baseline-ff-v1` | 已完成原生PASS；原分析确实失败 |
| [2k对照恢复](rck2k/recipe.suggested.yaml) | `sar8audit-ctrl-usage-rck2k-ff-v1` | 未来真实原生PASS后，可直接分析；当前未由本会话启动 |

源canonical recipe、注册、全部冻结输入、managed provenance、原生日志、源分析状态
均前后核对。运行中／已成功分析被拒绝；对照明确允许分析尚未启动，但不伪造失败。
原日志按原字节复制，PSF只读，输出位于独立managed运行；不删除原derived。

基线managed源SHA：`a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1`。
对照managed源SHA：`997693935954ebbce4f0d4191e0a55ac1e1f391d7502bd5f5005c92c39876b3a`。

## 已做验证与限制

两个focused测试通过：

- 同一合成PSF上，原／新全部统计字段、列定义、解码字节、状态／slew结果逐项一致，
  同时覆盖稀疏更新；分别使用基线73路和对照75路配置。
- 可压缩的200000字节数据完整通过1024字节压缩文件限制；不可压缩对照在64字节
  硬限制前被拒绝。测试数据仅是临时合成测量，不是电路或仿真成功证据。

变更见[写入器diff](reducer.diff)、[状态读取diff](storage_reader.diff)、
[slew读取diff](usage_reader.diff)、[源验证包装diff](source_wrapper.diff)。

原生结果、实际压缩比、耗时／内存和电气结论均待主聊天managed执行与回收确认。
intrinsic电流分解和region仍未知；本恢复不改变任何电路合格结论。
