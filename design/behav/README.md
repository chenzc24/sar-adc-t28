# B 版模块化行为模型

总规格见 [arch.json](../../specs/arch.json)。晶体管设计保持 B 版原值；行为实现和混合验证不构成新的物理基线。

| 功能 | Python | Verilog-A |
| --- | --- | --- |
| 配置与结果 | [config.py](python/config.py) | [b_defaults.vh](veriloga/b_defaults.vh)，由总规格生成 |
| 采样 | [sampler.py](python/sampler.py) | [sampler.va](veriloga/sampler.va) |
| CDAC | [cdac.py](python/cdac.py) | [cdac.va](veriloga/cdac.va) |
| 比较器 | [comparator.py](python/comparator.py) | [comparator.va](veriloga/comparator.va) |
| 异步 SAR | [sar.py](python/sar.py) | [sar.va](veriloga/sar.va) |
| 参考控制与延时 | [reference.py](python/reference.py) | [reference.va](veriloga/reference.va) |
| RC / clear 非对称延时 | 独立表征配置 | [timing.va](veriloga/timing.va) |
| 整机组合 | [sar_adc.py](python/sar_adc.py) | [sar_adc_b.va](veriloga/sar_adc_b.va) |

Python 顶层接收独立的 `sampler/cdac/comparator/sar/reference` 实现，默认使用上表模块。公开的 `AdcSpec`、`AnalogConfig`、`FrameResult`、`SarAdcModel` 导入方式保留。数值模型采用有效位权和一阶 trial 建立近似，保留原 8 种情形的事件/码字定义；它适合算法、误差分配和校准研究。

```python
from design.behav.python import SarAdcModel, AnalogConfig
from design.behav.python.sampler import Sampler

adc = SarAdcModel()
frame = adc.convert(0.123)
sampler = Sampler(AnalogConfig(), tau_s=1e-9)
held = sampler.acquire(0.2, duration_s=40e-9)
frame = adc.convert(held)
```

Python `convert(vin)` 接收采样关闭时的理想差分值。研究有限采样窗时，先用 `acquire` 求已建立电压，或注入含跟踪历史的 `capture` 实现；不会因设置独立 `acquire` 的时间常数而静默改变原来的整机标量输入定义。VA 采样器则直接接时变电压源及电容网络。

## 电气 VA 模型

VA 顶层实际连接各功能模块，保持与 B 顶层相同的 15 个端口顺序；局部供电标识符使用 `VDD/VSS`。各模块的接口、参数和约束直接定义在各自 `.va` 中。

- 采样器是有限开/关电阻，保持电荷由外部电容承担；不会用理想电压源钳住 CDAC 顶板。可设增益、偏移及按帧的近似噪声电荷注入。
- CDAC 使用每侧 255 单位二进制电容和 1 单位 dummy，以 `C·ddt(V)` 和有限开关电阻连接真实顶板/参考节点。位权误差按 LSB→MSB 设置。
- 比较器低相位双端预充，高相位经过输入相关延时后判决；输入电容和输出电阻显式保留，可注入偏移、噪声或强制不响应。
- SAR 从比较器实际输出接收有效判决，再产生写入、参考更新和下一位比较。新的采样优先取消旧事件；没有额外 BUSY/VALID/EOC 端口。
- 参考控制两次捕获 D/CODE，先关闭开关再经过 deadtime 开启新状态；初始预置字为 128。延时模块提供有限传播时间及边沿。

默认单位电容约 4.00407 fF，来自总规格中的同几何低频表征；它是定电容近似。50 Ω 采样开关、10 kΩ 单位参考开关、100 Ω 行为输出、2 fF 比较器输入及 100 ps 非交叠是明确的行为默认值，未被冒充为提取后的 B 参数。默认噪声为零；Python 与 Spectre 的随机数流不同。VA 的外部参考噪声应由测试台参考源注入，Python 的每次判决参考噪声是另一种数值抽象。

Python `weight_errors` 修改折合后的有效阈值系数；VA `weight_error0..7` 修改实际电容，阵列总容量和负载响应也随之变化。两者不能直接逐参数互拷，比较非理想位权时需先从电气模型提取有效系数。

物理 Bootstrap 的冷启动充电、非线性 MOM、kickback、PVT/原生失配、端压、功耗与 PEX 继续由管级实现验证。VA 模型初始化与有限 R/C 不能证明实际升压电路的启动历史。数值 trial 模型与电气电容网络是两个层次，不把二者的时间或所有边界码强行视为完全相同。

当前 CDAC 行为模型的门控输入只感知电压，尚未拟合真实开关的栅电荷。`control_xtor` 因此用于控制接口与功能检查，不能据此签核实际栅控建立或驱动功耗；这些结论使用 `current` 管级视图。启用 VA 多实例噪声时，应为各实例指定独立的 `noise_seed`，本轮未做噪声统计资格验证。

## 模块选择与测试

[views.json](../../specs/views.json) 是统一选择配置。默认 `current` 使用当前管级设计；`frozen-b` 只用于历史回归。混合视图使用原有 B 顶层连接，在生成测试包中选择实现，不编辑晶体管源码。

| 视图 | 管级实现 | 其余核心模块 |
| --- | --- | --- |
| `behavioral` | 原生外围负载 | VA |
| `comparator_xtor` | 比较器 | VA |
| `cdac_xtor` | CDAC/开关 | VA |
| `sampler_xtor` | Bootstrap 采样 | VA |
| `control_xtor` | SAR、参考控制与实际延时 | VA |

三端、使用全局电源的 Bootstrap 用生成的小包装适配五端采样行为模型；其他模块保持声明的标量端口顺序。Virtuoso 沿用已有接入，OA 数据库不由本次文本重构修改。

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m tools.saradc prepare tt_short --view comparator_xtor --run-id sar8-comp-mixed-v1
.venv/Scripts/python.exe -m tools.saradc behav sim --run-id sar8-modules-v3
.venv/Scripts/python.exe -m tools.saradc behav follow --run-id sar8-modules-v3
```

`follow` 是一次性的等待、分析、回收流程：只接续已经登记的运行，仿真成功后才启动分析，失败则保留并退出，不重提仿真。也可继续分别使用 `status / analyze / collect`。

模块测试条件见 [tb/behav](../../tb/behav/README.md)，实际证据见 [results/behav](../../results/behav/README.md)。旧 10-bit、旧外部位时钟及专用实验模型继续留在历史区，审查索引见 [model_audit.json](../../results/behav/model_audit.json)。

六模块可在命名视图后逐项覆盖：`--view current --view comparator=va --view reference=va`。`sar_xtor / reference_xtor / timing_xtor` 提供相应独立视图；完整六类模块测试见 [tb/blocks](../../tb/blocks/README.md)。

`timing.va` 的 RC/clear 近似分别保留上升与快速复位延时，来源与数值由 `specs/views.json` 的 `timing_approximations` 给出。其来源是独立 TT 接收门负载表征，不代表实际 SAR 全扇出或 PVT 拟合。旧 `sar8-modules-v3` 证据仍绑定其原模型/选择配置；本轮新测试以各自运行回执为准。
