"""Build the Bootstrap fill cell and filled wrapper in OA, then stream the wrapper (remote, Python 2).

Runs from its own new evidence directory, created by Layout/design/bootstrap_fill.py build, which uploads this
driver and build.il (generated from the fill plan). Under the shared layout lock it checks that no target view
belongs to another owner, records layout.oa of every existing view of the core cell, runs build.il once in a
non-graphical Virtuoso, requires every recorded view to be byte-identical afterwards, and streams the wrapper.
Usage: python bootstrap_fill_build.py CORE_VIEW FILL_CELL WRAPPER_CELL VIEW
"""
from __future__ import print_function
import fcntl, json, os, sys, time, traceback

HERE = os.path.dirname(os.path.realpath(__file__))
IDENT = os.path.basename(HERE)
CORE_VIEW, FILL_CELL, WRAPPER, VIEW = sys.argv[1:5]
CORE = 'sar_bootstrap_flat_8b_p_core'
STATUS = HERE + '/manifest.json'
RUNTIME = os.path.dirname(os.path.dirname(HERE)) + '/runtime'
OWNER = 'Layout/design/bootstrap_fill.py'


def save(value):
    with open(STATUS + '.next', 'w') as f:
        json.dump(value, f, indent=2, sort_keys=True)
    os.rename(STATUS + '.next', STATUS)


def digests(rp, cell):
    path = os.path.join(rp.LIB_PATH, cell)
    if not os.path.isdir(path):
        return {}
    return dict((v, rp.sha(rp.raw(os.path.join(path, v, 'layout.oa')))) for v in sorted(os.listdir(path))
                if os.path.isfile(os.path.join(path, v, 'layout.oa')))


def main(log):
    os.chdir(RUNTIME)
    sys.path.insert(0, RUNTIME)
    import workspace, run_physical as rp
    cfg = workspace.paths()
    for name in ('cds.lib', 'workspace.json'):
        rp.put(os.path.join(HERE, name), rp.raw(os.path.join(RUNTIME, name)))
    with open(cfg['lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for cell in (CORE, FILL_CELL, WRAPPER):
            path = os.path.join(rp.LIB_PATH, cell)
            if os.path.isdir(path) and any('.cdslck' in n for d, s, files in os.walk(path) for n in files):
                raise RuntimeError(cell + ' is locked by another editor')
        log['before'] = dict((c, digests(rp, c)) for c in (CORE, FILL_CELL, WRAPPER))
        if CORE_VIEW not in log['before'][CORE]:
            raise RuntimeError('Missing core view ' + CORE_VIEW)
        save(log)
        rc = rp.tool(rp.CADENCE, ['virtuoso', '-nograph', '-nocdsinit', '-log', HERE + '/oa.ciw.log', '-restore',
                                  HERE + '/build.il'], HERE, HERE + '/oa.console', 300)
        log['checks']['oa'] = dict(returncode=rc)
        save(log)
        console = rp.read(HERE + '/oa.console')
        if rc or 'BOOTSTRAP_FILL_OK' not in console:
            raise RuntimeError('OA build failed; see oa.console')
        after = digests(rp, CORE)
        if after != log['before'][CORE]:
            raise RuntimeError('The build changed a view of ' + CORE)
        log['after'] = dict((c, digests(rp, c)) for c in (CORE, FILL_CELL, WRAPPER))
        for cell, views in log['before'].items():
            for v, digest in views.items():
                if v != VIEW and log['after'][cell].get(v) != digest:
                    raise RuntimeError('The build changed %s/%s' % (cell, v))
        save(log)
        gds = HERE + '/wrapper.gds'
        rc = rp.tool(rp.CADENCE, ['strmout', '-library', rp.LIB, '-strmFile', gds, '-topCell', WRAPPER, '-view', VIEW,
                                  '-layerMap', os.path.join(rp.PDK, 'tsmcN28.layermap'), '-logFile', HERE + '/stream.log',
                                  '-summaryFile', HERE + '/stream.sum', '-cdslib', HERE + '/cds.lib', '-runDir', HERE,
                                  '-convertPin', 'geometry', '-convertPcellPin', 'geometry'], HERE, HERE + '/stream.console', 300)
        log['checks']['stream'] = dict(returncode=rc)
        if rc:
            raise RuntimeError('strmout failed')
        if digests(rp, CORE) != log['before'][CORE]:
            raise RuntimeError('A view of the core changed while streaming')
        log['gds'] = rp.gds_identity(gds)
        log['gds'].pop('labels', None)


if __name__ == '__main__':
    log = dict(ident=IDENT, core_view=CORE_VIEW, fill_cell=FILL_CELL, wrapper=WRAPPER, view=VIEW, owner=OWNER,
               started=time.time(), checks={}, status='running',
               build_il_sha256=__import__('hashlib').sha256(open(HERE + '/build.il', 'rb').read()).hexdigest())
    save(log)
    try:
        main(log)
    except Exception as exc:
        log.update(status='failed', error=str(exc), traceback=traceback.format_exc(), finished=time.time())
        save(log)
        raise
    log.update(status='complete', finished=time.time())
    save(log)
