# timer 修复图来源

原生 Spectre 21.1 APS 保存波形：`output/r3_refgate_events/a/` 与 `b3/`。
两组均从零完整重放原 12 帧输入历史；本图仅显示第 9 帧，绝对时间
800.9–843.5 ns。输入差分在采样期间保持 −442.529296875 mV。

T28 TT、0.9 V、27°C；无噪声／失配。Bootstrap、MOM、3×参考 pass MOS、
StrongARM 和 SAR 为管级；参考栅控、COMMIT、外部采样及供电仍理想化，
Cboot 和延时 RC 仍为理想元件。输入每侧 50 Ω，参考每轨 50 Ω＋4 pF。
对照只改变参考栅控事件处理，器件尺寸、名义时序及求解参数不变。

图中 N7 是 N 侧 MSB 电容底板，初始参考字要求它接 VREFP≈0.9 V。
“恢复初始参考字”不等于所有底板接 VCM。底板换轨需经真实开关建立，
不能将 timer 到达时刻等同于底板已经建立完成。

下栏为 `(TOPP−TOPN)−当帧恒定输入`；采样接通期间只称电压差，
841.65 ns 圆点才是保持误差测量。第一次比较约在 843.698 ns，位于图外。
原 A 为 −442.850497 mV、最终码 1；B 为 +0.101355 mV、最终码 65。
最终码取 898 ns 原生 D7..D0。保持值及码字均从保存波形重新读取。

事件证据：[修复报告](../../../docs/r3_refgate_events.md)；
受控数据：`verification/integration/r3_refgate_events_results.json`。
脚本 `scripts/reporting/wrapup_timer_figure.py` 验证原始 pickle 的 SHA256
与 receipt、受控结果一致。`manifest.json` 保存输入及输出哈希。
图线为原始保存点连线；没有平移、滤波、校零或新增仿真。

```powershell
.venv/Scripts/python.exe scripts/reporting/wrapup_timer_figure.py
```
