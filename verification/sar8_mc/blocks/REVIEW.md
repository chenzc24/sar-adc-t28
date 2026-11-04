# B 版 CDAC 和比较器 Monte Carlo 审查入口

本分支收录 64 个最终 v2 案例。每个模块的种子为 4101–4130，另有一组名义对照和一次 seed 4101 重复。先读 [实验报告](README.md) 和 [测试台边界](methods.md)，逐种子结果在 [samples.csv](samples.csv)，数值告警原文在 [monitor_v2_evidence.json](monitor_v2_evidence.json)。

逐运行的输入位于同名 `sar8mc-*-v2/` 目录，派生测量在 `results/<run_id>/result.json`。[回收摘要](result_receipts.json)记录了运行配方和结果的 SHA256，以及仿真、分析退出码。这些哈希来自原始回收回执。

在仓库根目录使用 Python 3.11+、NumPy、Matplotlib 复核。

```sh
python scripts/sar8_mc/test_blocks.py
python scripts/sar8_mc/validate_blocks.py
python scripts/sar8_mc/report_blocks.py
```

前两项检查权重与门限测量，最后一项先校验结果哈希，再重建汇总和图。制图软件版本可能影响图像的字节级哈希。一个依赖历史原生 AC 波形的测试在该文件缺席时会跳过。

冻结网表是本项目的电路设计。测试台用 include 指向服务器上的工艺模型与标准库。重新仿真需要有权使用这些模型的 Spectre 环境，以及实验服务器的 managed runner。复核现有数据只需本分支文件。生成器用于在空的目标目录生成 v2 测试台，已有案例目录受覆盖保护。

v1 的 CDAC 实例合并问题见 methods.md。归档结果仅包含 v2。请分别审查 CDAC 的线性化权重预测、比较器诊断窗口内的有效门限，以及数值告警样本 4101 和 4124。
