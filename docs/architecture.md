# 当前架构

完整定义见 [总设计规格](specification.md)，机器真源为 [specs/arch.json](../specs/arch.json)；[行为视图](../design/behav/README.md)与晶体管实现分别验证。

8 bit、10 MS/s、全差分异步 SAR ADC。Bootstrap 采样到差分顶板；18 个 MOM 构成 CDAC；StrongARM 的真实输出由异步 SAR 接收，逐位更新参考控制。

电路从 [顶层](../design/top/adc_top.scs) 阅读，模块和端口见 [电路索引](../design/README.md)。外部时钟周期 100 ns，初始低 60 ns、高 40 ns。内部比较、写入和参考更新由真实握手与 RC 延时产生。

数字逻辑使用原生标准单元；Bootstrap、CDAC 开关和比较器保留晶体管实现。PDK、标准库和 OA 独立保管。网表与 OA 的同步资格分别记录。
