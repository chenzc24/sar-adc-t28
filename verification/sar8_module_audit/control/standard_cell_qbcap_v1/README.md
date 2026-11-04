# QB内部MID电容：q2已完成，首次许可证失败记录保留

[q2同输入对照与波形](results/README.md)：QB下陷减小35.25%，恢复缩短46.37%；RB/RESET前沿仍超限。
实际q2 run为 `sar8audit-ctrl-stdcell-qbcap-ff-q2`，managed hash
`ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0`。
25项输入与原v1保持相同，父任务已完成原生仿真、分析和回收；本会话只读整理结果。

父任务已提交 `sar8audit-ctrl-stdcell-qbcap-ff-v1`，managed hash
`e51627eebe5435844411e185bfd80f38eb3a2ded3796abf95bdfd4c955c5a7ee`。
Spectre在许可证签出阶段以`SPECTRE-209`退出，exit2，31.302s，峰值RSS42,795,008B。
该次3份回收文件/6,023B的SHA与大小已核对；未进入电路解析或瞬态，不能判定电路失败。
v1失败记录保持；q2的电气结果独立记录，不覆盖原尝试。

只改 `XDUT.XCTRL.XTIM.XCLOCK.X003.CMID` 的 **`multi=2→1`**。
它是SR内部NAND的储荷电容，不是CDAC位权电容；保留原生`cfmom_2t`型号及全部单位几何参数。
原共享NAND/SR不改，只克隆目标路径；其余127个实例、所有MOS尺寸/扩散参数、逻辑和真实驱动/负载不变。
11份PWL和整份`test.scs`逐字节相同，采样窗口、关闭沿、模型及求解设置保持。
原生库和PDK只引用，不复制或改写正文。

测量仍为62个电压、435个电流、61个非电源节点KCL、606个物理端压对及3个历史别名；
十八个库MOS的72个四端电流必须原生绑定。既有观测目录与源功分类完全保持。

新增的本地流式测量会记录：

- QB最低值及在本次窗口内持续回到0.99V±1mV的时间；未恢复标为未知。
- RB越90%后到QB恢复的MID净充电、带符号端口功及电荷平衡。
- 前沿前、RB90%、QB低谷、低谷后30ps、恢复时的四端电压/电流与VGS/VDS。
- 上述各阶段五路源、七路理想边界源及被动R0的独立端口功率；完整源功仍由原分析器累计。
- 原有CLOCK_RESET/RB上下冲幅度、宽度、SR扰动、复位释放及全部端压，检查更快恢复是否伴随更大尖峰。

电流直接使用原生返回值，**不再乘除2**；局部端口功不等于唯一耗散功率。
没有保存region、Vth或沟道电流分量，不追加工作区、Cgd或长沟道公式推断，不预判通过。

源为完成的 `sar8audit-ctrl-stdcell-resetnand-ff-v1`，managed hash
`7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d`。
[源结果](../standard_cell_resetnand_v1/results/README.md)中QB约132ps恢复，RB90%之后MID净吸收约4.365fC。
[source_storage_reference.json](source_storage_reference.json)用相同新测量器回读已验证源波形，明确源电容仍为multi2，不是候选结果。

一次focused测试已通过：唯一电容变化、全部观测/源功目录不变、原生电荷/端口功与偏置、
未恢复保持未知、缺失电流拒绝；原v1许可证失败没有电气结果，后续q2已有独立结果。
**25项声明输入，4,668,313B**，逐项身份见 [freeze.json](freeze.json)。
[recipe.suggested.yaml](recipe.suggested.yaml) 文件SHA：
`bc207d890e6890435142443cf8b62b6b7a6504f921501b402cd7453f7f6e1c7c`。
run：`sar8audit-ctrl-stdcell-qbcap-ff-v1`；父任务统一managed注册、提交和回收。

保持FF/0.99V/−40°C、41.590786ns首事件台；1线程，仿真1GiB/900s，分析256MiB/600s。
外部电源/时钟理想，无噪声/失配/PEX；没有完整复位/闭环验证。原始CMI及0.99V筛查上限保留。
本会话无远端命令、OA修改、第二个改动、后续门替换、采纳、commit或push。
