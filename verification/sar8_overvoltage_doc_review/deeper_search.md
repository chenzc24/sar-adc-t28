# 独立 reliability 文件继续检索：2026-10-29

用户要求继续在服务器找明确的核心管电压—持续时间包络。本次结果：尚未取得该包络；
不能声称服务器绝对没有该文件。以下记录实际列目录与归档检查范围，避免以未检出当作不存在。
身份和目录清单见 [search_manifest.json](search_manifest.json)。

## 实际目录

`/home/process/tsmc28n/PDK_DOCS/`：

```text
DRC_2_3a/
layer_usage/
obsolete/              # DRC_Rule、DRC_RULE、DRC_RULE_2_2
sign-off/
```

`/home/process/tsmc28n/PDK_mmWave/PDK_DOC/PDK_doc/TSMC_DOC_WM/`：

```text
DRC/  LVS/  model/  PDK/  PDK_design_support_ref_flow/  RC/  Techfile/
```

`/home/process/tsmc28n/Packages/CLN28HPC+/`：

```text
Bonding_PAD/  design_rule/  DRC_command_file/  GDS_layer_usage/  IO/
Layout_Editor/  LVS_command_file/  memory/  PDK/  RC_extract_existing/
SC/  sign-off/  spice_model/  sram_spice_model/  tf_tluplus_outmap_lef/  utility/
```

`/home/process/tsmc28n/Packages/CRN28HPC+/`：

```text
Calibre_xRC/  others/  SPICE_Kit/  spice_model/
```

## 检索覆盖与排除

- 最终对筛选后的 6145 个目录完成遍历，无超时/权限错误，记录 216 个文档或关键词匹配项。
  排除 CDK/Back_End、单元 schematic/layout、memory、Pycell 运行库、RC 实现等树；
  重复 DB_* 标准单元数据手册不逐个枚举。此前两次更宽的遍历触发时间界限，未被当作完整搜索。
- 检查 Packages 下选定范围的 55 个 ZIP 中央目录，以及核心/射频模型包的嵌套 ZIP。
  包内没有以 reliability/qualification 等命名的匹配文档。大 PDK tar 和全部标准单元
  doc.tar.gz 没有逐一全解包；现有展开文档另行检索。
- SPKT_2163.tar.gz 仅包含两个编号 SPICE ZIP；不是独立可靠性文档包。
- CRN28HPC+/others 中编号 RP-014/024/025/029 实际分别为 IDDQ 估算、布局、芯片实现、
  RC 提取说明；CLN28HPC+/design_rule 中 RP-051 为 tape-out 指南。
  已读取六个小编号文档，未找到目标电压/脉宽包络。
- 32 页 HPC+ Sign-off Recommendation 实际是 STA/OCV 指南。其时钟不确定度 ps 数值
  是时序裕量，不是电压过冲容许持续时间。
- 补查 RF DRM v1.8_R（671 页）关键词及对应段落，与 v2.3 一样给寿命机理/一般形式，
  没有在命中段落给当前 HPC+ULL 核心管的 ps/ns 允许值。未对所有图像做全面 OCR。

## 新的明确资料线索

DRM v2.3 第 647 页 §10.2.3.4.3（已渲染核对）把实际 NBTI 退化判据和特殊应用的温度、
AC/DC 条件指向 **Qualification Report**。同页的 125°C、AC/DC=2、AC 10 年等是
特定寿命评估假设，不能换算成“允许 1.1 V 持续 1 ns”；且其 Vmax 段明确带 N28HP 语境。
第 644–646、648–649 页列出寿命模型及待 qualification 的 Vmax，缺少当前器件定标系数。
标准单元手册第 12 页另指向 **e-Reliability Model System / Overall Reliability Assessment**。

因此还缺当前 HPC+ULL 核心器件适用的 qualification/可靠性定标或使用条件报告、
以及（若有）瞬态 overshoot/undershoot 限制与累计暴露规则。以上是文档引用线索，
不是已确认存在于本机的具体文件名，也不是已取得的许可。

## 意外找到的标准单元配套依据

在此前未覆盖的公共 TSMCHOME 文档位置找到：

`/home/process/tsmc28n/STD_CELL/TSMCHOME/digital/Documentation/release_note/RN_TCBN28HPCPLUSBWP12T30P140_190A.pdf`

- 第 1 页明确给模型 **T-N28-CL-SP-079 1.0_2p8**，对应 HPC+ 模型包；当前项目使用的是
  ULL V1.8_3。这补上了“库发布说明要求哪套模型”的证据，尚不能推导两者可互换或告警为假。
- 第 2 页版本依赖表确认 190a 库配 CCS180a、文档170a、SPICE170a 是官方组合；
  这几个版本号不一致本身不是错误。两页已渲染核对。
- 只读打开指定 HPC+ 模型包内的 Spectre 模型，所检查核心 Vgs/Vds 默认阈值仍为
  **0.99 V**，与当前 ULL 阈值一致。不能通过换模型目录来消除可靠性疑问。
- 该 release note 列出 1.05 V 表征角，并不提供内部节点短脉冲耐压许可。
  实际重新配套验证需要独立冻结对照，当前没有改模型或启动仿真。

当前仍不能填写“1.05/1.10/1.20 V 各允许多少 ps/ns”的表。保留未知，原 CMI 和项目
筛查结论不变。原始文档仅位于忽略的 output；本报告为原创摘要，未提交任何文件。
