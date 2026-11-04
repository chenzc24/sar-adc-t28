"""Unique delayed-start M0 width cases; historical sources remain immutable."""
import hashlib
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OLD = R/'verification/manual_adc/bootstrap_short_v1'
OUT = R/'verification/manual_adc/bootstrap_width_v1'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def shift_step(match):
    tokens = match.group(1).split()
    for i in range(0, len(tokens), 2):
        value = float(tokens[i][:-1])
        if value >= 100:
            tokens[i] = '%.12gn' % (value+100)
    if tokens[0:1] == ['0n'] and len(tokens)>2 and tokens[2] != '1n':
        tokens[0:2] = ['0n', '0', '1n', tokens[1]]
    return 'wave=['+' '.join(tokens)+']'


def main():
    manifest = []
    for case, width in [('startup',4)]+[(c,w) for w in [4,6,8] for c in ['dc','sine']]:
        run = 'manual8-bootwidth-%s-m%d-v1' % (case,width)
        target = OUT/('%s_m%d' % (case,width))
        src = OLD/case
        cfg = json.loads((src/'measure.json').read_text())
        cfg.update(startup_shift_s=100e-9, M0_total_width_um=width,
                   sample_close0_s=149.975e-9, sample_open0_s=110.025e-9,
                   stop_s=cfg['stop_s']+100e-9)
        for file in src.iterdir():
            if file.suffix not in ['.va','.scs']: continue
            text = file.read_text()
            if file.name in ['test.scs','wrappers_hybrid.scs']:
                text = text.replace('main_mult=4', 'main_mult=%d'%width)
            if file.name == 'test.scs':
                assert text.count('delay=10n') == 2
                text = text.replace('delay=10n','delay=110n')
                for source,node in [('VVDD','VDD'),('VVDDH','VDDH'),('VREF','REF')]:
                    text = text.replace('%s (%s 0) vsource dc=.9'%(source,node),
                                        '%s (%s 0) vsource type=pwl wave=[0 0 1n .9]'%(source,node))
                if case != 'sine':
                    lines = text.splitlines(True)
                    for i,line in enumerate(lines):
                        if line.startswith(('VINP ','VINN ')):
                            lines[i] = re.sub(r'wave=\[([^]]+)\]',shift_step,line)
                    text = ''.join(lines)
                text = re.sub(r'tran_test tran stop=\S+', 'tran_test tran stop=%.14g'%cfg['stop_s'], text)
            write(target/file.name,text)
        write(target/'measure.json',json.dumps(cfg,indent=2)+'\n')
        old_recipe = json.loads((R/('management/recipes/manual8-bootshort-%s-v1.yaml'%case)).read_text())
        old_recipe.update(run_id=run,design_id='manual8_bootstrap_width_d110_v1',
                          analyzer='bootstrap_width_reduce.py',expected_stop_s=cfg['stop_s'],
                          qualification_scope='Delayed-start bootstrap M0-only width comparison; other modules behavioral; no PVT/FFT/OA adoption')
        old_recipe['test_conditions'].update(startup_supply_ramp_s=1e-9,first_clock_delay_s=110e-9,M0_total_width_um=width)
        inputs=[{'source':f.relative_to(R).as_posix(),'name':f.name} for f in sorted(target.iterdir()) if f.suffix in ['.va','.scs','.json']]
        inputs += [{'source':'scripts/manual_adc/bootstrap_width_reduce.py','name':'bootstrap_width_reduce.py'},
                   {'source':'scripts/manual_adc/reduce.py','name':'reduce.py'}]
        old_recipe['inputs']=inputs
        write(R/('management/recipes/'+run+'.yaml'),json.dumps(old_recipe,indent=2)+'\n')
        manifest.append({'run_id':run,'case':case,'width_um':width,'directory':target.relative_to(R).as_posix(),
                         'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in target.iterdir()}})
    # With timing fixed, M0 instance multiplicity is the sole electrical difference.
    for case in ['dc','sine']:
        for width in [6,8]:
            for f in (OUT/(case+'_m4')).glob('*'):
                if f.suffix not in ['.va','.scs']:continue
                assert f.read_text() == (OUT/('%s_m%d'%(case,width))/f.name).read_text().replace('main_mult=%d'%width,'main_mult=4'), f
    write(OUT/'manifest.json',json.dumps({'runs':manifest,'single_variable_check_pass':True},indent=2)+'\n')
    print('\n'.join(x['run_id'] for x in manifest))


if __name__=='__main__':main()
