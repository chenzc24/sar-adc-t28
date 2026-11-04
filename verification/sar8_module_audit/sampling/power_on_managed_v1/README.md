# 上电双例：32 MiB 管理配方与分析包装

两份配方已在本地准备，**未注册、未提交、未运行**，由父线程统一派发。

| 案例 | 本地配方 | run_id |
| --- | --- | --- |
| DC 核心电源对照 | [recipes/dc_core.yaml](recipes/dc_core.yaml) | `sar8audit-sample-start-dc-sscold-v1` |
| 核心电源从零爬升 | [recipes/ramp_core.yaml](recipes/ramp_core.yaml) | `sar8audit-sample-start-ramp-sscold-v1` |

复用已接受的 31.1–41.1 ns 诊断斜坡、共同外部偏置、低时钟前序，以及原 101/141、201/241 ns 正式边沿。SS / 0.81 V / −40°C、TT 无源；MOS 和工作电源 0.81–0.99 V 合约不变。该前序只是外部测试环境假设，不表示电路已有 POR，也没有冻结首帧有效性或启动误差规格。

**本包装将回收上限固定为 32 MiB，替代旧 `power_on/` 草案的 40 MiB 建议。**旧 deck、映射、diff 和 manifest 继续保留原字节；活动预算见 [compression_config.json](compression_config.json) 与两份新配方。

远端接口仍为 `--run-dir DIR --output-dir DIR`。新 [power_on_analyze.py](../power_on_analyze.py) 写为 Python 2/3 兼容包装，调用原字节的 `loaded_remote.py` 和 `stream.cpp`，不调用 Spectre：

1. 按 SHA 核对冻结 DUT、deck、映射和流式测量文件。
2. 在本次新运行的 `startup-reduce-*/native/` 中生成原始分析输出，不把未压缩波形放入自动回收的 `derived/`。
3. 用固定 1 MiB 块流式 gzip `wave.bin`，记录原始/压缩 SHA 与字节数，并独立流式解压核验 CRC、长度和原始 SHA。未压缩波形和 raw PSF 都保留，不删除。
4. 发布 `wave.bin.gz`、原生结果原件 `native_result.json`、全部端压/事件/极值/列/元数据、压缩回执和文件散列清单。`result.json` 最后发布。
5. 全部派生结果必须不超过 **31 MiB**，另预留 **1 MiB** 给管理状态和原生日志；检查已有根目录证据并保留 64 KiB 完成状态余量。压缩或完整交付超限时停止分析，保留原件，不删减记录、不提高上限。父线程回收后仍须确认 receipt 的 `skipped=[]` 且总量 ≤32 MiB。

压缩不会更改原流式解析器的表示：模拟波形仍是原有 **20 ps 选点数据**，不是每个原生模拟值的完整导出。全部原生点继续参与端压、极值、事件和计数；无额外抽点。237 MOS / 1422 条端压记录、581 个独立节点对和全部原生事件文件保留。两份 SHA 能证明选点二进制解压后逐字节相同。

原解析器的能量积分固定为 **0–100、100–200 ns**；虽观察到 260 ns，200 ns 后仍无原生能量统计，不宣称后续帧完整功耗。

资源配方：4 线程，仿真 RSS 上限 **1024 MiB**、分析 RSS 上限 **256 MiB**，观察 260 ns，排队超时 600 s；仍由项目管理入口实施独占和资源门禁。未对新例实测运行峰值或压缩比，也不依据这些配置宣布电路合格。

回收后用新的 [unpack_power_on.py](../unpack_power_on.py) 核对完整管理回执、无跳过项、交付清单及压缩/原始 SHA，再流式解压到新的本地目录，保持回收目录只读。该目录可直接交给冻结的 [review_power_on.py](../review_power_on.py)，分别量化两帧 Cboot、建立误差、关断净变化和端压；没有自动启动合格结论。

本地验证：**10 项**检查通过，包括跨块无损往返、SHA/CRC 损坏拒绝、压缩及完整证据超限拒绝、原件保留、工作目录与回收目录隔离、重复执行拒绝、配方资源和冻结依赖。Python 2 兼容写法经过本地代码审阅；服务器实际执行与内存峰值仍待父线程统一运行确认。源身份和输入包字节见 [manifest.json](manifest.json)。

在 sampling 目录检查确定性再生：

```powershell
& 'E:/bridge-Agent-T28/projects/sar-adc-t28/.venv/Scripts/python.exe' -B prepare_power_on_managed.py --check
```

本地准备没有更改管理器、32 MiB 策略或任何历史分析器，也没有启动远端任务。
