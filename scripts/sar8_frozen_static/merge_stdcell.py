"""Reapply only reviewed digital migration to immutable historical baseline."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CONTROL=ROOT/'verification/sar8_module_audit/control'
sys.path.insert(0,str(CONTROL))
import prepare_standard_cell_full as migration


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    src=ROOT/'netlist/sar8_l90_mmain2_frozen/dut.scs'
    assert sha(src)=='41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4'
    out=ROOT/'netlist/sar8_l90_mmain2_stdcell_v1'
    assert not out.exists(), 'Immutable candidate exists'
    text=src.read_text()
    candidate,pairs,changed=migration.candidate(text)
    old=migration.base.cells(text);new=migration.base.cells(candidate)
    expected=['sar8p_inv','sar8p_nand2','sar8p_dffr','sar8p_clkbuf']+['sar8p_refdrv_b%d'%i for i in range(8)]
    assert set(changed)==set(expected) and len(pairs)==96
    assert set(old)==set(new)
    restored=candidate
    for master in changed:
        assert migration.header(old[master])==migration.header(new[master])
        restored=restored.replace(new[master],old[master],1)
        if master.startswith('sar8p_refdrv_'):
            a=migration.base.parts(old[master]);b=migration.base.parts(new[master])
            for name,part in a.items():
                if part['model'] not in ['nch_mac','pch_mac']:
                    assert b[name]==part, (master,name)
    assert restored==text, 'Replacement contains unrelated change'
    out.mkdir()
    (out/'dut.scs').write_text(candidate,encoding='utf-8')
    lib=json.loads((CONTROL/'standard_cell_full_v1/ff/external_library.json').read_text())
    (out/'library_include.scs').write_text('simulator lang=spice\n.include "'+lib['file']+'"\nsimulator lang=spectre\n',encoding='utf-8')
    manifest=dict(parent=src.relative_to(ROOT).as_posix(),parent_sha256=sha(src),candidate_sha256=sha(out/'dut.scs'),
        transform=migration.__file__,transform_sha256=sha(Path(migration.__file__)),
        changed_masters=changed,reference_inverter_pairs=len(pairs),reference_pairs=pairs,
        exact_inverse_pass=True,unchanged_other_subcircuits=True,unchanged_driver_non_MOS=True,
        external_library=lib,simulation_performed=False,adopted_baseline=False,
        scope='Structure-only rebase of digital migration; timing/load/function unverified on this parent')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:manifest[k] for k in ['parent_sha256','candidate_sha256','changed_masters','reference_inverter_pairs','exact_inverse_pass','simulation_performed']}))


if __name__=='__main__':main()
