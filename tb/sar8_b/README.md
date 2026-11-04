# B 版测试台

每个测试分成四部分。`test.scs` 指定模型、工况、分析和保存信号；`tb.scs` 放激励、源阻抗、负载及 DUT 实例；观察器 `.va` 记录事件；Python 分析器处理原生波形。模块独立测试的实例和激励直接位于 `test.scs`。

以下是已经登记的真实测试输入，完整依赖、散列、分析器和资源预算见 [cases.json](cases.json)。

| 测试 | Spectre 入口 | 激励与连接 | Managed 配方 |
| --- | --- | --- | --- |
| TT 十帧启动与关键码 | [test.scs](../../verification/sar8_campaign/sar8camp-b-mm-bench-v1/test.scs) | [tb.scs](../../verification/sar8_ab_phase60/b/tb.scs) | [sar8camp-b-mm-bench-v1](../../management/recipes/sar8camp-b-mm-bench-v1.yaml) |
| TT 连续 1024 点 FFT | [test.scs](../../verification/sar8_campaign/sar8camp-b-tt-fft1024-mm-v1/test.scs) | [tb.scs](../../verification/sar8_campaign/sar8camp-b-tt-fft1024-v1/tb.scs) | [sar8camp-b-tt-fft1024-mm-v1](../../management/recipes/sar8camp-b-tt-fft1024-mm-v1.yaml) |
| TT 全码的首段，边界 1–3 | [test.scs](../../verification/sar8_campaign/sar8camp-b-tt-s001-003-v1/test.scs) | [tb.scs](../../verification/sar8_campaign/sar8camp-b-tt-s001-003-v1/tb.scs) | [sar8camp-b-tt-s001-003-v1](../../management/recipes/sar8camp-b-tt-s001-003-v1.yaml) |
| 比较器 TT 失配示例，seed 4101 | [test.scs](../../verification/sar8_mc/blocks/sar8mc-comp-s4101-v2/test.scs) | 真实接收负载与 [门槛搜索 VA](../../scripts/sar8_mc/comp_search.va) | [sar8mc-comp-s4101-v2](../../management/recipes/sar8mc-comp-s4101-v2.yaml) |
| CDAC TT 失配示例，seed 4101 | [test.scs](../../verification/sar8_mc/blocks/sar8mc-cdac-s4101-v2/test.scs) | 18 个 MOM 的独立 AC 位权测量 | [sar8mc-cdac-s4101-v2](../../management/recipes/sar8mc-cdac-s4101-v2.yaml) |
| SS 冷闭环示例，seed 5101 | [test.scs](../../verification/sar8_mc/timing_mc/sar8tm-ssc-s5101-v1/test.scs) | [tb.scs](../../verification/sar8_campaign/sar8camp-b-ssc-screen-v1/tb.scs) | [sar8tm-ssc-s5101-v1](../../management/recipes/sar8tm-ssc-s5101-v1.yaml) |
| FF 冷闭环示例，seed 5101 | [test.scs](../../verification/sar8_mc/timing_mc/sar8tm-ffc-s5101-v1/test.scs) | [tb.scs](../../verification/sar8_campaign/sar8camp-b-ffc-screen-v1/tb.scs) | [sar8tm-ffc-s5101-v1](../../management/recipes/sar8tm-ffc-s5101-v1.yaml) |

短测和冷角闭环使用 50 Ω 输入源/参考源阻抗、4 pF 参考旁路和 5 fF 数字输出负载。外部采样周期 100 ns，首段低电平 60 ns，随后高电平 40 ns。内部比较时钟由真实 SAR 异步环路产生。

当前冷角测试的随机范围为 `XDUT.XCOMP` 与 `XDUT.XCDAC`。SAR、参考控制和采样电路参与真实闭环，在该角使用名义局部参数。全电路失配尚待补测。MOS 使用 SS/FF local-MC section，部分被动模型沿用 TT；准确 include 以各 `test.scs` 为准。

当前标准单元 B 的外部参考保持 0.9 V。核心供电的 0.81/0.99 V 与参考电压分别记录。

本机已导出 7 类复现包。十帧短测可直接打开 [test.scs](../../output/sar8_b/tt_short/test.scs)、[tb.scs](../../output/sar8_b/tt_short/tb.scs) 和 [dut.scs](../../output/sar8_b/tt_short/dut.scs)。从其他检出工作区生成相同文件包时，执行下面命令。它会核对源散列，导出到 `output/sar8_b/tt_short/`。

```powershell
.venv/Scripts/python.exe scripts/sar8_entry.py export tt_short
```

导出的 `test.scs`、`tb.scs`、`dut.scs`、库 include、观察器和分析器，就是该历史配方实际使用的版本。其他别名为 `tt_fft1024`、`tt_static_low`、`mc_comparator_tt`、`mc_cdac_tt`、`mc_cold_ss`、`mc_cold_ff`。

查询服务器上的一个现有运行，在项目根目录执行：

```powershell
.venv/Scripts/python.exe scripts/management/project.py run-status sar8tm-ssc-s5103-v1
```

新实验通过 [managed 流程](../../management/README.md#统一仿真与回收)登记唯一运行 ID、冻结输入后提交。既有运行 ID 保留其输入身份，重复提交会复用原任务。

服务器实际文件统一在 `/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/<run_id>/`。`inputs/` 是输入，`spectre.out` 是日志，`raw/` 是原始波形，`derived/result.json` 是分析结果。具体运行 ID 与本地结果见 [仿真结果](../../results/sar8_b/README.md)。
