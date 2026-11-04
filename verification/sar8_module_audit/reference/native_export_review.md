# 原生边界导出器：本地审核交付

仅准备analysis-only提取器，未连接服务器、未重跑仿真。
父任务将以下三个输入冻结到新run的inputs：

- native_boundary_export.py：Python2.7/3标准库包装器。
- native_boundary_stream.cpp：独立C++11逐点解析器，未改历史版本。
- native_boundary_export.json：源身份、精确信号、时间范围及预算。

运行接口为 --run-dir NEW --output-dir NEW/derived --source-run-dir SOURCE。
新旧run必须互不包含，输出必须严格在新run内。源状态需complete/exit0、
logStatus含tran_perf PASS、冻结dut/test散列一致。source仅以读模式打开，
编译、临时清单、数据和报告均写新output。已有输出目录不为空时拒绝覆盖。

源raw已由原生日志第246行明确命名：
/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8fix-loaded-ref-ffcold/raw/tran_perf.tran.tran。
31条边界从0到66ns保存每个原生点：VDD、PHI_U、CAP_REQ/CAP_CLK、
SAMPLE_INT、SEQ_SAMPLE、CMP_CLK、RST0…7、D0…7、CODE0…7。
需覆盖65.246122ns原故障；不会补造66ns端点。25条诊断电压仅保留64–66ns，
其中21条必需，4条请求链观察点可选。缺必需信号/初值报错，可选缺项明确列出。
GNNRG、电阻串接点和未保存支路电流不在可恢复清单。

边界为boundary.f64le.gz：gzip无损压缩的little-endian float64行，
首列原生时间，列名在native.boundary.columns。诊断为独立f64le与列名。
记录压缩/解压数据SHA和初始值；无插值、抽点或相同值删除。
读到超过66ns的下一原生time后停止，不读完整13GB文件重算SHA；
报告区分“提取范围已覆盖”和“看到了源PSF END”。源完整执行证据独立检查。

压缩数据上限25MiB、诊断4MiB；扣除编译产物和128KiB报告预留后还检查
总输出31MiB上限。任何超限失败，不降精度或抽点。解析器固定4MiB输入缓冲、
一份当前点状态；Linux子进程地址空间限192MiB，整体RSS仍由managed256MiB
门禁监控。本轮未测真实源的压缩大小或服务器RSS，不能预报它一定满足。

safe_file使用Python2兼容的basestring，已测试JSON读回Unicode路径。
远端脚本未使用pathlib、f-string、类型注解或Python3专用subprocess参数；
本机只有Python3.13，Python2运行未实测。unittest本身是本地Python3测试。

本地合成验证：共53项（oracle34＋导出器19），52通过、1跳过。
跳过的是Windows账户无权限创建目录symlink的测试；常规路径隔离已通过。
成功端到端验证gzip解压逐字节一致、源文件集合/内容不变；失败对照覆盖
错散列、缺信号、稀疏/GROUP/PROP、缺t=0、NaN、非递增时间、截断及输出超限。
测试耗时5.386s；未读取真实raw，也未生成参考链网表或managed recipe。
