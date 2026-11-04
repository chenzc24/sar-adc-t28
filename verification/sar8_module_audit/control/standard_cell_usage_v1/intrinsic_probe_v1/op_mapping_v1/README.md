# MM65 原生字段暴露诊断包

**唯一测量包已准备，尚未注册或运行。** 保留直连基线 20 ns 电路、PWL、真实负载及完整功能／应力测量，只追加四条静态 info 输出。ids/id 若暴露，仅按原字段名记录，不称纯沟道电流，也不作为验收门槛。

| 项目 | 冻结内容 |
| --- | --- |
| 原电路 | 原生 DFCNQD1、58 MOS、348 端对及三个真实 Q 首级负载；dut.scs 原 SHA 不变。 |
| 原测量／时序 | 36 V、73 I、六个完整 KCL 节点，全部原 save 和 tran 语句原样保留；未加瞬态 OP group 或强制时间点。 |
| 条件 | FF／0.99 V／−40°C，20 ns；理想外部电源／命令，无噪声、失配、PEX。 |
| 唯一 deck 增量 | info what=primitives/inst/nodes/oppoint，使用已核实的 where=file、descriptions=yes 等参数。 |
| 回收范围 | 只提取 MM65 的原生别名、端口、字段名、显式单位及 ids/id 原始值文本；未知项保留 unknown，不猜 .M1。 |

## 语法依据

经补充授权，当前安装的两个帮助主题各完成一次只读查询，耗时 0.350／0.370 s，均受 8 s／512 KiB 限制，无 CIW、远端文件或仿真。证据：[info](installed_info_help.json)、[save](installed_save_help.json)。原缺项说明属于查询前阶段。

帮助确认 what=nodes 提供端口到节点映射，what=inst 提供实例输入信息，what=oppoint 给出解相关 OP 信息。inst=[...] 在该帮助中属于故障生成参数，不能借用作普通实例过滤。因此静态 info 文件会描述这个小电路，回收程序只筛选 MM65；不返回实例／几何参数正文，也不请求模型参数正文。

静态 info 可验证字段暴露，无需把整套 :oppoint 加到原始瞬态中。这个 OP 没有绑定 5 ns、5.5 ns 或 5.95 ns，值不能用于那些时刻的物理归因。原总端流、功能和全部应力分析复用已验证 gzip 流程。

## 有界回收

四份 info 写入本次 managed run 的 raw/，每份分析读取上限 2 MiB；原文件留在远端。回收仅保留元数据、选定单位／值和文件 SHA。文件缺失、未知格式、重复字段或未暴露字段都会明确记录，不自动改路径、追加字段或再跑一次。字段存在只证明暴露能力，TMI 本征含义、反向 VDS 符号及缩放仍未核定。

建议 run：sar8audit-ctrl-mm65-opmapping-ff-v1。17 项输入、179875 B；沿用 1 线程，仿真 1 GiB／300 s、分析 256 MiB／300 s。由主会话按 managed 流程提交。

最终 recipe SHA：95fddc61431ffd0980449765901a4ad6c52e64c6cfdefeeea6f833d9d26047fb。
冻结前仅修正一次报告标题过滤，旧草稿 5c5c4e58… 不供提交，见 [precheck_revision.json](precheck_revision.json)。

[精确差异](single_measurement.diff) · [manifest](manifest.json) · [freeze](freeze.json) · [建议 recipe](recipe.suggested.yaml) · [一次静态一致性检查](validation.json)

原基线 13 项输入及所有电气依赖保持只读。未启动仿真／重分析，未改标准库、提交或 push。这项能力检查不阻止其他模块继续诊断。
