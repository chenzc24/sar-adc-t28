"""Small review summary; omit model bodies, remote commands and raw PSF data."""
import json
from common import ROOT,OUT,load,sha


def main():
    rows=load('metrics/summary.json')
    final=[r for r in rows if r['name'].startswith(('final_','clean_va_'))]
    audit=load('audit/final.json');canvas=load('canvas_final_v2.json')
    proof=[]
    for row in final:
        name=row['name'];case=load(f'cases/{name}.json');result=load(f'runs/{name}_result.json')
        if row['ok']:
            assert result['ok']
            assert sha(OUT/f'decks/{name}.scs')==result['deck_sha256']==case['deck_sha256']
            for va,h in result['va_sha256'].items():assert sha(ROOT/'models/veriloga'/va)==h
        proof.append(dict(metrics=row,case=case,result_ok=result['ok'],va_sha256=result['va_sha256']))
    summary=dict(candidate_only=True,baseline_promoted=False,
        validation_status='failed_native_TT_reference_core_stress; long scans intentionally interrupted',
        completed_final_runs=sum(r['ok'] for r in final),
        interrupted_final_runs=[r['name'] for r in final if not r['ok']],
        completed_all_versions=sum(r['ok'] for r in rows),
        final_cases=proof,
        dependency_readbacks_equal=audit['dependencies_equal'],
        final_OA_exports_equal=audit['final_exports_equal'],va_remote_hashes=audit['va'],
        canvas={k:{'document_name':canvas[k]['snap']['documentName'],
            'revision':canvas[k]['vr']['revision'],'errors':canvas[k]['vr']['errors'],
            'warnings':canvas[k]['vr']['warnings'],'topology':canvas[k]['vr']['comparison']['status']} for k in ['top','leaf']},
        original_canvas_revision=canvas['original']['revision'],
        limits=['no complete native static or FFT acceptance','no PVT/noise/mismatch/layout qualification',
                'fixed-period controller is only a characterization fixture, not the selected asynchronous SAR implementation'])
    p=ROOT/'docs/figures/cdac8_dualrail/metrics.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print('CURATED',summary['completed_final_runs'],'final accepted-by-simulator runs; design stress gate FAILED')


if __name__=='__main__':main()
