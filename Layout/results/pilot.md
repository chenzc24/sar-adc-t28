# T28 MOM 小试验结果

完整差分 CDAC 的后续实现和验证见 [完整 CDAC](cdac.md)。本页保留单位与三颗 MOM 试验的独立证据。

本记录仅覆盖冻结 B 版的一颗单位 MOM 和三个单位组成的 1∶2 阵列。PCell 回读为 `Nfinger=8`、`Lfinger=2u`、`Wfinger=Sfinger=50n`、M1–M3，每颗外框 `0.76 × 2.42 µm`。阵列外部端口 `TOP`、`B0`、`B1` 均在 M3，LVS 参考来自独立的 [reference.cdl](../tb/reference.cdl)。

| 操作 | 证据目录 | Calibre 结果 |
| --- | --- | --- |
| 单位 MOM | `unit-verify`，OA/GDS 来自 `unit-check` | 1 颗、2 个端口，LVS `CORRECT`；DRC 保留 2 条提示 |
| 1∶2 基准 | `ratio-clean` | 3 颗、3 个端口，LVS `CORRECT`；DRC 保留 2 条提示与 1 条多晶硅密度标记 |
| 断开其中一颗 B1 底板 | `ratio-open` | LVS `INCORRECT`：B1 连通性错误，版图 4 个网络、参考 3 个；三颗器件仍识别 |
| B1 的 M3 引出从 0.5 µm 改到 3.5 µm | `ratio-reroute` | LVS `CORRECT`；DRC 标记同基准 |
| 恢复 0.5 µm | `ratio-rollback` | LVS `CORRECT`；DRC 标记同基准；GDS 结构散列与基准完全相同 |

2 条提示为 `IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1` 和 `DIODMY_L:WARNING`；试验单元没有 IO MOS 或低漏电二极管。阵列另有 `PO.DN.3.1`，这是保留的局部多晶硅密度结果，需要在完整布局与填充环境中处理。第一轮 `ratio-baseline` 还发现 TOP 焊盘与走线交界的小台阶；在同一工作 cell 调齐两者宽度后，`G.4:M3i` 和 `M3.W.4` 标记消失。未关闭相应 DRC 规则。

首轮试验回滚时，`SAR8_MOM_PILOT/sar8_mom_ratio/layout` 恢复了基准几何。基准与回滚的 GDS 结构 SHA-256 为 `3c0ec316ef1ca1a5d0255c55483fa74334d928b057f7dbf426e5254ab715b8f4`。

基础 RC deck 的诊断提取同时保留三颗原生 `cfmom_2t` 模型，显式的 TOP–B0、TOP–B1 耦合还分别达到约 3.554、7.118 fF，接近模型本身的量级。实验室 PEX runset 包含 MOM 器件区电容排除指令，单用基础 deck 不会读取。最终提取 `ratio-mom-base`、`ratio-mom-reroute` 在原 GDS 上应用这组指令；两份输出均有三颗 MOM 模型与剩余网间耦合。

| 提取量 | 0.5 µm B1 引出 | 3.5 µm B1 引出 |
| --- | ---: | ---: |
| TOP–B0 显式耦合 | 0.513070 fF | 0.513070 fF |
| TOP–B1 显式耦合 | 1.035125 fF | 1.035125 fF |
| B0–B1 显式耦合 | 0.000644 fF | 0.000644 fF |
| B1 对地寄生电容 | 0.680357 fF | 0.847306 fF |
| B1 引出变化处的串联段 | 0.788411 Ω | 6.419920 Ω |

比较两份提取网表，忽略注释后只有 B1 的两个对地电容项和一个电阻项改变。B1 额外增加 0.166948 fF，支路间显式耦合没有变化。完整报告和失败证据在 `/server_local_ssd/chenzc_intern25/sar-adc-t28/layout-mom-pilot/evidence/`。典型 RC 角的 xRC 两轮均为 0 errors；分布提取保留 30 条警告，格式化保留 5 条警告，原文随证据归档。

## 固定测试台的前后仿

TT/27 °C，0.45 V 共模与 TOP 初态，100 mV 阶跃、2 kΩ 驱动、4 fF 顶板负载。两组仿真均到达 9 ns，实测最大步长设置为 1 ps。初次测试台靠 1 TΩ 回拉建立 DC；Spectre 触发 `SPECTRE-17191`，导致后仿初始 TOP 为 0.404428 V。该轮结果只作为诊断保留（`layout-mom-base-tt`、`layout-mom-long-tt`）。最终测试台显式指定前仿和后仿 TOP 为 0.45 V，并在初始点和各阶跃前检查 10 µV 容差；最终两次均通过此检查，DC 容差放宽告警消失。

| 测量量 | 前仿 | 基准后仿 | B1 加长后仿 |
| --- | ---: | ---: | ---: |
| B0 有效电容 | 4.00347 fF | 4.51643 fF | 4.51643 fF |
| B1 有效电容 | 8.00682 fF | 9.04194 fF | 9.04195 fF |
| 有效电容比 B1/B0 | 1.99997 | 2.00201 | 2.00201 |
| B0 的 TOP 阶跃 | 25.006 mV | 24.290 mV | 24.290 mV |
| B1 的 TOP 阶跃 | 50.013 mV | 48.629 mV | 48.629 mV |
| B0 的 0.1% 建立 | 76.33 ps | 93.57 ps | 95.29 ps |
| B1 的 0.1% 建立 | 71.38 ps | 88.94 ps | 91.09 ps |

前后仿有效电容的差值与提取的显式耦合相符。单改 B1 引出长度后，有效电容比与最终阶跃基本不变，B0、B1 的建立分别多约 1.7 ps、2.2 ps。这是 1 ps 最大步长下的小阵列对照；未做积分或时间网格收敛，也未纳入整侧 CDAC 的匹配、填充和布线负载。

最终 managed Run 为 `layout-mom-base-ic-tt`、`layout-mom-long-ic-tt`，仿真及分析均完成。两轮均为 0 errors、1 条 `VACOMP-2435`（旧 AHDL 环境变量被忽略）。[精确测量与运行散列](measurements.json)记录了两轮的小结果；原始波形和日志留在对应 Run 目录。

## 三颗 MOM 的紧凑版及参考开关

在同一工作 cell 内将三颗 MOM 改排为 B1–B0–B1，中心距 0.96 µm，单元间隙 0.20 µm。电容行的几何宽度由 4.76 µm 收到 2.68 µm。B1 的两支在 M3 汇合，中间 B0 从 M2 穿过。两条底板线各接到对应 PMOS 和 NMOS 的漏端，四个开关栅极、参考端和体接触均已引出。

原参考开关每个支路采用并联单指管。这里将其折成 B0 三指、B1 六指，保留每指宽度和栅长。最终独立 CDL 的 LVS 为 `CORRECT`。Calibre DRC 留两条 deck 提示和一条 `PO.DN.3.1` 多晶硅密度标记，未发现器件或布线几何违规。

最终验证目录为 `evidence/ratio-compact-sw3`。DRC、LVS 和截图使用的 GDS SHA-256 为 `dcd830c164b841a37ce1ed86771ee43808ae85e20ae93f18d1b9bdb722f2d`。
