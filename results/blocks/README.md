# 独立模块与混合层次验证

配置与测试台见 [tb/blocks](../../tb/blocks/README.md)。下述模块仿真完成时，物理设计的 10 个源文件字节未变；[机器汇总](summary.json) 和 [54 项本地检查](local_validation.json) 保留该阶段的身份。随后 RNL 展示在八个当前源文件中增加绘图注释，去掉这些注释后原字节完全一致；冻结 B 未变，原运行回执不改写。RNL 当前来源与检查结果见 [绘图清单](../../design/rnl/manifest.json)。

| 运行 | 实际范围 | 结论 |
| --- | --- | --- |
| [管级模块](sar8-blocks-tt-v1-analysis-v3/result.json) · [来源](sar8-blocks-tt-v1-analysis-v3/provenance.json) | 六模块独立 TT，真实源阻抗、MOM、接收门及 CDAC 栅负载 | 功能通过；参考 MSB 的门控阈值交叠诊断未通过 |
| [VA 模块](sar8-blocks-va-v1/result.json) · [来源](sar8-blocks-va-v1/provenance.json) | 同类独立测试，以声明的电气 VA 模块替换 DUT；环境负载另列 | 功能与本轮诊断通过，不能转移为管级性能资格 |
| [逐模块混合整机](sar8-mixed-rtcmp-va-v1/result.json) · [来源](sar8-mixed-rtcmp-va-v1/provenance.json) | 管级采样/CDAC/SAR，VA 比较器/参考/RC 延时；原 TT 短测 10 帧 | 码字、8 次比较/更新及公开接口时序检查通过 |
| [SAR 挂起与重启](sar8-sar-reset-tt-v1/result.json) · [来源](sar8-sar-reset-tt-v1/provenance.json) | 正常六帧及第二套实际 SAR；比较器强制不响应 | 正常六码通过；六次均停在 bit7、无误更新，下一采样清除 |

管级 TT 表征的代表数值：

- 采样关闭后误差：首帧 −0.787 mV，后续 −1.061 mV；本测试负载是 256 单位原生 MOM，不能直接当作整机所有寄生。
- 比较器在 ±100 mV 到 ±0.1 mV 的十次判决均有效；最大测得延时约 0.365 ns。浮置输入下差分 kickback **峰值**约 35.8 µV，末端残留约 −0.293 µV；共模峰值约 236.5 µV。噪声/失配关闭。
- CDAC 八位的测量权重正向且尾段稳定；保存了相对有限长尾段的四分之一 LSB 带内建立时间，未据此分配新的逐位时间上限。
- 参考存储字零错误；MSB 两侧的半电源阈值交叠累计约 12.86 ps，首次约在 210.366 ns。它是波形阈值诊断，尚无步长收敛或 MOS 导通电流结论。不能标为非交叠通过。
- 延时链分别记录上升、快速 clear 下降延时与脉宽；SAR 正常六帧约 29.16 ns。参考 `gate_settle_s` 的空值表示该次相同字更新未观察到超出测量带的变化，不代表缺失波形或无限精度。

四类结果分别绑定实际运行输入。测量功能、诊断限值、工况、VA 替代和可靠性资格不互相代替；原生 CMI 端压、SFE、Spectre 数值及 VA 编译环境告警见各运行 `warnings.txt`。完整原始日志和大波形留在服务器，哈希和回收目录在来源回执。

首轮仿真成功，分析器因服务器 Python 2.7 的相对导入异常失败：[实际失败记录](initial_failure.json)。后续 A1/A2/A3 为绑定同一已完成源的 analysis-only：修复导入，分开功能/诊断判定，并补充 kickback 峰值与门控建立测量；未重新仿真、未改写旧结果。A1 保留当时过宽的汇总判定，当前以 A3 为准。

原生比较器/CDAC 的 200 种子统计、PVT 和整机 FFT 仍从 [总结果索引](../README.md) 阅读。本轮不是这些测试的新版本或新的整机/OA 基线。
