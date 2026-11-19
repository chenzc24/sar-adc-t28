"""Run installed foundry fill utilities on a verified CDAC stream, privately.

Macro-boundary switches and paths are set on a private job copy. An explicit
core dummy width can additionally change two fill-shape parameters; the
foundry DRC checker stays unchanged. Proprietary data stays on the server.
"""
from __future__ import print_function
import workspace
import argparse,fcntl,hashlib,json,os,re,shutil
from os.path import join
from run_physical import tool,CALIBRE,gds_identity

SOURCES='/home/dmanager/shared_lib/TSMC28/dummy'
BOUNDARY={'xLB':-1.165,'yLB':-50.0,'xRT':89.165,'yRT':42.48}

def digest(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest()

def change(text,pattern,replacement):
    text,n=re.subn(pattern,lambda m:replacement,text,flags=re.M)
    if n!=1:raise ValueError('Expected one documented directive: '+pattern)
    return text

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('evidence')
    p.add_argument('--module', choices=('cdac','comparator','sar-timing'), default='cdac')
    p.add_argument('--bounds', type=float, nargs=4, help='Native module stream boundary, x0 y0 x1 y1')
    p.add_argument('--core-od-width',type=float,default=0.1)
    p.add_argument('--core-only-clearance',action='store_true')
    p.add_argument('--mos-dummy-length',type=float,default=0.3)
    p.add_argument('--resume',action='store_true',help='Finish bookkeeping/remaining stages after a successful native stage')
    p.add_argument('--wait-for-lock',action='store_true',help='Queue behind the active physical job')
    a=p.parse_args()
    if a.core_od_width not in (0.1,0.2,0.3):raise ValueError('Unsupported dummy geometry')
    if a.mos_dummy_length not in (0.3,1.0):raise ValueError('Unsupported MOS dummy length')
    if a.mos_dummy_length!=0.3 and not a.core_only_clearance:raise ValueError('Require verified core-only region')
    for value in [a.source,a.evidence]:
        if not re.match(r'^[a-z][a-z0-9-]{1,55}$',value):raise ValueError('Unsafe identity')
    configured=workspace.paths();root=configured['runtime']
    lock=open(configured['lock'],'a');fcntl.flock(lock,fcntl.LOCK_EX if a.wait_for_lock else fcntl.LOCK_EX|fcntl.LOCK_NB)
    prior=workspace.evidence(a.source);m=json.load(open(join(prior,'manifest.json')))
    expected_case = 'full' if a.module == 'cdac' else a.module
    if m['case']!=expected_case or m['checks']['lvs']['verdict']!='CORRECT':raise ValueError('Need verified module source')
    top = m['top']
    boundary = BOUNDARY
    if a.module in ('comparator','sar-timing'):
        if not a.bounds or a.bounds[0]>=a.bounds[2] or a.bounds[1]>=a.bounds[3]:
            raise ValueError('Module needs a measured stream boundary')
        boundary = dict(zip(('xLB','yLB','xRT','yRT'),a.bounds))
    elif a.bounds:
        raise ValueError('CDAC retains its measured boundary')
    source_gds=join(prior,'fixture.gds')
    if digest(source_gds)!=m['gds']['sha256']:raise ValueError('Source identity changed')
    out=join(configured['evidence'],a.evidence)
    if not a.resume and os.path.exists(join(configured['legacy_root'],'evidence',a.evidence)):
        raise ValueError('Historical evidence identity cannot be reused')
    record={'source_evidence':a.source,'source_gds_sha256':digest(source_gds),'top':top,
            'boundary_um':boundary,'threads':4,'steps':{},'physical_signoff':False,
            'core_dummy_od_width_um':a.core_od_width,
            'core_only_clearance':a.core_only_clearance,
            'mos_dummy_od_length_um':a.mos_dummy_length,
            'fill_geometry_customized':a.core_od_width!=0.1 or a.core_only_clearance or a.mos_dummy_length!=0.3}
    if a.resume:
        previous=json.load(open(join(out,'fill_manifest.json')))
        for key in record:
            if key!='steps' and record[key]!=previous[key]:raise ValueError('Resume input identity differs')
        record=previous
        record['bookkeeping_recovery']='Resume native stages with returncode=0 only; preserve original driver failure'
    else:os.mkdir(out)
    def save():
        with open(join(out,'fill_manifest.json'),'w') as f:json.dump(record,f,indent=2,sort_keys=True)
    save()
    for kind in ['ODPO','metal']:
        work=join(out,kind)
        if not os.path.exists(work):
            os.mkdir(work);shutil.copyfile(source_gds,join(work,'source.gds'))
        elif not a.resume:raise ValueError('Existing native stage')
        assert digest(join(work,'source.gds'))==record['source_gds_sha256']
        path=join(SOURCES,'dummy_script_'+kind);text=open(path).read()
        text=change(text,r'^LAYOUT PATH[^\n]*','LAYOUT PATH "source.gds"')
        text=change(text,r'^LAYOUT PRIMARY[^\n]*','LAYOUT PRIMARY "'+top+'"')
        text=change(text,r'^\s*//#DEFINE dmOnCorner[^\n]*','#DEFINE dmOnCorner')
        text=change(text,r'^#DEFINE WithSealring[^\n]*','//#DEFINE WithSealring')
        for name,value in boundary.items():
            text=change(text,r'^VARIABLE '+name+r'\s+[^\n]*','VARIABLE '+name+' '+str(value))
        # The installed metal stack is M1..M7 thin, M8 Z, M9 U (6X1Z1U).
        if kind=='metal':
            assert re.search(r'^\s*#DEFINE 9K_THICK_M8\b',text,re.M)
            assert re.search(r'^\s*#DEFINE 34K_THICK_M9\b',text,re.M)
            text=change(text,r'^DRC RESULTS DATABASE[^\n]*','DRC RESULTS DATABASE "fill.gds" GDSII _DM')
        else:
            text=change(text,r'^DFM DEFAULTS RDB GDS FILE[^\n]*','DFM DEFAULTS RDB GDS FILE "fill.gds"')
            if a.core_od_width!=0.1:
                # Insertion geometry only. SR_DOD.W.1/W.2 bounds are 0.05..0.5um;
                # final native DRC must still verify spacing and every density.
                for parameter in ['CO_CEL_SRDOD_W','CO_ODB_W']:
                    text=change(text,r'^VARIABLE '+parameter+r'\s+[^\n]*',
                                'VARIABLE '+parameter+' '+str(a.core_od_width))
            if a.core_only_clearance:
                # The native insertion defaults include IO's 0.15um clearance.
                # This macro has no OD2 devices; core DRC S.1/S.5 permit 0.08um.
                # Keep a 5nm explicit margin plus the utility's 5nm grid margin.
                for parameter in ['SRDOD2OD','SRDOD2SRDOD']:
                    text=change(text,r'^VARIABLE '+parameter+r'\s+[^\n]*','VARIABLE '+parameter+' 0.085')
                text+='\nCDAC_CORE_ONLY_PRECONDITION { COPY OD2 }\n'
            if a.mos_dummy_length!=0.3:
                # Extend the dummy OD and its dummy poly together, preserving
                # the native 80nm poly endcaps and the original X dimensions.
                # This changes fill geometry, never the functional transistors.
                text=change(text,r'^VARIABLE MOS_L\s+[^\n]*','VARIABLE MOS_L 1.16')
                pattern=r'(DFM SPEC FILL SHAPE SHAPE_MOS_6_7\b.*?)(?=DFM SPEC FILL SPEC_MOS\b)'
                match=re.search(pattern,text,re.S);assert match
                block=match.group(1).replace('0.380','1.080').replace('0.460','1.160')
                text=text[:match.start(1)]+block+text[match.end(1):]
                text+='\nCDAC_VERTICAL_ONLY_PRECONDITION { COPY MOS_Ho }\n'
        job=join(work,'fill.svrf')
        if kind in record['steps']:
            step=record['steps'][kind]
            assert a.resume and step.get('returncode')==0 and step['status']=='exited'
            assert open(job).read()==text and digest(job)==step['job_sha256']
            rc=0
        else:
            open(job,'w').write(text)
            step=record['steps'][kind]={'source':path,'source_sha256':digest(path),'job_sha256':digest(job),'status':'running'};save()
            rc=tool(CALIBRE,['calibre','-drc','-hier','-turbo','4','-nowait','fill.svrf'],work,join(work,'fill.console'),600)
            step.update(returncode=rc,status='exited');save()
        if rc:raise RuntimeError('Native '+kind+' fill failed; preserve evidence')
        if kind=='ODPO' and a.core_only_clearance:
            report=open(join(work,'DODPO.sum')).read()
            match=re.search(r'RuleCheck CDAC_CORE_ONLY_PRECONDITION\s+.*?TOTAL Result Count\s*=\s*(\d+)',report,re.I)
            if not match or int(match.group(1))!=0:raise ValueError('Core-only insertion requires an empty OD2 region')
            step['od2_precondition_count']=0
        if kind=='ODPO' and a.mos_dummy_length!=0.3:
            match=re.search(r'RuleCheck CDAC_VERTICAL_ONLY_PRECONDITION\s+.*?TOTAL Result Count\s*=\s*(\d+)',report,re.I)
            if not match or int(match.group(1))!=0:raise ValueError('Long MOS dummy needs vertical gates only')
            step['horizontal_region_precondition_count']=0
        result=join(work,'fill.gds')
        if not os.path.isfile(result):raise ValueError('No generated fill GDS')
        ident=gds_identity(result)
        step.update(gds_sha256=ident['sha256'],bytes=os.path.getsize(result),cells=sorted(ident['labels']))
        save()
    record['generation_complete']=True;save()
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
