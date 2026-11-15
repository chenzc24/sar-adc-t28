# 最简参考候选

需求：[Issue #2](https://github.com/chenzc24/sar-adc-t28/issues/2)。当前默认为 `reference=minimal_msb_d2`：在初版 `minimal_direct` 上仅把 MSB 两侧末级 INV 从 D1 增强到 D2，门级数、逻辑和比较器不变。五角 90/90 帧功能与时序筛查通过，比较器端压通过；FF 冷仍有 SAR 存储 MM64 Vds 违例，参考源瞬态电流增加。[验证与限制](../../../results/soa/msb_drive_d2_trial_20261115.md) · [采用记录](../../../results/design/minimal_msb_d2_adoption_20261115.json)。

SAR 的 `CODE = D OR TOKEN` 经公共 PRESET 初态选择后，直接驱动差分参考开关。低七位在 PRESET 有效时取 0，MSB 取 1；PRESET 无效时跟随 CODE。SAR 的判决寄存器、位序列、握手和 quiet/write 延时保持原样。公共 idle/preset 与采样路径保持 B 的电气语句。

参考侧没有额外 MUX/DFF、捕获请求/确认、逐位复位延时、非交叠发生器或栅极串联电阻。每位的初态逻辑产生反相状态，分别通过 INV 和两级 INV 缓冲，驱动 P/N 两侧。每侧 PMOS/NMOS 的门极共用控制电平，切换中不保证死区。

原接口有四个独立栅极端口，候选用 Spectre 原生 `iprobe` 将每侧两门极短接；它是零压差连接及电流探针，不是额外驱动器。未消费的 RST_DONE 端口接 VSS；D、PHI_U、SAMPLE 输入为兼容现有模块接口而保留，不参与参考状态运算。没有伪造 CAP_CLK。

仅统计 `XREF`，不含 SAR、CDAC 开关和顶层公共 `XIDLE`：

| 元件 | 冻结 B | 最简候选 |
| --- | ---: | ---: |
| 原生 INV | 252 | 28 |
| 原生 NAND2 | 53 | 8 |
| 原生 DFF | 8 | 0 |
| rupolym 网表段 | 370 | 0 |
| MOM 实例 | 51 | 0 |
| 显式 nch/pch 实例 | 25/25 | 0/0 |
| 理想连接/电流探针 | 0 | 17 |

上述为展开后的实例数，不是标准单元内部晶体管数、面积或功耗结果。第一版驱动采用既有原生 D1 单元；驱动能力由实际 CDAC 栅极负载下的原生测试判断。

## 验证入口

`python -m tools.saradc.reference_short prepare --version current --corner tt` 生成冻结包；将 `prepare` 换成 `submit` 后通过 managed 流程登记并排队。`--version b` 指向冻结 B，`--version minimal` 显式复现初版 D1。`status / analyze / collect` 操作对应已登记身份。每次实际修改后使用新 `--revision`，不修改旧输入或重复提交。

五个 corner 为 `tt / ssc / ssh / ffc / ffh`。每版本每角 18 帧，12 个中心码及重复/大跳变。源阻抗、参考旁路、外部低 60 ns 高 40 ns 的采样时钟、真实模拟子电路和负载保持。采用相同原生波形分析器与独立公开输出观察器，电平阈值跟随 VDD，不要求旧参考捕获次数。

逐位底板判据是按标称二进制正权重计算的残差界，不覆盖浮动顶板 kickback。参考开关端口电流包含位移电流，不能直接等同于纯沟道直通电流。缺失信号、未完成波形和观察器不一致都不能算通过。首帧明确参与验收；原始端压告警单列保留。

TT 原生功能与测量通过后才提交其余四角；真实错码、超时或建立 screen 失败先定位。CPU/内存/磁盘不满足 managed 准入时保留队列，不放宽门禁、不终止其他任务。本次由用户明确采用为默认设计；该决定不改变端压规则及未通过结果。
