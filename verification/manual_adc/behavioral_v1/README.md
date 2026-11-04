# 手搭SAR8的行为模型

用于后续由用户指导的模块替换与组合实验。对应 `SAR_ADC_T28_manual` 的首位向上、后续向下算法，不代表历史R4或当前晶体管候选已通过验收。四个VA文件完整、自包含；不依赖PDK。原OA、晶体管网表与标准库均未改动。

## 从这里开始

- 日常实验入口：[tb_adc.scs](tb_adc.scs)，仅包含一个全行为ADC及理想外部激励。
- 模块连接与参数入口：[wrappers.scs](wrappers.scs)。后续逐个替换这里的实例。
- 自动自检入口：[tb_smoke.scs](tb_smoke.scs)，另带复位取消、非法响应和超时探针。
- 编译/行为检查结果：[validation.json](validation.json)。`tb_adc.scs`与已验证自检台使用同一ADC实例、激励和选存；它单独运行时尚未另作一次验收。

所有新运行通过项目managed流程。不要在同一已冻结run ID下改输入重跑。构建脚本 `scripts/manual_adc/behavioral_build.py` 会重新生成两个TB、wrappers与自检配方；手工实验请复制为新案例，避免被构建脚本覆盖。

## 模块接口与主要参数

### 采样开关：[manual8_sample.va](manual8_sample.va)

端口顺序：`CLKS GND VDD VIN VOUT`，与 `manual_boot`一致。CLKS高时跟踪，低时保持；保持电容由外部CDAC提供，模型不另加隐藏电容。

| 参数 | 默认值 | 含义 |
|---|---:|---|
| ron / roff | 1 Ω / 1 TΩ | 导通/关断电阻 |
| trf | 10 ps | 导通系数变化时间；不是额外RC延时 |
| threshold | 0.5 | 以VDD为基准的时钟判断比例 |
| cin | 0 F | 可选输入对地电容 |
| qclk | 0 C | 关闭时向保持节点注入的电荷；开启时反向抽取同量电荷 |

`qclk`是可选的互易时钟馈通抽象，不是已拟合的真实沟道电荷注入。主开关有有限Ron，因此需要采样建立；不生成Bootstrap升压节点，不能用它验证自举端压、启动预充或器件可靠性。

### CDAC：[manual8_cdac.va](manual8_cdac.va)

端口顺序：`GND VDD VTOP VREFP VREFN DCTRL_7 ... DCTRL_1`。这是单侧**电容＋参考开关**，采样开关在wrapper内独立实例化。

- 权重为64、32、16、8、4、2、1 C，另有1 C接GND；默认Cunit=10 fF，总计1.28 pF/侧。
- 控制高接VREFN、低接VREFP，匹配当前原生开关极性。
- 仅bit7在顶层交叉：P侧接DN7，N侧接DP7；其余位同侧连接。
- 顶板和底板均为真实电气节点，通过 `I <+ C*ddt(V)`守恒电荷，没有电压源强制顶板理想值。
- `ron_unit=10 Ω`，`scale_ron=1`时Ron随权重反比缩小；`roff=1 TΩ`；`ctop=0`可增加顶板寄生。
- `vsmooth=10 mV`控制参考开关电导切换平滑度；不包含真实非交叠、MOS栅电容、体二极管和注入。驱动端默认没有栅负载，SAR电气验证时必须另外接入真实/测量负载。
- 开关电导过渡期间两条参考支路可能同时有有限电导；该模型用于电荷/建立实验，不用于参考驱动功耗或非交叠资格判断。

### 比较器：[manual8_cmp.va](manual8_cmp.va)

端口顺序：`CLK VINP VINN VDD GND DCMPP DCMPN`，与 `manual_cmp`一致。

CLK低时两路输出为0；上升阈值时锁定输入符号，等待td后仅一路为高；相等时固定判P高。若td到期前CLK下降，取消待发布结果。必须先提供低电平复位，启动即高不会被视为一次有效比较。

| 参数 | 默认值 | 含义 |
|---|---:|---|
| td | 200 ps | 判决发布延迟 |
| trf / rout | 50 ps / 1 Ω | 输出边沿/输出电阻 |
| vos | 0 V | 判决依据为VINP−VINN−vos |
| cin | 0 F/侧 | 可选输入电容；真实比较器实验须按实测设置 |
| treg | 0 s | 非零时加入小输入延迟：treg×ln(1+vscale/max(|vd|,vfloor)) |
| vscale / vfloor | 1 mV / 1 µV | 上式尺度及下限 |
| qkickp / qkickn | 0 C | 每侧在CLK上升时抽取、下降时返回的电荷 |
| vlogic | 0.9 V | qkick对应的完整时钟摆幅；改变供电且使用qkick时同步调整 |

`treg`不是经过校准的亚稳态模型；默认没有噪声/随机失配。输入在上升沿锁定，不能复现真实比较器在再生过程中持续受输入变化影响的全部行为。负载和边沿可控制，但VA输出供能不从VDD端严格守恒，不能用VDD积分计算真实功耗。

### SAR：[manual8_sar.va](manual8_sar.va)

端口前缀与 `manual_sar`一致：`CLKS GND VDD DCMPP DCMPN CMPCK DO_7...0 DCTRLP_7...0 DCTRLN_7...0`；末尾增加 `BUSY EOC FAULT`三个诊断端口。

采样上升沿先锁存已完成帧的raw正侧判决码，再清工作状态；下降沿启动转换。八次比较，bit7首先向上切换，bit6至bit1向下切换，bit0只判决不切电容。输出是自然二进制偏移码，差模满量程为−VREF至+VREF；默认LSB=1.8/256=7.03125 mV。

| 参数 | 默认值 | 含义 |
|---|---:|---|
| t_start | 4 ns | 采样关闭后等待再发首个比较时钟 |
| t_capture | 50 ps | 有效响应跨阈值后，到读取双路结果的等待 |
| t_update | 100 ps | 接收结果并拉低CMPCK后，到更新参考控制的等待 |
| t_settle | 2 ns | 参考控制更新后，到允许下一比较的等待 |
| t_reset | 500 ps | 从CMPCK拉低算起的最小复位间隔 |
| t_timeout | 8 ns | 等待结果/复位的诊断超时参数 |
| trf / rout | 50 ps / 1 Ω | 各数字输出边沿/输出电阻 |
| cin_cmp | 0 F/路 | 可选比较器输出端接收负载 |

这些是**独立行为时序预算**，不能把t_settle直接等同于原晶体管SAR的tloop。定时动作使用显式timer，不使用RC，不在周期时钟上暗中轮询。

- BUSY：本帧正在转换。
- EOC：八位完成，保持到下次采样开始；不是输出码更新沿。
- DO：下一次采样开始后才更新上一帧码字；对比输入必须考虑此固定延迟。
- FAULT：双高/无有效结果、超时、采样提前中止未完成转换等诊断。失败帧不发布为新DO；故障保持到后续采样复位。FAULT是测试辅助，不是已经实现的硬件电路。
- 下一次比较前要求DCMPP和DCMPN均恢复为低；采样开始会取消未执行的动作。模型不模拟真实FF的setup/hold、内部过冲及亚稳态。

## 当前默认时序与刺激

全行为台为0.9 V供电，VREFP=0.9 V，VREFN=0，输入共模0.45 V；外部采样时钟上/下降50 ps、周期100 ns，首次10 ns上升，关闭50%点49.975 ns。有限开关电导转变由trf明确控制。

8帧输入为码中心对应的0、255、85、170、127、128、1、254。默认首个比较时钟约54 ns，随后约每2.4 ns一次，首帧约71.2 ns完成，110 ns采样上升后输出该帧结果。这是行为模型设定的时序，不是晶体管性能测量。

## 后续如何换入真实模块

| 实验 | 修改wrappers中的位置 | 注意 |
|---|---|---|
| 真比较器 | XC：`manual8_cmp`改为`manual_cmp`，使用其真实参数 | 端口同序，去掉VA专用参数；另加接收负载，默认VA控制器cin_cmp=0不能代表真实FF负载 |
| 真Bootstrap | 单侧wrapper的XS改为`manual_boot main_mult=4` | 端口同序；仍接本VA CDAC的真实电容节点 |
| 真CDAC＋Bootstrap | XP/XN改用`manual_cdac` | 保留原bit7交叉与cunit；该原生子模块已经含Bootstrap，不能重复接采样开关 |
| 真SAR | XL改用`manual_sar` | 去掉末尾BUSY/EOC/FAULT三个端口，换回真实参数；另加参考开关栅负载 |

混合实验需显式包含原生模型与PDK文件。优先引用 `candidate_io_v1/dut.scs`中理想delay版本（不是 `dut_rc.scs`）；混合后的数值与电气结果需重新验证。本目录没有自动替换OA，也没有隐式启动混合/PVT实验。

## 验证边界

独立Python电荷重分配oracle遍历256个码中心，只验证算法。Spectre短程自检覆盖8个代表码、每帧8次比较、共模/残差、比较器取消后恢复、双高拒绝、缺响应超时以及采样中止后不触发旧事件。它不等于晶体管全码扫描、FFT、PVT、端压、噪声、失配或功耗验收。

EVAS不支持本模型所需KCL和ddt电容贡献，因此不用于这些验证；使用项目原生Spectre。
