# 继续查找可靠性资料：找到认证报告编号，尚未找到正文

2026-10-29。沿引用文献及此前未展开的文档压缩包继续只读检索。

## 新的确定线索

`TN28CLDR002_2_3.pdf` **物理第 11 页，Reference Documentation 表**明确列出：

- **T-N28-CL-QR-095**：28HPC+，0.9/1.8 V，Fab15 的工艺认证报告。
- 同表另有 QR-002/003（Mr/My、Fab12）及 QR-074/087（其他技术/HVMOS）；
  不能把这些不同工艺的报告混用。
- 旧 DRM v1.8_R 第 10 页也引用 QR-095，说明它不是仅新版本才出现的名称。

第 11 页已渲染并核对。它给出了可向 PDK 管理员查询的准确编号，
**没有提供报告正文，也未证明 QR-095 覆盖当前 ULL 器件或包含所需脉冲包络。**
DRM 的可靠性章节指向 Qualification Report，标准单元手册另指向在线寿命评估，
这两条线索仍应分别保留。

## 本轮新增检索覆盖

1. 完整流式查看所用标准库 `tcbn28hpcplusbwp12t30p140_170a_doc.tar.gz`：
   98 个文件，其中 96 个为 DB_* 数据手册，另有 IMPORTANT.NOTE 与版本说明；
   未发现独立 qualification/reliability 文件。没有下载或完整解压该 437 MB 包。
2. 打开当前 ULL PDK 的 `TN28CRSP029W1_1_8_2P2A.zip`，继续查看嵌套的
   `iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531_all.tar.gz` 中
   `DOC_iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531.tar.gz`。
   文档子包遍历完整：263 个条目，筛出 122 个文档/文本条目；未发现 QR-095 或
   独立 reliability/qualification 文件名。PDF 文件名均在此前展开目录清单中出现。
   不等于全部 PDF 已逐页 OCR，也不覆盖主 PDK 实现子包的全部内容。
3. 下载并核对 7 份此前未读正文的 PDK/ERC/RF 使用指南及一个 3.94 MB IO 文档包；
   8 个下载文件的 SHA256 均与服务器原文件一致。对 7 份指南和一份代表性 IO
   数据手册提取全文并搜索可靠性/过冲/寿命关键词，再定向读取相关电气条件。
4. 按 QR 编号、reliability、qualification、aging 等关键词补查筛选后的实时文件名。
   此遍历在 25 秒边界停止，已访问 19505 个目录、未命中、无权限错误；
   **不能称为服务器全盘搜索完成**。未搜索其他用户私有目录。

## 排除的相似资料

- `TSMC_VDDR_Utility_Usage_Guide_v0d3_20120229.pdf` 是把电压属性映射到
  dummy/HV CAD 图层的放置工具说明，不是电压—脉宽可靠性表。
- ERC Usage 主要讲连接、电气规则检查；QCI 指南是 QRC/Calibre 提取流程，
  不能因缩写相似将其当作 qualification。
- IO 数据手册 `DB_TPHN28HPCPGV18_TT0P9V1P8V25C.pdf` 物理第 9 页
  Table 2.1（已渲染核对）给前级 0.81–0.99 V、后级 1.62–1.98 V 的推荐范围，
  没有给当前核心 MOS 短脉冲许可。第 10 页的 IO 输入低电平范围也不能拿来
  豁免 DFF 内部负节点或核心管 Vds/Vgs 超限。

## 目前能交付与仍缺什么

可以准确查询 **T-N28-CL-QR-095 及其适用于 HPC+ULL 的补充/替代报告**，并请求
当前 nch_mac/pch_mac、nch_18_mac/pch_18_mac 的电压应力、时间/占空比、温度、
目标寿命及失效准则，或对应 e-Reliability/Overall Reliability Assessment 条件。
文件编号是已找到的引用；报告正文和本项目的瞬态应力许可仍未取得。

现有 0.99/1.98 V 模型告警门槛与所有失败记录保持不变，不推导未提供的允许 ps/ns。
完整路径、文件身份、归档成员及搜索边界见
[followon_search_manifest.json](followon_search_manifest.json)。
本轮无新仿真、模型/电路/OA 修改、自动化变更、commit 或 push。
