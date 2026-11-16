# Layout 工作流

电气设计以[前端 manifest](../../design/manifest.json)为准，物理规划及所有权以[Layout manifest](../design/manifest.json)为准。迁移验证组织及输入等价，CDAC 性能修复另做。

## 从整机到模块再回整机

1. 更新 [floorplan](../design/floorplan.json)、[接口](../specs/interfaces.json)和[约束](../specs/constraints.json)：确定核心、模块位置/朝向、信号出口、电源/隔离/走线空间，区分实测尺寸与预留。
2. `python -m Layout check` 检查当前电气身份、端口顺序、实例覆盖、边界和重叠；`render` 生成集中规划图及面积表。未分配的寄生/时序预算保持空值。
3. 逐模块做器件匹配 placement、原生 PCell/标准单元参数读回和内部 routing。功能编辑落在固定 core cell，保留功能 dummy、body contact、guard 和屏蔽。
4. 模块完成局部 DRC/LVS、prefill PEX 和接口测量后，用实测 bbox、负载和时序反馈整体规划。当前只有 CDAC 已有物理实现，其他模块未完成此步骤。
5. 完成顶层连接、电源与隔离；统一分配填充归属，避免模块与顶层重复填充。最终 filled PEX 和整机后仿使用同一 GDS/规则/输入身份。

当前图是初步空间安排。新走线层、via、guard ring 和数值寄生预算须先由 native pin access、PDK 规则及电气预算确定，不能仅凭示意图决定。

查询 OA 实例、引脚、图形或坐标变换时，先读[版图查询说明](layout-query.md)，复用已有 bridge 接口；查询示例和使用约定统一维护在该页。

## 本地与远端

本地职责见[入口](../README.md)。生成输入、私有回收、运行配方、迁移检查点在忽略的 `work/layout/`、`work/decks/`、`work/output/`；不修改已冻结输入。

配置使用 `site.local.yaml:layout`，示例在 [site.example.yaml](../../site.example.yaml)。部署器核对主机、账户所有权和实际路径，沿用旧 `layout.lock`；运行器核对配置和执行目录。新目录只有：

```text
<configured remote_root>/
├─ runtime/        # 当前脚本、SKILL/CDL、workspace.json、cds.lib
├─ state/          # 提交防重回执、检查点、驱动日志
└─ evidence/<id>/  # 该次 native 输入、GDS、manifest、原始报告
```

OA 路径独立配置，保持 `llm_IO/SAR_ADC_T28_LAYOUT`，不复制进执行树。旧证据原址解析，新旧同名 ID 报歧义；历史失败、告警、路径不改写。部署及原生操作共用锁，不修改正在执行任务的 runtime。旧脚本仅作历史留存，日常不直接调用。

## 执行现有 CDAC 验证

在项目根使用 `.venv/Scripts/python.exe`；下面的 ID 均应是未使用的新证据身份：

```powershell
python -m Layout check
python -m Layout generate
python -m Layout deploy
python -m Layout physical UNIQUE_PHYSICAL_ID --through pex
python -m Layout status UNIQUE_PHYSICAL_ID
python -m Layout prepare-tt UNIQUE_PHYSICAL_ID UNIQUE_TT_ID
python -m tools.saradc register work/decks/UNIQUE_TT_ID/recipe.json
python tools/saradc/managed/execution.py submit UNIQUE_TT_ID --queue
python -m tools.saradc analyze UNIQUE_TT_ID --queue
python -m tools.saradc collect UNIQUE_TT_ID
```

`physical` 只验证现有 OA。它在启动前创建不可覆盖的提交回执，已有目录或回执均拒绝重提；网络返回不确定时先查该 ID 和 `state/<id>.driver`。失败要定位实际阶段，不靠换 ID 重复运行。原生流程保留 DRC marker、LVS 结论、同源 GDS/PEX 散列、退出码和告警；脚本成功不代表 DRC clean。Spectre 准入由既有 managed 执行策略控制。

`prepare-tt` 仅把 CDAC 换成实际 PEX，保留当前参考/SAR和原十帧激励。其余模块是前仿，不能称整机后仿签核。分布 PEX 的内部 bottom plate/支路电流与原理图命名不一致，当前分析器将相关建立/重叠电流项标为缺测，仍测码字、采样沿、握手、转换时间。无超时不代表精确模拟建立合格。旧 B 对照分析器 `Layout.tools.analysis.compare_integrated` 不用于当前参考版。

单位/三颗 MOM 入口为 `Layout.tools.simulation.prepare_sim`，完整 CDAC 独立阶跃为 `prepare_full_sim`；输入见 [tb](../tb/)。独立阶跃以 TOP=0.45V 初态测位权与0.1%建立，不替代整机性能。

## 结果适用性

[current.json](../results/current.json)关联规划、物理证据、TT 运行及限制。`check` 对比电气源与规划依赖散列；源变化报告失效，不静默重新绑定。`render` 只刷新规划投影，不更新旧资格证据的依赖散列。实时 OA 不能由本地哈希证明，改图后须重新 stream/native 验证。

功能核心变化会影响 fill、PEX 和后仿；填充变化影响密度与寄生；顶层 routing 变化影响顶层提取与电气证据。原结果保留为历史。DRC、LVS、功能、时序、寄生和端压分别记录。初步 floorplan 的未定预算不算通过。

## 恢复与同版迭代

源码原处修改，Git 保存已提交历史；本次开始时 Layout 尚未跟踪，真实恢复点是 `work/layout/restructure/source-before.zip` 和 `checkpoint.json`，不能声称已有 Git 历史保护。迁移映射在同目录 `relocation.json`。不覆盖原恢复点。

OA 不由 Git 管理。已有 native 备份记录在 [manifest](../design/manifest.json)；它是核心/填充分层之前的备份，不能冒充此后修改的快照。每次后续写 OA 前确认打开/未保存 view 和编辑者，保存受支持的 OA 检查点及 cell/GDS 身份；只恢复授权工作 cell，不覆盖同库其他模块或用户未保存修改。恢复后重新核对几何、端口及必要 DRC/LVS。

当前采用 `oa_owned_current`，默认 `allow_regeneration: false`。手工修改记录为 OA 所有，不承诺旧生成器完整重建。接受手工改动后，将其纳入 patch/参数并验证重建，或继续使用已检查的 OA checkpoint。完整 batch SKILL 含 `exit(0)`，不得载入交互 CIW。库及 cell 名不为每次改动新增版本。

填充分组诊断仍可用 `run_physical.py ... --source-stream ID --omit-fill metal|odpo`，它只修改运行内 stream，不改 OA；需要完整 DRC/LVS/PEX，保留密度失败，不能把诊断 stream 当工作版本。寄生数值分析须绑定真实完成源，经 managed analysis-only 执行。
