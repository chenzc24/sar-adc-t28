"""Current-design global+local MC: three voltage/temperature groups, 12 draws each."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from . import reference_short

ROOT = Path(__file__).resolve().parents[2]
CODES = [0,255,1,254,2,12,63,64,127,128]
GROUPS = {'nom27': (.90,27,15101), 'lowm40': (.81,-40,15201), 'highm40': (.99,-40,15301)}
SECTIONS = {'ttmacro_mos_moscap':'GlobalMC_LocalMC_MOS_MOSCAP',
            'tt_mom':'GlobalMC_LocalMC_MOM',
            'tt_res_bip_dio_disres':'GlobalMC_LocalMC_RES_BIP_DIO_DISRES'}


def prepare(group, seed, revision='v1'):
    supply,temp,first = GROUPS[group]
    assert first <= seed < first+12
    adopted, original_sources = reference_short.resetor_20261115_sources()
    # Keep the ten-frame global/local campaign bound to its dated reset-OR sources.
    base = ROOT/reference_short.prepare('current',group,'mc-template-'+revision,
        condition=dict(mos='TT',vdd_v=supply,temperature_c=temp),codes=CODES,max_output_mib=3072,
        source_blobs=original_sources)
    old = json.loads(base.read_text())
    blobs = {r['name']:(ROOT/r['source']).read_bytes() for r in old['inputs']}
    assert all(hashlib.sha256(blobs[k]).hexdigest()==v for k,v in adopted['source_sha256'].items())
    rid = 'sar8-resetor-mcgl-%s-s%d-%s' % (group,seed,revision)
    test = blobs['test.scs'].decode()
    for old_section,new in SECTIONS.items():
        assert test.count('section='+old_section)==1
        test = test.replace('section='+old_section, 'section='+new)
    mc = ('mc montecarlo numruns=1 seed=%d variations=all dut=[XDUT] sampling=standard donominal=no '
          'saveprocessparams=yes processparamfile="process.params" processscalarfile="process.values" '
          'savemismatchparams=yes mismatchparamfile="mismatch.params" mismatchscalarfile="mismatch.values" '
          'savefamilyplots=yes savedatainseparatedir=yes {\n') % seed
    test,n = re.subn(r'(?m)^(tran_short tran .*)$', lambda m:mc+m.group(1)+'\n}',test)
    assert n==1 and 'CAP_CLK' not in test and 'variations=mismatch' not in test
    blobs['test.scs'] = test.encode()
    blobs['mc_short_reduce.py'] = (ROOT/'tools/saradc/measure/mc_short_reduce.py').read_bytes()
    ctx = json.loads(blobs['context.json'])
    ctx.update(run_id=rid,design_id=adopted['design_id'],group=group,seed=seed,pilot=seed<first+2,
               mos='statistical_global',mismatch=True,process_variation=True,statistical_mode='all',
               mismatch_scope='All modeled devices under XDUT; ideal external sources/R/C remain deterministic',
               statistical_sections=list(SECTIONS.values()),passive_sections=['tt_ind_jvar','tt_r_metal'],
               nominal_codes_are_timing_stimuli_not_accuracy_oracle=True,
               settling_scope='Conservative sum of per-side maximum rail residuals, independent of positive capacitor weights; excludes top-node kickback and reference absolute error')
    ctx['source_hashes']={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items() if k!='context.json'}
    blobs['context.json']=(json.dumps(ctx,indent=2)+'\n').encode()
    dest=ROOT/'work/decks'/rid
    recipe=dict(old,run_id=rid,design_id=adopted['design_id'],analyzer='mc_short_reduce.py',test_conditions=ctx,
                qualification_scope='Ten-frame global+local whole-DUT gross timing screen, not yield/accuracy/noise/PEX or full-terminal qualification')
    recipe['inputs']=[dict(name=k,source=(dest/k).relative_to(ROOT).as_posix(),sha256=hashlib.sha256(v).hexdigest()) for k,v in blobs.items()]
    blobs['recipe.yaml']=(json.dumps(recipe,indent=2)+'\n').encode()
    for k,v in blobs.items():
        p=dest/k
        if p.exists() and p.read_bytes()!=v:raise ValueError('Frozen input collision: '+str(p))
    for k,v in blobs.items():
        p=dest/k;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
    return (dest/'recipe.yaml').relative_to(ROOT).as_posix()


def prepare_batch(revision='v1'):
    rows=[]
    for index in range(12):
        for group,(_,_,first) in GROUPS.items():
            path=prepare(group,first+index,revision)
            recipe=json.loads((ROOT/path).read_text())
            rows.append(dict(run_id=recipe['run_id'],group=group,seed=first+index,pilot=index<2,recipe=path))
    batch=dict(batch_id='sar8-resetor-mcgl36-'+revision,host='thu-song',max_inflight_runs=2,
               groups=list(GROUPS),runs=rows,code_centers=CODES,variation='global_process_and_whole_DUT_local_mismatch',
               protected_fft_run='sar8-resetor-noise-tt-fft1024-s101-v1')
    path=ROOT/'work/mc'/('resetor-global-local-'+revision)/'prepared.json';path.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(batch,indent=2)+'\n'
    if path.exists() and path.read_text()!=data:raise ValueError('Existing batch differs')
    path.write_text(data,encoding='utf-8',newline='\n')
    return path.relative_to(ROOT).as_posix()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',default='v1')
    print(prepare_batch(p.parse_args().revision))
