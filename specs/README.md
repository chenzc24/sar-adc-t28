# 规格与实验定义

- [arch.json](arch.json)：总设计真源，包含架构、完整端口、采样/转换、器件实现、负载、目标、误差预算、校准未定项、验证范围和行为模型参数。
- [完整总规格](../docs/specification.md)：从总规格生成的人读版。
- [corners.json](corners.json)：已有五点工况；精确器件 section 由冻结 deck 确定。
- [soa_rule.yaml](soa_rule.yaml)：用户采用的逐管端压工程验收规则、瞬态超限窗口及证据要求；不是 PDK 寿命包络。
- [blocks/](blocks/)：模块 master、端口和实现位置。
- [tests.json](tests.json)：7 个真实模板的输入散列、分析器、预算及历史运行身份。
- [monte_carlo.json](monte_carlo.json)：200 种子模块与两冷角各 50 种子的统计范围。
- [views.json](views.json)：命名视图及六模块的逐项 VA/管级选择；RC/clear 行为近似保留独立上升、下降延时及表征来源。
- [candidates.json](candidates.json)：物理候选、当前默认及公共接口；内部辅助电路不作为公共接口锁定。
- [block_tests.json](block_tests.json)：六项独立模块测试的激励、负载、测量、诊断限值和未覆盖项。

指标中的空缺代表尚未定义或验证，不能从退出码、功能正确或示意图推定。Monte Carlo 种子与模型范围共同定义一次抽样，单独相同 seed 不足以证明同一 draw。

当前采用 `reference=minimal_msb_d2` 与 `sar=reset_data_or`，其余模块沿用 B；[采用记录](../results/design/reset_data_or_adoption_20261115.json)保存准确文件散列及 FF 冷短测通过范围，其他角仍待验证。采用设计不豁免 [soa_rule.yaml](soa_rule.yaml)；历史 B 的 16 次捕获合同、行为时序与性能结果不转移给最简版。
