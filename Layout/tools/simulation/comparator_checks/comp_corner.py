"""Re-extract the frozen comparator v8 stream at one interconnect corner with the supplies extracted (remote, Python 2).

Runs from its own new evidence directory, named <SOURCE>-<corner>-supplies. It links the GDS, reference,
DRC and LVS of the completed source run, rebuilds the nominal PEX deck with run_physical.prepare_deck
and requires it to equal the recorded deck. The job deck uses prepare_deck(distributed_supplies=
VDD, VSS), which drops them from PEX EXTRACT EXCLUDE, and, for cworst_T / cbest_T, swaps the foundry xRC rules
include (sar_rc_corner.select). It writes a run_physical-schema manifest so prepare_comparator
can bind the extraction. Usage: python comp_corner.py CORNER   (typical | cworst_T | cbest_T)
"""
from __future__ import print_function
import fcntl, json, os, re, sys, time, traceback

HERE = os.path.dirname(os.path.realpath(__file__))
IDENT = os.path.basename(HERE)
SOURCE = 'comp-v8-20261120-pex'
CORNER = sys.argv[1]
STATUS = HERE + '/status.json'
RUNTIME = os.path.dirname(os.path.dirname(HERE)) + '/runtime'
EXCLUDE = re.compile(r'(?im)^[ \t]*PEX[ \t]+EXTRACT[ \t]+EXCLUDE[ \t]+([^\r\n]+)')
SUPPLIES = ('VDD', 'VSS')


def save(value):
    with open(STATUS + '.next', 'w') as f:
        json.dump(value, f, indent=2, sort_keys=True)
    os.rename(STATUS + '.next', STATUS)


def main(status):
    assert CORNER in ('typical', 'cworst_T', 'cbest_T')
    sys.path.insert(0, HERE)
    from sar_rc_corner import select
    os.chdir(RUNTIME)
    sys.path.insert(0, RUNTIME)
    import workspace, run_physical as rp
    cfg = workspace.paths()
    src = os.path.join(cfg['evidence'], SOURCE)
    trial = json.load(open(src + '/manifest.json'))
    assert trial['case'] == 'comparator' and not trial.get('error') and trial['checks']['lvs']['verdict'] == 'CORRECT'
    top = trial['top']
    with open(cfg['lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for name in ('fixture.gds', 'reference.cdl', 'drc', 'lvs'):
            os.symlink(os.path.join('..', SOURCE, name), os.path.join(HERE, name))
        gds = rp.gds_identity(HERE + '/fixture.gds')
        assert gds['sha256'] == trial['gds']['sha256']
        # Reconstruct the recorded nominal deck first, in its own directory, to prove the inputs match.
        check = HERE + '/nominal_deck'
        os.mkdir(check)
        os.symlink('../fixture.gds', check + '/fixture.gds')
        nominal = rp.prepare_deck(check, 'pex', top)
        assert nominal['job_sha256'] == trial['decks']['pex']['job_sha256'], 'Nominal deck reconstruction differs'
        excluded = EXCLUDE.findall(rp.raw(check + '/pex.svrf').decode('latin1'))
        work = HERE + '/pex'
        os.mkdir(work)
        os.symlink('../fixture.gds', work + '/fixture.gds')
        # The runner's own option: drop the supplies from PEX EXTRACT EXCLUDE so they extract as RC.
        meta = rp.prepare_deck(work, 'pex', top, distributed_supplies=SUPPLIES)
        assert meta['job_sha256'] != nominal['job_sha256'], 'Supply extraction did not change the deck'
        info = None
        if CORNER != 'typical':
            info = select(work, cfg, rp.PDK, os.path.join(rp.RULES, 'rcx'), meta, CORNER)
        status.update(gds_sha256=gds['sha256'], nominal_deck_job_sha256=nominal['job_sha256'], deck=meta,
                      nominal_exclude=excluded, interconnect_rc=info)
        save(status)
        for phase, args, limit in [('phdb', ['calibre', '-xrc', '-phdb', '-turbo', '4', '-nowait', 'pex.svrf'], 300),
                                   ('rcc', ['calibre', '-xrc', '-pdb', '-rcc', '-turbo', '4', '-nowait', 'pex.svrf'], 900),
                                   ('format', ['calibre', '-xrc', '-fmt', '-all', '-nowait', 'pex.svrf'], 300)]:
            status['phases'][phase] = {'started': time.time()}
            save(status)
            rc = rp.tool(rp.CALIBRE, args, work, HERE + '/' + phase + '.console', limit)
            status['phases'][phase].update(returncode=rc, finished=time.time())
            save(status)
            if rc:
                raise RuntimeError(phase + ' failed: ' + str(rc))
    pex = dict((n, rp.sha(rp.raw(work + '/' + n))) for n in os.listdir(work) if n.startswith('extracted.scs'))
    text = rp.raw(work + '/extracted.scs.pex').decode('latin1')
    for net in SUPPLIES:
        assert re.search(r'subckt PM_\S+%' + net + ' ', text), net + ' parasitic network missing'
    manifest = {
        'case': 'comparator', 'top': top, 'library': trial['library'],
        'derived_from': {'source_evidence': SOURCE, 'driver': 'comp_corner.py', 'corner': CORNER,
                         'distributed_supplies': list(SUPPLIES), 'source_manifest_sha256': rp.sha(rp.raw(src + '/manifest.json')),
                         'source_pex_sha256': trial['checks']['pex']['sha256']},
        'gds': trial['gds'], 'decks': dict(trial['decks'], pex=meta), 'physical_signoff': False,
        'interconnect_rc': info or 'typical (lab deck)',
        'checks': {'drc': trial['checks']['drc'], 'lvs': trial['checks']['lvs'],
                   'pex': {'sha256': pex.pop('extracted.scs'), 'companion_sha256': pex}}}
    with open(HERE + '/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


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
