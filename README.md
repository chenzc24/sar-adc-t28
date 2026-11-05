# SAR ADC T28

8 bit、10 MS/s、全差分异步 SAR ADC。当前验证对象为 B 版 `sar8_l90_mmain2_stdcell_v1`，采用 Spectre 网表设计；数字逻辑使用原生标准单元。

| 要找什么 | 入口 |
| --- | --- |
| 完整总规格 | [docs/specification.md](docs/specification.md)，机器真源 [specs/arch.json](specs/arch.json) |
| 顶层 | [design/top/adc_top.scs](design/top/adc_top.scs)；完整 include 为 [design/dut.scs](design/dut.scs) |
| 子模块 | [design/README.md](design/README.md) |
| RNL 原理图与层次展开 | [离线浏览器](docs/schematics/index.html)，[官方查看器与编辑说明](docs/schematics/README.md) |
| 独立模块测试 | [tb/blocks/README.md](tb/blocks/README.md) |
| 管级候选 | [design/xtor/README.md](design/xtor/README.md) |
| VA/Python 行为模型 | [design/behav/README.md](design/behav/README.md) |
| 实际测试台 | [tb/README.md](tb/README.md) |
| 仿真结果 | [results/README.md](results/README.md) |
| 架构、工况与验收 | [specs/README.md](specs/README.md) |
| 运行和监测 | [docs/simulation.md](docs/simulation.md) |

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m tools.saradc prepare tt_short
.venv/Scripts/python.exe -m tools.saradc observe cold
```

`prepare` 把真实用例打包进被忽略的 `work/decks/`。新仿真通过现有 managed 执行器登记、排队、分析和回收；原始波形及动态运行状态位于工作区和服务器。

日常默认当前管级设计。混合层次可重复指定 `--view comparator=va --view reference=va`；候选试用可加 `--candidate comparator=NAME`，冻结 B 仍显式回归。独立模块用 `block prepare/sim/follow`，源码、实际负载和测量均随运行冻结。

分模块设计与冻结 B 源的 49 个子电路电气语句逐段一致，当前源额外包含 RNL 绘图注释。迁移后的 TT 短测与冻结 B 的 10 帧码字、逐位事件计数、采样关闭沿和转换时间全部一致。[逐帧对照](results/migration/comparison.json)

个人笔记已迁到 `E:/Learning/SAR-ADC-T28`。旧实验、历史计划和一次性脚本通过 [来源记录](results/provenance.json) 的 Git 提交追溯；本机完整工作快照位于被忽略的 `work/legacy/`。

开发方法见 [AGENTS.md](AGENTS.md) 与 [工作流](docs/development-workflow.md)，Skills 保存在 `.agents/skills/`。端压可靠性、全电路局部失配和 PEX 仍按各项证据的实际范围报告。
