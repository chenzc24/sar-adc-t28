"""Resume only the completed MSB4600 waveform transfer, never run a simulator."""
import contextlib
import gzip
import shlex
import shutil
from flow import OUT,read,dump,sha,client,command,process_local


def recover():
    name='msb_4600';folder=OUT/name;dest=folder/'spectre';remote=read(folder/'launch.json')['remote']
    assert not (folder/'result.json').exists()
    ssh=client();assert command(ssh,'cat '+shlex.quote(remote+'/exit_code')).strip()=='0'
    manifest=folder/'recovery_manifest.json';parts=remote+'/transfer_parts_v1';local=dest/'parts_v1';local.mkdir(exist_ok=True)
    with (folder/'recovery_transfer.log').open('a') as log,contextlib.redirect_stdout(log):
        if not manifest.exists():
            # Completed manifest is a transaction marker; partial creation requires inspection.
            command(ssh,'test ! -e '+shlex.quote(parts)+' && mkdir '+shlex.quote(parts)+' && split -b 268435456 -d -a 3 '+shlex.quote(remote+'/transfer_tran.gz')+' '+shlex.quote(parts+'/part_'),timeout=300)
            listing=command(ssh,'cd '+shlex.quote(parts)+' && sha256sum part_*',timeout=120)
            rows=[dict(sha256=line.split()[0],name=line.split()[1]) for line in listing.splitlines()]
            assert rows and all(r['name']==f'part_{i:03d}' for i,r in enumerate(rows))
            compressed_hash=command(ssh,'sha256sum '+shlex.quote(remote+'/transfer_tran.gz'),timeout=120).split()[0]
            native_hash=command(ssh,'sha256sum '+shlex.quote(remote+'/test.raw/tran_perf.tran.tran'),timeout=180).split()[0]
            dump(manifest,dict(parts=rows,compressed_sha256=compressed_hash,native_sha256=native_hash,
                reason='Original large-file SCP timed out during anomalous wall-clock wait; native exit0 preserved.',native_rerun=False))
    m=read(manifest)
    for i,row in enumerate(m['parts']):
        target=local/row['name']
        if target.exists():assert sha(target)==row['sha256']
        else:
            with (folder/'recovery_transfer.log').open('a') as log,contextlib.redirect_stdout(log):
                r=ssh.download(parts+'/'+row['name'],target,timeout=300);assert r.returncode==0,r.stderr
            assert sha(target)==row['sha256']
        print('CHUNK_VERIFIED',i+1,'/',len(m['parts']),flush=True)
    archive=dest/'recovered_transfer.gz'
    if not archive.exists():
        with archive.open('xb') as target:
            for row in m['parts']:
                with (local/row['name']).open('rb') as src:shutil.copyfileobj(src,target,1024*1024)
    assert sha(archive)==m['compressed_sha256']
    psf=dest/'test.raw/tran_perf.tran.tran'
    if not psf.exists():
        with gzip.open(archive,'rb') as src,psf.open('xb') as target:shutil.copyfileobj(src,target,1024*1024)
    assert sha(psf)==m['native_sha256']
    dump(folder/'transfer.json',dict(remote_native_sha256=m['native_sha256'],local_uncompressed_match=True,
         recovery='Verified 256MiB parts of the existing gzip copy; original native files unchanged.'))
    process_local(name,0)


if __name__=='__main__':recover()
