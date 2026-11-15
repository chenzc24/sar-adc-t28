# 验证结果

当前设计为最简参考驱动版，见[采用记录](design/minimal_direct_adoption_20261115.json)。下面历史 A/B 全码、FFT、MC 与噪声结果仍归属原冻结输入，[provenance.json](provenance.json) 保留其来源；不可直接作为最简版性能。

| 验证 | 结果入口 |
| --- | --- |
| TT 全码：255 边界、256 中心码 | [static/results.json](static/results.json) |
| TT 1024 点 FFT 与 ADCtoolbox | [fft/results.json](fft/results.json)、[A/B 频谱](fft/ab_spectrum.png)、[B 版 12 图](fft/b_toolbox_panel.png) |
| B 版单种子 TT 瞬态噪声 | [noise/comparison.json](noise/comparison.json)，带宽与统计收敛未完成 |
| 独立模块与混合层次 | [六模块、逐项混合及 SAR 挂起/重启](blocks/README.md) |
| VA/Python 行为模型 | [行为交叉验证](behav/README.md)，与晶体管性能资格分别记录 |
| A/B 五点关键码 | [pvt/results.json](pvt/results.json) |
| 最简参考候选五点逐管端压 | [新规则判定与时间步长复核](soa/minimal_reference_five_corner_20261115.md)：TT/SS 两角通过本次范围，FF 冷/热持续时间违例 |
| 比较器、CDAC 各 200 种子 | [mc/modules_200.json](mc/modules_200.json) |
| 冷角闭环查询时快照 | [mc/cold_progress.json](mc/cold_progress.json)、[mc/checkpoint_snapshot.json](mc/checkpoint_snapshot.json) |
| 目录迁移 TT 短测 | [运行状态及原始告警](migration/native_short.json)，[迁移回执](migration/restructure.json) |

B 的确定性 TT 动态指标：SNDR 48.788 dB、SFDR 64.768 dBc、ENOB 7.812 bit、SNR 48.806 dB；瞬态噪声、失配和 PEX 在该测试中关闭。功耗估计 86.53 µW，积分网格收敛尚待验证，不含外部输入和时钟源。

比较器 200 种子的失调样本标准差约 14.188 mV；CDAC 独立静态位权预测的最大绝对 DNL 0.1617 LSB、端点 INL 0.0848 LSB。这些范围不等同于整机良率。闭环 MC 的局部失配仅覆盖比较器和 CDAC。

端压告警与未解决项保留。实时进度通过 `python -m tools.saradc observe cold`、`observe refs` 和 `checkpoint` 查询；结果页的 JSON 是有观察时间的快照。

迁移短测 `sar8-tree-tt-short-v1` 的 10 帧码字和事件计数与原 B 版完全一致，三个采样关闭沿及转换时间的最大差值均为 0 ps。首次分析因缺少四个 Bootstrap 内部节点失败，同源只读重分析完成了功能和时序对照。这四个节点的电容预充电压未测，端压告警仍保留。[逐帧对照](migration/comparison.json) · [运行和失败记录](migration/native_short.json) · [原始告警](migration/native_warnings.txt)

SS 5115 的原 q45 参照失败与 q38 修正回执见 [reference_5115.json](mc/reference_5115.json)。
