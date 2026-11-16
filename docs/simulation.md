# 运行与监测

实验收尾、提交大批任务或释放磁盘时，执行[波形归档与清理](waveform-retention.md)：归档测量与图表所需证据后可按清单删除原始大波形。现有 managed 执行器不会自动删除。

45 点扩展由 `python -m tools.saradc.pvt_short --revision NEW_ID` 准备，按 `specs/pvt_short.json` 排除原五点，冻结当前 OR 版的其余 40 个角。每角 10 个中心码、1.059 µs、10 ps 最大步长、4 线程、4 GiB 输出预算；仅保存真实接口和时序测量信号，不据此判断完整逐管端压。参考固定 0/0.9 V，无源模型固定 TT，没有独立 1.8 V 供电轨。

`tools/saradc/managed/batch_follow.py` 是有限批次的服务器调度器，读取已登记 run ID 与 recipe hash，沿用 managed 准入、仿真和分析接口，自动接续分析；同批次有唯一控制器锁。失败或结果不确定的任务保留并标记待核对，不自动重提，其余工况继续。调度器不删波形，完整结果回收和归档后按清理规则另行处理。

VA/Python 行为视图使用 `python -m tools.saradc behav generate` 同步总规格，`behav check` 做数值交叉，`behav sim --run-id sar8-modules-v3` 提交模块与混合层次原生验证；`behav follow --run-id ID` 一次性等待该运行完成后分析、回收，失败不自动重跑。详细范围见 [行为模型](../design/behav/README.md)。已登记的 ID 绑定冻结输入，修改源后使用新 ID。

在项目根目录使用 `.venv/Scripts/python.exe -m tools.saradc`。执行器沿用已验证的 managed 机制：唯一运行身份、冻结输入、资源排队、独立分析和有散列的回收。

当前最简参考版采用独立短测入口（不套用 B 的内部捕获计数）：

```powershell
.venv/Scripts/python.exe -m tools.saradc.reference_short prepare --version current --corner tt --revision current-v1
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

同一冻结激励的单变量候选可显式加 `--candidate reference=NAME`（也支持其他已登记模块）。该入口按模块接口绑定历史包中的实际文件，记录替换前后散列并重建端点清单；默认设计不随实验改变。功能分析器 `reference_short.py` 支持 managed 的 `--source-run-dir`，可对已完成的全端点运行作独立 analysis-only 时序复核。

同一 managed 执行器支持 `thu-wei`、`thu-sui` 与 `thu-song`。新登记可用 `engine().register(recipe, host='thu-song')` 选择服务器；初始化用 `engine().storage(host='thu-song')`。运行记录绑定主机，后续查询、分析、回收自动路由；无主机字段的历史记录归属 `thu-wei`。不得通过修改默认服务器迁移已有运行。

这些服务器的 `/home` 用户目录及 PDK 为共享 NFS，`/server_local_ssd` 为各自本地磁盘。队列锁和资源检查按主机执行；转移未完成实验时保留原运行，用新 ID 登记目的主机，记录对应关系并先停止原任务，避免重复运行。停止接口仅处理经启动时间、进程组、账户和命令确认的对应 worker/child，保留原始日志与取消原因。

当前 OR 版含噪声动态测试用 `python -m tools.saradc.noise_fft --run-id NEW_ID` 准备；`--pilot` 生成 8 帧的观察器/协议预检（2 MHz 噪声着色低频拐点，非正式频谱），完整包为 8 帧预热＋连续 1024 帧（10 kHz–2 GHz 配置、noise seed 101）。新观察器不依赖已移除的参考捕获时钟，原生波形解码与 VA 输出码交叉检查。`managed/noise_fft_follow.py` 读取两个已登记身份的冻结清单，预检通过后提交完整运行并自动接续分析；不自动重试、不拼接、不删波形。实际启动见[记录](../results/noise/resetor_1024_launch_20261115.md)。

整机全局＋局部 MC 的准备入口为 `python -m tools.saradc.mc_short --revision NEW_ID`，固定三组电压/温度、各 12 种子、每种子 10 点。`managed/mc_short_follow.py` 消费已登记的精确身份，每组前两个样本通过后自动补齐；原生参数文件核对实际随机覆盖，码字偏移与时序错误分开。已有批次从检查点查询，不重复运行准备/提交命令。当前批次和 analysis-only 源复用见[启动记录](../results/mc/resetor_global_local_launch_20261115.md)。
