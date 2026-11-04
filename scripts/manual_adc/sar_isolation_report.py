import json,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'verification/manual_adc/sar_isolation_v1'
runs=sys.argv[1:];text=['# 手搭SAR隔离实验：TT首轮结果','',
'TT、0.9 V、27°C；100 ns周期，外部采样关闭50%保持49.975 ns+n×100 ns。数字标准单元/尺寸/扇出保留，OA未改。',
'', '原生模拟波形delay在TB-A v2的67.1684 ns因最小步长退出。后续使用**VA阈值判定＋传输延时＋50 ps有限边沿**；2 ns/100 ps为50%至50%目标，属于明确的逻辑延时模型变更，不是RC，也不宣称与原模拟delay传递所有模拟细节等价。',
'', '真实参考MOS静态栅负载，DO每路5 fF；不含底板Miller反冲。TB-A为预定判决响应，TB-B为VA采样/CDAC/比较器闭环；VA比较器td200 ps、trf50 ps。16帧为0/255/85/170/128/127/1/254重复两轮。',
'','| 测量 | 案例 |','|---|---|']
bundle={}
for run in runs:
 p=R/'output/managed_execution/runs'/run/'collected';q=p/'derived/result.json'
 if not q.exists():q=p/'result.json'
 r=json.loads(q.read_text());bundle[run]=r
 delays=[f['completion_delay_s']*1e9 for f in r['frames'] if f['completion_delay_s'] is not None]
 good=sum(f['output']==f['expected'] for f in r['frames'])
 text+=['| %s | %s |'%(k,v) for k,v in [
  ('运行',run),('输出正确帧数',str(good)+'/16'),('每帧8次比较',str(r['functional_checks']['eight_comparisons'])),
  ('热码顺序7→0',str(r['functional_checks']['shift_order'])),('复位1 ns检查',str(r['functional_checks']['reset_within_1ns'])),
  ('转换完成50%时刻',('%.3f–%.3f ns'% (min(delays),max(delays))) if delays else '未完成'),
  ('40 ns建立检查',str(r['functional_checks']['raw_within_40ns'])),('输出1 ns检查',str(r['functional_checks']['output_within_1ns'])),
  ('VDD平均功率','%.3f µW'%(r['power_W']*1e6)),('代表DFF端压筛查',str(r['electrical_screen_ok'])),
  ('实际求解设置',str(r['native_state']['effective_settings']))]]
 text+=['','## '+run+' 端压','',
 '| 类别 | 实例 / 端差 | 峰值 | 时刻 | 最长连续超限 |','|---|---|---:|---:|---:|']
 groups={'移位':['I5','I12'],'正侧判决':['I14','I22','I28'],'负侧判决':['I30','I38','I44'],'输出':['I46_3','I46_7']}
 for label,insts in groups.items():
  choices=[]
  for dev,pairs in r['device_pairs'].items():
   if dev.split('.')[1] not in insts:continue
   for pair,key in pairs.items():choices.append((r['terminal_pairs'][key]['peak_V'],dev,pair,r['terminal_pairs'][key]))
  _,dev,pair,s=max(choices,key=lambda x:x[0])
  text+=['| %s | %s / V%s | %.6f V | %.6f ns | %.3f ps |'%(label,dev,pair,s['peak_V'],s['peak_t_s']*1e9,s['longest_interval_s']*1e12)]
 text+=['','峰值由同一时刻的两端电压相减；六端差筛查阈值0.99 V，非将不同时间极值拼接。持续时间用原生点间线性插值。全部32个DFF端口已保存；内部仅10个代表DFF、248只MOS，其他门内部没有完整逐管覆盖。',
 '', '![逐位时序](figures/'+run+'_timing.png)', '', '![16帧码字](figures/'+run+'_codes.png)', '', '![代表端压](figures/'+run+'_stress.png)', '',
 '原生告警：`'+', '.join(r['native_state']['warning_codes'])+'`。独立功能与电气结论见结果JSON，不由退出码0推断电气通过。','']
text+=['## 结果边界','',
'- 这是TT隔离诊断；未覆盖PVT、失配、瞬态噪声、PEX、完整ADC精度或真实比较器反冲。',
'- 库setup/hold、recovery/removal、最小脉宽约束尚未导入，实测50%间隔不能当库时序签核。',
'- 功耗为声明负载下VDD源积分，包含静态栅负载支路，未计理想delay/比较器/外部时钟提供的能量，不能当整机功耗。',
'- v1响应器语法失败；v2模拟delay收敛失败；v3触发旧2GiB输出预算；v4实际容差未变，核对进程身份后停止。旧日志/原波形保留。v5实际reltol=1e-6；用户随后将后续案例预算提高8GiB/1h。',
'- 无新基线、OA改动、标准库修改、commit或push。','']
(D/'results.json').write_text(json.dumps(bundle,indent=2)+'\n');(D/'results.md').write_text('\n'.join(text),encoding='utf-8')
print(D/'results.md')
