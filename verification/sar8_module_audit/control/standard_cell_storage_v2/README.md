# 标准存储验证 v2：测量缩减版

**当前状态（2026-10-27）：[双角报告与波形已完成](results/README.md)。两角502个保持阶段均通过，无额外Q沿；FF严格超限7596／11220对，SS为0对。配置仍为980V／89I，冻结输入不改动；尚非整机或完整Miller负载验证。**

下表保留v2初始配方。原SSv2仅queue_timeout、没有仿真；实际SS执行源为[SSv2q1](../standard_cell_storage_fastanalysis_v1/ss_v2q1/source_binding.json)，不重新启动旧SSv2。

[FF配方](ff/recipe.suggested.yaml) · [SS配方](ss/recipe.suggested.yaml) ·
[冻结清单](manifest.json) · [定向测试收据](test_receipt.json)

| 工况 | run ID | recipe文件SHA256 |
| --- | --- | --- |
| FF／0.99V／−40°C | `sar8audit-ctrl-stdfull-storage-ff-v2` | `2b6aff3cf08ad0e052a5311da7acfe38da7f302615e2a8c9b3e23100c7a2c8e4` |
| SS／0.81V／−40°C | `sar8audit-ctrl-stdfull-storage-ss-v2` | `5b01396275e00b895bd7618ab3c4e537e52cb13af089e3bfba3d02172df924d0` |

每组16项输入／2,371,764B；电路、20ns激励、求解设置和资源上限均与v1相同。
v1在约3.11ns触及输出上限，原生仿真未完成，不能据此得出电路功能结论；旧输入和失败数据保留，SSv1不启动。

- **完整保留：**980路电压、11220对同时刻MOS端压、两个SR与24个寄存器的功能观测。
- **选择保存：**89路端流＝7路独立源功＋34路SR支路＋48路RC支路。
- **明确未知：**其余7466路端流未保存；没有完整节点KCL测量，不填零、不宣称全端流或KCL通过。
- **测试边界：**真实第一级扇出／完整RC输入块，后级输出负载截断；不能替代完整Miller负载或ADC闭环验证。

资源仍为1线程、仿真≤1GiB、分析≤256MiB、原始输出≤2GiB、回收≤32MiB。
按v1部分运行的记录数粗估20ns约1.61GiB；阶段活动和步长会影响结果，须以实际完成状态为准。

一项定向测试通过：仅测量delta、未知覆盖标记、缺失必测端流拒绝；冻结输入哈希已核对。
回收后分别审阅稳定保持、额外Q沿／复位重叠、实际引脚延迟及逐器件端压；当前不预填通过结论。
