# SAR8：明晚优先交付 FFT 与五点 PVT 关键码

目标时间：北京时间2026-10-29晚。当前是执行目标，不是已确认完成时间。

服务器已启用6个managed重任务槽位，每任务最多4线程。实际CPU配额48核，
本次观测账户内存余量约29GiB、无交换；CPU/内存/磁盘/未知进程检查保留。

执行顺序：

1. 完成低60ns/高40ns的A/B启动短测，第一帧和后续码字均检查。
2. 优先选择通过的标准单元B；若B未通过而A通过，明确记录后使用A。
3. 与严格CX conservative参考比较CX moderate、MX moderate短测。
   码字/握手需通过，关闭沿差不超过5ps，转换/尾部裕量差不超过50ps，
   采样误差差不超过0.02LSB。这是求解器诊断筛查，不是改变ADC规格。
   对照未通过则保留严格设置，不宣称不同设置等精度。
4. 同时安排一个连续1024点FFT和SS冷/SS热/FF冷/FF热关键码测试。
   TT短测构成第五点。**五点关键码筛查不等于五角完整全码、噪声或失配通过。**
5. TT全码和通过抽查角的全码随后执行；Monte Carlo先完成统计/单位电容审核。

频谱：10MS/s，N1024，k461，4.501953125MHz，−1dBFS，连续瞬态、8帧预热。
功耗：源功率10ps网格积分，核心/参考/时钟分别报告，输入源功率不计。
网格收敛检查前标为估计值；过压告警保留，本轮不作电气合格判据。

服务器有限接力程序位于：
`/server_local_ssd/chenzc_intern25/sar-adc-t28/campaigns/sar8-functional-20261028/`
`status.json`为当前步骤，`selection.json`和`solver_selection.json`在相关阶段完成后生成；
各`*_result.json`与`tt_dynamic.json`、`pvt_status.json`逐步保存。
电脑关机不会终止该接力程序及已提交managed任务，定时自动化仍暂停。

当前读回：A/B phase60均运行中，尚无启动修复或新FFT/PVT通过结论。
100个严格未来案例与24个求解器对照/优先案例已登记，只有满足前置检查的案例才会提交。
原101ns方案未运行。旧全码的本地后续提交循环已停止，已在运行的低码案例保留。

部署首次失败发生在Python加载libcrypto之前（自加虚拟地址限制过小）；未调用managed
API。保留原始日志，核对进程已退出后用相同输入恢复。当前接力PID236574已读回运行。
程序只处理小型元数据，仿真与波形分析仍全部走managed流程。

Monte Carlo初查发现模型包含stat/stat_mom等统计section，但CDAC使用multi=1..128，
尚需确认其统计缩放与独立单位电容失配的对应关系，不能直接宣称30种子已安排。
无OA/PDK/library/DUT改动，无baseline采用、commit或push。


## 2026-10-28 回收更新（覆盖前述运行中状态）

A/B phase60及CX/MX对照均完成。原分析因四个小写内部保存名无效失败；四个source-bound分析已完成并回收，原波形未重跑。A/B首帧和后续9帧均正确，B关闭沿延后约4.93ps，转换提前约0.78ns。MX短测数值诊断通过，耗时5.136min，对严格CX34.659min为6.748x；实际MX为1e-6/trap，CX为1e-7/gear2only，不是等精度证明。CX moderate名义对照实际仍conservative，耗时34.413min。

[完整回收对比](recovery/README.md)。新接力continuation-v2已提交B/MX连续1024FFT及四个PVT关键码测试，TT短测构成第五点。原接力失败记录保留，候选未成为OA/整机基线，过压仍未判合格。
