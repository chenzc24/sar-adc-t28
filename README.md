# SAR ADC T28

8-bit、10 MS/s、全差分 SAR ADC 的设计与验证工作区。入口更新于 **2026-10-27（北京时间）**。

从[文档索引](docs/README.md)查看各设计分支、实验和历史报告。各分支的测试条件、
OA 对应关系及验收范围分别记录；本次整理没有采用新基线。

| 入口 | 范围与状态 |
| --- | --- |
| [手搭 ADC 网表验证](verification/manual_adc/README.md) | `SAR_ADC_T28_manual` 独立候选；四帧闭环功能已测，完整性能和电气验收未完成 |
| [手搭 ADC 端压与延时复核](verification/manual_adc/stress_diagnosis/README.md) | 标准单元应力尚未修复；RC 合龙结果仅属于该诊断候选 |
| [模块审计计划](plan/2026-10-25-sar8-module-audit/plan.md) | 原 SAR8 采样、比较器、参考和控制的分项诊断，保留未解决问题 |
| [项目管理](management/README.md) / [登记快照](management/STATUS.md) | 源文件、运行及 OA 清单；快照观察日期为 2026-10-25，不能当作实时状态 |
| [中文笔记](Obsidian_docs/Rvision/Head.md) | 沿用用户已调整的 Obsidian 目录 |

手搭 ADC、模块审计和独立 10 位实验包含本地未提交文件；上表描述本地工作区，
Git 提交状态见 `git status`，不表示这些文件已经发布。

仓库位于 `E:\bridge-Agent-T28\projects\sar-adc-t28`。原项目 OA 库为 `SAR_ADC_T28`，
手搭项目为独立的 `SAR_ADC_T28_manual`；PDK/共享库和用户未保存窗口均为受保护输入。
OA 必须通过支持的 Virtuoso/Bridge API 操作。

- `config/`、`models/`、`netlist/`、`scripts/`：规格、源模型、受控网表和自动化。
- `verification/`：实验定义与精选证据；`output/`：生成物与下载证据，逐案例决定保留。
- `docs/`：工程文档；`Obsidian_docs/`：人工笔记；`plan/`：任务计划和事实日志。
- 新仿真通过 `scripts/management/project.py` 的 register/submit/run-status/analyze/collect 流程。
  使用方法及资源预算见[管理说明](management/README.md#统一仿真与回收)。

整理规则、当前占用及清理回执见[2026-10-27 清理记录](management/cleanup/2026-10-27/review.md)。
旧的[根目录总览](docs/archive/2026-10-27/root-readme.md)和
[进度长页](docs/archive/2026-10-27/project_status.md)已归档，保留原阶段事实。
详细工程报告、输入、波形、失败证据及未解决计划保留原路径。

每个任务遵守 [AGENTS.md](AGENTS.md) 的计划、验证、日志和提交约定。
