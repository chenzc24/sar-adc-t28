"""Local receipt-bound storage review. No remote calls or simulator launch."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile

import yaml

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[2]
PACKAGE=OWN/'standard_cell_full_v1'


def digest(path):
    h=hashlib.sha256();size=0
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())


def read(path):
    with Path(path).open(encoding='utf-8') as f:return json.load(f)


def receipt_files(folder):
    """Verify all collected members in bounded chunks; retain no wave arrays."""
    folder=Path(folder).resolve();receipt=read(folder/'collection_receipt.json')
    if receipt.get('skipped'):raise ValueError('Incomplete collection: skipped members')
    total=receipt['total_bytes']
    if total>32*1024**2:raise ValueError('Collection exceeds user32MiB limit')
    paths={}
    for e in receipt['files']:
        name=e['name']
        if '\\' in name or name.startswith('/') or '..' in name.split('/') or ':' in name:
            raise ValueError('Unsafe receipt member')
        if name in paths or e['bytes']>32*1024**2:raise ValueError('Duplicate/oversized receipt member')
        p=(folder/name).resolve()
        if not p.is_relative_to(folder):raise ValueError('Receipt path leaves collection')
        wanted=dict(bytes=e['bytes'],sha256=e['sha256'])
        if not p.is_file() or digest(p)!=wanted:
            p=p.with_name(p.stem+'.'+e['sha256'][:12]+p.suffix)
        if not p.is_file() or digest(p)!=wanted:raise ValueError('Receipt SHA/size mismatch: '+name)
        paths[name]=p
    if sum(p.stat().st_size for p in paths.values())!=total:raise ValueError('Receipt total differs')
    return receipt,paths


def verify_wave(path,header,result,cfg):
    proof=result['returned_waveform'];expected=proof['uncompressed']
    if expected['bytes']>cfg['max_derived_binary_bytes']:raise ValueError('Uncompressed wave exceeds declared bound')
    if digest(path)!=proof['compressed']:raise ValueError('Compressed waveform identity differs')
    n=len(header['names']);pack=struct.Struct('<'+'d'*n);h=hashlib.sha256();size=0;rows=0;last=None;first=None
    with gzip.open(path,'rb') as f:
        while True:
            blob=f.read(pack.size)
            if not blob:break
            size+=len(blob);h.update(blob)
            if len(blob)!=pack.size or size>cfg['max_derived_binary_bytes']:
                raise ValueError('Incomplete/oversized decompressed wave')
            row=pack.unpack(blob)
            if not all(math.isfinite(v) for v in row) or (last is not None and row[0]<=last):
                raise ValueError('Nonfinite/nonmonotonic native wave')
            if first is None:first=row[0]
            last=row[0];rows+=1
    if dict(bytes=size,sha256=h.hexdigest())!=expected:raise ValueError('Decompressed waveform identity differs')
    if first!=0 or last is None or abs(last-cfg['source_history_stop_s'])>1e-15:
        raise ValueError('Native wave start/END mismatch')
    if rows!=result['diagnostic_points'] or rows!=result['storage_observations']['native_rows']:
        raise ValueError('Native wave/observation row count differs')
    return dict(rows=rows,first_s=first,last_s=last,all_finite_increasing=True,
                compressed_and_decoded_SHA_verified=True,every_original_row_retained=True)


def summarize(result,cfg):
    observations=result['storage_observations'];groups={};phase_rows=[];delays=[]
    for name,context in observations['contexts'].items():
        group=groups.setdefault(context['kind'],dict(contexts=0,hold_pass_phases=0,hold_fail_phases=0,
                     hold_unknown_phases=0,extra_or_missing_Q_pattern_phases=0,
                     reset_overlap_hold_fail=0,reset_overlap_pattern_fail=0))
        group['contexts']+=1
        for i,p in enumerate(context['phases']):
            state=p['stable_hold_observation_pass']
            group['hold_unknown_phases' if state is None else 'hold_pass_phases' if state else 'hold_fail_phases']+=1
            pattern_issue=i>0 and not p['exact_expected_edge_pattern']
            group['extra_or_missing_Q_pattern_phases']+=int(pattern_issue)
            overlap=p.get('overlap_clock_reset',False)
            group['reset_overlap_hold_fail']+=int(overlap and state is False)
            group['reset_overlap_pattern_fail']+=int(overlap and pattern_issue)
            row=dict(context=name,source_instance=context['source_instance'],kind=context['kind'],
                     phase=p['index'],stable_hold_pass=state,hold_samples=p['native_hold_points'],
                     input_mismatch_samples=p['input_mismatch_points'],Q_mismatch_samples=p['Q_mismatch_points'],
                     QB_mismatch_samples=p['QB_mismatch_points'],reset_overlap=overlap,
                     expected_Q_change=p['expected_Q_change'],observed_Q_events=len(p['Q_events']),
                     exact_Q_pattern=p['exact_expected_edge_pattern'],initial_DC_phase=(i==0),
                     actual_pin_to_Q_delay_s=p['signed_actual_input_to_Q_delay_s'],delay_status=p['delay_status'])
            phase_rows.append(row)
            if p['expected_Q_change']:delays.append(row)
    known=[r for r in delays if r['actual_pin_to_Q_delay_s'] is not None]
    # Literal threshold, no numerical tolerance band deleting microvolt failures.
    failed=[]
    for label,x in result['full_history_voltage_stress'].items():
        if label not in cfg['stress_voltage_pairs']:raise ValueError('Unexpected physical screen member')
        if not x['over_limit_native_points']:continue
        device,pair=label.rsplit('_',1);nodes=cfg['stress_voltage_pairs'][label]
        failed.append(dict(instance=device,pair=pair,model=cfg['observed_mos'][device]['model'],
            native_library_device=cfg['observed_mos'][device]['library'],
            positive_node=nodes['positive_node'],negative_node=nodes['negative_node'],
            limit_v=x['limit_abs_v'],peak_abs_v=x['max_abs_v'],excess_v=x['max_abs_v']-x['limit_abs_v'],
            peak_time_s=x['max_abs_time_s'],first_over_s=x['first_over_limit_s'],last_over_s=x['last_over_limit_s'],
            over_limit_native_points=x['over_limit_native_points']))
    failed.sort(key=lambda x:x['excess_v'],reverse=True)
    if len(result['full_history_voltage_stress'])!=len(cfg['stress_voltage_pairs']):
        raise ValueError('Physical-screen coverage incomplete')
    delay_summary=dict(expected_transitions=len(delays),measured=len(known),
        missing_or_ambiguous=len(delays)-len(known),
        min_signed_s=min((r['actual_pin_to_Q_delay_s'] for r in known),default=None),
        max_signed_s=max((r['actual_pin_to_Q_delay_s'] for r in known),default=None),
        negative_signed_count=sum(r['actual_pin_to_Q_delay_s']<0 for r in known))
    summary=dict(stable_holds=groups,delays=delay_summary,
        physical=dict(screened_pairs=len(cfg['stress_voltage_pairs']),failed_pairs=len(failed),
            failed_devices=len({r['instance'] for r in failed}),worst=failed[:8],
            literal_limit_policy='Use each frozen simultaneous-terminal limit exactly; no microvolt waiver or tolerance rounding.',
            interval_policy='First/last violating native samples are witnesses, not continuous overvoltage duration; repeated pairs can represent one event.'),
        native_CMI_present=result['native_CMI_present'],native_warning_codes=result['native_warning_codes'],
        native_effective_settings=result['native_effective_settings'],
        full_history_KCL_nodes=len(result['node_kcl']),
        maximum_KCL_residual_a=max((v['max_abs_a'] for v in result['node_kcl'].values()),default=None),
        independent_source_work=result['full_history_source_energy'],
        fixture_scope='All26 isolated storage contexts and mapped immediate input/complete RC fanout only; subsequent output fanout is cut, not complete Miller/ADC qualification.',
        whole_ADC_qualified=None)
    return summary,phase_rows,failed


def load_case(tag):
    planned=read(PACKAGE/'manifest.json')['cases'][tag];run=planned['run_id']
    authored=PACKAGE/tag/'recipe.suggested.yaml'
    if digest(authored)['sha256']!=planned['recipe_file_sha256']:raise ValueError('Authored frozen recipe changed')
    record=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text(encoding='utf-8'))
    recipe=record['recipe'];canonical=json.dumps(recipe,sort_keys=True,separators=(',',':')).encode()
    if hashlib.sha256(canonical).hexdigest()!=record['recipe_hash']:raise ValueError('Managed canonical recipe changed')
    files={f['name']:f for f in recipe['files']}
    if set(files)!={f['name'] for f in planned['inputs']}:raise ValueError('Registered15-input membership changed')
    for x in planned['inputs']:
        f=files[x['name']]
        if dict(bytes=f['bytes'],sha256=f['sha256'])!=dict(bytes=x['bytes'],sha256=x['sha256']):
            raise ValueError('Registered input differs from frozen package')
        if digest(ROOT/f['source'])!=dict(bytes=x['bytes'],sha256=x['sha256']):raise ValueError('Registered input source changed')
    folder=ROOT/'output/managed_execution/runs'/run
    receipt,paths=receipt_files(folder/'collected')
    if receipt['status']['registered']['recipe_hash']!=record['recipe_hash']:
        raise ValueError('Collection attached to a different managed recipe')
    for phase in ['simulation','analysis']:
        state=read(paths[phase+'.state.json'])
        if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Run phase not complete: '+phase)
        if phase=='simulation':
            n=state.get('native',{})
            if not n.get('native_analysis_pass') or not n.get('zero_error_footer'):raise ValueError('Native PASS/footer absent')
    if not __import__('re').search(r'tran_first\s+PASS',paths['raw/logStatus'].read_text()):
        raise ValueError('Native transient PASS absent')
    result=read(paths['derived/result.json']);cfg=read(ROOT/files['measurement.json']['source'])
    if not result['native_PSF_END'] or result['missing_required_signals']:raise ValueError('Native END/signals incomplete')
    if result['measurement_sha256']!=files['measurement.json']['sha256']:raise ValueError('Wrong measurement result')
    required={n.lower() for n in cfg['voltage_saves']+cfg['current_saves']}
    if not required<=set(result['trace_bindings']):raise ValueError('Native terminal/current coverage incomplete')
    if set(result['node_kcl'])!={n.lower() for n in cfg['kcl_terms']}:raise ValueError('Full KCL coverage incomplete')
    wave=verify_wave(paths['derived/peak.native.bin.gz'],read(paths['derived/peak.columns.json']),result,cfg)
    summary,phases,physical=summarize(result,cfg)
    proof=dict(run_id=run,authored_recipe_file_sha256=planned['recipe_file_sha256'],managed_recipe_sha256=record['recipe_hash'],
               receipt_sha256=digest(folder/'collected/collection_receipt.json')['sha256'],
               receipt_files=len(paths),receipt_bytes=receipt['total_bytes'],registered_inputs=len(files),
               all_received_and_frozen_input_hashes_verified=True,wave=wave)
    return dict(proof=proof,summary=summary),phases,physical


def write_review(output,tag,report,phases,physical):
    output.mkdir(parents=True,exist_ok=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    for name,rows in [('phases.csv',phases),('terminal_failures.csv',physical)]:
        with (output/name).open('w',newline='',encoding='utf-8-sig') as f:
            if rows:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            else:f.write('No failing simultaneous terminal pairs.\n')
    s=report['summary'];d=s['delays'];p=s['physical']
    lines=['# '+tag.upper()+' 标准存储验证','',
           '已核对managed身份、15项冻结输入、完整回收收据、原生PASS／END及gzip逐字节身份。','',
           '| 类型 | 上下文 | 保持通过／失败／未知 | 额外或缺失Q沿阶段 | 复位重叠：保持失败／沿异常 |',
           '| --- | ---: | --- | ---: | --- |']
    for k,g in s['stable_holds'].items():
        lines.append('| %s | %d | %d／%d／%d | %d | %d／%d |'%(k,g['contexts'],g['hold_pass_phases'],
             g['hold_fail_phases'],g['hold_unknown_phases'],g['extra_or_missing_Q_pattern_phases'],
             g['reset_overlap_hold_fail'],g['reset_overlap_pattern_fail']))
    lines += ['', '实际引脚→Q：预期%d次，测得%d次，缺失／歧义%d次；带符号范围%s～%s秒。'%(
                  d['expected_transitions'],d['measured'],d['missing_or_ambiguous'],d['min_signed_s'],d['max_signed_s']),
              '', '同时刻端压：%d／%d对超限，涉及%d只MOS；原生CMI=%s。'%(p['failed_pairs'],p['screened_pairs'],p['failed_devices'],s['native_CMI_present']),
              '', '阶段明细见[phases.csv](phases.csv)，逐管／端对／节点／原生超限时刻见[terminal_failures.csv](terminal_failures.csv)。',
              '0.99V筛查不因幅度小而豁免；首末超限采样点不代表连续持续时间。',
              '', '本台只含第一级真实输入／RC负载，后级输出截断。稳定保持、额外沿和端压分别报告；不据此宣布整机或完整Miller负载合格。']
    (output/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def self_test():
    # Integrity check on a tiny two-row native stream, without any real run read.
    with tempfile.TemporaryDirectory(prefix='_std_review_',dir=OWN) as t:
        p=Path(t)/'wave.gz';blob=struct.pack('<dddd',0.,0.,1.,1.)
        with gzip.open(p,'wb') as f:f.write(blob)
        cfg=dict(max_derived_binary_bytes=1024,source_history_stop_s=1.)
        result=dict(returned_waveform=dict(uncompressed=dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()),compressed=digest(p)),diagnostic_points=2,storage_observations=dict(native_rows=2))
        assert verify_wave(p,dict(names=['time','q']),result,cfg)['rows']==2
        wrong=read_dict=json.loads(json.dumps(result));wrong['returned_waveform']['uncompressed']['sha256']='0'*64
        try:verify_wave(p,dict(names=['time','q']),wrong,cfg)
        except ValueError:pass
        else:raise AssertionError('Corrupt decoded identity accepted')
    print('LOCAL_REVIEW_ENTRY_SELF_TEST_PASS; no native run read, no registered input changed')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['ff','ss','both']);ap.add_argument('--output-name');ap.add_argument('--self-test',action='store_true')
    a=ap.parse_args()
    if a.self_test:self_test();return
    if a.case is None or not a.output_name or not a.output_name.replace('-','').replace('_','').isalnum():
        ap.error('--case and a fresh simple --output-name are required after parent confirms collection')
    target=PACKAGE/'results'/a.output_name
    if target.exists():raise ValueError('Preserve prior review output; choose a fresh name')
    loaded={tag:load_case(tag) for tag in (['ff','ss'] if a.case=='both' else [a.case])}
    for tag,(report,phases,physical) in loaded.items():
        write_review(target/tag,tag,report,phases,physical)
        print(tag,report['proof']['run_id'],report['summary']['physical']['failed_pairs'],'failed terminal pairs',target/tag)


if __name__=='__main__':main()
