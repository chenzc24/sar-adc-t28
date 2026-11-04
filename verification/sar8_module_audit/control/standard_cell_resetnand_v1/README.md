# CLOCK_RESET末级NAND：父任务已完成，本地对照已整理

[结果表、平行波形与QB恢复分析](results/README.md)。源级前沿改善，QB长尾未消失，新增8对为微伏级端压超限。
以下保留准备时的冻结记录；冻结与仿真完成不代表电路合格。

只替换 `XDUT.XCTRL.XTIM.X023.X002` 为原生 `ND2D1BWP12T30P140`：
**AB→A1、BB→A2、CLOCK_RESET→ZN、VDD、VSS**。
AB/BB仍由原来的两个真实INV驱动，当前RB及SR负载、复位极性/优先级保持。
只克隆目标OR master，原共享OR/NAND/INV不变；其他124个实例、11份PWL及非save网表设置逐项不变。
采样窗口和关闭沿不变。原生标准库只引用，不复制或改写正文。

原四个自定义MOS及MID显式电容一起退出，新四个库MOS与内部`net10`接入。
旧电容参数原样记录于 [change_manifest.json](change_manifest.json)，无新增显式电容。
这是整级实现对照：尺寸、固有寄生和旧MID电容同时改变，不作单管/单电容因果解释。

保留101MOS的606个物理端压对及3个历史别名、62电压、435电流、61个非电源节点KCL；
电流少一路对应已退出的MID电容。十八个库MOS共72个D/G/S/B端流必须原生绑定，缺项即失败。
测量两路真实上游AB/BB的栅电流、事件电荷与端口功，以及CLOCK_RESET/RB过冲宽度、SR扰动和释放延迟。
五路原有源、七路其他理想边界源与被动R0吸收功分别核算，不据此宣称整周期ADC功耗。

源为已完成的 `sar8audit-ctrl-stdcell-rb-ff-v1`，managed hash
`745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4`。
[源结果](../standard_cell_rb_v1/results/README.md)仍有CLOCK_RESET +24.622mV、RB −20.571mV及+4.650mV回弹，释放延迟4.712ps。
两路原生输入负担参考见 [source_input_load_reference.json](source_input_load_reference.json)，不是候选仿真结果。

本台为FF/0.99V/−40°C首事件，停止41.590786ns；外部电源/时钟理想，无噪声/失配/PEX。
新的reset断言、完整复位周期及闭环均未覆盖；缺失事件保持未知。物理端压门限仍0.99V，原始CMI保留。
原生核心标准门不能预判为自动满足端压限制。

一个focused映射/覆盖测试已通过，包括真实负载不变、全部端流/KCL、带符号输入交换、缺失信号失败及源/被动功分类。
**24个声明输入，4,652,919B**，身份见 [freeze.json](freeze.json)。
[recipe.suggested.yaml](recipe.suggested.yaml) 文件SHA：
`358c53c6d6d5893974739a746534bb63328ce68ebd46a3110aae1cc5d6e0736a`。
实际run：`sar8audit-ctrl-stdcell-resetnand-ff-v1`；父任务managed hash
`7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d`。
1线程，仿真1GiB/900s，分析256MiB/600s，回收上限32MiB。
本会话只读回收数据，未执行远端命令、OA修改、采纳、commit或push，未扩展下一门或全链。
