"""Import native fill into fixed auxiliary masters and update the same CDAC."""
from __future__ import print_function
import workspace
import argparse,fcntl,json,os,re,struct
from os.path import join
from run_physical import tool,CADENCE,PDK,gds_identity,sha,raw

def namespaced(source,dest,old_top,new_top,prefix):
    data=raw(source);before=gds_identity(source)
    names={n:(new_top if n==old_top else prefix+sha(n.encode('ascii'))[:18]) for n in before['labels']}
    chunks=[];offset=0
    while offset<len(data):
        size,record,kind=struct.unpack_from('>HBB',data,offset)
        blob=data[offset:offset+size]
        if record in (6,18):
            value=names[blob[4:].rstrip(b'\0').decode('ascii')].encode('ascii')
            if len(value)%2:value+=b'\0'
            blob=struct.pack('>HBB',len(value)+4,record,kind)+value
        chunks.append(blob);offset+=size
        if record==4:break
    with open(dest,'wb') as f:f.write(b''.join(chunks))
    after=gds_identity(dest)
    assert before['structural_sha256'][old_top]==after['structural_sha256'][new_top]
    return after['sha256']

def records(data):
    offset=0
    while offset<len(data):
        size,record,kind=struct.unpack_from('>HBB',data,offset)
        if size<4:raise ValueError('Invalid GDS record')
        yield record,data[offset:offset+size]
        offset+=size
        if record==4:break


def gds_record(number,kind,payload=b''):
    if len(payload)%2:payload+=b'\0'
    return struct.pack('>HBB',len(payload)+4,number,kind)+payload


def cumulative(sources,dest,old_top,top,prefix):
    """Keep every native fill polygon, adding only a zero-offset wrapper."""
    header=[];structures=[];subtops=[];selected=[];units=None;dates=None
    for index,source in enumerate(sources):
        identity=gds_identity(source)
        if old_top not in identity['labels']:
            if identity['labels']:raise ValueError('Native fill has an unexpected top')
            continue  # Native KEEP EMPTY NO: no further fill was generated.
        part=dest+'.part%d'%index;subtop=top+'_pass%d'%index
        namespaced(source,part,old_top,subtop,prefix+str(index)+'_')
        subtops.append(subtop);selected.append(source)
        active=False
        for record,blob in records(raw(part)):
            if record==3:
                if units is None:units=blob
                elif units!=blob:raise ValueError('Inconsistent native fill units')
            if record==5:
                active=True
                if dates is None:dates=blob
            if active:structures.append(blob)
            elif index==0 and record!=4:header.append(blob)
            if record==7:active=False
    wrapper=[dates,gds_record(6,6,top.encode('ascii'))]
    for name in subtops:
        wrapper.extend([gds_record(10,0),gds_record(18,6,name.encode('ascii')),
                        gds_record(16,3,struct.pack('>ii',0,0)),gds_record(17,0)])
    with open(dest,'wb') as f:f.write(b''.join(header+structures+wrapper+[gds_record(7,0),gds_record(4,0)]))
    result=gds_identity(dest)
    for source,name in zip(selected,subtops):
        assert gds_identity(source)['structural_sha256'][old_top]==result['structural_sha256'][name]
    return result['sha256']


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('--prior',action='append',default=[])
    p.add_argument('--resume-imports',action='store_true');a=p.parse_args()
    for identity in a.prior+[a.evidence]:
        if not re.match(r'^cdac-full-fill[0-9]+$',identity):raise ValueError('Unsafe evidence')
    configured=workspace.paths();root=configured['runtime']
    lock=open(configured['lock'],'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    folder=workspace.evidence(a.evidence)
    if not folder.startswith(configured['evidence']+'/'):raise ValueError('Historical evidence is read-only')
    record=json.load(open(join(folder,'fill_manifest.json')))
    assert record['generation_complete']
    assert not os.path.exists(join(folder,'applied.json')), 'Fill already applied'
    applied={'fill_evidence':a.evidence,'prior_fill_evidence':a.prior,'source_gds_sha256':record['source_gds_sha256'],'imports':{}}
    for kind,suffix,prefix in [('ODPO','','CDFO_'),('metal','_DM','CDFM_')]:
        original=join(folder,kind,'fill.gds');assert sha(raw(original))==record['steps'][kind]['gds_sha256']
        dest=join(folder,kind,'fill-import.gds');top='sar8_cdac_fill_'+kind.lower()
        sources=[]
        for prior in a.prior:
            parent=workspace.evidence(prior);pm=json.load(open(join(parent,'fill_manifest.json')))
            source=join(parent,kind,'fill.gds');assert sha(raw(source))==pm['steps'][kind]['gds_sha256']
            sources.append(source)
        sources.append(original)
        identity=cumulative(sources,dest,'sar8j_r1_cdac'+suffix,top,prefix) if a.prior else namespaced(original,dest,'sar8j_r1_cdac'+suffix,top,prefix)
        console=join(folder,kind,'import.console')
        if os.path.exists(console):
            assert a.resume_imports and "INFO (XSTRM-234): Translation completed. '0' error(s)" in open(console).read()
            rc=0
        else:rc=tool(CADENCE,['strmin','-library','SAR_ADC_T28_LAYOUT','-strmFile',dest,'-topCell',top,'-view','layout',
                        '-attachTechFileOfLib','tsmcN28','-layerMap',join(PDK,'tsmcN28.layermap'),
                        '-logFile',join(folder,kind,'import.log')],root,console,180)
        if rc:raise RuntimeError('Fill import failed')
        applied['imports'][kind]={'sha256':identity,'top':top}
    script='''let((cv master old i)
unless(equal(ddGetObj("SAR_ADC_T28_LAYOUT")~>readPath "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT") error("Not private library\\n"))
cv=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "sar8j_r1_cdac" "layout" "maskLayout" "a")
unless(cv && length(cv~>terminals)==38 error("Invalid CDAC interface\\n"))
unless(length(setof(i cv~>instances equal(i~>name "XCORE")))==1 error("Missing shared functional core\\n"))
foreach(pair list(list("FILL_ODPO" "sar8_cdac_fill_odpo") list("FILL_METAL" "sar8_cdac_fill_metal"))
 old=car(setof(i cv~>instances equal(i~>name car(pair))))
 when(old dbDeleteObject(old))
 master=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" cadr(pair) "layout" "" "r")
 unless(master error("Missing native fill master\\n"))
 i=dbCreateInst(cv master car(pair) list(0 0) "R0")
 unless(i error("Cannot attach fill\\n")))
unless(dbSave(cv) error("Cannot save filled CDAC\\n"))
printf("CDAC_FILL_APPLIED ports=%d instances=%d bbox=%L\\n" length(cv~>terminals) length(cv~>instances) cv~>bBox)
dbClose(cv))
exit(0)
'''
    path=join(folder,'apply.il');open(path,'w').write(script)
    rc=tool(CADENCE,['virtuoso','-nograph','-nocdsinit','-log',join(folder,'apply.ciw.log'),'-restore',path],root,join(folder,'apply.console'),120)
    if rc or 'CDAC_FILL_APPLIED ports=38 instances=3' not in open(join(folder,'apply.console')).read():raise RuntimeError('No verified fill application')
    applied['apply_script_sha256']=sha(raw(path))
    for path in [join(folder,'applied.json'),workspace.state('fill_applied.json')]:
        with open(path,'w') as f:json.dump(applied,f,indent=2,sort_keys=True)
    print(json.dumps(applied,indent=2))

if __name__=='__main__':main()
