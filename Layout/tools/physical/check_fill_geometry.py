"""Verify that removing only fill references restores the routed GDS geometry."""
from __future__ import print_function
import argparse,json,os,re
import workspace
from run_physical import gds_identity


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence');a=p.parse_args()
    assert re.match(r'^[a-z0-9][a-z0-9-]{1,55}$',a.evidence)
    configured=workspace.paths()
    source=os.path.join(workspace.evidence('cdac-full-route3'),'fixture.gds')
    folder=workspace.evidence(a.evidence)
    if not folder.startswith(configured['evidence']+'/'):raise ValueError('Historical evidence is read-only')
    target=os.path.join(folder,'fixture.gds')
    baseline=gds_identity(source)
    projection=gds_identity(target,('sar8_cdac_fill_odpo','sar8_cdac_fill_metal'))
    top='sar8j_r1_cdac'
    functional='sar8j_r1_cdac_core' if 'sar8j_r1_cdac_core' in projection['structural_sha256'] else top
    assert projection['structural_sha256'][functional]==baseline['structural_sha256'][top]
    assert projection['labels'][top]==baseline['labels'][top]
    result={'pass':True,'comparison':'Shared functional core (or historical top with fill omitted) versus routed baseline',
            'source_gds_sha256':baseline['sha256'],'filled_gds_sha256':projection['sha256'],
            'functional_cell':functional,
            'functional_top_sha256':projection['structural_sha256'][functional],
            'half_sha256':projection['structural_sha256']['sar8_cdac_half'],
            'ports_unchanged':len(projection['labels'][top])==38}
    with open(os.path.join(folder,'functional_geometry.json'),'w') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
