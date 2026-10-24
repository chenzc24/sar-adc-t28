"""Separate bit7-caused peak from a later peak after bit4 releases its helper."""
import numpy as np
import importlib.util
from control import ROOT,OUT,VERIFY,read,dump,sha
spec=importlib.util.spec_from_file_location('gate_analysis',ROOT/'scripts/sar8_ref_gate_controls/analyze.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)

def main():
    for path in VERIFY.glob('*_metrics.json'):
        r=read(path)
        cache=OUT/(r['name']+'_window.npz');assert sha(cache)==r['cache_sha256']
        w=dict(np.load(cache));t=w['time']*1e9;y=w['xdut.xref.rst4']
        def falling_level(y,level):
            ids=np.flatnonzero((y[:-1]>level)&(y[1:]<=level))
            i=next(i for i in ids if t[i]>=r['rst7_ns'])
            return float(t[i]+(level-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i]))
        ygate=w['xdut.gnp7']/w['vdd!']
        r['bit7_gnp_fall90to10_ps']=(falling_level(ygate,.1)-falling_level(ygate,.9))*1000
        if 'idle_gnn4_peak_v' in r:
            dump(path,r);continue
        ids=np.flatnonzero((y[:-1]<.495)&(y[1:]>=.495));ids=[i for i in ids if t[i]>r['rst7_ns']]
        i=ids[0];own=t[i]+(.495-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])
        mask=(t>=r['rst7_ns'])&(t<own-.01);j=np.flatnonzero(mask)[np.argmax(w['xdut.gnn4'][mask])]
        r['idle_gnn4_peak_v']=r['same_event_gnn4_peak_v'];r['idle_gnn4_peak_time_ns']=r['same_event_gnn4_peak_time_ns']
        r['same_event_gnn4_peak_v']=float(w['xdut.gnn4'][j]);r['same_event_gnn4_peak_time_ns']=float(t[j]);r['same_event_end_before_rst4_ns']=float(own-.01)
        dump(path,r);print('Separated event window',r['name'],r['same_event_gnn4_peak_v'],r['idle_gnn4_peak_v'])
    analysis.combine()

if __name__=='__main__':main()
