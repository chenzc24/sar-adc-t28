"""Read-only final OA/dependency/VA provenance audit (no PDK source download)."""
from dataclasses import asdict
from common import LIB, ROOT, OUT, dump, load, sha
from virtuoso_bridge import VirtuosoClient
from oa import check, export
from run import blocks


def main():
    c=VirtuosoClient.from_env(profile='t28_io')
    lib=c.library.get(LIB)
    assert lib.path=='/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28'
    assert lib.technology_library=='tsmcN28'
    dependencies=[p for p in (OUT/'preflight').glob('*.json') if p.stem not in ['library','windows']]
    same={}
    for p in dependencies:
        fresh=c.schematic.read(LIB,p.stem,param_filters=None,include_positions=True)
        dump(f'audit/dependencies/{p.name}',fresh)
        same[p.stem]=fresh==load(f'preflight/{p.name}')
    assert all(same.values()),same
    va={}
    for p in sorted((ROOT/'models/veriloga').glob('cdac8_dualrail_*.va')):
        dest=OUT/'audit/va'/p.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        r=c.download_file(f'{lib.path}/{p.stem}/veriloga/veriloga.va',dest)
        assert not r.errors,r
        va[p.name]={'local_sha256':sha(p),'remote_sha256':sha(dest)}
        assert sha(p)==sha(dest)
    for bit in range(8):check(c,f'cdac8_dr_sw_b{bit}')
    for cell in ['cdac8_dr_nominal','cdac8_dr_literal']:check(c,cell)
    exports={}
    for key in ['nominal','literal','strongarm','ideal_sample']:
        cell=f'tb_cdac8_dr_{key}'
        export(c,cell,'final_audit')
        start=(OUT/f'oa_netlists/{cell}/clean_va/input.scs').read_text()
        end=(OUT/f'oa_netlists/{cell}/final_audit/input.scs').read_text()
        # OA export timestamp is metadata, never a circuit change.
        canonical=lambda t:'\n'.join(l for l in t.splitlines() if not l.startswith('//'))
        exports[cell]=canonical(start)==canonical(end)
        assert exports[cell],cell
        for deck in (OUT/'decks').glob('*.scs'):
            case=load(f'cases/{deck.stem}.json')
            if case['cell']==cell and case['oa_tag']=='clean_va':
                assert blocks(deck.read_text())==blocks(end),deck
    dump('audit/final.json',dict(library=asdict(lib),dependencies_equal=same,va=va,
        final_exports_equal=exports,original_canvas_revision=load('canvas_final.json')['original']['revision']))
    print('FINAL_AUDIT_OK',len(same),'dependencies',len(va),'VA',len(exports),'OA exports',flush=True)


if __name__=='__main__':main()
