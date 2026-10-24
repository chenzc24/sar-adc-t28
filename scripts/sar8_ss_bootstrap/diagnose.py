"""Extract original windows and characterize the frozen Mmain, without changing ADC circuits."""
from pathlib import Path
import json
import contextlib
import re
import shlex
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_pvt_mismatch'))
import flow as previous
OUT=ROOT/'output/sar8_ss_bootstrap'
REMOTE='/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ss_bootstrap_20261024'
NAMES=['tt_090_27_static','ss_081_m40_static','ss_081_125_static']
def start():
    OUT.mkdir(exist_ok=True)
    ssh=previous.base.client()
    previous.base.command(ssh,'mkdir '+shlex.quote(REMOTE))
    r=ssh.upload(ROOT/'scripts/sar8_ss_bootstrap/extract_remote.py',REMOTE+'/extract.py',timeout=60)
    assert r.returncode==0,r.stderr
    for name in NAMES:
        src=previous.REMOTE+'/'+name
        assert previous.base.command(ssh,'cat '+shlex.quote(src+'/exit_code')).strip()=='0'
        cmd='python '+shlex.quote(REMOTE+'/extract.py')+' '+shlex.quote(src)+' '+shlex.quote(REMOTE+'/'+name+'.json.gz')
        cmd+=' > '+shlex.quote(REMOTE+'/'+name+'.log')+' 2>&1; echo $? > '+shlex.quote(REMOTE+'/'+name+'.exit')
        print(previous.base.command(ssh,'nohup sh -c '+shlex.quote(cmd)+' > /dev/null 2>&1 < /dev/null & echo $!'))
def collect():
    ssh=previous.base.client()
    for name in NAMES:
        state=previous.base.command(ssh,'if test -f '+shlex.quote(REMOTE+'/'+name+'.exit')+'; then cat '+shlex.quote(REMOTE+'/'+name+'.exit')+'; else echo pending; fi').strip()
        if state=='pending':print('Extraction still running:',name);return
        assert state=='0',name
    for name in NAMES:
        print(name,previous.base.command(ssh,'cat '+shlex.quote(REMOTE+'/'+name+'.exit')+'; tail -2 '+shlex.quote(REMOTE+'/'+name+'.log')))
        assert previous.base.command(ssh,'cat '+shlex.quote(REMOTE+'/'+name+'.exit')).strip()=='0'
        dst=OUT/(name+'.json.gz');assert not dst.exists()
        r=ssh.download(REMOTE+'/'+name+'.json.gz',dst,timeout=60);assert r.returncode==0,r.stderr
    previous.dump(OUT/'receipt.json',dict(remote=REMOTE,files={n:previous.sha(OUT/(n+'.json.gz')) for n in NAMES},
        extractor_sha256=previous.sha(ROOT/'scripts/sar8_ss_bootstrap/extract_remote.py')))
DCNAMES=['iv_tt_27','iv_ss_m40','iv_ss_125']
def dc_start():
    dut,_=previous.idle.candidate()
    cell=previous.base.cells(dut)['sar_bootstrap_flat_8b_p']
    flat=re.sub(r'\\\n\s*',' ',cell)
    device=re.search(r'(?m)^\s*Mmain \([^\n]+$',flat)[0]
    params=device[device.index('nch_18_mac'):]
    header=(ROOT/'netlist/sar8_physical/tt_nominal.scs').read_text().split('include "dut.scs"')[0]
    previous.base.OUT=OUT;previous.base.REMOTE=REMOTE
    for name,corner,temp in zip(DCNAMES,['tt','ss','ss'],[27,-40,125]):
        folder=OUT/name;assert not folder.exists();folder.mkdir()
        text=header.replace('ttmacro_mos_moscap',corner+'macro_mos_moscap')
        text+='\nparameters VGSVAR=0.8\nVVDD (VDD! 0) vsource dc=0.9\nVS (S 0) vsource dc=0.045\nVG (G 0) vsource dc=0.045+VGSVAR\n'
        for i,vds in enumerate([.1,.4,.75]):
            text+=f'VD{i} (D{i} 0) vsource dc={.045+vds}\nM{i} (D{i} G S 0) {params}\n'
        text+=f'opts options temp={temp} tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13\nsaveOptions options save=selected\ndc_iv dc param=VGSVAR start=0.75 stop=1.05 step=0.01\nsave G S VD0:p VD1:p VD2:p\n'
        (folder/'test.scs').write_text(text)
        (folder/'r4_perf_monitor.va').write_bytes((previous.base.prior.SOURCE/'r4_perf_monitor.va').read_bytes())
        previous.dump(folder/'context.json',dict(name=name,corner=corner,temp_c=temp,source_v=.045,vds_v=[.1,.4,.75],
            main_device=params,DUT_source_sha256=previous.idle.EXPECTED,deck_sha256=previous.sha(folder/'test.scs'),
            spectre_args=['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],scope='Isolated frozen Mmain DC diagnostic, not changed ADC'))
    with (OUT/'dc_dispatch.log').open('x') as f,contextlib.redirect_stdout(f):previous.base.launch(DCNAMES)
    print('DC diagnostic submitted',DCNAMES)
def dc_collect():
    ssh=previous.base.client()
    for name in DCNAMES:
        src=REMOTE+'/'+name
        assert previous.base.command(ssh,'cat '+shlex.quote(src+'/exit_code')).strip()=='0'
        dest=OUT/name/'native';assert not dest.exists();dest.mkdir()
        with (OUT/name/'collect.log').open('w') as f,contextlib.redirect_stdout(f):
            for fn,recursive in [('spectre.out',False),('test.raw',True)]:
                r=ssh.download(src+'/'+fn,dest/fn,recursive=recursive,timeout=60);assert r.returncode==0,r.stderr
        print('DC collected',name)
def proof():
    ssh=previous.base.client()
    paths=[REMOTE+'/'+n+'/test.scs' for n in DCNAMES]
    hashes=previous.base.command(ssh,'sha256sum '+' '.join(shlex.quote(p) for p in paths))
    remote={line.split(None,1)[1].strip():line.split()[0] for line in hashes.splitlines()}
    for n,p in zip(DCNAMES,paths):assert remote[p]==previous.sha(OUT/n/'test.scs')==previous.read(OUT/n/'context.json')['deck_sha256']
    result=dict(remote_deck_sha256=remote,local_match=True,ADC_DUT_sha256=previous.idle.EXPECTED,
        native_exit={n:previous.base.command(ssh,'cat '+shlex.quote(REMOTE+'/'+n+'/exit_code')).strip() for n in DCNAMES},
        remote_bytes=int(previous.base.command(ssh,'du -sb '+shlex.quote(REMOTE)).split()[0]),
        local_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
        OA_changed=False,PDK_changed=False,ADC_changed=False,
        original_model_audit='verification/sar8_pvt_mismatch/audit.json')
    assert all(v=='0' for v in result['native_exit'].values())
    previous.idle.candidate()  # recheck frozen source identity
    previous.dump(ROOT/'verification/sar8_ss_bootstrap/provenance.json',result)
    print('Proof:',result)
if __name__=='__main__':
    {'start':start,'collect':collect,'dc_start':dc_start,'dc_collect':dc_collect,'proof':proof}[sys.argv[1]]()
