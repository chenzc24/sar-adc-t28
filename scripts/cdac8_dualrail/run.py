"""Native OA DUTs are immutable; only bench parameters/analysis/saves are wrapped."""
import argparse
import contextlib
import re
from common import ROOT,OUT,dump,sha

def blocks(text):
    return {m[1]:m[0] for m in re.finditer(r'(?ms)^subckt (\w+)\b.*?^ends \1\s*$',text)}

def prepare(name,cell='tb_cdac8_dr_nominal',vdiff=.453515625,stop_ns=300,
            corner='tt',sup=.9,temp=27,mode=0,strobe=False,maxstep='100p',tag='initial'):
    source=OUT/f'oa_netlists/{cell}/{tag}/input.scs'
    text=source.read_text()
    before=blocks(text)
    m=re.search(r'(?m)^parameters ((?:[^\n]*\\\n)*[^\n]*)\n',text);assert m
    keys=m[1].replace('\\\n',' ').split()
    default=dict(MULT_D=1,MULT_R=1,CKB=.05e-15,DEAD_TIME=100e-12,STIM_MODE=mode,
                 VDIFF=vdiff,FIN=10e6*115/256,RREF=50,SUP=sup,CDECAP=4e-12)
    assert set(keys)<=set(default),keys
    values={n:default[n] for n in keys}
    text=text[:m.start()]+'parameters '+' '.join(f'{n}={values[n]:.14g}' for n in keys)+'\n'+text[m.end():]
    text=text.replace('section=ttmacro_mos_moscap',f'section={corner}macro_mos_moscap')
    text=text.replace('temp=27',f'temp={temp}').replace('save=allpub','save=selected')
    text=text.replace('reltol=1e-4','reltol=1e-5').replace('vabstol=1e-6','vabstol=1e-7').replace('iabstol=1e-12','iabstol=1e-13')
    text=re.sub(r'(?m)^\w+ info .*\n','',text)
    assert blocks(text)==before,'DUT/hierarchy must stay byte-identical'
    saved=['TOPP','TOPN','VINP','VINN','VINP_SRC','VINN_SRC','VDD!','VREFP','VREFN','PHI','VALID','BUSY','CMP_CLK','COMP_P','COMP_N']
    saved += [f'DOUT\\<{b}\\>' for b in range(8)]
    if not strobe:
        saved += ['VREFHIGH:p','VREFLOW:p','VVDD:p']
        saved += [f'{side}{q}\\<{b}\\>' for side in 'PN' for q in 'HL' for b in range(8)]
        for side in 'PN':
            saved += [f'XCDAC.B{side}{b}' for b in range(8)]
            saved += [f'XCDAC.XS{side}{b}.{node}' for b in range(8) for node in ['EH_B','EL_B','EL_D']]
        if 'ideal_sample' not in cell: saved += ['XBOOTP.G','XBOOTN.G']
    text+=f'\ntran tran stop={stop_ns:.12g}n maxstep={maxstep} errpreset=conservative'
    if strobe:text+=' strobeperiod=100n strobedelay=93n strobeoutput=strobeonly'
    text+='\nsave '+' '.join(saved)+'\n'
    path=OUT/'decks'/f'{name}.scs';assert not path.exists(),f'Preserve {name}'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    dump(f'cases/{name}.json',dict(cell=cell,parameters=values,source_sha256=sha(source),deck_sha256=sha(path),
        stop_ns=stop_ns,corner=corner,temperature_c=temp,strobe=strobe,oa_tag=tag,scope='exact_OA_DUT_with_bench_analysis_wrapper'))
    return path

def batch(paths,category='runs',workers=2):
    from virtuoso_bridge.spectre import SpectreSimulator
    from virtuoso_bridge.spectre.runner import spectre_mode_args
    sim=SpectreSimulator.from_env(profile='t28_io',work_dir=OUT/'spectre'/category,timeout=7200,
        spectre_args=[*spectre_mode_args('aps'),'+lqtimeout','60'])
    with (OUT/f'{category}_runner.log').open('a',encoding='utf-8') as f:
        with contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
            results=sim.run_parallel([(p,{}) for p in paths],max_workers=workers)
    for path,r in zip(paths,results,strict=True):
        dump(f'{category}/{path.stem}_result.json',dict(ok=r.ok,errors=r.errors,warnings=r.warnings,
            metadata=r.metadata,deck_sha256=sha(path),va_sha256={p.name:sha(p) for p in (ROOT/'models/veriloga').glob('cdac8_dualrail_*.va')}))
        if r.ok:
            dump(f'{category}/{path.stem}_waveform.json',{str(k).strip('"').replace('\\','').lower():v for k,v in r.data.items()})
        print('SPECTRE',path.stem,'OK' if r.ok else str(r.errors)[:800],flush=True)
    assert all(r.ok for r in results),[(p.stem,r.errors) for p,r in zip(paths,results) if not r.ok]

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['quick','smoke','final','evidence','inputs','corners','static','dynamic']);p.add_argument('--tag',default='clean_va');a=p.parse_args()
    if a.action=='final':
        paths=[prepare(f'final_{key}',cell=f'tb_cdac8_dr_{key}',tag=a.tag) for key in ['nominal','literal','strongarm','ideal_sample']]
        paths += [prepare(f'{a.tag}_input_{round(v*1e6):+d}',vdiff=v,tag=a.tag) for v in [-.8,-.4,-.05,-.003515625,0,.003515625,.05,.4,.8]]
        paths += [prepare(f'{a.tag}_static_all_codes',mode=1,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag),
                  prepare(f'{a.tag}_dynamic_256',mode=2,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag)]
    elif a.action=='evidence':
        paths=[prepare(f'{a.tag}_input_{round(v*1e6):+d}',vdiff=v,tag=a.tag) for v in [-.8,-.4,-.05,-.003515625,0,.003515625,.05,.4,.8]]
        paths += [prepare(f'{a.tag}_static_all_codes',mode=1,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag),
                  prepare(f'{a.tag}_dynamic_256',mode=2,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag)]
    elif a.action=='quick':paths=[prepare('quick_nominal',stop_ns=200)]
    elif a.action=='smoke':
        paths=[prepare('smoke_nominal'),prepare('smoke_literal',cell='tb_cdac8_dr_literal'),
               prepare('smoke_strongarm',cell='tb_cdac8_dr_strongarm'),prepare('smoke_ideal_sample',cell='tb_cdac8_dr_ideal_sample')]
    elif a.action=='inputs':paths=[prepare(f'{a.tag}_input_{round(v*1e6):+d}',vdiff=v,tag=a.tag) for v in [-.8,-.4,-.05,-.003515625,0,.003515625,.05,.4,.8]]
    elif a.action=='corners':paths=[prepare(f'{a.tag}_corner_{c}_{round(s*100)}_{t}',corner=c,sup=s,temp=t,vdiff=.8,mode=3,stop_ns=600,tag=a.tag)
                                  for c,s,t in [('ss',.81,-40),('ss',.81,125),('ff',.99,-40),('ff',.99,125)]]
    elif a.action=='static':paths=[prepare(f'{a.tag}_static_all_codes',mode=1,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag)]
    else:paths=[prepare(f'{a.tag}_dynamic_256',mode=2,stop_ns=26020,strobe=True,maxstep='250p',tag=a.tag)]
    batch(paths)

if __name__=='__main__':main()
