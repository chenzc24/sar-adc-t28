# 异步 SAR：时钟、握手与 cell 划分

2026-10-20 用户选择异步 SAR。本方案替代此前固定 200 MHz 位时钟的
[同步控制提案](sar8_logic.md)。仍按当前 **8 bit、10 MS/s、全差分 flat CDAC**
讨论，不是历史 10 bit 5+5，也不涉及另一个未提交的 dual-rail CDAC 实验。

这是架构与接口方案，尚未实现异步门级电路、Verilog-A 控制器或 Virtuoso
原理图。旧同步模型、Canvas 门级图及其 256 码测试保留，不能作为异步验证。

## 1. 哪部分同步，哪部分异步？

外部采样周期仍为 100 ns（10 MHz）。采样、VCM/reference 交接、转换截止
由独立的帧控制负责；每帧内的 8 次比较则由本次比较完成事件推进，不再
要求外部送入 `CLK_TRIAL / CLK_COMPARE / CLK_LATCH` 三组逐位相位。
比较器仍有本地 `CMP_CLK`，但它是握手产生的评估/复位控制，不是自由振荡器。

第一版采用**有延时约束的 bundled-data 异步控制**：比较完成自定时，
CDAC 建立、锁存和复位使用经表征的保护延时。不是完全无延时假设的异步电路，
也不是模拟节点自动报告“已建立”。先不重叠复位与下一位 CDAC 建立，便于审核。

## 2. 一位转换的闭环

```text
TRIAL_LAUNCH(i)
  -> 参考开关 BBM + CDAC 建立保护
  -> DAC_OK 且 RESET_OK
  -> EVAL_REQ / CMP_CLK=1
  -> 本轮新鲜且合格的 DEC_VALID
  -> 数据稳定保护 -> CAPTURE(i) -> CAPTURE 拉低 / CAP_DONE
  -> CMP_CLK=0，比较器复位
  -> 两输出回到 11 且最小复位时间满足 / RESET_OK
  -> 非末位：ADVANCE -> TRIAL_LAUNCH(i-1)
     末位：PUBLISH -> VALID=1，BUSY=0
```

从 MSB 到 LSB，共 8 次。`CAPTURE` 与 `ADVANCE` 是不同事件；当前 token
在整个锁存脉冲期间保持不动，等锁存结束和复位确认后才移位。
`CAP_DONE` 必须覆盖寄存器时钟到 Q、数据保持及脉冲宽度要求，不能由
未经验证的短脉冲或理想零延迟反相器替代。

工作字与输出字分开。末位也先写 WORK，再等待输出数据稳定后 PUBLISH，
避免遗漏刚决定的 LSB。完成后保留参考状态至 PREPARE，不提前进入采样。

## 3. StrongARM 完成检测：不能直接把 XOR 当时钟

现有 `sar_strongarm_t28` 在 `CLK=0` 时把 OUTP、OUTN 同时预充高；
`VINP>VINN` 对应 OUTP>OUTN。依据是已有
[原理图与波形记录](strongarm_t28_first_pass.md)，不是通用比较器假设。

| 接收后的 P,N | 解释 | 控制处理 |
| --- | --- | --- |
| 11 | 复位态；评估时也可能尚未完成 | 仅复位相位可用于 RESET_OK |
| 10 | 正判决 | 本轮评估已 armed 时才接收，DATA=1 |
| 01 | 负判决 | 本轮评估已 armed 时才接收，DATA=0 |
| 00 | 非法/未合格状态 | 不锁存；资格窗口后仍存在则 FAULT |

组合解码候选：`RAILS_VALID=P XOR N`、`RESET_PAIR=P AND N`、
`ILLEGAL=NOT(P OR N)`、`DATA=P AND NOT N`。
这些只是电平分类，不是合格的脉冲发生器或模拟亚稳态检测器。

`sar8a_cmp_if` 必须记住：本轮已确认复位、当前 EVAL 已发出、结果尚未消费。
只有这些条件满足，且输出在规定输入阈值及后有效保护时间内稳定，才交付
一次 DEC_VALID。复位沿经过 XOR 时产生的暂态、上一轮残留结果、重复事件
均不能再次触发 CAPTURE。若在保护窗口内返回 11、翻转极性或进入 00，
不得继续锁存；报错或等待重新合格，第一版选择报错。

RESET_OK 同样要求 **CMP_CLK 确实为低 + 两输出为 11 + 最小 reset guard**。
只看到输出电平高不能证明 StrongARM 内部 X/Y 已充分预充。
比较器接收器阈值/负载、双轨单调性和 post-valid 数据裕量需联合瞬态确认；
若现有 StrongARM 波形不能可靠支持该协议，先调整接收/完成检测接口，
不直接修改比较器核心，也不让原始模拟输出驱动全芯片锁存时钟。

## 4. 模块与目标 cell

所有目标 cell 显式带 VDD/VSS；RST_N 为系统低有效复位。
下表为计划接口，不是已创建的 OA master。

| 目标 cell | 数量 | 核心职责与接口 |
| --- | ---: | --- |
| `sar8a_frame` | 1 | SAMPLE/HOLD_START/PREPARE/CONV_DEADLINE → START、ABORT、HOLD、工作清零；帧相位产生器在上层 |
| `sar8a_seq` | 1 | 异步相位状态存储；接收 DAC_OK/DEC_VALID/CAP_DONE/RESET_OK，产生 EVAL_REQ/CAPTURE/ADVANCE/PUBLISH |
| `sar8a_cmp_if` | 1 | P/N 接收、复位确认、armed/consumed 状态；交付 DATA、DEC_VALID、RESET_OK、BAD |
| `sar8a_delay` | 多个 | 可选 tap 的保护延时；DAC、post-valid、capture、reset、publish 各自实例，不混成一根链 |
| `sar8a_token8` | 1 | START 装入 T7；只在 ADVANCE 移位；一热位置 T7…T0；末位后清零 |
| `sar8a_bit` | 8 | TOKEN/DATA/CAPTURE → 工作位 W；`CODE=W OR TOKEN`，评估期间不可改变 |
| `sar8a_out8` | 1 | PUBLISH 时一次装入全部 WORK；采样清零不影响 DOUT，只有系统复位清输出 |
| `sar8a_bbm` | 8+dummy | HOLD/CODE → SEL0/SEL1；即刻关断、延迟导通，实际非重叠需表征 |
| `sar8a_status` | 1 | BUSY/VALID/FAULT、末位/超时/非法状态优先级；禁止失败发布 |

`CODE=W OR TOKEN` 在 CAPTURE 后仍把当前位保持为 trial=1；ADVANCE 时
当前位才落到最终 W，下一位被置为 trial。所有这些切换发生于比较器复位态，
并由下一轮 DAC guard 覆盖。最后一位结束时清 token，参考持有最终 WORK。

基础 cell 先采用静态 CMOS `inv/nand2/nor2/and2/or2/xor2/buf`、MUX2、
复位优先 SR latch、可复位 DFF 和可表征延时链。相位握手若使用 Muller
C-element，单列独立 cell，明确复位值、单调输入和互斥条件后再定门级实现；
不能把状态转移表直接当作无冒险组合电路。第一版不优先使用动态 TSPC，
避免可变等待时间带来的动态节点保持要求。

旧 SAR8_BIT 的 WORK/OUT 双寄存器思想可复用，但不原封不动复用其完整端口：
新方案将输出字单列 `sar8a_out8`，token 的 ADVANCE 与工作字 CAPTURE 分开。
旧 SAR8_FLAGS/CLK_GATE 依赖外部固定相位，需替换，不通过改名冒充异步控制。

建议逐 cell 审核顺序：**cmp_if → delay/BBM → seq → 单 bit/token → out/status → top**。
首先冻结 cmp_if 与 seq 的握手，再展开 NAND/SR/DFF 级图。

## 5. 初版时间预算，不是新的测量结果

保持源命令：采样 1–41 ns，42 ns 释放 VCM，43 ns HOLD_START，
90 ns PREPARE，90.22 ns VCM 重连，101 ns 下次采样。
新增独立帧截止 88 ns，给 PREPARE 留 2 ns 的计划裕量；这个截止相位尚未实现。
真正可用的转换窗口是 **43→88 ns，共 45 ns**，不能把整个 60 ns 名义
conversion allocation 都算作可用比较时间。

| 阶段 | 初始预算 |
| --- | ---: |
| 开始时的复位确认 guard | 0.5 ns/帧 |
| trial→eval（含 BBM、驱动传播、CDAC 建立） | 3.0 ns/位 |
| 比较器评估参考预算 | 1.5 ns/位，实际由完成事件决定 |
| valid→capture 数据保护 | 0.10 ns/位 |
| capture 高脉冲 | 0.15 ns/位 |
| comparator reset guard | 0.5 ns/位，还必须等 RESET_OK |
| token/相位推进 | 0.15 ns/位 |
| PUBLISH→DOUT 稳定→VALID 保护 | 0.2 ns/帧 |

若每次比较恰用 1.5 ns，且所有其它阶段都不超过表中预算：
`T = 0.5 + 8×(3+1.5+0.10+0.15+0.5+0.15) + 0.2 = 43.9 ns`，
则 86.9 ns 完成，到 88 ns 尚有 1.1 ns。全部初始数字仍是待验证分配。
**1.5 ns 不是比较器保证的最大延迟**；已有 PVT/offset 未通过的结论继续有效。
延迟链还必须同时满足快角最小建立时间和慢角总转换时限，不能只验 TT。

示意时序采用比较延迟 `[0.22,0.35,0.55,1.10,0.25,0.70,1.30,0.40] ns`，
对应 79.77 ns 完成。此序列是刻意构造的异步示例，**不是从原生波形提取**。
异步只允许快位少等，不承诺每位更快，也不修复 offset、噪声或 CDAC 应力。

## 6. 超时、重启与数据交接

- 系统复位最高优先：CMP_CLK=0、参考释放、内部状态及输出清零。
- CONV_DEADLINE 或 PREPARE 到来而仍 BUSY：中止转换，FAULT=1、VALID=0，
  保留旧 DOUT；不得用超时当成某个 0/1 位。先阻断本地事件，再安全释放参考。
- 新采样清内部工作/VALID；若意外打断 BUSY 同样记录 FAULT。FAULT 保持至
  下一次合法 START 或系统复位，正常 START 才清故障并初始化新握手。
- 每帧 START 仅接受一次；BUSY 中的重复 START、已消费完成事件均不重入。
- 中止后所有尚在延时链中的事件必须被抑制并回零确认，禁止迟到脉冲污染新帧。
- 成功时等末位 capture 和 reset 结束，再发布；VALID 保持至下次采样。
  正常 PREPARE 不清除已发布的 VALID/DOUT。
- DOUT 对外的“原子”指逻辑上同一发布事件；真实 8 路有时钟到 Q 偏差，
  VALID 必须晚于输出最慢稳定时间。异步 VALID 若进入外部时钟域，要用
  保持数据+同步完成标志/握手，不逐位同步数据总线。

## 7. 验证边界与后续工作

本次只验证配置自洽、预算算术和图文一致，不宣称异步功能已仿真通过。
下一门级阶段需覆盖：8 次 fresh decision、token 在 capture 时稳定、
先锁存后复位、复位/建立 guard、重复完成/残留 rail/非法 00、stuck comparator、
deadline 与完成同时到达（截止优先）、异步中止及下一帧恢复、末位发布和旧字保持。
之后再以实际 T28、负载、PVT 验证延时、pulse width、setup/hold、receiver
阈值与 BBM。现有模拟器件问题仍在单独计划内，本次不改变 OA。

参考：异步环路仍需区分比较、比较器复位、DAC 建立、ready 检测和寄存器
传播延迟，见 [Yang 等，J. Semicond. 2017，Fig. 4](https://www.jos.ac.cn/article/doi/10.1088/1674-4926/38/8/085007)。
本文采用便于审核的保守分相方案，不复刻该文 direct-pass 高速优化。

## 审核图与证据位置

Canvas 项目：`SAR8 Async Logic — Architecture Review`，当前入口
`SAR8A_REVIEW`；另有 `SAR8A_HANDSHAKE`、`SAR8A_CELLS`、`SAR8A_TIMING`。
四张均为功能/协议绘图，不含新的可执行异步电气网表。
旧入口改名 `SAR8_SYNC_REVIEW`，其余同步电气文档保留。

本地审核图：[总架构](figures/sar8_async/review.svg)、
[握手](figures/sar8_async/handshake.svg)、
[cell 划分](figures/sar8_async/cells.svg)、
[示意时序](figures/sar8_async/timing.svg)。
完整 Canvas 导出和逐图 PNG 位于 ignored `output/sar8_async/`。
配置解析、预算算术和原有 active/history 规格回归属于文档/配置检查，
不是新异步控制器的功能或电路验收。
