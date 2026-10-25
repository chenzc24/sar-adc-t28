# SAR ADC历史数据删减审核清单

本轮只盘点，没有删除、移动、压缩或重跑。建议先审传输残留，再决定是否只保留服务器的一份旧时序原始波形。当前过压诊断、修复候选、基线和独立10位实验不进入首轮删减。

## 容量与统计口径

| 范围 | 当前占用 | 建议优先审核的传输副本 | 追加可审的本地raw副本 |
| --- | ---: | ---: | ---: |
| 本地项目生成物 | 99.715 GiB | 2.639 GiB | 32.435 GiB |
| 服务器已登记运行 | 205.948 GiB | 10.913 GiB | 不删对应保留原件 |

本地观察：2026-10-25 15:11:50；
服务器观察接收时间：2026-10-25 15:11:53，均采用本机北京时间。
本地所在盘当时空闲 80.968 GiB。GiB=1024³字节；不是整个E盘或整个服务器的总占用。

统计按不重叠目录及inode去重，不能把父目录和子目录再相加。本地为逻辑文件大小，服务器另存分配块数；实际释放量还受硬链接、压缩及文件系统影响。建议量不是已释放量。
服务器 102 个存在根目录，72 个去重后的历史引用根目录未找到；未找到项不计为可删空间。

活动保护（前后两次进程观察）：`/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natscreen-sscold`，PID 5738,5767。这些目录禁止删减；删除前须重新核对所有候选的占用。

## 本地优先审核项

| 审核编号 | 对应实验与对象 | 条件可删量 | 必须保留 |
| --- | --- | ---: | --- |
| L-A1 | MSB4600已完成回收的传输分卷，11个文件 | 2.639 GiB | 服务器同案例完整PSF；本地输入、指标、图与回执 |
| L-B1 | R4 分位参考复位时序扫描的本地raw副本，7个文件 | 18.255 GiB | 服务器同案例完整PSF；本地输入、指标、图与回执 |
| L-B2 | R4 空闲段复位与恢复采样窗口的本地raw副本，3个文件 | 14.180 GiB | 服务器同案例完整PSF；本地输入、指标、图与回执 |

L-A1 是 `output/sar8_r4_staged/msb_4600/spectre/parts_v1/` 下11个分卷，不是整个实验目录。历史恢复回执记录了逐片及合并后校验；本轮仅重新统计尺寸，批准后仍需重核散列。
L-B1/L-B2 仅包含路径、案例和尺寸均对应到服务器的原始PSF，**尚未进行本轮完整内容比对**。只有逐文件SHA256相等，才能删除本地这一份。服务器对应原件在本清单中明确保留。
若两档均获批准且校验通过，本地条件可删总量为 35.074 GiB；不含服务器空间。

### 本地大目录与保留建议

本地项目根：`E:/bridge-Agent-T28/projects/sar-adc-t28`。以下为目录总占用，不等于可删量。

| 编号 | 实验与目录 | 当前占用 | 保留建议 |
| --- | --- | ---: | --- |
| L001 | R4 分位参考复位时序扫描<br>`output/sar8_r4_staged` | 24.239 GiB | 优先审传输副本；本地raw可在服务器原件核验后删 |
| L002 | R4 空闲段复位与恢复采样窗口<br>`output/sar8_r4_idle` | 16.886 GiB | 优先审传输副本；本地raw可在服务器原件核验后删 |
| L003 | R3 B版定向码与历史序列验收<br>`output/b_short_acceptance` | 11.072 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L004 | R4 首版管级合龙及边沿迭代<br>`output/sar8_physical` | 9.317 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| L005 | R4 早期先复位后采样方案<br>`output/sar8_r4_reset` | 7.211 GiB | 第二轮选留最终/精细案例；唯一原始波形不整组删除 |
| L006 | 8位简化异步控制与功能验证<br>`output/sar8_simple` | 4.118 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L007 | 参考支路端电流定位，FF冷/热<br>`output/sar8_ref_current_probe` | 2.920 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L008 | 独立10位双轨实验（用户所有）<br>`output/cdac10_dualrail` | 2.761 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L009 | R3 参考捕获与尖峰定位<br>`output/r3_refgate_events` | 2.653 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L010 | 8位flat迁移与模型基线<br>`output/eight_bit_flat` | 2.298 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L011 | 栅极保持与bit7边沿单变量对照<br>`output/sar8_ref_gate_controls` | 2.175 GiB | 保留全点reduced.json.gz；此前raw已清理，非普通缓存 |
| L012 | B版高频输入主开关宽度对照<br>`output/b_hf_main_w` | 1.873 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L013 | B版整周期正弦回放<br>`output/b_sine_period` | 1.871 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L014 | L90/Mmain2 与 Rgate/4 冷热四组对照<br>`output/sar8_stress_closure` | 1.736 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L015 | R3 异常码字重放<br>`output/r3_anomaly_replay` | 0.995 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L016 | 高低端对称保持与后续位复位<br>`output/sar8_ref_symmetric_hold` | 0.900 GiB | 保留全点reduced.json.gz；此前raw已清理，非普通缓存 |
| L017 | Mmain 2/3/4µm 与角落验证<br>`output/sar8_main_width` | 0.869 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| L018 | 8位 StrongARM 基线<br>`output/strongarm8_baseline` | 0.774 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L019 | 首批PVT风险点与失配验证框架<br>`output/sar8_pvt_mismatch` | 0.690 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| L020 | 历史Bootstrap/采样诊断：bootstrap_hold_ablation<br>`output/bootstrap_hold_ablation` | 0.657 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L021 | 早期复杂握手异步逻辑（历史方案）<br>`output/sar8_async_impl` | 0.589 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L022 | T28 比较器性能验证<br>`output/strongarm_t28_verification` | 0.534 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L023 | 比较器/Canvas拓扑阶段：canvas_bootstrap_t28<br>`output/canvas_bootstrap_t28` | 0.411 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L024 | 参考开关 L30/60/90nm 漏电与Ron<br>`output/sar8_ref_length` | 0.366 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| L025 | 参考源负载支路定位<br>`output/sar8_ref_load` | 0.285 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L026 | 8位MOM CDAC器件实现<br>`output/cdac8_device` | 0.241 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L027 | 原版R4全码与1024点频谱结果<br>`output/sar8_r4_performance` | 0.209 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L028 | 空闲复位版全码与1024点频谱最终结果<br>`output/sar8_idle_performance` | 0.202 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L029 | 统一入口回执与在研修复小结果<br>`output/managed_execution` | 0.200 GiB | 保留：基线、当前诊断/修复或独立实验 |
| L030 | 比较器/Canvas拓扑阶段：strongarm_cdac_integration<br>`output/strongarm_cdac_integration` | 0.147 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| L031 | FF源阻抗与决策时序反事实<br>`output/sar8_ff_counterfactual` | 0.114 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |

旧 `sar8_physical`、`sar8_r4_reset` 和 B版验收占用虽大，很多本地原始波形没有在本轮服务器清单中找到对应原件，不能按重复缓存整组删除。第二轮可由你指定保留的最终/精细/失败案例，再列精确raw文件。

## 服务器优先审核项

| 审核编号 | 对应实验与对象 | 条件可删量 | 必须保留 |
| --- | --- | ---: | --- |
| S-A1 | R4 分位参考复位时序扫描的传输压缩包/分卷，13个文件 | 6.900 GiB | 同案例 `test.raw/tran_perf.tran.tran`、输入、日志与回执 |
| S-A2 | R4 空闲段复位与恢复采样窗口的传输压缩包/分卷，2个文件 | 4.013 GiB | 同案例 `test.raw/tran_perf.tran.tran`、输入、日志与回执 |

S-A1：旧R4分位复位实验的 `transfer_tran.gz` 与 `transfer_parts_v1/part_*`；S-A2：旧R4空闲复位实验的 `transfer_tran.gz`。只审这些传输文件，不删原始PSF。两端的A档传输副本与B档本地raw目标互不重叠。

### 服务器目录与保留建议

- H：`/home/chenzc_intern25/TSMC28/llm_IO/`
- T：`/tmp/virtuoso_bridge_chenzc_intern25/90590/`
- SSD：`/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/`
- ADE：`/server_local_ssd/chenzc_intern25/simulation/`

| 编号 | 实验与目录 | 当前占用 | 保留建议 |
| --- | --- | ---: | --- |
| S001 | L90/Mmain2 与 Rgate/4 冷热四组对照<br>`H/sar8_stress_closure_20261024` | 90.075 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S002 | R4 分位参考复位时序扫描<br>`T/sar8_r4_staged_20261022` | 25.161 GiB | 保留原始PSF；只审传输包/分卷，作为本地raw删减的保留端 |
| S003 | R4 空闲段复位与恢复采样窗口<br>`T/sar8_r4_idle_20261022` | 18.195 GiB | 保留原始PSF；只审传输包/分卷，作为本地raw删减的保留端 |
| S004 | Mmain 2/3/4µm 与角落验证<br>`T/sar8_main_width_20261024` | 16.834 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| S005 | 首批PVT风险点与失配验证框架<br>`T/sar8_pvt_mismatch_20261024` | 16.781 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| S006 | 在研物理修复/器件边界探针：sar8fix-c1r4-ffcold<br>`SSD/sar8fix-c1r4-ffcold` | 13.130 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S007 | 参考支路端电流定位，FF冷/热<br>`H/sar8_ref_current_probe_20261025` | 11.926 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S008 | 参考开关 L30/60/90nm 漏电与Ron<br>`H/sar8_ref_length_20261024` | 5.853 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| S009 | FF源阻抗与决策时序反事实<br>`T/sar8_ff_counterfactual_20261024` | 2.038 GiB | 第二轮选留关键尺寸、角落和失败案例；暂不整组删除 |
| S010 | 栅极保持与bit7边沿单变量对照<br>`H/sar8_ref_gate_controls_20261024` | 1.957 GiB | 保留全点reduced.json.gz；此前raw已清理，非普通缓存 |
| S011 | B版正弦主开关宽度对照<br>`T/virtuoso_bridge_spectre/36fde9f4` | 1.870 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| S012 | 高低端对称保持与后续位复位<br>`H/sar8_ref_symmetric_hold_20261024` | 0.797 GiB | 保留全点reduced.json.gz；此前raw已清理，非普通缓存 |
| S013 | 参考源负载支路定位<br>`T/sar8_ref_load_20261024` | 0.247 GiB | 选留最终结果与代表性失败；中间raw需逐案例确认 |
| S014 | 空闲复位版全码与1024点频谱最终结果<br>`T/sar8_idle_performance_20261022` | 0.173 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S015 | 在研物理修复/器件边界探针：sar8fix-ioscreen-ffcold<br>`SSD/sar8fix-ioscreen-ffcold` | 0.124 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S016 | 在研物理修复/器件边界探针：sar8fix-ioscreen-ffhot<br>`SSD/sar8fix-ioscreen-ffhot` | 0.121 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S017 | 在研物理修复/器件边界探针：sar8fix-ioscreen-tt<br>`SSD/sar8fix-ioscreen-tt` | 0.118 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S018 | 在研物理修复/器件边界探针：sar8fix-ioscreen-sscold<br>`SSD/sar8fix-ioscreen-sscold` | 0.110 GiB | 保留：基线、当前诊断/修复或独立实验 |
| S019 | 在研物理修复/器件边界探针：sar8fix-ioscreen-sshot<br>`SSD/sar8fix-ioscreen-sshot` | 0.104 GiB | 保留：基线、当前诊断/修复或独立实验 |

### 当前必须保留的证据

- `sar8_stress_closure_20261024` 四组约90.075 GiB：原版与Rgate/4、FF冷/热的全管过压原始对照。Rgate/4未采用也不等于证据无用。
- 端电流定位约11.926 GiB、SSD电荷缓冲候选约13.130 GiB，以及两个IO器件边界探针：属于当前尚未结束的物理修复决策。
- R3 B验收、原版R4与空闲复位版的最终码字、全码/频谱、网表、配置、原生日志与图继续保留；不能因原生exit0就把失败证据删掉。
- `sar8_ref_gate_controls` / `sar8_ref_symmetric_hold` 的 `reduced.json.gz` 不是普通压缩缓存。此前部分原始PSF已经按旧授权清理，全点流式结果是关键保留证据。
- 独立 `cdac10_dualrail`、OA、PDK、Git、环境、Obsidian和未关联的其他服务器工程均不纳入删减。

## 其余本地小目录

每项小于0.1 GiB，建议暂留，避免用大量审核精力换很少空间。JSON记录分组统计和所有候选文件的精确路径。

| 编号 | 目录 | 当前占用 |
| --- | --- | ---: |
| L032 | `output/r3_b_oa` | 73.11 MiB |
| L033 | `output/sar8_ff_overvoltage` | 39.49 MiB |
| L034 | `output/bootstrap_bottom_plate_clamp_width_screen` | 19.18 MiB |
| L035 | `output/strongarm_t28_first_pass` | 18.38 MiB |
| L036 | `output/sar8_ff_timing` | 17.65 MiB |
| L037 | `output/sar8_simple_canvas` | 16.63 MiB |
| L038 | `output/cdac8_dualrail` | 16.01 MiB |
| L039 | `output/bootstrap_driver_design` | 15.69 MiB |
| L040 | `output/bootstrap_full_cdac_isolation` | 15.16 MiB |
| L041 | `output/bootstrap_bottom_plate_eval` | 14.73 MiB |
| L042 | `output/canvas_full_cdac` | 13.78 MiB |
| L043 | `output/top_plate_gmain_first_device` | 10.35 MiB |
| L044 | `output/sar8_bottom_undershoot` | 9.02 MiB |
| L045 | `output/bootstrap_main_switch_screening` | 8.56 MiB |
| L046 | `output/switch_characterization` | 7.61 MiB |
| L047 | `output/bootstrap_t28_hold_pulldown` | 7.22 MiB |
| L048 | `output/cdac8_reset` | 6.42 MiB |
| L049 | `output/switch_pvt_screening` | 6.41 MiB |
| L050 | `output/sar8_logic` | 6.26 MiB |
| L051 | `output/bootstrap_turnoff_charge_screen` | 6.25 MiB |
| L052 | `output/sar8_r4_refstress` | 6.21 MiB |
| L053 | `output/bootstrap_netlist_fast_ab` | 5.52 MiB |
| L054 | `output/sar8_physical_repair` | 5.51 MiB |
| L055 | `output/sar8_async` | 5.02 MiB |
| L056 | `output/bootstrap_isolate_before_reset` | 4.12 MiB |
| L057 | `output/top_plate_pgate_driver` | 3.99 MiB |
| L058 | `output/review` | 3.97 MiB |
| L059 | `output/b_dynamic_512` | 3.96 MiB |
| L060 | `output/analog_canvas` | 3.87 MiB |
| L061 | `output/sar8_reference_edge_slew` | 3.84 MiB |
| L062 | `output/sar8_join_r3` | 3.69 MiB |
| L063 | `output/sar8_r3_performance` | 2.99 MiB |
| L064 | `output/pdk_characterization` | 2.98 MiB |
| L065 | `output/b_sine_main_w` | 2.61 MiB |
| L066 | `output/sar8_join_r1` | 2.54 MiB |
| L067 | `output/sar8_ss_bootstrap` | 2.46 MiB |
| L068 | `output/cdac_reference_settling` | 2.38 MiB |
| L069 | `output/module_first_order` | 2.37 MiB |
| L070 | `output/bootstrap_protected_eval` | 1.97 MiB |
| L071 | `output/bootstrap_driver_error_reduction` | 1.95 MiB |
| L072 | `output/CDS_macro.log` | 1.58 MiB |
| L073 | `output/sar8_join_r2` | 1.25 MiB |
| L074 | `output/cdac8_uniform_scale` | 1.10 MiB |
| L075 | `output/cdac8_soa_check` | 750.4 KiB |
| L076 | `output/bootstrap_current_path_audit` | 723.0 KiB |
| L077 | `output/cdac8_pn_ratio` | 644.0 KiB |
| L078 | `output/sar8_n3_diagnosis` | 537.7 KiB |
| L079 | `output/electrical_macro_model` | 497.5 KiB |
| L080 | `output/canvas_bootstrap_replica` | 495.2 KiB |
| L081 | `output/b_sine_decomposition` | 471.5 KiB |
| L082 | `output/cdac8_no_driver` | 436.1 KiB |
| L083 | `output/sar8_restore_cross_input` | 427.8 KiB |
| L084 | `output/oa_electrical_macro_model` | 400.2 KiB |
| L085 | `output/veriloga_baseline_spectre` | 396.5 KiB |
| L086 | `output/oa_top_elaboration` | 365.9 KiB |
| L087 | `output/sar8_reference_alignment` | 340.0 KiB |
| L088 | `output/veriloga_baseline` | 312.8 KiB |
| L089 | `output/sar8_restore_guard` | 307.1 KiB |
| L090 | `output/CDS_macro_active.log` | 306.4 KiB |
| L091 | `output/sar8_join_r1_diagnosis` | 291.1 KiB |
| L092 | `virtuoso/snapshots` | 264.4 KiB |
| L093 | `output/integration_readiness_20261020` | 228.3 KiB |
| L094 | `output/project_inventory` | 184.7 KiB |
| L095 | `output/electrical_macro_model_decap_scan` | 170.3 KiB |
| L096 | `output/sar8_join_r0` | 132.4 KiB |
| L097 | `output/behavioral_baseline` | 111.7 KiB |
| L098 | `virtuoso/exports` | 106.8 KiB |
| L099 | `output/bootstrap_soa_map` | 99.5 KiB |
| L100 | `output/sar8_restore_diagnosis` | 42.2 KiB |
| L101 | `output/remote_waveform_cleanup` | 33.9 KiB |
| L102 | `output/electrical_macro_model_phase_probe` | 25.3 KiB |
| L103 | `output/electrical_macro_model_probe` | 24.4 KiB |
| L104 | `output/electrical_macro_model_probe5` | 24.2 KiB |
| L105 | `output/electrical_macro_model_probe6` | 24.2 KiB |
| L106 | `output/electrical_macro_model_probe2` | 24.2 KiB |
| L107 | `output/electrical_macro_model_probe3` | 24.1 KiB |
| L108 | `output/electrical_macro_model_probe4` | 24.1 KiB |
| L109 | `output/veriloga_allocated_noise_spectre` | 16.0 KiB |
| L110 | `output/storage_audit` | 9.8 KiB |
| L111 | `output/result_final_figures` | 8.8 KiB |
| L112 | `output/result_note` | 7.9 KiB |
| L113 | `output/wrapup_sections345` | 7.2 KiB |
| L114 | `output/wrapup_timer_review` | 5.3 KiB |
| L115 | `output/electrical_macro_model_smoke` | 4.3 KiB |
| L116 | `output/electrical_macro_model_analytic_check` | 4.2 KiB |
| L117 | `output/cdac_macro_oa.png` | 4.1 KiB |
| L118 | `output/tb_macro_oa.png` | 3.5 KiB |
| L119 | `output/oa_netlist_debug` | 3.2 KiB |
| L120 | `output/bootstrap_note_concise` | 3.1 KiB |
| L121 | `output/project_inventory_refresh.log` | 2.9 KiB |
| L122 | `output/project_inventory_runner.log` | 2.8 KiB |
| L123 | `output/sar_logic_compare` | 2.2 KiB |
| L124 | `output/obsidian_report_evidence` | 1.2 KiB |
| L125 | `output/obsidian_report_layout` | 0.8 KiB |
| L126 | `output/sar8_join_r0_capture.log` | 0.7 KiB |
| L127 | `artifacts` | 0.0 KiB |
| L128 | `output/.gitkeep` | 0.0 KiB |

## 其余服务器小目录

包括已登记恢复案例、当前修复小探针，以及在home/SSD的simulation父目录中按项目cell精确匹配的旧ADE运行。非项目名称未递归，不将未知工程计入可删空间。均建议暂留；在研项仍按前述规则保护。

| 编号 | 目录 | 当前占用 |
| --- | --- | ---: |
| S020 | `SSD/sar8fix-hyblong-sscold` | 73.86 MiB |
| S021 | `SSD/sar8fix-hybscreen-sscold` | 53.44 MiB |
| S022 | `T/virtuoso_bridge_spectre/7ed01ff4` | 48.09 MiB |
| S023 | `SSD/sar8fix-natscreen-sscold` | 17.22 MiB |
| S024 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_097_128_r2` | 15.98 MiB |
| S025 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_033_064_r2` | 15.98 MiB |
| S026 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_129_160_r2` | 15.98 MiB |
| S027 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_161_192_r2` | 15.98 MiB |
| S028 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_193_224_r2` | 15.98 MiB |
| S029 | `T/virtuoso_bridge_spectre/r4_recovery_20261022_r2/static_cx_225_255_r2` | 15.51 MiB |
| S030 | `T/virtuoso_bridge_spectre/6a4db60c` | 15.36 MiB |
| S031 | `T/virtuoso_bridge_spectre/ea2b72e3` | 14.98 MiB |
| S032 | `T/virtuoso_bridge_spectre/3eaee689` | 9.38 MiB |
| S033 | `T/sar8_ss_bootstrap_20261024` | 2.47 MiB |
| S034 | `ADE/tb_sar_adc8_join_r4` | 630.4 KiB |
| S035 | `ADE/tb_sar8p_unit` | 561.2 KiB |
| S036 | `ADE/tb_cdac8_sar` | 316.8 KiB |
| S037 | `ADE/tb_cdac8_sampling` | 304.5 KiB |
| S038 | `ADE/tb_cdac8_reset_literal` | 304.4 KiB |
| S039 | `ADE/tb_cdac8_ideal_input` | 285.1 KiB |
| S040 | `ADE/tb_cdac8_nominal_sar` | 282.3 KiB |
| S041 | `ADE/tb_cdac8_reset_strongarm` | 282.0 KiB |
| S042 | `ADE/tb_cdac8_safephase` | 270.3 KiB |
| S043 | `ADE/tb_cdac8_nominal` | 269.9 KiB |
| S044 | `ADE/tb_cdac8_reset_nominal` | 269.6 KiB |
| S045 | `ADE/tb_cdac10_dr_literal` | 267.5 KiB |
| S046 | `ADE/tb_sar_adc8_join_r3` | 263.5 KiB |
| S047 | `ADE/tb_sar_adc8_join_r2` | 261.2 KiB |
| S048 | `ADE/tb_sar_adc8_join_r1` | 258.6 KiB |
| S049 | `ADE/tb_cdac8_dr_literal` | 250.9 KiB |
| S050 | `ADE/tb_cdac10_dr_strongarm` | 247.9 KiB |
| S051 | `ADE/tb_cdac8_dr_strongarm` | 232.5 KiB |
| S052 | `ADE/tb_cdac10_dr_nominal` | 231.5 KiB |
| S053 | `ADE/tb_cdac8_dr_nominal` | 216.1 KiB |
| S054 | `ADE/tb_cdac10_dr_ideal_sample` | 212.4 KiB |
| S055 | `ADE/tb_sar8a_strongarm` | 207.5 KiB |
| S056 | `ADE/tb_cdac8_dr_ideal_sample` | 197.0 KiB |
| S057 | `ADE/tb_sar8a_logic` | 189.8 KiB |
| S058 | `ADE/tb_sar8s_strongarm` | 181.8 KiB |
| S059 | `ADE/tb_sar8s_logic` | 164.1 KiB |
| S060 | `ADE/tb_sar_cdac_strongarm_diag` | 163.2 KiB |
| S061 | `ADE/tb_sar_bottom_plate_clamp_w185_eval` | 145.2 KiB |
| S062 | `ADE/tb_sar_bottom_plate_clamp_w250_eval` | 145.2 KiB |
| S063 | `ADE/tb_sar_bottom_plate_clamp_w500_eval` | 145.2 KiB |
| S064 | `ADE/tb_sar_bottom_plate_clamp_w100_eval` | 145.1 KiB |
| S065 | `ADE/tb_sar_bottom_plate_clamp_w200_eval` | 145.1 KiB |
| S066 | `ADE/tb_sar_bottom_plate_t28clamp_eval` | 145.1 KiB |
| S067 | `ADE/tb_cdac8_device` | 141.2 KiB |
| S068 | `ADE/tb_sar_bottom_plate_eval` | 140.0 KiB |
| S069 | `ADE/tb_bootstrap_canvas_full_cdac` | 136.7 KiB |
| S070 | `ADE/tb_bootstrap_flat_8b` | 132.7 KiB |
| S071 | `ADE/tb_sar8a_gates` | 132.3 KiB |
| S072 | `ADE/tb_cdac_strongarm_flat_8b` | 129.0 KiB |
| S073 | `ADE/tb_cdac8_caps` | 109.1 KiB |
| S074 | `ADE/tb_sar_macro_transient` | 106.8 KiB |
| S075 | `ADE/tb_sar_macro_flat_8b` | 102.7 KiB |
| S076 | `ADE/tb_sar_bootstrap_protected_full18_eval` | 90.4 KiB |
| S077 | `ADE/tb_sar_bootstrap_protected_eval` | 89.8 KiB |
| S078 | `ADE/tb_cdac8_ref18_char` | 89.1 KiB |
| S079 | `ADE/tb_cdac8_switch_char` | 88.8 KiB |
| S080 | `ADE/tb_sar_bootstrap_transient` | 88.0 KiB |
| S081 | `ADE/tb_bootstrap_canvas_t28` | 87.7 KiB |
| S082 | `ADE/tb_sar_strongarm_t28_f2` | 85.8 KiB |
| S083 | `ADE/tb_sar_strongarm_t28_f4` | 85.8 KiB |
| S084 | `ADE/tb_sar_strongarm_t28` | 85.6 KiB |
| S085 | `ADE/tb_cdac8_unit_char` | 73.9 KiB |
| S086 | `ADE/tb_tg_switch_hvt_char` | 70.1 KiB |
| S087 | `ADE/tb_tg_switch_char` | 70.0 KiB |
| S088 | `ADE/sar_comparator_macro` | 68.9 KiB |
| S089 | `ADE/tb_bootstrap_dnw_main_char` | 68.3 KiB |
| S090 | `ADE/tb_bootstrap_core_main_char` | 68.3 KiB |
| S091 | `ADE/tb_bootstrap_18_main_char` | 68.3 KiB |
| S092 | `ADE/tb_sar8p_passives` | 67.9 KiB |
| S093 | `ADE/tb_pmos_char` | 67.9 KiB |
| S094 | `ADE/tb_nmos_char` | 67.8 KiB |
| S095 | `ADE/tb_sampling_acquisition` | 67.3 KiB |
| S096 | `ADE/tb_cdac_ref_settling` | 67.3 KiB |
| S097 | `ADE/sar_sampling_macro` | 67.2 KiB |
| S098 | `ADE/tb_comparator_regeneration` | 66.8 KiB |
| S099 | `ADE/tb_cap_char` | 66.6 KiB |
| S100 | `SSD/workflow-rc-20261025-final` | 45.1 KiB |
| S101 | `SSD/workflow-rc-20261025` | 44.7 KiB |
| S102 | `ADE/sar_cdac_macro_10b` | 1.6 KiB |

## 审核与执行边界

所有项均待你批准。本清单无删除脚本，也不会因为勾选或编辑JSON就执行操作。你可以按编号批准A档、B档，或指定某个大目录只保留哪些案例。
执行前另做精确清单、占用复核、散列与保留副本验证；不允许将同一运行的本地和服务器最后一份原始波形同时列为删除。
证据入口：[精确审核清单](review_manifest.json)、[本地元数据](local_census.json)、[服务器元数据](server_census.json)、[登记快照](registry_snapshot.json)。
此前清理回执仍在 `verification/storage/`；本次不把已清理的文件重新算作候选空间。
