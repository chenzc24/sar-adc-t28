# 运行与监测

VA/Python 行为视图使用 `python -m tools.saradc behav generate` 同步总规格，`behav check` 做数值交叉，`behav sim --run-id sar8-modules-v3` 提交模块与混合层次原生验证；`behav follow --run-id ID` 一次性等待该运行完成后分析、回收，失败不自动重跑。详细范围见 [行为模型](../design/behav/README.md)。已登记的 ID 绑定冻结输入，修改源后使用新 ID。

在项目根目录使用 `.venv/Scripts/python.exe -m tools.saradc`。执行器沿用已验证的 managed 机制：唯一运行身份、冻结输入、资源排队、独立分析和有散列的回收。

当前最简参考版采用独立短测入口（不套用 B 的内部捕获计数）：

```powershell
.venv/Scripts/python.exe -m tools.saradc.reference_short prepare --version minimal --corner tt --revision current-v1
```

下面保留历史 B 回归示例；普通 `prepare` 负责打包当前选择，但旧用例分析器不会自动适配最简参考状态机，当前原生整机短测应使用上面的 `reference_short` 入口。

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m tools.saradc prepare tt_short --view frozen-b --run-id sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc sim tt_short --view frozen-b --run-id sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc status sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc analyze sar8-frozen-short-v1 --queue
.venv/Scripts/python.exe -m tools.saradc collect sar8-frozen-short-v1
```

日常默认 `--view current`，打包实际 `design/dut.scs` 及其当前子模块；`--view frozen-b` 明确选择冻结 B 回归。`check` 校验当前端口和冻结来源，单列当前实现与冻结 B 是否相同，允许在日常设计中修改声明过的模块实现。

混合视图由 [specs/views.json](../specs/views.json) 选择。目前支持 `tt_short --view behavioral|comparator_xtor|cdac_xtor|sampler_xtor|control_xtor`；其余用例继续使用当前管级设计或显式冻结回归。混合短测使用公开端口观察器，不套用依赖管级内部节点的历史分析器，不把行为模型当作原生 MC 或端压验证。

现在也支持逐模块覆盖及物理候选：

```powershell
python -m tools.saradc prepare tt_short --view current --view reference=va --view comparator=va --view timing=va --run-id NEW_ID
python -m tools.saradc prepare tt_short --view behavioral --view sar=xtor --view timing=xtor --candidate sar=b --run-id OTHER_ID
python -m tools.saradc block list
python -m tools.saradc block sim --module cdac --run-id NEW_BLOCK_ID
python -m tools.saradc block follow --run-id NEW_BLOCK_ID
python -m tools.saradc draw --check
```

原理图使用源网表内的 RNL 注释。`draw` 生成展示，`draw --serve` 打开本机官方查看器服务；这两项不提交仿真。编辑与导出见 [RNL 原理图](schematics/README.md)。

六项选择为 `sampler / cdac / comparator / sar / reference / timing`，每项可选 `xtor` 或 `va`。不修改源网表的拓扑连接；RC/clear 模型使用明确的非对称上升/下降延时。候选为 VA 时拒绝同时指定该模块的物理候选。冻结回归拒绝模块覆盖。完整说明见 [独立模块测试](../tb/blocks/README.md) 和 [候选约定](../design/xtor/README.md)。

Virtuoso 沿用工作区已经接入的 bridge/ADE 环境。本次不重建连接、不修改 OA；相同模块选择通过生成的 Spectre/VA 网表实现。连接可用与 OA 是否同步当前文本设计分别记录。

`sim` 登记后提交一次仿真，分析与回收显式执行。相同 ID 的不同输入会被拒绝；网络不确定时先查询该 ID，不改 ID 重提。运行记录和冻结包在 `work/state/runs/` 与 `work/output/managed_execution/`。

```powershell
.venv/Scripts/python.exe -m tools.saradc observe modules
.venv/Scripts/python.exe -m tools.saradc observe cold
.venv/Scripts/python.exe -m tools.saradc observe refs
.venv/Scripts/python.exe -m tools.saradc checkpoint
.venv/Scripts/python.exe -m tools.saradc module-results
```

监测器通过原有 launch 回执连接现有只读数据库，游标保存在 `work/state/timing_mc/`。远端 refs 队列继续执行已有任务，旧 cold 控制器 held 记录保持历史身份。目录整理不重新登记这些任务。

本机配置由 `site.local.yaml` 保管，配置结构参考 [site.example.yaml](../site.example.yaml)。当前远端 T28 适配器保留原账户、服务器工作区与 PDK 限制；7 个重任务槽，单个既有案例 4 线程，仿真 1 GiB、分析 256 MiB、回收 32 MiB；实际准入还检查服务器资源。

分析器接口为 `--run-dir DIR --output-dir DIR`，analysis-only 额外绑定实际完成源。原始波形留在服务器，正常回收仅取小结果。

最简参考候选的五点逐管端压采集入口为 `python -m tools.saradc.soa prepare|submit --corner tt|ssc|ssh|ffc|ffh --revision NEW_ID`，固定提交到 `thu-song`。它读取既有最简版短测的冻结输入，保持电路和 18 帧激励不变，增加全部 MOS 端点保存；可显式用 `--maxstep-ps` 收紧时间步长。标准库只读，保存端点清单及库文件散列，不复制库参数进仓库。运行仍由 managed 执行器控制，完成后 `analyze ID --queue`、`collect ID`。

该分析读取 [端压工程规则](../specs/soa_rule.yaml)，对原生波形作分段线性阈值交点和滑动窗口累计时间测量，输出 `derived/terminal_results.json` 与 `derived/result.json`。全端点缺失或未分类模型会导致分析失败；数值通过先标为待时间分辨率复核。原始 CMI/LTE 告警保留。退出成功、18 帧码字正确与端压通过分开报告。

同一 managed 执行器支持 `thu-wei`、`thu-sui` 与 `thu-song`。新登记可用 `engine().register(recipe, host='thu-song')` 选择服务器；初始化用 `engine().storage(host='thu-song')`。运行记录绑定主机，后续查询、分析、回收自动路由；无主机字段的历史记录归属 `thu-wei`。不得通过修改默认服务器迁移已有运行。

这些服务器的 `/home` 用户目录及 PDK 为共享 NFS，`/server_local_ssd` 为各自本地磁盘。队列锁和资源检查按主机执行；转移未完成实验时保留原运行，用新 ID 登记目的主机，记录对应关系并先停止原任务，避免重复运行。停止接口仅处理经启动时间、进程组、账户和命令确认的对应 worker/child，保留原始日志与取消原因。
