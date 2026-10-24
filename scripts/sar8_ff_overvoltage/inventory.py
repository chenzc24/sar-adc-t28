"""Read frozen native evidence; separate peak-pair inventory from event causes."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_ff_overvoltage';VERIFY=ROOT/'verification/sar8_ff_overvoltage'
SOURCE=ROOT/'output/sar8_ref_length'
NAMES=['l90_ff_099_m40_static','l90_ff_099_125_static']
OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    summaries={}
    for name in NAMES:
        folder=SOURCE/name;ctx=read(folder/'context.json');path=folder/'reduced/reduced.json.gz'
        assert sha(path)==read(folder/'reduced_receipt.json')['compressed_sha256']
        assert sha(folder/'test.scs')==ctx['deck_sha256'] and sha(folder/'dut.scs')==ctx['DUT_sha256']
        with gzip.open(path,'rt') as f:r=json.load(f)
        old=read(ROOT/'verification/sar8_ref_length'/(name+'.json'))
        assert r['native_psf_sha256']==old['native_psf_sha256'] and r['PSF_END']
        log=(folder/'reduced/spectre.out').read_text()
        assert 'spectre completes with 0 errors' in log
        stress=r['stress'];assert len(stress)==2670
        groups={}
        for g in sorted({s['group'] for s in stress}):
            rows=[s for s in stress if s['group']==g]
            groups[g]=dict(top=sorted(rows,key=lambda s:s['peak_v']/s['limit_v'],reverse=True)[:12],
                bins={str(mv):dict(pairs=sum(s['peak_v']>s['limit_v']+mv/1000 for s in rows),
                    unique_MOS=len({s['instance'] for s in rows if s['peak_v']>s['limit_v']+mv/1000}),
                    unique_node_pairs=len({tuple(sorted(s['nodes'])) for s in rows if s['peak_v']>s['limit_v']+mv/1000}))
                    for mv in [0,1,10,25,50]})
        windows={}
        for win in r['windows']:
            group=win['group'];w={k:np.array(v) for k,v in win['wave'].items()}
            dest=OUT/(name+'_'+group+'.npz');np.savez_compressed(dest,**w)
            worst=win['worst'];a,b=worst['nodes'];va=w[a] if a!='0' else 0;vb=w[b] if b!='0' else 0
            volts=va-vb;idx=int(np.argmax(abs(volts)))
            assert abs(abs(volts[idx])-worst['peak_v'])<1e-12
            windows[group]=dict(worst=worst,cache_sha256=sha(dest),start_ns=w['time'][0]*1e9,end_ns=w['time'][-1]*1e9,
                signed_peak_v=float(volts[idx]),peak_time_ns=float(w['time'][idx]*1e9),
                VDD_min_v=float(min(w['vdd!'])),VDD_max_v=float(max(w['vdd!'])),signals=len(w),native_samples=len(w['time']))
        # Full timing wave retained for assigning conversion/reset events, not redecimated.
        keep=['time','sample','vdd!','xdut.seq_sample','xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u',
              'xdut.active','xdut.xref.cap_clk','xdut.rst_done']
        keep += ['xdut.xref.rst'+str(b) for b in range(8)]
        timepath=OUT/(name+'_timing.npz');np.savez_compressed(timepath,**{k:r['wave'][k] for k in keep})
        summaries[name]=dict(context=dict(corner=ctx['corner'],vdd=ctx['vdd'],temperature_c=ctx['temperature_c'],
             DUT_sha256=ctx['DUT_sha256'],deck_sha256=ctx['deck_sha256'],native_psf_sha256=r['native_psf_sha256'],
             effective_settings=old['effective_settings']),groups=groups,windows=windows,
             timing_sha256=sha(timepath),native_CMI_lines=old['CMI_or_suppression_lines'],
             threshold_note='Bins above0/1/10/25/50mV are descriptive, NOT relaxations of model SOA limits. Pair/MOS/node counts are not event counts.',
             all_pair_peaks=stress)
        print(name)
        for g,row in groups.items():print(g,'bins',row['bins'],'worst',windows[g]['worst'],flush=True)
        del r
    dump(VERIFY/'inventory.json',summaries)

if __name__=='__main__':main()
