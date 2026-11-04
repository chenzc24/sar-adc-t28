# 有界托管归档索引：准备完成，尚未运行

运行ID：`sar8audit-ctrl-dependency-ccs-index-v1`。
[配方](recipe.suggested.yaml)为`analysis_only`，绑定真实完成的
`sar8audit-ctrl-usage-baseline-ff-v1`及其canonical SHA
`a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1`。
这是源实验的依赖条件审计，不重跑电路，也不重做波形分析。

## 执行内容

先核对thu-wei／UID596、源注册／全部冻结输入／native PASS／零错误footer及managed
provenance，再核对实际SPICE库和PDK文件SHA。已知库SHA为
`b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e`。
保存这些身份及归档size／mtime／inode，流式读到原来20480字节前缀时核对既有SHA。
索引后再次核对源、依赖和归档身份。

归档固定为原路径的`tcbn28hpcplusbwp12t30p140_180a_ccs.tar.gz`，
共13,657,415,950压缩字节。只记录成员名、大小、类型、链接信息和解压后tar偏移；
偏移不能当作gzip随机访问或自动续扫指令。

解码、读取和跳过正文始终使用≤64KiB块。不会对267MB `.db`执行一次性read、
成员内容分配、解包、复制或加载；支持USTAR、有限PAX及GNU长名元数据。
异常base256数字、拼接gzip或损坏输入明确报告未完成，不静默省略。
只有tar终止和gzip CRC／尾部检查均完成，才报告完整索引及完整压缩SHA。

发现所需FF成员名和相关release元数据名后可以提前停止，明确`archive_index_complete=false`；
名称命中不意味着内容、表征条件或跨版配套已验证。

## 硬限制与部分结果

| 项目 | 限制 |
| --- | --- |
| 并行／RSS／虚拟内存 | 1线程／256MiB／1024MiB |
| 托管时间／内部停止时间 | 1800s／1740s，为保存证据预留时间 |
| 压缩／解压输入 | 精确13,657,415,950B／64GiB |
| 整个运行输出／回收 | 1MiB／沿用32MiB |
| 成员NDJSON／checkpoint／result | 640KiB／48KiB／64KiB |

保留身份记录、`members.ndjson`、`checkpoint.json`及`result.json`。限额触发时写明
`incomplete_bound`和最后观测位置，不自动重复扫描。审计正常结束不等于完整索引：
必须同时检查`index_status`、`archive_index_complete`和`analysis_complete`。
读入损坏返回非零退出并保留部分记录；输出目录非空则拒绝再次启动。

## 已做验证

三项focused合成测试通过：固定块跳过5MiB成员并验证完整SHA／CRC、PAX和链接；
在267MB声明成员正文前提前停止及压缩／解压／时间／输出边界；损坏header、CRC、
截断、前缀变化及tar尾部额外数据被拒绝。测试不读取真实大归档或创建仿真成功记录。

另只读检查了已知`.cshrc.synopsys`小setup文件，候选路径保留到30项上限后停止。
没有在该有限子集中确认`lc_shell/dc_shell`，也未启动工具、输出许可环境或安装软件。
首次查询达到候选数门禁的回执与后续有界部分结果均保留；不能据此判断工具未安装／无许可。

当前只交付[来源绑定](source_binding.json)、[限额配置](index_config.json)、解析器、配方
和测试。主聊天审核后统一managed执行。本包不解码`.db`时序、不宣称库／PDK兼容，
不修改原始失败结果、冻结输入、共享计划／日志或OA。
