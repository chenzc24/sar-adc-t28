# 下一项：给 MP1 栅极留正电位余量

可直接使用 [recipe.suggested.yaml](recipe.suggested.yaml)，运行名
`sar8audit-ctrl-mp1floor-v1`。仅在 MP1shape 上增加一条 VDD→3只相同原R0→B_PM
支路；原器件、连接、全部PWL、供电和外部采样沿不变。

已有串联栅电阻为R，上拉支路为3R，低态近似 `B_PM=(VDD+3×LIVE)/4`，实际
值由加载后的DC解确定。它直接给VSG/VGD留余量，并弱化MP1早期保持作用；
不继续仅靠增大R减峰，也没有新理想偏置源、时钟或拟合电容。

新增静态电流粗估约25µA、25µW（0.99V、当前R约9.79kΩ），不是实测。
必须同时检查低态LIVE、N是否仍超轨、B_PM端压、QUIET边沿/延迟及功耗代价。
原101 MOS保持，合计22无源器件；64V/444I/16项关键KCL。

新独立分析器对0到END的每个原生点计算MP1 VSG/VGD、恢复反相器NMOS VGS和
VDD/4路条件偏置源的带符号能量；不以诊断窗口代替全程，也不宣称整机功耗合格。
一次“最大越界位于诊断窗之前”的合成数据及解析能量测试通过。

验证命令：项目虚拟环境运行 `prepare_mp1_floor.py`（唯一新增支路、参数/PWL
不变断言），然后运行 `test_gate_observer.py`。无新增远端操作，主聊天串行执行。
