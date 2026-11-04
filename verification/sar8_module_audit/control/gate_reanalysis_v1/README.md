# 原始结果全时程端压与能量补算

这是读取已有完整波形的 analysis-only 包，**无需重跑Spectre，也不阻断floor
候选先运行**。两份均未由本session登记或执行：

- [MP1shape](mp1shape/recipe.suggested.yaml)：优先补齐0–END同时VSG/VGD和5路源能量；
- [both](both/recipe.suggested.yaml)：用于同口径完整VDD能量基线，可随后按需要串行补算。

每包约175kB，严格绑定已完成的原simulation recipe、全部冻结输入、原生PASS，
输出目录与源分离；原始文件只读。新分析器逐个原生点求联合端压，不以窗口或
非同时极值代替全程；按原生不等间隔积分 `P_delivered=-V×I_source`。
回收保留原诊断表、全时程极值/能量和源SHA，资源256MiB、输出/回收上限不变。

已通过一项闭式能量/“越界发生在诊断窗之前”的合成测试。源绑定复用已审阅的
只读SHA、完整注册输入及路径校验；实际全时程数值待主聊天统一执行后交付。
`full_gate_analyze.py` 现已随floor包冻结，不再改动。
