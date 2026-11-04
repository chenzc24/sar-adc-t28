"""Python2.7 streaming terminal-current and charge-balance diagnosis; no circuit edits."""
from __future__ import print_function
import argparse
import gzip
import json
import os
from reduce import frames, norm
import cdac_l60pvt_edge_reduce as cdac_edge_reduce


def main():
    cdac_edge_reduce.main()  # Keep the established precision/timing/stress measurements.
    ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--output-dir',required=True)
    a=ap.parse_args();cfg=json.load(open(a.run_dir+'/inputs/measure.json'));ex=cfg['leakage']
    result=json.load(open(a.output_dir+'/result.json'))
    TH=.5*cfg['logic_vdd_V']
    paths=[a.run_dir+'/raw/'+f for f in os.listdir(a.run_dir+'/raw') if f.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected one native transient')
    names=sorted(set(norm(n) for n in cfg['signals']+ex['extra_signals']))
    devices=cfg['devices'];branches=ex['branches'];windows=ex['steady_windows_s']
    # Export all native samples around every terminal peak and bottom minimum.
    # Metrics still use every point; merged intervals bound local plot payload.
    ranges=list(ex['native_windows_s'])
    ranges += [(q['time_s']-300e-12,q['time_s']+300e-12) for q in result['terminal_pairs']]
    ranges += [(q['min_s']-300e-12,q['min_s']+300e-12) for k,q in result['node_extrema'].items() if '.xd.net' in k]
    merged=[]
    for left,right in sorted(ranges):
        if merged and left<=merged[-1][1]:merged[-1][1]=max(right,merged[-1][1])
        else:merged.append([left,right])
    result['current_export_native_windows_s']=merged

    accum=[{'duration_s':0.,'integrals':{}} for w in windows]
    kcl={'device_four_ports':{},'bottom_nodes':{},'high_reference':0.,'low_reference':0.}
    peaks={};closes=[];previous=None;last_write=-1.;count=0
    out=gzip.open(a.output_dir+'/branch_wave.csv.gz','wb')
    out.write(('time,'+','.join(names)+'\n').encode('ascii'))

    def values(v,close):
        d={'refp_draw_A':-v['vrefp:1'],'refn_receive_A':v['vrefn:1'],'body_supply_draw_A':-v['vvdd:1']}
        init={s:v0 for s,v0 in [('P',close['xadc.topp']-close['vinp']),('N',close['xadc.topn']-close['vinn'])]}
        ideal={s:close['vin'+s.lower()] for s in ['P','N']};pred=dict(init)
        for dev in devices:
            p=norm(dev['path']);ts=[v[norm(n)] if n!='0' else 0. for n in dev['terminals']]
            for idx,term in enumerate('DGSB'):
                d[p+'.I'+term]=v[p+':'+str(idx+1)]
            d[p+'.VGS']=ts[1]-ts[2];d[p+'.VDS']=ts[0]-ts[2];d[p+'.VBS']=ts[3]-ts[2]
        for b in branches:
            key=b['side']+str(b['weight']);g=v[norm(b['gate'])];bottom=v[norm(b['bottom'])]
            high=g<TH;rail=.9 if high else 0.;initial=.9 if b['bit']!=7 else 0.
            delta=bottom-rail;delta0=close[norm(b['bottom'])]-initial
            contribution=(delta-delta0)*b['weight']/128.
            p=norm(b['pmos']);n=norm(b['nmos'])
            d[key+'.bottom_V']=bottom;d[key+'.gate_V']=g;d[key+'.rail_error_V']=delta
            d[key+'.initial_rail_error_V']=delta0
            d[key+'.dm_contribution_V']=contribution*(1 if b['side']=='P' else -1)
            d[key+'.refp_draw_A']=v[p+':3'];d[key+'.refn_receive_A']=-v[n+':3']
            d[key+'.off_drain_A']=v[n+':1'] if high else v[p+':1']
            d[key+'.on_drain_A']=v[p+':1'] if high else v[n+':1']
            d[key+'.cap_bottom_A']=v[norm(b['capacitor'])+':2']
            d[key+'.high_state']=float(high)
            pred[b['side']]+=contribution
            ideal[b['side']]+=(rail-initial)*b['weight']/128.
        for s in ['P','N']:
            d[s+'.initial_top_error_V']=init[s]
            d[s+'.actual_top_error_V']=v['xadc.top'+s.lower()]-ideal[s]
            d[s+'.predicted_top_error_V']=pred[s]
        d['actual_dm_error_V']=d['P.actual_top_error_V']-d['N.actual_top_error_V']
        d['predicted_dm_error_V']=pred['P']-pred['N']
        d['dm_reconstruction_residual_V']=d['actual_dm_error_V']-d['predicted_dm_error_V']
        return d

    for t,v in frames(paths[0]):
        v['0']=0.;count+=1
        if count==1:
            missing=set(names)-set(v)
            if missing:raise ValueError('Missing current ports '+str(sorted(missing)))
        for dev in devices:
            p=norm(dev['path']);curr=[v[p+':'+str(i)] for i in [1,2,3,4]]
            kcl['device_four_ports'][p]=max(kcl['device_four_ports'].get(p,0.),abs(sum(curr)))
            peaks[p]=max(peaks.get(p,0.),max(abs(x) for x in curr))
        for b in branches:
            p=norm(b['pmos']);n=norm(b['nmos']);cap=norm(b['capacitor'])
            resid=v[p+':1']+v[n+':1']+v[cap+':2']
            node=norm(b['bottom']);kcl['bottom_nodes'][node]=max(kcl['bottom_nodes'].get(node,0.),abs(resid))
        hp=v['vrefp:1']+sum(v[norm(b['pmos'])+':3'] for b in branches)
        lp=v['vrefn:1']+sum(v[norm(b['nmos'])+':3'] for b in branches)
        kcl['high_reference']=max(kcl['high_reference'],abs(hp));kcl['low_reference']=max(kcl['low_reference'],abs(lp))
        if previous:
            tp,vp=previous;dt=t-tp
            if vp['clks']>=TH>v['clks']:
                ratio=(TH-vp['clks'])/(v['clks']-vp['clks'])
                close={n:vp[n]+ratio*(v[n]-vp[n]) for n in v}
                closes.append(close)
            for idx,(start,end) in enumerate(windows):
                left=max(start,tp);right=min(end,t)
                if right<=left:continue
                if len(closes)<=idx:raise ValueError('Missing sample close')
                old=values(vp,closes[idx]);new=values(v,closes[idx]);mid=(.5*(left+right)-tp)/dt
                duration=right-left;acc=accum[idx];acc['duration_s']+=duration
                for key in old:
                    val=old[key]+mid*(new[key]-old[key])
                    acc['integrals'][key]=acc['integrals'].get(key,0.)+val*duration
        native=any(start<=t<=end for start,end in merged)
        if native or t-last_write>=100e-12 or previous is None:
            out.write((','.join(['%.15g'%t]+['%.15g'%v[n] for n in names])+'\n').encode('ascii'));last_write=t
        previous=(t,v)
    out.close()
    if abs(t-cfg['stop_s'])>1e-14 or len(closes)!=8:raise ValueError('Incomplete run/close count')
    steady=[]
    for idx,(acc,w) in enumerate(zip(accum,windows)):
        if abs(acc['duration_s']-(w[1]-w[0]))>1e-15:raise ValueError('Window coverage')
        steady.append({'frame':idx,'code':cfg['codes'][idx],'window_s':w,'duration_s':acc['duration_s'],
                       'mean':{k:x/acc['duration_s'] for k,x in acc['integrals'].items()}})
    worstkcl=max([kcl['high_reference'],kcl['low_reference']]+list(kcl['device_four_ports'].values())+list(kcl['bottom_nodes'].values()))
    # 1nA is a numerical closure screen, not a leakage budget. Retain failures.
    result['leakage']={'run_id':ex['run_id'],'source_run_id':ex['source_run_id'],'native_points':count,
                       'branches':branches,'devices':devices,'steady':steady,'kcl_max_A':kcl,'kcl_screen_pass':worstkcl<1e-9,
                       'largest_kcl_residual_A':worstkcl,'terminal_current_peaks_A':peaks,
                       'sign_convention':ex['positive_current'],
                       'current_scope':'External macro terminal totals include conduction, junction, gate and displacement. No microscopic mechanism partition assumed.',
                       'charge_balance':'Top error = initial top error + sum C_i/Ctotal * (bottom rail error now - at sample close); compare against measured top error.',
                       'export':'All native points in current_export_native_windows_s; elsewhere >=100ps display sampling. Metrics use all native points.'}
    json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
    total=sum(os.path.getsize(a.output_dir+'/'+f) for f in os.listdir(a.output_dir))
    if total>28*1024**2:raise ValueError('Derived output exceeds28MiB')
    print('Leakage measured',count,'points; KCL residual',worstkcl,'bytes',total)

if __name__=='__main__':main()
