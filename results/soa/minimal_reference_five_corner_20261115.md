# 最简参考候选：五点 PVT 逐管端压

结论：**本次新规则筛查整体不通过，FF 冷与 FF 热存在持续时间违例。**

对象为 `reference=minimal_direct`，在 `thu-song` 运行。沿用此前五角全管级短测的冻结电路和 18 帧输入，仅增加全部 MOS 端点保存；TT、FF 冷、FF 热另做最大步长 10 ps → 2 ps 复核。输入、参考、采样窗口、关闭沿及器件尺寸不变。

按 [工程规则](../../specs/soa_rule.yaml) 检查每角 1,049 只薄栅 MOS 的 3,147 个 `|Vgs|/|Vgd|/|Vds|` 端对，包含启动。上限为连续 1.1 V、峰值 1.29 V，任意滑动 10 ns 内累计超过 1.1 V 不多于 100 ps。

| 工况 | 最大端压 / V | 最坏窗口累计 >1.1 V / ps | 违例端对数 | 判定 |
| --- | ---: | ---: | ---: | --- |
| TT 0.90 V / 27°C | 1.115417 | 77.916 | 0 | 通过本次覆盖范围 |
| SS 冷 0.81 V / −40°C | 1.061091 | 0.000 | 0 | 通过本次覆盖范围 |
| SS 热 0.81 V / 125°C | 1.009114 | 0.000 | 0 | 通过本次覆盖范围 |
| FF 冷 0.99 V / −40°C | 1.205524 | 166.050 | 9 | 不通过 |
| FF 热 0.99 V / 125°C | 1.191259 | 173.498 | 1 | 不通过 |

五角均为 18/18 帧码字正确。码字正确与端压通过分开判定。SS 两角使用原生自适应时间点（最大步长 10 ps）；TT 和 FF 两角表中采用 2 ps 复核值。

## 违例位置

- 两个 FF 角：比较器输入管 `XDUT.XCOMP.MNINP` 的 `|Vgd|` 持续超限。峰值低于 1.29 V，但单个脉冲已超过 100 ps，首帧及后续正常周期均出现。
- FF 冷额外 8 处：`XDUT.XCTRL.XBIT[7:0].XSTORE.XFF.MM64` 的 `|Vds|`，位于原生标准触发器内部。
- 本次五角的最简参考驱动 `XREF` 没有新规则违例；不据这些结果要求恢复原复杂参考驱动。

## 数值复核与证据范围

| 工况 | 2 ps − 10 ps 峰值变化 / µV | 最坏累计时间变化 / ps | 通过/失败判定一致 |
| --- | ---: | ---: | --- |
| tt | -2.026568 | -0.008883 | 是 |
| ffc | 3.707043 | 0.001336 | 是 |
| ffh | -0.240254 | -0.002831 | 是 |

TT 全波形同时经 Python 参考实现和 C++ 流式实现计算：全部 6,450 个端对的峰值、其中 3,147 个规定端对的累计超限时间及判定完全一致。8 项定向测试和编译扫描器的正负阈值交叉自检通过。器件清单 1,075 只与 Spectre 实际 MOS 数一致，所需 581 个端点均保存。

26 只厚栅 MOS 与体端电压另行记录，不套用本次薄栅规则。例如 SS 冷的比较器 `MNINN` 的 `|Vgb|` 约 1.1425 V，因此这里的通过不能解释为所有端压或晶圆厂寿命资格通过。无 MC、噪声、PEX、供电爬升及更广输入序列覆盖。原始 CMI 和 LTE 暂时放宽警告仍保留。

首次 TT 采集 `sar8-minref-soa-tt-song-v1` 因节点大小写导致新增保存项被忽略，已中断并保留，不进入判定。四角较慢的解释器分析被独立 analysis-only 流式分析替代，完成源的电路与波形未改写。

## 运行与结果

[机器可读汇总及逐项证据散列](minimal_reference_five_corner_20261115.json)。逐管完整统计保存在各运行回收目录的 `derived/terminal_results.json`。

| 工况 | 原生 10 ps 采集 | analysis-only | 2 ps 复核 |
| --- | --- | --- | --- |
| tt | `sar8-minref-soa-tt-song-v2` | `sar8-minref-soa-tt-song-v2-fast-v1` | `sar8-minref-soa-tt-song-v3-step2p` |
| ssc | `sar8-minref-soa-ssc-song-v2` | `sar8-minref-soa-ssc-song-v2-fast-v1` | `—` |
| ssh | `sar8-minref-soa-ssh-song-v2` | `sar8-minref-soa-ssh-song-v2-fast-v1` | `—` |
| ffc | `sar8-minref-soa-ffc-song-v2` | `sar8-minref-soa-ffc-song-v2-fast-v1` | `sar8-minref-soa-ffc-song-v3-step2p` |
| ffh | `sar8-minref-soa-ffh-song-v2` | `sar8-minref-soa-ffh-song-v2-fast-v1` | `sar8-minref-soa-ffh-song-v3-step2p` |

原生完整波形位于 `thu-song:/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/<采集运行 ID>/raw/tran_short.tran.tran`，不回传大型原始文件、不删除历史。所有数值仅覆盖本次 18 帧试验。用户随后于 2026-11-15 采用此实现为默认设计，见[采用记录](../design/minimal_direct_adoption_20261115.json)；FF 违例仍保持开放。
