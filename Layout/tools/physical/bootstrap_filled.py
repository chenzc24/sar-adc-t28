"""DRC, LVS and PEX of a Bootstrap core with its planned fill, at one interconnect corner (remote, Python 2).

Runs from its own new evidence directory, created by Layout/design/bootstrap_fill.py launch, which uploads this
driver, sar_rc_corner.py, filled.gds (the source core stream with Layout/design/bootstrap_fill.py's plan
flattened into the core top) and fill.json (the plan summary and the source stream digest). The OA is not
opened. DRC (cell deck), LVS against the source run's reference and PEX run fresh on the filled stream; for
cworst_T or cbest_T only the foundry xRC rules include changes (sar_rc_corner.select). The manifest keeps the
run_physical bootstrap schema, so Layout/tools/simulation/bootstrap_pex.py packages it like a core extraction.
Usage: python bootstrap_filled.py SOURCE CORNER   (typical | cworst_T | cbest_T)
"""
from __future__ import print_function
import fcntl, json, os, re, shutil, sys, time, traceback

HERE = os.path.dirname(os.path.realpath(__file__))
IDENT = os.path.basename(HERE)
SOURCE, CORNER = sys.argv[1], sys.argv[2]
STATUS = HERE + '/status.json'
RUNTIME = os.path.dirname(os.path.dirname(HERE)) + '/runtime'


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
    record = json.load(open(src + '/manifest.json'))
    checks = record['checks']
    assert record['case'] == 'bootstrap' and not record.get('error') and 'interconnect_rc' not in record
    assert checks['lvs']['verdict'] == 'CORRECT' and 'sha256' in checks['pex']
    references = [k for k in record['source_sha256'] if k.endswith('reference.cdl')]
    assert len(references) == 1
    top = record['top']
    plan = json.load(open(HERE + '/fill.json'))
    assert plan['core_gds_sha256'] == record['gds']['sha256'], 'Fill assembled on another core stream'
    log = dict(checks={}, decks={})
    with open(cfg['lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        shutil.copyfile(HERE + '/filled.gds', HERE + '/fixture.gds')
        shutil.copyfile(os.path.join(src, 'reference.cdl'), HERE + '/reference.cdl')
        assert rp.sha(rp.raw(HERE + '/reference.cdl')) == record['source_sha256'][references[0]]
        gds = rp.gds_identity(HERE + '/fixture.gds')
        assert gds['sha256'] == plan['out_sha256']
        assert sorted(gds['labels'].get(top, [])) == sorted(rp.BOOTSTRAP_PORTS), 'Filled stream ports differ'
        status.update(gds_sha256=gds['sha256'])
        save(status)
        for name, args, limit in [('drc', ['calibre', '-drc', '-hier', '-turbo', '4', '-nowait', 'drc.svrf'], 600),
                                  ('lvs', ['calibre', '-lvs', '-hier', '-turbo', '4', '-nowait', 'lvs.svrf'], 600),
                                  ('pex', None, None)]:
            work = HERE + '/' + name
            os.mkdir(work)
            os.symlink('../fixture.gds', work + '/fixture.gds')
            meta = rp.prepare_deck(work, name, top)
            if name == 'pex' and CORNER != 'typical':
                meta['interconnect_rc'] = select(work, cfg, rp.PDK, os.path.join(rp.RULES, 'rcx'), meta, CORNER)
            log['decks'][name] = meta
            phases = [(name, args, limit)] if args else [
                ('phdb', ['calibre', '-xrc', '-phdb', '-turbo', '4', '-nowait', 'pex.svrf'], 300),
                ('rcc', ['calibre', '-xrc', '-pdb', '-rcc', '-turbo', '4', '-nowait', 'pex.svrf'], 1800),
                ('format', ['calibre', '-xrc', '-fmt', '-all', '-nowait', 'pex.svrf'], 300)]
            for phase, command, seconds in phases:
                status['phases'][phase] = {'started': time.time()}
                save(status)
                rc = rp.tool(rp.CALIBRE, command, work, HERE + '/' + phase + '.console', seconds)
                status['phases'][phase].update(returncode=rc, finished=time.time())
                save(status)
                if rc:
                    raise RuntimeError(phase + ' failed: ' + str(rc))
            if name == 'drc':
                report = rp.read(work + '/DRC.rep')
                count = re.search(r'TOTAL DRC Results Generated:\s*(\d+)', report, re.I)
                rules = rp.drc_rules(work + '/DRC_RES.db')
                assert count and sum(rules.values()) == int(count.group(1)), 'DRC marker counts disagree'
                log['checks']['drc'] = dict(markers=int(count.group(1)), markers_by_rule=rules,
                                            verdict='NOT_CLEAN' if rules else 'CLEAN',
                                            deferred_fill_rules=sorted(set(rules) & rp.BOOTSTRAP_FILL_RULES))
                status['drc_markers_by_rule'] = rules
                save(status)
            elif name == 'lvs':
                report = rp.read(work + '/lvs.rep')
                match = re.search(r'(?m)^[ \t]+(CORRECT|INCORRECT)[ \t]+' + re.escape(top) + r'[ \t]+' + re.escape(top)
                                  + r'[ \t]*$', report)
                assert match, 'Missing LVS comparison verdict'
                log['checks']['lvs'] = dict(verdict=match.group(1))
                if match.group(1) != 'CORRECT':
                    raise RuntimeError('LVS ' + match.group(1))
        if rp.sha(rp.raw(HERE + '/fixture.gds')) != gds['sha256']:
            raise RuntimeError('GDS changed during the checks')
    work = HERE + '/pex'
    pex = dict((n, rp.sha(rp.raw(work + '/' + n))) for n in os.listdir(work) if n.startswith('extracted.scs'))
    assert sorted(pex) == sorted(['extracted.scs'] + list(checks['pex']['companion_sha256'])), 'Extracted file set differs'
    log['checks']['pex'] = {'sha256': pex.pop('extracted.scs'), 'companion_sha256': pex,
                            'bytes': os.stat(work + '/extracted.scs').st_size}
    manifest = dict(record, id=IDENT, gds=gds, decks=log['decks'], checks=log['checks'], active_step='complete',
                    filled=dict(source_evidence=SOURCE, plan=plan, driver='bootstrap_filled.py'),
                    derived_from={'source_evidence': SOURCE, 'driver': 'bootstrap_filled.py', 'corner': CORNER,
                                  'source_manifest_sha256': rp.sha(rp.raw(src + '/manifest.json')),
                                  'source_pex_sha256': checks['pex']['sha256'],
                                  'driver_sha256': dict((n, rp.sha(rp.raw(HERE + '/' + n)))
                                                        for n in ('bootstrap_filled.py', 'sar_rc_corner.py'))})
    manifest.pop('oa_checkpoint_sha256', None)
    manifest.pop('other_views_layout_oa_sha256', None)
    if CORNER != 'typical':
        manifest['interconnect_rc'] = CORNER
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
