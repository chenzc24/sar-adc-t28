from __future__ import print_function
import os,struct,gzip
import full_gate_analyze as native

def pin_edges(rows,index,rail):
    levels={}
    for fraction in [.1,.2,.5,.8,.9]:
        hits=[];level=fraction*rail
        for a,b in zip(rows,rows[1:]):
            x,y=a[index]-level,b[index]-level
            direction=1 if x<0<=y else -1 if x>0>=y else 0
            if direction:hits.append(dict(time_s=a[0]-x*(b[0]-a[0])/(y-x),direction=direction,native_bracket_s=[a[0],b[0]]))
        levels[fraction]=hits
    out=[]
    for e in levels[.5]:
        found={}
        for f,hits in levels.items():
            selected=[h for h in hits if h['direction']==e['direction'] and abs(h['time_s']-e['time_s'])<=.25e-9]
            found[f]=selected[0] if len(selected)==1 else None
        value=dict(e,crossings=dict((str(f),v) for f,v in found.items()))
        for name,a,b in [('slew_10_90_s',.1,.9),('slew_20_80_s',.2,.8)]:
            value[name]=abs(found[b]['time_s']-found[a]['time_s']) if found[a] and found[b] else None
        out.append(value)
    return out


def usage_observations(output,cfg):
    names=native.read(os.path.join(output,'peak.columns.json'))['names'];index=dict((n,i) for i,n in enumerate(names))
    pins=cfg['usage']['input_pins'];columns=[0]+[index[native.norm(n)] for n in pins.values()]
    rows=[];pack=struct.Struct('<'+'d'*len(names));observed=0
    with gzip.open(os.path.join(output,'peak.native.bin.gz'),'rb') as handle:
        while True:
            blob=handle.read(pack.size)
            if not blob:break
            if len(blob)!=pack.size:raise ValueError('Incomplete native diagnostic row')
            row=pack.unpack(blob);rows.append(tuple(row[i] for i in columns));observed+=1
            if observed>200000:raise ValueError('Diagnostic edge-memory budget exceeded')
    return dict(actual_pin_edges=dict((key,pin_edges(rows,j+1,cfg['usage']['vdd_v'])) for j,key in enumerate(pins)),
        pin_waveform_rows=observed,threshold_policy='10/90 and20/80 percent declared0.99V; native linear crossing brackets retained; no library table range inferred',
        intrinsic_channel_overlap_junction_split=None,region_saved=False,
        source_timing_unchanged=True,whole_ADC_qualified=None)

