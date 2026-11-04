# X020 CMID：唯一单变量实验

以已回收的 `sar8audit-ctrl-mp1floor-v1` 为基点，只将私有
`XDUT.XCTRL.XTIM.X020.X000.CMID` 的 `multi=2` 改为 `multi=1`。
不是修改通用 NAND，也不改其他实例。单位 MOM 几何与原 `sar8p_sr.CQB`
完全一致，未引入新几何或拟合电容。

目的：减少 MID 的待释放电荷，检验上管 MN0 能否更早从 N 吸收电流。
原 floor 在 N 达峰时，MN1 漏端约846 µA、CMID 向 MID 释放约785 µA，
N 流入 MN0 漏端仅19.7 µA。该假设需要仿真验证，不能据此判定修复。

- 网表仅一个字节变化；[精确差异](electrical_change.diff)。全部101个 MOS、
  4个栅极支路电阻及其他电容保持；总计22个无源实例。
- `test.scs`、11份 PWL、冻结的 `full_gate_analyze.py` 均字节一致。
  0.99 V、FF、−40°C、外部采样窗口和关闭沿、Spectre参数保持。
- 原64个电压、444个端电流、16个重点节点 KCL、QUIET时序及边沿数、
  五个源的全史能量均保留。原生 CMI 日志保留；显式联立端压观察仍是
  MP1 VSG/VGD、恢复反相器 NMOS VGS 三项，并不声称已覆盖所有端压。
- 15个声明输入，4,422,728 B；1线程，仿真1 GiB/900 s、分析256 MiB/600 s，
  使用父会话统一串行调度。本会话没有登记或远端操作。

交付入口：[recipe.suggested.yaml](recipe.suggested.yaml)。
recipe文件SHA256：`8fcc66eee7c99f49ed7f539f6f9de3af929ae60b3c6354ad21fe140e8c95cb43`。
输入散列与结构核对见 `freeze.json` 和 `change_manifest.json`。

验收需同时观察 N/栅极端压、MID放电与N吸收电流、QUIET单边沿和延迟、
静态电流与能量。减小电容不一定能消除过冲；已有 floor 的静态功耗代价
不会因此自动消失。仅是首事件机理实验，尚未仿真，不代表整周期或整机合格。
