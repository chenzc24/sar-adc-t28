"""Plot unchanged native Spectre samples; no smoothing or synthetic waveforms."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from inventory import ROOT, OUT, VERIFY, NAMES, read, dump, sha

FIG=ROOT/'docs/figures/sar8_ff_overvoltage'
FIG.mkdir(parents=True,exist_ok=True)
E=read(VERIFY/'events.json')
I=read(VERIFY/'inventory.json')
plt.rcParams.update({'font.size':11,'axes.titlesize':12,'axes.labelsize':11,
    'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,
    'savefig.dpi':180,'axes.prop_cycle':plt.cycler(color=['#c54639','#007f86','#405cb0','#b57b1d'])})
artifacts={}

def data(name,group):
    p=OUT/(name+'_'+group+'.npz')
    assert sha(p)==I[name]['windows'][group]['cache_sha256']
    return dict(np.load(p)),E[name]['events'][group]

def grid(title,rows=2):
    fig,axes=plt.subplots(rows,2,figsize=(13,2.5*rows+1.15),layout='constrained',squeeze=False)
    fig.suptitle(title+'\nL90 candidate | Mmain 2 um | FF, VDD = 0.99 V | native Spectre X CX',fontsize=14)
    for a in axes.flat:
        a.grid(alpha=.18);a.set_ylabel('Voltage (V)')
        a.ticklabel_format(axis='x',style='plain',useOffset=False)
    return fig,axes

def line(ax,w,node,t0,label,**kw):
    ax.plot((w['time']*1e9-t0)*1e3,w[node],label=label,lw=1.7,**kw)

def limit(ax):
    ax.axhline(.99,color='#555555',ls='--',lw=1,label='VDD / model limit 0.99 V')

def finish(fig,axes,name):
    for a in axes.flat:a.legend(fontsize=9,loc='best',framealpha=.94)
    path=FIG/(name+'.png');fig.savefig(path);plt.close(fig)
    artifacts[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))

def near_edge(name,signal,p):
    es=[e['time_ns'] for e in E[name]['timing_events'] if e['signal']==signal and e['direction']=='rise']
    return min(es,key=lambda t:abs(t-p))

def reference():
    fig,axes=grid('Reference gate: bit 7 reset disturbs a still-held bit 4 gate',3)
    for col,name in enumerate(NAMES):
        w,e=data(name,'reference');p=e['peak']['time_ns'];t0=near_edge(name,'xdut.xref.rst7',p)
        temp=I[name]['context']['temperature_c'];rst4=near_edge(name,'xdut.xref.rst4',p)
        a=axes[0,col];a.set_title(f'{temp:+g} C | RST7 rising edge = {t0:.3f} ns')
        for node,label in [('xdut.xref.rst7','RST7'),('xdut.xref.rst4','RST4 (not yet reset)'),('xdut.xref.q7','Q7')]:line(a,w,node,t0,label)
        a.set_ylim(-.07,1.15)
        a=axes[1,col]
        for node,label in [('xdut.xcdac.bn7','BN7: reset bit'),('xdut.topn','TOPN: shared top plate'),('xdut.xcdac.bn4','BN4: disturbed bit')]:line(a,w,node,t0,label)
        a.set_ylim(-.1,1.05)
        a=axes[2,col]
        line(a,w,'xdut.gnn4',t0,'GNN4 = MN_LOW Vgb');line(a,w,'xdut.xref.xdrv4.gnndrv',t0,'GNNDRV4: before gate resistor')
        limit(a);a.set_ylim(.982,1.074)
        a.annotate(f"{e['peak']['peak_v']:.4f} V",xy=((p-t0)*1e3,e['peak']['peak_v']),xytext=(410,1.059),arrowprops={'arrowstyle':'->','color':'#555'})
        a.set_xlabel(f'Time from RST7 rise (ps); RST4 rises at +{(rst4-t0)*1e3:.0f} ps')
        for row in range(3):axes[row,col].set_xlim(-150,800)
    finish(fig,axes,'01_reference_cross_bit')

def driver():
    fig,axes=grid('Reference driver: input-edge feedthrough before the output falls')
    for col,name in enumerate(NAMES):
        w,e=data(name,'reference_driver');p=e['peak']['time_ns'];tag='gnn' if col==0 else 'gpn'
        phase='conversion / bit update' if col==0 else 'idle / RST0'
        axes[0,col].set_title(f"{I[name]['context']['temperature_c']:+g} C | {phase}\n{e['peak']['instance'].split('.')[-1]} | peak at {p:.6f} ns")
        line(axes[0,col],w,'xdut.xref.xdrv0.'+tag+'b',p,tag.upper()+'B: inverter input')
        axes[0,col].set_ylim(-.05,1.08)
        a=axes[1,col]
        line(a,w,'xdut.xref.xdrv0.'+tag+'drv',p,tag.upper()+'DRV = Vds',marker='.',ms=2.6)
        limit(a);a.set_ylim(.91,1.075)
        a.set_title(f"Peak {e['peak']['peak_v']:.4f} V | >0.991 V for {e['duration_above_limit_plus1mV']['duration_ps']:.2f} ps",fontsize=11)
        a.set_xlabel('Time from local voltage peak (ps)')
        for row in range(2):axes[row,col].set_xlim(-12,12)
    finish(fig,axes,'02_driver_feedthrough')

def active():
    fig,axes=grid('ACTIVE: a high-held control net is disturbed during bit 4 -> bit 3 handoff')
    for col,name in enumerate(NAMES):
        w,e=data(name,'sequencer');p=e['peak']['time_ns']
        axes[0,col].set_title(f"{I[name]['context']['temperature_c']:+g} C | peak at {p:.6f} ns")
        for node,label in [('xdut.phi_u','PHI_U'),('xdut.cmp_clk','CMP_CLK'),('xdut.xref.cap_clk','CAP_CLK')]:line(axes[0,col],w,node,p,label)
        axes[0,col].set_ylim(-.05,1.1)
        a=axes[1,col];line(a,w,'xdut.active',p,'ACTIVE = XIDLE.XN.MN Vgs');limit(a)
        a.set_ylim(.98,1.079);a.set_title(f"Peak {e['peak']['peak_v']:.4f} V | >0.991 V for {e['duration_above_limit_plus1mV']['duration_ps']:.2f} ps",fontsize=11)
        a.set_xlabel('Time from local voltage peak (ps)')
        for row in range(2):axes[row,col].set_xlim(-100,120)
    finish(fig,axes,'03_active_handoff')

def comparator():
    fig,axes=grid('Comparator: precharged internal nodes rise above VDD at evaluation start',3)
    for col,name in enumerate(NAMES):
        w,e=data(name,'comparator');p=e['peak']['time_ns'];t0=near_edge(name,'xdut.cmp_clk',p)
        axes[0,col].set_title(f"{I[name]['context']['temperature_c']:+g} C | CMP_CLK rising edge = {t0:.6f} ns")
        line(axes[0,col],w,'xdut.cmp_clk',t0,'CMP_CLK: release reset / enable tail')
        axes[0,col].set_ylim(-.05,1.1)
        a=axes[1,col]
        for node,label in [('xdut.xcomp.x','X'),('xdut.xcomp.y','Y'),('xdut.xcomp.tail','TAIL')]:line(a,w,node,t0,label)
        a.set_ylim(-.05,1.12);limit(a)
        a=axes[2,col];victim='x' if col==0 else 'y'
        line(a,w,'xdut.xcomp.'+victim,t0,victim.upper()+' = -Vbs of '+e['peak']['instance'].split('.')[-1]);limit(a)
        a.set_ylim(.975,1.063)
        a.set_title(f"Peak {e['peak']['peak_v']:.4f} V | >0.991 V for {e['duration_above_limit_plus1mV']['duration_ps']:.1f} ps",fontsize=11)
        a.set_xlabel('Time from CMP_CLK rising edge (ps)')
        for row in range(3):axes[row,col].set_xlim(-80,180)
    finish(fig,axes,'04_comparator_evaluate')

if __name__=='__main__':
    reference();driver();active();comparator();dump(VERIFY/'figures.json',artifacts)
    print('Saved and hashed',len(artifacts),'native-waveform figures')
