# QB NAND栅位对照：首事件已完成，完整SR仍未验证

[与qbcap-q2的紧凑对照及同轴波形](results/README.md)：QB负向下陷72.698→0.388mV，
MID由充电转为放电；仍有RB/RESET尖峰和237对端压超限。16.442ps稳定指标包含后续正峰衰减。
实际run为 `sar8audit-ctrl-stdcell-qborder-ff-v1`，managed hash
`c933758028b599adad5e3ab700a3e610424c2ab10133ccbaa33ead845fd87ce4`，由主聊天完成并回收。
以下保留原冻结包记录；首事件结果不替代完整SR置位/复位验证。

唯一电路变化是 `XCLOCK.X003` 两个串联NM的栅极互换：

- `MN0`仍靠QB，D/S/B不变，栅极由RB改为Q。
- `MN1`仍靠地，D/S/B不变，栅极由Q改为RB。

PM网络、MID原生MOM `multi1`、全部MOS几何/扩散参数及其余126个实例不变，无器件增删。
只克隆目标SR/NAND路径，原共享master不改；11份PWL及整份`test.scs`逐字节相同。
原模型、求解设置、真实驱动/负载、采样窗口和关闭沿保持。对象是`XCLOCK.X003`，历史X020互换包未覆盖。

**观测接线同步修订。** RB的QB支路NM栅端为`MN1:2`，Q对应`MN0:2`；
Q还观测原PM反馈及后级buffer，覆盖全部四个栅负载。两门端的节点目录、RB/Q KCL和VGS/VGD/VGB端对按实际连接重建。
62电压、435电流的名字保持；61节点KCL、606个物理端压对及3个历史别名均保留。
十八个库MOS的72个原生四端电流、MID电荷/端口功、QB恢复、各阶段偏置/端流、源功和输入负担继续记录。
电流不补零、不做重复倍乘，没有region/Vth/沟道分量时不作工作区推断。

**自然初态。** 未新增`.ic`、`.nodeset`或内部PWL；只保留原外部输入/电源初值见证。
QB/Q/MID等内部起始电压允许自然变化，不强行回到基线，不要求复现旧峰值。

**本台验收缺口。** 当前仍是首个采样关闭后的复位释放窗口，不能证明完整SR双向功能：

- 置位：`CLOCK_SET↑`后的Q↑/QB↓、锁存保持及竞争尚未覆盖。
- 复位：从Q高电平开始，`CLOCK_RESET↑→RB↓`后的Q清零、QB恢复及复位优先级尚未覆盖。

结果会保留实际边沿，缺失事件保持未知；栅位变化可能把储荷负担转移到另一方向，不能凭首事件收益判整SR通过。

源为完成的 `sar8audit-ctrl-stdcell-qbcap-ff-q2`，managed hash
`ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0`。
[source_observation_reference.json](source_observation_reference.json)保留原RB上/Q下、multi1电容的储荷观测，
并从已存原生电流提取完整Q门负担；不是新候选仿真结果。
前述q2报告已更正：提交recipe的`run_id`和`retry_provenance`不同，25项电气输入及solver不变。

一个focused测试通过：只有两栅连接变化、全部端流/KCL及应力端对、真实RB/Q负担映射、
负向MID电荷也如实保留、缺失端流拒绝和双向验收缺口；本会话只读主聊天回收的原生结果。
**26项声明输入，4,678,670B**，见 [freeze.json](freeze.json)。
[recipe.suggested.yaml](recipe.suggested.yaml) 文件SHA：
`86cdada64927dd1c7ae68b3a6b99a1de99b6d570c3c20f1885b4a134c3ab0cda`。
run：`sar8audit-ctrl-stdcell-qborder-ff-v1`，由主聊天统一managed提交，当前已有首事件结果。

FF/0.99V/−40°C、41.590786ns；1线程，仿真1GiB/900s，分析256MiB/600s。
外部电源/时钟理想，无噪声/失配/PEX；保留0.99V端压筛查及全部原生CMI。
本会话无远端操作、OA修改、第二个改动、采纳、commit或push。
