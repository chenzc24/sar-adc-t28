# 精简异步 SAR：Canvas 门级审核入口

2026-10-20。当前 Circuit 为 **SAR8 Simple Async — Gate-level Controller**，
云端项目 `yc3a7geyrf`，保存版本2；顶层为 `sar_logic_8b_async_simple`。
只保留当前21种 cell，旧同步/握手/评审页面已从这个 Circuit 移除。
Virtuoso 旧 cell、历史源码及全部仿真结果没有删除或修改。

## 时钟整体逻辑

这是**固定采样周期、逐位自定时的异步 SAR**。外部只有10MHz的 `SAMPLE`，
没有200MHz位时钟。一次比较耗时随比较器判决变化，本地延时保证写入、
移位、比较器复位与下一次比较之间的顺序。

1. `SAMPLE=1`：比较器复位、停止回路；工作SAR字清零、位序回到T7。
2. `SAMPLE`下降：连接MSB试探码，经过预留建立延时，启动`CMP_CLK`。
3. 比较器P/N输出分出高低：接收器产生`DATA`；XOR及短资格延时检测判决，
   再由本地时钟缓冲产生`PHI_W`。原始比较器XOR不直接驱动DFF时钟。
4. `PHI_W`上升：8个SAR DFF都看同一写时钟，只有TOKEN选中的位取DATA；
   其他位的MUX反馈自身D，因此数值保持。`CODE = D OR TOKEN`。
5. 约0.46ns后（当前TT用例测量，不是全角点常量）`PHI_U`上升：位序推进、
   比较器复位；新CODE更新P/N底板参考选择。BBM立即断旧选择，延时接新选择。
6. 写入/更新脉冲结束，静默延时覆盖比较器复位及DAC建立后，再启动下一位。
   T0写完且移空后，`ACTIVE=OR(T7..T0)=0`抑制下一次启动，不产生第9次比较。

`ACTIVE`、`QUIET`等是内部组合节点，不是新的握手状态。唯一时钟状态锁存器
是比较器时钟SR；另外16个DFF分别保存8位位序和8位工作码。没有独立
RST_N/START/ACCEPT/RESET_OK/DEADLINE/EOC及第二组输出寄存器。
DFF内部仍需初始化端，直接由SAMPLE控制，不能把“无独立复位入口”理解为
“触发器没有复位”。输出在转换中逐位变化，到下一次采样时清零。

## 按模块审核

| 打开的 cell | 内容 |
| --- | --- |
| `sar_logic_8b_async_simple` | 时序、位序、8个SAR位、P/N驱动及7个OR组成的空链检测树 |
| `sar8s_timing` | 比较器接收/判决检测、写入/更新延时、静默间隔、比较器时钟SR |
| `sar8s_bitseq8` | XF7..XF0；第一位用反相输出实现SAMPLE置T7，不增独立set信号 |
| `sar8s_bit` | MUX + 上升沿DFF + 试探OR；在顶层独立实例化8次 |
| `sar8s_bp_p8` / `sar8s_bp_n8` | 各8个BBM slice；N侧交换高低参考选择，非简单倒相最终驱动 |
| `sar8s_bp_slice` | CODE/SAMPLE生成两路请求；每路“请求 AND 延时请求”实现先断后通 |
| `sar8s_dffr` / `sar8s_sr` / `sar8s_mux2` | 继续展开状态及选择电路 |
| `sar8s_delay_{quiet,valid,write,bbm}` | 两级10k RC/反相器，加快速回零MOS；C种子分别150/5/20/5fF |

短距离内部链路用导线连接，跨区/公共控制使用**电气绑定的同名网络标签**，
不是装饰文字；同名只在所属Cell内相连，父子通过明确端口映射连接。
门符号绑定到本项目的真实CMOS子cell，而不是用理想门替代原实现。
部分触发器/MUX采用可展开的层级符号，内含完整源图连接。

## 验证与边界

Canvas原生结构比较对21个cell返回`status=equal, topology=equal`，器件、
目标子cell、端口集合、节点成员、绑定及参数均无差异。端口顺序不是本次
图面要求，因此比较中关闭了`portOrder`，没有关闭连接或参数比较。
21个cell逐页检查均0错误、0警告；全部PNG导出并人工式视觉检查。
证据见 `verification/sar8_simple/canvas.json`。

这里是**完整控制器门级/CMOS连接的审核投影，不是完整物理ADC**。
Canvas仅保存`nch_mac/pch_mac`模型名和尺寸，未上传PDK模型卡或运行T28
瞬态仿真。既有原生仿真边界仍以[sar8_simple_async.md](sar8_simple_async.md)
为准：FF器件应力、真实CDAC/采样/参考整合与全PVT验证尚未关闭。

本地生成器 `scripts/sar8_simple/canvas.py` 只写离线投影和参考SPICE，不连接
网络、不改变OA。必须通过MCP显式应用并重新verify，不能将本地生成成功
等同于Canvas修改成功。

## 备份与恢复资料

- 旧Circuit完整备份：`output/sar8_simple_canvas/before-sar8-simple.analog.json`。
- 新Circuit保存后导出：`output/sar8_simple_canvas/final.analog.json`。
- 顶层SVG、21个PNG及结构参考：`output/sar8_simple_canvas/`。
- 旧页面可从本地备份恢复；没有发布到Gallery，没有Git push。
