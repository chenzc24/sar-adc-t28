"""Two sign-symmetric charge-history packages; no remote or simulator use."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import build_d_fixture as d
import build_kickback_fixture as k

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=HERE/'generated/feedback_tt_v2';SUPPORT=HERE/'generated/feedback_v2_reduce_v1/feedback_source_reduce.py'
OUT=HERE/'generated/history_charge_v1'
LSB=1.8/256.;LARGE=8*LSB;SMALL=.25*LSB;ALPHA=255/256.;STEP=(LARGE+SMALL)/(2*ALPHA)
CASES=[('negative_to_positive',-1,'neg-pos'),('positive_to_negative',1,'pos-neg')]


def sha(b):return hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,indent=2,allow_nan=False)+'\n'


def draft_write(dest,name,blob,run_id):
    blob=blob.encode() if isinstance(blob,str) else blob;p=dest/name
    if p.exists() and p.read_bytes()==blob:return
    if any((ROOT/'management'/kind/(run_id+'.yaml')).exists() for kind in ['recipes','runs']):
        raise ValueError('Registered history package is immutable')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)


def prepare():
    parent=json.loads((BASE/'recipe_proposal.json').read_bytes())
    for f in parent['inputs']:
        if sha((ROOT/f['source']).read_bytes())!=f['sha256']:raise ValueError('Frozen v2 differs')
    original=json.loads((BASE/'measurement.json').read_bytes());cap=(BASE/'cdac_load.scs').read_text(encoding='utf-8')
    cap=cap.replace('TOPN TOPP VCM VREFN VREFP','TOPN TOPP BOT_N BOT_P VREFN VREFP',1)
    cap=re.sub(r'(CMOMN[0-7] \(TOPN) VCM\)',r'\1 BOT_N)',cap)
    cap=re.sub(r'(CMOMP[0-7] \(TOPP) VCM\)',r'\1 BOT_P)',cap)
    caps=list(d.instances(d.blocks(cap)['audit_cdac_hold']));weights={side:0 for side in ['P','N']}
    for n,ns,m,p in caps:
        if n[-1]!='8':weights[n[4]]+=int(re.search(r'\bmulti=(\d+)',p)[1])
    if weights!={'P':255,'N':255}:raise ValueError('Physical bit-array weights differ')
    helper=SUPPORT.read_text(encoding='utf-8')
    if helper.count("if len(cols)!=57:raise ValueError('Frozen57-column interface differs')")!=1:raise ValueError('Export interface changed')
    helper=helper.replace("if len(cols)!=57:raise ValueError('Frozen57-column interface differs')","if len(cols)!=60:raise ValueError('History60-column interface differs')")
    cells=(BASE/'cells.scs').read_text(encoding='utf-8');defs=d.blocks(cells);body=defs['audit_feedback']
    head=body.splitlines()[0]
    interface=body.replace(head,head.replace('audit_feedback','audit_history_feedback',1)+' CMP_CLK PHI_U',1)
    interface=interface.replace('ends audit_feedback','ends audit_history_feedback',1)
    combined=dict(defs);combined.update(d.blocks(interface))
    old_bind={p:p for p in d.ports(defs['audit_feedback'])};old_bind.update(VDD='VDD!',VSS='0')
    new_bind=dict(old_bind,CMP_CLK='CMP_CLK',PHI_U='PHI_U')
    old_flat=d.flatten(defs,'audit_feedback',old_bind)
    new_flat=d.flatten(combined,'audit_history_feedback',new_bind)
    alias={'XDUT.CMP_CLK':'CMP_CLK','XDUT.PHI_U':'PHI_U'}
    canonical={n:{**v,'nodes':[alias.get(x,x) for x in v['nodes']]} for n,v in old_flat.items()}
    if canonical!=new_flat:raise ValueError('Observation interface changed native electrical devices/loads')
    shared={n:(BASE/n).read_bytes() for n in ['cells.scs','initializer.va','native_support.py','feedback_analyze.py']}
    shared.update({'cdac_load.scs':cap.encode(),'history_charge.va':(HERE/'history_charge.va').read_bytes(),
        'history_analyze.py':(HERE/'history_analyze.py').read_bytes(),'history_export.py':helper.encode(),
        'history_interface.scs':('// TB wrapper: unchanged native body, two passive observation ports.\n'+interface+'\n').encode()})
    for name,sign,suffix in CASES:
        dest=OUT/name;cfg=copy.deepcopy(original)
        cfg['scope']='TT opposite-decision charge-history diagnostic with native feedback; physical bit-MOM bottom step only, not full ADC/PVT/noise qualification'
        cfg['history_case']=dict(name=name,HSIGN=sign,LSB_v=LSB,large_LSB=8,small_LSB=.25,
            nominal_diff_by_cycle_v=[sign*LARGE]+[-sign*SMALL]*7,
            expected_DATA_by_cycle=[int(sign>0)]+[int(sign<0)]*7,bottom_P_step_v=-sign*STEP,
            alpha_nominal=ALPHA,nominal_common_mode_v=.45,delay_after_armed_CLK_fall10_s=900e-12,slew_s=200e-12,
            actual_residual_not_normalized=True,unknown_input_gate_charge_not_compensated=True)
        cfg['voltage_saves']=sorted(original['voltage_saves']+['BOT_P','BOT_N','HIST_MARK'])
        cfg['wave_voltage_columns']=original['wave_voltage_columns']+['bot_p','bot_n','hist_mark']
        rename={'XDUT.CMP_CLK':'CMP_CLK','XDUT.PHI_U':'PHI_U','xdut.cmp_clk':'cmp_clk','xdut.phi_u':'phi_u'}
        cfg['voltage_saves']=sorted(rename.get(n,n) for n in cfg['voltage_saves'])
        cfg['roles']={n:rename.get(v,v) for n,v in cfg['roles'].items()}
        cfg['wave_voltage_columns']=[rename.get(n,n) for n in cfg['wave_voltage_columns']]
        for p in cfg['mos_pairs']:p['nodes']=[rename.get(n,n) for n in p['nodes']]
        cfg['export_policy']=dict(baseline_row_budget=20000,max_witness_times=10000,max_export_rows=30000,max_wave_bytes=14*1024**2,
            export_range_s=[0.,100e-9],figure_label_required=True)
        cfg['boundaries']['input']='One ideal charge step on255-unit bit bottoms; dummy rails fixed. TOP initializer off18.1ns and no later TOP drive.'
        cfg['boundaries']['bottom_bit_plates']='Initially450mV; once +/-29.117647mV after first PHI_U and armed CLK falling0.1VDD plus900ps/200ps slew'
        text=(BASE/'test.scs').read_text(encoding='utf-8')
        text=text.replace('parameters SUP=0.9','parameters SUP=0.9 HSIGN=%d'%sign,1)
        text=text.replace('include "cells.scs"','include "cells.scs"\ninclude "history_interface.scs"',1)
        text=text.replace('XDUT (TOPP TOPN SAMPLE_INT VDD! 0 D0 D1 D2 D3 D4 D5 D6 D7) audit_feedback',
            'XDUT (TOPP TOPN SAMPLE_INT VDD! 0 D0 D1 D2 D3 D4 D5 D6 D7 CMP_CLK PHI_U) audit_history_feedback',1)
        text=text.replace('ahdl_include "initializer.va"','ahdl_include "initializer.va"\nahdl_include "history_charge.va"',1)
        text=text.replace('XCDAC (TOPN TOPP VCM VREFN VREFP)','XCDAC (TOPN TOPP BOT_N BOT_P VREFN VREFP)',1)
        text=text.replace('VPREP (PREP 0) vsource dc=0.45087890625','VPREP (PREP 0) vsource dc=(0.45+HSIGN*0.028125)',1)
        text=text.replace('VPREN (PREN 0) vsource dc=0.44912109375','VPREN (PREN 0) vsource dc=(0.45-HSIGN*0.028125)',1)
        text='\n'.join(s for s in text.splitlines() if not s.startswith('save '))+'\n'
        text+='XHISTORY (BOT_P BOT_N HIST_MARK CMP_CLK PHI_U VDD! VCM 0) cmp_history_charge step_sign=(-HSIGN) amp_v=0.02911764705882353 delay_s=900p slew_s=200p\n'
        text+='\n'.join('save '+n for n in cfg['voltage_saves']+cfg['current_saves'])+'\n'
        payload=dict(shared);payload['test.scs']=text.encode()
        cfg['required_input_sha256']={n:sha(v) for n,v in payload.items()};payload['measurement.json']=js(cfg).encode()
        proposal=copy.deepcopy(parent)
        proposal.update(run_id='sar8audit-comp-history-'+suffix+'-tt-v1',design_id='sar8_comp_charge_history_'+suffix.replace('-','_'),
            analyzer='history_analyze.py',qualification_scope=cfg['scope'],
            summary_signals=['topp','topn','cmp_clk','phi_u','bot_p','bot_n'],
            inputs=[dict(name=n,source=(dest/n).relative_to(ROOT).as_posix(),sha256=sha(v)) for n,v in payload.items()])
        proposal['test_conditions'].update(input='%+dLSB (%+.8fmV) -> nominal %+.2fLSB (%+.7fmV) by bottom-plate charge; actual TOP floats and is not normalized'%(sign*8,sign*LARGE*1e3,-sign*.25,-sign*SMALL*1e3),
            input_history=cfg['history_case'],history_TB='Bottom-plate charge actuator observes only; no internal clock/token drive')
        if proposal['resources']!=parent['resources'] or proposal['spectre_args']!=parent['spectre_args']:raise ValueError('Solver/resources changed')
        manifest=dict(status='local_only_not_Spectre_compiled',parent_proposal_sha256=sha((BASE/'recipe_proposal.json').read_bytes()),
            source_circuit_MOS=1457,unchanged_native_chain=True,unchanged_MOM_parameters=True,MOM_instances=18,
            case=cfg['history_case'],bit_weight_units_per_side=255,total_weight_units_per_side=256,
            ideal_second_diff_v=sign*LARGE+ALPHA*(-2*sign*STEP),ideal_second_CM_v=.45,
            unchanged_payloads=['cells.scs','initializer.va','native_support.py','feedback_analyze.py'],
            passive_observation_ports=dict(test_wrapper='audit_history_feedback',aliases=alias,flattened_native_devices_and_loads_identical=True),
            native_voltage_saves=127,native_current_saves=23,wave_columns=60,selected_MOS_pairs=990,full_stress_complete=False,
            max_wave_raw_bytes=30000*60*8,queue='Parent serial scheduling; standard-cell FF has priority',
            input_bytes=sum(map(len,payload.values())),input_sha256={n:sha(v) for n,v in payload.items()},builder_sha256=sha(Path(__file__).read_bytes()),remote_submitted=False,baseline_adopted=False)
        for n,v in payload.items():draft_write(dest,n,v,proposal['run_id'])
        draft_write(dest,'recipe_proposal.json',js(proposal),proposal['run_id']);draft_write(dest,'manifest.json',js(manifest),proposal['run_id']);draft_write(dest,'README.md',README,proposal['run_id'])
        print('LOCAL_HISTORY_PACKAGE',name,'inputs',manifest['input_bytes'],'HSIGN',sign,'nominal_second',manifest['ideal_second_diff_v'])
    k.exact(OUT/'fixture_scheme.md',SCHEME)


README='''# Opposite history: controlled charge, native feedback

Local only, not Spectre compiled/submitted. Parent dispatches after standard-cell
FF priority work. Same1457MOS/cells/RCs/receive chain,18 native MOM parameters,
100ns/settings/1GiB/one-thread/2048MiB raw budget and original SAMPLE_INT closing
20--20.1ns and initializer release18--18.1ns. No new baseline/noise/MC/PVT claim.

history_interface.scs copies the native root body and only exports CMP_CLK and
PHI_U as passive TB observation ports. Original cells.scs stays byte-identical;
flattened native devices/loads are identical under this two-node alias map.
XHISTORY connects ordinary top-level ports, not ambiguous hierarchical stubs.

Only input history differs between the two cases: HSIGN=-1 gives -8LSB then
nominal+0.25LSB; HSIGN=+1 is symmetric. 8LSB=56.25mV,32x small residual, initially
TOP421.875/478.125mV around450mV. Bit bottoms255Cu and dummy1Cu are unchanged.
alpha=255/256; equal/opposite29.1176470588mV bottom shifts give ideal target
+/-1.7578125mV and zero common-mode shift. Actual gate charge/parasitics are not
corrected: report absolute second TOPP/TOPN/DM/CM and target deviation as measured.

history_charge.va observes the first PHI_U rise then the following CLK fall at
0.1VDD, waits900ps, slews200ps once, then holds bottom voltages constant. Drives
only BOT_P/BOT_N and an isolated marker; no TOP/clock/token force. No sampler
window change. TOP initialization is never reattached; zero-conductance init
branch/current and real phase order are checked in analysis. This is a TB charge
history experiment, not actual transistor reference switching or ADC bit weights.

127V/23I native saves;990 selected direct-chain stress screens, remaining7752
unmeasured. Original full-circuit CMI logs retained. All-native metrics; two-pass
bounded60-column export <=30000 rows/14MiB, derived29MiB, collection32MiB. Native
protocol reducer is unchanged; runtime adapter changes only expected history/D
polarity and adds stimulus phase/actual-residual diagnostics. Success cannot be
claimed if the step overlaps comparison/write or is incomplete at second input.
'''

SCHEME='''# 成对历史电荷验证方案

两组只反转HSIGN和对应目标：先−8LSB再名义+0.25LSB；先+8LSB再名义−0.25LSB。
大残差56.25mV是小残差32倍，初始TOP为421.875/478.125mV，保持450mV共模。
不扫尺寸、共模、时钟或PVT。保留1457MOS原生异步反馈及既有接收链和有限参考切口。

每侧位电容255Cu、dummy1Cu；绝对Cu未假定。输入TOP浮置时的一阶关系为

    ΔVDM = (255/256)(ΔBP−ΔBN) − (ΔQgP−ΔQgN)/(256Cu)
    ΔVCM = (255/512)(ΔBP+ΔBN) − (ΔQgP+ΔQgN)/(512Cu)

忽略未知栅端电荷项仅用于名义刺激计算：ΔBP=−ΔBN=±29.1176470588mV，
得到从∓56.25mV到±1.7578125mV，名义共模变化0。dummy底板仍接0/0.9V；
位底板范围420.882353–479.117647mV。绝对电荷只能写成±7.425Cu·V，不编造pC。
实际比较器门电荷、泄漏/寄生导致的目标偏差均原样报告，不重标定输入或事后归一化。

初始化18.1ns断开；外部SAMPLE_INT关闭沿20--20.1ns保持。首轮PHI_U后，仅测试台
监听下一个CLK下降0.1VDD，在其后900ps开始200ps底板阶跃。内部CLK/token无任何
理想源驱动或强制。阶跃必须落在首轮内部reset90之后且第二次CLK激活前，并且CLK、
PHI_W、PHI_U、SAMPLE_INT均低；实际相位由原生数据核对，不能由预设900ps宣称通过。

阶跃结束后底板维持常值，TOP仍仅连原生MOM、输入MOS栅和已关闭初始化支路。
测绝对第二次判决前TOPP/TOPN/VDM/VCM、DATA/PHI_W、复位和990项选定端压；
检查初始化控制/支路电流及步进前后KCL。负向写入以真实DATA和PHI_W/token及两组
D历史共同判断，不把初始化0的静态D电平单独当作成功写入。完整8742项仍未覆盖。

原始日志、全部原生点指标保持；仅图用受限原生行导出，取样/范围/见证点显式记录。
本地仅建包，未编译或仿真，主聊天统一managed串行调度，标准单元FF先跑。
'''

if __name__=='__main__':prepare()
