"""Read-only device metadata; no OA edits, model contents or simulator launch."""
import argparse,json
from pathlib import Path
from virtuoso_bridge import VirtuosoClient

ROOT = Path(__file__).resolve().parents[2]
PARAMS = set('l w nf sd ad as pd ps nrd nrs sa sb sa1 sa2 sa3 sa4 sb1 sb2 sb3 spa spa1 spa2 spa3 sap sapb spba spba1 spmt spomt spomt1 spmb spomb spomb1'.split())

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');a=p.parse_args()
    c = VirtuosoClient.from_env(profile='t28_io')
    result = {}
    for family in (['na18'] if a.native else ['18', '18ud12']):
        for pol in (['n'] if a.native else ['n', 'p']):
            name = pol+'ch_'+family+'_mac'
            entries = c.fetch('cdfGetCellCDF(ddGetObj("tsmcN28" "'+name+'"))~>parameters',
                              ['name', 'defValue'], timeout=20)
            values = {x['name']: x['defValue'] for x in entries}
            result[name] = dict(description=values['description'],
                parameters={k: values[k] for k in sorted(PARAMS) if k in values},
                qualification='CDF default geometry; native acceptance still required; not DRC')
    p = ROOT/'verification/sar8_physical_repair'/('native_cdf_audit.json' if a.native else 'io_cdf_audit.json')
    p.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
