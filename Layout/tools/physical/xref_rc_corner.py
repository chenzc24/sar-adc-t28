"""Re-extract a completed coupled XREF/CDAC stream at one foundry interconnect corner (remote, Python 2).

Runs from its own new evidence directory, created by launch_xref_rc_corner.py. It links the GDS and
copies the reference and intent of the completed source run, rebuilds the source PEX job deck with
run_physical.prepare_deck plus the source run's recorded FLATTEN additions, and requires it to equal the
recorded deck. Only the foundry xRC rules include changes (sar_rc_corner.select); supply extraction stays
as in the source. DRC and LVS are inherited from the source. The manifest keeps the run_reference_driver
schema so prepare_reference_driver.fetch_pex binds it.
Usage: python xref_rc_corner.py SOURCE CORNER   (cworst_T | cbest_T)
"""
from __future__ import print_function
import fcntl, json, os, re, shutil, sys, time, traceback

HERE = os.path.dirname(os.path.realpath(__file__))
IDENT = os.path.basename(HERE)
SOURCE, CORNER = sys.argv[1], sys.argv[2]
STATUS = HERE + '/status.json'
RUNTIME = os.path.dirname(os.path.dirname(HERE)) + '/runtime'
FLATTEN = re.compile(r'(?m)^FLATTEN CELL [^\n]+$')


def save(value):
    with open(STATUS + '.next', 'w') as f:
        json.dump(value, f, indent=2, sort_keys=True)
    os.rename(STATUS + '.next', STATUS)


def main(status):
    assert CORNER in ('cworst_T', 'cbest_T')
    sys.path.insert(0, HERE)
    from sar_rc_corner import select
    os.chdir(RUNTIME)
    sys.path.insert(0, RUNTIME)
    import workspace, run_physical as rp
    cfg = workspace.paths()
    src = os.path.join(cfg['evidence'], SOURCE)
    record = json.load(open(src + '/manifest.json'))
    assert record['case'] == 'reference-driver' and record['active_step'] == 'complete' and not record.get('error')
    assert record['checks']['lvs']['verdict'] == 'CORRECT'
    top = record['top']
    with open(cfg['lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        os.symlink(os.path.join('..', SOURCE, 'fixture.gds'), HERE + '/fixture.gds')
        for name in ('reference.cdl', 'intent.json'):
            shutil.copyfile(os.path.join(src, name), os.path.join(HERE, name))
        gds = rp.gds_identity(HERE + '/fixture.gds')
        assert gds['sha256'] == record['gds']['sha256']
        assert rp.sha(rp.raw(HERE + '/reference.cdl')) == record['reference_sha256']
        assert rp.sha(rp.raw(HERE + '/intent.json')) == record['input_hashes']['intent.json']
        work = HERE + '/pex'
        os.mkdir(work)
        os.symlink('../fixture.gds', work + '/fixture.gds')
        meta = rp.prepare_deck(work, 'pex', top, distributed_supplies=tuple(record['distributed_supplies']))
        # Reapply the source run's FLATTEN additions (density row of the filled stream) from its own deck.
        deck = rp.raw(work + '/pex.svrf')
        ours, = FLATTEN.findall(deck.decode('latin1'))
        theirs, = FLATTEN.findall(rp.raw(src + '/pex/pex.svrf').decode('latin1'))
        added = [c for c in theirs.split()[2:] if c not in ours.split()[2:]]
        assert ours.split()[2:] == [c for c in theirs.split()[2:] if c not in added]
        deck = deck.replace((ours + '\n').encode('latin1'), (theirs + '\n').encode('latin1'))
        rp.put(work + '/pex.svrf', deck)
        meta['job_sha256'] = rp.sha(deck)
        assert meta['job_sha256'] == record['decks']['pex']['job_sha256'], 'Source deck reconstruction differs'
        meta['support'] = dict(record['decks']['pex']['support'])
        info = select(work, cfg, rp.PDK, os.path.join(rp.RULES, 'rcx'), meta, CORNER)
        status.update(gds_sha256=gds['sha256'], source_deck_job_sha256=record['decks']['pex']['job_sha256'],
                      flatten_added=added, deck=meta, interconnect_rc=info)
        save(status)
        for phase, args, limit in [('phdb', ['calibre', '-xrc', '-phdb', '-turbo', '4', '-nowait', 'pex.svrf'], 300),
                                   ('rcc', ['calibre', '-xrc', '-pdb', '-rcc', '-turbo', '4', '-nowait', 'pex.svrf'], 1800),
                                   ('format', ['calibre', '-xrc', '-fmt', '-all', '-nowait', 'pex.svrf'], 300)]:
            status['phases'][phase] = {'started': time.time()}
            save(status)
            rc = rp.tool(rp.CALIBRE, args, work, HERE + '/' + phase + '.console', limit)
            status['phases'][phase].update(returncode=rc, finished=time.time())
            save(status)
            if rc:
                raise RuntimeError(phase + ' failed: ' + str(rc))
    pex = dict((n, rp.sha(rp.raw(work + '/' + n))) for n in os.listdir(work) if n.startswith('extracted.scs'))
    assert len(pex) >= 3, 'Missing extracted companions'
    manifest = dict(record, id=IDENT, stream_source=SOURCE, drc_lvs_inherited_from=SOURCE, interconnect_rc=CORNER,
                    decks=dict(record['decks'], pex=meta), active_step='complete',
                    derived_from={'source_evidence': SOURCE, 'driver': 'xref_rc_corner.py', 'corner': CORNER,
                                  'source_manifest_sha256': rp.sha(rp.raw(src + '/manifest.json')),
                                  'source_pex_sha256': record['checks']['pex']['sha256']})
    manifest['checks'] = {'drc': record['checks']['drc'], 'lvs': record['checks']['lvs'],
                          'pex': {'sha256': pex.pop('extracted.scs'), 'companion_sha256': pex,
                                  'bytes': os.stat(work + '/extracted.scs').st_size}}
    with open(HERE + '/manifest.json.next', 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    os.rename(HERE + '/manifest.json.next', HERE + '/manifest.json')


if __name__ == '__main__':
    status = {'ident': IDENT, 'source': SOURCE, 'corner': CORNER, 'started': time.time(), 'phases': {},
              'status': 'running', 'physical_signoff': False}
    save(status)
    try:
        main(status)
    except Exception as exc:
        status.update(status='failed', error=str(exc), traceback=traceback.format_exc(), finished=time.time())
        save(status)
        raise
    status.update(status='complete', finished=time.time())
    save(status)
