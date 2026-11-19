"""Import native comparator fill and attach it to a fixed core wrapper."""
from __future__ import print_function
import fcntl,json,os,tarfile
from os.path import join
import workspace
from apply_fill import namespaced
from run_physical import tool,CADENCE,PDK,LIB,LIB_PATH,raw,sha,gds_identity


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence')
    args=parser.parse_args()
    config=workspace.paths()
    with open(config['lock'],'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        folder=workspace.evidence(args.evidence)
        record=json.loads(raw(join(folder,'fill_manifest.json')))
        if not record.get('generation_complete') or record['top']!='sar_strongarm_t28_core':
            raise ValueError('Need completed comparator fill')
        if os.path.exists(join(folder,'applied.json')):
            raise ValueError('Fill already applied')
        source = workspace.evidence(record['source_evidence'])
        original = join(source,'fixture.gds')
        if sha(raw(original)) != record['source_gds_sha256']:
            raise ValueError('Original core stream changed')
        current = join(folder,'current-core.gds')
        rc=tool(CADENCE,['strmout','-library',LIB,'-strmFile',current,'-topCell',record['top'],'-view','layout',
                        '-layerMap',join(PDK,'tsmcN28.layermap'),'-cdslib',join(config['runtime'],'cds.lib'),
                        '-logFile',join(folder,'core-stream.log'),'-runDir',folder,
                        '-convertPin','geometry','-convertPcellPin','geometry'],
                config['runtime'],join(folder,'core-stream.console'),120)
        if rc or gds_identity(current)['structural_sha256'][record['top']] != gds_identity(original)['structural_sha256'][record['top']]:
            raise ValueError('Current core differs from fill input')
        owned=['sar_strongarm_t28','sar8_comp_fill_odpo','sar8_comp_fill_metal']
        with tarfile.open(join(folder,'before-wrapper-oa.tar.gz'),'w:gz') as archive:
            for cell in owned:
                path=join(LIB_PATH,cell)
                if os.path.isdir(path):
                    if any('.cdslck' in name for directory,dirs,files in os.walk(path) for name in files):
                        raise ValueError('Owned cell has an edit lock')
                    archive.add(path,arcname=cell)
        applied={'fill_evidence':args.evidence,'core_evidence':record['source_evidence'],'imports':{}}
        for kind,suffix,prefix in [('ODPO','','SCFO_'),('metal','_DM','SCFM_')]:
            source=join(folder,kind,'fill.gds')
            if sha(raw(source))!=record['steps'][kind]['gds_sha256']:
                raise ValueError('Fill stream changed')
            target=join(folder,kind,'fill-import.gds')
            top='sar8_comp_fill_'+kind.lower()
            digest=namespaced(source,target,record['top']+suffix,top,prefix)
            rc=tool(CADENCE,['strmin','-library',LIB,'-strmFile',target,'-topCell',top,'-view','layout',
                            '-attachTechFileOfLib','tsmcN28','-layerMap',join(PDK,'tsmcN28.layermap'),
                            '-logFile',join(folder,kind,'import.log')],config['runtime'],join(folder,kind,'import.console'),180)
            if rc:raise RuntimeError('Native fill import failed')
            applied['imports'][kind]={'sha256':digest,'top':top}
        script=join(config['runtime'],'comparator-wrapper.il')
        frozen=join(folder,'comparator-wrapper.il')
        with open(frozen,'wb') as stream:stream.write(raw(script))
        rc=tool(CADENCE,['virtuoso','-nograph','-nocdsinit','-log',join(folder,'wrapper.log'),'-restore',frozen],
                config['runtime'],join(folder,'wrapper.console'),120)
        if rc or b'COMPARATOR_WRAPPER_OK' not in raw(join(folder,'wrapper.console')):
            raise RuntimeError('Wrapper failed native readback')
        applied['wrapper_script_sha256']=sha(raw(frozen))
        with open(join(folder,'applied.json'),'w') as stream:json.dump(applied,stream,indent=2)
        with open(workspace.state('comparator-fill-applied.json'),'w') as stream:json.dump(applied,stream,indent=2)
        print(json.dumps(applied,indent=2))


if __name__=='__main__':main()
