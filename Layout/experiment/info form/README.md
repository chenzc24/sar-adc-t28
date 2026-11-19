# 比较器 V4：原始几何与 LayoutML 信息结构对照

本目录按请求保存两份**完整文本**，没有截取前 N 项，也没有用省略号代替坐标。本次选择 GDS 路径；没有读取当前编辑会话的 OA，不能把这些文本称为完整 OA 数据库导出。

## 先打开这两份

| 文件 | 内容 |
| --- | --- |
| [01_gds_complete.txt](01_gds_complete.txt) | V4 GDS 的全部 2300 个记录，包含层级、坐标、变换、文字及属性；随后附顶层递归展开后的全部 573 个对象。每条 GDS 记录同时保留解码值和原始字节十六进制，末尾 716 字节 padding 也保留，可逐字节重建原 GDS。 |
| [02_layoutml_complete.txt](02_layoutml_complete.txt) | 同一 V4 经 LayoutML 导入器产生的完整 flat LML、Meso-LML、完整 store、所用 CDL，以及经上游编译器导回 GDS 后的全部 389 个展开对象。这是工具的数据表示和编译结果，不是浏览器 DOM 的截取。 |

两份文本中的 `ALL_FLATTENED_SHAPES_JSONL` 段使用完全相同的字段结构，方便逐对象比较。坐标为整数 DBU，**1 DBU = 1 nm = 0.001 µm**。`box` 的 bbox 就是完整矩形；多边形、path 会输出全部顶点/宽度/端部延伸，文字会输出文本/位置/变换等。源 GDS 的层级原貌在第一份的原始记录段保留，展开段则统一到顶层坐标。

供程序使用的原生文本另存为 `layoutml.flat.lml`、`layoutml.meso.lml`、`layoutml.store.json` 和 `reference.cdl`。LML 内的 store 引用保留上游原名，使用这些重命名副本时须显式传入 `--store layoutml.store.json`。完整来源与各文件哈希见 [manifest.json](manifest.json)，逐层差异及全部导入端口见 [geometry_diff.json](geometry_diff.json)。

## 确认是哪个 V4

- 冻结运行：`comp-v4-20261117-pex`。
- Top：`sar_strongarm_t28_core`；来源库 `SAR_ADC_T28_LAYOUT`。
- 本地输入：`work/layout/comparator-redesign/official-v4.gds`。
- 服务器输入：`thu-wei:/server_local_ssd/chenzc_intern25/sar-adc-t28/layout/evidence/comp-v4-20261117-pex/fixture.gds`。
- 两端 GDS SHA256 均为 `af089c02ae82219e312d9006609eb6206c150cb025d2ca3c342974652e933ea7`。
- CDL 来自同一运行，SHA256 为 `e5e3e20693a0b0123573650419d222aaffb3bb11388b388b3e0b2865ebc0aca4`。
- LayoutML 固定提交：`e19fb224207147ddb531d0ea2b1812b5862fd7e4`。

## 信息结构到底有什么不同

| 维度 | 直接查 OA | 直接解析 GDS（本次第一份） | LayoutML（本次第二份） |
| --- | --- | --- | --- |
| 基本对象 | cellView、instance、shape、via、terminal、pin、net、属性等 | structure、BOUNDARY/PATH/TEXT、SREF/AREF、层号/datatype、变换、属性 | `pcell`、`device`、`route`、`viastack`、`cell_port`，另以 realization 索引 store |
| 坐标 | 对象本地坐标＋实例变换；递归后才是顶层坐标 | 精确整数 DBU＋层级变换；没有自动的电路解释 | 文本坐标/相对锚点＋store 内部局部 nm 几何；需要合成才有完整形状 |
| 器件身份 | master、实例名、PCell 参数可由实际数据库查询，取决于对象及读取范围 | 保留导出的子 cell 和引用；不保证保留原始实例名、完整 PCell 参数或可编辑性 | 从几何、标签和 CDL 重建器件/网络，按行归组，不能等同 OA 原生对象身份 |
| 连接信息 | 可读已经存在的 net/terminal 属性；没有赋网的物理形状仍需提取 | 图形交叠、过孔、标签是提取的输入，标签并非完整连通图 | 显式写出网络、器件端子与端口契约，便于语义查询；覆盖度和正确性取决于导入算法 |
| 供 Agent 操作 | 能精确查实际对象，但需选字段、递归和解释设计意图 | 最忠实地回答“实际有哪些几何”，直接阅读很冗长 | 容易表达“移动这一行”“查看某网络”，有压缩与关联价值，但不是新增工艺知识 |
| 设计经验 | 不自动包含匹配、对称、敏感节点优先级 | 不自动包含这些意图 | 同样不会自动知道；需来自设计约束、模板或人工/Agent 判断 |

**它的价值是把几何组织成较容易阅读和编辑的语义对象，而不是获得 OA/GDS 原本没有的真实几何信息。** 这些语义也可以通过 OA 查询加明确约束获得。来自 CDL 的网名、从几何推断的器件、用户给定的匹配意图，应分别记录来源，不能混成一种“数据库真值”。

现有 bridge 的 `layout_read_geometry` 只返回当前层的图形和实例，不递归，且不完整包含 pin/via/mosaic/net。该快捷查询的字段少，属于**查询范围限制**，不能据此说 OA 数据本身缺少这些信息。细节见 [layout-query.md](../../docs/layout-query.md)。

## V4 实测差异

| 项目 | 原始 GDS | LayoutML 导回 GDS |
| --- | ---: | ---: |
| 展开矩形数 | 522 | 382 |
| 展开文字数 | 51 | 7 |
| 总展开对象数 | 573 | 389 |

对象数改变不单独证明几何损失，因为矩形可分割或合并。为此另做了 KLayout **逐层 polygon union XOR**；8 个层的覆盖区域确实不同：

| 层 | 缺少面积 µm² | 新增面积 µm² |
| --- | ---: | ---: |
| OD 6:0 | 1.1160 | 0 |
| PO 17:0 | 0.0468 | 0 |
| PP 25:0 | 1.4898 | 0 |
| NP 26:0 | 1.2080 | 0 |
| CO 30:0 | 0.1632 | 0 |
| M1 31:0 | 0 | 0.0896 |
| M2 32:0 | 0 | 0.1408 |
| M3 33:0 | 0 | 0.0722 |

这里的缺少/新增是相对于源 GDS 的几何集合差，不代表已经定位到哪一行导入器代码，也不是 DRC 违规面积。不同层的面积不能相加解释为版图面积损失百分比。

LayoutML 将器件组织为 3 行、14 个物理指，保留 10 个命名 route。store 只给出 **17 个 SD 表面端口、7 个网络**（OUTN、OUTP、TAIL、VDD、VSS、X、Y）；CLK/VINP/VINN 虽然出现在 device/route 文本中，却没有对应的栅端口契约。故“文本里有这个网”和“完整检查了这个网的所有端子”是两回事。B 端也不能凭 device 中的 B= 字段视为已验证物理接触。

这份 V4 结果独立于前一次 V3，不沿用 V3 的面积差数值。**目前不能用这套转换取代原始几何或据此回写 OA。** 可用它研究语义组织和草稿操作；要作为真实设计编辑层，至少须补齐几何与端子覆盖并通过同源往返验证。该比较不涉及新的 Calibre、PEX 或电气验收。

## 生成与验证

在项目根目录使用 `.venv/Scripts/python.exe`，依次执行：

```text
work/layout/layoutml-v3-preview/LayoutML/explorations/Q-tech-decoupling/gds_to_lml_algo.py --gds work/layout/comparator-redesign/official-v4.gds --cdl work/layout/layoutml-v4-info/comparator-reference.cdl --out-dir work/layout/layoutml-v4-info/bundle --no-mount-viewer
work/layout/layoutml-v3-preview/LayoutML/explorations/Q-tech-decoupling/meso_compiler.py work/layout/layoutml-v4-info/bundle/sar_strongarm_t28_core.meso.lml --store work/layout/layoutml-v4-info/bundle/sar_strongarm_t28_core.store.json -o work/layout/layoutml-v4-info/roundtrip.gds
"Layout/experiment/info form/export_comparison.py"
```

`export_comparison.py` 校验输入哈希、GDS 全记录可重建性、坐标单位与逐层 XOR，并生成两份全文。没有修改原始 GDS、OA、PDK 或其他模块文件，没有 commit/push。本目录包含完整设计几何，按项目私有设计资料管理。
