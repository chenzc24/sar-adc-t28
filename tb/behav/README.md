# 行为视图交叉测试

[observer.va](observer.va) 从真实输出引脚电压独立解码，探针不读取行为模型的内部码字。

由 `python -m tools.saradc behav prepare` 在 `work/behav/<run_id>/` 生成确定性的 Spectre deck、2050 个输入、8 种非理想/故障情形和 Python 预期表。测量在每帧采样关闭后 55 ns 读取输出；截止或停滞记录还保留具体失败位。

源模型在 [design/behav](../../design/behav/README.md)。数据集包含 256 中心码、765 边界探针、5 个饱和/零输入和 1024 个既有原生 FFT 源电压采样值。只有行为视图接收这些合成输入，不重跑晶体管全码或 FFT。

新运行使用不同 managed 身份，冻结 spec、VA、观察器、Python 模型哈希、输入与期望表；同一 ID 不接受变动后的输入。默认 4 线程、仿真 RSS≤1 GiB、分析≤256 MiB，由现有队列准入。
