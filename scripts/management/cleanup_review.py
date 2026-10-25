"""Read-only data census and human cleanup proposal. No deletion operation."""
import argparse,base64,collections,json,os,re,shlex,shutil,stat,subprocess,time
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'management/cleanup/2026-10-25'
TRANS=ROOT/'output/project_management/cleanup_review'
GIB=1024**3
PREFIXES=('/home/chenzc_intern25/TSMC28/llm_IO/','/tmp/virtuoso_bridge_chenzc_intern25/90590/',
    '/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/','/server_local_ssd/chenzc_intern25/simulation/')

def load(p):
    with Path(p).open(encoding='utf-8-sig') as f:return json.load(f)

def save(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def outermost(paths):
    result=[]
    for p in sorted(set(paths),key=lambda s:(len(s),s)):
        if not any(p==q or p.startswith(q+'/') for q in result):result.append(p)
    return sorted(result)

def category(p):
    s=p.lower();parts=s.replace('\\','/').split('/');name=parts[-1]
    if '__pycache__' in parts or name.endswith('.pyc'):return 'bytecode_cache'
    if any(x.startswith(('parts_v','transfer_parts')) for x in parts) or re.fullmatch(r'part_[0-9]+',name):return 'transfer_parts'
    if name.endswith(('.tar.gz','.tgz','.zip','.tar','.7z')) or name in {'transfer_tran.gz','recovered_transfer.gz'}:return 'archive'
    if name.endswith(('.tran.tran','.ac.ac','.dc.dc','.psf')):return 'native_waveform'
    if name.endswith(('.npz','.npy','.bin','.bin.gz','.pkl','.pickle')):return 'derived_waveform'
    return 'other_preserve'

def registry():
    # The bundled analysis runtime has no YAML package. Use existing project
    # Python only as the YAML reader, not as the spreadsheet-analysis engine.
    code="""import json,yaml,pathlib
r=pathlib.Path('.');read=lambda p:yaml.safe_load(p.read_text(encoding='utf-8-sig'))
print(json.dumps(dict(runs=read(r/'management/runs/index.yaml')['runs'],managed=[read(p) for p in (r/'management/runs').glob('*.yaml') if not p.name.startswith('legacy-') and p.name!='index.yaml'],project_cells=[x['cell'] for x in read(r/'management/cells.yaml')['cells'] if x['observed_exists']],designs=read(r/'management/designs.yaml'))))
"""
    return json.loads(subprocess.check_output([str(ROOT/'.venv/Scripts/python.exe'),'-c',code],cwd=ROOT))

def local_capture():
    started=time.time();rows=[];errors=[];skipped=[];roots=[];seen=set()
    for base in ['output','artifacts','virtuoso/exports','virtuoso/snapshots']:
        parent=ROOT/base
        if not parent.is_dir():continue
        children=list(parent.iterdir()) if base=='output' else [parent]
        for p in children:
            if p.name=='project_management':continue
            if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):skipped.append(str(p));continue
            if p.is_dir() or (base=='output' and p.is_file()):roots.append(p)
    for root in sorted(roots):
        row=dict(path=root.as_posix(),relative=root.relative_to(ROOT).as_posix(),bytes=0,files=0,
            categories={},large_files=[],complete=True,hardlink_bytes_not_added=0)
        counts=collections.Counter()
        def onerror(e):errors.append(dict(path=str(e.filename),error=type(e).__name__));row['complete']=False
        iterator=[(str(root.parent),[],[root.name])] if root.is_file() else os.walk(root,followlinks=False,onerror=onerror)
        for parent,dirs,files in iterator:
            if time.time()-started>90:row['complete']=False;errors.append(dict(path=str(root),error='census_time_budget'));break
            dirs[:]=[d for d in dirs if not (Path(parent)/d).is_symlink() and not (hasattr(Path(parent)/d,'is_junction') and (Path(parent)/d).is_junction())]
            for name in files:
                p=Path(parent)/name
                try:
                    s=p.lstat()
                    if not stat.S_ISREG(s.st_mode):continue
                    identity=(s.st_dev,s.st_ino)
                    if s.st_ino and identity in seen:row['hardlink_bytes_not_added']+=s.st_size;continue
                    if s.st_ino:seen.add(identity)
                    c=category(p.as_posix());row['bytes']+=s.st_size;row['files']+=1;counts[c]+=s.st_size
                    if s.st_size>=1024**2 or c=='bytecode_cache':row['large_files'].append(dict(path=p.as_posix(),bytes=s.st_size,category=c,mtime_ns=s.st_mtime_ns,nlink=s.st_nlink))
                except OSError as e:onerror(e)
        row['categories']=dict(counts);rows.append(row)
    return dict(observed_at_utc=utc(),scope='SAR ADC generated data only; excludes other E-drive projects, tools, environments, Git, OA and user data',
        disk_free_bytes=shutil.disk_usage(ROOT).free,groups=rows,errors=errors,skipped_links=skipped,
        total_bytes=sum(r['bytes'] for r in rows),size_basis='logical bytes, hardlinks counted once; Windows allocated/reclaimable bytes not measured',read_only=True)

SERVER=r'''from __future__ import print_function
import os,sys,json,time,stat,re,resource,socket
os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
cfg=json.load(sys.stdin);start=time.time();deadline=start+150;seen=set();rows=[];errors=[]
prefixes=('/home/chenzc_intern25/TSMC28/llm_IO/','/tmp/virtuoso_bridge_chenzc_intern25/90590/','/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/','/server_local_ssd/chenzc_intern25/simulation/')
def valid(p):return p.startswith(prefixes) and '..' not in p.split('/') and '\x00' not in p and '\n' not in p
def tiny(path):
 try:
  if os.path.getsize(path)>65536:return None
  return open(path).read()
 except (IOError,OSError):return None
def kind(path):
 s=path.lower();parts=s.split('/');name=parts[-1]
 if '__pycache__' in parts or name.endswith('.pyc'):return 'bytecode_cache'
 if any(x.startswith(('parts_v','transfer_parts')) for x in parts) or re.match(r'^part_[0-9]+\Z',name):return 'transfer_parts'
 if name.endswith(('.tar.gz','.tgz','.zip','.tar','.7z')) or name in ['transfer_tran.gz','recovered_transfer.gz']:return 'archive'
 if name.endswith(('.tran.tran','.ac.ac','.dc.dc','.psf')):return 'native_waveform'
 if name.endswith(('.npz','.npy','.bin','.bin.gz','.pkl','.pickle')):return 'derived_waveform'
 return 'other_preserve'
discovery=[];extra=[]
for base in ['/server_local_ssd/chenzc_intern25/simulation','/home/chenzc_intern25/TSMC28/llm_IO/simulation']:
 d=dict(path=base,exists=os.path.isdir(base),matched_project_paths=[],unassociated_entries=0)
 if d['exists']:
  assert os.path.realpath(base)==base and os.stat(base).st_uid==596
  for name in os.listdir(base):
   p=base+'/'+name
   if (name in cfg['project_cells'] or name=='SAR_ADC_T28') and os.path.isdir(p) and not os.path.islink(p):
    d['matched_project_paths'].append(p);extra.append(p)
   else:d['unassociated_entries']+=1
 discovery.append(d)
unique=[]
for p in sorted(set(cfg['paths']+extra),key=lambda s:(len(s),s)):
 if not any(p==q or p.startswith(q+'/') for q in unique):unique.append(p)
cfg['paths']=sorted(unique)
def processes():
 result=[]
 for pid in os.listdir('/proc'):
  if not pid.isdigit() or int(pid)==os.getpid():continue
  try:
   b='/proc/'+pid
   if os.stat(b).st_uid!=596:continue
   comm=open(b+'/comm').read().strip()
   cmd=open(b+'/cmdline','rb').read().replace(b'\x00',b' ').decode('utf-8','replace')
   try:cwd=os.readlink(b+'/cwd')
   except OSError:cwd=''
   refs=set(p for p in cfg['paths'] if p in cmd or cwd==p or cwd.startswith(p+'/'))
   for fd in os.listdir(b+'/fd')[:256]:
    try:
     target=os.readlink(b+'/fd/'+fd)
     refs.update(p for p in cfg['paths'] if target==p or target.startswith(p+'/'))
    except OSError:pass
   if refs:result.append(dict(pid=int(pid),comm=comm,referenced_roots=sorted(refs)))
  except (IOError,OSError):pass
 return result
before=processes()
for path in cfg['paths']:
 assert valid(path),path
 row=dict(path=path,exists=os.path.exists(path),bytes=0,allocated_bytes=0,files=0,categories={},large_files=[],complete=True,hardlink_bytes_not_added=0)
 if not row['exists']:rows.append(row);continue
 if os.path.realpath(path)!=path or os.stat(path).st_uid!=596 or not os.path.isdir(path):
  row.update(complete=False,excluded='symlink_owner_or_type');rows.append(row);continue
 def walk_error(e):row['complete']=False;errors.append(dict(path=path,error=type(e).__name__))
 for parent,dirs,files in os.walk(path,followlinks=False,onerror=walk_error):
  if time.time()>deadline:row.update(complete=False,reason='census_time_budget');break
  # A root accidentally pointing at a library is never traversed.
  if 'data.dm' in files or 'master.tag' in files or 'cdsinfo.tag' in files:
   row.update(complete=False,excluded='OA_metadata_detected');dirs[:]=[];continue
  dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
  for name in files:
   p=parent+'/'+name
   try:
    s=os.lstat(p)
    if not stat.S_ISREG(s.st_mode):continue
    identity=(s.st_dev,s.st_ino)
    if identity in seen:row['hardlink_bytes_not_added']+=s.st_size;continue
    seen.add(identity);c=kind(p);row['bytes']+=s.st_size;row['allocated_bytes']+=s.st_blocks*512;row['files']+=1
    row['categories'][c]=row['categories'].get(c,0)+s.st_size
    if s.st_size>=1024**2 or c=='bytecode_cache':row['large_files'].append(dict(path=p,bytes=s.st_size,allocated_bytes=s.st_blocks*512,category=c,mtime=s.st_mtime,nlink=s.st_nlink))
   except OSError as e:walk_error(e)
 row['native_exit_record']=tiny(path+'/exit_code');row['reduce_exit_record']=tiny(path+'/reduce_exit')
 for phase in ['simulation','analysis']:
  text=tiny(path+'/'+phase+'.state.json')
  if text:
   try:row[phase+'_status']=json.loads(text).get('status')
   except ValueError:row[phase+'_status']='unreadable_state'
 rows.append(row)
after=processes();allproc=before+after
for row in rows:row['active_references']=[p for p in allproc if row['path'] in p['referenced_roots']]
fs=[]
for path in ['/home/chenzc_intern25/TSMC28/llm_IO','/tmp','/server_local_ssd']:
 s=os.statvfs(path);fs.append(dict(path=path,free_bytes=s.f_bavail*s.f_frsize))
print(json.dumps(dict(observed_epoch=time.time(),duration_seconds=time.time()-start,groups=rows,errors=errors,filesystems=fs,discovery=discovery,read_only=True,raw_contents_read=False)))
'''

def remote_paths(reg):
    old=load(ROOT/'management/inventory/server.json');paths=set()
    for r in reg['runs']:paths.update(r['remote_paths'])
    paths.update(r['remote_path'] for r in reg['managed'] if r and r.get('managed'))
    # Named SAR8 containers only. Never sweep the whole bridge bucket or OA workspace.
    for row in old['shallow_directories']:
        if row['path'].rsplit('/',1)[-1].startswith('sar8_'):paths.add(row['path'])
    return outermost(p.rstrip('/') for p in paths if p.startswith(PREFIXES) and '..' not in p.split('/'))

def remote_capture(paths,cells):
    TRANS.mkdir(parents=True,exist_ok=True);stamp=str(time.time_ns());inp=TRANS/(stamp+'.input.json');save(inp,dict(paths=paths,project_cells=cells))
    out=TRANS/(stamp+'.output.json');err=TRANS/(stamp+'.stderr')
    cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(SERVER.encode()).decode()+"'))")
    with inp.open('rb') as i,out.open('wb') as o,err.open('wb') as e:
        try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',cmd],stdin=i,stdout=o,stderr=e,timeout=190).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:raise RuntimeError('Read-only server census failed; no writes/deletions. '+str(err)+': '+err.read_text(errors='replace')[-600:])
    result=load(out);result['observed_at_utc']=utc()
    result['server_reported_at_utc']=datetime.fromtimestamp(result['observed_epoch'],timezone.utc).isoformat(timespec='seconds')
    result['size_basis']='logical and st_blocks*512 allocated bytes; unique inode counted once; not guaranteed freed bytes'
    result['total_bytes']=sum(r['bytes'] for r in result['groups']);return result

def capture():
    reg=registry();save(DEST/'registry_snapshot.json',reg)
    local=local_capture();save(DEST/'local_census.json',local)
    remote=remote_capture(remote_paths(reg),reg['project_cells']);save(DEST/'server_census.json',remote)
    for name,data in [('local',local),('server',remote)]:
        print(name,'GiB',round(data['total_bytes']/GIB,3),'groups',len(data['groups']),'errors',len(data['errors']))
        for row in sorted(data['groups'],key=lambda r:r['bytes'],reverse=True)[:14]:print(round(row['bytes']/GIB,3),row['path'],row.get('categories'))

LABELS={
 'sar8_r4_staged':'R4 分位参考复位时序扫描', 'sar8_r4_idle':'R4 空闲段复位与恢复采样窗口',
 'sar8_r4_reset':'R4 早期先复位后采样方案', 'sar8_physical':'R4 首版管级合龙及边沿迭代',
 'sar8_simple':'8位简化异步控制与功能验证', 'b_short_acceptance':'R3 B版定向码与历史序列验收',
 'b_sine_period':'B版整周期正弦回放','b_hf_main_w':'B版高频输入主开关宽度对照','b_sine_main_w':'B版正弦主开关宽度对照',
 'r3_refgate_events':'R3 参考捕获与尖峰定位','r3_anomaly_replay':'R3 异常码字重放',
 'strongarm8_baseline':'8位 StrongARM 基线','strongarm_t28_verification':'T28 比较器性能验证',
 'cdac10_dualrail':'独立10位双轨实验（用户所有）','sar8_ref_current_probe':'参考支路端电流定位，FF冷/热',
 'sar8_physical_repair':'物理过压修复候选及器件探针','managed_execution':'统一入口回执与在研修复小结果',
 'sar8_stress_closure':'L90/Mmain2 与 Rgate/4 冷热四组对照','sar8_main_width':'Mmain 2/3/4µm 与角落验证',
 'sar8_pvt_mismatch':'首批PVT风险点与失配验证框架','sar8_ref_length':'参考开关 L30/60/90nm 漏电与Ron',
 'sar8_ref_load':'参考源负载支路定位','sar8_ref_gate_controls':'栅极保持与bit7边沿单变量对照',
 'sar8_ref_symmetric_hold':'高低端对称保持与后续位复位','sar8_ff_counterfactual':'FF源阻抗与决策时序反事实',
 'sar8_ss_bootstrap':'SS冷角Bootstrap建立诊断','sar8_idle_performance':'空闲复位版全码与1024点频谱最终结果',
 'sar8_r4_performance':'原版R4全码与1024点频谱结果','eight_bit_flat':'8位flat迁移与模型基线',
 'cdac8_device':'8位MOM CDAC器件实现','pdk_characterization':'T28单管表征','module_first_order':'模块一阶约束',
 'sar8_async_impl':'早期复杂握手异步逻辑（历史方案）',
 'b_dynamic_512':'B版512点动态结果','r3_b_oa':'R3 B版OA采用证据','sar8_r3_performance':'R3性能对照',
 'result_final_figures':'最终结果图生成物','obsidian_report_evidence':'Obsidian图表证据','obsidian_report_layout':'Obsidian排版生成物',
}
PROTECTED={'b_short_acceptance','sar8_r4_performance','sar8_idle_performance','sar8_stress_closure',
 'sar8_ref_current_probe','sar8_physical_repair','managed_execution','cdac10_dualrail','b_dynamic_512','r3_b_oa'}

def label(group):
    if group in LABELS:return LABELS[group]
    if group.startswith('sar8fix-'):return '在研物理修复/器件边界探针：'+group
    if group.startswith('bootstrap_') or group.startswith('top_plate_'):return '历史Bootstrap/采样诊断：'+group
    if group.startswith(('electrical_macro','oa_electrical_macro')):return '完整电气宏模型阶段：'+group
    if group.startswith('cdac8_'):return '8位CDAC器件/复位扫描：'+group
    if group.startswith(('strongarm','canvas_')):return '比较器/Canvas拓扑阶段：'+group
    if group.startswith('veriloga_'):return '历史Verilog-A行为建模：'+group
    return group

def protected(group):return group in PROTECTED or group.startswith('sar8fix-')

def advice(group,categories,active=False):
    if active:return '保留：观察到进程引用，暂不进入删减'
    if protected(group):return '保留：基线、当前诊断/修复或独立实验'
    if group in {'sar8_r4_staged','sar8_r4_idle'}:return '优先审传输副本；本地raw可在服务器原件核验后删'
    if group=='sar8_r4_reset':return '第二轮选留最终/精细案例；唯一原始波形不整组删除'
    if group in {'sar8_ref_gate_controls','sar8_ref_symmetric_hold'}:return '保留全点reduced.json.gz；此前raw已清理，非普通缓存'
    if group in {'sar8_main_width','sar8_pvt_mismatch','sar8_ref_length','sar8_ff_counterfactual','sar8_physical'}:
        return '第二轮选留关键尺寸、角落和失败案例；暂不整组删除'
    if sum(categories.values())<.1*GIB:return '暂留：体积小，清理收益低'
    return '选留最终结果与代表性失败；中间raw需逐案例确认'

def bytes_label(n):
    if n>=.1*GIB:return f'{n/GIB:.3f} GiB'
    if n>=1024**2:return f'{n/1024**2:.2f} MiB'
    return f'{n/1024:.1f} KiB'

def source_group(path,reg):
    result=set()
    for row in reg['runs']:
        if any(p==path or p.startswith(path+'/') or path.startswith(p+'/') for p in row['remote_paths']):result.add(row['group'])
    if len(result)==1:return next(iter(result))
    name=path.rsplit('/',1)[-1]
    if name.startswith(('sar8fix-','workflow-')):return name
    return re.sub(r'_20[0-9]{6}$','',name)

def retention_evidence(group):
    return [p for p in ['docs/'+group+'.md','verification/'+group,'netlist/'+group,'scripts/'+group] if (ROOT/p).exists()]

def proposal(pid,side,title,files,retained,conditions,evidence):
    return dict(id=pid,side=side,title=title,approval='pending_human_review',bytes=sum(x['bytes'] for x in files),
        file_count=len(files),files=files,required_retained_paths=sorted(set(retained)),conditions=conditions,
        evidence=evidence,delete_entire_experiment_directory=False,content_identity_verified_this_audit=False)

def render():
    manifest_path=DEST/'review_manifest.json'
    if manifest_path.exists():
        existing=load(manifest_path)
        if existing.get('approved') or any(p.get('approval')!='pending_human_review' for p in existing.get('proposals',[])):
            raise RuntimeError('Human review exists. Preserve it and create a new dated snapshot instead of overwriting decisions.')
    local=load(DEST/'local_census.json');remote=load(DEST/'server_census.json');reg=load(DEST/'registry_snapshot.json')
    assert not local['errors'] and not remote['errors'] and all(r['complete'] for r in remote['groups'])
    present=sorted((r for r in remote['groups'] if r['exists']),key=lambda r:-r['bytes'])
    lg=sorted(local['groups'],key=lambda r:-r['bytes']);allremote={f['path']:f for r in present for f in r['large_files']}
    proposals=[];rootmap={r['relative'].split('/')[-1]:r for r in lg}
    mirrors={
        'sar8_r4_staged':'/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_staged_20261022',
        'sar8_r4_idle':'/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_idle_20261022'}
    transfer_conditions=['删除前重新检查进程占用、尺寸、mtime与散列；本轮未重算大文件SHA256',
        '核对传输manifest/回执及压缩数据与保留原件的对应关系；不是仅凭名称认定重复',
        '保留所列服务器原始PSF、源网表、模型/角落配置、日志、回执、分析与最终图']
    for group,rpath in mirrors.items():
        lrow=rootmap[group];rrow=next(r for r in present if r['path']==rpath)
        assert not rrow['active_references']
        native=[f for f in rrow['large_files'] if f['category']=='native_waveform']
        native_paths=[f['path'] for f in native]
        parts=[f for f in lrow['large_files'] if f['category']=='transfer_parts']
        if parts:proposals.append(proposal('L-A1','local','MSB4600已完成回收的传输分卷',parts,native_paths,transfer_conditions,
            ['output/sar8_r4_staged/msb_4600/recovery_manifest.json','output/sar8_r4_staged/msb_4600/transfer.json','output/sar8_r4_staged/msb_4600/result.json']))
        targets=[f for f in rrow['large_files'] if f['category'] in {'transfer_parts','archive'}]
        proposals.append(proposal('S-A1' if group=='sar8_r4_staged' else 'S-A2','server',label(group)+'的传输压缩包/分卷',targets,native_paths,transfer_conditions,['scripts/sar8_r4_staged/recover_transfer.py']))
        local_raw=[];retained=[]
        for f in lrow['large_files']:
            if f['category']!='native_waveform':continue
            suffix=f['path'][len(lrow['path'])+1:].replace('/spectre/','/',1)
            counterpart=allremote.get(rpath+'/'+suffix)
            if counterpart and counterpart['bytes']==f['bytes']:
                local_raw.append(dict(f,remote_counterpart=counterpart['path'],match='exact case/path + size, not fresh SHA256'))
                retained.append(counterpart['path'])
        if local_raw:proposals.append(proposal('L-B1' if group=='sar8_r4_staged' else 'L-B2','local',label(group)+'的本地raw副本',local_raw,retained,
            ['逐文件本地/服务器完整SHA256相等后才可删；大小一致不足以证明内容相同',
             '对应服务器原始PSF锁定保留，不可同轮同时删除两端',
             '保留本地网表、配置、metadata、wave.npz、分析JSON、最终指标与图'],retention_evidence(group)))
    for i,row in enumerate(lg,1):
        group=row['relative'].split('/')[-1];row['review_id']=f'L{i:03d}';row['experiment']=label(group)
        row['retention_advice']=advice(group,row['categories']);row['evidence_paths']=retention_evidence(group)
    for i,row in enumerate(present,1):
        group=source_group(row['path'],reg);row['review_id']=f'S{i:03d}';row['experiment']=label(group)
        row['retention_advice']=advice(group,row['categories'],bool(row['active_references']));row['evidence_paths']=retention_evidence(group)
        if group in mirrors:row['retention_advice']='保留原始PSF；只审传输包/分卷，作为本地raw删减的保留端'
    payload=dict(schema_version=1,status='review_only_no_deletion',approved=False,local_observed_at_utc=local['observed_at_utc'],
        server_observed_at_utc=remote['observed_at_utc'],local_total_bytes=local['total_bytes'],server_total_bytes=remote['total_bytes'],
        local_disk_free_bytes=local['disk_free_bytes'],local_groups=lg,server_groups=present,
        missing_registered_roots=[r['path'] for r in remote['groups'] if not r['exists']],proposals=proposals,
        totals={side:{tier:sum(p['bytes'] for p in proposals if p['side']==side and p['id'].split('-')[1].startswith(tier)) for tier in ['A','B']} for side in ['local','server']},
        exclusions=['OA/PDK/other libraries','Git and environments','Obsidian and user dirty sources','other E-drive projects','unassociated server folders'],
        server_simulation_discovery=remote.get('discovery',[]),
        size_basis='GiB=1024^3; mutually exclusive roots and inode dedup; logical bytes, not guaranteed disk reclamation',
        source_metadata_only=True,raw_contents_read=False,provenance_note='Historical integrity receipts are not fresh large-file hash checks')
    save(DEST/'review_manifest.json',payload)
    local_a=payload['totals']['local']['A'];local_b=payload['totals']['local']['B'];server_a=payload['totals']['server']['A']
    lines=['# SAR ADC历史数据删减审核清单','',
        '本轮只盘点，没有删除、移动、压缩或重跑。建议先审传输残留，再决定是否只保留服务器的一份旧时序原始波形。当前过压诊断、修复候选、基线和独立10位实验不进入首轮删减。','',
        '## 容量与统计口径','',
        '| 范围 | 当前占用 | 建议优先审核的传输副本 | 追加可审的本地raw副本 |',
        '| --- | ---: | ---: | ---: |',
        f"| 本地项目生成物 | {bytes_label(local['total_bytes'])} | {bytes_label(local_a)} | {bytes_label(local_b)} |",
        f"| 服务器已登记运行 | {bytes_label(remote['total_bytes'])} | {bytes_label(server_a)} | 不删对应保留原件 |",'',
        f"本地观察：{datetime.fromisoformat(local['observed_at_utc']).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}；",
        f"服务器观察接收时间：{datetime.fromisoformat(remote['observed_at_utc']).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}，均采用本机北京时间。",
        f"本地所在盘当时空闲 {bytes_label(local['disk_free_bytes'])}。GiB=1024³字节；不是整个E盘或整个服务器的总占用。",'',
        '统计按不重叠目录及inode去重，不能把父目录和子目录再相加。本地为逻辑文件大小，服务器另存分配块数；实际释放量还受硬链接、压缩及文件系统影响。建议量不是已释放量。',
        f"服务器 {len(present)} 个存在根目录，{len(payload['missing_registered_roots'])} 个去重后的历史引用根目录未找到；未找到项不计为可删空间。",'',
        '本次前后两次进程观察未见所列目录被引用（每进程检查前256个文件描述符）；执行删除前仍须重新核对。' if not any(r['active_references'] for r in present) else
        '活动保护（前后两次进程观察）：'+ '；'.join('`'+r['path']+'`，PID '+','.join(str(pid) for pid in sorted({p['pid'] for p in r['active_references']})) for r in present if r['active_references'])+'。这些目录禁止删减；删除前须重新核对所有候选的占用。','',
        '## 本地优先审核项','',
        '| 审核编号 | 对应实验与对象 | 条件可删量 | 必须保留 |','| --- | --- | ---: | --- |']
    for p in proposals:
        if p['side']=='local':lines.append(f"| {p['id']} | {p['title']}，{p['file_count']}个文件 | {bytes_label(p['bytes'])} | 服务器同案例完整PSF；本地输入、指标、图与回执 |")
    lines += ['', 'L-A1 是 `output/sar8_r4_staged/msb_4600/spectre/parts_v1/` 下11个分卷，不是整个实验目录。历史恢复回执记录了逐片及合并后校验；本轮仅重新统计尺寸，批准后仍需重核散列。',
        'L-B1/L-B2 仅包含路径、案例和尺寸均对应到服务器的原始PSF，**尚未进行本轮完整内容比对**。只有逐文件SHA256相等，才能删除本地这一份。服务器对应原件在本清单中明确保留。',
        f'若两档均获批准且校验通过，本地条件可删总量为 {bytes_label(local_a+local_b)}；不含服务器空间。','',
        '### 本地大目录与保留建议','',
        f'本地项目根：`{ROOT.as_posix()}`。以下为目录总占用，不等于可删量。','',
        '| 编号 | 实验与目录 | 当前占用 | 保留建议 |','| --- | --- | ---: | --- |']
    for row in lg:
        if row['bytes']<.1*GIB:continue
        lines.append(f"| {row['review_id']} | {row['experiment']}<br>`{row['relative']}` | {bytes_label(row['bytes'])} | {row['retention_advice']} |")
    lines += ['', '旧 `sar8_physical`、`sar8_r4_reset` 和 B版验收占用虽大，很多本地原始波形没有在本轮服务器清单中找到对应原件，不能按重复缓存整组删除。第二轮可由你指定保留的最终/精细/失败案例，再列精确raw文件。','',
        '## 服务器优先审核项','',
        '| 审核编号 | 对应实验与对象 | 条件可删量 | 必须保留 |','| --- | --- | ---: | --- |']
    for p in proposals:
        if p['side']=='server':lines.append(f"| {p['id']} | {p['title']}，{p['file_count']}个文件 | {bytes_label(p['bytes'])} | 同案例 `test.raw/tran_perf.tran.tran`、输入、日志与回执 |")
    lines += ['', 'S-A1：旧R4分位复位实验的 `transfer_tran.gz` 与 `transfer_parts_v1/part_*`；S-A2：旧R4空闲复位实验的 `transfer_tran.gz`。只审这些传输文件，不删原始PSF。两端的A档传输副本与B档本地raw目标互不重叠。','',
        '### 服务器目录与保留建议','',
        '- H：`/home/chenzc_intern25/TSMC28/llm_IO/`',
        '- T：`/tmp/virtuoso_bridge_chenzc_intern25/90590/`',
        '- SSD：`/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/`',
        '- ADE：`/server_local_ssd/chenzc_intern25/simulation/`','',
        '| 编号 | 实验与目录 | 当前占用 | 保留建议 |','| --- | --- | ---: | --- |']
    for row in present:
        if row['bytes']<.1*GIB:continue
        path=row['path']
        for prefix,alias in zip(PREFIXES,['H/','T/','SSD/','ADE/']):
            if path.startswith(prefix):path=alias+path[len(prefix):];break
        lines.append(f"| {row['review_id']} | {row['experiment']}<br>`{path}` | {bytes_label(row['bytes'])} | {row['retention_advice']} |")
    lines += ['', '### 当前必须保留的证据','',
        '- `sar8_stress_closure_20261024` 四组约90.075 GiB：原版与Rgate/4、FF冷/热的全管过压原始对照。Rgate/4未采用也不等于证据无用。',
        '- 端电流定位约11.926 GiB、SSD电荷缓冲候选约13.130 GiB，以及两个IO器件边界探针：属于当前尚未结束的物理修复决策。',
        '- R3 B验收、原版R4与空闲复位版的最终码字、全码/频谱、网表、配置、原生日志与图继续保留；不能因原生exit0就把失败证据删掉。',
        '- `sar8_ref_gate_controls` / `sar8_ref_symmetric_hold` 的 `reduced.json.gz` 不是普通压缩缓存。此前部分原始PSF已经按旧授权清理，全点流式结果是关键保留证据。',
        '- 独立 `cdac10_dualrail`、OA、PDK、Git、环境、Obsidian和未关联的其他服务器工程均不纳入删减。','',
        '## 其余本地小目录','',
        '每项小于0.1 GiB，建议暂留，避免用大量审核精力换很少空间。JSON记录分组统计和所有候选文件的精确路径。','',
        '| 编号 | 目录 | 当前占用 |','| --- | --- | ---: |']
    for row in lg:
        if row['bytes']<.1*GIB:lines.append(f"| {row['review_id']} | `{row['relative']}` | {bytes_label(row['bytes'])} |")
    lines += ['', '## 其余服务器小目录','',
        '包括已登记恢复案例、当前修复小探针，以及在home/SSD的simulation父目录中按项目cell精确匹配的旧ADE运行。非项目名称未递归，不将未知工程计入可删空间。均建议暂留；在研项仍按前述规则保护。','',
        '| 编号 | 目录 | 当前占用 |','| --- | --- | ---: |']
    for row in present:
        if row['bytes']>=.1*GIB:continue
        path=row['path']
        for prefix,alias in zip(PREFIXES,['H/','T/','SSD/','ADE/']):
            if path.startswith(prefix):path=alias+path[len(prefix):];break
        lines.append(f"| {row['review_id']} | `{path}` | {bytes_label(row['bytes'])} |")
    lines += ['', '## 审核与执行边界','',
        '所有项均待你批准。本清单无删除脚本，也不会因为勾选或编辑JSON就执行操作。你可以按编号批准A档、B档，或指定某个大目录只保留哪些案例。',
        '执行前另做精确清单、占用复核、散列与保留副本验证；不允许将同一运行的本地和服务器最后一份原始波形同时列为删除。',
        '证据入口：[精确审核清单](review_manifest.json)、[本地元数据](local_census.json)、[服务器元数据](server_census.json)、[登记快照](registry_snapshot.json)。',
        '此前清理回执仍在 `verification/storage/`；本次不把已清理的文件重新算作候选空间。','']
    (DEST/'review.md').write_text('\n'.join(lines),encoding='utf-8')
    check()
    print(json.dumps(dict(status='REVIEW_ONLY',local_total_gib=local['total_bytes']/GIB,server_total_gib=remote['total_bytes']/GIB,
        local_transfer_gib=local_a/GIB,local_mirror_gib=local_b/GIB,server_transfer_gib=server_a/GIB),indent=2))

def check():
    d=load(DEST/'review_manifest.json');assert not d['approved'] and d['raw_contents_read'] is False
    seen=set();retain={p for x in d['proposals'] for p in x['required_retained_paths']}
    for p in d['proposals']:
        assert p['approval']=='pending_human_review' and not p['delete_entire_experiment_directory']
        assert sum(f['bytes'] for f in p['files'])==p['bytes']
        for f in p['files']:
            key=(p['side'],f['path']);assert key not in seen;seen.add(key)
            assert f['path'] not in retain,'Proposal would delete a required retained copy'
            assert f['nlink']==1,'Shared inode needs explicit retention review'
    for side in ['local','server']:
        rows=d[side+'_groups'];paths=[r['path'] for r in rows]
        assert outermost(paths)==sorted(paths),'Parent/child overlap'
        assert sum(r['bytes'] for r in rows)==d[side+'_total_bytes']
        assert all(r['complete'] for r in rows)
    print('REVIEW_CHECK_PASS',len(d['proposals']),'mutually exclusive proposals; no delete/retain conflict')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['capture','render','check']);args=parser.parse_args()
    if args.action=='capture':capture()
    elif args.action=='render':render()
    else:check()
