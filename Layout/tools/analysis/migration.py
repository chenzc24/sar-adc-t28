"""Compare immutable native evidence and collected current-DUT short tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from Layout.project import ROOT, config, evidence, write_json
from Layout.tools.simulation.prepare_full_sim import pull


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def canonical_netlist(blob):
    # Strip only whole-line simulator comments/blank lines, never statements,
    # instance order, node names, parameters, or paths inside include statements.
    return '\n'.join(line.rstrip() for line in blob.decode('ascii').splitlines()
                     if line.strip() and not line.lstrip().startswith(('//', '*'))).encode('ascii')


def netlist_identities(remote, expected):
    """Stream hashes on the log host; return only small metadata, no model text."""
    for name in expected:
        if Path(name).name != name:raise ValueError('Unsafe PEX member')
    request = json.dumps({'directory': remote+'/pex', 'expected':expected})
    code = '''import json,os,hashlib
r=json.loads(%r);result={}
for name,expected in r['expected'].items():
 p=os.path.join(r['directory'],name)
 assert os.stat(p).st_uid==os.getuid()
 raw=hashlib.sha256();statements=hashlib.sha256();first=True
 with open(p,'rb') as f:
  for line in f:
   raw.update(line)
   if not line.strip() or line.lstrip().startswith((b'//',b'*')):continue
   if not first:statements.update(b'\\n')
   statements.update(line.rstrip());first=False
 assert raw.hexdigest()==expected,'PEX identity changed'
 result[name]={'sha256':raw.hexdigest(),'statement_sha256':statements.hexdigest()}
print(json.dumps(result))
''' % request
    return json.loads(subprocess.check_output(['ssh',config()['host'],'python -'],input=code.encode(),timeout=45))


def compare_physical(before_id, after_id):
    manifests = []
    for identity in [before_id, after_id]:
        remote = evidence(identity)
        raw = pull(remote+'/manifest.json'); m = json.loads(raw)
        if m.get('error') or m['checks'].get('format', {}).get('returncode') != 0:
            raise ValueError('Physical evidence incomplete/failed: '+identity)
        manifests.append((remote, raw, m))
    before, after = [item[2] for item in manifests]
    top = before['top']
    checks = {'same_cell': top == after['top'] and before['library'] == after['library'],
              'geometry_equal': before['gds']['structural_sha256'][top] == after['gds']['structural_sha256'][top],
              'labels_equal_raw_names': before['gds']['labels'] == after['gds']['labels'],
              'labels_equal_by_geometry': sorted((before['gds']['structural_sha256'][k],sorted(v)) for k,v in before['gds']['labels'].items()) ==
                                           sorted((after['gds']['structural_sha256'][k],sorted(v)) for k,v in after['gds']['labels'].items()),
              'drc_markers_equal': before['checks']['drc']['markers_by_rule'] == after['checks']['drc']['markers_by_rule'],
              'lvs_correct': before['checks']['lvs']['verdict'] == after['checks']['lvs']['verdict'] == 'CORRECT',
              'generator_and_reference_bytes_equal': before['source_sha256'] == after['source_sha256'],
              'rule_decks_equal': before['decks'] == after['decks']}
    # Deck paths may be run-local. Report raw differences instead of normalizing
    # them speculatively; exact rule/deck identities remain in both manifests.
    references = [pull(remote+'/reference.cdl') for remote,_,_ in manifests]
    checks['lvs_reference_text_equal'] = references[0].decode().splitlines() == references[1].decode().splitlines()
    file_sets = []
    for remote, raw, m in manifests:
        hashes = {'extracted.scs': m['checks']['pex']['sha256'], **m['checks']['pex']['companion_sha256']}
        file_sets.append(netlist_identities(remote,hashes))
    checks['pex_statements_equal'] = ({k:v['statement_sha256'] for k,v in file_sets[0].items()} ==
                                       {k:v['statement_sha256'] for k,v in file_sets[1].items()})
    return {'before': before_id, 'after': after_id, 'checks': checks,
            'evidence': [{'remote': p, 'manifest_sha256': sha(raw), 'gds': m['gds'],
                          'checks': m['checks'], 'decks': m['decks'], 'pex_files': fs}
                         for (p,raw,m),fs in zip(manifests,file_sets)],
            'qualification': 'migration_equivalence_only; original warnings and performance failures remain'}


def summarize_tt(run_id):
    run = ROOT/'work/output/managed_execution/runs'/run_id/'collected'
    path = run/'derived/result.json'; raw = path.read_bytes(); d = json.loads(raw)
    if not d['analysis_complete'] or len(d['frames']) != 10:
        raise ValueError('Incomplete ten-frame analysis')
    frames = [{key:f.get(key) for key in ['frame','expected_code','code_90','code_pass','counts',
                'timing_pass','sample_edges_pass','observer_crosscheck','event_order_pass','conversion_ns',
                'deadline_margin_ns','issues']} | {'sample_close_events':[e for e in f['events']
                if e['signal'] in ['sample','sample_int','close'] and not e['rising']]}
              for f in d['frames']]
    return {'run_id': run_id, 'result_sha256': sha(raw), 'context': d['context'],
            'frames': frames, 'all_code_pass': d['all_code_pass'],
            'all_timing_pass': all(f['timing_pass'] and f['sample_edges_pass'] and f['observer_crosscheck']
                                   and f['event_order_pass'] for f in frames),
            'first_issue': d['first_issue'], 'precharge': d['precharge'],
            'warning_codes': d['warning_codes'], 'warning_lines': d['warning_lines'],
            'settling_scope': d['settling_scope'], 'current_scope': d['current_scope'], 'limitations': d['limitations']}


def compare_tt(before, after, tolerance_s):
    if before['context']['prelayout_design_id'] != after['context']['prelayout_design_id']:
        raise ValueError('Different electrical design')
    if before['context']['expected_codes'] != after['context']['expected_codes']:
        raise ValueError('Different fixture codes')
    rows = []
    for a,b in zip(before['frames'], after['frames']):
        exact = all(a[k] == b[k] for k in ['frame','expected_code','code_90','counts','timing_pass',
                                         'sample_edges_pass','observer_crosscheck','event_order_pass','issues'])
        ea, eb = a['sample_close_events'], b['sample_close_events']
        edge_identity = [(e['signal'],e['rising']) for e in ea] == [(e['signal'],e['rising']) for e in eb]
        delta = max([abs(x['time_s']-y['time_s']) for x,y in zip(ea,eb)] or [0])
        conversion = abs(a['conversion_ns']-b['conversion_ns'])*1e-9
        rows.append({'frame':a['frame'],'same_codes_events_verdicts':exact,'sample_edge_delta_s':delta,
                     'conversion_delta_s':conversion,'pass':exact and edge_identity and delta <= tolerance_s and conversion <= tolerance_s})
    return {'pass':all(x['pass'] for x in rows),'tolerance_s':tolerance_s,'frames':rows,
            'scope':'Equality of migration measurements, not ADC performance acceptance'}


def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('physical');a.add_argument('before');a.add_argument('after')
    a=s.add_parser('tt');a.add_argument('run_id')
    args=p.parse_args()
    value=compare_physical(args.before,args.after) if args.action=='physical' else summarize_tt(args.run_id)
    target=ROOT/'work/layout/restructure'/('physical_comparison.json' if args.action=='physical' else args.run_id+'-summary.json')
    write_json(target,value)
    print(json.dumps({'output':str(target),'checks':value.get('checks'),
                      'all_code_pass':value.get('all_code_pass'),'all_timing_pass':value.get('all_timing_pass')},indent=2))


if __name__=='__main__':main()
