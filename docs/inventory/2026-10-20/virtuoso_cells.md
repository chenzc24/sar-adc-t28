# Virtuoso 设计文件完整清单

库 `SAR_ADC_T28`，远端清点时间 `2026-10-20T14:31:20+08:00`。

以下分类是导航，不是验收状态。`未登记` 表示实际存在但原 manifest 尚未收录；
`远端不存在` 是已登记的计划/本地模型，不能当作可打开的 OA cell。完整字段见 [CSV](virtuoso_cells.csv)。

## 10bit新实验_未冻结

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `cdac10_dr_bank256` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_literal` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_nominal` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b0` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b1` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b2` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b3` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b4` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b5` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b6` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b7` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dr_sw_b8` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac10_dualrail_comparator` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `cdac10_dualrail_controller` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `cdac10_dualrail_input` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `tb_cdac10_dr_ideal_sample` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac10_dr_literal` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac10_dr_nominal` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac10_dr_strongarm` | schematic | 实际存在，原 manifest 未登记 |

## 8bit双轨CDAC候选

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `cdac8_dr_literal` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_nominal` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b0` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b1` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b2` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b3` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b4` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b5` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b6` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dr_sw_b7` | schematic symbol | 实际存在，原 manifest 未登记 |
| `cdac8_dualrail_comparator` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `cdac8_dualrail_controller` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `cdac8_dualrail_input` | symbol veriloga | 实际存在，原 manifest 未登记 |
| `tb_cdac8_dr_ideal_sample` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac8_dr_literal` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac8_dr_nominal` | schematic | 实际存在，原 manifest 未登记 |
| `tb_cdac8_dr_strongarm` | schematic | 实际存在，原 manifest 未登记 |

## 8bit器件CDAC与诊断

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `cdac8_bank_1` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_128` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_16` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_2` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_32` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_4` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_64` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_bank_8` | schematic symbol | zero_markers_literal_unit_instances |
| `cdac8_caps_ideal_switch` | schematic symbol | zero_markers_exact_oa_256_code_nominal_verified |
| `cdac8_controller` | symbol veriloga | native_compiled_cdf_verified_no_dummy_schematic |
| `cdac8_device` | schematic symbol | zero_markers_nominal_characterized_not_qualified |
| `cdac8_device_nominal` | schematic symbol | zero_markers_correlated_open_and_closed_loop_stress_open |
| `cdac8_device_sequence` | symbol veriloga | native_compiled_no_dummy_schematic |
| `cdac8_ref18_b7` | schematic symbol | zero_markers_ss_low_v_cold_vcm_headroom_failed |
| `cdac8_ref_switch_b0` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b1` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b2` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b3` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b4` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b5` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b6` | schematic symbol | zero_markers_characterized_reset_soa_open |
| `cdac8_ref_switch_b7` | schematic symbol | zero_markers_27_mos_dc_corners_characterized_reset_soa_open |
| `cdac8_unit` | schematic symbol | zero_markers_schematic_not_layout |
| `cdac8_unit_candidate_a` | schematic symbol | zero_markers_bias_ac_200_active_local_mc |
| `cdac8_unit_candidate_b` | schematic symbol | zero_markers_bias_ac_200_active_local_mc |
| `cdac8_unit_candidate_c` | schematic symbol | zero_markers_bias_ac_200_active_local_mc |
| `tb_cdac8_caps` | schematic | zero_markers_200_mc_512_randoms_actual_weight_oracle |
| `tb_cdac8_device` | schematic | zero_markers_exact_oa_256_code_nominal_verified |
| `tb_cdac8_ideal_input` | schematic | zero_markers_ss_low_v_cold_first_step_pass_isolates_native_bootstrap_failure |
| `tb_cdac8_nominal` | schematic | zero_markers_256_code_pvt_dynamic_characterization_stress_open |
| `tb_cdac8_nominal_sar` | schematic | zero_markers_code_smoke_correct_device_stress_failed |
| `tb_cdac8_ref18_char` | schematic | zero_markers_three_dc_endpoints_candidate_not_promoted |
| `tb_cdac8_safephase` | schematic | zero_markers_not_promoted_soa_failed |
| `tb_cdac8_sampling` | schematic | zero_markers_correlated_nominal_not_qualified |
| `tb_cdac8_sar` | schematic | zero_markers_code_smoke_correct_device_stress_failed |
| `tb_cdac8_switch_char` | schematic | zero_markers_27_mos_dc_corners_characterized |
| `tb_cdac8_unit_char` | schematic | zero_markers_exact_oa_bias_ac_active_local_mc |

## 8bit复位驱动候选

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `cdac8_reset_device` | schematic symbol | zero_markers_nominal_correlated_not_qualified |
| `cdac8_reset_nominal` | schematic symbol | zero_markers_single_input_pass_cross_input_stress_failed |
| `cdac8_reset_sw_b0` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b1` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b2` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b3` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b4` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b5` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b6` | schematic symbol | zero_markers_not_frozen |
| `cdac8_reset_sw_b7` | schematic symbol | zero_markers_not_frozen |
| `tb_cdac8_reset_literal` | schematic | zero_markers_exact_oa_nominal_tested |
| `tb_cdac8_reset_nominal` | schematic | zero_markers_exact_oa_characterized_not_qualified |
| `tb_cdac8_reset_strongarm` | schematic | zero_markers_exact_oa_one_nominal_input_tested |

## 8bit异步控制

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar8a_and2` | schematic symbol | zero_markers_native_prototype |
| `sar8a_bbm` | schematic symbol | zero_markers_native_RC_prototype |
| `sar8a_bit` | schematic symbol | zero_markers_native_prototype |
| `sar8a_buf` | schematic symbol | zero_markers_native_prototype |
| `sar8a_cmp_if` | schematic symbol | zero_markers_native_prototype |
| `sar8a_delay_advance` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_bbm` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_capture` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_dac` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_publish` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_reset` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_delay_valid` | schematic symbol | zero_markers_loaded_characterization_not_PDK_RC |
| `sar8a_dffr` | schematic symbol | zero_markers_native_reset_unit_pass_not_SOA_qualified |
| `sar8a_frame` | schematic symbol | zero_markers_native_prototype |
| `sar8a_inv` | schematic symbol | zero_markers_native_prototype |
| `sar8a_mux2` | schematic symbol | zero_markers_native_prototype |
| `sar8a_nand2` | schematic symbol | zero_markers_native_prototype |
| `sar8a_nor2` | schematic symbol | zero_markers_native_prototype |
| `sar8a_or2` | schematic symbol | zero_markers_native_prototype |
| `sar8a_out8` | schematic symbol | zero_markers_native_prototype |
| `sar8a_plant` | symbol veriloga | native_compiled_not_controller_or_physical_ADC |
| `sar8a_seq` | schematic symbol | zero_markers_native_prototype |
| `sar8a_sr` | schematic symbol | zero_markers_native_prototype |
| `sar8a_status` | schematic symbol | zero_markers_native_prototype |
| `sar8a_token8` | schematic symbol | zero_markers_native_prototype |
| `sar8a_xor2` | schematic symbol | zero_markers_native_prototype |
| `sar_logic_8b_async` | schematic symbol | zero_markers_TT_representative_pass_SS_timing_and_SOA_open |
| `tb_sar8a_gates` | schematic | zero_markers_TT_and_selected_MOS_corners_tested |
| `tb_sar8a_logic` | schematic | zero_markers_bounded_native_scenarios_not_qualified |
| `tb_sar8a_strongarm` | schematic | zero_markers_representative_codes_correct_negative_input_stress_open |

## 8bit电气宏模型

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_cdac_flat_8b` | schematic symbol | zero_markers_18_cap_groups_52_relays_no_bridge_exact_oa_spectre_verified |
| `sar_comparator_macro_8b` | schematic symbol | zero_markers_13_closed_loop_spectre_cases_completed |
| `sar_macro_controller_8b` | symbol veriloga | compiled_in_exact_oa_closed_loop_no_floating_schematic_placeholder |
| `tb_sar_macro_flat_8b` | schematic | zero_markers_ten_nominal_cases_pass_three_sensitivity_cases_characterized |

## 8bit采样与接口

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_bootstrap_canvas_flat_8b` | schematic symbol | main_width_1um_length_150nm_five_point_tt_full_flat_cdac_pass |
| `tb_bootstrap_flat_8b` | schematic | zero_markers_exact_oa_0p5um_failure_preserved_selected_1um_five_point_pass |
| `tb_cdac_strongarm_flat_8b` | schematic | zero_markers_1um_selected_six_on_off_tt_cases_pass_not_full_transistor_sar |

## Canvas自举源拓扑与旧负载

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_bootstrap_canvas_cdac_t28` | schematic symbol | exact_native_source_minus_cs_zero_markers_full_cdac_tt_verified |
| `sar_bootstrap_canvas_t28` | schematic symbol | zero_markers_exact_oa_netlist_selected_five_point_tt_sizing_verified |
| `tb_bootstrap_canvas_full_cdac` | schematic | zero_markers_exact_oa_export_five_point_tt_and_precision_crosschecks_completed |
| `tb_bootstrap_canvas_t28` | schematic | schematic_read_back_oa_exported_seventeen_sizing_transients_completed |

## T28比较器_8bit复用

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_strongarm_t28` | schematic symbol | 实际存在，原 manifest 未登记 |
| `tb_sar_strongarm_t28` | schematic | 实际存在，原 manifest 未登记 |

## 历史10bit底板实验

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_cdac_bottom_plate_clamp_w100_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_nominally_screened_soa_blocked |
| `sar_cdac_bottom_plate_clamp_w185_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_nominally_screened_soa_blocked |
| `sar_cdac_bottom_plate_clamp_w200_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_nominally_screened_soa_blocked |
| `sar_cdac_bottom_plate_clamp_w250_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_nominally_screened_soa_blocked |
| `sar_cdac_bottom_plate_clamp_w500_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_nominally_screened_soa_blocked |
| `sar_cdac_bottom_plate_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_spectre_sample_hold_screened |
| `sar_cdac_bottom_plate_t28clamp_eval_10b` | schematic symbol | schematic_and_symbol_read_back_zero_markers_sampling_error_failed |
| `tb_sar_bottom_plate_clamp_w100_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_clamp_w185_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_clamp_w200_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_clamp_w250_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_clamp_w500_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bottom_plate_t28clamp_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |

## 历史10bit模型与宏模型

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_cdac_macro_10b` | schematic symbol | schematic_and_symbol_read_back_hierarchically_netlisted |
| `sar_comparator_macro` | schematic symbol | schematic_and_symbol_read_back_zero_markers_and_transient_validated |
| `sar_macro_controller_10b` | symbol veriloga | veriloga_and_symbol_parsed_hierarchically_netlisted_and_transient_validated |
| `sar_sampling_macro` | schematic symbol | schematic_and_symbol_read_back_hierarchically_netlisted |
| `tb_sar_cdac_strongarm_diag` | schematic | schematic_read_back_zero_markers_exact_netlist_exported_nominally_screened_soa_blocked |
| `tb_sar_macro_transient` | schematic | schematic_read_back_zero_markers_exported_and_spectre_transient_validated |

## 历史10bit自举实验

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_bootstrap` | schematic symbol | transistor_prototype_read_back_netlisted_nominally_screened_but_blocked |
| `sar_bootstrap_protected_eval` | schematic symbol | schematic_symbol_read_back_zero_markers_spectre_soa_and_hold_failed |
| `sar_bootstrap_protected_full18_eval` | schematic symbol | schematic_symbol_read_back_zero_markers_nominal_model_warning_clear_hold_failed |
| `tb_sar_bootstrap_protected_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bootstrap_protected_full18_eval` | schematic | schematic_read_back_zero_markers_oa_exported_spectre_screened |
| `tb_sar_bootstrap_transient` | schematic | schematic_read_back_zero_markers_exported_and_nominally_screened |

## 历史比较器尺寸候选

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_strongarm_t28_f2` | schematic symbol | 实际存在，原 manifest 未登记 |
| `sar_strongarm_t28_f4` | schematic symbol | 实际存在，原 manifest 未登记 |
| `tb_sar_strongarm_t28_f2` | schematic | 实际存在，原 manifest 未登记 |
| `tb_sar_strongarm_t28_f4` | schematic | 实际存在，原 manifest 未登记 |

## 器件表征与一阶模型

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `tb_bootstrap_18_main_char` | schematic | schematic_read_back_netlisted_and_pvt_swept |
| `tb_bootstrap_core_main_char` | schematic | schematic_read_back_netlisted_and_pvt_swept |
| `tb_bootstrap_dnw_main_char` | schematic | schematic_read_back_netlisted_and_pvt_swept |
| `tb_cap_char` | schematic | schematic_netlisted_and_tt_simulated |
| `tb_cdac_ref_settling` | schematic | schematic_read_back_netlisted_and_spectre_correlated |
| `tb_comparator_regeneration` | schematic | schematic_read_back_netlisted_and_spectre_correlated |
| `tb_nmos_char` | schematic | schematic_netlisted_and_tt_simulated |
| `tb_pmos_char` | schematic | schematic_netlisted_and_tt_simulated |
| `tb_sampling_acquisition` | schematic | schematic_read_back_netlisted_and_spectre_correlated |
| `tb_tg_switch_char` | schematic | schematic_read_back_netlisted_and_tt_swept |
| `tb_tg_switch_hvt_char` | schematic | schematic_read_back_netlisted_and_pvt_swept |

## 登记计划或本地模型_远端不存在

| Cell | 实际 view | 登记状态 |
| --- | --- | --- |
| `sar_adc_ideal_10b` | 远端不存在 | local_model_only |
| `sar_adc_top` | 远端不存在 | planned |
| `sar_cdac_10b` | 远端不存在 | planned |
| `sar_clock_gen` | 远端不存在 | planned |
| `sar_comp_strongarm` | 远端不存在 | planned |
| `sar_logic_10b` | 远端不存在 | planned |
| `sar_ref_buffer` | 远端不存在 | planned |
| `sar_sample_switch` | 远端不存在 | planned |
| `tb_sar_adc_dynamic` | 远端不存在 | planned |
| `tb_sar_adc_ideal_dynamic` | 远端不存在 | local_netlist_only |
| `tb_sar_adc_ideal_static` | 远端不存在 | local_netlist_only |
| `tb_sar_adc_ideal_timing` | 远端不存在 | local_netlist_only |
| `tb_sar_adc_static` | 远端不存在 | planned |
| `tb_sar_cdac` | 远端不存在 | planned |
| `tb_sar_comp` | 远端不存在 | planned |
