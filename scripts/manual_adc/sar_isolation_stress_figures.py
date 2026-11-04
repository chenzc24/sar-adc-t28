"""Plot only collected stress windows; never starts simulation or remote work."""
import json,csv,gzip,array
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
R=Path(__file__).resolve().parents[2]
P=R/'output/managed_execution/runs/manual8-sar-a-v6-stress-windows-v1/collected/derived'
O=R/'verification/manual_adc/sar_isolation_v1/stress_windows';O.mkdir(exist_ok=True)
r=json.loads((P/'result.json').read_text())
with gzip.open(P/'wave.csv.gz','rt') as f:
 reader=csv.reader(f);names=next(reader);cols={k:array.array('d') for k in names}
 for row in reader:
  for k,v in zip(names,row):cols[k].append(float(v))
d={k:np.frombuffer(v,dtype='d') for k,v in cols.items()};t=d['time']
font=Path('C:/Windows/Fonts/msyh.ttc')
if font.exists():plt.rcParams['font.family']=FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'font.size':10,'axes.unicode_minus':False,'axes.grid':True,'grid.alpha':.2,'axes.spines.right':False,'axes.spines.top':False})
def val(k):return np.zeros_like(t) if k=='0' else d[k.lower()]
def stat(dev,pair):return r['terminal_pairs'][r['device_map'][dev]['pairs'][pair]]
def voltage(dev,pair):
 s=stat(dev,pair);return np.abs(val(s['nodes'][0])-val(s['nodes'][1]))
def line(ax,k,label,mask,x):ax.plot(x[mask],val(k)[mask],label=label,lw=1.25)
def stress(ax,dev,pair,mask,x):
 ax.plot(x[mask],voltage(dev,pair)[mask],lw=1.5,label=dev.split('.')[-1]+' |V'+pair+'|')
 ax.axhline(.99,color='#bd3030',ls='--',lw=1,label='0.99 V 限值');ax.set_ylabel('端压 (V)');ax.legend(fontsize=9,loc='best')
 ax.fill_between(x[mask],.99,voltage(dev,pair)[mask],where=voltage(dev,pair)[mask]>.99,color='#bd3030',alpha=.18)
def finish(fig,filename):
 fig.text(.5,.012,'条件：TT · 0.9 V · 27°C｜真实标准单元 SAR＋理想逻辑延时/比较器响应｜静态参考栅负载，DO=5 fF\n已有 TB-A 波形；无真实比较器/采样/CDAC反冲。指标使用原生点，显示窗口最多约0.5–5 ps抽点。',ha='center',fontsize=9)
 fig.tight_layout(rect=[0,.075,1,.93]);fig.savefig(O/filename,dpi=180);plt.close(fig)
fig,ax=plt.subplots(3,2,figsize=(12,8),sharex='col')
for j,base in enumerate([10.025e-9,210.025e-9]):
 x=(t-base)*1e12;m=(x>=-15)&(x<=100)
 for k,l in [('clks','CLKS'),('xdut.clksn','CDN（低有效复位）')]:line(ax[0,j],k,l,m,x)
 for k,l in [('xdut.i5.qf_x','qf_x'),('xdut.i5.qf','qf'),('xdut.i5.mq','mq（D固定高）')]:line(ax[1,j],k,l,m,x)
 stress(ax[2,j],'XDUT.I5.MM76','GB',m,x)
 for a in ax[:,j]:a.axvline(0,color='gray',lw=.8,ls=':')
 for a in ax[:2,j]:a.set_ylabel('节点电压 (V)');a.legend(fontsize=9,loc='best')
 ax[0,j].set_title(('启动复位，10.025 ns' if j==0 else '正常复位，210.025 ns')+'｜移位首级 I5')
 ax[2,j].set_xlabel('相对 CLKS 上升50%时刻 (ps)')
fig.suptitle('① 复位：qf_x 被置高时，qf 短暂高于 VDD；随后恢复',fontsize=14)
finish(fig,'01_reset_qf.png')
fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True);x=(t-210.025e-9)*1e12;m=(x>=-15)&(x<=420)
for k,l in [('xdut.clksn','I12.CDN'),('xdut.clk_1','I12.D = CLK1'),('xdut.valid','I12.CP = VALID')]:line(ax[0],k,l,m,x)
for k,l in [('xdut.i12.mq','mq（MM65栅）'),('xdut.i12.net176','net176（MM64源）'),('xdut.i12.mq_x','mq_x（MM64漏）')]:line(ax[1],k,l,m,x)
stress(ax[2],'XDUT.I12.MM64','DS',m,x);ax[2].plot(x[m],voltage('XDUT.I5.MM64','DS')[m],ls=':',label='I5.MM64（D固定高对照）');ax[2].legend(fontsize=9)
for a in ax[:2]:a.set_ylabel('节点电压 (V)');a.legend(ncol=3,fontsize=9)
ax[2].annotate('1.08448 V，连续约230.65 ps\n0.88973 − (−0.19475)',xy=(43.0587,1.08448),xytext=(145,1.06),arrowprops=dict(arrowstyle='->',color='#444'),fontsize=10)
ax[2].set_xlabel('相对正常复位 CLKS 上升沿210.025 ns (ps)')
fig.suptitle('② 后级移位 I12：复位叠加D下降，内部源极下冲扩大MM64的VDS',fontsize=14)
finish(fig,'02_shift_source_undershoot.png')
fig,ax=plt.subplots(3,3,figsize=(16,8.5),sharex='col');x=(t-169.5e-9)*1e12;m=(x>=-40)&(x<=410)
cases=[('I22','MM79','正侧判决 bit3：主锁存器','dcmpp','xdut.clk_3','xdut.net28','net0118','mq_x','mq'),
 ('I46_3','MM79','输出 bit3：主锁存器','xdut.net28','clks','do_3','net0118','mq_x','mq'),
 ('I38','MM1','负侧判决 bit3：从锁存器','dcmpn','xdut.clk_3','xdut.net10','net086','qf','qf_x')]
for j,(inst,mos,title,di,cp,qo,src,dr,gate) in enumerate(cases):
 for k,l in [(di,'D'),(cp,'CP'),(qo,'Q')]:line(ax[0,j],k,l,m,x)
 for k,l in [(src,src+'（源）'),(dr,dr+'（漏）'),(gate,gate+'（邻管栅）')]:line(ax[1,j],'xdut.'+inst.lower()+'.'+k,l,m,x)
 dev='XDUT.'+inst+'.'+mos;s=stat(dev,'DS');stress(ax[2,j],dev,'DS',m,x)
 duration=next((b-a)*1e12 for a,b in s['intervals_s'] if a<=s['peak_t_s']<=b)
 ax[2,j].set_title('峰值 %.5f V｜本次连续 %.2f ps'%(s['peak_V'],duration),fontsize=10)
 ax[0,j].set_title(inst+' / '+mos+'\n'+title,fontsize=11)
 for a in ax[:2,j]:a.set_ylabel('节点电压 (V)');a.legend(fontsize=8,loc='best')
 ax[2,j].set_xlabel('相对169.500 ns (ps)')
fig.suptitle('③ 普通DFF：内部PMOS源节点短暂高于VDD；输出FF的CP保持低也会发生',fontsize=14)
finish(fig,'03_dff_internal_pumping.png')
selected=[]
for dev,pair,label in [('XDUT.I5.MM76','GB','移位复位 qf'),('XDUT.I12.MM64','DS','后级移位源极下冲'),('XDUT.I22.MM79','DS','判决DFF主锁存'),('XDUT.I46_3.MM79','DS','输出DFF主锁存'),('XDUT.I38.MM1','DS','负侧判决DFF从锁存')]:
 s=stat(dev,pair);interval=next(([a,b] for a,b in s['intervals_s'] if a<=s['peak_t_s']<=b),None)
 selected.append(dict(label=label,device=dev,pair=pair,peak_V=s['peak_V'],peak_ns=s['peak_t_s']*1e9,peak_interval_ps=(interval[1]-interval[0])*1e12 if interval else None,longest_interval_ps=s['longest_over_s']*1e12,simultaneous_nodes_V=s['peak_nodes_V'],terminals_DGSB=r['device_map'][dev]['terminals']))
(O/'key_events.json').write_text(json.dumps(dict(source=r['source_run'],scope=r['scope'],scope_s=r['scope_s'],events=selected,native_settings=r['source_native']['effective_settings']),indent=2),encoding='utf-8')
print(json.dumps(selected,indent=2,ensure_ascii=False))
