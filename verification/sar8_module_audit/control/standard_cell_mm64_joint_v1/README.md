# FF MM64：小型联合节点抽取

[配方](recipe.suggested.yaml) · [角色／窗口](joint_measurement.json) · [冻结清单](freeze.json) · [最小测试](test_receipt.json)

只读绑定已完成的FFv2源，SHA与原fast分析一致；不新增仿真，不重算11220对。
读取12路原生电压：MM64的D/G/S、U19 CK/DATA/RST/RN/Q、内部clkb/mq/net184及VDD；B为显式接地0。

全0–20ns测量MM64六端对联合极值、同刻节点及带原生括区的线性超限持续时间。
CSV只导出0–0.1ns、1–19ns各边沿±0.1ns，以及4.9–6.15ns、15.9–18.15ns的原始点（重叠窗口合并）。
输出为`joint_native.csv`与`result.json`；后者含全历史极值、同刻5.031257327ns峰值、源SHA和持续时间，首末超限采样点不当作持续时间。

1线程，分析≤256MiB／1200s，新目录输出≤64MiB、回收≤32MiB。
最小3点合成检查通过，验证同刻D−S、原始窗口点、严格阈值与跨阈持续时间；未执行远端分析。
