# XDRV0 FF冷案例的重放证据检查

结论：原规格所需边界尚不齐，未生成deck。检查只涉及
`sar8fix-loaded-ref-ffcold`，独立命令字仍为243/12。

已核对的本地来源为
`output/managed_execution/runs/sar8fix-loaded-ref-ffcold/collected/derived/`：
`wave.events.tsv`是原生0.5VDD交越；`wave.columns/meta.json/bin`是7997点、
210列紧凑波形，实际点间隔20–30ps；`wave.extrema.tsv`保留原生极值。
六份文件的路径、字节数和SHA见`replay_evidence_audit.json`，其中五个回收文件
的字节与散列均匹配collection receipt，receipt本身散列在本地计算。
核心单次读取13,563,878字节；连同小文件与源码核对，保守总读取上界16MiB，
低于32MiB限制。大波形二进制只读一次，并从同一内存校验和解析。

| 边界 | 原生事件记录 | 紧凑列 | 判断 |
| --- | --- | --- | --- |
| PHI_U | 16升/16降 | 有 | 顺序可查，原生边沿形状不足 |
| CAP_CLK | 32升/32降 | 有 | 两帧捕获输出时序可查 |
| CAP_REQ | 未记录 | 无，仅极值 | 缺少原定CAP缓冲输入 |
| RST0…7 | 每位2升/2降 | 有 | 初态与时间可查，原生斜率不足 |
| SEQ_SAMPLE / CMP_CLK | 有 | 有 | 可定位采样/比较，原生斜率不足 |
| CODE0…7 | 未记录 | 无，仅极值 | 缺捕获前后输入时序证据；命令值仍独立生成 |
| XDRV0 GNNA/GNNB/GNNDRV | 未记录 | 无，仅极值 | 不能还原内部尖峰过程 |

“未记录”表示没有选入本地事件导出，并非该信号没有跳变。冻结test.scs确实
保存了CAP_REQ、CODE及driver0节点电压，因此将来可从历史raw流式抽取已有
电压。GNNRG及电阻内部串接点未保存，XDRV0四端电流与LSB参考开关电流
也未在原测试保存；这些需要未来显式测量，不能凭电压导出补造。

推荐最小逻辑闭合：在既定捕获岛外保留原`X000/X001/X002`早相缓冲、
`X007/X003`组合逻辑、`XREQUEST`、`XD_LATE_CLK/XD_ACK`，由物理SR/RC
产生CAP_REQ。边界上移到已有记录的PHI_U与SAMPLE_INT，不需要完整异步SAR。
此选项仍需解决输入斜率和接收负载匹配；另一条路是补回原CAP_REQ原生电压。
两条路都不能把CAP_CLK输出沿简单前移后冒充CAP_REQ。

后续XDRV0归因需同步局部节点、电流及Rgate回流，闭合GNNDRV/GNNB节点KCL。
本轮没有借用GNN4电流来解释XDRV0，也没有展开历史L90测试台。
