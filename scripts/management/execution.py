"""Unified local controller. Remote state is authoritative; no automatic retries."""
from __future__ import annotations
import argparse,base64,hashlib,json,math,os,posixpath,re,shlex,shutil,subprocess,time
from pathlib import Path
import yaml
import project

ROOT=project.ROOT
OUT=ROOT/'output/managed_execution'
SPEC_ROOT=ROOT/'management/runs'
REMOTE_ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
POLICY={
 'version':2,'max_managed_workloads':7,'threads_per_simulation':16,'host_memory_reserve_mib':8192,'user_memory_reserve_mib':1024,
 'disk_reserve_mib':16384,'runtime_disk_floor_mib':4096,'max_swap_rate_mib_s':4,'max_load_per_cpu':1.25,
 'max_collection_mib':32,'local_disk_reserve_mib':2048,
 'spectre_path':'/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre',
 'cadence_setup':'/home/cshrc/.cshrc.cadence.IC618SP201'}

def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':')).encode()
def recipe_hash(d):return hashlib.sha256(canonical(d)).hexdigest()
def valid_id(s):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',s):raise ValueError('run_id must be a lowercase stable identifier')
    return s
def root_path(value):
    p=Path(value)
    p=p if p.is_absolute() else ROOT/p
    if p.is_symlink():raise ValueError('Symlink inputs are not supported')
    p=p.resolve()
    if not p.is_relative_to(ROOT) or not p.is_file() or p.is_symlink():raise ValueError('Input must be a project file: '+value)
    return p
def rpc(request,timeout=45):
    OUT.mkdir(exist_ok=True);stamp=str(time.time_ns());folder=OUT/'transport';folder.mkdir(exist_ok=True)
    agent=ROOT/'scripts/management/remote_agent.py';blob=agent.read_bytes();version=hashlib.sha256(blob).hexdigest()
    payload=dict(agent=base64.b64encode(blob).decode(),agent_hash=version,request=request)
    inp=folder/(stamp+'.input.json');project.save(inp,payload)
    bootstrap=r'''import os,sys,json,base64,hashlib
payload=json.load(sys.stdin);blob=base64.b64decode(payload['agent']);h=hashlib.sha256(blob).hexdigest()
assert h==payload['agent_hash']
root='/server_local_ssd/chenzc_intern25/sar-adc-t28';path=root+'/tools/agent_'+h+'.py'
scope={'__name__':'managed_agent','__file__':path};exec(compile(blob,path,'exec'),scope)
request=payload['request']
if request['action']=='init':result=scope['main'](request)
else:scope['owned'](root)
if not os.path.exists(path):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(blob)
assert scope['sha'](path)==h
if request['action']!='init':result=scope['main'](request)
print(json.dumps({'ok':True,'result':result}))
'''
    # thu-wei uses csh: do not send literal newlines through its command parser.
    encoded=base64.b64encode(bootstrap.encode()).decode('ascii')
    cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+encoded+"'))")
    out=folder/(stamp+'.output.json');err=folder/(stamp+'.stderr')
    with inp.open('rb') as i,out.open('wb') as o,err.open('wb') as e:
        try:rc=subprocess.run(['ssh','-C','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
            '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',cmd],stdin=i,stdout=o,stderr=e,timeout=timeout).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:raise RuntimeError(f'Remote result uncertain (exit {rc}); inspect {out}. Never auto-resubmit. '+err.read_text(errors='replace')[-1200:])
    response=json.loads(out.read_text(encoding='utf-8'))
    if not response.get('ok'):raise RuntimeError(str(response))
    return response['result']

def storage():
    result=rpc(dict(action='init',policy=POLICY))
    assert result['root']==REMOTE_ROOT and result['uid']==596 and result['probe_readback']
    dest=ROOT/'verification/managed_execution/storage.json';project.save(dest,result)
    cfg=project.load(ROOT/'management/project.yaml')
    cfg['roots'].update(new_run_root=REMOTE_ROOT+'/runs',new_run_root_status='owner_mount_write_read_verified')
    cfg['resource_policy'].update(status='enforced_by_managed_entry',policy_file='management/execution_policy.json')
    project.save(ROOT/'management/project.yaml',cfg);project.save(ROOT/'management/execution_policy.json',POLICY)
    return result

def register(spec_path):
    spec=project.load(root_path(spec_path));run_id=valid_id(spec['run_id']);files=[]
    kind=spec.get('kind','simulation')
    if kind not in ('simulation','analysis_only'):raise ValueError('Unsupported recipe kind')
    source_ref=None
    if kind=='analysis_only':
        source_id=valid_id(spec['source_run_id'])
        if source_id==run_id:raise ValueError('Analysis source cannot be itself')
        record=project.load(SPEC_ROOT/(source_id+'.yaml'))
        if not record.get('managed') or record['recipe'].get('kind','simulation')!='simulation':raise ValueError('Source must be a managed simulation')
        if record['recipe_hash']!=recipe_hash(record['recipe']):raise ValueError('Source recipe hash mismatch')
        if record['recipe']['run_id']!=source_id:raise ValueError('Source run ID mismatch')
        source_ref=dict(run_id=source_id,recipe_hash=record['recipe_hash'])
        if not spec.get('analyzer'):raise ValueError('Analysis-only run requires a dedicated analyzer')
    local=OUT/'runs'/run_id
    defaults=dict(threads=4,simulation_rss_mib=2048,simulation_virtual_mib=8192,analysis_rss_mib=512,
        analysis_virtual_mib=1024,max_output_mib=1024,simulation_wall_seconds=3600,analysis_wall_seconds=1800,queue_timeout_seconds=3600)
    defaults.update(spec.get('resources',{}))
    if any(not isinstance(v,int) or v<=0 for v in defaults.values()):raise ValueError('Resource limits must be positive integers')
    if defaults['threads']>POLICY['threads_per_simulation']:raise ValueError('Thread limit exceeds project policy')
    declared=spec['inputs']+[dict(source='scripts/management/native_summary.py',name='native_summary.py')]
    names=set()
    for row in declared:
        source=root_path(row['source']);name=row['name']
        if not re.fullmatch(r'[A-Za-z0-9_.+/-]+',name) or any(x in ('','.','..') for x in name.split('/')):raise ValueError('Unsafe package member')
        if name in names:raise ValueError('Duplicate package member')
        names.add(name)
        if source.stat().st_size>32*1024**2:raise ValueError('Source package file too large')
        files.append(dict(name=name,source=source.relative_to(ROOT).as_posix(),bytes=source.stat().st_size,sha256=project.digest(source)))
    entry=spec.get('entry',spec.get('analyzer')) if kind=='analysis_only' else spec['entry']
    if entry not in names:raise ValueError('Entry missing from package')
    analyzer=spec.get('analyzer','native_summary.py')
    if analyzer not in names:raise ValueError('Analyzer missing from package')
    if sum(f['bytes'] for f in files)>32*1024**2:raise ValueError('Input package exceeds 32 MiB')
    dependencies=[]
    for f in files:
        if not f['name'].endswith(('.scs','.sp','.cir')):continue
        text=root_path(f['source']).read_text(encoding='utf-8')
        for kind,inc,section in re.findall(r'(?m)^\s*(include|ahdl_include)\s+"([^"]+)"(?:\s+section=([^\s]+))?',text):
            normalized=posixpath.normpath(inc)
            if inc.startswith('/'):
                if not normalized.startswith(('/home/process/','/home/cadence/')):raise ValueError('Unregistered absolute include '+inc)
                dependencies.append(dict(path=inc,section=section or None,content='remote_read_only_not_copied'))
            elif posixpath.normpath(posixpath.join(posixpath.dirname(f['name']),inc)) not in names:
                raise ValueError('Relative include missing from package '+inc)
    spectre_args=spec.get('spectre_args',['+preset=cx',f"+mt={defaults['threads']}",'+lqtimeout','60','-preset_override'])
    if not all(isinstance(x,str) and re.fullmatch(r'\+preset=(?:cx|ax|mx)|\+mt=(?:[1-9]|1[0-6])|\+lqtimeout|[0-9]{1,3}|-preset_override',x) for x in spectre_args):raise ValueError('Unsupported Spectre argument; extend the reviewed allowlist first')
    if [x for x in spectre_args if x.startswith('+mt=')]!=[f"+mt={defaults['threads']}"]:raise ValueError('Declared thread count must match exactly one +mt')
    if sum(x.startswith('+preset=') for x in spectre_args)!=1:raise ValueError('Declare exactly one preset')
    recipe=dict(schema_version=1,run_id=run_id,design_id=spec['design_id'],entry=entry,analyzer=analyzer,
        files=files,resources=defaults,spectre_args=spectre_args,summary_signals=[s.lower() for s in spec.get('summary_signals',[])],
        expected_stop_s=float(spec['expected_stop_s']),qualification_scope=spec.get('qualification_scope','workflow_only'),
        source_commit=project.git('rev-parse','HEAD').strip(),oa=spec.get('oa'),oa_parity=spec.get('oa_parity','not_claimed'))
    # Keep existing v1 recipes byte-identical when no new metadata is requested.
    if source_ref:recipe.update(schema_version=2,kind='analysis_only',source=source_ref)
    if dependencies:recipe['model_dependencies']=dependencies
    if 'test_conditions' in spec:recipe['test_conditions']=spec['test_conditions']
    if not recipe['summary_signals'] or len(recipe['summary_signals'])>128:raise ValueError('Declare 1..128 summary signals')
    if not math.isfinite(recipe['expected_stop_s']) or recipe['expected_stop_s']<=0:raise ValueError('Positive finite expected_stop_s required')
    target=SPEC_ROOT/(run_id+'.yaml')
    if target.exists():
        old=project.load(target)
        recipe['source_commit']=old['recipe']['source_commit']
    h=recipe_hash(recipe)
    if target.exists():
        if old['recipe_hash']!=h:raise ValueError('Run ID inputs already registered; use a new ID for changed inputs')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        record=dict(managed=True,recipe_hash=h,recipe=recipe,remote_path=REMOTE_ROOT+'/runs/'+run_id)
        try:
            with target.open('x',encoding='utf-8') as f:yaml.safe_dump(record,f,allow_unicode=True,sort_keys=False)
        except FileExistsError:
            if project.load(target).get('recipe_hash')!=h:raise ValueError('Concurrent registration with different inputs; preserve the existing record')
    local.mkdir(parents=True,exist_ok=True)
    for f in files:
        dest=local/'inputs'/f['name'];dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if project.digest(dest)!=f['sha256']:raise ValueError('Frozen local input changed')
        else:shutil.copyfile(ROOT/f['source'],dest)
    project.save(local/'recipe.json',recipe)
    # A capped32MiB package expands under base64; allow a bounded upload without
    # relaxing execution/resource gates or automatically retrying uncertain work.
    result=rpc(dict(action='register',recipe=recipe,recipe_hash=h,files=[dict(name=f['name'],sha256=f['sha256'],base64=base64.b64encode((local/'inputs'/f['name']).read_bytes()).decode()) for f in files]),timeout=180)
    project.save(local/'registration.json',result);return result

def recipe(run_id):return project.load(SPEC_ROOT/(valid_id(run_id)+'.yaml'))['recipe']
def phase(action,run_id,queue=False):
    recp=recipe(run_id)
    if action=='submit' and recp.get('kind')=='analysis_only':raise ValueError('Analysis-only runs cannot submit a simulation; use analyze')
    result=rpc(dict(action=action,run_id=run_id,queue=queue))
    project.save(OUT/'runs'/run_id/(action+'.json'),result)
    return result
def admission(run_id,phase_name='simulation'):
    return rpc(dict(action='gate',recipe=recipe(run_id),phase=phase_name))
def collect(run_id):
    recipe(run_id);listing=rpc(dict(action='artifacts',run_id=run_id))
    dest=OUT/'runs'/run_id/'collected';dest.mkdir(parents=True,exist_ok=True)
    result=transfer(listing,dest,dict(action='fetch',run_id=run_id))
    result['state']=listing['status'];return result

def transfer(listing,dest,request):
    if shutil.disk_usage(dest).free<POLICY['local_disk_reserve_mib']*1024**2+listing['total_bytes']*2:raise RuntimeError('Insufficient local collection headroom')
    for item in listing['files']:
        p=(dest/item['name']).resolve()
        if not p.is_relative_to(dest.resolve()):raise ValueError('Unsafe artifact path')
        p.parent.mkdir(parents=True,exist_ok=True)
        # Mutable state snapshots get versioned by their content hash.
        if p.exists() and project.digest(p)!=item['sha256']:p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        if p.exists():
            if project.digest(p)!=item['sha256']:raise RuntimeError('Artifact collision')
            continue
        response=rpc(dict(request,name=item['name']),timeout=180)
        blob=base64.b64decode(response['base64'])
        if hashlib.sha256(blob).hexdigest()!=item['sha256'] or len(blob)!=item['bytes']:raise RuntimeError('Transfer checksum mismatch; retry collection only')
        with p.open('xb') as f:f.write(blob)
    project.save(dest/'collection_receipt.json',listing)
    return dict(collected_files=len(listing['files']),bytes=listing['total_bytes'],skipped=listing.get('skipped',[]),local_path=project.rel(dest))

def legacy_collect(run_id,remote_index=None):
    runs=project.load(project.RUN_INDEX)['runs']
    rec=next((r for r in runs if r['run_id']==run_id),None)
    if rec is None:raise ValueError('Unknown historical run ID; refresh inventory first')
    paths=rec['remote_paths']
    if remote_index is None:
        if len(paths)!=1:raise ValueError('Choose --remote-index from '+str(list(enumerate(paths))))
        remote_index=0
    if remote_index<0 or remote_index>=len(paths):raise ValueError('remote-index outside registered paths')
    path=paths[remote_index]
    if not path.startswith(project.REMOTE_PREFIXES[:2]) or not project.safe_remote(path):raise ValueError('Not a registered legacy root')
    listing=rpc(dict(action='legacy-list',remote_path=path))
    dest=OUT/'legacy'/run_id/hashlib.sha256(path.encode()).hexdigest()[:12];dest.mkdir(parents=True,exist_ok=True)
    return transfer(listing,dest,dict(action='legacy-fetch',remote_path=path))

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('action',choices=['storage','register','submit','run-status','analyze','collect','gate','legacy-collect'])
    p.add_argument('target',nargs='?');p.add_argument('--queue',action='store_true');p.add_argument('--phase',choices=['simulation','analysis'],default='simulation')
    p.add_argument('--remote-index',type=int)
    a=p.parse_args(argv)
    if a.action!='storage' and not a.target:p.error('target is required for '+a.action)
    if a.action=='storage':result=storage()
    elif a.action=='register':result=register(a.target)
    elif a.action=='gate':result=admission(a.target,a.phase)
    elif a.action=='collect':result=collect(a.target)
    elif a.action=='legacy-collect':result=legacy_collect(a.target,a.remote_index)
    else:result=phase('status' if a.action=='run-status' else a.action,a.target,a.queue)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':main()
