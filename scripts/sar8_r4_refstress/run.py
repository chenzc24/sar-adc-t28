"""One-thread diagnostic replay; immutable DUT and continuous sine history."""
from pathlib import Path
import sys
import json
import re
import contextlib
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
from common import blocks,sha,dump,read,SOURCE

OUT=ROOT/'output/sar8_r4_refstress/replay01'
source=ROOT/'output/sar8_r4_performance/cases/sine_cx_1024_k461'

def main():
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    assert not OUT.exists(),'Diagnostic already exists: inspect rather than duplicate'
    source_ctx=read(source/'context.json')
    text=(source/'sine_cx_1024_k461.scs').read_text()
    assert sha(source/'sine_cx_1024_k461.scs')==source_ctx['deck_sha256']
    text,n=re.subn(r'(?m)^tran_perf tran.*$',
        'tran_perf tran stop=450n maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=all outputstart=398n',text)
    assert n==1
    saves=['SAMPLE','XDUT.SAMPLE_INT','XDUT.CMP_CLK','XDUT.PHI_U','XDUT.XREF.CAP_CLK',
           'XDUT.TOPP','XDUT.TOPN','VINP','VINN','VINP_SRC','VINN_SRC','VREFP','VREFN','VDD!',
           'XDUT.XBOOTP.G','XDUT.XBOOTN.G']
    for bit in (5,6,7):
        saves += [f'XDUT.XCDAC.BP{bit}',f'XDUT.XCDAC.BN{bit}',f'XDUT.XREF.Q{bit}']
        saves += [f'XDUT.{g}{bit}' for g in ('GPP','GPN','GNP','GNN')]
    text,n=re.subn(r'(?m)^save .*$', 'save '+' '.join(saves),text);assert n==1
    assert blocks(text)==blocks((SOURCE/'dut.scs').read_text())
    OUT.mkdir(parents=True)
    for inc in source_ctx['includes']:
        original=Path(inc['path']);assert sha(original)==inc['sha256']
        (OUT/original.name).write_bytes(original.read_bytes())
    deck=OUT/'refstress.scs';deck.write_text(text)
    dump(OUT/'context.json',dict(source_case=source_ctx['name'],source_deck_sha256=source_ctx['deck_sha256'],
         deck_sha256=sha(deck),DUT_unchanged=True,saved_signals=saves,stop_ns=450,outputstart_ns=398,
         solver='CX',threads=1,measurement_only=True))
    sim=SpectreSimulator.from_env(profile='t28_io',work_dir=OUT/'spectre',timeout=3600,
         spectre_args=['+preset=cx','+mt=1','+lqtimeout','60'])
    start=time.monotonic()
    with (OUT/'runner.log').open('w') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        r=sim.run_simulation(deck,dict(include_files=[OUT/'r4_perf_monitor.va']))
    dump(OUT/'result.json',dict(ok=r.ok,errors=r.errors,warnings=r.warnings,metadata=r.metadata,
         elapsed_s=time.monotonic()-start,deck_sha256=sha(deck)))
    assert r.ok,r.errors
    w={str(k).strip('"').replace('\\','').lower():np.asarray(v) for k,v in r.data.items()
       if isinstance(v,(list,np.ndarray)) and str(k).lower()!='units'}
    assert np.all(np.diff(w['time'])>0) and w['time'][-1]>=450e-9-1e-14
    assert all(len(v)==len(w['time']) and np.isfinite(v).all() for v in w.values())
    np.savez_compressed(OUT/'wave.npz',**w)
    dump(OUT/'wave_receipt.json',dict(sha256=sha(OUT/'wave.npz'),points=len(w['time']),signals=list(w)))
    print('COMPLETE',r.ok,len(w['time']),flush=True)

if __name__=='__main__':main()
