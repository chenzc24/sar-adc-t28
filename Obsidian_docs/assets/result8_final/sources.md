# Result 最终结果配图

图片由脚本 `scripts/reporting/result8_final_figures.py` 读取已保存的仿真数据绘制；没有新增仿真。PNG 用于笔记阅读，SVG 用于放大；数据和图片指纹保存在 `manifest.json`。

| 图 | 实现与来源（路径相对仓库根目录） |
| --- | --- |
| 1 电气宏模型 | `output/eight_bit_flat/electrical/macro8_code_192_*`；理想电容、有限 Ron 开关、gm/C 比较器、VA 控制。共模按正常电压刻度显示，细小数值波动不放大。 |
| 2 采样开关 | `output/eight_bit_flat/bootstrap/boot8_w1u_only_new_vdp800_*`；沿用移除旧对照支路的独立检查网表，已选 1 µm 电路不变。保持误差仅在参考交接完成后显示。 |
| 3 MOM 阵列 | `output/cdac8_device/banks/summary_200.json`；200 次 PDK 局部电容 MC 和解析静态转移，非整机开关 MC。 |
| 4 比较器 | `output/strongarm8_baseline/waves/det_nom_p.json`；真实 StrongARM 初始尺寸，图示第一周期，5 fF/输出。 |
| 5 异步控制 | `output/sar8_simple/waves/two_cycles_simple_v2_aps.json`；只画最终 simple_v2 第一帧，35–80 ns，模拟端口为行为模型。 |
| 6 当前合龙 | `output/b_sine_period/waveform.pickle` 与 `summary.json`；已采用 R3＋B、1 µm，第 5 帧的 435–478 ns 窗口。 |
| 7 连续输入 | 同一 B 正弦数据；保留 4 帧启动与 20 个观察点，采样基准不移动，保持在 SAMPLE 下降 50% 后 0.6 ns 读取。 |

时序线均来自原始模拟电压，未替换成理想方波。顶板共模为 `(TOPP+TOPN)/2`，差模为 `TOPP−TOPN`；工作码按各位实际电压的 VDD/2 门限解码。图 7 仅为平滑源正弦的显示抽稀，全部测量点保留。

每图顶部标明环境、负载、模块实现、理想源及噪声／失配状态。当前 Result 展示已采用实现；旧图和过程证据仍保留在仓库历史报告与 `assets/result8/` 中。
