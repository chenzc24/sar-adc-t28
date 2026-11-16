# 验证结果

完成实验按[波形归档与清理规则](../docs/waveform-retention.md)保存小数据、图表、告警及运行身份；允许随后清理原始大波形，回执与归档索引放在 `results/storage/`。

2026-11-15 已清理 thu-song 旧波形 374.985 GiB，保留最新 OR 版五角数据；[归档与删除回执](storage/20261115-song-waveform-cleanup.md)。

当前设计为最简参考 MSB D2＋数据复位 OR 版，见[采用记录](design/reset_data_or_adoption_20261115.json)。本版 45 点 PVT 短测共 490 帧码字及功能时序通过；原五角逐管端压数值违例为 0，保留时间分辨率复核标记，新增 40 角仅验证功能时序与接口筛查。下面历史 A/B 全码、FFT、MC 与噪声结果仍归属原冻结输入，[provenance.json](provenance.json) 保留其来源；不可直接作为最简版性能。

| 验证 | 结果入口 |
| --- | --- |
| TT 全码：255 边界、256 中心码 | [static/results.json](static/results.json) |
| TT 1024 点 FFT 与 ADCtoolbox | [fft/results.json](fft/results.json)、[A/B 频谱](fft/ab_spectrum.png)、[B 版 12 图](fft/b_toolbox_panel.png) |
| 当前 OR 版连续 1024 点含噪声 FFT | [最终回收及频谱](noise/resetor_1024_20261116/README.md)：SNR 48.576dB、SNDR 48.554dB、ENOB 7.773bit、SFDR 65.495dBc；1032帧协议通过，单噪声种子，保留端压/LTE及收敛限制 |
| 当前 OR 版整机全局＋局部 MC | [36/36 种子最终回收](mc/resetor_global_local_36/README.md)：360 帧、2880 次逐位比较通过时序及建立筛查；码字偏移和测量范围分别记录 |
| 当前 OR 版选择性失配边界补测 | [14/16案例回收](mc/selective_boundary_results_20261116/README.md)：476帧、3808次逐位比较通过本次诊断；标称C/D两例预算未覆盖，边界偏移与告警分别记录 |
| B 版单种子 TT 瞬态噪声 | [noise/comparison.json](noise/comparison.json)，带宽与统计收敛未完成 |
| 当前 OR 版其余 40 角短测 | [45 点回收：新增 400/400 帧通过及范围限制](pvt/resetor_45_short_20261115.md)；[原入队记录](pvt/resetor_40_launch_20261115.md) |
| 独立模块与混合层次 | [六模块、逐项混合及 SAR 挂起/重启](blocks/README.md) |
| VA/Python 行为模型 | [行为交叉验证](behav/README.md)，与晶体管性能资格分别记录 |
| A/B 五点关键码 | [pvt/results.json](pvt/results.json) |
| 最简参考候选五点逐管端压 | [新规则判定与时间步长复核](soa/minimal_reference_five_corner_20261115.md)：TT/SS 两角通过本次范围，FF 冷/热持续时间违例 |
| 比较器栅漏超限定位 | [输入顶板切换下冲](soa/comparator_input_undershoot_20261115.md)；[D2 候选五角短测及比较器端压通过](soa/msb_drive_d2_trial_20261115.md)，FF 冷仍有 SAR 存储违例；已按用户决定采用 |
| FF 冷 SAR 标准 DFF 内部超限 | [复位反馈与 MM64 源极下冲](soa/dff_reset_feedback_20261115.md)；[外围时序隔离对照](soa/dff_periphery_order_20261115.md)：库内部不变，D 下降移出清零区间使超限时间约 132→25 ps；真实外围验证见下一项 |
| 数据 DFF 外部原生 OR 候选 | [FF 冷真实闭环短测](soa/dff_reset_or_ffc_20261115.md)：18/18 帧功能时序通过，规则内违例 8→0，最坏累计 131.527→52.515 ps；已按用户决定采用；后续其余角结果见上方 45 点回收 |
| 比较器、CDAC 各 200 种子 | [mc/modules_200.json](mc/modules_200.json)；[与当前版的复用核对及补测范围](mc/modules_200_reuse_audit_20261116.md) |
| 冷角闭环查询时快照 | [mc/cold_progress.json](mc/cold_progress.json)、[mc/checkpoint_snapshot.json](mc/checkpoint_snapshot.json) |
| 目录迁移 TT 短测 | [运行状态及原始告警](migration/native_short.json)，[迁移回执](migration/restructure.json) |

B 的确定性 TT 动态指标：SNDR 48.788 dB、SFDR 64.768 dBc、ENOB 7.812 bit、SNR 48.806 dB；瞬态噪声、失配和 PEX 在该测试中关闭。功耗估计 86.53 µW，积分网格收敛尚待验证，不含外部输入和时钟源。

历史比较器 200 种子的失调样本标准差约 14.188 mV；CDAC 独立静态位权预测的最大绝对 DNL 0.1617 LSB、端点 INL 0.0848 LSB。这些范围不等同于整机良率。该历史冷角闭环 MC 的局部失配仅覆盖比较器和 CDAC；2026-11-15 当前 OR 版新批次采用全局＋全 DUT 局部统计变化，见上表。

端压告警与未解决项保留。实时进度通过 `python -m tools.saradc observe cold`、`observe refs` 和 `checkpoint` 查询；结果页的 JSON 是有观察时间的快照。

迁移短测 `sar8-tree-tt-short-v1` 的 10 帧码字和事件计数与原 B 版完全一致，三个采样关闭沿及转换时间的最大差值均为 0 ps。首次分析因缺少四个 Bootstrap 内部节点失败，同源只读重分析完成了功能和时序对照。这四个节点的电容预充电压未测，端压告警仍保留。[逐帧对照](migration/comparison.json) · [运行和失败记录](migration/native_short.json) · [原始告警](migration/native_warnings.txt)

SS 5115 的原 q45 参照失败与 q38 修正回执见 [reference_5115.json](mc/reference_5115.json)。
