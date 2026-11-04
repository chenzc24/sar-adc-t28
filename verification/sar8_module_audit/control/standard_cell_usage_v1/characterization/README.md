# 库资料只读检查：阶段结论

已确认远端 `thu-wei`、UID596，资料仍在原标准库目录；没有解包13.66GB CCS包、
安装工具、复制整册PDF或修改库。基线与2k对照的冻结输入未改。

- FF0.99V／−40°C手册正文为 **Version170a，2017/03/31**。PDF SHA为
  `d04a3586051ced68c04dcf20b7b747d5a1b74f3dbf0cd951b9379f2ce7c85097`。
  与当前SPICE路径的170a标记一致；目录标签一致不能证明与当前PDK模型完全配套。
- 文档与SPICE交付中的两份 `IMPORTANT.NOTE` 和版本编号说明分别同SHA。
  这些小文件没有提供已解析的具体模型配套版本。外层190a／CCS180a仍待核实。
- 手册第12页的绝对最高供电／输入／输出电压没有固定数值，要求按产品寿命条件
  查询TSMC的可靠性评估系统。因此不能用推荐供电上限直接替代瞬态寿命限制。
- 第13页推荐供电为标称±10%、结温−40～125°C。第14页定义传播延迟为输入50%
  到输出50%；第15页说明手册简化延迟不能替代Liberty的输入slew／输出load二维表。
  同页模板还有1.2V示例文字，不能当作本0.9V库的推荐工作电压。
- **尚未取得DFCNQD1的slew阈值定义、二维表轴、max_transition/max_capacitance及
  具体时序约束。** 约2.8ps CK是否超出表征范围仍未知。相关PDF页的图形信息也未
  用文字提取来补猜；保持原严格0.99V项目端对筛查，但不宣称已有寿命判定依据。

原始资料页保留远端。这里仅保留路径／文件身份、限定页码、提取脚本和必要元数据。
诊断实验可继续；本检查不阻塞它，也不将内部过冲等同库失效。

小台基线及2k对照的导出恢复、配对分析现已完成，见[配对报告](../results/README.md)。

## 配套与Liberty补查

170a SPICE实读头部标注`Technology: CLN28HT`、`Version: 170a`，全文件SHA与既有冻结
记录一致。文件本身没有`.include/.lib`依赖声明。DFCNQD1的28只管只调用`nch_mac`／
`pch_mac`；整份库中另有`nch_18_mac`供其他单元使用，不能据此称此DFF使用了IO管。

当前实验由已验证wrapper的FF macro section链接`cln28ull_1d8_elk_v1d8_3.scs`的FF等段。
该模型头部明确为`V1.8_3`，并记有2019年的模型修订及BSIM6迁移信息。此前已验证
宏的D/G/S/B端序和实际运行成功；**尚无资料证明这就是170a库表征时要求的模型版本**。
CLN28HT、HPC+ULL与版本目录的名称本身都不能完成这种证明，也不能据此判定不兼容。

FF手册第14页将完整表征条件指向“associated release note”的第5节NOTE。本次已知
documentation目录仅有96个`DB_*.pdf`，未找到该关联release note；已检查的标准库根目录
没有展开的`digital/Front_End/.../CCS`。仍未取得同版Liberty，因此下列项目保持未知：

| DFCNQD1所需信息 | 状态 |
| --- | --- |
| CP／D／CDN的slew测量阈值 | 未读取，不能把本项目10/90%当作库定义 |
| 各引脚／时序弧输入slew与输出load表轴 | 未读取 |
| setup／hold／recovery／removal／最小脉宽具体值 | 未读取 |
| 输出pin capacitance／max_capacitance与max_transition | 未读取 |
| 170a SPICE与当前V1.8_3 PDK／180a CCS的正式配套关系 | 未证明 |

只读归档前缀共**20480字节压缩数据**，在首个267632640字节`.db`正文前停止。
两份小公共说明与170a文档中的文件同SHA，但它们只是通用说明，不是配套证明。
没有扫描完整归档、读取大成员、落盘解包或加载编译库。

进一步获取准确Liberty条件需要主聊天管理的有界归档索引／工具确认，
具体见[提取请求](archive_index_request.json)；这里只提交请求，没有启动。
当前PATH未找到`lc_shell/dc_shell`，仅表示本查询环境未发现，不能推断服务器未安装或无许可。

汇总依据：[配套元数据](dependency_findings.json)、[SPICE目录与头部](compat_inventory.json)、
[当前PDK头部](model_cell_locator.json)、[归档前缀身份](archive_prefix.json)。
