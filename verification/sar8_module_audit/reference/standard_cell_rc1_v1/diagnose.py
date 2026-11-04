"""Existing native HL RC1 branch diagnosis; no simulation or frozen edits."""
import csv,gzip,hashlib,json,os,sys,textwrap
from pathlib import Path
OWN=Path(__file__).resolve().parent
REF=OWN.parent
sys.path.append(str(REF))
import numpy as np
import yaml
from analyze_real_bbm import digest,HERE,ROOT
BASELINE=REF/'standard_cell_bbm_hlswap_v1'
OUT=OWN/'diagnosis'


def read(path):return json.loads(path.read_bytes())


def load():
    std=True;corner='ffcold';swapped=True
    name='sar8audit-ref-bbm-stdcell-hlswap-ff-v1'
    package=BASELINE/'ffcold';proposal=package/'recipe_proposal.json'
    assert digest(proposal)=='739a937ac526501d15922f09de3babc87a4dc9270e9845a5731bfe50d26874e4'
    for x in read(proposal)['inputs']:assert digest(ROOT/x['source'])==x['sha256']
    registered=yaml.safe_load((ROOT/'management/runs'/(name+'.yaml')).read_text())
    assert registered['managed'] and registered['recipe']['run_id']==name
    for x in registered['recipe']['files']:
        p=ROOT/x['source'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    folder=ROOT/'output/managed_execution/runs'/name/'collected'
    receipt=read(folder/'collection_receipt.json')
    assert not receipt['skipped'] and len(receipt['files'])==11
    assert receipt['status']['registered']['recipe_hash']==registered['recipe_hash']
    assert registered['recipe_hash']=='d0020c7f2887144d28c373ad052a6f24e81d0d4af120993e2c1066b7c8f186f7'
    assert receipt['total_bytes']==26389195
    assert sum(x['bytes'] for x in receipt['files'])==receipt['total_bytes']<=32*1024*1024
    for x in receipt['files']:
        p=folder/x['name'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    cfg=read(package/'measurement.json');r=read(folder/'derived/result.json');state=read(folder/'simulation.state.json')
    assert r['analysis_complete'] and r['acceptance_pass'] is None and r['native_PSF_END']
    assert r['all_selected_currents_present_and_initialized'] and r['selected_current_count']==(652 if std else 656)
    assert r['measurement_sha256']==digest(package/'measurement.json')
    assert state['status']=='complete' and state['exit_code']==0 and state['native']['native_analysis_pass'] and state['native']['zero_error_footer']
    assert len(r['selected_mos_pair_extrema'])==738
    e=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
    assert len(e['columns'])==441
    # Project only diagnostic voltages and actual output/reference/clear currents.
    wanted=set(cfg['diagnostic_voltage_columns'])|{'time','vcode:1','vvdd:1','rrefp:1','rrefn:1'}
    wanted.update(r['cell_measurements']['CODE_source_and_input_load']['incident_load_branches'])
    for q in r['cell_measurements']['internal_driver_load_work'].values():
        wanted.update(q['source_port_branches']+q['load_port_branches'])
    for side in ['n','p']:
        wanted.update('xdut.xcdac.xs'+side+'0.'+m+':1' for m in ['mn_low','mp_high'])
    for leg in ['hd','ld']:
        wanted.update('xdut.xbbm0.xd_'+leg+'.mp_clear:'+str(j) for j in [1,2,3,4])
    wanted.update(b.lower() for b,x in cfg['terminal_current_catalog'].items()
                  if x['node'].lower() in ['xdut.xbbm0.cb','xdut.xbbm0.ld'])
    for leg in ['hd','ld']:
        stem='xdut.xbbm0.xd_'+leg+'.'
        wanted.update([stem+'c1:1',stem+'r1:1',stem+'r1:2',stem+'x005.xlib.mm1:2',stem+'x005.xlib.mm0:2'])
    wanted.update('kcl:xdut.xbbm0.xd_'+leg+'.rc1' for leg in ['hd','ld'])
    assert wanted<=set(e['columns'])
    ids=[j for j,n in enumerate(e['columns']) if n in wanted];columns=[e['columns'][j] for j in ids]
    w=np.empty((r['native_points'],len(ids)),dtype='<f8');stride=8*len(e['columns']);h=hashlib.sha256();count=total=0
    with gzip.open(folder/'derived'/e['file'],'rb') as f:
        while True:
            b=f.read(stride*128)
            if not b:break
            assert len(b)%stride==0;h.update(b);total+=len(b)
            q=np.frombuffer(b,dtype='<f8').reshape(-1,len(e['columns']))
            assert count+len(q)<=len(w)
            w[count:count+len(q)]=q[:,ids];count+=len(q)
    assert count==11298 and count==len(w) and total==e['uncompressed_bytes'] and h.hexdigest()==e['uncompressed_sha256']
    assert w[0,0]==0 and w[-1,0]==52e-9 and np.all(np.diff(w[:,0])>0)
    return dict(run=name,result=r,cfg=cfg,w=w,c={n:j for j,n in enumerate(columns)},
        native_points=count,receipt_bytes=receipt['total_bytes'],managed_recipe_sha256=registered['recipe_hash'],
        result_sha256=digest(folder/'derived/result.json'),
        external_body='\n'.join(l for l in (package/'test.scs').read_text().splitlines()
            if not l.startswith(('save ','simulator lang=','.include '))),
        source_commit=registered['recipe'].get('source_commit'))


def analyze():
    from rc1_event_measure import measure
    d=load();folder=ROOT/'output/managed_execution/runs'/d['run']/'collected/derived'
    events=measure(d['result'],d['cfg'],str(folder))
    assert events['native_points']==11298 and d['result']['selected_current_count']==652
    for q in events['events'].values():
        assert q['leading']['status']=='observed' and q['observed_return_within400ps']
        assert q['leading']['max_KCL_A']<1e-10
    OUT.mkdir(exist_ok=True)
    data=dict(run=d['run'],result_sha256=d['result_sha256'],managed_recipe_sha256=d['managed_recipe_sha256'],
        native_points=d['native_points'],receipt_bytes=d['receipt_bytes'],measurements=events)
    (OUT/'events.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'cache/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,2,figsize=(12.5,9),layout='constrained')
    colors=['#b65339','#176fa6','#258578','#9c5d9e'];t=d['w'][:,0]*1e9;w,c=d['w'],d['c']
    for j,leg in enumerate(['HD','LD']):
        for k,pos in enumerate([True,False]):
            q=events['events'][leg+('_positive' if pos else '_negative')]
            edge=q['nominal_edge_s']*1e9
            a=q['leading']['native_interval_s'][0]*1e9-.002
            b=q['peak_time_s']*1e9+(.035 if pos else .0006)
            ids=(t>=a)&(t<=b);st='xdut.xbbm0.xd_'+leg.lower()+'.'
            y=(w[:,c[st+'rc1']]-(.99 if pos else 0))*1e3
            axes[k*2,j].plot(t[ids],y[ids],color='#176fa6',lw=1.4)
            axes[k*2,j].axhline(0,color='#999',ls=':',lw=.8)
            axes[k*2,j].axvspan(q['leading']['native_interval_s'][0]*1e9,q['leading']['native_interval_s'][1]*1e9,color='#777',alpha=.12)
            axes[k*2,j].set_ylabel('RC1 - '+('VDD' if pos else '0')+' (mV)')
            for (name,bs),color in zip(q['current_groups'].items(),colors):
                v=sum(w[:,c[b]] for b in bs)*1e6
                axes[k*2+1,j].plot(t[ids],v[ids],color=color,lw=1.2,label=name)
            axes[k*2+1,j].set_ylabel('Into component port (uA)');axes[k*2+1,j].legend(fontsize=7,ncol=2,loc='upper right')
            for i in [k*2,k*2+1]:
                axes[i,j].set_xlim(a,b);axes[i,j].grid(alpha=.16);axes[i,j].set_xlabel('Native time (ns)');axes[i,j].ticklabel_format(useOffset=False,axis='x')
        axes[0,j].set_title(leg+' / positive release');axes[2,j].set_title(leg+' / negative reset edge')
    fig.suptitle('Native standard-cell HL: RC1 charge exchange on both delay legs',fontsize=13)
    fig.supxlabel(textwrap.fill('FF0.99V/-40C, frozen H+L native NAND pin swaps, C0x1, real CDAC/Bootstrap/IO/Rgate; ideal CODE/rails/clock, comparator reset. Shading: native rail-crossing to peak. Negative panels zoom into leading kick; full reset retained numerically. Total port currents include displacement.',155),fontsize=8)
    fig.savefig(OUT/'RC1_native_charge_currents.png',dpi=165);plt.close(fig)
    lines=['# 标准单元版RC1支路诊断','',
        '使用已回收HL-swap FF0.99V/−40°C的原生数据，无新仿真。接收器是原生 INVD1 的 MM1/MM0；下表不借用历史自建INV的电流。完整652路端电流已由原生分析确认初始化；RC1实际五端口归并为四组，逐节点核对完整入射集合。','',
        '| 事件 | RC1峰值V／时刻ns | 到峰值MP_CLEAR D电荷fC | C1 / R1 / 原生X005栅电荷fC | 最大KCL残差pA |',
        '| --- | --- | --- | --- | --- |']
    for name,q in events['events'].items():
        charges=q['leading']['charge_C'];take=lambda name:f"{charges[name]*1e15:.6f}"
        lines.append(f"| {name} | {q['RC1_peak_V']:.6f} / {q['peak_time_s']*1e9:.6f} | {take('MP_CLEAR_D')} | {take('C1')} / {take('R1')} / {take('X005_native_gates')} | {q['leading']['max_KCL_A']*1e12:.3f} |")
    lines+=['','电流/电荷正方向均为流入器件端口。正峰时MP_CLEAR D为负，表示它向RC1送电荷，由C1、R1与接收栅吸收；负峰时MP_CLEAR D为正，从RC1抽走电荷，其他支路给出反向平衡。这证明主交换支路是MP_CLEAR的实际总D端口，不把它进一步武断分成纯Cgd、沟道或二极管电流。阴影/积分起点是同一原生轨线最后一次跨过VDD/0到峰值，完整回轨积分另存JSON。','',
        '![四事件支路波形](RC1_native_charge_currents.png)','',
        '| 事件 | 同刻MP_CLEAR D/G/S/B V | 同刻Vds/Vgd V | 接收NMOS Vgs/Vgd V |',
        '| --- | --- | --- | --- |']
    for name,q in events['events'].items():
        x=q['MP_CLEAR_peak_DGSB_V'];r=q['receiver_X005_peak_V']
        lines.append(f"| {name} | "+'/'.join(f"{x[k]:.6f}" for k in ['D','G','S','B'])+f" | {x['Vds']:.6f}/{x['Vgd']:.6f} | {r['NMOS_Vgs']:.6f}/{r['NMOS_Vgd']:.6f} |")
    lines+=['','同刻端压不混用不同时间极值；全窗最坏端压仍以已回收的738项及其持续时间为准。MP_CLEAR源/体为VDD，RC1被拉负会使其绝对Vds/Vbd超过0.99V；RC1正峰直接加到核心接收栅。','',
        '## 选择一个最小变量','',
        '**仅在HD腿MP_CLEAR栅极串入一只与现有R0完全相同的PDK rupolym电阻，LD腿保留作未改对照。** 不改clear尺寸/直流强度，不改普通标准逻辑或原RC0/RC1电容。新增电阻与新增门节点的保存/入射电流会显式纳入测量。','',
        '理由是两种极性都由clear漏端电荷交换主导，且与其栅边沿一致。现有R1实测约9.7907kΩ（R0同几何）；HD门端在所声明的上升窗口交换约1.9677fC，除以0.99V得到约1.9876fF的本次事件等效负担，R×Qg/ΔV约19.46ps。该量只是选首个边沿缓和实验的估计，不是固定本征电容。使用已原生通过的同几何电阻避免臆造PDK尺寸或理想边沿源。','',
        '预期检验：较缓clear栅边沿能否让R1/接收通路在注入期间分流，从而降低正峰和负峰。风险同样明确：MP_CLEAR关断/开启会延后，可能与R1驱动竞争、拖慢assert及复位，或在新门节点产生过轨。必须同时比较两极性、clear/接收全端压、RC复位/延迟、实际门极间隔和参考建立。既有H/L约2.3mV残余和其他核心过轨不据此宣称修复。','',
        '完整事件积分、四端电流/端压、回轨状态及来源哈希见events.json。仅准备一个HD门串阻候选，由父任务核对后managed提交；本轮未运行。','']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('RC1_NATIVE_EVENTS_READY',{name:q['leading']['charge_C'] for name,q in events['events'].items()})


if __name__=='__main__':analyze()


