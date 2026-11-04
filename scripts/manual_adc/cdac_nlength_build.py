"""Length-only reference NMOS candidates; source and PDK remain read-only."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_nlength_v1'
S=R/'verification/manual_adc/cdac_leak_ffhot_v1'
SOURCE='manual8-cdac-leak-ffhot-v1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def audit():
    # Remote read-only model metadata. Never export model contents.
    program=r'''
import re,json,hashlib,socket,os
p='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/cln28ull_1d8_elk_v1d8_3.scs'
s=open(p).read();start=s.index('inline subckt nch_mac ');end=s.index('.model nch.global',start);block=s[start:end]
lengths=[float(v)*1000 for v in re.findall(r'lrdr\d+=([\d.]+)',re.search(r'(?m)^\.param lrdr1=.*',block).group(0))]
assert all(x in lengths for x in [30,60,90])
assert ".param l0='l*factor*1e6'" in block
assert ".param ll='(l+dl)*min(2*lf,1)'" in block
# Return the limited geometry mapping needed to distinguish total/per-finger W.
mapping=re.findall(r"\b(w0|ww|wf|factor|nf)\s*=\s*('[^']*'|[^\s]+)",block)
bins=[]
for m in re.finditer(r'\.model nch\.(\d+) nmos \(\s*lmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+lmax\s*=\s*\x27?([\deE.+-]+)\x27?\s*\+wmin\s*=\s*\x27?([\deE.+-]+)\x27?\s+wmax\s*=\s*\x27?([\deE.+-]+)',s):
 idx=int(m.group(1));a,b,c,d=map(float,m.groups()[1:])
 for width in [100.,1000.]:
  for L in [30,60,90]:
   if a-1e-15<=L*.9e-9<=b+1e-15 and c-1e-15<=width*.9e-9<=d+1e-15:
    bins.append(dict(L_nm=L,width_unscaled_nm=width,model_bin=idx,length_scaled_range_nm=[a*1e9,b*1e9],width_scaled_range_nm=[c*1e9,d*1e9]))
print(json.dumps(dict(host=socket.gethostname(),uid=os.getuid(),path=p,sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),listed_short_lengths_nm=lengths,geometry_mapping=mapping,matched_bins=bins)))
'''
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei','python -'],input=program,text=True,capture_output=True,timeout=45)
    if r.returncode:raise RuntimeError(r.stderr)
    data=json.loads(r.stdout)
    assert data['uid']==596
    assert ['w0',"'w/nf*factor*1e6'"] in data.pop('geometry_mapping')
    data['geometry']={'netlist_w_nm':1000,'nf':10,'width_per_finger_nm':100,'shrink_factor':0.9,'model_width_nm':90}
    data['matched_bins']=[b for b in data['matched_bins'] if b['width_unscaled_nm']==100]
    assert {b['L_nm'] for b in data['matched_bins']}=={30,60,90}
    data['model_domain_pass']=True
    data['scope']='Model range/length metadata only; frozen diffusion/LDE parameters. Not PCell or physical DRC certification.'
    (B/'legality.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))

def build():
    assert (B/'legality.json').exists()
    manifest={'baseline_run':SOURCE,'baseline_reused':True,'cases':[]}
    for length in [60,90]:
        folder=B/('l'+str(length));folder.mkdir(exist_ok=False)
        run='manual8-cdac-nl%d-ffhot-v1'%length
        recipe=json.loads((R/'management/recipes'/(SOURCE+'.yaml')).read_text())
        for item in recipe['inputs']:
            if item['source'].startswith('verification/manual_adc/'):
                name=item['name'];(folder/name).write_bytes((S/name).read_bytes())
                item['source']=(folder/name).relative_to(R).as_posix()
        core=(folder/'cdac_core.scs').read_text()
        changed,n=re.subn(r'(\bnch_mac l=)30n\b',r'\g<1>%dn'%length,core)
        assert n==7
        assert changed.replace('nch_mac l=%dn'%length,'nch_mac l=30n')==core
        # Correct provenance comment without changing electrical content.
        # Retain the original source comment verbatim to keep L-only byte diff.
        (folder/'cdac_core.scs').write_text(changed)
        cfg=json.loads((folder/'measure.json').read_text())
        cfg['leakage'].update(run_id=run,source_run_id=SOURCE,scope='All reference NMOS L-only sweep; all other parameters/stimuli fixed')
        cfg['experiment']['reference_nmos_length_nm']=length
        (folder/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
        recipe.update(run_id=run,design_id='manual8_cdac_nlength_v1')
        recipe['test_conditions'].update(measurement_only=False,reference_nmos_length_nm=length,baseline_run=SOURCE)
        recipe['test_conditions']['single_variable']['reference_nmos_length_nm']=length
        (R/'management/recipes'/(run+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
        identical={p.name:sha(p)==sha(S/p.name) for p in folder.iterdir() if p.name not in ['cdac_core.scs','measure.json']}
        assert all(identical.values())
        manifest['cases'].append(dict(length_nm=length,run_id=run,nmos_definitions_changed=n,nmos_instances_changed=14,other_files_identical=identical,files={p.name:sha(p) for p in folder.iterdir()}))
    (B/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared L60/L90; L30 reused; exact electrical diff is seven L tokens.')

if __name__=='__main__':
    import sys
    B.mkdir(exist_ok=True)
    {'audit':audit,'build':build}[sys.argv[1]]()
