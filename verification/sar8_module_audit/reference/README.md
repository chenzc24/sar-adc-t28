# 参考字独立判据：本地验收准备

交付范围：命令生成的期望状态、数字捕获/映射检查、独立契约规定的模拟建立检查
及合成反例。没有读取整机波形，
没有重写旧指标，也没有生成新的整机合格结论。

## 来源与真值表

只读源 `netlist/experiments/sar8_physical_repair/loaded_seed/dut.scs`，
SHA256 `41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4`。

| 来源行 / 子电路 | 推导出的契约 |
| --- | --- |
| 667 / sar8p_bitseq8 | 位序 7→0，PHI_U 上升后移向下一位 |
| 683 / sar8p_mux2；694 / sar8p_bit | D 保存判决；CODE=D OR TOKEN |
| 3197 / sar8i_refword | PHI_U 高时 TARGET=D，低时 TARGET=CODE；两次 CAP_CLK 捕获 |
| 同上 XSTORE7/X018/X017 | MSB 反相存储；复位后 Q7=1，其余 Q=0，即字128 |
| 795 / nonoverlap；807 / refdrv | 稳态 H=Q、L=~Q，P侧 GN=GP=Q，N侧 GN=GP=~Q |
| 313 / sar8j_r1_cdac | dummy P接VREFP，dummy N接VREFN |

| 期望 Q_i | BP_i | BN_i | GPN/GPP | GNN/GNP |
| --- | --- | --- | --- | --- |
| 0 | VREFP | VREFN | 0/0 | 1/1 |
| 1 | VREFN | VREFP | 1/1 | 0/0 |

当前位b判决后，第一捕获取已决定字D；第二捕获取
`D OR (1<<(b-1))`（b=0时仅D）。这两个捕获即使字值相同，也必须分别出现。
early和late均须验证Q字与命令相符，但early为中间D状态，不自动要求电容
达到最终模拟建立精度。晚相切换可在早相模拟建立完成前发生。
每位 RST_i 置位时优先于捕获：该位恢复预置值；未复位位仍接受捕获。
解除复位只保持状态，不凭空捕获新字。逐位复位期间不要求尚未复位位
立即变成最终预置字。

`decision.value`、bit与reset事件必须来自独立测试命令或预先审核的参考序列。
实测D/CODE/Q和栅压只供核查，不允许用它们反推本工具的期望命令。
从真实波形提取事件时，必须保留额外/缺失CAP边沿，并独立检查PHI_U电平、
位位置及时序；不能先按“应该有16次”修整事件列表。

## 观察输入与独立测试契约 schema v1

顶层恰含 `schema_version: 1`、`config`对象、`windows`数组和`events`数组。
工具严格校验字段；所有时间为ns，所有电压为V，全部数值必须有限。

`config` 必须明确给出五项，没有自动采用项目预算：

| 字段 | 含义 |
| --- | --- |
| vrefp_v / vrefn_v / vdd_v | 独立命令电平，VREFP>VREFN、VDD>0 |
| logic_low_max_v / logic_high_min_v | 观察窗口内低/高逻辑区；中间电压判未知并拒绝 |

每个window恰含 `name,start_ns,end_ns,stage,bit,checks,analog_requirement`。
`checks`为非空、不重复的`logic/analog`列表。logic-only窗口的
`analog_requirement=null`；含analog时必须绑定独立契约中的一个requirement id。
name唯一，stage为
`reset/early/late`；reset时bit=null，其他为0…7。观察窗口起点必须晚于
最近一次改变参考目标的事件，且实际检查时stage和bit必须匹配。
调用方应按模块建立时间声明窗口；本工具不推定建立预算或自动移窗。

测试契约是单独的必需输入，由父审查/测试方案提供，不能从观察数据派生。
`validate_document(document, contract)`要求显式传入；CLI通过`--contract`读取。
contract恰含 `schema_version:1,contract_id,analog_requirements`。后者为非空数组，
每项恰含 `id,stage,bit,start_ns,end_ns,tolerance_v,purpose`。id唯一；stage/bit
规则同window；时间和容差必须有限且明确，null/NaN预算或缺少契约一律拒绝。
模拟window的stage、bit和整个时间区间必须与绑定的契约项一致，防止移动或
缩小观察窗口掩盖失败。所有契约项都必须有模拟检查，不能通过删除window、
改成logic-only或删除观察事件得到通过。

真实契约可将模拟必检项放在晚相后的下一比较之前、最终reset后的下一采样之前；
数值期限和容差需事先批准。工具不自行增加early模拟建立要求。契约本身的删改
属于显式改变验收要求，须重新审查和冻结，不能仅靠本工具认证其合理性。
合成测试契约为初始reset加八次late检查，仅用于证明工具行为。

每个event恰含 `time_ns,kind` 加下表所列字段，时间严格递增。同一时刻
的事件必须由提取器给出可验证顺序；顺序不明时不能用任意排序获得通过。

| kind | 额外字段 | 作用 |
| --- | --- | --- |
| reset_assert / reset_release | bit | 本位参考存储复位；初始Q未知，需逐位明确初始化 |
| begin_conversion | 无 | 要求预置字128已知、复位已释放；建立独立D=0和TOKEN7 |
| decision | bit,value | 对应PHI_W后的已提交判决命令；value=0/1，按7→0 |
| update_rise | bit | 对应本位PHI_U上升，TOKEN推进，进入第一捕获阶段 |
| capture | 无 | 第一次取D；update_fall后的第二次取CODE |
| update_fall | 无 | 必须已有第一捕获，进入第二捕获阶段 |
| observe | window,values | 仅在声明窗口内核对模拟与可选数字观测 |
| end_conversion | 无 | 要求8次判决、16次正确阶段捕获及复位释放 |

logic窗口的`values`必须含`q_word`，以独立命令生成的Q核对实际存储字。
`d_word,code_word`（0…255整数）与`gates`是可选附加核查；后者须含
`gpn,gpp,gnn,gnp`四个bit0在前的八值列表。
analog窗口必须含`bp_v,bn_v`（bit0在前、长度8的列表）和
`dummy_p_v,dummy_n_v`（标量），按绑定契约的`tolerance_v`检查。
logic-only窗口可以省略全部模拟字段；若提供模拟值，仅检查格式和有限性，
不检查轨电压容差。每条输出记录明确给出`logic_checked/analog_checked`。
传入null/NaN、未知逻辑区、未声明窗口或转场窗口均拒绝。

完整文档验收还要求reset窗口及每一位early/late窗口均有观测，
这些阶段必须含logic检查；模拟覆盖单独依据外部契约。
不能通过删掉窗口定义获得部分覆盖的“通过”。单个窗口中只验证提供的样点，
没有证明样点之间连续建立、峰值应力、噪声或模拟动态精度。
`ReferenceOracle.apply()`供局部反例测试；只有`finish()`通过才给出完整文档结果。

合成示例构造器为 `test_oracle.fixture()`。它从预先给出的判决字生成事件与
模拟表计值，不读取oracle内部状态；独立契约构造器为`fixture_contract()`。
测试值0.9V、1mV及0.09/0.81V逻辑线
仅属于合成测试，未批准为新模块指标。

## 已验证的反例与旧检查边界

命令要求BP0=0.9V，但错误实际栅控GN=GP=0.9V、BP0稳定在0V：
旧转换检查从GP推断低参考，误差0mV且栅态不非法；独立命令检查误差900mV。
这是合成测量反例，没有证明实际ADC发生同一映射错误。

历史 `loaded_analyze.py` 的转换目标在第144行从GP生成；
**其第100行 reset readiness 已使用固定目标，因此不受此次循环依赖问题影响。**
其SHA256为 `83eab7ae27dc47c8ec46c67a2934c95e8c5830dd0d5c3118dd3ebc67ec5e0307`。
已有码字检查仍能发现已测输入的最终错码，不能替代逐相参考字核对。

## 运行与结果

从项目根目录运行：

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s verification/sar8_module_audit/reference -p test_oracle.py -v
.venv/Scripts/python.exe -B verification/sar8_module_audit/reference/oracle.py path/to/fixture.json --contract path/to/approved_contract.json
```

CLI只读两个输入并输出JSON；不创建报告或改写证据。每个输入上限1MiB。
正例为6种已知判决字的完整序列；负例覆盖错轨、P/N交换、位引脚交换、
早相误取晚相字、顺序错误、漏/重复捕获、逐位reset优先、MSB/dummy、
未知值、未定义/跨转场窗口和遗漏覆盖。额外正例证明early模拟未建立而Q字正确、
late在指定窗口建立时能够通过；负例分别证明early错字、late未建立、删去模拟
要求的观察窗口和未知预算均被拒绝。测试结果在本目录plan.md记录。
