"""Read-only source/server/OA inventory; generated registries are local only.

No run submission, waveform parsing, source edits, OA writes or data deletion.
Local Python supports local/check/status; workspace bridge Python supports OA.
"""
from __future__ import annotations
import argparse
import base64
import collections
import contextlib
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import time

import yaml

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/'management'
INV=REG/'inventory'
OUT=ROOT/'output/project_management'
RUN_INDEX=REG/'runs/index.yaml'
CELL_INDEX=REG/'cells.yaml'
REMOTE_PREFIXES=('/home/chenzc_intern25/TSMC28/llm_IO/','/tmp/virtuoso_bridge_chenzc_intern25/90590/')
META_NAMES={'launch.json','context.json','result.json','recovered_result.json','reduced_receipt.json','reduction.json','run.json','remote.json','analysis.json'}

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def load(p):
    with Path(p).open(encoding='utf-8-sig') as f:
        return json.load(f) if str(p).endswith('.json') else yaml.safe_load(f)
def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.json':text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    else:text=yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=120)
    p.write_text(text,encoding='utf-8',newline='\n')
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def csvsave(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def csvread(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8')
def rel(p):return p.relative_to(ROOT).as_posix()
def uid(local_case):return 'legacy-'+hashlib.sha256(local_case.encode()).hexdigest()[:16]
def directory_scope(path,known,catalog):
    if path=='/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28':return 'project_OA'
    if path in known or any(p.startswith(path+'/') for p in known):return 'registered_run_or_container'
    if any(x.get('path')==path and x.get('name')!='SAR_ADC_T28' for x in catalog):return 'other_library_read_only'
    name=PurePosixPath(path).name
    if name.startswith('virtuoso_bridge_') or name in {'screenshots','x11'}:return 'bridge_runtime'
    if name.startswith('.'):return 'cadence_session_support_read_only'
    return 'unresolved_shared_workspace_directory'
def safe_remote(value):
    return isinstance(value,str) and value.startswith(REMOTE_PREFIXES) and '..' not in PurePosixPath(value).parts and not any(c in value for c in ['\n','\r','\x00'])
def remote_references(data):
    found=set()
    def walk(x,key=''):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,str(k))
        elif isinstance(x,list):
            for v in x:walk(v,key)
        elif isinstance(x,str):
            if key.lower() in {'remote','remote_dir','remote_path','remote_work_dir','remote_workdir','work_dir','workdir','scratch','run_dir','remote_root'} and safe_remote(x):found.add(x.rstrip('/'))
            elif key in {'command','spectre_command'}:
                # Register paths, never retain commands or environment values.
                for p in re.findall(r'(?:/tmp/virtuoso_bridge_chenzc_intern25/90590/|/home/chenzc_intern25/TSMC28/llm_IO/)[A-Za-z0-9_./+-]+',x):
                    if safe_remote(p):
                        q=PurePosixPath(p)
                        found.add(str(q.parent if q.suffix in {'.scs','.out','.pid'} else q))
    walk(data)
    return sorted(found)
def snapshot_patch(**changes):
    path=INV/'snapshot.json';s=load(path) if path.exists() else {'schema_version':1}
    s.update(changes);save(path,s)

def merge_observations(index,data):
    observed={r['path']:r for r in data['directories']}
    for row in index['runs']:
        row['remote_observations']=[dict(path=p,exists=observed[p].get('exists'),exit_code=observed[p].get('exit_code'),
            raw_present=observed[p].get('raw_present'),at_utc=data['observed_at_utc']) for p in row['remote_paths'] if p in observed]
        if any(x['exit_code']=='0' for x in row['remote_observations']):row['native_execution']='exit_0_observed'
    return index

def local_inventory():
    INV.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    tracked=set(filter(None,git('ls-files','-z').split('\0')))
    untracked=set(filter(None,git('ls-files','--others','--exclude-standard','-z').split('\0')))
    dirty=set()
    for item in git('status','--porcelain=v1','-z').split('\0'):
        if item:dirty.add(item[3:])
    rows=[]
    for name in sorted(tracked|untracked):
        if name.startswith(('management/inventory/','management/runs/')) or name in {'management/cells.yaml','management/STATUS.md'}:continue
        p=ROOT/name;present=p.is_file() and not p.is_symlink()
        role='design_or_workflow_source'
        if name.startswith('Obsidian_docs/'):role='user_review_notes'
        elif name.startswith('verification/'):role='verification_evidence_or_definition'
        elif name.startswith('docs/'):role='engineering_documentation'
        elif name.startswith('plan/'):role='task_plan_or_log'
        elif name.startswith('virtuoso/'):role='OA_reference_or_export_placeholder'
        rows.append(dict(path=name,root=name.split('/')[0],role=role,
            git_state='tracked' if name in tracked else 'untracked',dirty=name in dirty,
            present=present,bytes=p.stat().st_size if present else 0,sha256=digest(p) if present else ''))
    csvsave(INV/'local_files.csv',rows,list(rows[0]))
    output_rows=[];metadata=[];skipped=[]
    for group in sorted((ROOT/'output').iterdir()):
        if not group.is_dir() or group.is_symlink() or group.name=='project_management':continue
        count=total=0
        for parent,dirs,files in os.walk(group,followlinks=False):
            dirs[:]=sorted(d for d in dirs if not (Path(parent)/d).is_symlink() and d not in {'.venv','node_modules','__pycache__'})
            for fn in sorted(files):
                p=Path(parent)/fn
                try:
                    if p.is_symlink():continue
                    size=p.stat().st_size;total+=size;count+=1
                    if fn in META_NAMES:
                        if size<=8*1024**2:metadata.append(p)
                        else:skipped.append(dict(path=rel(p),reason='metadata_over_8MiB'))
                except OSError as e:skipped.append(dict(path=rel(p),reason=type(e).__name__))
        output_rows.append(dict(path=rel(group),files=count,bytes=total,role='generated_evidence',cleanup_status='requires_separate_review'))
    csvsave(INV/'local_outputs.csv',output_rows,['path','files','bytes','role','cleanup_status'])
    grouped={};errors=[]
    for p in metadata:
        try:data=load(p)
        except (OSError,ValueError,yaml.YAMLError) as e:errors.append(dict(path=rel(p),error=type(e).__name__));continue
        if not isinstance(data,dict):continue
        # Ignore observer-specific exports with no run identity or recipe.
        if not any(k in data for k in ['remote','metadata','DUT_sha256','deck_sha256','native_exit','spectre_args','state','pid','ok','run_id']):continue
        folder=rel(p.parent);row=grouped.setdefault(folder,dict(run_id=uid(folder),local_case=folder,
            group=folder.split('/')[1],case=p.parent.name,metadata=[],remote_paths=[],hashes={},
            native_execution='unknown',analysis='unknown',verdict='not_inferred',oa_parity='not_inferred'))
        row['metadata'].append(rel(p));row['remote_paths']=sorted(set(row['remote_paths'])|set(remote_references(data)))
        for key in ['DUT_sha256','deck_sha256','frozen_DUT_sha256']:
            if isinstance(data.get(key),str):row['hashes'][key]=data[key]
        if 'native_exit' in data:
            row['native_execution']='exit_0_recorded' if data['native_exit']==0 else 'nonzero_exit_recorded'
        if data.get('reduction_exit')==0:row['analysis']='reduction_receipt_present'
        if p.name in {'result.json','recovered_result.json'}:
            row.setdefault('transport_receipts',[]).append(dict(path=rel(p),ok=data.get('ok')))
    runs=sorted(grouped.values(),key=lambda x:x['local_case'])
    for row in runs:
        if row['group']=='sar8_stress_closure':row['design_id']='sar8_l90_mmain2_stress_screen'
        elif row['group']=='sar8_idle_performance':row['design_id']='sar8_idle_reset'
        elif row['group']=='sar8_r4_performance':row['design_id']='sar8_r4_original'
        else:row['design_id']=None
        row['retention']='protected_pending_review' if row['group'] in {'sar8_stress_closure','sar8_r4_performance','sar8_idle_performance','b_short_acceptance'} else 'unreviewed_historical_evidence'
        receipt=ROOT/'verification'/row['group']/(row['case']+'_stream_receipt.json')
        analysis=ROOT/'verification'/row['group']/(row['case']+'_stream_analysis.json')
        if receipt.exists() and analysis.exists():
            row['analysis']='stream_analysis_evidence_present'
            row['analysis_evidence']=[rel(receipt),rel(analysis)]
    index=dict(schema_version=1,observed_at_utc=now(),scope='legacy metadata registration, not requalification',runs=runs,
        metadata_errors=errors,skipped=skipped)
    if (INV/'server.json').exists():merge_observations(index,load(INV/'server.json'))
    save(RUN_INDEX,index)
    # Give the active four cases explicit immutable-input manifests. Mutable
    # execution observations stay in the shared index, not copied into recipes.
    for row in runs:
        if row['group']!='sar8_stress_closure':continue
        folder=ROOT/row['local_case'];ctx=load(folder/'context.json')
        recipe_path=REG/'runs'/(row['run_id']+'.yaml')
        recipe=dict(schema_version=1,run_id=row['run_id'],design_id=row['design_id'],
            local_case=row['local_case'],remote_paths=row['remote_paths'],source_of_inputs=rel(folder/'context.json'),
            context_sha256=digest(folder/'context.json'),hashes=row['hashes'],
            test_conditions={k:ctx.get(k) for k in ['corner','vdd','temperature_c','stop_ns','frames','input_diff_v','rg_parallel_factor']},
            solver_requested=ctx.get('spectre_args'),saved_signal_count=len(ctx.get('saved_signals',[])),
            observation_index='management/runs/index.yaml',oa_parity='not_promoted',retention='protected_pending_review')
        if recipe_path.exists() and load(recipe_path)['context_sha256']!=recipe['context_sha256']:
            errors.append(dict(path=rel(recipe_path),error='registered_input_changed_preserved_previous_recipe'))
        else:save(recipe_path,recipe)
    save(RUN_INDEX,index)
    snapshot_patch(local_observed_at_utc=now(),source_commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),
        local_files=len(rows),missing_tracked=sum(not r['present'] and r['git_state']=='tracked' for r in rows),
        local_output_roots=len(output_rows),local_output_bytes=sum(r['bytes'] for r in output_rows),registered_local_cases=len(runs))
    print('LOCAL',len(rows),'source records,',len(output_rows),'output roots,',len(runs),'legacy cases',flush=True)

SERVER_CODE=r'''from __future__ import print_function
import os,sys,json,stat,time,resource,subprocess
os.nice(10)
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
cfg=json.load(sys.stdin);start=time.time();deadline=start+110
prefixes=('/home/chenzc_intern25/TSMC28/llm_IO/','/tmp/virtuoso_bridge_chenzc_intern25/90590/')
def valid(p):return p.startswith(prefixes) and '..' not in p.split('/') and '\x00' not in p
def tiny(p):
 try:
  with open(p) as f:return f.read(2048).strip()
 except IOError:return None
def scan(path):
 result=dict(path=path,exists=os.path.exists(path),symlink=os.path.islink(path),bytes=0,files=0,complete=True,raw_bytes=0)
 if not result['exists']:return result
 if os.path.islink(path) or not os.path.isdir(path):result['complete']=False;result['reason']='not_regular_directory';return result
 resolved=os.path.realpath(path)
 if not valid(resolved):result['complete']=False;result['reason']='resolved_outside_scope';return result
 result['resolved_path']=resolved
 for parent,dirs,files in os.walk(path,followlinks=False):
  if time.time()>deadline:result['complete']=False;result['reason']='metadata_time_budget';break
  dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
  for fn in files:
   p=os.path.join(parent,fn)
   try:
    s=os.lstat(p)
    if not stat.S_ISREG(s.st_mode):continue
    result['bytes']+=s.st_size;result['files']+=1
    if fn.endswith(('.tran.tran','.psf','.raw')):result['raw_bytes']+=s.st_size
   except OSError:result['complete']=False
 result['exit_code']=tiny(path+'/exit_code')
 result['reduce_exit']=tiny(path+'/reduce_exit')
 result['native_log_status']=tiny(path+'/test.raw/logStatus')
 result['raw_present']=result['raw_bytes']>0
 return result
workspace='/home/chenzc_intern25/TSMC28/llm_IO'
discovered=[]
for base in [workspace,'/tmp/virtuoso_bridge_chenzc_intern25/90590']:
 try:
  for name in sorted(os.listdir(base)):
   p=base+'/'+name
   if os.path.isdir(p) and not os.path.islink(p):discovered.append(dict(path=p,name=name,kind='shallow_directory_observation'))
 except OSError:pass
rows=[]
for p in cfg['paths']:
 assert valid(p),p
 if time.time()>deadline:rows.append(dict(path=p,exists=None,complete=False,reason='metadata_time_budget'));continue
 rows.append(scan(p))
mem={s.split(':')[0]:s.split(':')[1].strip() for s in open('/proc/meminfo')}
resources={k:mem[k] for k in ['MemTotal','MemAvailable','SwapTotal','SwapFree','Cached','AnonPages']}
usage=[]
for path in [workspace,'/tmp','/server_local_ssd']:
 try:
  st=os.statvfs(path);usage.append(dict(path=path,available_bytes=st.f_bavail*st.f_frsize,total_bytes=st.f_blocks*st.f_frsize))
 except OSError:pass
proc=subprocess.check_output(['ps','-u','chenzc_intern25','-o','pid,ppid,stat,etime,pcpu,rss,comm','--sort=-rss']).decode().splitlines()[:16]
mounts=[s.strip() for s in open('/proc/mounts') if s.split()[1] in [workspace,'/home/chenzc_intern25','/','/server_local_ssd']]
print(json.dumps(dict(host=subprocess.check_output(['hostname']).decode().strip(),observed_epoch=time.time(),
 directories=rows,shallow_directories=discovered,resources=resources,filesystems=usage,processes=proc,mounts=mounts,
 duration_seconds=time.time()-start,read_only=True)))
'''

def server_inventory():
    index=load(RUN_INDEX);paths=sorted({p for r in index['runs'] for p in r['remote_paths'] if safe_remote(p)})
    # Scan overlapping trees only once. Exact descendants remain explicitly
    # registered and are queried separately when they are individual run paths.
    OUT.mkdir(parents=True,exist_ok=True);stamp=str(int(time.time()))
    payload=OUT/('server_input_'+stamp+'.json');save(payload,dict(paths=paths))
    command='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(SERVER_CODE.encode()).decode()+"'))")
    args=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',command]
    stdout=OUT/('server_'+stamp+'.json');stderr=OUT/('server_'+stamp+'.stderr')
    with payload.open('rb') as inp,stdout.open('wb') as out,stderr.open('wb') as err:
        try:rc=subprocess.run(args,stdin=inp,stdout=out,stderr=err,timeout=150).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:
        save(INV/'server_access.json',dict(at_utc=now(),status='failed',returncode=rc,raw_output=rel(stdout)))
        raise RuntimeError('Server inventory failed; retained diagnostic '+rel(stderr))
    data=load(stdout);assert data['host']=='thu-wei' and data['read_only']
    data['observed_at_utc']=datetime.fromtimestamp(data['observed_epoch'],timezone.utc).isoformat(timespec='seconds')
    save(INV/'server.json',data)
    refs=collections.defaultdict(list)
    for r in index['runs']:
        for p in r['remote_paths']:refs[p].append(r['run_id'])
    rows=[]
    for r in data['directories']:
        rows.append(dict(path=r['path'],exists=r.get('exists'),bytes=r.get('bytes'),raw_bytes=r.get('raw_bytes'),
            files=r.get('files'),complete=r.get('complete'),exit_code=r.get('exit_code'),reduce_exit=r.get('reduce_exit'),
            run_ids=' '.join(refs[r['path']]),observation='exact_metadata_scan'))
    known=set(refs)
    catalog=load(CELL_INDEX).get('library_catalog',[]) if CELL_INDEX.exists() else []
    for row in rows:row['scope']=directory_scope(row['path'],known,catalog)
    for r in data['shallow_directories']:
        if r['path'] not in known:rows.append(dict(path=r['path'],exists=True,bytes='',raw_bytes='',files='',complete=False,exit_code='',reduce_exit='',run_ids='',observation='shallow_only',scope=directory_scope(r['path'],known,catalog)))
    csvsave(INV/'remote_directories.csv',rows,['path','scope','exists','bytes','raw_bytes','files','complete','exit_code','reduce_exit','run_ids','observation'])
    save(RUN_INDEX,merge_observations(index,data))
    snapshot_patch(server_observed_at_utc=data['observed_at_utc'],remote_exact_paths=len(data['directories']),remote_shallow_paths=len(data['shallow_directories']),remote_metadata_complete=all(r.get('complete') for r in data['directories']))
    print('SERVER',len(data['directories']),'exact paths,',len(data['shallow_directories']),'shallow paths',flush=True)

DISPLAY_CODE=r'''from __future__ import print_function
import os,json,subprocess,time
rows=[]
for pid in os.listdir('/proc'):
 if not pid.isdigit():continue
 base='/proc/'+pid
 try:
  if os.stat(base).st_uid!=os.getuid():continue
  with open(base+'/comm') as f:comm=f.read().strip()
  if comm not in ['virtuoso','Xvnc','Xtigervnc','Xorg','Xvfb','xterm','gnome-terminal-','mate-terminal','xfce4-terminal']:continue
  env={}
  try:
   with open(base+'/environ','rb') as f:
    for entry in f.read().split(b'\x00'):
     k,sep,v=entry.partition(b'=')
     if k in [b'DISPLAY',b'XAUTHORITY']:env[k.decode()]=v.decode('utf-8','replace')
  except IOError:env['inspection']='permission_denied'
  try:cwd=os.readlink(base+'/cwd')
  except OSError:cwd=None
  rows.append(dict(pid=int(pid),comm=comm,display=env.get('DISPLAY'),xauthority_path=env.get('XAUTHORITY'),cwd=cwd,inspection=env.get('inspection','read')))
 except OSError:pass
print(json.dumps(dict(observed_epoch=time.time(),host=subprocess.check_output(['hostname']).decode().strip(),
 processes=rows,x_sockets=sorted(os.listdir('/tmp/.X11-unix')) if os.path.isdir('/tmp/.X11-unix') else [],
 ssh_shell_display=os.getenv('DISPLAY'),read_only=True)))
'''

def display_inventory():
    OUT.mkdir(parents=True,exist_ok=True);stamp=str(int(time.time()))
    code='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(DISPLAY_CODE.encode()).decode()+"'))")
    output=OUT/('display_'+stamp+'.json');error=OUT/('display_'+stamp+'.stderr')
    with output.open('wb') as out,error.open('wb') as err:
        try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','thu-wei',code],stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=40).returncode
        except subprocess.TimeoutExpired:rc=124
    assert rc==0,'Display read failed; inspect '+rel(error)
    d=load(output);d['observed_at_utc']=datetime.fromtimestamp(d['observed_epoch'],timezone.utc).isoformat(timespec='seconds')
    save(INV/'display.json',d);print(json.dumps(d,ensure_ascii=False,indent=2))

def oa_inventory():
    from virtuoso_bridge import VirtuosoClient,decode_skill_output
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'bridge_capture.log').open('a',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        client=VirtuosoClient.from_env(profile='t28_io',timeout=20,log_to_ciw=False)
        visible=client.library.list(timeout=20)
        info=client.library.get('SAR_ADC_T28',timeout=20)
        assert info.path=='/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28' and info.technology_library=='tsmcN28'
        # DD metadata listing copied from the supported basic/04 example.
        result=client.execute_skill('''let((lib out views)
 lib=ddGetObj("SAR_ADC_T28") out=""
 foreach(cell lib~>cells
  views=""
  foreach(view cell~>views views=strcat(views view~>name " "))
  out=strcat(out sprintf(nil "%s|views=%s\\n" cell~>name views)))
 out)''',timeout=30)
        assert result.status.value=='success',result.errors
        actual={}
        for line in decode_skill_output(result.output or '').splitlines():
            name,sep,views=line.partition('|views=');assert sep and name not in actual
            actual[name]=sorted(views.split())
        assert actual
        windows=client.list_windows(timeout=15)
        catalog=[]
        for name in sorted(visible):
            try:
                item=client.library.get(name,timeout=10)
                catalog.append(dict(name=name,path=item.path,technology_library=item.technology_library,
                    scope='project' if name=='SAR_ADC_T28' else 'visible_read_only_reference',cell_inventory_in_scope=name=='SAR_ADC_T28'))
            except Exception as e:catalog.append(dict(name=name,scope='visible_metadata_unresolved',error_type=type(e).__name__,cell_inventory_in_scope=False))
    legacy=load(ROOT/'virtuoso/cell_manifest.yaml')['cells']
    stamp=now();cells=[]
    for name in sorted(set(actual)|set(legacy)):
        old=legacy.get(name,{})
        cells.append(dict(library='SAR_ADC_T28',cell=name,actual_views=actual.get(name,[]),observed_exists=name in actual,
            legacy_registered=name in legacy,legacy_role=old.get('role'),legacy_status=old.get('status'),
            role='testbench' if name.startswith('tb_') else 'design_or_model',group=cell_group(name),
            ownership='project_OA',qualification='not_inferred_from_presence',observed_at_utc=stamp))
    data=dict(schema_version=1,observation='live_bridge_DD_metadata',observed_at_utc=stamp,
        library=dict(name=info.name,path=info.path,technology_library=info.technology_library),
        visible_libraries=sorted(visible),library_catalog=catalog,
        planned_work_library=dict(name='SAR_ADC_T28_WORK',visible='SAR_ADC_T28_WORK' in visible,created_by_inventory=False),
        actual_count=len(actual),cells=cells,window_count=len(windows),oa_mutations=[])
    save(CELL_INDEX,data)
    csvsave(INV/'oa_cells.csv',[dict(library=r['library'],cell=r['cell'],group=r['group'],views=' '.join(r['actual_views']),
        exists=r['observed_exists'],legacy_registered=r['legacy_registered'],legacy_role=r['legacy_role'] or '') for r in cells],
        ['library','cell','group','views','exists','legacy_registered','legacy_role'])
    listing=['# Virtuoso 单元清单','',f'当前 CIW 读回：`{stamp}`。项目库 `{info.name}`，技术库 `{info.technology_library}`。','',
        '分类依据单元名，仅用于导航。旧 manifest 的状态作为历史描述保留，不代表本次重新验收。','']
    for group in sorted({r['group'] for r in cells}):
        listing += ['## '+group,'','| Cell | 当前 view | 旧登记 |','| --- | --- | --- |']
        for r in cells:
            if r['group']!=group:continue
            state='已登记' if r['legacy_registered'] else '旧清单漏登，现已收录'
            views=' '.join(r['actual_views']) if r['observed_exists'] else '当前库未找到'
            listing.append(f"| `{r['cell']}` | {views} | {state} |")
        listing.append('')
    listing += ['## 可见库元数据','','只对 `SAR_ADC_T28` 清点 cell；其他库保持只读。','',
        '| Library | 路径 | 技术库 |','| --- | --- | --- |']
    for item in catalog:listing.append(f"| `{item['name']}` | {item.get('path','元数据未解析')} | {item.get('technology_library') or '未绑定或不适用'} |")
    (INV/'oa_cells.md').write_text('\n'.join(listing)+'\n',encoding='utf-8')
    save(INV/'oa_access.json',dict(at_utc=stamp,status='live_read_success'))
    snapshot_patch(oa_observed_at_utc=stamp,oa_observation='live_bridge_DD_metadata',actual_cells=len(actual),
        actual_not_in_legacy=sorted(set(actual)-set(legacy)),legacy_missing_from_live=sorted(set(legacy)-set(actual)))
    print('OA',len(actual),'actual cells,',len(visible),'visible libraries',flush=True)

def cell_group(name):
    if name.startswith(('sar8p_','sar_adc8_join_r4','tb_sar_adc8_join_r4')):return 'R4 原生整机与驱动'
    if name.startswith(('sar8j_','sar_adc8_join_r','tb_sar_adc8_join_r')):return 'R0至R3 合龙历史'
    if name.startswith(('sar8s_','sar8a_','sar_logic_8b','tb_sar8a_','tb_sar8s_')):return '异步控制与数字模块'
    if name.startswith(('cdac10_dr','cdac10_dualrail','tb_cdac10_dr')):return '独立十位双轨实验'
    if name.startswith(('cdac8_','tb_cdac8_')):return '八位CDAC与测试台'
    if 'strongarm' in name:return '比较器与接口'
    if 'bootstrap' in name or 'gmain' in name or 'pgate' in name:return '采样开关与历史诊断'
    if 'macro' in name:return '宏模型'
    if name.startswith('tb_'):return '其他测试台与表征'
    return '其他历史单元待分类'

def dependency_inventory():
    from virtuoso_bridge import VirtuosoClient
    current=load(CELL_INDEX);assert current['observation']=='live_bridge_DD_metadata'
    actual={r['cell']:r['actual_views'] for r in current['cells'] if r['observed_exists']}
    roots=['sar_adc8_join_r3','sar_adc8_join_r4','tb_sar_adc8_join_r3','tb_sar_adc8_join_r4']
    queue=list(roots);seen=set();records={};errors=[];started=time.monotonic()
    OUT.mkdir(exist_ok=True)
    with (OUT/'bridge_dependencies.log').open('a',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        client=VirtuosoClient.from_env(profile='t28_io',timeout=20,log_to_ciw=False)
        info=client.library.get('SAR_ADC_T28',timeout=15)
        assert info.path==current['library']['path'] and info.technology_library=='tsmcN28'
        while queue:
            name=queue.pop(0)
            if name in seen:continue
            seen.add(name)
            if len(seen)>90 or time.monotonic()-started>180:
                errors.append(dict(cell=name,reason='bounded_dependency_walk_limit'));break
            if 'schematic' not in actual.get(name,[]):
                records[name]=dict(views=actual.get(name,[]),masters=[],read='terminal_model_or_missing_schematic');continue
            try:
                data=client.schematic.read('SAR_ADC_T28',name,include_positions=False,timeout=20)
                counts=collections.Counter()
                for inst in data.get('instances',[]):
                    assert inst.get('lib') and inst.get('cell'), 'Unexpected supported-reader instance shape'
                    counts[(inst['lib'],inst['cell'])]+=1
                masters=[dict(library=lib,cell=cell,count=n) for (lib,cell),n in sorted(counts.items())]
                records[name]=dict(views=actual[name],instance_count=len(data.get('instances',[])),masters=masters,read='supported_schematic_reader')
                queue.extend(m['cell'] for m in masters if m['library']=='SAR_ADC_T28' and m['cell'] not in seen)
            except Exception as e:errors.append(dict(cell=name,reason=type(e).__name__,message=str(e)[:250]))
    closures={}
    for root in roots:
        pending=[root];closure=set()
        while pending:
            name=pending.pop()
            if name in closure:continue
            closure.add(name)
            pending.extend(m['cell'] for m in records.get(name,{}).get('masters',[]) if m['library']=='SAR_ADC_T28')
        closures[root]=sorted(closure)
    data=dict(observed_at_utc=now(),library='SAR_ADC_T28',roots=roots,cells=records,closures=closures,errors=errors,
        completeness='complete_for_selected_schematic_roots' if not errors and not queue else 'partial',
        qualification='master dependency observation only; no netlist parity, connectivity/ERC or device validation',oa_mutations=[])
    save(INV/'dependencies.yaml',data)
    for row in current['cells']:
        row['referenced_by_selected_roots']=[root for root,closure in closures.items() if row['cell'] in closure]
        row['dependency_observed_at_utc']=data['observed_at_utc']
    save(CELL_INDEX,current)
    snapshot_patch(dependencies_observed_at_utc=data['observed_at_utc'],dependency_cells=len(records),dependency_completeness=data['completeness'])
    print('DEPENDENCIES',len(records),'cells;',len(errors),'errors',flush=True)

def issues_and_status(refresh=True):
    s=load(INV/'snapshot.json');issues=[]
    if refresh and CELL_INDEX.exists() and (INV/'dependencies.yaml').exists():
        cells=load(CELL_INDEX);deps=load(INV/'dependencies.yaml')
        for row in cells['cells']:
            row['referenced_by_selected_roots']=[root for root,closure in deps['closures'].items() if row['cell'] in closure]
            row['dependency_observed_at_utc']=deps['observed_at_utc']
        save(CELL_INDEX,cells)
    for r in csvread(INV/'local_files.csv'):
        if r['present']=='False':issues.append(dict(kind='missing_local_tracked_file',path=r['path'],action='preserve_user_change'))
    if CELL_INDEX.exists():
        c=load(CELL_INDEX)
        if c['observation']!='live_bridge_DD_metadata':issues.append(dict(kind='live_OA_capture_pending',action='load_bridge_in_CIW_then_inventory_oa'))
        for r in c['cells']:
            if r['observed_exists'] and not r['legacy_registered']:issues.append(dict(kind='OA_unregistered_in_legacy',cell=r['cell'],action='registered_in_management_cells'))
            elif not r['observed_exists'] and r['legacy_registered']:issues.append(dict(kind='legacy_cell_not_observed',cell=r['cell'],action='do_not_treat_as_existing'))
    else:issues.append(dict(kind='live_OA_capture_pending',action='load_bridge_in_CIW_then_inventory_oa'))
    if (INV/'server.json').exists():
        d=load(INV/'server.json');known={r['path'] for r in d['directories']}
        for r in d['directories']:
            if r.get('exists') is False:issues.append(dict(kind='recorded_remote_path_missing',path=r['path'],action='keep_historical_reference'))
            elif not r.get('complete'):issues.append(dict(kind='remote_scan_incomplete',path=r['path'],action='metadata_only_followup'))
        catalog=load(CELL_INDEX).get('library_catalog',[]) if CELL_INDEX.exists() else []
        for r in d['shallow_directories']:
            if directory_scope(r['path'],known,catalog)=='unresolved_shared_workspace_directory':issues.append(dict(kind='remote_root_unmapped',path=r['path'],action='outside_project_or_unresolved_keep_read_only'))
    else:issues.append(dict(kind='server_capture_pending'))
    if RUN_INDEX.exists():
        for item in load(RUN_INDEX).get('metadata_errors',[]):issues.append(dict(kind='metadata_registration_error',**item))
    issues.append(dict(kind='resource_policy_not_enforced_by_legacy_launchers',action='unified_submit_layer_next_phase'))
    issues.append(dict(kind='new_SSD_run_root_not_allocated',action='verify_storage_ownership_before_new_runs'))
    if refresh:
        save(INV/'issues.yaml',dict(observed_at_utc=now(),issues=issues))
        render_status(s,issues)
    print(json.dumps(dict(snapshot={k:v for k,v in s.items() if not isinstance(v,list)},issue_counts=dict(collections.Counter(x['kind'] for x in issues))),ensure_ascii=False,indent=2))

def render_status(snapshot,issues):
    def china_time(value):
        return datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S') if value else '未读取'
    lines=['# 项目管理状态','',
        '统一登记本地源文件、远端仿真目录和 Virtuoso 单元。各端观察时间分别记录；清单不代替设计验收。','',
        '| 范围 | 已登记 | 观察时间 北京时间 |','| --- | ---: | --- |',
        f"| 本地源文件记录 | {snapshot.get('local_files',0)} | {china_time(snapshot.get('local_observed_at_utc'))} |",
        f"| 本地生成物目录 | {snapshot.get('local_output_roots',0)} | 同上 |",
        f"| 历史运行元数据记录 | {snapshot.get('registered_local_cases',0)} | 同上 |",
        f"| 远端精确引用路径 | {snapshot.get('remote_exact_paths',0)} | {china_time(snapshot.get('server_observed_at_utc'))} |",
        f"| Virtuoso 实际单元 | {snapshot.get('actual_cells','待读取')} | {china_time(snapshot.get('oa_observed_at_utc'))} |",'']
    if CELL_INDEX.exists():lines += ['OA 观察方式：`'+load(CELL_INDEX)['observation']+'`。','']
    lines += ['## 当前设计登记','',
        '| 版本 | 定位 | OA 对应情况 |','| --- | --- | --- |']
    for d in load(REG/'designs.yaml')['designs']:
        oa=d.get('oa');label='/'.join(oa.values()) if oa else '网表候选或独立实验，未登记为已同步 OA'
        lines.append(f"| `{d['id']}` | {d['role']} | {label} |")
    lines += ['', '版本采用情况与各项验证结论见 [designs.yaml](designs.yaml)。没有因本次盘点提升任何基线。','',
        '## 需要处理的差异','', '| 项目 | 数量 |','| --- | ---: |']
    labels={'missing_local_tracked_file':'本地已删除的受控文件', 'OA_unregistered_in_legacy':'旧 manifest 漏登的实际 cell',
        'legacy_cell_not_observed':'旧登记存在但当前库未找到', 'recorded_remote_path_missing':'当前未找到的历史远端路径',
        'remote_root_unmapped':'尚未关联实验的浅层目录', 'resource_policy_not_enforced_by_legacy_launchers':'旧提交器尚未执行统一资源策略',
        'new_SSD_run_root_not_allocated':'新 SSD 运行根目录待配置', 'live_OA_capture_pending':'当前 CIW 读回待完成'}
    for kind,n in sorted(collections.Counter(x['kind'] for x in issues).items()):lines.append(f'| {labels.get(kind,kind)} | {n} |')
    lines += ['', '历史远端路径未找到不等于仿真失败；用户已删除或重组的笔记原样保留。',
        '浅层发现的未关联目录先登记，不自动认领或清理。远端路径可能互相包含，体积不可直接相加。','',
        '## 清单入口','',
        '- [本地文件](inventory/local_files.csv)：Git 状态、用途、大小、散列；不包含环境和大型原始波形。',
        '- [本地输出](inventory/local_outputs.csv)：只统计文件元数据，不解析波形。',
        '- [服务器目录](inventory/remote_directories.csv)：存在性、体积、运行引用和退出码。',
        '- [Virtuoso 单元清单](inventory/oa_cells.md)、[机器登记](cells.yaml)：实际 view、旧登记用途和存在性差异。',
        '- [单元表格](inventory/oa_cells.csv)、[R3/R4依赖](inventory/dependencies.yaml)。',
        '- [实验索引](runs/index.yaml)：本地案例与远端路径的关联；当前四组另有输入清单。',
        '- [完整差异](inventory/issues.yaml)、[资源与权责](project.yaml)、[使用说明](README.md)。','',
        '当前实现覆盖盘点、登记和检查。统一提交/收集执行器与 SSD 运行根目录配置仍待后续落实。','']
    (REG/'STATUS.md').write_text('\n'.join(lines),encoding='utf-8')

def check():
    s=load(INV/'snapshot.json');local=csvread(INV/'local_files.csv');runs=load(RUN_INDEX)['runs']
    assert len(local)==s['local_files'] and len({r['path'] for r in local})==len(local)
    assert len({r['run_id'] for r in runs})==len(runs) and len({r['local_case'] for r in runs})==len(runs)
    assert all(r['run_id']==uid(r['local_case']) for r in runs)
    for r in runs:
        assert all(safe_remote(p) for p in r['remote_paths'])
        assert all((ROOT/p).is_file() for p in r['metadata'])
        assert r['verdict']=='not_inferred'
    cfg=load(REG/'project.yaml');assert cfg['roots']['new_run_root'] is None
    assert cfg['resource_policy']['concurrent_simulations']==1
    for d in load(REG/'designs.yaml')['designs']:
        for p in d.get('evidence',[]):assert (ROOT/p).exists(),p
    if CELL_INDEX.exists():
        c=load(CELL_INDEX);assert c['oa_mutations']==[]
        assert len({r['cell'] for r in c['cells']})==len(c['cells'])
        assert c['actual_count']==sum(r['observed_exists'] for r in c['cells'])
        if c['observation']=='live_bridge_DD_metadata':assert c['library']['technology_library']=='tsmcN28'
    for p in sorted((REG/'runs').glob('legacy-*.yaml')):
        recipe=load(p);assert digest(ROOT/recipe['source_of_inputs'])==recipe['context_sha256'],str(p)
    if (INV/'dependencies.yaml').exists():
        d=load(INV/'dependencies.yaml');assert d['oa_mutations']==[]
        assert d['completeness']=='complete_for_selected_schematic_roots' and not d['errors']
        for closure in d['closures'].values():assert set(closure)<=set(d['cells'])
    for path in [REG/'README.md',REG/'STATUS.md',INV/'oa_cells.md']:
        if not path.exists():continue
        for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            target=match[1].split('#')[0]
            if target and '://' not in target:assert (path.parent/target).exists(),(str(path),target)
    print('REGISTRY CHECK PASS',len(local),'local files,',len(runs),'run records')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inventory','status','cells','check'])
    p.add_argument('--scope',choices=['local','server','oa','display','dependencies'],default='local')
    a=p.parse_args()
    if a.action=='inventory':
        try:
            {'local':local_inventory,'server':server_inventory,'oa':oa_inventory,'display':display_inventory,'dependencies':dependency_inventory}[a.scope]()
        except Exception as e:
            if a.scope=='oa':save(INV/'oa_access.json',dict(at_utc=now(),status='failed',error_type=type(e).__name__,message=str(e)[:800]))
            raise
        issues_and_status()
    elif a.action=='status':issues_and_status(refresh=False)
    elif a.action=='cells':
        d=load(CELL_INDEX);print(d['library']);print('actual cells',d['actual_count'])
        for r in d['cells']:
            if r['observed_exists']:print(r['cell'],' '.join(r['actual_views']))
    else:check()

if __name__=='__main__':main()
