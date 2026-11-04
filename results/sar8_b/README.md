# B 版仿真结果

整理于 2026-11-04。对象为 [B 版电路](../../design/sar8_b/README.md)，设计 ID `sar8_l90_mmain2_stdcell_v1`，冻结源 SHA256 `f31b66c8…`。A 版自建数字门的结果在原 A/B 报告中单列。

| 验证 | 已有结果 | 数据与条件 |
| --- | --- | --- |
| TT 全码静态 | 255 个边界、256 个中心码完成；DNL 约 −0.0391～+0.0391 LSB；最大端点 INL 0.0445 LSB | [原始汇总 JSON](../../verification/sar8_campaign/ab_static/fullstatic_recovered.json) 中的 `b`；确定性 TT |
| TT 1024 点动态 | SNDR 48.788 dB，SFDR 64.768 dBc，ENOB 7.812 bit；SNR 48.806 dB | [频谱、完整报告与数值](../../verification/sar8_campaign/fft_final/README.md)；4.502 MHz、−1 dBFS、8 帧预热 |
| 五点关键码 | 每角 10 帧的启动、码字与事件计数完成 | [五点报告](../../verification/sar8_campaign/ab_pvt/README.md)；关键码筛查 |
| TT 比较器 200 种子 | 失调 SD 14.188 mV，范围 −29.938～+37.688 mV | [逐种子与最终汇总](../../verification/sar8_mc/timing_mc/module_results.json)；局部失配、固定共模诊断测试台 |
| TT CDAC 200 种子 | 200 组静态 DAC 电平均单调；最大绝对 DNL 0.1617、INL 0.0848 LSB | [逐种子与最终汇总](../../verification/sar8_mc/timing_mc/module_results.json)；独立 MOM 静态位权 |
| 冷角闭环 50 种子/角 | 完成数和原始闭环、同种子延长保持对照审核见检查点 | [检查点](../../verification/sar8_mc/timing_mc/checkpoint.json)、[最近逐角进度](../../verification/sar8_mc/timing_mc/cold_progress.json)；各 JSON 是查询时快照 |
| 比较器实际保持输入与分组定位 | 输入对为主要失调来源；另有再生 N/P 分组证据 | [真实输入测试](../../verification/sar8_mc/physical_input/README.md)、[30 种子分组结果](../../verification/sar8_mc/regen30/README.md) |

FFT 使用 Spectre X MX、4 线程、reltol=1e-6、trap、maxstep=10 ps。其 SNR 包含确定性量化和剩余失真。该测试关闭瞬态噪声、失配和 PEX。核心加参考功耗估计为 86.53 µW，积分网格收敛仍待验证，外部输入源和时钟源另算。TT 全码采用原登记的 CX 设置，各实验的完整配置见 [TB 清单](../../tb/sar8_b/README.md)。

器件端压告警尚未闭合。校准支路、全电路局部失配、噪声和版图寄生会增加后续验证范围。原始告警与数值失败保存在每个运行的日志和分析回执。

当前 Monte Carlo 运行与监测命令，在项目根目录执行：

```powershell
.venv/Scripts/python.exe scripts/sar8_mc/timing_mc/observe.py cold
.venv/Scripts/python.exe scripts/sar8_mc/timing_mc/observe.py refs
.venv/Scripts/python.exe scripts/sar8_mc/timing_mc/checkpoint.py
```

`cold` 统计原始闭环，`refs` 统计延长保持对照。判定是否通过需看逐位分析及对照审核。最初 `cold` 调度器的根节点分类问题已保留在失败记录中，接续调度和放行以 `refs` 的实际状态、`pilot_pass.json` 和审核结果为准。

实时权威文件在 `thu-wei` 的 `/server_local_ssd/chenzc_intern25/sar-adc-t28/` 下：

| 内容 | 相对服务器根目录的位置 |
| --- | --- |
| 某次仿真的原始日志、波形和分析 | `runs/<run_id>/spectre.out`、`raw/`、`derived/` |
| TT 模块补样 | `campaigns/sar8-timing-mc-20261104-modules/` |
| 冷角原始运行监测 | `campaigns/sar8-timing-mc-20261104-cold/` |
| 当前冷角接续调度和对照审核 | `campaigns/sar8-timing-mc-20261104-refs/` |

用 [cases.json](../../tb/sar8_b/cases.json) 可以从测试别名找到完整运行 ID、配方、输入文件、分析器、资源配置和服务器路径。
