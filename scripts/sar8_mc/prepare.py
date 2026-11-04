"""Freeze B key-code Monte Carlo inputs; never launch or edit the frozen DUT."""
import hashlib,json,re
from pathlib import Path

R=Path(__file__).resolve().parents[2]
V=R/'verification/sar8_mc'
EXPECTED='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')

def main():
    source=json.loads((R/'management/recipes/sar8camp-b-mm-bench-v1.yaml').read_text())
    assert sha(R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs')==EXPECTED
    cases=[('nominal',None)]+[('s%d'%s,s) for s in range(3101,3131)]+[('s3101-repeat',3101)]
    manifest={'seeds':list(range(3101,3131)),'pilot_seeds':[3101,3102,3103],
        'source_run':'sar8camp-b-mm-bench-v1','dut_sha256':EXPECTED,'runs':{},
        'inspector_commit':'164dbe66391b580fe28ff73ad9fd07824644f934',
        'scope':'TT local mismatch only; ten key-code frames, not full static/yield/FFT/electrical qualification',
        'mom_representation':'Original multi retained: model includes inverse sqrt(total capacitance) mismatch scaling; no geometry/topology change'}
    for tag,seed in cases:
        run='sar8mc-b-tt-'+tag+'-v1';dest=V/run;dest.mkdir(parents=True,exist_ok=False)
        rec=json.loads(json.dumps(source));inputs=[]
        for row in source['inputs']:
            src=R/row['source'];assert sha(src)==row['sha256'],row['name']
            name=row['name'];target=src
            if name=='test.scs':
                text=src.read_text()
                for old,new in [('ttmacro_mos_moscap','TTGlobalCorner_LocalMC_MOS_MOSCAP'),('tt_mom','TTGlobalCorner_LocalMC_MOM'),('tt_res_bip_dio_disres','TTGlobalCorner_LocalMC_RES_BIP_DIO_DISRES'),('tt_ind_jvar','TTGlobalCorner_LocalMC_IND_JVAR')]:
                    assert text.count('section='+old)==1
                    text=text.replace('section='+old,'section='+new)
                if seed is not None:
                    child=re.search(r'(?m)^tran_ab tran .+$',text).group()
                    mc='mc montecarlo numruns=1 seed=%d variations=mismatch sampling=standard donominal=no savemismatchparams=yes mismatchparamfile="mismatch.params" mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n%s\n}'%(seed,child)
                    text=text.replace(child,mc)
                target=dest/name;target.write_text(text)
            elif name=='context.json':
                c=json.loads(src.read_text());c.update(run_id=run,kind='local_mismatch_key_code',seed=seed,mismatch=seed is not None,
                    statistical_sections=True,process_variation=False,nominal_code_is_reference_not_random_oracle=True,
                    parent_dut_sha256=EXPECTED,original_nominal_source=source['run_id'])
                target=dest/name;write(target,c);rec['test_conditions']=c
            elif name=='reduce.py':
                name='reduce_mc.py';target=R/'scripts/sar8_mc/reduce.py'
            inputs.append({'source':target.relative_to(R).as_posix(),'name':name,'sha256':sha(target)})
        base=R/'scripts/sar8_ab_phase60/reduce.py'
        inputs.append({'source':base.relative_to(R).as_posix(),'name':'baseline_reduce.py','sha256':sha(base)})
        rec.update(run_id=run,inputs=inputs,analyzer='reduce_mc.py',qualification_scope=manifest['scope'])
        rec['resources'].update(max_output_mib=1536,simulation_wall_seconds=21600,analysis_wall_seconds=1200)
        write(R/'management/recipes'/(run+'.yaml'),rec)
        manifest['runs'][tag]={'run_id':run,'seed':seed}
    write(V/'manifest.json',manifest)
    print('Prepared',len(cases),'immutable cases; DUT unchanged')

if __name__=='__main__':main()
