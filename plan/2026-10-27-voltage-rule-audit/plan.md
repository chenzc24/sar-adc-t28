# PDK与标准单元瞬态端压规则核查

目标：查阅已安装DRM、可靠性说明、模型限制与原生数字库文档，分清推荐工作范围、模型告警、端压绝对限制及可能的瞬态/寿命条件，针对当前nch_mac/pch_mac和DFF告警给出有来源的判断。无仿真，无电路修改。

所有权：本计划、verification/manual_adc/voltage_rule_audit/的摘要与来源元数据、output/manual_adc_voltage_rule_audit/的私有文档缓存与提取/页图、追加plan/log.md。远端/OA修改none；PDK、库、原结果、其他模块、用户笔记只读。大量既有dirty归属其他实验，不重置、不编辑；本轮不commit/push，原厂完整资料不加入受控源目录。

步骤：只读定位文档与实际模型版本；下载必要文档至ignored output并核对身份；按电压、脉宽、占空比、温度、寿命和器件种类查找条款；视觉核对相关表/脚注；输出适用与未知范围，保留CMI证据，不擅自豁免超限或改门槛。

验证：精确来源路径/SHA/版本/页码、模型与库对应关系、相关条款完整上下文；摘要不得外推未提供的瞬态容许量；JSON和scoped diff检查。不访问或公开上传私有PDK内容，不下载网上非授权副本。


完成：只读核对DRM T-N28-CL-DR-002 v2.3(2025-08-27)第643–649页、170a TT标准单元手册第12–13页及当前V1.8_3模型。核心nch/pch六端差默认max0.99V，1.8V管对应1.98V；原生CMI阈值一致。DRM给寿命机制/条件但Vmax相关条目仍待qualification且指定N28HP；数字库绝对电压指向TSMC Online e-Reliability按寿命条件评估。未找到可用于当前HPC+ULL尖峰的峰值/脉宽豁免表，未取得正式模型/库配套证明。明确严格端压筛查未过不等于已证明寿命失败，也不能因脉冲短或属于标准单元而批准。ov_ratio未改；MSOA文档实为Mixed Signal Open Access，排除为SOA证据。
资料缓存仅ignored output/manual_adc_voltage_rule_audit，三份新PDF远端SHA匹配，既有标准库PDF SHA与清点匹配；关键表/寿命段已视觉核对。摘要与来源JSON在verification/manual_adc/voltage_rule_audit，JSON/定向空白检查完成。无新仿真、无远端写入/OA/PDK/标准库修改，无commit/push；其他实验dirty保留。后续所缺为对应工艺qualification/产品寿命条件/厂商认可可靠性评估，本轮资料核查已完成，不把缺失数据猜成许可值。
