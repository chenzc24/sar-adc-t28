# A/B 五点 PVT 简报

- 目标：按用户指定 ADC-过压图解.md 风格填充 Obsidian_docs/Report/PVT验收-频谱.md，简明报告最新已回收 A/B 五点功能短测，注明全码和 FFT 边界。
- 脏状态：仓库存在既有实验与笔记改动，全部保留；目标文件当前为空。风格参考只读。共享 plan/log.md 仅追加。
- 所有权：目标笔记、本计划、plan/log.md 新增记录。无图像或电路改动。
- 远端 OA：none；远端仅执行已注册 A/B FFT run-status 只读查询，不改变任何任务。
- 只读依赖：verification/sar8_campaign/ab_pvt/comparison.json、各角回收记录、recovery/a_mx、recovery/mm、pvt_recovery 与 ab_static 已完成证据；ADC-过压图解.md。
- 步骤：核对 A/B 五角功能/时序/电压告警；核对最新 FFT 状态；编写概况、版本、核心指标表及折叠来源。
- 验证：数值逐项对照 JSON，条件/术语准确，折叠链接存在，target diff --check 与全文审阅。
- 不将历史 027b951 频谱归给 A/B；不把关键码短测称为全码/PVT电气合格；无噪声/失配/PEX资格。
- 提交：不 commit/push；不重启/提交仿真，不改自动化。
- 状态：完成；2026-10-28 15:30 北京时间查询 A/B TT FFT 均 simulation running、analysis not_started。笔记按概况/五角结果/标准单元时序影响/频谱状态/端压分段，详细依据折叠。10 个版本×工况的码字与时序布尔值、转换/采样误差/安静裕量表格数值均程序核对通过，CMI 矩阵一致，所有本地来源链接存在，目标 diff --check 通过。无新仿真或远端修改。

## 2026-10-28 FFT结果补充

用户要求将已完成A/B FFT简洁写入同篇笔记。保留现有PVT/时序内容，仅更新概况、频谱段和来源，并标明原CMI矩阵属于短测。新增所有权Obsidian_docs/assets/sar8_campaign_fft/中ab_spectrum.png、a_toolbox_panel.png、b_toolbox_panel.png（从已验证结果复制，使vault内可显示）。verification/sar8_campaign/fft_final只读。验证指标与JSON一致、图片hash一致、链接有效和scoped diff检查；无远端/仿真/commit/push。

FFT补充完成：指标JSON核对、三图复制hash、全部笔记相对链接与scoped diff检查通过。

2026-11-01 用户授权补充TT转换边界扫描DNL/INL及B含噪声FFT。仅更新目标笔记和vault assets/sar8_campaign_fft内static_dnl_inl_zoom.png、static_dnl_inl_overview.png、b_noise_spectrum_comparison.png、b_noise_toolbox_panel.png，保留已有PVT和端压内容。来源为已验证ab_static/fullstatic_recovered.json及sar8_noise/fft_final；记录单seed和无失配/PEX限制。验证源图hash、数值、相对链接和diff；无仿真/OA/commit/push。
