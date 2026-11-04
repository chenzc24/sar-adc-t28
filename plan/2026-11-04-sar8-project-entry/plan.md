# SAR8 B 版设计与仿真入口整理

目标是从项目首页直接找到当前 B 版顶层、子模块、测试台和结果，参考用户提供的 ADC-12b-100M 仓库的职责划分。建立 design/sar8_b 下冻结 B 的分模块阅读与 include 入口，tb/sar8_b 下测试清单，results/sar8_b 下报告入口。每个路径关联真实源和运行身份。

开始时 git status 有 2513 条既有改动，分支 exp/cdac-flat8-device。README.md 与 docs/README.md 干净，design/、tb/、results/ 目标路径均不存在。原有管理文件、用户笔记和实验改动保持各自所有权。本任务拥有 README.md、docs/README.md、design/sar8_b/、tb/sar8_b/、results/sar8_b/、scripts/sar8_entry.py、本计划及追加的 plan/log.md。远端 OA 所有权为 none。

只读输入为 netlist/sar8_l90_mmain2_stdcell_v1/dut.scs（f31b66c8…）、其库 include、既有 managed 配方和小型结果。原始电路、PDK、OA、历史实验和所有在途运行按原身份继续。

实施按四步进行。先从冻结源提取完整 subckt，按采样、CDAC、比较器、数字单元、延时、SAR、参考和顶层分文件。再生成源锁定清单与测试入口映射。随后更新项目首页、文档入口和 B 版简明结果页。最后验证所有 subckt 电气语句逐段一致、顶层依赖完整、所有本地相对链接与配方输入散列有效，并做定向语法和差异检查。拆分视图的静态一致性和原冻结源的 Spectre 验证身份分别记录。

预期交付包括可打开的 adc_top.scs、完整的子模块文件、TB/激励/配方/分析器映射、仿真配置与结果入口，以及可重复执行的本地一致性检查命令。本次无需新原生仿真，也不提交或推送 Git。

用户随后授权提交、推送与合并，发布动作见 plan/2026-11-04-sar8-publish/plan.md。

已完成。B 版 49 个 subckt 已逐段核对，其中顶层可达 46 个、保留辅助定义 3 个，外部标准单元 master 共 3 类。7 类 TB 的所有配方依赖散列通过，完整复现输入已导出至 output/sar8_b/。首页与历史文档索引已连到设计、TB、结果页。5 个导航页的本地链接、脚本语法与新文件空白检查通过，git diff --check 通过。分文件视图尚未作为独立包执行 Spectre，原生仿真证据仍绑定冻结源。
