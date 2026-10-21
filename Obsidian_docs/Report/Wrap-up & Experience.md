---
title: 8-bit SAR ADC 晶体管级设计总结
updated: "2026-10-21"
---

# 8-bit SAR ADC 晶体管级设计总结

## 1. 知识基础

快速浏览《现代模拟集成电路设计》与 IC Design《SAR ADC》专栏。

| 模拟电路基础 | SAR ADC 专题 |
| :---: | :---: |
| ![[Pasted image 20261021112406.png\|160]] | ![[Pasted image 20261021112457.png\|400]] |

## 2. Bootstrap Switch 设计

| 旧拓扑 | 新拓扑 |
| :---: | :---: |
| ![[Pasted image 20261021113121.png\|320]] | ![[Pasted image 20261021112932.png\|320]] |

旧版：获取速度已满足，但保持误差与核心管过压未解决；尺寸和时序优化仅将历史夹具的最坏误差从 12.03 mV 降至 9.10 mV。

新版：采用 T28 1.8-V MOS 与真实反相器；主管 1 µm 时，8-bit flat 五点台阶测试的最坏保持误差为 0.126 mV。

R3＋B 连续正弦短测（TT／0.9 V／27°C，500 kHz、差分 ±0.8 V）：

| 主管 W | 原始保持误差峰值 |
| --- | ---: |
| 1 µm | 4.465 mV |
| 2 µm | 2.242 mV |
| 3 µm | 1.519 mV |

3 µm 尚未写回 OA；加宽改善跟踪，也增加关断扰动。

## 3. SAR Logic 设计

两版均为 T28 CMOS 控制器＋理想模拟测试台。TT／0.9 V／27°C，差分输入＋0.123 V；两图各一个 100 ns 周期，0 为 SAMPLE 上升沿中点，浅底为采样阶段。

### 旧版：多层确认与保护

加入判决确认、复位确认、超时和独立输出锁存，保护上一帧结果，但增加了等待与跨帧状态。SS／0.81 V／125°C 下，截止前仅完成 7 位。

![[assets/sar_logic_compare/old_one_cycle.png|640]]

### 新版：简化位循环

SAMPLE 初始化后，按“比较→写入→推进／复位→建立等待”循环，八位完成后自然停止，取消独立输出银行和 EOC。

![[assets/sar_logic_compare/new_one_cycle.png|640]]

CAPTURE／PHI_W 为写入，ADVANCE／PHI_U 为换位；时钟行均为 0→0.9 V，总线为实际寄存器引脚解码的十进制值。

| 实现规模 | 旧版 | 新版 |
| --- | ---: | ---: |
| 原生 cell 种类 | 26 | 21 |
| 展开 MOS 数 | 1742 | 1476 |

新版 13 项有界测试的功能／时序检查通过；FF 应力仍未通过，比较器卡住时可能留下部分码。

## 4. 项目结构

历史版本、候选和基线混存，登记也未同步：10 月 20 日清点时，15 条登记无对应 cell，实际库另有 42 个 cell 未登记。

| 位置 | 保存内容／当前入口 |
| --- | --- |
| 本地 Git | 配置、脚本、报告和版本记录 |
| 远端 Virtuoso OA | 原理图与器件连接 |
| 当前顶层／测试台 | `sar_adc8_join_r3`／`tb_sar_adc8_join_r3`，已接入 B 修复 |

冻结版本时同步记录 OA、导出网表、模型和结果目录的对应关系。

## 5. 长仿真前先验证历史与统计是否有效

12 帧重放定位到 timer 回调被重复时间比较拒绝，导致参考在采样关断后才恢复。B 修复改为由有效回调推进状态，器件尺寸不变。

| 第 9 帧 | 修复前 | B 修复后 |
| --- | ---: | ---: |
| 输出码，预期 65 | 1 | 65 |
| 保持误差 | −442.850 mV | ＋0.101 mV |

电容 MC 也曾出现“有随机变量、无实际散布”，启用 mismatch 后才继续统计。

长任务前先跑连续短测，检查跨帧复位、每帧八次比较／写入／更新及真实参数散布；异常重放保留完整前导历史。

> [!info]- 仓库依据
>
> - 开关：[初版与尺寸扫描](../../docs/bootstrap_driver_design.md)、[放电优化](../../docs/bootstrap_driver_error_reduction.md)、[电流路径](../../docs/bootstrap_current_path_audit.md)、[先关断再复位](../../docs/bootstrap_isolate_before_reset.md)、[历史隔离方案](../../docs/sampling_architecture_status.md)、[新旧完整负载对比](../../docs/canvas_bootstrap_full_cdac.md)、[八位迁移](../../docs/eight_bit_flat_migration.md)、[最新主管宽度对比](../../docs/b_sine_main_w.md)。
> - 时序：[旧握手控制器](../../docs/sar8_async_implementation.md)、[精简异步控制器](../../docs/sar8_simple_async.md)。
> - 版本：[项目状态与清单](../../docs/project_status.md)、[B 修复同步 OA](../../docs/r3_b_oa_adoption.md)。
> - 短测：[12 帧事件修复](../../docs/r3_refgate_events.md)、[电容失配验证](../../docs/cdac_flat_8b_device.md)。
