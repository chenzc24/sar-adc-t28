# RB复位反相器：父任务已完成仿真，本地对照已整理

[同输入结果对照与平行波形](results/README.md)。本轮下冲改善19.40%，回弹和上游过压仍在。
以下保留本地准备时的冻结记录；新原生结果与输入是否合格须分别判断。

源为已完成的 `sar8audit-ctrl-stdcell-live-ff-v1`，managed hash
`a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226`。

只将 `XDUT.XCTRL.XTIM.XCLOCK.X000` 换成原生 `INVD1BWP12T30P140`：
端口顺序为 **CLOCK_RESET、RB、VDD、VSS**。原来的两个自定义MOS退出，
换成库内两个MOS；无显式电容增删，器件尺寸与固有寄生随整级实现改变。
只克隆目标SR，原共享SR/INV不变；真实上游驱动、SR四个栅负载及复位优先级均保留。
另127个实例、11份PWL、模型/求解设置、采样窗口与关闭沿不变。原生库只引用，不复制正文。

保留101MOS的606个物理端压对与3个历史别名、62个电压、436个电流、61个非电源节点KCL。
十四个库MOS共56个D/G/S/B端流必须原生绑定，缺项即失败。
测量CLOCK_RESET输入栅电流/电荷/端口功、RB实际接收负载、双端过冲宽度、SR状态与复位释放延迟。
五路原有源、七路其他理想边界源、被动R0吸收功分别核算。

已有源基线：CLOCK_RESET峰值 **1.014006V**，超过0.991V约 **6.844ps**；
RB最低 **−25.523mV**，低于−1mV约 **3.890ps**，另有 **+2.873mV** 上冲。
R下降→RB上升的半轨延迟约 **3.706ps**。
这些宽度由原生样点交叉估计，±1mV是描述阈值，物理端压筛查仍为0.99V。
详见 [source_reset_reference.json](source_reset_reference.json)，不是新候选结果。

本台仅覆盖FF/0.99V/−40°C首事件，截止41.590786ns；外部电源和时钟理想，无噪声/失配/PEX。
源中未观察到新的reset断言、CLOCK_SET/CLOCK_Q切换；不能宣称完整复位或闭环验证。
SR接收节点只测电压/边沿，未指定栅端测量的电荷/功标为不可用。
保留原始CMI；换接收器不能预判上游24mV过冲消失。

一个最小映射与测量覆盖测试已通过，含有符号半轨延迟、缺失电流拒绝和源/被动功分类。
**23个声明输入，4,640,740B**；[freeze.json](freeze.json) 记录逐项身份。
[recipe.suggested.yaml](recipe.suggested.yaml) 文件SHA：
`d4f3a5fea3e3d2043e58643da2a923bd74d172b092bd10116ff10c30be2b6e42`。
实际run：`sar8audit-ctrl-stdcell-rb-ff-v1`，由父任务managed注册、提交、分析和回收。
实际managed hash：`745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4`。
本会话只读已回收结果，未执行远端命令、OA修改、采纳、commit或push。
