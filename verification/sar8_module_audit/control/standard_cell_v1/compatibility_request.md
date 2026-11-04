# 生成FF包前缺少的确切元数据

**已解决。** 主会话已补[two_cell_probe_metadata.json](../../standard_cells/two_cell_probe_metadata.json)
和[model_master_metadata.json](../../standard_cells/model_master_metadata.json)。
当前本地包状态见[README](README.md)。以下保留当时缺项的记录，不再作为准备门禁；
SPICE-M原生绑定和端流探针由首次managed运行检验。

已具备：170a原SPICE路径、两单元端口顺序、4+2 MOS计数、真值表、LIVE→A1
栈位、无全局.option/.param/.include，以及原snload-both冻结输入。

主会话只需补两组只读元数据：

1. **原SPICE身份和探针/单位表**：文件SHA256/字节数；ND2D1与INVD1六只MOS
   的实际实例名、D/G/S/B节点名（用于测量目录）、L/W文本的量纲形式/范围。
   不需要复制foundry网表正文；实例/节点与单位元数据足以建立原生探针和量纲检查。
2. **实际PDK master类型**：当前FF模型include链中的 `nch_mac/pch_mac` 定义
   分别是 `model` 还是 `subckt`；若为subckt，给端口顺序。若已有这类SPICE M
   调用在Spectre中的成功例子，附读入方式/端流保存形式即可；没有样例则记录未验证，
   后续由同一个低资源managed包检查原生读入，不改写foundry M/X前缀来凑通过。

原因：M调用引用subckt/model及原生端流端口名不能由同名推断；仅有l/w参数名也
不足以确认长度量纲。未拿到这些信息时不生成猜测的内部实例/探针，不宣布包可运行。
提出此清单时尚无可执行recipe。现已在本目录准备未提交的建议recipe；没有远端命令或新基线，IO V2及旧包保持冻结。
