# 项目管理入口

从 [当前状态](STATUS.md) 查看设计、文件、远端数据和待核对项。这里统一登记位置和证据，不搬动现有目录。

历史数据审核见 [2026年10月25日删减清单](cleanup/2026-10-25/review.md)：本地与服务器分开列明占用、实验和保留建议；尚未批准或执行删除。

## 各端职责

| 范围 | 真源与用途 | 维护方式 |
| --- | --- | --- |
| 本地 Git | 指标、模型、脚本、受控网表、实验输入、审核后的指标与图 | 按任务提交；用户笔记和独立实验分别保护 |
| Virtuoso OA | schematic、symbol、layout、Maestro 与技术库绑定 | 支持的 Virtuoso/Bridge API；登记精确 library/cell/view |
| 服务器运行目录 | 原生仿真、日志、raw 波形、分析临时文件 | 每次运行独立身份；先核对已有任务再重试 |
| 本地 output | 下载结果与可生成缓存 | 不作为 OA 真源；清理另立清单 |
| Obsidian | 审核后的说明、结果解释与复盘 | 引用设计与实验，不独立宣称版本已采用 |

服务器内存和磁盘空间分别管理。盘点只读取元数据，不加载原始波形。目录扫描结果可能互相包含，不能直接把所有行的字节数相加。

## 四类登记

- [project.yaml](project.yaml)：路径、权责、资源默认值及保留规则。
- [designs.yaml](designs.yaml)：R3/R4、空闲复位及当前尺寸/驱动实验的定位；网表候选与 OA 同步状态分别记录。
- [cells.yaml](cells.yaml)：当前 CIW 实际可见的 library、项目 cell/view 与旧登记差异。其他可见库只登记元数据，不盘点或修改其内容。
- [runs/index.yaml](runs/index.yaml)：历史运行的本地目录、元数据来源、远端位置和退出码观察。当前四组另有独立输入清单。

历史运行按本地案例相对路径生成稳定编号；同名案例属于不同实验时不会合并。一个案例可以关联原始路径、恢复路径和 raw 子目录，关联不等于它们是独立仿真，也不意味着所有尝试都成功。

技术库绑定、单元存在、网表对应、标称/PVT/过压/失配/版图结论分别登记。退出码为零只说明进程正常结束；旧回传失败记录与后来恢复成功的证据同时保留。

原 `virtuoso/cell_manifest.yaml` 作为旧工具兼容和历史描述输入保留；现状以这里带观察时间的实际读回为准。R3/R4 的逐层依赖单列，当前开发网表仍需另外验证与 OA 的对应关系。

## 查看和更新

在项目根目录执行，状态查询不会发起仿真或刷新远端：

```powershell
.venv/Scripts/python.exe scripts/management/project.py status
.venv/Scripts/python.exe scripts/management/project.py cells
.venv/Scripts/python.exe scripts/management/project.py check
```

按需要刷新某一端：

```powershell
.venv/Scripts/python.exe scripts/management/project.py inventory --scope local
.venv/Scripts/python.exe scripts/management/project.py inventory --scope server
E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/management/project.py inventory --scope oa
E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/management/project.py inventory --scope dependencies
```

本地清单包括 Git 跟踪及未忽略文件；环境和生成物另列。缺失的受控文件仍保留记录，避免覆盖用户主动删除或重组的笔记。清单本身不递归生成自身散列。

服务器清点限定在已有运行记录引用的位置和已知工作区的浅层目录；单进程、降低调度优先级、限制内存与扫描时间，不读取 raw 内容。未关联目录先保留，当前不存在的历史路径不自动判作失败或已删除。

OA 清点要求 Bridge/CIW 可用，并核对 `SAR_ADC_T28` 的路径和 `tsmcN28` 绑定。R3/R4 的依赖通过原理图 reader 读回；依赖图不代替网表等价或连接检查。

## 统一仿真与回收

新运行目录：`thu-wei:/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/<run_id>/`。
已核对账户、真实路径、本地 XFS 挂载和写入/读回；项目目录权限 `0700`。
这是运行暂存区，不是内存盘；管理员清理周期与备份承诺尚不明确，不能作为唯一归档。
OA、PDK、现有历史目录均未迁移，`SAR_ADC_T28_WORK` 仍未创建。

```text
本地受控输入 → register（冻结+SHA256） → submit（门禁/排队）
→ run-status → analyze（独占资源、流式处理） → collect（小结果+校验）
```

在项目根目录执行。示例已完成，重复提交只返回同一运行，不会重跑：

```powershell
.venv/Scripts/python.exe scripts/management/project.py register management/recipes/rc_smoke.yaml
.venv/Scripts/python.exe scripts/management/project.py submit workflow-rc-20261025-final --queue
.venv/Scripts/python.exe scripts/management/project.py run-status workflow-rc-20261025-final
.venv/Scripts/python.exe scripts/management/project.py analyze workflow-rc-20261025-final --queue
.venv/Scripts/python.exe scripts/management/project.py collect workflow-rc-20261025-final
```

每个新实验建独立 YAML 配方，明确 `run_id / design_id / entry / inputs / resources`，
并记录 PVT、电压、时序、模型 section、OA 对应状态和选存信号。
参考 [示例配方](recipes/rc_smoke.yaml) 与 [冻结记录](runs/workflow-rc-20261025-final.yaml)。
本地输入逐项列出，包含文件也需打包；PDK 只引用服务器路径，不复制内容。
同一 ID 不接受改动后的输入；失败或连接丢失先查原状态，不能自动换 ID 重跑。

默认分析器只输出所选瞬态信号的极值、首尾值、样本均值和完整性，逐行扫描 PSF ASCII，
不把整条波形读入内存。**样本均值不是时间加权均值；原生 PASS 不代表 ADC 性能合格。**
复杂 ADC 测量需打包专用流式分析器，接口为
`--run-dir DIR --output-dir DIR`，结果写 `derived/result.json`，仍受分析资源门禁约束。
服务器当前是 Python 2.7.5，专用远端分析器需兼容此运行时；ADCtoolbox 等 Python 3
分析放在本地小结果上运行，不把整份原始波形拉到本地再展开。

### 存放位置

| 内容 | 本地 | 服务器 |
| --- | --- | --- |
| 配方/版本/散列 | `management/recipes`、`management/runs/<id>.yaml` | `<id>/recipe.json`、`inputs/` |
| 原生日志与波形 | 默认不下载 raw | `<id>/spectre.out`、`raw/` |
| 分析小结果 | `output/managed_execution/runs/<id>/collected/` | `<id>/derived/` |
| 实时状态与资源回执 | 查询快照在 `output/managed_execution` | `<id>/{simulation,analysis}.state.json` 为权威 |
| 审核后的结论/图 | `verification`、`docs`、Obsidian | 不代替本地归档 |

`collect` 默认每次最多 32 MiB，不下载原始波形；逐文件 SHA256 校验。
超过预算的文件列在 `skipped`，不会暗中删减原件。结果变化另存散列版本，已有文件不覆盖。
回收中断可以重做 collect，不需重跑仿真；本地保留至少 2 GiB 余量。

历史运行也有只读小证据回收入口，不改变旧路径或覆盖原有本地结果：

```powershell
.venv/Scripts/python.exe scripts/management/project.py legacy-collect <legacy-id> --remote-index 0
```

ID 和远端路径序号见 [历史索引](runs/index.yaml)；多路径必须明确序号。
只收日志、退出码、原生 logStatus 和已知小回执；不自动重算或下载历史 raw。
新副本写到 `output/managed_execution/legacy/`，目录不存在会明确报错。

### 资源门禁

| 检查或限制 | 已执行规则 |
| --- | --- |
| 并发 | 仿真与重型分析共用独占锁，单组；Spectre 最多 4 线程 |
| 内存准入 | 主机 `MemAvailable ≥ 声明RSS预算 + 8 GiB`；用户 cgroup 余量另留 1 GiB |
| 换页/CPU | 检查实际换页速率、CPU 配额与负载；SwapFree 低不单独等同故障 |
| 磁盘准入 | SSD 空间 ≥ 声明输出预算 + 16 GiB；运行中另设 4 GiB 底线 |
| 运行中 | 每进程虚拟内存硬限、单文件上限；进程组 RSS/耗时/总输出量看门狗 |
| 调度 | nice +10、idle I/O；分析数值库默认单线程 |
| 已有工作 | 检测本账户 Spectre、已知流式分析器和托管遗留子进程；有冲突则拒绝或排队 |

`gate <id>` 只读检查。`submit/analyze --queue` 在后台等待，等待原因写入状态；
不加 `--queue` 时，未过门禁不会启动。队列超时、原生失败、分析失败分别记录，保留部分输出。
运行超限只终止本次托管的子进程组，核对 boot ID、PID 起始时刻和组号，不动旧进程。

限制：这是项目入口与采样式看门狗，不是管理员级 cgroup/磁盘配额，也不能约束任意 SSH
启动的程序。RSS/耗时约每 0.5 秒检查，磁盘约每 5 秒检查，瞬时超出可能先发生；其他用户
的资源变化也不受本工具控制。旧 staged/idle 新提交入口已关闭，其余历史脚本禁止用于新任务，
不是全部重写。已上传的旧任务保持原样。

### 验证与后续

[实测回执](../verification/managed_execution/validation.json)：服务器原生 RC 仿真、分析与两次回收通过；
双客户端同时提交只启动一个 worker；重复提交不重跑；超大内存预算在准入阶段被拒绝。
另有门禁、路径、PID 重用、散列传输和流式解析的定向测试。这里只验证管理链路，不提升 ADC 基线。

未审核运行、冻结基准及关键异常证据继续保护。本轮不清理历史数据；下一轮由用户主导删减。
删除仍需精确清单、结束/占用核对、证据校验和回执，本工具没有删除命令。
