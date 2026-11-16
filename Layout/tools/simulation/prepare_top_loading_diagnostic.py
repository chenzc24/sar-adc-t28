"""One-variable causal diagnostic: restore TOP fixed-node loading to prefill.

This edits a new, explicitly synthetic simulation package, never OA or native
extraction evidence. All R, MOM/MOS, bottom-plate coupling and stimuli stay exact.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

from Layout.tools.analysis.analyze_top_loading import INSTANCE, parameter, predict

ROOT=Path(__file__).resolve().parents[3]
SOURCE='cdac-full-tt-filled-hold-v1'
FIXED=('0','VSS','VDD','VREFP','VREFN')


def sha(blob):return hashlib.sha256(blob).hexdigest()


def blocks(text):
    part=[]
    for line in text.splitlines(keepends=True):
        part.append(line)
        if line.rstrip().endswith('\\'):continue
        yield ''.join(part)
        part=[]
    assert not part


def label(node):
    for n in ('TOPP','TOPN')+FIXED:
        if node==n or node.startswith('N_'+n+'_'):return n
    return None


def main():
    p=argparse.ArgumentParser();p.add_argument('run_id');a=p.parse_args()
    assert re.fullmatch(r'[a-z][a-z0-9-]{1,55}',a.run_id)
    dest=ROOT/'work/layout'/a.run_id
    assert not dest.exists(), 'Do not reuse an execution identity'
    audit_path=ROOT/'work/output/managed_execution/runs/cdac-top-loading-audit-v2/collected/derived/result.json'
    audit=json.loads(audit_path.read_text())
    pre,filled=[audit['cases'][k] for k in ['prefill','filled']]
    base=ROOT/'work/layout'/SOURCE
    recipe=json.loads((base/'recipe.json').read_text())
    payload={}
    for row in recipe['inputs']:
        blob=(ROOT/row['source']).read_bytes()
        assert sha(blob)==row['sha256']
        payload[row['name']]=blob
    assert filled['source_run_id']==SOURCE
    for name,digest in filled['files_sha256'].items():assert sha(payload[name])==digest
    ratios={};changes={};counterfactual=copy.deepcopy(filled)
    for side in ('TOPP','TOPN'):
        f=filled['top'][side];b=pre['top'][side]
        before=b['ground_f']+sum(b['coupling_f'].get(n,0) for n in FIXED if n!='0')
        after=f['ground_f']+sum(f['coupling_f'].get(n,0) for n in FIXED if n!='0')
        ratios[side]=before/after
        changes[side]=dict(original_f=after,target_f=before,scale=ratios[side],removed_f=0.0,elements=0)
        counterfactual['top'][side]['total_attached_parasitic_f']-=after-before
    modified=[]
    for name in ['extracted.scs.pex','extracted.scs.sar8j_r1_cdac.pxi','extracted.scs']:
        result=[];network=None;count=0
        for block in blocks(payload[name].decode('ascii')):
            flat=re.sub(r'\\\s*\n\s*',' ',block).strip()
            if flat.startswith('subckt '):network=flat.split()[1].split('\\%')[-1]
            if flat.startswith('ends '):network=None
            m=INSTANCE.match(flat)
            side=None
            if m and m.group(3)=='capacitor':
                nodes=m.group(2).split()
                if name.endswith('.pex'):
                    if network in ratios and '0' in nodes:side=network
                else:
                    n1,n2=map(label,nodes)
                    if n1 in ratios and n2 in FIXED:side=n1
                    elif n2 in ratios and n1 in FIXED:side=n2
                if side:
                    old=parameter(m.group(4),'c');new=old*ratios[side]
                    # xRC may continue between "capacitor" and "c=". Change
                    # only the parameter token, preserving all original lines.
                    block,n=re.subn(r'(\bc=)\S+',lambda x:x[1]+format(new,'.16g'),block)
                    assert n==1
                    changes[side]['removed_f']+=old-new;changes[side]['elements']+=1;count+=1
            result.append(block)
        blob=''.join(result).encode('ascii')
        if count:
            modified.append(dict(name=name,elements=count,before_sha256=sha(payload[name]),after_sha256=sha(blob)))
            payload[name]=blob
        else:assert blob==payload[name]
    assert {x['name'] for x in modified}=={'extracted.scs.pex','extracted.scs.sar8j_r1_cdac.pxi'}
    for c in changes.values():assert abs(c['removed_f']-(c['original_f']-c['target_f']))<1e-23
    context=json.loads(payload['context.json'])
    scope=('SYNTHETIC CAUSAL DIAGNOSTIC ONLY: filled native CDAC with only TOP-to-fixed-node parasitic capacitors '
           'scaled so each TOP fixed load equals the prefill sum; all R, native devices, TOP-bottom coupling and '
           '260ns TT stimuli unchanged. Not a physical layout, not DRC-qualified, not a candidate baseline.')
    context.update(scope=scope,synthetic_diagnostic=True,diagnostic_source_run_id=SOURCE,
                   loading_audit_sha256=sha(audit_path.read_bytes()),changes=changes,modified_extraction_files=modified,
                   predicted_counterfactual=predict(counterfactual,filled['predicted']['unit_capacitance_f']))
    payload['context.json']=(json.dumps(context,indent=2)+'\n').encode()
    dest.mkdir()
    for name,blob in payload.items():(dest/name).write_bytes(blob)
    recipe.update(run_id=a.run_id,design_id='sar8_cdac_top_load_diagnostic',qualification_scope=scope,
                  test_conditions=context,
                  inputs=[dict(name=n,source=(dest/n).relative_to(ROOT).as_posix(),sha256=sha(b)) for n,b in payload.items()])
    (dest/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print(json.dumps(dict(recipe=(dest/'recipe.json').relative_to(ROOT).as_posix(),changes=changes,
                         predicted_gain=context['predicted_counterfactual']['gain_ratio']),indent=2))


if __name__=='__main__':main()
