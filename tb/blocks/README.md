# 独立模块测试

用例真源是 [block_tests.json](../../specs/block_tests.json)。每项声明实际激励、负载、测量项目、诊断限值与未覆盖项；测试源直接保存在各模块的 `acceptance.scs`。

| 模块 | 测试台 | 测量 |
| --- | --- | --- |
| Bootstrap | [bootstrap/acceptance.scs](bootstrap/acceptance.scs) | 正常 60 ns 低 / 40 ns 高时钟；首帧、后续采样误差和保持漂移；50 Ω 输入及原生 MOM 负载 |
| CDAC | [cdac/acceptance.scs](cdac/acceptance.scs) | 单位到 MSB 的有效位权、四分之一 LSB 带内建立、满量程换向、保持；50 Ω / 4 pF 参考 |
| 比较器 | [comparator/acceptance.scs](comparator/acceptance.scs) | 正负多幅度判决、延时、复位；原生输出 MOM 与接收门负载；浮置 MOM 输入下的差分 kickback |
| SAR | [sar/acceptance.scs](sar/acceptance.scs) | 六个低/中/高码，首帧、8 次比较及更新、转换时间；管级 SAR 接电气 VA 环境；强制比较器不响应并检查下一采样撤销挂起 |
| 参考控制 | [reference/acceptance.scs](reference/acceptance.scs) | 预置、两次捕获、存储字、门控阈值非交叠；实际 CDAC 及开关栅负载 |
| RC / clear 延时 | [clock/acceptance.scs](clock/acceptance.scs) | 全部导出的延时/边沿辅助模块，上升与下降延时、脉宽、缺失边沿；原生接收门负载 |

比较器失调和 CDAC 静态位权的原生 MC 继续使用 [comparator/test.scs](comparator/test.scs) 和 [cdac/test.scs](cdac/test.scs)，不重复创建种子任务。

```powershell
python -m tools.saradc block list
python -m tools.saradc block prepare --module comparator --run-id sar8-comp-char-v1
python -m tools.saradc block sim --run-id NEW_ID
python -m tools.saradc block follow --run-id NEW_ID
python -m tools.saradc block sim --module reference --view behavioral --view reference=xtor --candidate reference=b --run-id NEW_ID
```

省略 `--module` 运行六项；可重复选择模块。`prepare` 只打包，`sim` 打包并登记一次，`follow` 只接续已有运行并回收。已使用的运行 ID 不重新生成或重提。

每次生成的 `test.scs`、模块 fixture、选择配置、来源哈希和 managed 配方位于 `work/blocks/ID/`。测量器是 [analyze_blocks.py](../../tools/saradc/measure/analyze_blocks.py)，结果在 [results/blocks](../../results/blocks/README.md)。它检查保存信号完整性，以流式方式测量实际波形。

分析器修复时：

```powershell
python -m tools.saradc block reanalyze --run-id NEW_ANALYSIS_ID --source-run COMPLETED_SIM_ID
python -m tools.saradc block follow --run-id NEW_ANALYSIS_ID
```

`pass_functional` 与 `diagnostic_screens_pass` 分开；完整 `pass_validation` 要求二者均通过。小信号不响应、门控交叠和未分配的时序限值保留，不从进程退出码推断电气合格。CDAC 建立时间相对有限长、且已检查稳定的尾段电压测量，不冒充无限保持 oracle。

当前测试不构成所有 PVT、局部失配、原生噪声概率、MOS 导通电流非交叠、器件可靠性和 PEX 的完整签核。VA 环境的负载/延时近似及统计范围见 [行为模型说明](../../design/behav/README.md)。
