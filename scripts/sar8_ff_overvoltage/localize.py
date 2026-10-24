"""Full-resolution peak neighborhoods, timing attribution, frozen device mapping."""
import re
import numpy as np
from inventory import ROOT,OUT,VERIFY,SOURCE,NAMES,read,dump,sha

def edges(t,v,level=.495):
    rows=[]
    for up in [True,False]:
        ids=np.flatnonzero((v[:-1]<level)&(v[1:]>=level) if up else (v[:-1]>level)&(v[1:]<=level))
        for i in ids:rows.append((float(t[i]+(level-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i])), 'rise' if up else 'fall'))
    return sorted(rows)

def duration(t,v,level,idx):
    assert v[idx]>level
    a=idx;b=idx
    while a>0 and v[a-1]>level:a-=1
    while b<len(v)-1 and v[b+1]>level:b+=1
    left=float(t[a]) if a==0 else float(t[a-1]+(level-v[a-1])*(t[a]-t[a-1])/(v[a]-v[a-1]))
    right=float(t[b]) if b==len(v)-1 else float(t[b]+(level-v[b])*(t[b+1]-t[b])/(v[b+1]-v[b]))
    return dict(start_ns=left,end_ns=right,duration_ps=(right-left)*1000,truncated=(a==0 or b==len(v)-1))

def mapping(text):
    logical=text.replace('\\\n',' ');cells={}
    for m in re.finditer(r'(?ms)^subckt (\w+) ([^\n]+)\n(.*?)^ends \1',logical):
        cells[m[1]]=(m[2].split(),m[3])
    devices={}
    def walk(master,path,bind):
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)',cells[master][1]):
            label,nodes,model,tail=m.groups();path1=path+'.'+label
            ns=[bind.get(n,n if n in ['0','VDD!'] else path+'.'+n) for n in nodes.split()]
            if model in cells:
                assert len(ns)==len(cells[model][0]);walk(model,path1,dict(zip(cells[model][0],ns)))
            else:devices[path1]=dict(model=model,nodes=[n.lower() for n in ns],parameters=dict(re.findall(r'(\w+)=([^\s]+)',tail)))
    ports=cells['sar_adc8_join_r4'][0];walk('sar_adc8_join_r4','XDUT',dict(zip(ports,ports)))
    return devices

def main():
    inv=read(VERIFY/'inventory.json');results={}
    for name in NAMES:
        data=inv[name];tw=dict(np.load(OUT/(name+'_timing.npz')));tt=tw['time']*1e9
        assert sha(OUT/(name+'_timing.npz'))==data['timing_sha256']
        eventlist=[]
        for n,v in tw.items():
            if n in ['time','vdd!']:continue
            for at,direction in edges(tt,v):eventlist.append(dict(signal=n,time_ns=at,direction=direction))
        devices=mapping((SOURCE/name/'dut.scs').read_text())
        probes=read(SOURCE/name/'context.json')['stress_devices'];allmos=[(k,v) for k,v in devices.items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']]
        summary={}
        for group in ['reference','reference_driver','sequencer','comparator']:
            meta=data['windows'][group];peak=meta['worst'];cache=OUT/(name+'_'+group+'.npz')
            assert sha(cache)==meta['cache_sha256'];w=dict(np.load(cache));t=w['time']*1e9;p=peak['time_ns']
            a,b=peak['nodes'];v=(w[a] if a!='0' else 0)-(w[b] if b!='0' else 0);idx=int(np.argmax(abs(v)))
            row=dict(peak=peak,signed_peak_v=float(v[idx]),device=devices[peak['instance']],
              native_peak_step_ps=float((t[idx+1]-t[idx-1])*500),
              duration_above_limit=duration(t,abs(v),.99,idx),duration_above_limit_plus1mV=duration(t,abs(v),.991,idx),
              nearest_events=sorted(eventlist,key=lambda e:abs(e['time_ns']-p))[:8],
              supplies_v=dict(min=float(min(w['vdd!'])),max=float(max(w['vdd!']))))
            offsets=np.array([-.2,-.1,-.05,-.02,0,.02,.05,.1,.2])
            if group=='reference':
                signals=['xdut.gnn4','xdut.xref.xdrv4.gnndrv','xdut.xref.xdrv4.gnnb','xdut.xcdac.bn4',
                  'xdut.xcdac.bn7','xdut.gnn7','xdut.gnp7','xdut.xref.rst7','xdut.xref.rst4','xdut.xref.q7','xdut.xref.q4','xdut.topp','xdut.topn']
            elif group=='reference_driver':
                tag='gnn' if 'm40' in name else 'gpn'
                signals=['xdut.xref.xdrv0.'+tag+s for s in ['pre','a','b','drv']]+['xdut.'+tag+'0','xdut.xref.h0','xdut.xref.l0']
            elif group=='sequencer':signals=['xdut.active','xdut.xidle.idle','xdut.phi_u','xdut.cmp_clk','xdut.xctrl.phi_w']
            else:signals=['xdut.xcomp.x','xdut.xcomp.y','xdut.xcomp.tail','xdut.comp_p','xdut.comp_n','xdut.cmp_clk']
            row['offsets_ps']=(offsets*1000).tolist()
            row['samples']={n:np.interp(p+offsets,t,w[n]).tolist() for n in signals}
            # Devices sharing this victim voltage: do not mistake multiple warnings for independent events.
            victim=a if a!='0' else b
            row['connected_MOS']={k:d for k,d in allmos if victim in d['nodes']}
            summary[group]=row
            print(name,group,'peak',p,'duration1mV',row['duration_above_limit_plus1mV'],flush=True)
            print('nearest',row['nearest_events'][:4]);print('samples',row['samples'])
        results[name]=dict(events=summary,selected_MOS_count=len(probes),netlisted_MOS_instances=len(allmos),
          coverage_note='2670 pairs belong to445 selected MOS instances, NOT every MOS in the ADC. Native warning log covers more devices but may suppress repeated warnings. No missing internal node is synthesized.',
          timing_events=sorted(eventlist,key=lambda e:e['time_ns']))
    dump(VERIFY/'events.json',results)

if __name__=='__main__':main()
