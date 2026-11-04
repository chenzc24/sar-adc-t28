# SAR ADC T28

8 bit、10 MS/s、全差分异步 SAR ADC，TSMC 28 nm。入口更新于 **2026-11-04**。

本轮验证对象为 **B 版 `sar8_l90_mmain2_stdcell_v1`**，模拟电路沿用 L90 / Mmain2，数字逻辑使用原生标准单元。使用 Spectre 网表设计和验证。

| 我要找什么 | 直接打开 |
| --- | --- |
| **顶层电路** | [design/sar8_b/top/adc_top.scs](design/sar8_b/top/adc_top.scs) |
| **子模块与接口** | [design/sar8_b/README.md](design/sar8_b/README.md)；采样、CDAC、比较器、SAR、参考和延时各有独立文件 |
| **测试台 TB** | [tb/sar8_b/README.md](tb/sar8_b/README.md)；包含实际 test.scs、tb.scs、观察器、配方与分析器 |
| **仿真配置与结果** | [results/sar8_b/README.md](results/sar8_b/README.md)；TT 全码、FFT、PVT、200 种子和在途冷角验证 |

```text
design/sar8_b/
  top/adc_top.scs       顶层连接
  blocks/              Bootstrap、MOM CDAC、StrongARM、SAR、参考、标准门、RC 延时
  dut.scs              完整分模块 include 入口
tb/sar8_b/
  README.md            测试台、激励、条件、运行命令
  cases.json           实际输入路径、散列、运行 ID 和服务器位置
results/sar8_b/
  README.md            各项验证结果和证据入口
```

顶层 master 名为 `sar_adc8_join_r4`。B 的冻结源是 [netlist/sar8_l90_mmain2_stdcell_v1/dut.scs](netlist/sar8_l90_mmain2_stdcell_v1/dut.scs)，SHA256 `f31b66c8…`。`design/sar8_b` 是与该源逐子电路核对的分文件视图。原生仿真证据绑定原冻结源；OA 同步及端压可靠性仍有待完成项。

在项目根目录检查电路来源和测试输入，或导出一个测试的完整文件包：

```powershell
.venv/Scripts/python.exe scripts/sar8_entry.py check
.venv/Scripts/python.exe scripts/sar8_entry.py export tt_short
```

第二条把十帧短测的实际输入集中放到 `output/sar8_b/tt_short/`。新仿真沿用 [managed 执行流程](management/README.md#统一仿真与回收)，各项源输入、模型和预算由配方冻结。

| 其他版本与工程资料 | 入口 |
| --- | --- |
| A 版，L90 / Mmain2 自建数字门对照 | [冻结网表](netlist/sar8_l90_mmain2_frozen/dut.scs)、[A/B 频谱](verification/sar8_campaign/fft_final/README.md) |
| 早期 R3、R4、修复实验和独立手搭 ADC | [历史文档索引](docs/README.md) |
| 设计与运行登记 | [management/designs.yaml](management/designs.yaml)、[管理说明](management/README.md) |
| 当前失配验证计划 | [模块 200 种子与冷角闭环](plan/2026-11-04-sar8-timing-mc/plan.md) |
| 工程记录 | [plan/log.md](plan/log.md)、[AGENTS.md](AGENTS.md) |

工作区位于 `E:\bridge-Agent-T28\projects\sar-adc-t28`，本地整理内容以实际工作区为准。用户笔记在 `Obsidian_docs/`，实验明细在 `verification/`，生成物和回收数据在 `output/`。
