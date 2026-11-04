# 标准单元完整候选与首批存储验证包

**历史v1：7555路端流过密，FF在约3.11ns触及2GiB输出上限，未完成；SSv1未启动，不再执行这些配方。当前使用[v2：89路端流](../standard_cell_storage_v2/README.md)，FFv2／SSv2q1原生20ns已完成，[快速分析](../standard_cell_storage_fastanalysis_v1/README.md)结果待回收。**

[完整ADC候选](full_adc/dut.scs)已生成并保持冻结。以下保留v1首次准备时的设计、测试与配方记录，不作为当前执行入口，也不代表整机已通过。

| 工况 | 建议 run | recipe 文件 SHA256 |
| --- | --- | --- |
| FF／0.99V／−40°C | `sar8audit-ctrl-stdfull-storage-ff-v1` | `6b79278918ed1435da37007c1a3054b5f10728880241cd8e3d3606327cdb657e` |
| SS／0.81V／−40°C | `sar8audit-ctrl-stdfull-storage-ss-v1` | `91e7d8abce4b80e924fe85e9f3ca6ddb57cc8330acf0da2ac1af54e21b9928c8` |

[FF recipe](ff/recipe.suggested.yaml) · [SS recipe](ss/recipe.suggested.yaml) ·
[输入清单](manifest.json) · [定向测试收据](test_receipt.json)。每组15项输入／4,133,359B。

## 候选范围

[完整ADC候选](full_adc/dut.scs)基于原始核心参考驱动版 `b9bf…133680`，
不含后来IO／单级GPP修复。候选SHA：`0eb51413d69a8a3a7da7708dbbb6b9e8a4a82688cb30944bc7da7fb3d65c27cf`。

- 原174项清单中的普通逻辑、24个DFF、2个SR及90个延迟内部INV均标准化。
- 参考末级和中间级另识别的**96级普通核心N/P反相对全部替换**，没有因下游是模拟就豁免。
- 明确保留30个RC块的R0/R1/C0/C1及60只clear MOS、两个SR显式CQB、全部Rgate、CDAC、Bootstrap与比较器；
  原NAND和DFF内部共210个私有MOM随原实现退出。未接入库单元隐藏节点，未添加拟合负载电容。
- 顶层端口、原复位优先与握手连接不变，未修改外部激励。D1为首个结构候选，尚未证明驱动能力合适。
  门传播改变后的内部有效采样关闭沿仍须原生验证，不强行对齐或悄悄重定时。

逐项变化、保留理由和数量见[migration_manifest.json](migration_manifest.json)。
候选1977只MOS，其中1848只来自原样库SPICE、60只RC清零核心管、69只受保护模拟MOS。

## 已核实的库契约

只读SSH核实了原始170a SPICE、模型入口／模型子文件的哈希和实际三单元连接；
无foundry器件尺寸或模型正文复制，运行时include原文件。
INV、NAND2真值，以及28管DFCNQD1的稳定状态／主从记忆切换已从实际MOS图枚举验证：
**CP上升沿捕获，CDN低异步清Q**。wrapper将原高有效RST反相接CDN。
这不是数值瞬态、setup/hold或recovery/removal表征。清零期间内部主锁存状态与旧自搭实现有差别，
所以专门测试高／低时钟清零、释放及复位／时钟重叠。

[library_probe.json](library_probe.json)保存端口、连接和文件哈希；
[library_truth.json](library_truth.json)保存推导及其限制。
补充的模型section只读查询因匹配规则未识别`pre_simu`而退出，未获得新增section证据；
不能据此推断模型缺失。配方保留既有模型模板，实际elaboration由本次原生运行验证，未追加远端探测。

## 首批测试的准确边界

两个工况各执行20ns，包含**两个SR和全部24个寄存器的独立上下文、76个实际第一级扇出／完整RC输入负载块**。
共1870只MOS，保存980路电压、7555路端流和11220对同时刻MOS端压；所有节点KCL在原生全历史计算。

SR覆盖复位、释放、置位、保持、从Q高复位、重叠输入及两种释放次序。
DFF覆盖0/1捕获、两种时钟电平下的数据保持、异步复位、高／低电平释放和上升沿重叠复位。
命令经真实标准门驱动，其他负载输入有独立条件激励，无Q／QB理想钳位或内部初态强制。
每个角重新生成0/VDD命令，不把FF模拟波形改标签当SS使用。

**这是真实第一级输入负载下的状态烟测。** 扇出单元后级输出在边界截断，
不能称为完整实际Miller负载、真实ADC反馈或参考末级资格。负载寄存器保持复位以使背景状态确定；
各条件连接及未保留部分见[load_boundaries.json](load_boundaries.json)。完整候选仍保留实际Rgate/CDAC。

每段0.4–0.9ns检查所有原生点的10/90%VDD保持带；额外／缺失Q沿、复位重叠毛刺、
实际引脚到Q延迟独立记录。缺失或歧义记未知，不填零通过。物理筛查与CMI独立保留，整机合格字段为空。

资源：**1线程，仿真≤1GiB／1200s，分析≤256MiB／1200s，原始输出≤2GiB**。
分析临时表≤64MiB；回收波形为逐字节验证的无损gzip，保留每个原生时间点。
完整原始电压／端流留远端PSF，全历史端压／电流／KCL／各源能量留result.json。
最终所有派生文件加managed日志／状态及256KiB尾部预留必须≤30MiB，用户回收上限32MiB；超限明确失败，不静默跳文件。

4项定向测试通过，另已核对全部冻结输入哈希、项目／库端序、AST及scoped whitespace。
未登记／提交仿真、修改OA／PDK／共享计划、采纳、commit或push；旧自搭SR对照仍未启动。
