# SAR ADC 文档索引

整理日期：**2026-10-27（北京时间）**。先确定设计分支，再使用其证据。
旧报告中的“当前”只对应其记录日期；退出码、功能、性能、应力和 OA 同步分别判断。

## 本地在研工作

| 工作 | 入口 | 使用边界 |
| --- | --- | --- |
| 手搭 `SAR_ADC_T28_manual` | [拓扑审查](../verification/manual_adc_review/README.md)、[网表测试](../verification/manual_adc/README.md)、[端压与延时](../verification/manual_adc/stress_diagnosis/README.md) | 四帧 RC 候选功能已测；应力未修复，理想延时主线仍待验证；未回写 OA |
| 原 SAR8 模块审计 | [总计划](../plan/2026-10-25-sar8-module-audit/plan.md)、[控制](../verification/sar8_module_audit/control/README.md)、[参考](../verification/sar8_module_audit/reference/README.md)、[比较器](../verification/sar8_module_audit/comparator/review.md)、[采样](../verification/sar8_module_audit/sampling/review.md) | 分项诊断；各子报告保留自己的源身份、日期和未解决项 |
| 独立 10 位双轨实验 | [计划](../plan/2026-10-20-cdac10-dualrail/plan.md) | 用户独立实验，包含未提交工作；区别于早期 10 位 5+5，也未替换 8 位规格 |

这些入口反映本地工作区，不代表已经提交、采用或完成验收。
规格默认值见 `config/design_spec.yaml`；不同拓扑的 Cunit、负载、LSB 和时序须按各自冻结输入核对。

## 保留的设计参考

| 分支 | 入口 | 状态 |
| --- | --- | --- |
| R3 / B | [OA 采用记录](r3_b_oa_adoption.md)、[短验收](b_short_acceptance.md)、[中断的动态任务](b_dynamic_512.md) | 保留的 OA 参考；短测不能替代完整动态验收 |
| R4 原版 | [管级合龙](sar8_physical.md)、[性能](sar8_r4_performance.md) | 保留的性能参考；应力及 PVT 未闭合 |
| 空闲复位候选 | [性能](sar8_idle_performance.md)、[工具箱](sar8_idle_toolbox.md) | 网表候选，未据本次整理推广为 OA 基线 |
| L90 / Mmain2 及修复 | [应力对照](sar8_stress_closure.md)、[修复记录](sar8_physical_repair.md) | 2026-10-25 登记的开发线；未解决问题仍保留 |
| 早期 10 位 5+5 | [历史总览](archive/2026-10-27/root-readme.md)、[历史采样状态](sampling_architecture_status.md)、[review 说明](../review/README.md) | 旧拓扑和评审工具，不用于手搭或 8 位候选的性能宣称 |

版本定位以[设计登记](../management/designs.yaml)的观察时间为准；本页不改变登记中的采用状态。
本轮只归档两份旧导航；下列工程报告和 review 的源锁定依赖保留原路径。

## 完整工程报告目录

以下覆盖 `docs/` 顶层全部工程 Markdown。分类用于查找，未将失败或待验证实验判为完成。

### 规格与长期约定

| 文件 | 原报告标题 |
| --- | --- |
| [architecture.md](architecture.md) | Architecture |
| [design_log.md](design_log.md) | Design Log |
| [error_budget.md](error_budget.md) | System Error Budget |
| [module_first_order_models.md](module_first_order_models.md) | Module-Level First-Order Models |
| [pdk_characterization.md](pdk_characterization.md) | T28 PDK Primitive Characterization |
| [verification_plan.md](verification_plan.md) | Verification Plan |

### 8 位实验与历史候选

| 文件 | 原报告标题 |
| --- | --- |
| [b_dynamic_512.md](b_dynamic_512.md) | B版本1倍主管的512点动态验收 |
| [b_hf_main_w.md](b_hf_main_w.md) | B版本4.5 MHz主采样管宽度短测 |
| [b_short_acceptance.md](b_short_acceptance.md) | B版本1倍主管的整机短验收 |
| [b_sine_decomposition.md](b_sine_decomposition.md) | B版本正弦采样误差分离 |
| [b_sine_main_w.md](b_sine_main_w.md) | B版本主采样管宽度短正弦对比 |
| [b_sine_period.md](b_sine_period.md) | B版本单周期正弦时域验证 |
| [cdac8_dualrail.md](cdac8_dualrail.md) | 8-bit 双轨互补 CDAC：独立器件级候选 |
| [cdac8_no_driver.md](cdac8_no_driver.md) | CDAC 二管选轨：去掉驱动器的网表级对照 |
| [cdac8_pn_ratio.md](cdac8_pn_ratio.md) | CDAC 二管选轨：独立 P/N 尺寸对照 |
| [cdac8_reset.md](cdac8_reset.md) | 8 bit CDAC 复位时序与驱动：第二轮实验 |
| [cdac8_uniform_scale.md](cdac8_uniform_scale.md) | CDAC 参考开关等比例扩大：2x / 3x / 4x |
| [cdac_flat_8b_device.md](cdac_flat_8b_device.md) | 8-bit flat CDAC 器件级首轮实现 |
| [eight_bit_flat_migration.md](eight_bit_flat_migration.md) | 8-bit flat 主线迁移与验证 |
| [r3_anomaly_replay.md](r3_anomaly_replay.md) | R3 异常点重放与时序分析 |
| [r3_b_oa_adoption.md](r3_b_oa_adoption.md) | R3 的 B 事件修复同步和前置验证方案 |
| [r3_refgate_events.md](r3_refgate_events.md) | R3 参考栅控事件处理核实与修复 |
| [sampling_acceptance.md](sampling_acceptance.md) | 采样验收指标与主采样管宽度判断 |
| [sar8_async_implementation.md](sar8_async_implementation.md) | 异步 SAR：可运行模型与 Virtuoso 门级原型 |
| [sar8_async_logic.md](sar8_async_logic.md) | 异步 SAR：时钟、握手与 cell 划分 |
| [sar8_async_two_cycles.md](sar8_async_two_cycles.md) | 两个完整采样周期：异步 SAR 关键节点时序 |
| [sar8_bottom_undershoot.md](sar8_bottom_undershoot.md) | 底板负向偏移：低参考到高参考交接中的两段下冲 |
| [sar8_idle_performance.md](sar8_idle_performance.md) | 空闲段复位版本：全码与频谱对照 R4 |
| [sar8_idle_toolbox.md](sar8_idle_toolbox.md) | 空闲段复位版：ADCToolbox 与时域拟合 |
| [sar8_join_r0.md](sar8_join_r0.md) | SAR8 首组合龙冻结候选 |
| [sar8_join_r1.md](sar8_join_r1.md) | SAR8 R1 冻结电路与合龙仿真结果 |
| [sar8_join_r2.md](sar8_join_r2.md) | SAR8 参考换轨对齐版 R2 |
| [sar8_join_r3.md](sar8_join_r3.md) | SAR8 原理图新基准与合龙复验 |
| [sar8_logic.md](sar8_logic.md) | Eight-bit SAR logic: phase and register contract |
| [sar8_main_width.md](sar8_main_width.md) | Mmain 加宽：SS 冷角建立与五点 PVT |
| [sar8_physical.md](sar8_physical.md) | 8-bit ADC：内部控制的晶体管级实现 |
| [sar8_physical_repair.md](sar8_physical_repair.md) | 8 bit ADC 物理过压修复 |
| [sar8_pvt_mismatch.md](sar8_pvt_mismatch.md) | 8 bit ADC 首批 PVT 风险筛查 |
| [sar8_r3_performance.md](sar8_r3_performance.md) | SAR8 R3 全码静态和正弦动态测量 |
| [sar8_r4_adctoolbox_panel.md](sar8_r4_adctoolbox_panel.md) | R4：ADCToolbox 12-panel 分析 |
| [sar8_r4_idle.md](sar8_r4_idle.md) | R4：把参考分步复位移到转换后的空闲段 |
| [sar8_r4_performance.md](sar8_r4_performance.md) | R4 全码扫描与正弦频谱 |
| [sar8_r4_reference_stress.md](sar8_r4_reference_stress.md) | R4 参考开关过压：采样启动与参考码复位交叠 |
| [sar8_r4_reset.md](sar8_r4_reset.md) | R4 参考复位与采样错峰实验 |
| [sar8_r4_staged.md](sar8_r4_staged.md) | R4 参考分步复位与栅极驱动对比 |
| [sar8_ref_current_probe.md](sar8_ref_current_probe.md) | 原版参考开关的过冲与下冲电流定位 |
| [sar8_ref_symmetric_hold.md](sar8_ref_symmetric_hold.md) | 参考栅极对称保持的 FF 冷热角验证 |
| [sar8_reference_alignment.md](sar8_reference_alignment.md) | SAR8 参考换轨对齐实验 |
| [sar8_reference_edge_slew.md](sar8_reference_edge_slew.md) | SAR8 参考栅压边沿与恢复裕量对照 |
| [sar8_restore_cross_input.md](sar8_restore_cross_input.md) | SAR8 参考恢复候选的正输入和跨帧切换验证 |
| [sar8_restore_guard.md](sar8_restore_guard.md) | SAR8 提前参考恢复：0.1 / 0.5 / 2 ns 对照 |
| [sar8_simple_async.md](sar8_simple_async.md) | 精简异步 SAR：采样初始化、本地位循环 |
| [sar8_simple_canvas.md](sar8_simple_canvas.md) | 精简异步 SAR：Canvas 门级审核入口 |
| [sar8_ss_bootstrap.md](sar8_ss_bootstrap.md) | SS 冷角 Bootstrap 采样不足定位 |
| [sar8_stress_closure.md](sar8_stress_closure.md) | 栅极串联电阻对照：顺序流式回收 |
| [strongarm8_baseline.md](strongarm8_baseline.md) | 8-bit StrongARM：未优化管级基线 |

### 早期采样与比较器实验

| 文件 | 原报告标题 |
| --- | --- |
| [bootstrap_bottom_plate_clamp_width_screen.md](bootstrap_bottom_plate_clamp_width_screen.md) | T28 bottom-plate top-clamp width screen |
| [bootstrap_bottom_plate_eval.md](bootstrap_bottom_plate_eval.md) | Full-CDAC bootstrap sampling-order experiment |
| [bootstrap_current_path_audit.md](bootstrap_current_path_audit.md) | Full-control bootstrap turn-off current-path audit |
| [bootstrap_driver_design.md](bootstrap_driver_design.md) | Transistor-level bootstrap-driver prototype |
| [bootstrap_driver_error_reduction.md](bootstrap_driver_error_reduction.md) | Bootstrap-driver held-error reduction screen |
| [bootstrap_full_cdac_isolation.md](bootstrap_full_cdac_isolation.md) | Protected bootstrap in a full differential CDAC |
| [bootstrap_hold_error_analysis.md](bootstrap_hold_error_analysis.md) | Bootstrap held-sample error ablation |
| [bootstrap_isolate_before_reset.md](bootstrap_isolate_before_reset.md) | Turn off the sampling path before resetting BOOT |
| [bootstrap_main_switch_screening.md](bootstrap_main_switch_screening.md) | Bootstrapped main-switch PVT screening |
| [bootstrap_netlist_fast_ab.md](bootstrap_netlist_fast_ab.md) | Full-control bootstrap: netlist-only fast A/B screen |
| [bootstrap_protected_eval.md](bootstrap_protected_eval.md) | Mixed-voltage bootstrap screening experiments |
| [bootstrap_soa_map.md](bootstrap_soa_map.md) | Bootstrap transistor terminal-stress map |
| [bootstrap_t28_hold_pulldown.md](bootstrap_t28_hold_pulldown.md) | T28 GMAIN hold pull-down: first full-CDAC iteration |
| [bootstrap_turnoff_charge_screen.md](bootstrap_turnoff_charge_screen.md) | Bootstrap MN11 turn-off charge screen |
| [canvas_bootstrap_full_cdac.md](canvas_bootstrap_full_cdac.md) | Canvas 0.5 µm Bootstrap 接入完整 CDAC 的对比 |
| [canvas_bootstrap_t28.md](canvas_bootstrap_t28.md) | Canvas topology implemented with native T28 devices |
| [cdac_reference_settling.md](cdac_reference_settling.md) | CDAC And Reference First-Order Envelope |
| [electrical_macro_model.md](electrical_macro_model.md) | Topology-aware electrical macro-model |
| [sampling_architecture_status.md](sampling_architecture_status.md) | Active sampling architecture: top-plate |
| [strongarm_cdac_integration.md](strongarm_cdac_integration.md) | Full split-CDAC to StrongARM interface diagnostic |
| [strongarm_t28_first_pass.md](strongarm_t28_first_pass.md) | T28 StrongARM comparator — first transistor-level pass |
| [strongarm_t28_verification.md](strongarm_t28_verification.md) | T28 StrongARM first-pass verification screen |
| [switch_characterization.md](switch_characterization.md) | T28 transmission-gate switch characterization |
| [switch_pvt_screening.md](switch_pvt_screening.md) | T28 transmission-gate PVT screening |
| [top_plate_gmain_device_screen.md](top_plate_gmain_device_screen.md) | Top-plate GMAIN-to-VIN first T28 device screen |
| [top_plate_pgate_driver.md](top_plate_pgate_driver.md) | Top-plate PGATE: first T28 local driver |

### 历史记录入口

| 文件 | 原报告标题 |
| --- | --- |
| [project_status.md](project_status.md) | SAR ADC 进度入口 |
| [storage_cleanup_candidates.md](storage_cleanup_candidates.md) | 本地历史仿真清理记录 |

## 笔记、执行与归档

- 人工笔记：[Obsidian 入口](../Obsidian_docs/Rvision/Head.md)，沿用用户现有目录；不恢复被用户删除的旧笔记。
- 运行和 OA：[管理说明](../management/README.md)、[2026-10-25 快照](../management/STATUS.md)、[运行索引](../management/runs/index.yaml)。
- 任务事实：[维护日志](../plan/log.md)；未解决、阻塞和待确认计划保持可见。
- 本轮：[清理记录与保留规则](../management/cleanup/2026-10-27/review.md)；历史批准的删减见[2026-10-25 回执](../management/cleanup/2026-10-25/execution.md)。
- 归档导航：[原根目录总览](archive/2026-10-27/root-readme.md)、[原进度长页](archive/2026-10-27/project_status.md)。

新结果更新所属实验的报告和登记；本入口只维护链接与分支边界，避免再积累逐次运行流水。
