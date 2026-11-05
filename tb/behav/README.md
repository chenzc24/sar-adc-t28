# 模块与混合层次测试

数值测试位于 [tests/test_modules.py](../../tests/test_modules.py)，既有整机量化与协议测试保留在 [test_behavioral.py](../../tests/test_behavioral.py)。测试跨模块公开接口，包括有限采样建立、位权、比较器偏移/延时、参考非交叠、模块替换及当前/冻结设计打包。

`python -m tools.saradc behav prepare --run-id ID` 生成一个原生测试包到 `work/behav/ID`；`behav sim` 使用同一受管执行器提交。生成入口是 [modular.py](../../tools/saradc/modular.py)，结果分析是 [analyze_modules.py](../../tools/saradc/measure/analyze_modules.py)。不复制大量测试目录。

原生测试包含：

- 六个低/中/高码和首帧：当前全管级、核心全行为、比较器管级、CDAC 管级、采样管级、控制与参考管级。
- 比较器强制不响应：确认部分码与具体停滞位，不能误报完整转换。
- 采样开关接 1 pF：观察跟踪、关闭和输入变化后的保持。
- 比较器接每端 20 fF：检查正负决策、失调极性及双端复位。
- 参考所有位栅控：检查 NMOS/PMOS 不同时开启；公开 CMP_CLK/PHI_U 波形验证逐位事件。

整机混合短测保留每端 50 Ω 输入/参考阻抗、4 pF 参考旁路、5 fF 输出负载及 B 的正常 60 ns 低/40 ns 高外部时钟。独立 [observer.va](observer.va) 在采样关闭后 55 ns 读取八个实际输出电压。

配置见 [views.json](../../specs/views.json)。VA 电阻、电容和延时是明确的模型近似；此测试不授予模拟精度、PVT、原生失配、功耗或端压资格。已有原始告警、失败运行和冻结来源继续保留。
