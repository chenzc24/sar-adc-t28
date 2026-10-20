"""Native port reconstruction and focused plots for the driver-removal experiment."""
import json
import re
from pathlib import Path
import numpy as np
from analyze import instances
from no_driver_experiment import ROOT,BASE,OUT,load,dump,sha,blocks

FIG=ROOT/'docs/figures/cdac8_no_driver'


def half_cross(ns,v,direction):
    ids=np.flatnonzero((ns[:-1]>=203.10)&(ns[1:]<=203.3)&
        ((v[:-1]<.45)&(v[1:]>=.45) if direction>0 else (v[:-1]>.45)&(v[1:]<=.45)))
    if not len(ids):return None
    j=ids[0];return float(ns[j]+(.45-v[j])*(ns[j+1]-ns[j])/(v[j+1]-v[j]))


def analyze(name):
    case=load(f'cases/{name}.json');r=load(f'runs/{name}_result.json');assert r['ok'],r['errors']
    assert sha(OUT/f'decks/{name}.scs')==case['deck_sha256']==r['deck_sha256']
    raw=load(f'runs/{name}_waveform.json')
    w={k:np.array(v,dtype=float) for k,v in raw.items() if k!='units' and isinstance(v,list)}
    ns=w['time']*1e9
    assert np.all(np.diff(ns)>0) and ns[-1]>=300-1e-6
    assert all(len(v)==len(ns) and np.isfinite(v).all() for v in w.values())
    assert sha(BASE/f"decks/{case['source_case']}.scs")==case['source_deck_sha256']
    for filename,h in case['va_sha256'].items():
        assert sha(OUT/'sources'/filename)==h==sha(ROOT/'models/veriloga'/filename)
    at=lambda k,t:float(np.interp(t,ns,w[k]))
    word=lambda key,t:sum((at(f'{key}<{b}>',t)>.45)*(1<<b) for b in range(8))
    q=[]
    for j in range(8):
        t=245.9+5*j;active=word('nh',t);ideal=case['vdiff_v']+.9-active*1.8/256
        actual=at('topp',t)-at('topn',t)
        q.append(dict(time_ns=t,error_mv=(actual-ideal)*1000,active_code=active))
    log=(Path(r['metadata']['output_dir']).parent/'spectre.out').read_text(errors='replace')
    row=dict(name=name,result_ok=True,direct_gates=case['direct_gates'],pass_multiplier=case['pass_multiplier'],
        source_case=case['source_case'],source_deck_sha256=case['source_deck_sha256'],
        code=word('dout',293),expected_code=int(np.clip(np.floor((case['vdiff_v']+.9)/(1.8/256)),0,255)),
        compare_max_error_mv=max(abs(x['error_mv']) for x in q),comparisons=q,
        restore_words=[word('nh',202.99),word('nh',203.3)],
        printed_cmi=len(re.findall(r'WARNING \(CMI-',log)),
        suppressed_warnings=sum(map(int,re.findall(r'(\d+) warnings suppressed',log))),
        lte_relaxations=log.count('WARNING (SPECTRE-16780)'),
        p_gate_bit7_fall_half_ns=half_cross(ns,w['xcdac.xsn7.eh_b'],-1),
        n_gate_bit5_rise_half_ns=half_cross(ns,w['xcdac.xsn5.el_d'],1),
        deck_sha256=case['deck_sha256'],va_sha256=case['va_sha256'])
    if case['direct_gates']:
        error=max(max(abs(w[f'xcdac.xs{s}{b}.eh_b']-(w['vdd!']-w[f'{s}h<{b}>']))) for s in 'pn' for b in range(8))
        error=max(error,max(max(abs(w[f'xcdac.xs{s}{b}.el_d']-w[f'{s}l<{b}>'])) for s in 'pn' for b in range(8)))
        assert error<1e-10,error
        row['ideal_gate_equation_max_error_v']=float(error)
    if row['p_gate_bit7_fall_half_ns'] is not None and row['n_gate_bit5_rise_half_ns'] is not None:
        row['gate_half_cross_skew_ps']=1000*(row['n_gate_bit5_rise_half_ns']-row['p_gate_bit7_fall_half_ns'])
    text=(OUT/f'decks/{name}.scs').read_text();sub=blocks(text)
    cdac_nodes,master=instances(text)['XCDAC'];array=sub[master]
    ports=array.replace('\\\n',' ').splitlines()[0].split()[2:]
    parent=dict(zip(ports,cdac_nodes,strict=True));zero=np.zeros_like(ns)
    def voltage(n):
        n=n.lower().replace('\\','')
        if n=='0':return zero
        assert n in w,n
        return w[n]
    masks={'all':np.ones_like(ns,dtype=bool),'post_startup':ns>=100,
           'restore':(ns%100>=2.9)&(ns%100<=12),'sar':(ns%100>=43)&(ns%100<=83)}
    worst={k:{'value_v':-1} for k in masks};count=0;pass_envelope=np.zeros_like(ns)
    for leaf,(nodes,master) in instances(array).items():
        if not leaf.startswith('XS'):continue
        lb=sub[master];lp=lb.replace('\\\n',' ').splitlines()[0].split()[2:]
        mapping=dict(zip(lp,nodes,strict=True))
        def resolve(n):
            if n in mapping:
                p=mapping[n];return parent.get(p,'XCDAC.'+p)
            return f'XCDAC.{leaf}.{n}'
        for dev,(nets,model) in instances(lb).items():
            if model not in ['pch_mac','nch_mac']:continue
            count+=1;d,g,s,b=[voltage(resolve(n)) for n in nets]
            for term,v in {'vds':d-s,'vgs':g-s,'vgd':g-d,'vbs':b-s,'vbd':b-d}.items():
                if dev in ['MP_HIGH','MN_LOW']:pass_envelope=np.maximum(pass_envelope,abs(v))
                for label,mask in masks.items():
                    ids=np.flatnonzero(mask);j=ids[np.argmax(abs(v[ids]))]
                    if abs(v[j])>worst[label]['value_v']:
                        worst[label]=dict(value_v=float(abs(v[j])),signed_v=float(v[j]),
                            instance=f'XCDAC.{leaf}.{dev}',terminal=term,time_ns=float(ns[j]))
    assert count==case['native_reference_mos_count']
    row.update(reference_driver_mos_count=count,stress=worst,screen_pass=worst['all']['value_v']<=.990001)
    ids=np.flatnonzero((ns>=203)&(ns<=204));bottom={}
    for s in 'pn':
        for b in range(8):
            v=w[f'xcdac.b{s}{b}'];hi=ids[np.argmax(v[ids])];lo=ids[np.argmin(v[ids])]
            bottom[f'B{s.upper()}{b}']=dict(max_v=float(v[hi]),min_v=float(v[lo]),max_time_ns=float(ns[hi]))
    cm=(w['topp']+w['topn'])/2;j=ids[np.argmax(cm[ids])]
    row.update(bottoms_restore=bottom,bn5_peak_v=bottom['BN5']['max_v'],
        restore_cm_peak_v=float(cm[j]),restore_cm_peak_time_ns=float(ns[j]),
        reset_bottom_error_mv=max(abs(at(f'xcdac.b{s}{b}',235)-at('vrefp' if (b!=7 if s=='p' else b==7) else 'vrefn',235))*1000 for s in 'pn' for b in range(8)))
    dump(f'metrics/{name}.json',row)
    return row,w,pass_envelope


def plot(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':11,'axes.unicode_minus':False,
        'axes.grid':True,'grid.alpha':.18,'legend.frameon':False})
    fig,ax=plt.subplots(4,1,figsize=(11.5,10),sharex=True,layout='constrained')
    for a in ax:
        a.axvline(203.01,color='.5',ls=':',lw=1);a.axvline(203.11,color='.5',ls='--',lw=1)
        a.set_xlim(202.98,203.55)
    for name,label,color in [('native_bad','原六管驱动','#bd4a3e'),('direct_bad','去驱动、栅极直驱','#2378b0')]:
        row,w,env=results[name];ns=w['time']*1e9;sel=(ns>=202.98)&(ns<=203.55);t=ns[sel]
        ax[0].plot(t,.9-w['xcdac.xsn7.eh_b'][sel],color=color,label=label+'：高轨 P 栅激励',lw=1.4)
        ax[0].plot(t,w['xcdac.xsn5.el_d'][sel],color=color,ls='--',label=label+'：低轨 N 栅电压',lw=1.4)
        ax[1].plot(t,w['xcdac.bn5'][sel],color=color,label=f"{label}：{row['bn5_peak_v']:.4f} V",lw=1.4)
        ax[2].plot(t,env[sel],color=color,label=label,lw=1.4)
        ax[3].plot(t,(w['topp'][sel]+w['topn'][sel])/2,color=color,label=label,lw=1.4)
    ax[0].set(ylabel='栅激励 (V)',title='−0.5 LSB，127→128 恢复｜只删除驱动器，二管尺寸与时序不变')
    ax[0].legend(ncol=2,loc='lower right',fontsize=9)
    ax[1].axhline(.9,color='.4',ls=':',lw=1,label='名义高轨 0.9 V');ax[1].legend(loc='upper right',fontsize=10)
    ax[1].set_ylabel('BN5 对地 (V)')
    ax[2].axhline(.99,color='.25',ls='-.',lw=1,label='0.99 V 筛选线');ax[2].legend(loc='upper right',fontsize=10)
    ax[2].set_ylabel('全部二管端口最大值 (V)')
    ax[3].axhline(.45,color='.25',ls='--',lw=1,label='理想共模 0.45 V');ax[3].legend(loc='upper right',fontsize=10)
    ax[3].set(ylabel='顶板共模 (V)',xlabel='时间 (ns)')
    fig.savefig(FIG/'comparison.png',dpi=160,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(12,6.6),sharex='col',sharey='row',layout='constrained')
    for col,(start,end,enable,title) in enumerate([(202.98,203.55,203.11,'下一采样：127→128 恢复'),
                                                  (47.50,48.07,47.61,'第一次 SAR 换轨：仍可能超限')]):
        for name,label,ls in [('direct_bad_half','二管 0.5×','--'),('direct_bad','二管 1×','-'),('direct_bad_double','二管 2×',':')]:
            row,w,env=results[name];ns=w['time']*1e9;sel=(ns>=start)&(ns<=end)
            ax[0,col].plot(ns[sel],w['xcdac.bn5'][sel],ls=ls,label=label,lw=1.5)
            ax[1,col].plot(ns[sel],env[sel],ls=ls,label=label,lw=1.5)
        for a in ax[:,col]:
            a.set_xlim(start,end);a.axvline(enable,color='.5',ls='--',lw=1);a.legend(loc='upper right',fontsize=10)
        ax[0,col].axhline(.9,color='.4',ls=':',lw=1)
        ax[0,col].set_title(title,fontsize=11)
        ax[1,col].axhline(.99,color='.25',ls='-.',lw=1,label='0.99 V 筛选线')
        ax[1,col].legend(loc='upper right',fontsize=10)
        ax[1,col].set_xlabel('时间 (ns)')
    ax[0,0].set_ylabel('BN5 对地 (V)')
    ax[1,0].set_ylabel('全部二管端口最大值 (V)')
    fig.suptitle('去驱动后的二管尺寸对照｜同时改变导通能力和寄生，不是纯 Ron 扫描',fontsize=12)
    fig.savefig(FIG/'size_scan.png',dpi=160,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':
    results={}
    for p in sorted((OUT/'runs').glob('*_result.json')):
        name=p.stem.removesuffix('_result')
        if load(f'runs/{name}_result.json')['ok']:
            results[name]=analyze(name)
            row=results[name][0]
            print(json.dumps({k:v for k,v in row.items() if k not in ['comparisons','bottoms_restore','va_sha256']},ensure_ascii=False),flush=True)
    if 'native_bad' in results:
        retained=json.loads((BASE/'metrics/clean_va_input_-3516.json').read_text())
        assert abs(results['native_bad'][0]['stress']['all']['value_v']-retained['stress']['all']['value_v'])<1e-4
    FIG.mkdir(parents=True,exist_ok=True)
    proof=dict(scope='Independent native Spectre netlist diagnostics; not saved OA or ADC qualification',
        circuit='T28 Bootstrap/MOM/pass MOS; ideal sign comparator and VA clocked SAR control',
        conditions={'vdd_v':.9,'corner':'tt','temperature_c':27,'stop_ns':300,'physical_transient_noise':False},
        cases=[r[0] for r in results.values()])
    if 'direct_bad_double_fine' in results:
        coarse=results['direct_bad_double'][0];fine=results['direct_bad_double_fine'][0]
        port_delta=1e6*(fine['stress']['all']['value_v']-coarse['stress']['all']['value_v'])
        error_delta=1000*(fine['compare_max_error_mv']-coarse['compare_max_error_mv'])
        assert abs(port_delta)<5 and abs(error_delta)<1,(port_delta,error_delta)
        proof['fine_check']={'maxstep_s':[1e-10,1e-11],'port_delta_uv':port_delta,'compare_error_delta_uv':error_delta}
    (FIG/'metrics.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    if all(k in results for k in ['native_bad','direct_bad','direct_bad_half','direct_bad_double']):plot(results)
