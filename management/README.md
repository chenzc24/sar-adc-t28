# 项目管理入口

从 [当前状态](STATUS.md) 查看设计、文件、远端数据和待核对项。这里统一登记位置和证据，不搬动现有目录。

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

## 当前运行规则

默认单组仿真、每组四线程；重型分析单独排队、单组流式或内存映射处理。提交前分别检查系统和用户内存余量、换页、目标盘空间及短测估算的输出量。旧脚本尚未接入统一提交器，这些默认值目前登记为策略，不声称已经自动强制执行。

新运行根目录暂未配置。现有 OA 路径保持不变；`SAR_ADC_T28_WORK` 只作为后续规划登记，尚未由本次盘点创建。旧远端目录不因登记而迁移。

未审核运行、冻结基准及关键异常证据默认保护。清理仍需精确文件清单、运行结束与占用核对、保留证据校验和删除回执；本工具不执行删除。

## 下一阶段

在这份登记基础上实现统一提交/回收入口和资源门禁，确认 SSD 使用权限与保留周期，再整理开发库与冻结库。当前阶段完成盘点、追溯和差异清单；没有更改电路、提升候选或重跑验证。
