# 运行与监测

VA/Python 行为视图使用 `python -m tools.saradc behav generate` 同步总规格，`behav check` 做本地交叉，`behav sim --run-id sar8-behav-cross-v1` 提交原生 Spectre 验证。详细范围见 [行为模型](../design/behav/README.md)。

在项目根目录使用 `.venv/Scripts/python.exe -m tools.saradc`。执行器沿用已验证的 managed 机制：唯一运行身份、冻结输入、资源排队、独立分析和有散列的回收。

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m tools.saradc prepare tt_short --split-design --run-id sar8-tree-tt-short-v1
.venv/Scripts/python.exe -m tools.saradc sim tt_short --split-design --run-id sar8-tree-tt-short-v1
.venv/Scripts/python.exe -m tools.saradc status sar8-tree-tt-short-v1
.venv/Scripts/python.exe -m tools.saradc analyze sar8-tree-tt-short-v1 --queue
.venv/Scripts/python.exe -m tools.saradc collect sar8-tree-tt-short-v1
```

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
