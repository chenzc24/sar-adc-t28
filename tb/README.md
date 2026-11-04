# 测试台

VA/Python 的算法与协议交叉测试见 [behav/README.md](behav/README.md)。下表继续描述已完成晶体管级验证的冻结输入。

实际文件直接位于本目录，各用例的输入散列、历史身份、条件和预算由 [specs/tests.json](../specs/tests.json) 记录。

| 用例别名 | 实际入口 |
| --- | --- |
| `tt_short` | [top/short/test.scs](top/short/test.scs) |
| `tt_fft1024` | [top/fft/test.scs](top/fft/test.scs) |
| `tt_static_low` | [top/static/test.scs](top/static/test.scs) |
| `mc_cold_ss` | [top/mc_ss_cold/test.scs](top/mc_ss_cold/test.scs) |
| `mc_cold_ff` | [top/mc_ff_cold/test.scs](top/mc_ff_cold/test.scs) |
| `mc_comparator_tt` | [blocks/comparator/test.scs](blocks/comparator/test.scs) |
| `mc_cdac_tt` | [blocks/cdac/test.scs](blocks/cdac/test.scs) |

`test.scs` 提供模型、分析和保存设置，`tb.scs` 提供激励、真实负载及 DUT 实例。VA 监视器位于 `common/veriloga/`，测量代码位于 `tools/saradc/measure/`。

整机测试使用 50 Ω 输入/参考源阻抗、4 pF 参考旁路、5 fF 数字输出负载。外部时钟先低 60 ns、高 40 ns。精确值和模型 section 以实际 deck 为准。

`tt_static_low` 保留已验证的前三个边界测试。已完成全码结果包含 255 个边界和 256 个中心码；后续分段由工作区中的历史运行定义追溯，当前模板不复制数百份生成 deck。

`prepare CASE --seed N` 从单个 MC 模板生成指定种子；闭环局部失配只覆盖比较器和 CDAC。原生 MOS/MOM 统计模型由 deck 指定。历史用例默认打包冻结 B；`--split-design` 显式验证当前分模块入口。
