# 有限正常低相位：SS 冷角对照准备

只准备 `sar8audit-sample-v2-low60cold`，未注册、未运行；父任务审核后才可使用管理队列提交。

已核对现有 loaded rx2 TT 测试文件中的原始时钟：

```text
VSAMPLE ... val0=SUP val1=0 delay=41n rise=100p fall=100p width=59.9n period=100n
```

周期 100 ns（10 MS/s）。41–41.1 ns 下降，101–101.1 ns 上升，141–141.1 ns 再下降。按半电平交点计算，正常低相位为 60 ns、高相位为 40 ns；完全低电平平台是 41.1–101 ns，即 **59.9 ns**。`low60cold` 名称采用名义低相位，配方中的 `external_low_plateau_ns` 如实填 59.9。

| 对照 | 第一次下降沿 | 低电平平台 | 正式上升 / 关闭沿 |
| --- | --- | --- | --- |
| 冻结 low40cold | 60.9–61 ns | 40 ns | 101–101.1 / 141–141.1 ns |
| 新 low60cold | **41–41.1 ns** | **59.9 ns** | 完全相同 |

相对 low40cold 仅一个 VSAMPLE 行变化；高相位 DC 初态、输入在 100.2–100.3 ns 翻转、器件尺寸、负载、参考 Q128、比较器复位、SS/0.81 V/−40°C/TT 无源、测量和资源预算均不变。原 low40cold 和所有共用文件按 SHA 校验后只读复用。

目的：检查正常周期可用低相位能否恢复足够的 Cboot 泵压，避免把充分预充的 DC 对照当作有限周期恢复，也避免未经定位就加宽 Mmain。它仍是固定参考、比较器复位的隔离诊断，未包含真实转换和参考切换历史；即使通过也不能宣称整机正常周期或上电/POR 合格。

运行后复核同一自然 DC、实际 SEQ_SAMPLE 低区间和获取窗口，再比较 Cboot、CTRL、G−VIN、两侧主开关电流、关断前/141.8 ns 误差及全部 MOS 原生端压。保持阶段净变化继续与关断前建立误差分开。实际时序与最短预充需求目前均未知。

准备文件：[deck](low60cold/test.scs)、[单变量 diff](low60cold/source.diff)、[散列与时钟契约](manifest.json)、[管理配方建议](recipe_suggestions.json)。五项本地结构/反例测试通过；确定性检查命令：

```powershell
& 'E:/bridge-Agent-T28/projects/sar-adc-t28/.venv/Scripts/python.exe' -B prepare_normal_period.py --check
```

命令在本 sampling 目录运行，不会提交远端任务。
