# 原 bit0 BBM 标准单元对照：冻结交付

本地准备完成，原生 Spectre 尚未执行。主聊天负责 managed 排队、运行和回收；这里不注册或提交。

| 工况 | run_id | recipe_proposal.json SHA256 |
| --- | --- | --- |
| FF / 0.99 V / −40°C | sar8audit-ref-bbm-stdcell-ffcold-v1 | f8748125aa8e3528ba6fc2767f6e6d6f20aeb0d467144d085b5a1cda415dba6c |
| SS / 0.81 V / −40°C | sar8audit-ref-bbm-stdcell-sscold-v1 | f36c9d35de24675e06ee1a5a077974aeaa104d4e55c049569a2db2bdfa6cb9d4 |

配方位于各工况同名子目录；每份 8 个冻结输入，共 443,855 B。交付后不修改这些输入。

从原 `generated/real_bbm_v1` 的完整 bit0、C0 multi=1 基线出发，普通 INV、AND 内的 NAND+INV、RC 阈值/复位 INV，以及 GNP/GPN 的六对核心反相驱动，统一使用原生 INVD1/ND2D1。共 42 只标准单元内部 MOS；NAND A1 对应原来靠输出端的 NMOS 输入 A，A2 对应输入 B。

保留 RC 的 R0/R1/C0/C1、四只 clear 管、GNN ABC 和单级 GPP 的原 IO 器件、Rgate，以及完整 CDAC/Bootstrap/复位比较器负载。152 条原叶级记录完全相同。原自建 NAND 内的两只 CMID 随门实现一起移除，未接入标准单元隐藏节点。详细映射见 migration.json。

器件几何和库网表不复制；test.scs 只读 include 原 `.spi`，随后恢复 Spectre 语法。library_metadata.json 仅含端口/连接/哈希元数据。原 PDK 模型、激励、采样窗口、关闭沿、CODE 边沿和求解设置不变。首轮 native elaboration 必须核对库文件身份、模型 include、MM 实例的 1..4 端电流绑定；本地测试不能证明这些原生条件。

两角均保存 116 路电压、652 路端电流、738 项实际 MOS 端压检查；36 个 KCL 节点，372 列原生诊断流。统计全部 0–52 ns，保留半轨顺序、相反方向总 D 电流、CODE 输入电荷、各外部源/内部端口功和体端极性。稳定高相位止于下一个 CODE 边沿开始前 47.995 ns，低相位至 52 ns；旧半轨窗口只作切换诊断。两条延迟链分别检查 RC0/RC1/输出复位；缺边沿和未建立明确报告。1 mV/1% 是诊断阈值，不是规格放宽。

资源：4 线程、仿真 RSS 1 GiB，分析 RSS 256 MiB、地址空间内部限 240 MiB，流式分析；派生文件硬上限 30 MiB，预计收集不超过 32 MiB。原始波形留服务器。

验证：Python AST、冻结 SHA/字节数和空白检查通过；一项 focused unittest 通过，覆盖精确保留/映射、外部时序相同、合成 native 数据全流程、端压统计、物理建立窗/切换窗分离、低相位未建立、两条复位、缺控制边沿、电流/功闭合和错误门限拒绝。合成测试不代表电路性能。

这是单 bit0、有理想 CODE/电源、比较器复位的对照，尚未采用，也不是标准单元完整 ADC 版本。D1 为首轮候选，建立、复位、过压与负载能力均待原生仿真；由主聊天随后统一组合各模块。
