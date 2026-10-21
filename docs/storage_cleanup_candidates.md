# 本地历史仿真文件清理候选

2026-10-21只读盘点。没有删除、移动、压缩或上传任何历史文件；本清单不是删除授权。范围仅为本项目的 `output/`，不涉及源代码、PDK、远端OA或其他项目。

本目录合计约 **106.947 GiB**；其中大于100 MiB的236个文件共 **81.332 GiB**。清理前保留网表、配置、源提交/哈希、原生日志、指标、图和故障记录；Git忽略不等于数据可丢。

## 优先核对的内容重复副本

以下两个文件各814,368,482字节，SHA256均为 `54b3731124ac9bb57297c9dbbeff4d143e42e9cfd9f753c90702a27c17f03e0f`。内容完全相同；经确认只保留一份可减少约 **0.758 GiB**。默认分析脚本读取`spectre`副本，因此`confirm`副本是优先核对候选；仍需确认其他调用是否依赖其固定路径。目前两份都保留。

- `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_driver_error_reduction/confirm/run_summary.json`
- `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_driver_error_reduction/spectre/run_summary.json`

## 保留原始PSF后可考虑重建的派生缓存

下列每个pickle都在同一实验目录找到一份PSF。仅这些缓存合计约 **5.611 GiB**。它们不是独立备份；删缓存必须保留PSF并先确认对应解析/重建命令。特别是 `directed_a16/waveform.pickle` 被当前 `b_dynamic_512_reduce.py --self-check` 直接读取，不能无替代地清理。

| 缓存绝对路径 | GiB | 留存与影响 |
| --- | ---: | --- |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/directed_b16/waveform.pickle` | 0.906 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/directed_a16/waveform.pickle` | 0.902 | 同组1份PSF；analysis.json存在；当前解析回归直接依赖 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/history12/waveform.pickle` | 0.677 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w2/waveform.pickle` | 0.501 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_period/waveform.pickle` | 0.501 | 同组1份PSF；b_sine_period/summary.json已核对 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_main_w/w3/waveform.pickle` | 0.501 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w3/waveform.pickle` | 0.501 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_main_w/w2/waveform.pickle` | 0.501 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w1/waveform.pickle` | 0.500 | 同组1份PSF；analysis.json存在 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/r3_anomaly_replay/original_stop/waveform.pickle` | 0.122 | 同组1份PSF；analysis.json存在 |

其他4个大pickle约0.594 GiB未列为优先项：3个 `r3_refgate_events` 缓存的原始PSF在别处，另1个 `r3_anomaly_replay/waveform.pickle` 目录内有多份PSF，尚未逐一验证准确映射。

## 体积较大的JSON还不能按小报告处理

大于100 MiB的74个JSON合计约 **17.318 GiB**，包括整段波形/大型run_summary。不能因为扩展名为JSON就当成可随意删除的小日志。除上面已验证的重复对外，尚未逐项证明它们可由留存PSF完整重建。

| 待核对文件 | GiB |
| --- | ---: |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_driver_error_reduction/confirm/run_summary.json` | 0.758 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_driver_error_reduction/spectre/run_summary.json` | 0.758 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_driver_error_reduction/screen/run_summary.json` | 0.495 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/bootstrap_hold_ablation/spectre/run_summary.json` | 0.455 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/sar8_async_impl/waves/two_cycles_keynodes_aps_01.json` | 0.384 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/sar8_join_r2/runs/nhalf_waveform.json` | 0.330 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/sar8_reference_alignment/runs/nhalf_a200_waveform.json` | 0.330 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/sar8_restore_cross_input/runs/pfull_g100ps_waveform.json` | 0.327 |

## 原始波形需要归档决策

大于100 MiB的145个 `.tran` 文件合计约 **57.007 GiB**。这部分不是缓存；未确认其他有效备份前，删除将失去重新算指标、查应力、查电流和重画时序的依据，恢复可能需要重新仿真。以下只是定位较大的文件，不是直接删除建议。

| 原始PSF绝对路径 | GiB |
| --- | ---: |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/directed_b16/spectre/directed_b16.raw/tran_b_sine.tran.tran` | 4.033 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/directed_a16/spectre/directed_a16.raw/tran_b_sine.tran.tran` | 4.019 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_short_acceptance/history12/spectre/history12.raw/tran_b_sine.tran.tran` | 3.016 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w2/spectre/b_hf_w2.raw/tran_b_sine.tran.tran` | 1.870 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_period/spectre/b_sine_period.raw/tran_b_sine.tran.tran` | 1.869 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w3/spectre/b_hf_w3.raw/tran_b_sine.tran.tran` | 1.869 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_main_w/w3/spectre/b_sine_w3.raw/tran_b_sine.tran.tran` | 1.869 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_sine_main_w/w2/spectre/b_sine_w2.raw/tran_b_sine.tran.tran` | 1.869 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/b_hf_main_w/w1/spectre/b_hf_w1.raw/tran_b_sine.tran.tran` | 1.868 |
| `E:/bridge-Agent-T28/projects/sar-adc-t28/output/veriloga_allocated_noise_spectre/allocated_noise/tb_sar_adc_allocated_noise_dynamic.raw/tran.tran.tran` | 1.830 |

另有3个大CSV约0.802 GiB，也需先确认是唯一数据还是可再导出的结果。

## 目录占用定位

下面是总占用，不建议整目录删除。这里与上述缓存/原始文件有重叠，不能把这些表的数字相加。

| output下目录 | 总GiB |
| --- | ---: |
| `b_short_acceptance` | 13.557 |
| `b_hf_main_w` | 7.115 |
| `sar8_reference_edge_slew` | 6.736 |
| `bootstrap_driver_error_reduction` | 5.586 |
| `cdac8_reset` | 5.323 |
| `cdac8_device` | 4.845 |
| `b_sine_main_w` | 4.742 |
| `sar8_async_impl` | 4.517 |
| `sar8_simple` | 4.118 |
| `sar8_join_r1` | 3.488 |

本次B512目录目前只有少量元数据/测试小文件；约25.60 GB的不完整原生PSF保留在远端cf76d807，未下载。本轮95/516帧异常退出的故障证据也不在清理授权内。
