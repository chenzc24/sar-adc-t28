# 规格与实验定义

- [arch.json](arch.json)：总设计真源，包含架构、完整端口、采样/转换、器件实现、负载、目标、误差预算、校准未定项、验证范围和行为模型参数。
- [完整总规格](../docs/specification.md)：从总规格生成的人读版。
- [corners.json](corners.json)：已有五点工况；精确器件 section 由冻结 deck 确定。
- [blocks/](blocks/)：模块 master、端口和实现位置。
- [tests.json](tests.json)：7 个真实模板的输入散列、分析器、预算及历史运行身份。
- [monte_carlo.json](monte_carlo.json)：200 种子模块与两冷角各 50 种子的统计范围。

指标中的空缺代表尚未定义或验证，不能从退出码、功能正确或示意图推定。Monte Carlo 种子与模型范围共同定义一次抽样，单独相同 seed 不足以证明同一 draw。
