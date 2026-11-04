# X020私有NMOS栈次序实验

以完成的 `sar8audit-ctrl-cmidhalf-v1` 为基点，只交换两只NMOS的栅极。
全部101个MOS的模型/尺寸、全部电阻、CMID multi=1及其他无源器件均保留。
电路源文件仅两字节变化：[electrical_change.diff](electrical_change.diff)。

| 器件/端口 | half | 本实验 |
| --- | --- | --- |
| MN0，靠N的上管 | G=Q1；D=N、S=MID、B=VSS | G=LIVE；其余端口保持 |
| MN1，靠地的下管 | G=LIVE；D=MID、S=B=VSS | G=Q1；其余端口保持 |
| MN0:2栅电流归属 | Q1的KCL | LIVE的KCL |
| MN1:2栅电流归属 | LIVE的KCL | Q1的KCL |

目的：在本事件Q1先为高、LIVE后上升的条件下，让MID由下管先拉低，再由上管
建立N吸收通路。MID初态变化由DC解自然得到，没有强制初值。该机理尚未仿真验证。

原 `test.scs`、11份PWL和 `full_gate_analyze.py` 均字节保持；不需要新wrapper。
冻结分析器已支持数据配置的联立端压。现有供电0.99V、FF、−40°C和原首事件
停止时间41.590786ns不变，原采样窗口与关闭沿不变。没有远端操作或OA修改。

测量保存64个电压、444个端电流；重点KCL从16节点增至17节点，加入Q1。
电流目录按实际新栅连接重建KCL；局部原生输出含75个电流，覆盖Q1/LIVE全部
直接端口和MN0/MN1/MP1各自D/G/S/B端流。重点比较新MN0漏端是否出现净注入、
其与LIVE栅端变化及MP1漏端注入的先后关系。总端电流不直接等同于纯Cgd电流。

| 新增联立端压 | MN0：D=N、G=LIVE、S=MID、B=VSS | MN1：D=MID、G=Q1、S=B=VSS |
| --- | --- | --- |
| VGS | LIVE−MID | Q1−VSS |
| VGD | LIVE−N | Q1−MID |
| VDS | N−MID | MID−VSS |
| VGB | LIVE−VSS | Q1−VSS |
| VDB，漏结电压 | N−VSS | MID−VSS |
| VSB，源结电压 | MID−VSS | 0 |

这12项与原3项共15项，均由0到END的同一原生时刻电压相减，记录有符号极值、
发生时间、最大绝对值及0.99V诊断筛查。结电压负向偏移仍显示；此处没有新设
正向结导通合格阈值，也不以0.99V绝对值筛查代替PDK原生CMI判断。
五个源的全史能量、QUIET边沿/延迟、原始CMI与其余告警保留。

旧整机/half的内部初态和峰值仅作为历史参考。新的初值比较只保留7个理想重放
边界和VDD；不要求MID、内部逻辑节点、峰值或边沿时间与旧版相同。
分析器的`acceptance_pass`仍为空；原始数值、CMI、边沿数和电流需逐项评估。
三电阻偏置的持续静态功耗仍是未解决项。首事件通过也不代表完整周期/PVT通过。

交付入口：[recipe.suggested.yaml](recipe.suggested.yaml)，建议ID
`sar8audit-ctrl-stackorder-v1`。15个声明输入，4,428,042B（不含管理器默认摘要）。
recipe文件SHA256：`11dce5c2bed8b007bc64d55ac086cb85945918b97b0b71264238764439f73f33`。
1线程、仿真1GiB/900s、分析256MiB/600s，沿用父会话的串行管理执行。
精确叶实例差异、栅电流归属和输入散列见 `change_manifest.json`、`freeze.json`。

一次针对性本地合成测试已通过：新栅端/KCL归属、两管全部12项有符号端压、
诊断窗之前的全史极值、不同相位极值不能独立相减，以及MID初态可变化。
合成测试不构成实际Spectre电路结果；尚未登记、提交或仿真本候选。
