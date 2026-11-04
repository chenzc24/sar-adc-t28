# 手搭SAR逻辑隔离研究：首轮测试定义

用户要求本聊天研究SAR，先给出测试指标、TB搭建逻辑、理想模块状态、输入与DFF监控。当前只定义实验，不提交新仿真。

Owner root。所有权：本计划；verification/manual_adc/sar_isolation_v1/test_contract.md；追加plan/log.md。远端/OA所有权none；无远端操作。只读依赖为candidate_io_v1/dut.scs、behavioral_v1、stress_diagnosis与标准库/PDK。当前分支ahead31且有大量其他任务未提交内容；本次仅新建上述文件，保留已有变更，不commit/push。

步骤：核对原生SAR门级连接与VA边界；明确功能/时序/电气/功耗目标与假设；分别定义已知判决序列隔离及理想模拟闭环；列出三类32个DFF与代表内部节点；记录未测量的真实负载、库时序约束及首次功能/端压未知。

验证：源网表映射人工核对、Markdown表格检查、scoped diff --check。不将本次拟定目标当作已有结果，不将热码误作独热，不将无栅负载VA当真实接口，不将RC版时序移植为理想delay验收。

完成：test_contract.md已形成。保留0.81–0.99V、8bit/10MS/s、外部采样窗口/关闭沿；本轮从TT0.9V27C与50ps激励边沿开始，40ns转换预算/1ns复位与输出建立/100uW数字电源预算均标为拟定子模块目标，后续PVT按相同边界验证。未启动仿真。

## 2026-10-27 用户授权开始测试

本次推进TB-A，功能与握手确认后再运行TB-B，保持原生17个理想delay，不用RC替代。新增所有权：verification/manual_adc/sar_isolation_v1/全部新文件；scripts/manual_adc/sar_isolation_*.py；management/recipes/manual8-sar-{a,b}-tt-v*.yaml及对应management/runs记录；output/managed_execution/runs/对应案例；远端仅/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/对应唯一managed案例。OA所有权none。只读依赖和其他任务脏文件保持原样，管理脚本已有修改为共享依赖，只调用不编辑。不commit/push。

实施：事件响应器按DUT比较时钟发码，首轮16帧；全部32DFF端口与十个代表DFF内部端压保存，说明内部覆盖范围，不能宣称所有门电气通过；静态参考栅复制负载与5fF输出负载；Py2兼容流式分析，输出功能、时序、六端压、功耗和精简波形。若功能失败先定位，不修改用户拓扑或扩大PVT；数值失败保留日志，不擅自换RC。TB-B复用已通过原生检查的VA采样/CDAC/比较器。

验证：构建时核对原生SAR原文一致、32DFF连接映射、VA事件取消；managed原生结束及日志、16帧预期码/8步热码/复位与输出时序、代表MOS同一时间点端压、实际资源和solver设置；检查最终波形图。端压与功能独立报告，未知库时序约束保持unknown。资源1线程、仿真<=1GiB、分析<=256MiB、回收<=32MiB；单重任务，不重复提交。

TB-A v1因响应器小数常量缺前导0编译失败，v2修复后在67.1684ns因SPECTRE-16928退出；原delay输出net32/CMPCKe有16780/16191，实际reltol=1e-7。日志和失败原波形保留。准许v3仅更换17个理想延时的实现：数字阈值事件+transition传输延时，trf=50ps，延时参数补偿半边沿使50%到50%仍为2ns/100ps；保留原门/尺寸/扇出。此为逻辑延时抽象对照，不宣称模拟波形delay严格等价；单独核对17路径实际50%延时及原生数值警告，未改OA/库。首帧前未初始化启动活动单独记录，不隐瞒。

v3运行中观察到conservative实际reltol=1e-7导致波形量超过原预估趋势，既有任务保持原预算，不修改运行中限制。若触发预算失败，v4仅在tran显式指定reltol=1e-6（原options意图），其余v3条件、保存范围和预算相同；必须核对实际设置，不声称等精度加速。较严失败案例的原始数据保留，不当完整结果。先获得16帧功能/失败窗口，再按需要对短窗口加严；不批量扫数值设置。

v3由managed输出预算在2GiB终止。v4读回仍为1e-7，查本机Spectre 21.1原生tran帮助确认conservative将options.reltol乘0.1，tran直接reltol未覆盖。因此核对v4 managed child boot/PID/start/cmdline后SIGINT停止这个冗余对照，由原managed worker收尾，不改状态文件；保留停止回执。v5将options.reltol设1e-5以得到实际1e-6，其余不变，要求实际读回。该操作不提高原输出/内存预算，不改变电路。

用户随后明确要求放宽资源上限。当前服务器仍有约278GiB空闲，运行RSS约330MiB，问题为本任务低估输出预算。后续新注册案例改为8GiB输出、仿真3600s、分析1800s；仿真1GiB/分析256MiB/单并发/回收32MiB保持。v5已经启动且文件大小硬限已固化，不修改冻结配方或运行身份；让它继续，有完整结果直接采用该结果进入B；仅若触及旧预算则用同电路/同实际容差/同保存范围v6新身份续跑，明确记录预算变化。未注册B配方直接更新预算。无需修改共享管理脚本/全局策略。

## 最新范围纠正：仅端压定位

用户指出重复两轮对当前端压定位没有必要。接受纠正：16帧是过度引入功能回归，不能把正常复位代表窗口等同于必须重复整轮8码。已停止本地sar_isolation_flow.py串行控制器，取消TB-B自动注册/提交；TB-B尚未运行。核对时v6已到869.58ns、运行约299s，第一轮已经过去；在途v6保留运行以取得可直接分析的完整原生文件，不再重跑/追加案例。只对启动复位、正常复位、代表数据翻转窗口做端压分析；不要按旧自动流程推进闭环、PVT或更多码点。后续新端压实验缩至约120–220ns、必要代表DFF与驱动/内部端节点；是否扩展由具体新问题决定。

## 已有结果回收：不启动新测试

用户要求回收现有结果、仅看几个端压窗口并画相关DFF波形。新增精确所有权management/recipes/manual8-sar-a-v6-stress-windows-v1.yaml及对应managed运行记录/output/远端分析目录；只运行kind=analysis_only，绑定完成的manual8-sar-a-tt-v6。脚本sar_isolation_stress_windows.py在已有0–220ns原生点上筛查10代表DFF，保存峰值同刻端压对应的两个节点、连续超限区间及有限窗口波形，不扫描后续重复轮次。源仿真只读，不启动Spectre。图与报告写sar_isolation_v1/stress_windows/。电流未保存，关于耦合/高阻恢复的归因以连接和电压先后为依据，保留机制推断边界。原生日志、阶段、条件与覆盖范围随报告交付；不commit/push。


## 2026-10-27 本轮窗口回收与交付完成

manual8-sar-a-tt-v6已原生正常完成1.62us，零错误结束，CMI保留；本轮只对已有前220ns做analysis-only，未启动新Spectre测试。manual8-sar-a-v6-stress-windows-v1完成42951原生时刻、10代表DFF/248MOS六端差分析，37.034s、RSS约10.6MiB；回收7739896字节，原始大波形保留远端。TB-B未运行。

已交付stress_windows/report.md、key_events.json与三张PNG，图像逐张检查。确认I5.MM76复位VGB1.061118V/6.13ps、I12.MM64正常复位VDS1.084476V/230.65ps，以及判决/输出普通DFF内部PMOS源节点上冲。时长均对应所列峰值所属单次连续区间；I22另一脉冲最长193.98ps不混用。区分同刻端电压证据与寄生耦合/弱恢复机制推断，未保存电流，未宣称功能/电气/PVT通过。

验证：流式分析实际执行成功、本地绘图执行成功、Python AST与JSON/图片路径检查、scoped diff --check通过。未改电路/OA/库/其他任务；不commit/push。本轮用户要求已完成，后续实验须按新的明确问题继续，不自动启动旧完整功能回归。


## 内部节点拓扑图

用户要求将已定位端压对应到内部拓扑。沿用本计划所有权，在scripts/manual_adc/sar_isolation_topology.py生成stress_windows/内的局部晶体管连接PNG/SVG及节点对照说明；只读native_cell_connectivity.json，标明局部省略和寄生耦合推断，不修改库/电路、不启动仿真。逐管核对D/G/S/B连接并查看生成图，追加日志，不commit/push。

拓扑交付完成：4张局部PNG/SVG与1张总览，16个绘制器件逐一断言核对原生D/G/S/B，检查记录topology_connectivity_check.json；总览已查看并修正标签压线。report.md补充节点和波形对应。未运行仿真、未改库/OA、不commit/push。


## tcb DFF候选清点与CDN最小方案（不仿真）

用户授权只读清点tcb库可替代DFF、比较内部拓扑并形成CDN边沿最小测试方案。所有权增加verification/manual_adc/sar_isolation_v1/dff_inventory/、scripts/manual_adc/sar_isolation_dff_inventory.py及output/manual_adc_dff_inventory/；远端库只读，远端/OA修改none。已有其他任务变更保留，不提交。先枚举当前12T库及已安装tcb库，只读小型SPICE/功能模型元数据；提取型号、端口、图结构特征和相对尺寸差异，不复制完整专有网表入可提交目录。用端口固定、内部节点可重命名的连接图比较，区分输出级、内部尺寸、真正拓扑变化；功能替换条件与模型限制明示。输出候选报告、来源哈希及最小CDN试验定义，不生成或提交运行，不commit/push。验证枚举完整性、候选图映射/逻辑定义和scoped diff。

只读清点完成：11个非LPE SPICE路径去重为9库，主库336个DFF型号。采用固定端口、N/P与DGSB端角色、并联合并后的图分组及精确映射，区分尺寸与拓扑差异。优先候选GDFCNQMCOD1/GDFQMCOD1（同引脚ECO实现）及SDFSYNCNQD1/SDFSYNQD1（SE固定0的缓冲隔离结构），全部为BWP12T30P140后缀；D8 OPTMA作为后备。核对170a TT25C手册功能、端口电容；SDFSYNCNQ仍异步清零，DFKCNQ是同步清零不能直接替换。GDF CP电容约7倍成本保留。

DFQD2只改输出两支路；DFQD4含22个非Q支路尺寸变化；DFCNQD2/4另有从锁存复位串联支路复制，关键主锁存链仍在。OPTB扫描D1与对应普通扫描D1图同构，OPTMA/OPTSAD非扫描D8图同构，不虚增架构候选。结果dff_inventory/README.md、inventory.json、validation.json；CDN方案3条件×2实例，每次约9ns，复位下降沿1/2/4倍、50%时刻固定，原D1与其他激励/5fF诊断负载冻结，不冒充原SAR真实扇出。无仿真配方注册/提交，未改OA/库。脚本执行、内部节点重命名/实例重排的图等价检查、候选差异检查、手册关键页视觉复核及scoped diff完成；不commit/push。

## CDN三边沿最小测试执行（用户本轮授权）

目标：保持原生DFCNQD1与TT0.9V27C、CP/D、5fF负载，运行1/2/4倍CDN下降沿三个9ns案例，对比两DFF（D固定高/原后级D下降）的峰值、连续超限时长、清零与恢复捕获。仅本测试，不换单元、不跑SAR整机/PVT。
所有权新增scripts/manual_adc/sar_cdn_*.py；verification/manual_adc/sar_isolation_v1/cdn_slew_v1/；management/recipes/manual8-cdn-s{0,1,2}-tt-v1.yaml、对应runs登记与output/managed_execution目录；远端仅相应managed run目录。只读原源波形、标准库、PDK、OA及其他模块。当前大量dirty含共享管理工具是已授权依赖，本轮调用不修改；不commit/push。
步骤：核对库条件与波形；生成源回放及冻结输入，原始D1引用不改；managed register/submit/status/analyze/collect；原生点同时刻六端差与阈值插值持续时间；画图并检查，报告失败与边界。最多两managed重任务总并发，单例1线程/1GiB仿真、256MiB分析、512MiB输出、300s仿真/分析、32MiB回收。固定maxstep1ps；保留CMI，不以功能通过替代电气通过。验证网表单变量diff、源/库哈希、实际容差、9ns完整性、初始/预置/复位/恢复状态；原始历史与结果不覆盖。

三源仿真均9ns原生成功；初版Py2分析在最后json写出因列表推导泄漏变量a覆盖argparse对象失败，保留失败身份/导出波形。不重跑仿真。新增所有权manual8-cdn-s{0,1,2}-reduce-v2分析配方及对应登记/output/远端目录；修复args变量名后analysis-only绑定各已完成v1源，重新流式分析、原源只读。该失败为分析代码问题，非电路/仿真失败。

完成：manual8-cdn-s0/s1/s2-tt-v1三例各9ns原生成功；实际maxstep1ps/reltol1e-6/gear2only，三例约13s、峰值RSS313–315MiB。v2 analysis-only完成约9.1MiB，原生点10426/10450/10428，所有56MOS六端差与独立数组测量一致，稳定功能窗口通过，所选MOS四端总流KCL残差<4.6e-16A。三张最终图已查看并改善net176纵轴/功能分行。
结果：CDN16.83/33.65/67.30ps；A.MM76峰1.057358/1.032722/1.000578V，超限6.116/5.700/3.596ps；B.MM64峰1.084223/1.080499/1.072681V，超限230.474/227.200/204.267ps。B内部mq下降仍约5.53ps。Q复位27.25/30.28/34.80ps，功能三例通过但电气全部未过。CDN只对首类明显有效，建议下一步独立换结构候选，不继续只放慢CDN；尚未运行候选。报告与comparison/validation在cdn_slew_v1，原生库SHA不变，CMI/SFE告警、失败分析身份和原数据保留。不改OA/用户文件，不commit/push。

## 两种原生DFF结构候选对照（本轮授权）

保持CDN1×、CP/D回放、0.9V/TT27C、5fF负载、9ns和实际求解设置，两个新案例分别SDFSYNCNQD1（SE/SI接0）与GDFCNQMCOD1；复用已有原D1结果，不重跑baseline。保存候选全部MOS端节点，以实际端口表构造实例，比较目标窗口/整段最大六端差、连续超限、复位/捕获、供能及CP/D端源电荷。非整机/PVT签核，不改库内部、不改OA或采用新基线。
所有权：scripts/manual_adc/sar_dff_candidates_*.py、verification/manual_adc/sar_isolation_v1/dff_candidates_v1/、management/recipes/manual8-dff-{syn,gdf}-tt-v1.yaml与对应runs/output/远端managed目录；追加本计划和log。源D1/原生库/PDK/其他模块/Obsidian只读；现有dirty不重置，不commit/push。单例1线程、仿真1024MiB/分析256MiB、输出512MiB、300s，最多总计2managed重任务。先核对端口与完整器件清单/源哈希，一次最小验证后提交；仅两个9ns新仿真。报告波形视觉检查、原生点独立端压/宽度复核、功能稳定区间检查、scoped diff。


完成：仅新增manual8-dff-syn/gdf-tt-v1两个9ns TT0.9V27C案例，原D1复用CDN1x结果；SDF SI/SE接0，GDF同端口，库SHA核对一致。两例原生零错误，功能稳定窗口通过，但电气未过。原D1/SDF/GDF的A全部端差最大1.057563/1.005447/0.970827V；B.MM64 VDS为1.084223/1.089457/1.096250V，连续超限230.474/283.173/321.195ps。GDF首级通过本小台筛查，但后级更差；SDF缓冲后MM65局部边沿3.601ps更陡，关键主锁存串联链仍在。GDF时钟绝对电荷积分为原版7.62倍，不能在理想CP条件下忽略真实驱动代价。暂不采用替代单元，建议下一步单变量D/CDN相对时序，本轮未执行。
实际Spectre21.1 CX、reltol1e-6/maxstep1ps/gear2only；两仿真14.079/13.442s、RSS322.24/315.12MiB，分析约9.27/9.10MiB；CMI/SFE原告警保留。全部MOS六端差流式测量与独立数组复核一致，时长差<1e-12ps，所选MOS KCL残差<1.4e-16A。三张图已视觉检查；AST/JSON/定向空白检查完成。报告/机器数据/图在dff_candidates_v1，两个新运行全部回收，无在途任务。仅TT理想回放5fF诊断负载，不是实际级联/PVT/整机签核；未改OA/库/其他实验，无commit/push。
