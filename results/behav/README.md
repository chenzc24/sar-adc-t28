# B 版行为模型验证

模型按功能拆分；Python 与电气 VA 的适用层次分别记录。本页 `sar8-modules-v3` 证据属于上一轮选择配置，保留其原始来源。本轮逐模块选择、RC/clear 非对称模型及独立测试见 [模块结果](../blocks/README.md)。

- [数值回归](modules_python.json)：16,400 条既有确定性记录，码字、计数、事件时间保持一致。
- [原生模块与混合测试](modules_native.json)、[来源回执](modules_provenance.json)、[运行状态](modules_status.json)、[原始告警](modules_warnings.txt)。
- [模型审查](model_audit.json)：历史去向、当前源码与哈希。

原生运行 `sar8-modules-v3` 的仿真和分析均完成，失败数为 0，共 42 次独立输出引脚读取。

| 视图 | 测试结果 |
| --- | --- |
| `current` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `behavioral` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `comparator_xtor` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `cdac_xtor` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `sampler_xtor` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `control_xtor` | 首帧及低/中/高码匹配，8 次比较及参考更新 |
| `stuck` | 强制不响应被识别，未误报完成 |

采样器的跟踪/保持、带 10 mV 偏移的比较器正负输入及复位检查通过；核心全行为视图的 8 位参考门控波形未观察到 NMOS/PMOS 同开。
实际警告代码：`CMI-2751`、`CMI-2752`、`CMI-2753`、`CMI-2754`、`CMI-2755`、`SFE-1131`、`SFE-2453`、`SPECTRE-16780`、`SPECTRE-16881`、`VACOMP-2435`。原始日志在运行回执的回收目录及服务器保存，端压/数值告警不等于已经通过可靠性或模拟精度验收。

[首轮测量失败](modules_initial_failure.json)：实例大小写导致内部信号漏存，另一个比较器探针处于复位相位；该次未计为验收通过。
[第二轮资源失败](modules_resource_failure.json)：完整波形超出 768 MiB 磁盘预算；随后去掉未用于分析的数字输出保存项，磁盘预算改为 1536 MiB，RSS 上限仍为 1024 MiB。

本测试仅验证 TT 功能、模块接口和事件。VA 的电容、输入/驱动及延时参数尚非完整物理等效提取；Bootstrap 启动、栅电荷、PVT/原生失配、端压、功耗及 PEX 使用 current 管级视图。

历史整机宏模型的 [16,400 帧原生交叉](native_crosscheck.json) 属于上一次源码版本，见 [旧来源](native_provenance.json)，不冒充当前电气模块的波形精度。
数值模型对 B 的 256 个实测中心码及十帧 TT 码字一致；TT 近似时间最大差约 0.13 ns。理想源采样量化与 B 高频码字仍有最多 3 LSB 差异，见 [数值范围](python_crosscheck.json)。
