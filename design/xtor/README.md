# 管级实现与候选

当前实现保持在各模块原路径。候选登记与默认选择的真源是 [candidates.json](../../specs/candidates.json)；目前六个功能模块各有一个 `b` 候选。

新增候选可放在 `design/xtor/<module>/<name>.scs` 或该目录的同名子目录，原实现保留。候选文件提供本模块全部需要的定义；公共 master 与端口顺序须符合登记的接口，内部结构可不同。平台 include、PDK 和标准库由测试台统一提供。

```powershell
python -m tools.saradc candidates list
python -m tools.saradc candidates add --module comparator --id trial --file design/xtor/comparator/trial.scs
python -m tools.saradc block sim --module comparator --candidate comparator=trial --run-id NEW_ID
python -m tools.saradc sim tt_short --candidate comparator=trial --run-id ANOTHER_NEW_ID
```

登记保持默认候选不变。每次实验的 `--candidate module=name` 只改变生成包；运行回执保留候选 ID、实际文件及哈希。接口、重复定义、未声明依赖和调用端口数在打包时检查，功能及性能由真实测试判断。

正式换入当前设计是显式的设计变更：同时更新默认选择、规范设计入口和实现清单，验证相关模块及整机接口。候选登记、相同文件名、相同种子均不转移旧结果的资格。历史冻结 B 始终通过 `--view frozen-b` 独立回归。

当前不引入排行榜、自动晋升或 CI；原生仿真复用现有 managed 队列。模块验收见 [独立测试](../../tb/blocks/README.md)，实际证据见 [结果索引](../../results/README.md)。
