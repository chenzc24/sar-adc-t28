"""Compare two exact completed native runs; do not change models or resimulate."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import ROOT, OUT, load, sha
from analyze import data, instances
from run import blocks

FIG=ROOT/'docs/figures/cdac8_dualrail'
NAMES=['final_nominal','clean_va_input_-3516']
TITLES=['正常输入 +453.516 mV｜192 → 128',
        '−0.5 LSB = −3.515625 mV｜127 → 128']
BLUE='#2378b0';ORANGE='#d57c20';GREEN='#278467';RED='#c74538'
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':10,
    'axes.unicode_minus':False,'axes.grid':True,'grid.alpha':.18,
    'legend.frameon':False,'axes.titleweight':'normal'})


def at(w,key,ns):return float(np.interp(ns,w['time']*1e9,w[key]))


def word(w,prefix,ns):
    return sum((at(w,f'{prefix}<{b}>',ns)>.45)*(1<<b) for b in range(8))


def read_and_check():
    records=[];waveforms=[];contexts=[];native=[]
    for name,expected in zip(NAMES,[192,127],strict=True):
        result,case,w=data(name);waveforms.append(w);contexts.append(case)
        deck=OUT/f'decks/{name}.scs';text=deck.read_text();native.append(blocks(text))
        assert sha(deck)==case['deck_sha256']==result['deck_sha256']
        old,new=word(w,'nh',202.99),word(w,'nh',203.20)
        assert old==word(w,'dout',193)==expected and new==128
        reset=(w['time']*1e9>=202.94)&(w['time']*1e9<=203.50)
        ids=np.flatnonzero(reset);idx=int(ids[np.argmax(w['xcdac.bn5'][ids])])
        peak_ns=float(w['time'][idx]*1e9)
        abs_idx=int(ids[np.argmax(abs(w['xcdac.bn5'][ids]))])
        row=dict(name=name,case_sha256=sha(OUT/f'cases/{name}.json'),
            deck_sha256=sha(deck),waveform_sha256=sha(OUT/f'runs/{name}_waveform.json'),
            source_sha256=case['source_sha256'],va_sha256=result['va_sha256'],
            before_high_word=old,after_high_word=new,changed_bits=(old^new).bit_count(),
            bn5_peak_v=float(w['xcdac.bn5'][idx]),peak_time_ns=peak_ns,
            bn5_min_v=float(np.min(w['xcdac.bn5'][ids])),
            max_abs_vbd_v=float(abs(w['xcdac.bn5'][abs_idx])),
            max_abs_vbd_time_ns=float(w['time'][abs_idx]*1e9),
            node='XCDAC.BN5',device='XCDAC.XSN5.MN_LOW',
            terminals={'D':'XCDAC.BN5','G':'XCDAC.XSN5.EL_D','S':'VREFN','B':'0'},
            vbd_at_peak_v=-float(w['xcdac.bn5'][idx]),
            vds_at_peak_v=float(w['xcdac.bn5'][idx]-w['vrefn'][idx]),
            phi_at_peak_v=at(w,'phi',peak_ns),busy_at_peak_v=at(w,'busy',peak_ns),
            valid_at_peak_v=at(w,'valid',peak_ns))
        records.append(row)
    assert native[0]==native[1]
    assert contexts[0]['source_sha256']==contexts[1]['source_sha256']
    for key in ['cell','corner','temperature_c','stop_ns','oa_tag']:
        assert contexts[0][key]==contexts[1][key],key
    assert {k:v for k,v in contexts[0]['parameters'].items() if k!='VDIFF'}=={
        k:v for k,v in contexts[1]['parameters'].items() if k!='VDIFF'}
    assert records[0]['va_sha256']==records[1]['va_sha256']
    assert [r['changed_bits'] for r in records]==[1,8]
    leaf=native[0]['cdac8_dr_sw_b5']
    assert instances(leaf)['MN_LOW']==(['BOT','EL_D','VREFN','VSS'],'nch_mac')
    nodes,master=instances(native[0]['cdac8_dr_nominal'])['XSN5']
    assert master=='cdac8_dr_sw_b5'
    formals=leaf.replace('\\\n',' ').splitlines()[0].split()[2:]
    assert dict(zip(formals,nodes,strict=True))['BOT']=='BN5'
    array_formals=native[0]['cdac8_dr_nominal'].replace('\\\n',' ').splitlines()[0].split()[2:]
    root_nodes,_=instances((OUT/'decks/final_nominal.scs').read_text())['XCDAC']
    assert dict(zip(array_formals,root_nodes,strict=True))['VSS']=='0'
    bad=records[1];retained=load('metrics/clean_va_input_-3516.json')['stress']['all']
    assert abs(bad['bn5_peak_v']-retained['value_v'])<1e-12
    assert abs(bad['peak_time_ns']-retained['time_ns'])<1e-9
    assert bad['phi_at_peak_v']>.89 and bad['busy_at_peak_v']<.01 and bad['valid_at_peak_v']<.01
    return waveforms,records


def save(fig,name):
    fig.savefig(FIG/name,dpi=180,bbox_inches='tight')
    plt.close(fig)


def ideal_residual(name):
    q=load(f'metrics/{name}.json')
    values=[p['ideal_v'] for p in q['comparisons']]
    final=q['vin_v']+.9-q['code']*1.8/256
    x=[100,101.05,147.51,152.51,157.51,162.51,167.51,172.51,177.51,182.51,201.05,245]
    return x,np.array([final,q['vin_v'],*values[1:],final,q['vin_v'],q['vin_v']])*1000


def overview(waves,records):
    fig,ax=plt.subplots(4,2,figsize=(12,10.2),sharex=True,sharey='row',layout='constrained',
                       height_ratios=[.8,1.2,1.2,1.15])
    for col,(name,w,row) in enumerate(zip(NAMES,waves,records,strict=True)):
        t=w['time']*1e9;sel=(t>=100)&(t<=245);ts=t[sel]
        for a in ax[:,col]:
            for lo,hi,color in [(101.05,141.05,BLUE),(141.05,182.53,ORANGE),
                                (182.53,201.05,GREEN),(201.05,241.05,BLUE)]:
                a.axvspan(lo,hi,color=color,alpha=.06)
            a.axvline(203.01,color='.4',ls=':',lw=1)
            a.set_xlim(100,245)
        for k,label,color in [('phi','PHI 采样',BLUE),('cmp_clk','比较时钟',ORANGE),('valid','码有效',GREEN)]:
            ax[0,col].plot(ts,w[k][sel],label=label,color=color,lw=1.1)
        ax[0,col].set_title(TITLES[col],pad=28,fontsize=11)
        for x,label in [(121,'采样'),(162,'保持 / SAR'),(191,'有效'),(221,'下一次采样')]:
            ax[0,col].text(x,1.025,label,transform=ax[0,col].get_xaxis_transform(),ha='center',fontsize=9)
        for k,label,color in [('topp','TOPP',BLUE),('topn','TOPN',ORANGE)]:
            ax[1,col].plot(ts,w[k][sel],label=label,color=color,lw=1.1)
        ax[1,col].plot(ts,(w['topp'][sel]+w['topn'][sel])/2,label='共模',color=GREEN,lw=1)
        ax[1,col].axhline(.45,color='.4',ls='--',lw=1,label='理想共模 0.45 V')
        ax[2,col].plot(ts,(w['topp'][sel]-w['topn'][sel])*1000,label='实际 TOPP−TOPN',color=BLUE,lw=1.1)
        x,y=ideal_residual(name)
        ax[2,col].step(x,y,where='post',label='理想瞬时采样 / 换轨',color='.3',ls='--',lw=1)
        ax[3,col].plot(ts,w['xcdac.bn5'][sel],label='BN5（N 侧 32Cu 底板）',color=RED,lw=1.1)
        ax[3,col].axhline(.9,color='.5',ls='--',lw=1,label='名义高轨 0.9 V')
        ax[3,col].axhline(0,color='.5',ls=':',lw=1)
        ax[3,col].axhline(.99,color='.25',ls='-.',lw=1,label='正向端口筛选 0.99 V')
        ax[3,col].set_xlabel('时间 (ns)')
        ax[0,col].legend(ncol=3,loc='lower right',fontsize=8.8)
        ax[1,col].legend(ncol=2,loc='upper right',fontsize=9)
        ax[2,col].legend(loc='lower right',fontsize=9)
        ax[3,col].legend(loc='center right',fontsize=9)
    for a,label in zip(ax[:,0],['控制 (V)','顶板电压 (V)','差分残差 (mV)','BN5 对地电压 (V)'],strict=True):a.set_ylabel(label)
    peak=records[1]
    ax[3,1].annotate('BN5：1.399620 V\n203.128786 ns',
        xy=(peak['peak_time_ns'],peak['bn5_peak_v']),xytext=(213,1.14),fontsize=9.5,
        arrowprops={'arrowstyle':'->','color':RED},color=RED)
    fig.suptitle('8-bit 双轨 CDAC｜TT，0.9 V，27°C｜延伸到下一周期恢复参考',fontsize=13)
    save(fig,'restore_compare_overview.png')


def zoom(waves,records):
    fig,ax=plt.subplots(3,2,figsize=(12,8),sharex=True,sharey='row',layout='constrained')
    for col,(w,row) in enumerate(zip(waves,records,strict=True)):
        t=w['time']*1e9;sel=(t>=202.94)&(t<=203.5);ts=t[sel]
        for a in ax[:,col]:
            a.axvspan(203.01,203.11,color='.5',alpha=.10)
            a.axvline(203.01,color='.4',ls=':',lw=1)
            a.axvline(203.11,color='.4',ls='--',lw=1)
            a.set_xlim(202.94,203.5)
        for k,label,color,ls in [('phi','PHI（采样相）','.3',':'),
                                ('nl<5>','N bit5 低轨使能',ORANGE,'--'),
                                ('xcdac.xsn5.el_d','MN_LOW 实际栅极',GREEN,'-')]:
            ax[0,col].plot(ts,w[k][sel],label=label,color=color,ls=ls,lw=1.3)
        ax[0,col].set_title(TITLES[col],fontsize=11)
        ax[0,col].legend(loc='lower right',fontsize=9)
        ax[1,col].plot(ts,w['xcdac.bn5'][sel],label='BN5（MN_LOW 漏极）',color=RED,lw=1.4)
        ax[1,col].plot(ts,w['vrefp'][sel],label='实际 VREFP',color='.4',ls='--',lw=1)
        ax[1,col].plot(ts,w['vrefn'][sel],label='实际 VREFN',color='.4',ls=':',lw=1)
        if col==0:ax[1,col].legend(loc='upper right',fontsize=9)
        ax[2,col].plot(ts,abs(w['xcdac.bn5'][sel]),label='MN_LOW |Vbd|',color=RED,lw=1.4)
        ax[2,col].plot(ts,abs(w['xcdac.bn5'][sel]-w['vrefn'][sel]),label='MN_LOW |Vds|',color=BLUE,ls='--',lw=1.1)
        ax[2,col].axhline(.99,color='.25',ls='-.',lw=1,label='0.99 V 筛选线')
        if col==0:ax[2,col].legend(loc='upper right',fontsize=9)
        ax[2,col].set_xlabel('时间 (ns)')
    for a,label in zip(ax[:,0],['控制 / 栅极 (V)','底板 / 参考轨 (V)','MOS 端口绝对值 (V)'],strict=True):a.set_ylabel(label)
    p=records[1]
    for r in [1,2]:
        ax[r,1].scatter([p['peak_time_ns']],[p['bn5_peak_v']],s=25,color=RED,zorder=6)
    ax[1,1].annotate('BN5 = 1.399620 V\n203.128786 ns',
        xy=(p['peak_time_ns'],p['bn5_peak_v']),xytext=(203.22,1.15),color=RED,fontsize=10,
        arrowprops={'arrowstyle':'->','color':RED})
    ax[2,1].annotate('|Vbd| = 1.399620 V',xy=(p['peak_time_ns'],p['bn5_peak_v']),
        xytext=(203.22,1.20),color=RED,fontsize=10,arrowprops={'arrowstyle':'->','color':RED})
    fig.suptitle('放大：下一次采样内恢复参考（不是 SAR 比较阶段）',fontsize=13)
    fig.supxlabel('203.01 ns：恢复命令｜203.11 ns：新轨逻辑使能｜灰带：变化 bank 的 100 ps 逻辑间隔',fontsize=10)
    save(fig,'restore_compare_zoom.png')


if __name__=='__main__':
    waves,records=read_and_check()
    FIG.mkdir(parents=True,exist_ok=True)
    overview(waves,records);zoom(waves,records)
    proof=dict(scope='Replot of existing completed native T28 runs; ideal comparator and VA fixed-period control',
        phase='next sampling, after previous conversion; not SAR comparison',
        sampling_window_ns=[201.05,241.05],restore_command_ns=203.01,new_rail_logic_enable_ns=203.11,
        baseline_same_node_caveat='BN5/MN_LOW is the identical node/device in both columns, not the baseline global worst MOS',
        runs=records)
    (FIG/'restore_compare_metrics.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False,indent=2))
