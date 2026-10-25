# 项目管理状态

统一登记本地源文件、远端仿真目录和 Virtuoso 单元。各端观察时间分别记录；清单不代替设计验收。

| 范围 | 已登记 | 观察时间 北京时间 |
| --- | ---: | --- |
| 本地源文件记录 | 1397 | 2026-10-25 15:50:40 |
| 本地生成物目录 | 116 | 同上 |
| 历史运行元数据记录 | 190 | 同上 |
| 远端精确引用路径 | 274 | 2026-10-25 15:47:04 |
| Virtuoso 实际单元 | 247 | 2026-10-25 10:56:43 |

OA 观察方式：`live_bridge_DD_metadata`。

## 当前设计登记

| 版本 | 定位 | OA 对应情况 |
| --- | --- | --- |
| `sar8_r3_b_reference` | preserved_OA_reference | SAR_ADC_T28/sar_adc8_join_r3/schematic |
| `sar8_r4_original` | preserved_transistor_performance_reference | SAR_ADC_T28/sar_adc8_join_r4/schematic |
| `sar8_idle_reset` | tested_netlist_candidate | 网表候选或独立实验，未登记为已同步 OA |
| `sar8_l90_mmain2_stress_screen` | active_netlist_development | 网表候选或独立实验，未登记为已同步 OA |
| `independent_cdac10_dualrail` | independent_user_experiment_read_only | 网表候选或独立实验，未登记为已同步 OA |

版本采用情况与各项验证结论见 [designs.yaml](designs.yaml)。没有因本次盘点提升任何基线。

## 需要处理的差异

| 项目 | 数量 |
| --- | ---: |
| 旧 manifest 漏登的实际 cell | 119 |
| 历史入口非系统级隔离；新任务必须走统一入口 | 1 |
| 旧登记存在但当前库未找到 | 15 |
| 本地已删除的受控文件 | 3 |
| 当前未找到的历史远端路径 | 144 |
| 尚未关联实验的浅层目录 | 25 |

历史远端路径未找到不等于仿真失败；用户已删除或重组的笔记原样保留。
浅层发现的未关联目录先登记，不自动认领或清理。远端路径可能互相包含，体积不可直接相加。

## 清单入口

- [本地文件](inventory/local_files.csv)：Git 状态、用途、大小、散列；不包含环境和大型原始波形。
- [本地输出](inventory/local_outputs.csv)：只统计文件元数据，不解析波形。
- [服务器目录](inventory/remote_directories.csv)：存在性、体积、运行引用和退出码。
- [Virtuoso 单元清单](inventory/oa_cells.md)、[机器登记](cells.yaml)：实际 view、旧登记用途和存在性差异。
- [单元表格](inventory/oa_cells.csv)、[R3/R4依赖](inventory/dependencies.yaml)。
- [实验索引](runs/index.yaml)：本地案例与远端路径的关联；当前四组另有输入清单。
- [完整差异](inventory/issues.yaml)、[资源与权责](project.yaml)、[使用说明](README.md)。

## 统一执行入口

新任务使用 `scripts/management/project.py` 的 register / submit / run-status / analyze / collect。
服务器 SSD 根目录与资源策略见 [执行说明](README.md#统一仿真与回收)。历史清理由独立审核清单和回执管理。

| Managed run | 本地最后观察 | 远端目录 |
| --- | --- | --- |
| `sar8fix-c1r4-ffcold` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-c1r4-ffcold` |
| `sar8fix-hyblong-sscold` | complete / not_started | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-hyblong-sscold` |
| `sar8fix-hybscreen-sscold` | 未查询 / 未查询 | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-hybscreen-sscold` |
| `sar8fix-ioscreen-ffcold` | 未查询 / 未查询 | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-ioscreen-ffcold` |
| `sar8fix-ioscreen-ffhot` | complete / not_started | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-ioscreen-ffhot` |
| `sar8fix-ioscreen-sscold` | complete / not_started | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-ioscreen-sscold` |
| `sar8fix-ioscreen-sshot` | 未查询 / 未查询 | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-ioscreen-sshot` |
| `sar8fix-ioscreen-tt` | 未查询 / 未查询 | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-ioscreen-tt` |
| `sar8fix-natlong-ffcold` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natlong-ffcold` |
| `sar8fix-natlong-ffhot` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natlong-ffhot` |
| `sar8fix-natlong-sscold` | complete / not_started | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natlong-sscold` |
| `sar8fix-natlong-sshot` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natlong-sshot` |
| `sar8fix-natlong-tt` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natlong-tt` |
| `sar8fix-natscreen-sscold` | complete / not_started | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-natscreen-sscold` |
| `workflow-rc-20261025-final` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/workflow-rc-20261025-final` |
| `workflow-rc-20261025` | complete / complete | `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/workflow-rc-20261025` |

本地最后观察不保证实时；`run-status RUN_ID` 才会查询服务器。

## 已批准历史清理

[执行回执与 home 检查](cleanup/2026-10-25/execution.md)：本地35.074 GiB、服务器10.913 GiB重复副本已清理；10份服务器原始波形保留。home未删。
