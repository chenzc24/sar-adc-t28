# Reference load branch diagnosis

Status: complete; start7c9a4f9. User requests cause localization and modification
proposal, not implementation. Preserve unrelated Obsidian/10-bit dirty paths.
Owned: this plan, plan/log.md append, scripts/sar8_ref_load/,
verification/sar8_ref_load/, output/sar8_ref_load/, docs/figures/sar8_ref_load/.
Remote OA none; no CIW/OA/PDK/baseline writes. Read-only source: selected2um
FF/0.99V/125C case, prior reference/wait controls, PDK models and proven tooling.
Remote scratch: /tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ref_load_20261024.

Measure unchanged integrated ADC with extra32 reference-switch four-terminal
current probes, rail/dummy-cap currents and all gates/bottom nodes. Short180ns
transients, output120-180ns; FF hot and FF cold at same0.99V and50ohm sources.
Save-only changes and stop/output window do not change DUT or stimuli.
Check130ns steady reference KCL, rank branches and compare actual gate/source
and drain/body potentials. Distinguish settled off-state leakage from incomplete
gate drive/overlap using measured voltages, currents and temperature contrast.

Then bounded isolated DC probes of the exact implicated devices/pairs at observed
biases: actual versus ideal rail-off gates, plus small off-gate sweep if needed.
No production changes. Preserve internal-current definition and model/terminal
identity; use KCL to distinguish channel, gate and body current. Do not claim a
specific microscopic leakage mechanism without enough model evidence.
Native Spectre via t28_io only; model/license preflight. At most2 concurrent
4-thread jobs, <=6 diagnostic cases, <2GiB remote/<300MiB local. No broad PVT,
FFT, layout or reliability qualification. Preserve CMI warnings and raw PSF.

Validate native exit/logStatus/finite complete samples, source/DUT and remote
hashes, rail-current KCL and baseline130ns voltage agreement, exact setup and
solver settings. Plot compact measured branch/gate evidence and inspect it.
Artifacts: reproducible measurement scripts, case contexts/results, figures and
cause/proposal in this plan. Compile/focused execution/scoped diff review,
append log and scoped local commit, no push or baseline promotion.

## 定位结果

五个原生诊断均完成：两组180ns整机电流探针（保存120–180ns）、两组21点
隔离器件对DC扫描、一个DELTA=0的原生工作点。正式DUT/时序/PDK/OA未修改。
FF/0.99V/125C、130ns采样稳态、参考字128：

| 路径 | VREFP负载 | 比例 |
| --- | ---: | ---: |
| PMOS导通→底板→NMOS关断漏电 | 135.281uA | 87.72% |
| PMOS关断漏电→底板→NMOS导通 | 18.938uA | 12.28% |
| 全部参考开关 | 154.219uA | 100% |

最大支路为XDUT.XCDAC.XSN7：MP_HIGH导通，MN_LOW关断。
VREFP=.892289V→MP_HIGH→BN7=.891928V→MN_LOW→VREFN=.007714V。
支路高参考电流67.906uA，NMOS漏电流67.906uA、源返回67.897uA；差值来自
很小的体/栅电流。各MOS四端KCL、底板KCL、参考轨KCL均小于1nA门限。
源电阻压降电流与直接测得vsource电流一致，不是用压降猜测支路。
第二大为XSP6约33.953uA，第三为XSP5约16.976uA。
完整阵列按二进制权重贡献，bit7两侧合计77.412uA。并非仅某一只异常器件；
不同参考字下大电流会换到相应的互补侧，表内路径仅指130ns状态。

MN_LOW为nch_mac，L=30nm、W=150nm、bit7 multi=384，总宽57.6um；
这是3x加权核心参考开关，不是1.8V Bootstrap Mmain。
实际关断栅压.501244mV，端口VGS=-7.21265mV、VDS=.884214V。
120–140ns全阵列关断栅电平偏离0/.99V均不足1mV，无持续命令重叠。

## 不是栅极没拉到位：独立对照

固定实测参考/体偏置，使用相同完整器件参数重建bit7器件对；DELTA=0结果：

| 条件 | XSN7型NMOS关断路径电流 | XSP7型PMOS关断路径电流 |
| --- | ---: | ---: |
| 125C，实际栅压 | 67.90569uA | 9.50624uA |
| 125C，关断栅压理想拉到0/.99V | 67.25945uA | 9.48239uA |
| -40C，保持热角实测偏置不变 | .102849uA | .006518uA |

强制理想关断电平只改善NMOS路径.952%、PMOS路径.251%；不足以消除参考压缩。
两组隔离DC与热角整机同支路电流相符至.002uA以内。
整机自身冷角负载.2994uA（其参考/实际栅压也随温度变化），不是上述固定偏置
.102849uA的单支路值。必须区分两种冷角对照。

原生tmibsimbulk内部工作点给出代表NMOS：VGS=-7.22149mV、Vth=.140268V、
ids=67.8962uA、总id=67.9055uA；ibd=9.143nA、igidl约1.02e-14A、
isub约.0346nA、栅漏隧穿约.116nA。内在电压与外端口略有差别，不混用。
低于阈值的漏源沟道电流占主要部分，支持高温亚阈值漏电，而非GIDL、体二极管
正向导通或栅驱动不足。注意Spectre的isub字段在此定义为impact ionization，
不能将它错误当作“subthreshold current”。这是模型证据，不是硅测量。

## 修改方案（仅建议，尚未实施）

1. 优先重新选参考开关L，而不是改Bootstrap或继续延长quiet等待。
   建议以现有30nm为对照，确认PDK允许尺寸后测试60/90nm候选；先固定W/并联数
   看NMOS漏电与Ron，再给必要的PMOS配套。NMOS占88%，但剩余PMOS约19uA也
   不可忽略。L加长可能显著压低短沟道漏电，实际收益必须用PDK验证。
2. 再调整W/并联数以满足既有bit建立时间。不要预设W随L同比放大：增W会增加
   漏电、栅负载、注入和能耗。比较Ioff、Ron、栅负载、瞬态建立与注入的可行域。
   临时筛选建议总关断参考负载每轨<=10uA，在50ohm上双轨跨度损失约1mV，
   留出参考增益误差余量；这不是新增的冻结整机规格。
3. 若尺寸折中不够，再审查PDK支持的高阈值/低漏电器件，或耐压器件方案；不能
   假定可直接替换。必须重查SS低压下驱动余量、导通速度、模型与尺寸合法性。
4. 实际reference buffer仍需给出负载相关输出阻抗预算。上轮1ohm对照只证明
   更硬参考可恢复码字，不是一个管级buffer实现；不应只靠源端硬顶186uA负载。
   不推荐以新增负栅压硬关断为首选，会增加电源/控制复杂性及VGD应力。
5. 回整机先做FF热角六点码字/参考平台/CMI，再做SS冷角建立与原五点PVT。
   任一候选需保持原时序和采样窗口；CMI另行处理，加长L不等于提高额定耐压。

## 验证与边界

模型/配置/原网表哈希预检通过，五组远端上传网表哈希与本地一致，所有native
exit=0和对应logStatus PASS。探针整机网表可逆还原原测试（除保存/停止时间、
冷角温度），原DUT完整不变。新标量PSF读取器独立正则交叉核对DC数据通过。
实际整机CX reltol1e-4、maxstep1.8ns（短stop自动改变，原600ns为6ns），
热角130ns参考平台与旧案例一致到远小于10uV；不声称全部求解设置完全相同。
隔离DC使用preset_override、reltol1e-6；记录精确设置，不作等精度速度比较。
图branch_and_gate_controls.png已查看；Python编译、KCL、源电流、稳态栅压、
局部源diff和原生日志检查通过。数据位于verification/sar8_ref_load/。
原始波形均保留，本地约292MiB、远端约253MiB；未删除数据。
整机FF热/冷CMI告警仍存在；这不是整机PVT或可靠性通过。仅本地限定提交，不push。
