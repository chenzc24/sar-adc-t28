# 预绑定端压统计的 analysis-only

**当前状态（2026-10-27）：两角快速分析均已由父任务完成并回收，[本地双角报告与波形](../standard_cell_storage_v2/results/README.md)已交付。源绑定与冻结输入保持原样，本会话只做本地结果审阅。**

[FF配方](recipe.suggested.yaml) · [FF冻结清单](freeze.json) · [FF源绑定](source_binding.json) · [等值测试收据](test_receipt.json)

- 唯一绑定源：`sar8audit-ctrl-stdfull-storage-ff-v2`，managed SHA `351d0c4ca4e27bd33dccbe0057e92e1f2146e5f4ba2ca5619983749217407596`。
- FF入口只接受真实分析墙钟超时，或父任务核实定向终止后的非零退出终态；running／submitted／complete均拒绝。
- [SSv2q1备用配方](ss_v2q1/recipe.suggested.yaml)另行绑定新源 `sar8audit-ctrl-stdfull-storage-ss-v2q1`，managed SHA `3bd20be455b023474fcf80be74819b95c7fe8c7d0cb6a35db77e76486071a9f8`。
  仅原生成功后启用；缺失分析状态明确记not_started，不先制造旧分析失败。FF绑定仍固定为false，旧SSv2的queue_timeout不能当仿真源。

优化仅预先规范端压节点名、绑定统计字典，移除每点／每端对的重复函数与临时字典构造。
11220对阈值、原生点、窗口、极值／并列时刻、端流、源功及26个功能观察全部保留，不降采样或放宽判断。
同一6点合成PSF覆盖全部980V／89I／11220对及稀疏更新／GROUP别名：新旧统计字段、列描述、二进制波形与gzip逐字节一致。
另有源身份及激活状态定向测试通过；未测真实运行加速比。

运行时核对源配方／注册／native PASS及footer、全部源输入、managed源证明、旧分析终态、原始波形与元数据不变。
完整复制原spectre.out与logStatus到派生目录（各≤1MiB，否则明确失败）；不创建新simulation.state或假raw/PASS。
只读原PSF，输出到独立新analysis-only目录，保留原失败／中止结果。

资源保持1线程、分析≤256MiB／1200s、回收≤32MiB（完整集合30MiB门禁）；新分析目录输出预算128MiB。
FF为8项输入／2,302,047B；SSv2q1为8项／2,301,986B，原生成功尚由父任务确认。
FF冻结清单只记录其单独冻结时状态，不因新增SS绑定而改写。原v1/v2、PDK、OA、共享计划与日志均未改动。
