"""Read-only circuit diagnosis through added native terminal-current saves."""
from pathlib import Path
import contextlib
import re
import shlex
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_main_width'))
import width_flow as wf
OUT=ROOT/'output/sar8_ref_load';VERIFY=ROOT/'verification/sar8_ref_load'
REMOTE='/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ref_load_20261024'
SOURCE=ROOT/'output/sar8_main_width/w2_ff_099_125_static'
wf.OUT=wf.base.OUT=OUT;wf.VERIFY=VERIFY;wf.REMOTE=wf.base.REMOTE=REMOTE
read,dump,sha=wf.read,wf.dump,wf.sha
NAMES=['branches_ffhot','branches_ffcold']

def prepare():
    OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)
    ctx0=read(SOURCE/'context.json');original=(SOURCE/'test.scs').read_text()
    dut=(SOURCE/'dut.scs').read_text()
    assert sha(SOURCE/'test.scs')==ctx0['deck_sha256']
    assert sha(SOURCE/'dut.scs')==ctx0['DUT_sha256']
    saves=['VREFP','VREFN','VDD!','XDUT.TOPP','XDUT.TOPN','XDUT.CMP_CLK','XDUT.SEQ_SAMPLE',
           'VREFHIGH:p','VREFLOW:p','CREFP:currents','CREFN:currents',
           'XDUT.XCDAC.CMOMP8:currents','XDUT.XCDAC.CMOMN8:currents']
    for side in ['P','N']:
        for b in range(8):
            saves += [f'XDUT.XCDAC.XS{side}{b}.{mos}:currents' for mos in ['MP_HIGH','MN_LOW']]
            saves += [f'XDUT.G{side}{pol}{b}' for pol in ['N','P']]
            saves += [f'XDUT.XCDAC.B{side}{b}',f'XDUT.XCDAC.CMOM{side}{b}:currents']
    for name,temp in zip(NAMES,[125,-40]):
        folder=OUT/name;assert not folder.exists();folder.mkdir()
        text=original.replace('stop=600n','stop=180n').replace('outputstart=0n','outputstart=120n')
        text=text.replace('temp=125 tnom=27',f'temp={temp} tnom=27')
        text,n=re.subn(r'(?m)^save .+$','save '+' '.join(saves),text);assert n==1
        assert dut in text
        (folder/'test.scs').write_text(text)
        (folder/'r4_perf_monitor.va').write_bytes((SOURCE/'r4_perf_monitor.va').read_bytes())
        dump(folder/'context.json',dict(name=name,temperature_c=temp,corner='ff',vdd=.99,
             source_deck_sha256=ctx0['deck_sha256'],DUT_sha256=ctx0['DUT_sha256'],
             deck_sha256=sha(folder/'test.scs'),spectre_args=ctx0['spectre_args'],
             stop_ns=180,outputstart_ns=120,save_requests=saves,OA_changed=False,
             scope='Unchanged integrated DUT; probe-only terminal currents, not full-frame validation'))
        dump(VERIFY/(name+'_setup.json'),read(folder/'context.json'))

def collect(names):
    ssh=wf.base.client()
    for name in names:
        folder=OUT/name;remote=read(folder/'launch.json')['remote']
        assert wf.base.command(ssh,'cat '+shlex.quote(remote+'/exit_code')).strip()=='0'
        target=folder/'native';assert not target.exists();target.mkdir()
        for fn,rec in [('spectre.out',False),('test.raw',True)]:
            r=ssh.download(remote+'/'+fn,target/fn,recursive=rec,timeout=120);assert r.returncode==0,r.stderr
        remotehash=wf.base.command(ssh,'sha256sum '+shlex.quote(remote+'/test.scs')).split()[0]
        assert remotehash==sha(folder/'test.scs')
        dump(folder/'receipt.json',dict(native_exit=0,remote_deck_sha256=remotehash,
             native_files={p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file()}))

if __name__=='__main__':
    action=sys.argv[1];names=sys.argv[2:] or NAMES
    if action=='prepare':prepare()
    elif action in ['preflight','status']:getattr(wf,action)()
    else:
        with (OUT/(action+'.log')).open('a') as log,contextlib.redirect_stdout(log):
            if action=='launch':wf.launch(names)
            elif action=='collect':collect(names)
            else:raise ValueError(action)
        print(action,names)
