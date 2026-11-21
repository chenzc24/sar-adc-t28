# thu-song 旧设计波形审查（未删除）

2026-11-20 采用单沿 SAR 后，按 `docs/waveform-retention.md` 审查 thu-song 本地盘上被取代设计（reset-OR、标准延迟、QUIET）的原始波形。仅涉及本项目、本账户的 `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs`。

- **本次未删除任何文件，回收空间 0。** 服务器端预检在第一步取独占锁时失败（`IOError Errno 11`）：仍有批次控制器持锁，正在运行 `sar8-sebit-pvt45-fft-fe-20261120b-fft/-pvt`，另有 7 个 managed Spectre 任务。策略要求删除前取得独占访问，因此没有绕过该检查。预检失败发生在任何写入之前：服务器上没有建立回执目录，也没有写入 `raw_cleanup.json`。
- 审查范围内共 **68 个运行、约 340.7 GiB**。其中仅 **3 个运行、1.498 GiB** 满足全部条件，已形成待执行清单；其余 **65 个运行、339.25 GiB** 保留，原因见下表。
- 可用空间：清点时 438,754,488,320 B（408.62 GiB），读回时（21:39:47）为 439,269,576,704 B。差值来自并行仿真，与本次操作无关。
- 读回确认：3 个待删波形的大小和 inode 与清单一致，均无清理标记。

## 待执行清单（满足条件，未删除）

结论均见 [QUIET LPE 报告](../../Layout/results/sar_quiet_lpe_20261119.md)，压缩证据来自已有的 `archives/sar8/sar-quiet-lpe-20261119/`，散列已复核，包内输入和回收文件也逐一核对。三者均无下游分析，也不被采用记录、单沿设计记录、采集案例或 CDAC 孔径工作引用。

| 运行 | 目标文件 | 字节 | inode | 归档 SHA256 |
| --- | --- | ---: | ---: | --- |
| `sar-qlpe-xrc-q5-ffc-pilot-20261119a` | `raw/tran_short.tran.tran` | 535,897,420 | 84091201 | `d446a5ba7bdca19e2a77bd28b88bca7bf2b0241bb377b81ae4eb9c6cd967740a` |
| `sar-qlpe-xrc-q5-ssc-pilot-20261119a` | `raw/tran_short.tran.tran` | 536,105,460 | 2207559417 | `e618ed7c5ee6c54893e8128980bb80ae024ba76f7aac52f59d02635d4efe24ff` |
| `sar-qlpe-xrc-q6-ffc-pilot-20261119a` | `raw/tran_short.tran.tran` | 535,901,858 | 6467678027 | `2ffdc444bd6507eee3aa9cb37af07207dd57c9942bd3bb2717c37d7023bc7c4f` |

当前运行的批次结束、账户空闲后执行 `work/storage/release_superseded_20261120.py`（先预检，再加 `--apply`）。脚本会重新核对文件身份、消费者和读写进程。

## 保留的运行

| 原因 | 运行数 | GiB | 解除条件 |
| --- | ---: | ---: | --- |
| 端压证据不完整：reset-OR 五角 `sar8-minref-soa-{tt,ssc,ssh,ffc,ffh}-song-msbd2-resetor-v1-step2p`（186.0 GiB），标准延迟 `sar8-minref-soa-{ffc,ffh}-song-delx-qbuf-20261119a`、`-ffc-song-delx-stress-20261119b` | 8 | 237.47 | 已有逐器件峰值和窗口统计，但没有超限区间及最坏事件的原生时间片段；除 FF 冷 reset-OR 外也没有时间步审阅。需由 managed 纯分析任务补齐并带散列归档。reset-OR 五角另被 `sar8-pvt40-resetor-v1` 引用，该批次状态仍为 running，最后更新于 11-15 |
| 无闭合结论：`sar8-minref-soa-ffc-song-delx-stress-20261119a`、`sar8-minref-current-{ssc,tt}-delx-cal-*`（limit_exceeded）、`sar-qlpe-xrc-q6-ssc-long-20261119a`、`sar8-resetor-mcgl-*-v1`（未分析）、`sar8-pair-s15212-{cd,p}-edge-v3`（分析被拒） | 8 | 49.39 | 记录闭合诊断或完成分析后再归档 |
| 未被结论记录引用：`sar-qlpe-xrc-q6-{tt,ssc,ssh,ffc,ffh}-pvt`、`sar8-minref-current-ffh-delx-cal-20261119a`、`sar8-latch-*`、`sar-qlpe-rc-q5-ssc-cworst-pilot`、`sar8-delx-cal-clock-sar-tt` | 12 | 23.15 | 在 `results/` 中写入结论 |
| 明确保留：标准静态候选 C（`sar-del-pex-c-*`、`sar-del-schem-c-*` 等） | 11 | 15.91 | 见 [候选 C 记录](sar_std_static_candidate_c_20261119.json)：慢角诊断和 ECO 对比关闭后再审 |
| 未在本地回收：`sar8-pair-*-pilot-v2`、`sar8-resetor-mcgl-*-v2` | 6 | 7.35 | 回收到 `work/output/managed_execution/runs/<id>/collected` 并核对散列 |
| 被采用的 CDAC 视图或 CDAC 孔径工作引用：`sar-qlpe-xrc-q6-ssc-pilot`（`sar-acq-q6-xrc-s10-ssc-20261119c` 的参考运行）、`sar-qlpe-rc-q6-*`、`sar-qlpe-rc-q6d200-*`、`sar-qlpe-rc-q5-ffc-cbest-pilot`、`delcell-lpe-ssc` | 8 | 4.35 | 负责人确认孔径工作已关闭，且采用的 CDAC 视图无需重分析 |
| 有测得问题但没有归档异常片段，或归档与回收回执不符（`delcell-lpe-tt`） | 12 | 1.63 | 补充异常片段或关闭问题，重新打包 |

逐运行原因及解除条件见 [JSON](20261120-song-superseded-waveform-review.json)。范围外未作改动：单沿运行（含正在运行的 `sar8-sepl-*-r3a`、`sar8-sebit-pvt-*-lpe-20261120b`、`sar8-sebit-tt-noise-fft1024-*`）、B 基线时序运行、`sar-acq-*`、`xref-*`，以及采用记录中的证据，包括 `sar8-minref-soa-ffc-song-bitwise-a/-b`。

清单 `archives/sar8/20261120-superseded-cleanup/thu-song/plan.json`（SHA256 `406aabd62b5e9e903bd4164bf5c5ab0fbc8d0da01cd716ddd9476b8763f45539`）；清点 `work/storage/20261120-superseded/thu-song-inventory.json`（SHA256 `898d9a9b15e680dc9b56355c842a060050bd11dbf11df7f438e8ebd8d70a7b50`）。审查只读取元数据和本地压缩证据，没有读取波形内容，也没有改动网表、PDK、OA、日志或仿真状态。
