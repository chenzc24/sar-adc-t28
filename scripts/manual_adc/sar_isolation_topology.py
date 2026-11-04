"""Read-only native connectivity -> selected DFF transistor topology diagrams."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/manual_adc/sar_isolation_v1/stress_windows'
DATA=json.loads((ROOT/'verification/manual_adc/stress_diagnosis/native_cell_connectivity.json').read_text())
plt.rcParams['font.family']=FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name()
plt.rcParams['svg.fonttype']='none'
plt.rcParams['axes.unicode_minus']=False
RED='#bd3030'; BLUE='#16639b'; GRAY='#687582'; BLACK='#26323a'
checks=[]

def wire(a,pts,color=BLACK,ls='-',lw=1.5):
 a.plot(*zip(*pts),color=color,ls=ls,lw=lw,zorder=1)

def txt(a,x,y,s,size=11,color=BLACK,ha='left',va='center',**kw):
 a.text(x,y,s,fontsize=size,color=color,ha=ha,va=va,**kw)

def dot(a,x,y,color=BLACK):a.plot(x,y,'o',ms=4,color=color,zorder=4)

def mos(a,cell,name,expected,x,y,gate,red=False):
 m=next(m for m in DATA[cell]['mos'] if m['name']==name)
 assert m['terminals']==expected,(name,m['terminals'],expected)
 checks.append({'cell':cell,'device':name,'DGSB':expected})
 p=m['model'].startswith('pch');c=RED if red else BLACK
 # Vertical channel, gate on left; physical upper terminal is S for PMOS, D for NMOS.
 wire(a,[(x,y+.7),(x,y+.42),(x-.3,y+.42)],c)
 wire(a,[(x-.3,y-.42),(x,y-.42),(x,y-.7)],c)
 wire(a,[(x-.3,y-.45),(x-.3,y+.45)],c,lw=2)
 wire(a,[(x-.53,y-.37),(x-.53,y+.37)],c)
 if p:
  a.add_patch(Circle((x-.68,y),.10,fill=False,ec=c,lw=1.4))
  wire(a,[(x-1.5,y),(x-.78,y)],c)
 else:wire(a,[(x-1.5,y),(x-.53,y)],c)
 txt(a,x-1.57,y,gate,10,BLUE,ha='right')
 txt(a,x+.3,y,name+('  P' if p else '  N'),11,c)
 txt(a,x+.09,y+.47,'S' if p else 'D',8,c)
 txt(a,x+.09,y-.47,'D' if p else 'S',8,c)

def setup(a,title,subtitle):
 a.set_xlim(0,14);a.set_ylim(0,12.5);a.axis('off')
 txt(a,.35,12.05,title,15,va='top',fontweight='bold')
 txt(a,.35,11.4,subtitle,10,GRAY,va='top')

def node(a,x,y,label,red=False,dx=.3):
 dot(a,x,y,RED if red else BLACK);txt(a,x+dx,y+.16,label,11,RED if red else BLUE,va='bottom')

def rail(a,x,y,label):
 wire(a,[(x-.4,y),(x+.4,y)]);txt(a,x,y+.3,label,10,ha='center')

C='DFCNQD1BWP12T30P140';F='DFQD1BWP12T30P140'

def reset(a):
 setup(a,'① 移位 DFF：复位时 qf 上冲','I5 · DFCNQD1｜CDN=低有效复位；只画相关复位/反馈支路')
 # qf pull-down and qf_x reset stack.
 x=4;y=9.3
 wire(a,[(x,9.3),(x,7.2)]);node(a,x,9.3,'qf ↑ 1.0611 V',True)
 mos(a,C,'MM4',['qf','clkb','net0152','VSS'],x,6.5,'clkb')
 wire(a,[(x,5.8),(x,4.7)]);node(a,x,5.3,'net0152')
 mos(a,C,'MM5',['net0152','qf_x','VSS','VSS'],x,4,'qf_x ↑')
 wire(a,[(x,3.3),(x,2.7)]);rail(a,x,2.7,'VSS = 0 V')
 x=10.2
 rail(a,x,10.6,'VDD = 0.9 V');wire(a,[(x,10.6),(x,10.2)])
 mos(a,C,'MM78',['qf_x','CDN','VDD','VDD'],x,9.5,'CDN ↓ → 开')
 wire(a,[(x,8.8),(x,7.2)]);node(a,x,8.15,'qf_x ↑')
 mos(a,C,'MM76',['qf_x','qf','net208','VSS'],x,6.5,'',red=True)
 wire(a,[(4,9.3),(7,9.3),(7,6.5),(8.7,6.5)],RED)
 txt(a,7.15,7.15,'qf 接 MM76 栅',10,RED)
 wire(a,[(x,5.8),(x,4.7)]);node(a,x,5.3,'net208')
 mos(a,C,'MM75',['net208','CDN','VSS','VSS'],x,4,'CDN ↓ → 关')
 wire(a,[(x,3.3),(x,2.7)]);rail(a,x,2.7,'VSS = 0 V')
 txt(a,.4,1.9,'MM76：G=qf，B=VSS → VGB=1.0611 V',12,RED)
 txt(a,.4,1.22,'qf_x 快速上升时，qf 先上冲再被反馈拉低。',11)
 txt(a,.4,.6,'省略：qf 上拉、传输门、并联反馈上拉及 Q 输出级。',9,GRAY)

def shift(a):
 setup(a,'② 后级移位 DFF：MM64 源极下冲','I12 · DFCNQD1｜正常复位 210.068 ns；CP=VALID 保持低')
 x=5
 node(a,x,10.3,'mq_x = 0.88973 V（漏）')
 wire(a,[(x,10.3),(x,9.4)])
 mos(a,C,'MM64',['mq_x','clkbb','net176','VSS'],x,8.7,'clkbb ≈ 0',True)
 wire(a,[(x,8),(x,6.8)]);node(a,x,7.45,'net176 = −0.19475 V（源）',True)
 mos(a,C,'MM65',['net176','mq','net184','VSS'],x,6.1,'mq ↓')
 wire(a,[(x,5.4),(x,4.2)]);node(a,x,4.8,'net184')
 mos(a,C,'MM66',['net184','CDN','VSS','VSS'],x,3.5,'CDN ↓ → 关')
 wire(a,[(x,2.8),(x,2.25)]);rail(a,x,2.25,'VSS = 0 V')
 txt(a,9,10,'D=前级 CLK1 ↓\nmq ↓，mq_x ↑',11,BLUE,va='top')
 txt(a,9,6.15,'内部节点失去\n强接地通路；\n下冲后慢恢复',11,va='center')
 txt(a,.4,1.45,'MM64：VDS = 0.88973 − (−0.19475) = 1.08448 V',12,RED)
 txt(a,.4,.72,'省略：输入支路、mq 反相器、主锁存上拉及后级。',9,GRAY)

def ordinary(a,slave=False):
 if slave:
  title='④ 负侧判决 DFF：从锁存器内部上冲'
  sub='I38 · DFQD1｜CLK3 上升捕获低电平；169.586 ns'
  upper=('MM0',['net086','qf_x','VDD','VDD']);lower=('MM1',['qf','clkbb','net086','VDD'])
  invp=('MM77',['qf_x','qf','VDD','VDD']);invn=('MM76',['qf_x','qf','VSS','VSS'])
  src='net086';dr='qf';fb='qf_x';gate='clkbb ↑';srcv='1.00682';drv='0.00083';peak='1.00599'
 else:
  title='③ 输出 / 正侧判决 DFF：主锁存器内部上冲'
  sub='以 I46_3 · DFQD1 为例｜CP=CLKS 仍低、Q保持；169.591 ns'
  upper=('MM60',['net0118','mq','VDD','VDD']);lower=('MM79',['mq_x','clkb','net0118','VDD'])
  invp=('MM50',['mq','mq_x','VDD','VDD']);invn=('MM49',['mq','mq_x','VSS','VSS'])
  src='net0118';dr='mq_x';fb='mq';gate='clkb ≈ VDD';srcv='1.01402';drv='0.00194';peak='1.01208'
 setup(a,title,sub)
 x=4.2;z=10.2
 rail(a,x,10.5,'VDD');wire(a,[(x,10.5),(x,9.6)])
 mos(a,F,*upper,x,8.9,'')
 wire(a,[(x,8.2),(x,6.3)]);node(a,x,7.45,src+' = '+srcv+' V',True)
 mos(a,F,*lower,x,5.6,gate,True)
 wire(a,[(x,4.9),(x,3.6)]);node(a,x,4.05,dr+' = '+drv+' V')
 # Explicit inverter producing the feedback gate, both actual native MOS.
 rail(a,z,10.5,'VDD');wire(a,[(z,10.5),(z,9.6)])
 mos(a,F,*invp,z,8.9,'')
 mos(a,F,*invn,z,5.6,'')
 wire(a,[(z,8.2),(z,6.3)]);node(a,z,7.1,fb+' ↑')
 wire(a,[(z,4.9),(z,3.6)]);rail(a,z,3.6,'VSS')
 wire(a,[(x,3.6),(7.8,3.6),(7.8,8.9),(z-1.5,8.9)])
 wire(a,[(7.8,5.6),(z-1.5,5.6)]);dot(a,7.8,5.6)
 wire(a,[(z,7.1),(13,7.1),(13,2.7),(.65,2.7),(.65,8.9),(x-1.5,8.9)],BLUE)
 txt(a,7.1,2.45,fb+' 反馈到 '+upper[0]+' 的栅极（上升 → PMOS关断）',10,BLUE,ha='center')
 txt(a,.4,1.5,lower[0]+'：源节点高于 VDD，漏节点接近地 → |VDS|='+peak+' V',12,RED)
 txt(a,.4,.75,'省略其余输入/反馈/传输门及 Q 输出级；右侧为实际两管反相器。',9,GRAY)

panels=[reset,shift,lambda a:ordinary(a),lambda a:ordinary(a,True)]
names=['04_topology_reset','05_topology_shift','06_topology_master','07_topology_slave']
footer='实线为原生网表连接，同名节点相连；D/S 按网表端序。体端省略：N→VSS，P→VDD。红色为超限管/节点；局部图不是完整 DFF。'
for fn,name in zip(panels,names):
 fig,ax=plt.subplots(figsize=(11,10));fn(ax)
 fig.text(.5,.02,footer,ha='center',fontsize=9,color=GRAY)
 fig.subplots_adjust(left=.02,right=.98,top=.98,bottom=.05)
 fig.savefig(OUT/(name+'.png'),dpi=180)
 fig.savefig(OUT/(name+'.svg'));plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(22,20))
for fn,a in zip(panels,axes.flat):fn(a)
fig.text(.5,.014,footer,ha='center',fontsize=13,color=GRAY)
fig.subplots_adjust(left=.015,right=.985,top=.99,bottom=.035,wspace=.02,hspace=.03)
fig.savefig(OUT/'dff_topology_overview.png',dpi=150);plt.close(fig)
(OUT/'topology_connectivity_check.json').write_text(json.dumps({'source':'verification/manual_adc/stress_diagnosis/native_cell_connectivity.json','terminal_order':'D G S B','verified_drawn_devices':checks[:sum([5,3,4,4])],'new_simulations':0},indent=2),encoding='utf-8')
print('Generated 4 PNG/SVG local schematics and overview; native D/G/S/B checks passed.')
