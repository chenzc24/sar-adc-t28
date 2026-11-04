# 精确FF文本Liberty：语义读取包已准备

**尚未启动远端读取。** 本包为`analysis_only`，源仍是实际完成的
`sar8audit-ctrl-usage-baseline-ff-v1`，另绑定已完成索引
`sar8audit-ctrl-dependency-ccs-index-v1`的注册、输入、输出SHA及完整归档SHA。

精确成员为`TSMCHOME/digital/Front_End/timing_power_noise/CCS/tcbn28hpcplusbwp12t30p140_180a/`
下的`tcbn28hpcplusbwp12t30p140ffg0p99vm40c_ccs.lib`。正文大小1,556,315,212 B，
解压后正文偏移13,230,658,048 B；完整绑定见[来源记录](source_binding.json)。

## 一次流式读取，保留有限语义

直接跳过已知解压偏移，校验该成员的原tar头、名称、类型、大小和正文起点；
不再逐个扫描目录。以≤64KiB块处理正文，只保留：

- 库单位、显式阈值／默认条件与operating_conditions引用。
- `DFCNQD1BWP12T30P140`的D／CP／CDN／Q属性和明确声明的slew／cap限制。
- FF逻辑关系及setup、hold、recovery、removal、min-pulse等相关timing类型、
  related_pin、when、sense和表模板引用。
- 延迟／transition／constraint表的有效轴、模板／本弧覆盖来源、数值数量和极值。
  完整数值矩阵不保留；不把负约束值改成正值。

其他cell、power／CCS current组按块跳过，不将其数值展开到数组。模板可在使用后定义，
完整成员读完后再解析引用；未解析引用明确列出。随后同一次顺序流丢弃剩余归档数据，
核对已完成索引的完整SHA／gzip CRC和45,137,694,720解压字节；不另扫一遍目录或解码db。

## 与现有输入波形对照

从已完整校验的两例小台波形生成了小型原生参考，只含`time、VDD、CP、D、CDN`五列。
两例全部22772／23083个原生时间点与引脚值保留，来源run／raw SHA／解码SHA均登记，
不是库文件或新仿真。

取得库内实际声明的上／下阈值后，用这些原生点和相邻括区重新计算任意百分比slew，
相关显式阈值按pin→cell→library优先级保留和选择，三层来源均在现有测试中验证；
不把10/90%结果线性换算。保留相关时序弧及输入方向映射；多related_pin或方向未知时
不擅自指定单一参考。`slew_derate_from_library`原值单列，**本包不假定STA derate公式**；
只并列未归一化的阈值间隔和声明表轴，不给时序合格结论。

Q的真实输出负载仍是原三组晶体管／RC网络，没有拟合有效电容；可报告Liberty轴和
max_capacitance，但实际等效负载是否落入范围仍未知。表轴范围、推荐slew/cap与绝对
可靠性界限分别保留；170a SPI／180a Liberty／当前PDK的正式配套仍未证明。

## 预算、验证和交付

一线程／256MiB RSS／1024MiB虚拟内存；托管900s，内部840s留出检查点时间。
压缩输入固定13,657,415,950 B，解压上限为已知完整45,137,694,720 B＋64KiB。
总运行输出4MiB，其中有限语义结果≤1MiB、身份／checkpoint各≤64KiB；回收沿用32MiB。
冻结输入约1.28MB，主要是两份小型引脚参考。

一个focused合成测试通过：17字节块边界、注释／引号中的括号、大CCS跳过、
后定义模板与轴覆盖、负constraint和30/70%原生slew重算。原source／索引／库与PDK未改，
未启动仿真、工具或远端解析。真实Python2.7执行和实际Liberty字段仍待托管运行验证。

[配方](recipe.suggested.yaml) · [限额](semantic_config.json) ·
[原生参考证明](native_references.json) · [解析测试](test_parser.py)

遇界限／语法或完整性问题保留checkpoint并明确未完成；不自动重试，不复制库正文，
不覆盖原索引和失败结果。主聊天负责审核、注册与执行。
