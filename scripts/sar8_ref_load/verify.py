"""Focused source, scalar-reader and steady-gate validation, no simulation launch."""
import re
import numpy as np
from control import ROOT,OUT,VERIFY,SOURCE,NAMES,read,dump,sha
from native import load

ctx0=read(SOURCE/'context.json');original=(SOURCE/'test.scs').read_text();dut=(SOURCE/'dut.scs').read_text()
assert sha(SOURCE/'test.scs')==ctx0['deck_sha256'] and sha(SOURCE/'dut.scs')==ctx0['DUT_sha256']
proof={};stable={}
for name in NAMES+['pair_ffhot','pair_ffcold_fixedbias','pair_ffhot_op']:
    folder=OUT/name;ctx=read(folder/'context.json');receipt=read(folder/'receipt.json')
    assert sha(folder/'test.scs')==ctx['deck_sha256']==receipt['remote_deck_sha256']
    assert receipt['native_exit']==0
    if name in NAMES:
        text=(folder/'test.scs').read_text();assert dut in text
        text=text.replace('stop=180n','stop=600n').replace('outputstart=120n','outputstart=0n')
        if name.endswith('cold'):text=text.replace('temp=-40 tnom=27','temp=125 tnom=27')
        line=re.search(r'(?m)^save .+$',original)[0]
        text=re.sub(r'(?m)^save .+$',lambda m:line,text)
        assert text==original
        w=dict(np.load(folder/'wave.npz'));t=w['time']*1e9;mask=(t>=120)&(t<=140)
        r=read(VERIFY/(name+'.json'));gate=[]
        for br in r['branches']:
            side,b=br['side'],br['bit']
            gn=w[f'xdut.g{side.lower()}n{b}'][mask];gp=w[f'xdut.g{side.lower()}p{b}'][mask]
            # Detect persistent simultaneous commanded conduction in the settled interval.
            assert not np.any((gn>.495)&(gp<.495))
            gate.append(float(np.max(abs(gn))) if br['off_device']=='MN_LOW' else float(np.max(abs(gp-.99))))
        assert max(gate)<.001
        stable[name]=dict(max_off_gate_rail_error_v=max(gate),interval_ns=[120,140],command_overlap=False)
    elif name!='pair_ffhot_op':
        path=folder/'native/test.raw/dc_leak.dc';w=load(path);text=path.read_text().split('VALUE')[1].split('END')[0]
        for key in ['DELTA','Xactual_N.MP_HIGH:3','Xideal_N.MP_HIGH:3','Xactual_P.MP_HIGH:3']:
            matches=re.findall(r'(?m)^"'+re.escape(key)+r'" (.+)$',text)
            independently=np.array([float(s.split()[-1]) for s in matches])
            assert np.array_equal(independently,w[key.lower()])
    proof[name]=dict(remote_local_deck_sha256=ctx['deck_sha256'],native_exit=0,
                    native_files=receipt['native_files'])
local_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
assert local_bytes<300*1024**2
dump(VERIFY/'validation.json',dict(original_unchanged=True,probe_only_inverse_pass=True,
     scalar_DC_reader_independent_match=True,steady_gate_checks=stable,cases=proof,
     local_bytes=local_bytes,OA_changed=False,PDK_changed=False,production_circuit_changed=False))
print('Source, five native receipts, scalar parser and gate checks PASS; local MiB',local_bytes/1024**2)
