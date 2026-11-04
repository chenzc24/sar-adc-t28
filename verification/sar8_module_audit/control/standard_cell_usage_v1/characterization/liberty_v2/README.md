# v2：精确成员头读取修复包

**本地准备完成，未启动远端读取。** v1真实失败为成员头身份检查不符；正文语义读取
计数为0。旧回执没有保存实际名称／大小／类型，因此GNU／PAX覆盖仍是待验证假设。
旧冻结输入、失败结果和已完成索引全部保留。

## 已知证据与新读取范围

完整索引中，目标前一个正常成员是相邻的FF `.db`。其正文填充结束为
13,230,656,512 B，目标header为13,230,657,536 B，间隔恰好1024 B。
这段内容尚未在本会话远端读取，不能据此直接断言扩展类型。

新配方绑定同一真实baseline、完整index及目标成员，并校验index中紧邻前一成员。
按已知偏移顺序跳过前缀，仅解析这段有界间隔，然后读取目标512 B header。
不保留前一db的正文尾部，不重新扫描归档目录。间隔上限128KiB，单个扩展payload≤64KiB；
全部读取和跳过仍≤64KiB块。

支持间隔内GNU长名／长链接和PAX path／size／linkpath，使用与既有索引相同的覆盖顺序。
更早的全局PAX状态没有被读取；无法由本间隔和原始header恢复并匹配的字段明确拒绝，
不从索引期望值补造实际值，也不退化为只比较basename。

## 每个字段先记录，再决定是否进入正文

`header_evidence.json`记录原始字段、header／payload SHA、扩展识别字段、恢复来源及下列
expected／observed／match：完整名称、有效大小、类型、header偏移、body偏移和链接名。
保留原始header checksum检查；名称等任何必需字段不符都停止。
此处正文计数指Member语义读取量，解码器的小块预取不会保存为库正文。

命中头检查后，后续原语义代码、模板与阈值继承、原生参考和完整archive SHA／CRC校验
全部冻结复用。差异见[wrapper变更](reader_delta.diff)；新逻辑集中在[header读取器](header_reader.py)。

## 测试与执行边界

一个focused合成测试通过：GNU长名、PAX path／size覆盖；无扩展时名称不符拒绝；
错误大小／类型／偏移与损坏校验和拒绝，且全部字段证据保留、尚未读取成员正文。
这不是实际归档根因确认，真实字段须由下一次managed结果回答。

[新配方](recipe.suggested.yaml)仍为source-bound `analysis_only`：
`sar8audit-ctrl-ff-liberty-semantics-v2`。沿用1线程／256MiB／900s／4MiB总输出及32MiB回收，
无新仿真。主聊天统一admit执行，本会话未读取远端或改动PDK／库。

[原失败证明](v1_failure_reference.json) · [来源与前一成员绑定](source_binding.json) ·
[限额](semantic_config.json) · [focused测试](test_reader.py)
