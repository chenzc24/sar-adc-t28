# B 版行为模型

总规格是 [specs/arch.json](../../specs/arch.json)，人读版是 [完整规格](../../docs/specification.md)。模型接口与当前 B 顶层的 15 个端口顺序一致；VA 内部使用 `VDD`、`VSS` 代替网表的 `VDD!`、`0` 标识符。

| 模型 | 文件 | 用途 |
| --- | --- | --- |
| Python | [python/sar_adc.py](python/sar_adc.py) | 独立理想量化、有效位权、非理想和逐位事件轨迹 |
| Verilog-A | [veriloga/sar_adc_b.va](veriloga/sar_adc_b.va) | 同一接口的电压/事件行为视图，原生 Spectre 编译与交叉验证 |
| 生成默认值 | [veriloga/b_defaults.vh](veriloga/b_defaults.vh) | 从总规格生成的 TT 名义时序；通过 `behav generate` 更新 |

SAMPLE 高时清除 SAR，下降沿采样后自主逐位推进。没有额外 CLK_SAR、BUSY、VALID 或 EOC。新采样取消旧事件。输出码在转换中逐位更新，完成后才能读取最终值。

```python
from design.behav.python import SarAdcModel, AnalogConfig

adc = SarAdcModel()
frame = adc.convert(0.123)
print(frame.code, frame.completed, frame.counts)

offset = SarAdcModel(analog=AnalogConfig(comparator_offset_v=0.010))
print(offset.convert(0.123).code)
```

所有电压和时间参数使用 SI 单位。`weight_errors` 按 LSB→MSB，表示已经折合到比较节点的有效位权相对误差；模型不重新归一化它们，也不将这些用户参数冒充原生 MOM 的失配抽样。正 `comparator_offset_v` 抬高决策阈值、降低输出码。`reconstruct` 可以接收数字权重，校准器本身尚未实现。

有限建立使用 trial 阈值的一阶近似；可选对数决策延时是接收流水的抽象。默认 TT 时序取十帧原生事件中位数，不能预测 SS/FF 或局部失配的延时尾部。默认噪声为零；显式开启时，采样噪声按帧、比较器与参考噪声按决策独立抽样。Python 与 Spectre 的随机数流不同。

原生启动预充、开关电荷注入、参考电流、kickback、晶体管端压、功耗及 PEX 由管级模型验证。该行为视图初始化为确定的零状态，不能证明冷启动的电容充电历史。

## 交叉验证

```powershell
.venv/Scripts/python.exe -m tools.saradc behav generate
.venv/Scripts/python.exe -m tools.saradc behav check
.venv/Scripts/python.exe -m unittest discover -s tests -p test_behavioral.py -v
.venv/Scripts/python.exe -m tools.saradc behav sim --run-id sar8-behav-cross-v1
.venv/Scripts/python.exe -m tools.saradc status sar8-behav-cross-v1
.venv/Scripts/python.exe -m tools.saradc analyze sar8-behav-cross-v1 --queue
.venv/Scripts/python.exe -m tools.saradc behav collect --run-id sar8-behav-cross-v1
```

本地交叉验证包括 256 个中心码、255 个转换边界的两侧及精确相等、饱和、位序、取消/停滞、偏移符号和位权。代码中心还与 B 版实测转换边界交叉；TT 十帧比较时间近似误差直接报告。

原生 VA 测试每个输入运行 8 种情形：名义、采样增益/偏移、比较器偏移、MSB 位权、有限建立、比较超时、bit3 停滞、输入相关决策延时。独立 VA 观察器读取 D0..D7 的真实输出电压，避免只比较内部变量。结果在 [results/behav](../../results/behav/README.md)。

高频比较使用已记录的源电压采样与真实 B 输出码。理想瞬时量化省略模拟采样传递，差异单列，不能为了对齐频谱而静默修正输入相位或码字。

## 旧模型审查

- 原 Python 理想模型的参数化量化保留为功能，去掉 ADCtoolbox SAR 接口依赖和旧 10-bit 描述。
- 原两个 Python 异步模型合并，清除旧 43/89 ns 时限、固定初始相位和 BUSY/VALID 发布机制。
- 原 8-bit VA 的外部位时钟接口被当前自主异步接口替代。
- 原电气宏控制器依赖外部 TRIAL/LATCH，继续留在历史区；10-bit、5+5 split、早期参考门驱动模型均未迁入当前行为目录。

历史源的哈希和本次处理见 [model_audit.json](../../results/behav/model_audit.json)。当前模型运行时只读取新总规格。
