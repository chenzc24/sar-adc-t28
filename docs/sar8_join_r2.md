# SAR8 参考换轨对齐版 R2

已将参考整字对齐时序落到 Virtuoso，采用为后续开发版本 R2。冻结 R1 原样保留。
**这仍是理想栅控时序，尚未实现管级同步驱动；采样中点恢复过压仍未解决。**

## Virtuoso 入口

库为 `SAR_ADC_T28`，技术库 `tsmcN28`：

| Cell | View | 用途 |
| --- | --- | --- |
| `sar_adc8_join_r2` | schematic、symbol | 当前开发顶层，112个实例，已打开 |
| `tb_sar_adc8_join_r2` | schematic | 对应测试台，26个实例 |
| `sar8j_refcommit` | symbol、veriloga | 观察32路原生参考请求，整字稳定200ps后通知 |
| `sar8j_aligned_refgate` | symbol、veriloga | 16份，改变选择的bank共同关断，100ps后共同开启新轨 |

栅边沿20ps；不改变选择的bank保持原连接；采样上升后2ns恢复中点的约定不变。
没有从输入电压计算码字。Bootstrap、StrongARM、原生异步控制器、MOM电容和
3×参考pass MOS均复用R1，不改拓扑或尺寸。参考仍为每轨50Ω串阻、4pF去耦，
没有把实际CDAC参考节点直接钳到理想电压源。

两个VA cell分别保存一个module，函数体与[先前对齐实验](sar8_reference_alignment.md)
逐字一致。新建对象之外的34个已有原理图前后指纹一致。顶层和测试台的实例、
参数、端口连接读回通过，检查标记为空；两个远端VA源码逐字节读回通过。

## 保存原理图来源的复验

从已保存的 `tb_sar_adc8_join_r2/schematic` 导出网表，保留原导出不动。
全部原生子电路体与R1一致；新顶层的电气语句与先前对齐实验一致。
仿真只设置参数、激励、include位置、分析和保存项，未修改导出的DUT。

两次Spectre21.1 APS均 `result.ok=true`。TT、0.9V、27°C、200ns、最大步长10ps，
保存全部求解点。每组两帧、每帧8次实际比较/写入/更新，码字、物理参考映射、
位序及比较器已判决检查通过；门限检查无参考使能重叠、BBM100ps，变化bank
的关断和开启时刻在保存精度内一致。

| 输入 | 两帧输出码字 | 最大比较前误差 | 转换阶段参考管最大端电压 | 转换阶段比较器最大端电压 |
| --- | --- | ---: | ---: | ---: |
| −800mV | 14、14 | 0.807895mV | 0.951088V | 0.950686V |
| −半LSB | 127、127 | 0.560789mV | 0.951079V | 0.951473V |

误差均小于0.25LSB＝1.7578125mV。上述指标与先前网表级对齐实验数值完全一致，
不是将原理图和另一份改写DUT网表混用。

负大输入在103.173270ns的采样中点恢复仍使TOPN／比较器VGB达到1.136126V，
TOPP最低−0.148911V。该组仍打印10条比较器CMI及后续重复抑制记录；负半LSB
没有CMI。两组各有7条既有配置警告，均无LTE。R2是采用了对齐时序的工作版本，
不是通过全部器件应力、PVT、噪声、失配或动态性能验收的ADC。

## 本地文件和结果

- 配置：[sar8_join_r2.yaml](../config/sar8_join_r2.yaml)。
- 模型：`models/veriloga/sar8_join_r2/`。
- OA构建／检查：[join_r2.py](../scripts/integration/join_r2.py)。
- 仿真：[join_r2_sim.py](../scripts/integration/join_r2_sim.py)；
  后处理：[join_r2_analyze.py](../scripts/integration/join_r2_analyze.py)。
- 指纹及逐帧结果：[join_r2_results.json](../verification/integration/join_r2_results.json)。
- 原始读回、导出、运行日志、PSF和波形：忽略目录 `output/sar8_join_r2/`。

离线复核已有结果：

```powershell
.venv/Scripts/python.exe scripts/integration/join_r2_analyze.py nfull nhalf --curate
E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe -m unittest verification.integration.test_join_r2 -v
```

构建和网表准备命令保留所有权及不可覆盖保护；已有case不得覆盖。R1报告和
先前对齐实验报告保持原历史状态，当前版本以本入口和配置为准。
