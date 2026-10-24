# SS 冷角 Bootstrap 获取诊断

状态：诊断与方案完成。已提取三角原始窗口、完成三项单管 DC 表征和三张对比图。主要瓶颈定位到 Mmain 在实际栅压下的放电能力；预充损失/启动延迟为次要因素。尺寸、电源和时序方案尚未实施。

## 范围和所有权

起点 89542cc，exp/cdac-flat8-device。用户 Obsidian 移动/编辑和 10-bit 未跟踪文件均不重叠，保留。
冻结候选 027b951，DUT ef0fc74a3df306a366261bd5ce6bbe01f6b4386007c0b86c3150e09c28f976ea。
本次拥有本计划、plan/log.md 追加、scripts/sar8_ss_bootstrap/、verification/sar8_ss_bootstrap/、
output/sar8_ss_bootstrap/、docs/sar8_ss_bootstrap.md、docs/figures/sar8_ss_bootstrap/。
远端 OA none；仅新建 /tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ss_bootstrap_20261024 诊断输出。
原 PVT PSF/模型/所有冻结网表只读；不删除数据、不写 OA、不改时钟、尺寸或源。

## 步骤

1. 核对主开关与自举支路连接、尺寸、负载，以及既有 SS 冷角隔离实验。
2. 从原 TT/0.90/27、SS/0.81/-40、SS/0.81/125 静态案例提取第 1 帧前后
   原生时间步；对比输入、TOP、G、BTOP/BBOT、CTRL/CLKSB 及实际采样窗。
3. 定量区分预充、泵启动、栅压损失、大信号搬移与末段建立；不将 source 电阻电流
   冒充纯 Mmain 电流，不把电容斜率估计当作直接测得 Ron。
4. 如已有数据不足，允许新建只读诊断仿真（不修改冻结电路），先更新具体范围与资源预算。
5. 生成平行波形、简洁报告和方案优先级；明确尚未独立确认的原因。

## 验证与交付

原始数据路径/哈希与前次记录一致，原生 PASS/END。所提取窗口不抽点；测量点早于第一次比较。
图注明角落、供电、输入阶跃、理想外部源、无失配/噪声/PEX及对比基准。
Python 编译、实际分析、图像查看、scoped diff 检查；维护日志和仅本任务本地提交，不 push。
本地新增目标 <0.2 GiB、远端提取 <0.2 GiB，不重跑完整批次。

诊断补充：原生波形显示 105 ns 时 SS 两侧 G−VIN 已接近 0.81 V，而 TOPP
随后仍缓慢下降。新增 3 项单管 DC 表征（TT/27、SS/-40、SS/125），复制
冻结 Mmain 原尺寸/寄生参数，VS=0.045 V、VB=0，VDS=0.1/0.4/0.75 V，
扫 VGS=0.75–1.05 V。测漏极供电电流，用于检验实际栅压附近的放电能力，
不是电路优化或 1.05 V 新偏置方案的批准。使用原生 Spectre，2并行×4线程，
新增预算 <50 MiB，无 OA、PDK 或整机网表改动；不声称直接提取到 Vth。
