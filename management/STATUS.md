# 项目管理状态

统一登记本地源文件、远端仿真目录和 Virtuoso 单元。各端观察时间分别记录；清单不代替设计验收。

| 范围 | 已登记 | 观察时间 北京时间 |
| --- | ---: | --- |
| 本地源文件记录 | 1207 | 2026-10-25 11:00:38 |
| 本地生成物目录 | 115 | 同上 |
| 历史运行元数据记录 | 188 | 同上 |
| 远端精确引用路径 | 256 | 2026-10-25 10:56:25 |
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
| 旧登记存在但当前库未找到 | 15 |
| 本地已删除的受控文件 | 3 |
| 新 SSD 运行根目录待配置 | 1 |
| 当前未找到的历史远端路径 | 144 |
| 尚未关联实验的浅层目录 | 25 |
| 旧提交器尚未执行统一资源策略 | 1 |

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

当前实现覆盖盘点、登记和检查。统一提交/收集执行器与 SSD 运行根目录配置仍待后续落实。
