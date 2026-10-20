"""Independent netlist-only driver removal. Never edits saved OA or PDK files."""
import argparse
import contextlib
import json
import re
import shutil
from pathlib import Path
from common import ROOT, OUT as BASE, sha
from run import blocks

OUT=ROOT/'output/cdac8_no_driver'
DRIVERS={'MP_IL1','MN_IL1','MP_IL2','MN_IL2','MP_IH','MN_IH'}
CASES=[('native_bad',False,1,'clean_va_input_-3516'),
       ('direct_bad',True,1,'clean_va_input_-3516'),
       ('direct_bad_half',True,.5,'clean_va_input_-3516'),
       ('direct_bad_double',True,2,'clean_va_input_-3516'),
       ('direct_control',True,1,'final_nominal')]


def dump(relative,value):
    p=OUT/relative;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def load(relative):return json.loads((OUT/relative).read_text(encoding='utf-8'))


def statements(block):
    lines=block.splitlines(keepends=True);out={};j=0
    while j<len(lines):
        m=re.match(r'^    (\w+)\s+\(',lines[j])
        if m:
            start=j
            while lines[j].rstrip().endswith('\\'):j+=1
            out[m[1]]=''.join(lines[start:j+1])
        j+=1
    return out


def remove_driver(block):
    old=statements(block)
    assert set(old)==DRIVERS|{'MP_HIGH','MN_LOW'},set(old)
    for name in DRIVERS:block=block.replace(old[name],'',1)
    end=re.search(r'(?m)^ends ',block);assert end
    ideal=('    E_PGATE (EH_B VDD EH VSS) vcvs gain=-1\n'
           '    E_NGATE (EL_D VSS EL VSS) vcvs gain=1\n')
    block=block[:end.start()]+ideal+block[end.start():]
    new=statements(block)
    assert set(new)=={'MP_HIGH','MN_LOW','E_PGATE','E_NGATE'}
    for name in ['MP_HIGH','MN_LOW']:assert new[name]==old[name]
    return block


def prepare(name,direct,mult,source,fine=False):
    source_path=BASE/f'decks/{source}.scs'
    original=source_path.read_text();before=blocks(original)
    retained=json.loads((BASE/f'runs/{source}_result.json').read_text())
    assert retained['ok'] and sha(source_path)==retained['deck_sha256']
    includes=[]
    for filename,h in retained['va_sha256'].items():
        local=ROOT/'models/veriloga'/filename
        assert sha(local)==h,(filename,'local VA changed since retained run')
        target=OUT/'sources'/filename;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert sha(target)==h
        else:shutil.copyfile(local,target)
        includes.append(str(target))
    text=original
    if direct:
        for bit in range(8):
            key=f'cdac8_dr_sw_b{bit}'
            text=text.replace(before[key],remove_driver(before[key]),1)
        text=re.sub(r' ?XCDAC\.XS[PN]\d\.EL_B\b','',text)
    after=blocks(text)
    changed=[k for k in before if before[k]!=after[k]]
    assert changed==([f'cdac8_dr_sw_b{b}' for b in range(8)] if direct else [])
    # Only top-level experiment parameters/VA include locations/analysis change.
    text,n=re.subn(r'(?m)\bMULT_R=1\b',f'MULT_R={mult:g}',text,count=1);assert n==1
    if fine:
        text,n=re.subn(r'maxstep=100p',r'maxstep=10p',text,count=1);assert n==1
    def stage(m):
        # OA stores each module as <cell>/veriloga/veriloga.va, whereas the
        # staged, version-pinned source uses its unique module filename.
        match=re.search(r'/SAR_ADC_T28/([^/]+)/veriloga/veriloga\.va$',m[1]);assert match,m[1]
        filename=match[1]+'.va'
        assert filename in retained['va_sha256']
        return f'ahdl_include "{filename}"'
    text,n=re.subn(r'ahdl_include "([^"]+)"',stage,text)
    assert n==3 and blocks(text)==after
    deck=OUT/f'decks/{name}.scs';deck.parent.mkdir(parents=True,exist_ok=True)
    assert not deck.exists(),f'Preserve {name}'
    deck.write_text(text,encoding='utf-8')
    old_case=json.loads((BASE/f'cases/{source}.json').read_text())
    case=dict(name=name,direct_gates=direct,pass_multiplier=mult,source_case=source,
        source_deck_sha256=sha(source_path),deck_sha256=sha(deck),va_sha256=retained['va_sha256'],
        include_files=includes,changed_native_subckts=changed,stop_ns=300,
        native_reference_mos_count=32 if direct else 128,
        vdiff_v=old_case['parameters']['VDIFF'],corner='tt',temperature_c=27,supply_v=.9,
        dead_time_s=1e-10,command_edge_s=20e-12,maxstep_s=1e-11 if fine else 1e-10,
        scope='explicit netlist-level diagnostic, not an OA implementation or baseline change')
    dump(f'cases/{name}.json',case)
    print('PREPARED',name,'direct' if direct else 'native','MULT_R',mult,flush=True)


def run(names):
    from virtuoso_bridge.spectre import SpectreSimulator
    from virtuoso_bridge.spectre.runner import spectre_mode_args
    sim=SpectreSimulator.from_env(profile='t28_io',work_dir=OUT/'spectre',timeout=1800,
        spectre_args=[*spectre_mode_args('aps'),'+lqtimeout','60'])
    cases=[load(f'cases/{name}.json') for name in names]
    for name in names:assert not (OUT/f'runs/{name}_result.json').exists(),f'Preserve {name}'
    tasks=[(OUT/f"decks/{c['name']}.scs",{'include_files':c['include_files']}) for c in cases]
    with (OUT/'runner.log').open('a',encoding='utf-8') as f:
        with contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
            results=sim.run_parallel(tasks,max_workers=2)
    for case,r in zip(cases,results,strict=True):
        name=case['name']
        dump(f'runs/{name}_result.json',dict(ok=r.ok,errors=r.errors,warnings=r.warnings,
            metadata=r.metadata,deck_sha256=sha(OUT/f'decks/{name}.scs'),va_sha256=case['va_sha256']))
        if r.ok:
            dump(f'runs/{name}_waveform.json',{str(k).strip('"').replace('\\','').lower():v for k,v in r.data.items()})
        print('SPECTRE',name,r.ok,r.errors[:4],flush=True)
    assert all(r.ok for r in results),'All failure logs/results preserved'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','prepare_fine']);p.add_argument('--names',nargs='+');a=p.parse_args()
    if a.action=='prepare':
        for case in CASES:prepare(*case)
    elif a.action=='prepare_fine':prepare('direct_bad_double_fine',True,2,'clean_va_input_-3516',True)
    else:run(a.names or [c[0] for c in CASES])
