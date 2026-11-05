# RNL 原理图

顶层和六个模块的绘图记录直接写在[当前源网表](../../design/README.md)的 `// @RNL` 注释中；共用符号为 [sar8.rnl](../../design/rnl/sar8.rnl)。49 个本地子电路按电路拓扑排列：比较器对称再生、Bootstrap 预充与升压、两侧 MOM 阵列、参考与 SAR 位片、RC 和主动 clear。总共提供 83 个层次，包含独立测试台及外部接口。

## 查看

在项目根目录执行：

```powershell
.venv/Scripts/python.exe -m tools.saradc draw --serve
```

打开 <http://127.0.0.1:8875/>。左侧选择顶层或模块，双击图中子电路或点击下方实例按钮进入内部；重叠对象先选择元件，再点“进入子电路”。右侧可缩放、适应画布，也可进入完整官方查看器。支持源网表查看、单页 SVG 和自包含 RNL 网表导出。下载的展示网表包含绘图符号，可独立打开，不作为仿真输入。

[离线页](index.html) 内嵌全部 SVG，可直接打开并逐层浏览；官方查看器的平移、缩放和编辑功能需要上述本地服务。浏览器中的编辑不会自动写回项目文件，修改后需导出并核对源文件。相同网络名表示连接；交叉线仅在有连接点时相连。

## 编辑与更新

```powershell
# 源网表或绘图注释更新后，重新生成展示和散列
.venv/Scripts/python.exe -m tools.saradc draw
# 检查当前展示与实际源是否一致
.venv/Scripts/python.exe -m tools.saradc draw --check
```

普通 `draw` 保留源文件中手工编辑的 RNL。只有要重新应用 [布局生成器](../../tools/saradc/rnl_layouts.py) 时使用 `draw --annotate`：它替换 `BEGIN/END SARADC RNL` 标记内的注释，不改变标记外的源字节。共享符号由 [rnl.py](../../tools/saradc/rnl.py) 定义并生成。

[current.scs](../../design/rnl/current.scs) 直接 include 当前分模块源；[export.scs](../../design/rnl/export.scs) 是独立下载副本。[manifest.json](../../design/rnl/manifest.json) 记录实际源、生成器、绘图输出的 SHA256 与 RNL 检查结果。冻结 B、PDK 和 OA 不进入编辑流程。

## 候选与范围

候选从 [specs/candidates.json](../../specs/candidates.json) 读取。已登记的候选可在相应模块页选择；候选展示按其实际网表生成，未编排的新拓扑标注为自动布局。切换展示不会提升候选或修改仿真默认值；登记方法见 [候选约定](../../design/xtor/README.md)。

本地包装电路可逐层展开，外部标准库、PDK 和 VA 只显示真实端口接口。RNL 是文本设计的展示，不表示 OA 同步、版图完成或电气合格。

## 工具与来源

生成需要官方 RNL 0.5.5 CLI，按系统 PATH、本机 `work/tools/rnl-0.5.5/cli/rnl.exe` 查找，也可用 `--rnl PATH` 指定相同版本；CLI 不随项目提交。官方 viewer 0.5.3 / core 0.5.5 按 [逐文件锁](../../tools/saradc/rnl_viewer.lock.json) 缓存于忽略的 `work/tools/`。首次启动下载官方静态资源，后续校验缓存；上游内容不符锁定散列时保留失败，需明确更新版本。服务只绑定回环地址并提供清单内的绘图输入，不托管整个项目。

布局与层次组织参考 [ADC-12b-100M 的源网表 RNL](https://github.com/many-question/ADC-12b-100M/tree/10ef811bf94fbc928992aec2520382304390a960/design)，本项目器件、参数与连接来自自己的当前设计。工具、格式和上游许可见 [RNL 项目](https://github.com/rich-netlist/rnl)。未复制参考项目的电路实现。
