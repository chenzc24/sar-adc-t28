# 仿真诊断小工具方案：日志优先，ADC 契约补充

审查日期：2026-11-02（北京时间）。本轮为只读调研和方案，尚未发布诊断工具；未启动仿真、修改已有检查器、作业或 OA。排除杂散、FFT 频谱分析。

## 1. 结论与范围

首版以 Spectre 21.1 原生日志为核心，复用已有 managed 运行身份、资源状态和 PSF 流式读取；补充 SAR ADC 的帧/握手/正确码契约。统一入口、统一事件格式、冻结真实日志测试集，代替每次实验重新写解析器。

不把“工具正常退出”“仿真跑完”“ADC功能通过”“端压合格”压成一个 pass。规则分 confirmed / suspected / unknown / not_applicable；运行状态另列 running / complete / failed / incomplete / unknown。

## 2. 服务器工具审查

通过 thu-wei 当前账户 UID596 只读检查目录和命令，未做许可证占用测试。

| 工具 | 实际证据 | 首版定位 |
| --- | --- | --- |
| Spectre | `/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre -W` 返回 21.1.0.509.isr12 | 首先支持；现有 ADC 使用 Spectre X MX/CX，视为同引擎不同配置 |
| Xcelium | xrun/irun 可解析，xrun -version 为 21.09-s008 | 后续数字/AMS日志适配；尚无本轮真实运行日志验收 |
| Virtuoso/OCEAN/PSF | IC618Hotfix4 对应命令可解析；另有 ICADVM201 目录 | 波形/工程辅助入口；不作为日志检查前置条件，不宣称 GUI/许可可用 |
| Synopsys VCS | V-2023.12-SP2 目录存在；现有通用 setup 却引用不存在的 D-2009.12 | 环境配置异常证据；未确认可执行或可用许可证，不纳入首版承诺 |
| HSPICE/FineSim/XA/ngspice/WaveView | 当前 Cadence 环境未找到；Synopsys setup 检查亦未找到相关命令 | 不等于全服务器未安装；没有真实语料前不宣称支持 |

证据：server_inventory.json、server_commands.json、server_secondary.json。浅层目录发现不是完整软件资产清单。未修改 setup。

## 3. 原生日志与输出抽样

审查四组完成日志及四组失败日志；三组完成案例另外核对服务器 spectre.out hash、logStatus、raw头尾。仅读取每个 raw 的1500字节头和1200字节尾，不遍历GB波形。

| 案例 | 原生证据 | 工具必须做到 |
| --- | --- | --- |
| A TT FFT | 无CMI，但有SFE/VACOMP以及16780/16881；1032条R4MEAS | 无端压日志≠没有其他问题；记录覆盖范围 |
| B TT FFT | CMI-2751..2755各打印5次，随后抑制；method请求gear2only、实际trap | 事件上下文+抑制标识；requested/effective分开 |
| B 含噪声 FFT | 16780 LTE暂时放松、555 swap 1.87MB；日志汇总21700496条warning被抑制 | 数值风险与性能提示分开；抑制总数不能分摊成各类违规次数 |
| B 静态228..255 | 实际maxstep10ps，附带default285.59ns；其他段default不同 | 比较单位归一后的有效值，保留原文；避免已发生的汇总AssertionError |
| manual8-cdac-l60-ss081cold-v1 | 1.14929ns，SPECTRE-16927最小步长收敛次数超限，premature termination，exit1 | 定位仿真阶段、时间和错误类别；不是泛称“步长不好” |
| manual8-sar-a-tt-v1 | VACOMP-1795非法实数，AHDL编译失败，exit2 | 保留多行错误、源文件行号，区别编译与电路数值失败 |
| manual8-sar-a-tt-v3 | managed limit_exceeded/output_size_limit；exit0；SPECTRE-27/7082及FATAL | exit0不得掩盖限额停止和写出失败；根因候选与后续级联错误分开 |
| sar8audit-ctrl-stdcell-qbcap-ff-v1 | SPECTRE-209许可证无法取得，exit2 | license unavailable，不判电路错误 |

原始摘录、行号、hash见 native_log_samples.json / failure_samples.json / remote_raw_samples.json。未找到/未标注的类别不能声称已有真实样例覆盖。

raw观察：PSF ASCII具有 HEADER/TYPE/SWEEP/TRACE/VALUE/END；GROUP别名和稀疏更新需保留状态。含噪声raw约5.27GB，静态末段约14.74MB，必须流式处理。logStatus是按analysis命名的START/PASS；不能拿别的analysis的PASS替代目标analysis。raw头部同时存在tolerance.relative与reltol，必须保留字段来源而非按名字近似合并。输出采样间隔不等于内部求解步长。

## 4. 现有 ADC 工具审查与复用

| 代码 | 可复用 | 当前缺口 |
| --- | --- | --- |
| scripts/management/remote_agent.py | run/recipe身份、PID重用保护、阶段状态、资源和analysis-only来源检查 | 原生日志只提warning code集合；任意0errors/任意PASS不足以识别多分析或拼接日志 |
| scripts/management/native_summary.py；scripts/sar8_campaign/native_stream.py | 有界PSF流式解析、别名/稀疏更新、END/终点检查 | 显式NaN/Inf、重复/截断、不同格式支持矩阵需补齐；不可默默小写归一导致碰撞 |
| scripts/sar8_campaign/static_reduce.py | 码中心、边界单调性、native与observer交叉核对 | 时刻/位宽/阈值硬编码；启动与正常周期需独立结论 |
| scripts/sar8_campaign/screen_reduce.py | CMP→WRITE→UPDATE顺序、稳定窗和关闭沿 | 提取协议定义，避免只检查事件总数 |
| scripts/sar8_campaign/r4_perf_monitor.va | R4MEAS逐帧记录 | 字段契约需版本化；valid不等于与独立理想码比较通过 |
| scripts/sar8_campaign/live_fft_audit.py | 仅完整行、连续帧检查 | 持久游标、轮换/截断、幂等追加和半行缓存 |
| scripts/management/test_execution.py | 资源、身份、hash、路径、稀疏PSF等测试 | 不是日志分类黄金测试集，不能据此宣称告警识别准确 |

已有功能判定通常混合协议和时限，不能把它更名为“错码检测”直接复用。必须分别输出 protocol、native_observer_match、code_oracle、startup、steady。

## 5. 首版规则目录

| 类别 | 检查项 | 依据与边界 |
| --- | --- | --- |
| 启动/环境 | 二进制缺失、版本、环境引用失效、许可证失败/排队 | 日志与进程状态；找不到命令不等于未安装 |
| 读入/编译 | 网表语法、include/model/parameter缺失、VA编译、端口冲突、重复设置 | ERROR/WARNING多行事件；已知code精确映射，未知保留 |
| 数值/收敛 | DC失败、minstep失败、LTE放松、方法变更、容差变更 | 实际日志证据；告警并不自动证明结果错误，不自动放宽容差 |
| 端压/器件 | CMI端子对、正负电压、限值、实例、仿真时间、SOA相关事件 | 报已打印值、最高已打印值；无全波形时不报全程峰值/超限时长 |
| 执行中断 | 非零退出、fatal、信号终止、wall/RSS/output限额、analysis失败 | 多源合并；native错误优先于exit0，原因未知保留unknown |
| 资源/速度 | swap、线程实际禁用、资源排队、磁盘/文件限额 | 性能提示≠功能失败；无输出只报疑似停滞，结合sim_time/PID/CPU核对 |
| 完整性 | 目标analysis终态、预期stop、raw END、缺信号、NaN/Inf、损坏/不支持格式 | 运行中半行/无END是pending；结束后缺数据才判不完整 |
| 设置一致性 | corner/VDD/temp/solver/reltol/maxstep/noise seed等声明和有效值 | SI单位归一、作用域与analysis绑定；默认值说明不参与有效值比较 |
| ADC帧 | 漏帧、重复/乱序、样本数不足、启动帧失败 | 带版本的observer契约；预热不等于可以隐藏启动失败 |
| ADC协议 | 比较次数、逐位写入顺序、提前结束、复位、关闭沿、转换期限 | 位宽/阈值/时序来自契约，不能全局硬编码8次或0.45V |
| ADC码字 | 非法码、码输出不稳定、observer/native不同、与独立oracle不符 | oracle明确输入节点、采样时刻、满量程、量化约定和容许误差；无oracle则unknown |
| ADC静态 | 中心码错误、转换边界乱序、搜索未收敛、覆盖缺口 | 搜索协议与码密度数据区分；局部覆盖不能宣称全码无缺码 |
| 数据可信度 | 警告抑制、截断、只读尾部、recipe/hash不一致、重启混入旧结果 | 显式coverage，不静默忽略，也不允许“无发现”变成“全通过” |

后续可加窗口内建立残差、参考跨度、采样下冲、门限交叉/振铃、功耗异常等波形插件；首版不做通用根因推理。没有保存信号或没有定义门槛就不作对应判定。含噪声相邻码跳动本身不叫错码。

## 6. 产品形态：一个包、少数稳定命令

建议名称 simcheck（暂定），Agent调用固定CLI而不是生成新的正则脚本。

```text
simcheck inspect --run <run-id> --profile spectre-sar8.yaml
simcheck watch   --run <run-id> --cursor <cursor.json>
simcheck compare --left <run-id> --right <run-id> --checks settings,protocol
simcheck report  --input diagnostics.json --format markdown
```

inspect默认只读日志/状态/小元数据；需要全raw重分析时交给现有managed analysis-only，绑定完成源。watch只跟踪增量、遇到进程退出后做终态归并，不自动杀任务/重跑/改网表。发现新类别是新增规则和测试，不是允许Agent输出未经验证的临时判定。

内部只分三层：输入适配（Spectre/logStatus/managed/PSF）、规则、报告。ADC契约是可选插件，保留未来xrun/VCS/HSPICE适配接口，但没有语料就不承诺支持。不增加一套调度器或审批层。

每个事件至少包含 schema_version、rule_id/rule_version、run_id/attempt/analysis、原始severity与产品severity、certainty、sim_time_s、instance/terminal、measured/limit/unit、source_path+line/byte、原文摘要、source_hash、coverage。日志全局抑制数量与某个code已打印数量分别保存。长日志游标绑定文件身份、offset和前缀hash；截断/轮换切新attempt，不复用旧成功结论。

最终JSON分别给 execution / numerical / electrical / protocol / code / data_integrity，另给analysis coverage；Markdown按类别合并显示首例、最严重已观察值和证据位置，避免刷屏。

## 7. 验收与分期

### P0：原生日志与完整性（优先交付）

完成Spectre事件解析、完成/失败合并、数值设置归一、警告抑制、JSON/Markdown。用本次8个真实案例加正常/未完成对照冻结测试。先旁路运行，与现有结果并列，不替换生产判定。

### P1：ADC契约与波形基础

迁移现有帧/握手/native交叉检查为插件；startup/steady独立。引入PSF finite、END、时间轴、信号覆盖检查。正确码golden oracle需要单独手工验证，不由被测输出自己反推真值。以旧版本已知错码案例和人工注错案例验收。

### P2：增量监控及更多工具

watch游标和报告去重、受控analysis-only重分析、真实电气窗口插件。获取Xcelium等真实通过/失败日志后再扩展适配器。暂不扩大频谱/杂散范围。

每阶段必须有：冻结版本/语料、规则覆盖矩阵、变更说明、可重复测试命令、已知限制。测试至少包括：

- exit0+FATAL、前PASS后FAIL、多analysis、缺footer、未到stop、worker消失、半行日志。
- 同一日志整文件与任意分块解析等价；重复读取不增计数；重启/轮换不沿用旧pass。
- 10ps与1e-11s相同；default变化不误报；请求与实际设置不同不能丢失。
- CMI负电压、多实例、多行、suppression；只读尾部和缺信号不得给全程安全结论。
- NaN/Inf、稀疏PSF、别名碰撞、损坏和不支持格式；输出网格不可冒充求解步长。
- 漏帧/错序/错bit、正确计数但错误顺序、启动失败但稳态通过、门限附近噪声跳码。
- license排队不是失败、swap不是错码、零CMI不是电气合格等负例。

验收标准：冻结标注集内各规则expected/actual事件与字段逐项匹配、已知致命失败零漏报、负例不误报；precision/recall只报告该数据集范围。新格式/未知code全部可见且不自动PASS。另设未参与开发的留出日志集，资源测试验证内存不随日志长度线性增长，沿用analysis<=256MiB/回收<=32MiB预算。

## 8. 本轮交付与未完成项

已完成服务器实际入口检查、8组原生日志抽样、3组远端raw/终态检查、现有代码复用与独立误报审查。工具本体、golden测试集标注、生产接入尚未实现。license可用性、其他模拟器运行语料、所有错误类别覆盖未验证。

建议下一步只实现P0，先把本次真实失败、警告抑制、有效设置与完成状态判断固化；再做P1，不从零重写已有ADC测量流程。
