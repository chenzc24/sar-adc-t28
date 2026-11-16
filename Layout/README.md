# SAR8 Layout

从整机规划开始，再做模块 placement/routing，最后完成顶层互联和同源物理、电气验证。当前只实现了 **CDAC 版图候选**；整机 floorplan 是尚未写入 OA 的初步规划。

| 当前信息 | 唯一入口 |
| --- | --- |
| 实际电气设计 | [前端 manifest](../design/manifest.json)，Layout 不另维护一份电路 |
| 物理源、OA 所有权和恢复点 | [design/manifest.json](design/manifest.json) |
| 整机 placement 意图 | [design/floorplan.json](design/floorplan.json) → [预览](results/floorplan.svg)、[面积](results/area.json) |
| 模块端口、朝向、互联优先级 | [specs/interfaces.json](specs/interfaces.json) |
| 匹配、填充、时序和验收边界 | [specs/constraints.json](specs/constraints.json) |
| 当前证据和未完成项 | [results/current.json](results/current.json) |
| 操作、原处迭代和回滚 | [docs/workflow.md](docs/workflow.md) |
| OA 实例、引脚、图形和坐标查询 | [docs/layout-query.md](docs/layout-query.md) |

初步核心框为 **176 × 170 µm，0.02992 mm²**。其中只有 CDAC 的 **90.33 × 92.49 µm** 来自现有 OA；比较器、采样、参考和 SAR 的数字是空间预留，尚未证明能放下全部器件。未分配部分预留给走线、电源、隔离和边界。Die、IO ring、保护结构面积未定，不以此估计最终芯片面积。关键寄生、布线层和路由时序预算仍待原生读回及电气分配。

所有工作 layout 使用一个 `SAR_ADC_T28_LAYOUT` Library，位于 `llm_IO` 下，实际主机/路径只在本机 `site.local.yaml:layout` 配置。

| 打开哪个 cell | 用途 |
| --- | --- |
| `sar8j_r1_cdac_core/layout` | 功能连接、placement、routing；保留匹配 dummy、功能屏蔽与器件，不带密度填充 |
| `sar8j_r1_cdac/layout` | 引用同一 XCORE，加 FILL_ODPO/FILL_METAL，进行完整物理验证及 PEX |

工作 cell 不按版本复制。当前 OA 含已接受的修改，默认验证现有 OA，**禁止直接用旧生成器覆盖**；源码重建能力尚未重新认证。完整顶层的38端口保持不变；当前外部参考为 `minimal_msb_d2`、SAR 为 `reset_data_or`，不假设旧非交叠逻辑仍适用。

```text
Layout/
├─ README.md
├─ __main__.py              # python -m Layout
├─ project.py               # site 配置、历史/当前证据解析
├─ planning.py              # 规划检查及派生视图
├─ design/                  # manifest、floorplan、CDAC 生成器和 SKILL
├─ specs/                   # 接口、约束和验收范围
├─ tb/                      # MOM fixture、独立 CDL 参考
├─ tools/
│  ├─ deploy.py
│  ├─ physical/             # 原生 OA/GDS/DRC/LVS/PEX 执行器
│  ├─ simulation/           # managed 后仿/诊断打包
│  └─ analysis/             # 测量、比较和寄生统计
├─ results/                 # 当前索引、规划图、精简证据及历史结果
└─ docs/                    # 工作流、原 MOM 实验范围
```

远端职责为 `layout/runtime/`（当前部署）、`layout/state/`（回执/状态）、`layout/evidence/<运行ID>/`（冻结输入及结果）。OA 仍留在共享 home 的统一库，Spectre 仍走既有 managed `runs/`。原 `layout-mom-pilot/evidence/` 保持原址查阅；新旧入口共享旧锁。运行 ID 是证据身份，不是另一个工作版图版本。

从仓库根目录运行：

```powershell
.venv/Scripts/python.exe -m Layout check
.venv/Scripts/python.exe -m Layout render
.venv/Scripts/python.exe -m Layout generate
.venv/Scripts/python.exe -m Layout deploy
.venv/Scripts/python.exe -m Layout physical UNIQUE_ID --through pex
.venv/Scripts/python.exe -m Layout status UNIQUE_ID
.venv/Scripts/python.exe -m Layout prepare-tt PHYSICAL_ID TT_RUN_ID
```

`generate` 仅在 `work/` 生成输入；`prepare-tt` 仅打包，登记、执行、分析和回收使用[既有仿真入口](../docs/simulation.md)。不得重复使用已执行身份。迁移实际结果见 [workflow_migration.json](results/workflow_migration.json)。

**2026-11-16 迁移验收通过：**同一 OA 的几何哈希、LVS 连接和规则身份一致；DRC 保留原两条 warning。迁移前后当前参考/SAR配置的十帧码字、握手计数和判定一致，最大转换时间差约 0.074 ps（对照容差10 ps）。两组都存在 12→0、243→255 的码字失败；采样沿与握手时序通过，精确模拟建立和端压未获资格。原始日志、冻结输入与测量已[归档](../results/storage/layout_migration_archive_20261116.json)，大波形因后续 CDAC 定位保留。

CDAC 历史后仿的约 **15.12% 幅度损失与两处错码仍未修复**。它们来自历史 B 配置，不能当作当前参考/SAR 的新测量。寄生分组证据显示金属与 OD/PO 填充约占新增 TOP 固定负载的61%/39%；见[CDAC 结果](results/cdac.md)。本次整理不改变几何或宣称性能修复；LVS、DRC warning、功能、建立和端压分开报告。

[库迁移](results/library_migration.json) · [核心/填充管理](results/core_fill_management.json) · [历史目录整理](results/organization.json) · [MOM 实验](docs/pilot-spec.md) · [当前需求 Issue #3](https://github.com/chenzc24/sar-adc-t28/issues/3)
