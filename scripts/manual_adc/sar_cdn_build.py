"""Build three bounded CDN-only diagnostic decks. Does not launch simulations."""
import csv, gzip, hashlib, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'verification/manual_adc/sar_isolation_v1/cdn_slew_v1'
CELL='DFCNQD1BWP12T30P140'
def dump(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    BASE.mkdir(parents=True,exist_ok=True)
    src=ROOT/'output/managed_execution/runs/manual8-sar-a-v6-stress-windows-v1/collected/derived/wave.csv.gz'
    with gzip.open(src,'rt') as f:
        rows=[r for r in csv.DictReader(f) if 210e-9<=float(r['time'])<=210.2e-9]
    t=np.array([float(r['time']) for r in rows]);cdn=np.array([float(r['xdut.clksn']) for r in rows]);data=np.array([float(r['xdut.clk_1']) for r in rows])
    def cross(v,level):
        i=next(i for i in range(1,len(t)) if v[i-1]>level>=v[i])
        return float(t[i-1]+(t[i]-t[i-1])*(level-v[i-1])/(v[i]-v[i-1]))
    mid=cross(cdn,.45)
    # Preserve observed edge, including small overshoot; only trim stable ends to rails.
    def edge(v,factor):
        hi=next(i for i in range(len(t)) if v[i]<.8999)
        lo=next(i for i in range(hi,len(t)) if abs(v[i])<.0001)
        a=max(0,hi-1);b=min(len(t)-1,lo+1)
        ts=5e-9+factor*(t[a:b+1]-mid);vs=v[a:b+1].copy();vs[0]=.9;vs[-1]=0
        return list(zip(ts.tolist(),vs.tolist()))
    dpoints=[(0,.9)]+edge(data,1)+[(9e-9,0)]
    conn=json.loads((ROOT/'verification/manual_adc/stress_diagnosis/native_cell_connectivity.json').read_text())[CELL]
    assert conn['ports']==['D','CP','CDN','Q','VDD','VSS']
    devices=[];signals={'VDD','CDN','CP','DA','DB','QA','QB'}
    for inst,q,d in [('XA','QA','DA'),('XB','QB','DB')]:
        mapping=dict(D=d,CP='CP',CDN='CDN',Q=q,VDD='VDD',VSS='0')
        for m in conn['mos']:
            nodes=[mapping.get(n,inst+'.'+n) for n in m['terminals']]
            signals.update(n for n in nodes if n!='0')
            devices.append(dict(path=inst+'.'+m['name'],terminals=nodes,model=m['model']))
    currents=['VVDD:1','VCDN:1','VCP:1','VDA:1','VDB:1']
    for inst in ['XA','XB']:
        for m in ['MM64','MM65','MM66','MM75','MM76','MM78']:
            currents += [inst+'.'+m+':'+str(i) for i in range(1,5)]
    signals=sorted(signals)+currents
    modelsrc=ROOT/'verification/manual_adc/sar_isolation_v1/tb_a_v6/models.scs'
    def pwl(name,node,pts):
        assert all(pts[i][0]<pts[i+1][0] for i in range(len(pts)-1))
        return name+' ('+node+' 0) vsource type=pwl wave=[ '+' '.join('%.16g %.16g'%p for p in pts)+' ]'
    built=[]
    for k,factor in enumerate([1,2,4]):
        out=BASE/('s'+str(k));out.mkdir(exist_ok=True)
        cp=[(0,0),(1.975e-9,0),(2.025e-9,.9),(2.975e-9,.9),(3.025e-9,0),(7.975e-9,0),(8.025e-9,.9),(9e-9,.9)]
        reset=[(0,0),(.975e-9,0),(1.025e-9,.9)]+edge(cdn,factor)+[(6.975e-9,0),(7.025e-9,.9),(9e-9,.9)]
        lines=['simulator lang=spectre','global 0','include "models.scs"','VVDD (VDD 0) vsource dc=0.9',pwl('VCDN','CDN',reset),pwl('VCP','CP',cp),'VDA (DA 0) vsource dc=0.9',pwl('VDB','DB',dpoints),'XA (DA CP CDN QA VDD 0) '+CELL,'XB (DB CP CDN QB VDD 0) '+CELL,'CQA (QA 0) capacitor c=5f','CQB (QB 0) capacitor c=5f','simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-14 temp=27 tnom=27','tran_test tran stop=9n maxstep=1p errpreset=conservative method=gear2only','saveOptions options save=selected currents=selected']
        lines += ['save '+' '.join(signals[i:i+8]) for i in range(0,len(signals),8)]
        (out/'test.scs').write_text('\n'.join(lines)+'\n');(out/'models.scs').write_bytes(modelsrc.read_bytes())
        dump(out/'measure.json',dict(case='s'+str(k),factor=factor,devices=devices,signals=signals,stop_s=9e-9,window_s=[4.85e-9,6.2e-9],threshold_V=.99))
        rid='manual8-cdn-s%d-tt-v1'%k
        inputs=[dict(source=(out/n).relative_to(ROOT).as_posix(),name=n) for n in ['test.scs','models.scs','measure.json']]
        inputs += [dict(source='scripts/manual_adc/'+n,name=n) for n in ['sar_cdn_reduce.py','reduce.py']]
        recipe=dict(schema_version=1,run_id=rid,design_id='manual8_sar_cdn_slew_v1',entry='test.scs',analyzer='sar_cdn_reduce.py',inputs=inputs,expected_stop_s=9e-9,summary_signals=['CDN','QA','QB'],qualification_scope='Two original D1 cells, CDN diagnostic only, ideal sources and 5fF Q loads; not SAR/PVT qualification',oa_parity='none; OA read-only',test_conditions=dict(corner='tt',vdd=.9,temperature_c=27,noise=False,mismatch=False,PEX=False),spectre_args=['+preset=cx','+mt=1','-preset_override'],resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=512,simulation_wall_seconds=300,analysis_wall_seconds=300,queue_timeout_seconds=600))
        dump(ROOT/'management/recipes'/ (rid+'.yaml'),recipe)
        built.append(dict(run_id=rid,test_sha256=sha(out/'test.scs'),model_include_sha256=sha(out/'models.scs')))
    # Exact single-variable comparison: only VCDN line may differ.
    texts=[(BASE/('s'+str(k))/'test.scs').read_text().splitlines() for k in range(3)]
    assert len({tuple(l for l in x if not l.startswith('VCDN ')) for x in texts})==1
    dump(BASE/'build_receipt.json',dict(source_run='manual8-sar-a-tt-v6',source_display_sha256=sha(src),source_cdn_fall_s=cross(cdn,.09)-cross(cdn,.81),source_d_fall_s=cross(data,.09)-cross(data,.81),source_d_delay_s=cross(data,.45)-mid,replay_note='Native-derived display CSV, stable endpoints within 0.1mV trimmed to rails; same shaping all cases',cell=CELL,mos_per_instance=len(conn['mos']),single_variable_check=True,runs=built,library_conditions=dict(manual='170a TT0.9V25C PDF pages208/210; test27C',max_Q_cap_fF=91.5231,diagnostic_Q_cap_fF=5,CDN_min_low_ps=28.2843,recovery_ps=-22.7608,removal_ps=47.5779,CP_min_high_ps=19.3214,CP_min_low_ps=21.5721,planned_pulse_and_recovery_margin_ns=1,complete_TT27_slew_qualification='unknown; diagnostic sweep, not library/reliability acceptance')))
    print(json.dumps(built,indent=2))
if __name__=='__main__':main()
