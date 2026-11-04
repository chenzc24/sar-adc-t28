import re,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build as b
base=(b.OUT/'candidate_v1/dut.scs').read_text()
# Native PDK geometric parameters from a previously exported legal 1um/150nm IO device.
lines=(b.ROOT/'verification/sar8_module_audit/sampling/compact_v2/fixture_dut.scs').read_text().splitlines()
templates={typ:next(l.split(') ',1)[1] for l in lines if (') '+typ+' ') in l) for typ in ['nch_18_mac','pch_18_mac']}
boot=base.split('subckt manual_boot',1)[1].split('ends manual_boot',1)[0]
for line in boot.splitlines():
 m=re.match(r'(M\w+) \(([^)]+)\) (nch_mac|pch_mac) .*',line)
 if not m:continue
 typ=m[3].replace('_mac','_18_mac');tail=templates[typ]
 tail=re.sub(r' multi=1\b',' multi=main_mult' if m[1]=='M0' else ' multi=1',tail)
 base=base.replace(line,m[1]+' ('+m[2]+') '+tail,1)
io=b.OUT/'candidate_io_v1';io.mkdir(exist_ok=True)
b.write(io/'dut.scs',base)
b.write(io/'provenance.json',json.dumps(dict(change='Only manual_boot transistor type/geometry to native IO1.8V unit1um L150nm; M0 multiplicity parameter; all12 original connections and Cboot1pF preserved',evidence='manual8-sample-base-v2 native CMI coreVgb/Vbd/Vgd/Vds violations',geometry_source='verification/sar8_module_audit/sampling/compact_v2/fixture_dut.scs',no_OA_write=True),indent=2))
def replace_dut(name,text):
 b.write(b.OUT/name/'dut.scs',text)
 # recipe paths bound at register; no digest supplied until then.
x=b.pulse('VCLK','CLKS',10,39.9);s=['CLKS']
for j,v in enumerate([.05,.45,.85]):
 x+='VIN%d (IN%d 0) vsource dc=%g\nX%d (CLKS 0 VDD IN%d OUT%d) manual_boot main_mult=4\nCLOAD%d (OUT%d 0) capacitor c=1.28p\n'%(j,j,v,j,j,j,j,j)
 s+=['IN%d'%j,'OUT%d'%j]+['X%d.%s'%(j,n) for n in ['net1','net2','net3','net4','net7','CLKSB']]
b.make_case('sample_io_v1',x,215,s);replace_dut('sample_io_v1',base)
x=b.pulse('VCLK','CLKS',10,39.9);s=['CLKS','VIN']
x+='VIN (VIN 0) vsource type=sine sinedc=.45 ampl=.401 freq=4.502Meg\n'
for j,mm in enumerate([1,2,4]):
 x+='X%d (CLKS 0 VDD VIN OUT%d) manual_boot main_mult=%d\nCLOAD%d (OUT%d 0) capacitor c=1.28p\n'%(j,j,mm,j,j)
 s+=['OUT%d'%j]+['X%d.%s'%(j,n) for n in ['net1','net2','net3','net4','net7','CLKSB']]
b.make_case('sample_sine_io_v1',x,615,s);replace_dut('sample_sine_io_v1',base)
# Isolate CDAC reference switches: only the TB's sampling clamp is ideal.
cdac=base.replace('I1 (CLKS GND VDD VIN VTOP) manual_boot main_mult=main_mult','SCLAMP (VIN VTOP CLKS GND) relay rclosed=.01 ropen=1e15 vt1=.4 vt2=.5')
x=b.pulse('VCLK','CLKS',10,39.9,1000)+'VP (INP 0) vsource dc=.5\nVN (INN 0) vsource dc=.4\nVREF (REF 0) vsource dc=.9\n'
pctrl={k:1 if k==7 else 0 for k in range(1,8)};nctrl=dict(pctrl);events={side+str(k):[(0,.9*d[k])] for side,d in [('P',pctrl),('N',nctrl)] for k in range(1,8)}
r=.1
for bit in range(7,0,-1):
 decision=r>=0
 side=('N' if decision else 'P') if bit==7 else ('P' if decision else 'N')
 value=0 if bit==7 else .9;t=55+(7-bit)*5
 events[side+str(bit)]+=[(t,events[side+str(bit)][-1][1]),(t+.05,value)]
 r-= (1 if decision else -1)*.9*2**(bit-1)/128
for node,points in events.items():x+='V'+node+' ('+node+' 0) vsource type=pwl wave=['+' '.join('%gn %g'%p for p in points)+']\n'
s=['CLKS','REF','VREF:1','INP','INN','TOPP','TOPN']
for side in ['P','N']:
 x+='X'+side+' (CLKS 0 VDD IN'+side+' TOP'+side+' REF 0 '+' '.join(side+str(k) for k in range(7,0,-1))+') manual_cdac\n'
 s += [side+str(k) for k in range(1,8)]+['X'+side+'.net'+str(k) for k in range(1,8)]
b.make_case('cdac_steps_v1',x,110,s);replace_dut('cdac_steps_v1',cdac)
print('IO bootstrap DC/sine sweep and isolated CDAC step cases ready')
