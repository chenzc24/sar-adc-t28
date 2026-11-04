# 分段复位版性能笔记整理

- 目标：按用户要求移除目标笔记中的 R4 对照，只描述空闲段分步复位版 027b951；精简文字并重画两张单版本工程图。
- 脏状态：仓库已有大量与仿真、管理及笔记整理有关的改动，保持原样；本笔记无既有未提交修改。共享 plan/log.md 只追加本次记录。
- 所有权：Obsidian_docs/Rvision/8bit性能与ADCToolbox.md；Obsidian_docs/assets/idle_performance/static_idle.png、spectrum_idle.png；scripts/sar8_idle_performance/note_figures.py；本计划；plan/log.md 追加段。
- 远端 OA：none。无远端操作、无新仿真、无基线变更。
- 只读依赖：verification/sar8_idle_performance/results.json、toolbox_panel.json、toolbox_time_fit.json，已有图像与工程报告，以及全部电路、PDK、标准库、历史结果。
- 步骤：从 candidate 数值重绘静态/频谱图；改写笔记为单版本结果；保留测试条件、日期、版本归属、相位与残差定义以及验证范围。
- 验证：运行绘图脚本、目视检查新图；检查嵌入图片与本地链接存在、关键指标一致、正文无 R4 对照；git diff --check 与完整目标 diff 审阅。
- 提交策略：不 commit、不 push，不改正在执行的 A/B 仿真。
- 状态：完成。笔记删除全部 R4 对照，十二图说明压缩为表格；历史指标与版本日期保留。两张单版本图已生成并目视检查，5 个图片嵌入及本地数据链接均存在，关键静态数值已核对源 JSON。
- 验证结果：脚本实际执行成功；目标 diff 审阅通过。全仓 git diff --check 发现原有非本次文件 Obsidian_docs/Report/Wrap-up & Experience.md:13 尾随空格，未修改该文件；本次范围单独检查通过。无远端修改、无新仿真、无提交。

## 后续：ADCToolbox 总览图

- 用户要求新增原生 plot_dnl_inl 绘制的 ±1 LSB 总览，保留放大图并标明边界搜索方法与分辨率。
- 扩展所有权：Obsidian_docs/assets/idle_performance/static_idle_overview.png；沿用本计划脚本、笔记及日志范围。
- 笔记在前次完成后有用户精简与格式调整，本次保留这些修改，仅插入总览和方法说明，不恢复已删段落。
- 从同一 candidate 数组直接调用工具箱绘图函数，不运行直方图分析；独立 code/transition 横轴，保留原 DNL/INL 归一化。
- 验证：脚本运行、图像目视、纵轴 ±1 与数组一致性断言、图片链接存在和 scoped diff --check。无新仿真、不提交。
- 状态：完成。项目虚拟环境实际调用工具箱绘图成功，±1 LSB 纵轴及原数组一致性断言通过；新图目视检查通过，笔记 6 个图片嵌入存在，scoped diff --check 通过。保留用户精简及旧放大图，未重新生成旧图。

## 后续：从原始正弦输出码重新分析

- 用户要求实际用 ADCToolbox 重算。新增所有权：scripts/sar8_idle_performance/reanalyze_static.py；verification/sar8_idle_performance/reanalysis_20261028.json；Obsidian_docs/assets/idle_performance/static_sine_reanalysis.png。
- 从历史 candidate.dynamic_frames 的 1024 个整数输出码调用 analyze_inl_from_sine(num_bits=8, clip_percent=0.01)，保存完整输出、样本覆盖、输入及工具实现 SHA256。既有边界搜索数据不伪装为均匀斜坡。
- 对相同采样长度和相干频率的理想量化器做单独合成对照（拟合输出正弦幅相，仅用于检查方法有限样本误差，不是电路证据）。
- 将笔记总览替换为真实重算结果，保留边界搜索放大图及原指标，明确正弦样本不足、非全码覆盖和分析口径区别；不把短记录估计值宣称为正式全码静态指标。
- 验证：真实整数码数量/哈希、计算函数实际执行、数值及覆盖检查、图像目视、链接与 scoped diff --check。无新远端仿真，无 commit/push。
- 状态：完成历史正弦记录重算及笔记更新。1024 个实际码、230 个观察码（13–242），工具箱返回轴 15–238；DNL −0.3132305～0.2749805 LSB，INL 最大绝对值 0.170241 LSB。同长度理想量化器合成对照也有类似估计起伏，故保留短记录诊断属性，不替代全码静态结论。源哈希、样本数、链接、图像与 scoped diff 检查通过；独立慢斜坡采集尚未运行。
