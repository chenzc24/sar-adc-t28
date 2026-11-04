"""One local native-feedback TT fixture; no simulator/remote operations."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

import build_d_fixture as d
import build_kickback_fixture as k

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'generated/feedback_tt_v1'
SOURCE=ROOT/'output/managed_execution/runs/sar8fix-loaded-both-rx2-tt/inputs/dut.scs'
SOURCE_SHA='c10982b40a9cf4a8aa861852f454b2a26e45ca0988fecd9a26f83c617887cd36'
BASE=HERE/'generated/kickback_actual_tt_v1'
FRONT={'GNPAN','GNPAP','GPPAN','GPPAP','X025','X008'}
REF_KEEP={'X002','X001','X000','X007','X003','XREQUEST','XD_LATE_CLK','XD_ACK','X008','X018','X017'}
REF_KEEP|={stem+str(i) for stem in ['XMUX','XSTORE','XBBM','XDRV'] for i in range(8)}


def sha(b):return hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,indent=2,allow_nan=False)+'\n'
def emit(n,ns,m,p=''):return '    %s (%s) %s%s'%(n,' '.join(ns),m,' '+p if p else '')
def mos(x):return x['model'].startswith(('nch_','pch_'))


def draft_write(path,blob):
    """This new package is editable until parent registration; old cases untouched."""
    blob=blob.encode() if isinstance(blob,str) else blob
    if path.exists() and path.read_bytes()==blob:return
    registered=any((ROOT/'management'/kind/'sar8audit-comp-feedback-tt-v1.yaml').exists() for kind in ['recipes','runs'])
    if registered:raise ValueError('Registered feedback package is immutable')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)


def prepare():
    if sha(SOURCE.read_bytes())!=SOURCE_SHA:raise ValueError('Frozen DUT differs')
    original=d.blocks(SOURCE.read_text(encoding='utf-8'));defs=dict(original)
    front=[]
    for bit in range(8):
        old='sar8p_refdrv_b'+str(bit);new='audit_ref_front_b'+str(bit)
        rows=[emit(n,ns,m,p) for n,ns,m,p in d.instances(original[old]) if n in FRONT]
        if len(rows)!=6:raise ValueError('First receiving stage changed')
        defs[new]='subckt '+new+' H L VDD VSS\n'+'\n'.join(rows)+'\nends '+new
        front.append(new)
    refpins=['CODE'+str(i) for i in range(8)]+['D'+str(i) for i in range(8)]
    refpins+=['PHI_U','SAMPLE','VDD','VSS']+['RST'+str(i) for i in range(8)]
    rows=['subckt audit_ref_receive '+' '.join(refpins)]
    for n,ns,m,p in d.instances(original['sar8i_refword']):
        if n not in REF_KEEP:continue
        if n.startswith('XDRV'):
            bit=n[4:];ns=['H'+bit,'L'+bit,'VDD','VSS'];m='audit_ref_front_b'+bit
        rows.append(emit(n,ns,m,p))
    if len(rows)!=len(REF_KEEP)+1:raise ValueError('Receive island incomplete')
    defs['audit_ref_receive']='\n'.join(rows+['ends audit_ref_receive'])
    pins=['TOPP','TOPN','SAMPLE_INT','VDD','VSS']+['D'+str(i) for i in range(8)]
    rows=['subckt audit_feedback '+' '.join(pins)]
    wanted={'XCTRL','XCOMP','CL_COMP_N','CL_COMP_P','CL_CMP_CLK'}
    for n,ns,m,p in d.instances(original['sar_adc8_join_r4']):
        if n in wanted:rows.append(emit(n,['VDD' if a=='VDD!' else 'VSS' if a=='0' else a for a in ns],m,p))
    if len(rows)!=6:raise ValueError('Original core instance set changed')
    bind=[n if n not in ['SAMPLE','VDD','VSS'] else {'SAMPLE':'SAMPLE_INT','VDD':'VDD','VSS':'VSS'}[n] for n in refpins]
    bind=['SAMPLE_INT' if re.fullmatch(r'RST[0-7]',n) else n for n in bind]
    rows.append(emit('XREF',bind,'audit_ref_receive'))
    defs['audit_feedback']='\n'.join(rows+['ends audit_feedback'])
    selected=d.closure(defs,['audit_feedback'])
    if any('bootstrap' in n or n=='sar8i_refword' or n.startswith('sar8p_refdrv_b') for n in selected):
        raise ValueError('Cut expanded into complete ADC/reference power chain')
    cells='// Native feedback fixture; local structural validation only.\n'+'\n\n'.join(defs[n] for n in selected)+'\n'
    binding={p:p for p in pins};binding.update(VDD='VDD!',VSS='0')
    devices=d.flatten(defs,'audit_feedback',binding)
    old=d.flatten(original,'sar_adc8_join_r4',{p:p for p in d.ports(original['sar_adc8_join_r4'])})
    # The three extracted boundary nodes move from internal ADC nodes to ports.
    node_map={'XDUT.TOPP':'TOPP','XDUT.TOPN':'TOPN','XDUT.SAMPLE_INT':'SAMPLE_INT'}
    old={n:{**v,'nodes':[node_map.get(x,x) for x in v['nodes']]} for n,v in old.items()}
    # Use the source's TOP naming and compare every original comparator/controller leaf.
    core={n:v for n,v in old.items() if n.startswith(('XDUT.XCOMP.','XDUT.XCTRL.'))}
    if sum(mos(v) for v in core.values())!=783:raise ValueError('783-MOS source core differs')
    for n,v in core.items():
        if devices.get(n)!=v:raise ValueError('Native core leaf/binding changed: '+n)
    if sum(mos(v) for v in devices.values())!=1457:raise ValueError('Expected 783+674 MOS')
    protected=['XDUT.PHI_U','XDUT.COMP_P','XDUT.COMP_N','XDUT.CMP_CLK','XDUT.XCTRL.DATA','XDUT.XCTRL.PHI_W']
    protected+=['XDUT.CODE'+str(i) for i in range(8)]+['D'+str(i) for i in range(8)]
    protected+=['XDUT.XREF.'+p for p in ['FIRST0','FIRST1','FIRST2','REQ_Q','LATE_CLK','ACK','CAP_REQ','CAP_CLK','MSB_QN']]
    protected+=['XDUT.XREF.'+s+str(i) for s in ['TARGET','Q','H','L'] for i in range(8)]
    unchanged={}
    for n in protected:
        a,b=d.fanout(old,n),d.fanout(devices,n)
        if a!=b:raise ValueError('Native interface/load fanout changed: '+n)
        unchanged[n]=a
    cut={}
    for bit in range(8):
        for local in ['GNPA','GPPA','GNNPRE','GPNPRE']:
            n='XDUT.XREF.XDRV%d.%s'%(bit,local);a,b=d.fanout(old,n),d.fanout(devices,n)
            removed=[r for r in a if r not in b]
            if len(removed)!=2 or any(r['terminal']!='g' for r in removed):raise ValueError('Unexpected cut: '+n)
            if len(b)!=2 or any(r['terminal']!='d' for r in b):raise ValueError('Cut lost native driver drains')
            cut[n]=dict(retained_native_drains=b,removed_downstream_gate_terminals=removed,
                condition='Zero external fanout after complete first inverter; native D/S/B voltages self-consistent. No clamp or substitute capacitance.')
    cap_text,cap_identity=k.cap_load(original)
    cddefs=d.blocks(cap_text)
    devices.update(d.flatten(cddefs,'audit_cdac_hold',dict(TOPP='TOPP',TOPN='TOPN',VCM='VCM',VREFN='VREFN',VREFP='VREFP'),prefix='XCDAC'))
    allnodes={n for v in devices.values() for n in v['nodes']}|{'CINIT','PREP','PREN','VCM','VREFP','VREFN','VDD!','SAMPLE_INT','HOLD_P','HOLD_N'}
    voltage={n for v in devices.values() if mos(v) for n in v['nodes'] if n!='0'}
    voltage|={'CINIT','PREP','PREN','VCM','VREFP','VREFN','VDD!','SAMPLE_INT','TOPP','TOPN'}
    roles={n:'XDUT.XCTRL.XTIM.'+s for n,s in dict(clock='CMP_CLK',write='PHI_W',update='PHI_U',data='DATA',pr='PR',nr='NR',raw='RAW',raw_d='RAW_D',dec='DEC',clock_reset='CLOCK_RESET',clock_q='CLOCK_Q',quiet='QUIET',quiet_d='QUIET_D').items()}
    roles.update(clock='XDUT.CMP_CLK',write='XDUT.XCTRL.PHI_W',data='XDUT.XCTRL.DATA',update='XDUT.PHI_U',active='XDUT.ACTIVE',comp_p='XDUT.COMP_P',comp_n='XDUT.COMP_N',x='XDUT.XCOMP.X',y='XDUT.XCOMP.Y',sample='SAMPLE_INT',topp='TOPP',topn='TOPN',rail='VDD!',init='CINIT')
    roles.update({n:'XDUT.XREF.'+s for n,s in dict(cap_clk='CAP_CLK',req_q='REQ_Q',ack='ACK',late_clk='LATE_CLK').items()})
    voltage.update(roles.values())
    if not voltage<=allnodes:raise ValueError('Nonexistent voltage saves: '+str(voltage-allnodes))
    tokens=['XDUT.XCTRL.T'+str(i) for i in range(8)];data=['D'+str(i) for i in range(8)]
    q=['XDUT.XREF.Q'+str(i) for i in range(8)];voltage.update(tokens+data+q)
    pairs=[]
    for n,v in devices.items():
        if not mos(v):continue
        limit=.99 if v['model'] in ['nch_mac','pch_mac'] else 1.98
        if v['model'] not in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac','nch_na18_mac']:raise ValueError('Unknown MOS model class')
        ns=dict(zip('dgsb',v['nodes']))
        for a,b in ['ds','gs','gd','gb','bd','bs']:
            pairs.append(dict(instance=n.lower(),terminal=a+b,nodes=[ns[a].lower(),ns[b].lower()],screen_v=limit))
    currents={'VVDD:1'};kcl={};catalog={}
    for side in ['P','N']:
        top='TOP'+side;terms=[]
        for n,v in devices.items():
            for i,node in enumerate(v['nodes'],1):
                if node==top:
                    term=n+':'+str(i);terms.append(term);currents.add(term)
                    catalog[term.lower()]=dict(node=top.lower(),port=i,model=v['model'])
        term='VSENSE_'+side+':1';terms.append(term);currents.add(term)
        catalog[term.lower()]=dict(node=top.lower(),port=1,model='vsource')
        if len(terms)!=11:raise ValueError('Expected eleven complete TOP incidence terms')
        kcl[top.lower()]=[x.lower() for x in terms]
    # Copy model include declarations and numerical options, never foundry content.
    prior=(HERE/'generated/deterministic_v2/tt.scs').read_text(encoding='utf-8').splitlines()
    rows=['// TT native completion feedback; conditional reference output cut; NOT SPECTRE COMPILED.','simulator lang=spectre','global 0 VDD!','parameters SUP=0.9']
    rows += [r for r in prior if r.startswith('include "/home/process/')]
    rows += ['include "cells.scs"','include "cdac_load.scs"','ahdl_include "initializer.va"',emit('XDUT',[binding[p] for p in pins],'audit_feedback'),emit('XCDAC',['TOPN','TOPP','VCM','VREFN','VREFP'],'audit_cdac_hold'),
        'VVDD (VDD! 0) vsource dc=SUP','VSAMPLE (SAMPLE_INT 0) vsource type=pwl wave=[0n SUP 20n SUP 20.1n 0 100n 0]',
        'VINIT (CINIT 0) vsource type=pwl wave=[0n SUP 18n SUP 18.1n 0 100n 0]',
        'VPREP (PREP 0) vsource dc=0.45087890625','VPREN (PREN 0) vsource dc=0.44912109375',
        'VVCM (VCM 0) vsource dc=0.45','VREFLOW (VREFN 0) vsource dc=0','VREFHIGH (VREFP 0) vsource dc=0.9']
    for side,prep in [('P','PREP'),('N','PREN')]:
        rows += ['VSENSE_%s (TOP%s HOLD_%s) vsource dc=0'%(side,side,side),
            'XINIT_%s (HOLD_%s %s CINIT 0) cmp_charge_initializer ron=10 control_high=0.9'%(side,side,prep)]
    rows += ['COUT%d (D%d 0) capacitor c=5f'%(i,i) for i in range(8)]
    rows += [r for r in prior if r.startswith('simulatorOptions ')]
    rows += ['tran_feedback tran stop=100n maxstep=5p errpreset=conservative','saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no']
    rows += ['save '+n for n in sorted(voltage)+sorted(currents)]
    wave=list(dict.fromkeys(list(roles.values())+tokens+data+q))
    cfg=dict(schema_version=1,scope='Native comparator/control completion and recovery, with finite unloaded reference-front output cut; not whole ADC qualification',
        stop_s=100e-9,release_end_s=18.1e-9,sample_fall_end_s=20.1e-9,target_diff_v=.0017578125,target_cm_v=.45,
        roles={n:v.lower() for n,v in roles.items()},tokens=[n.lower() for n in tokens],data_nodes=[n.lower() for n in data],ref_q_nodes=[n.lower() for n in q],
        voltage_saves=sorted(voltage),current_saves=sorted(currents),wave_voltage_columns=[n.lower() for n in wave],
        wave_current_columns=['xdut.xcomp.mninp:2','xdut.xcomp.mninn:2','vvdd:1'],
        kcl_terms=kcl,terminal_catalog=catalog,mos_pairs=pairs,pair_scope='All1457 retained MOS wrappers, six d/g/s/b differences each; no lifetime signoff',
        max_events=2000,max_native_points=2000000,max_output_bytes=29*1024**2,collection_allowance_bytes=32*1024**2,
        acceptance_pass=None,boundaries=dict(reference_driver_outputs='32 first-inverter drain pairs: zero external fanout; not real downstream Miller/rail switching',
            capture_reset='All eight original capture RST ports bound to SAMPLE_INT; preset sequencer excluded',
            startup='Declared SAMPLE_INT boundary only; excludes external SAMPLE/PRESET/RST_DONE handshake',
            input='18 native MOMs, ideal fixed bottoms; temporary finite initialization off18.1ns',
            clock='Original full transistor/RC feedback; no ideal internal clocks, DONE or token drive',noise=False,mismatch=False,PEX=False))
    if not set(cfg['wave_current_columns'])<=set(n.lower() for n in currents):raise ValueError('Unknown wave current')
    payload={'cells.scs':cells.encode(),'test.scs':('\n'.join(rows)+'\n').encode(),'cdac_load.scs':cap_text.encode(),
        'initializer.va':(BASE/'initializer.va').read_bytes(),'native_support.py':(BASE/'kickback_analyze.py').read_bytes(),
        'feedback_analyze.py':(HERE/'feedback_analyze.py').read_bytes()}
    cfg['required_input_sha256']={n:sha(v) for n,v in payload.items()}
    payload['measurement.json']=js(cfg).encode()
    manifest=dict(status='local_only_not_Spectre_compiled',source_DUT=dict(path=SOURCE.relative_to(ROOT).as_posix(),sha256=SOURCE_SHA),
        core_MOS=783,reference_receive_MOS=674,total_MOS=1457,all_MOS_pair_screens=len(pairs),
        native_voltage_saves=len(voltage),native_current_saves=len(currents),native_wave_columns=1+len(wave)+3+2,
        unchanged_native_subcircuits={n:sha(original[n].encode()) for n in selected if n in original},
        preserved_terminal_fanout=unchanged,physical_cut=cut,CDAC_instances=cap_identity,
        reset_remap=dict(original='XREF.RST0..7 from preset-step chain',condition='All eight formal reset ports use declared SAMPLE_INT startup guard'),
        input_hashes={n:sha(v) for n,v in payload.items()},input_bytes=sum(map(len,payload.values())),builder_sha256=sha(Path(__file__).read_bytes()),remote_submitted=False,baseline_adopted=False)
    recipe=dict(run_id='sar8audit-comp-feedback-tt-v1',design_id='sar8_comp_native_feedback_tt_v1',entry='test.scs',analyzer='feedback_analyze.py',
        inputs=[dict(name=n,source=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(v)) for n,v in payload.items()],expected_stop_s=100e-9,
        summary_signals=['TOPP','TOPN','XDUT.CMP_CLK','XDUT.PHI_U'],qualification_scope=cfg['scope'],oa_parity='netlist_only',
        test_conditions=dict(corner='ttmacro_mos_moscap/TT passives',vdd_v=.9,temperature_c=27,mismatch=False,transient_noise=False,PEX=False,
            input='Held+0.25LSB; one native eight-token sequence',startup='Ideal SAMPLE_INT, not full startup handshake'),
        spectre_args=['+preset=cx','+mt=1','+lqtimeout','60','-preset_override'],
        resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=512,
            max_output_mib=2048,simulation_wall_seconds=1800,analysis_wall_seconds=1800,queue_timeout_seconds=600))
    if recipe['resources']['simulation_rss_mib']>1024 or recipe['resources']['threads']!=1:
        raise ValueError('Authorized simulation ceiling is1GiB and one thread')
    for n,v in payload.items():draft_write(OUT/n,v)
    draft_write(OUT/'manifest.json',js(manifest));draft_write(OUT/'recipe_proposal.json',js(recipe))
    draft_write(OUT/'README.md',README)
    print('LOCAL_FEEDBACK_TT_PACKAGE',OUT,'input_bytes',manifest['input_bytes'],'MOS',1457,'voltage/current',len(voltage),len(currents))
    return manifest


README='''# TT native completion-feedback fixture

Local only; not Spectre compiled or submitted. Run proposal: recipe_proposal.json.
783 unchanged comparator/controller MOS +674 native receive/capture/BBM/front
MOS =1457. Three original comparator/clock MOMs,18 flat-CDAC MOMs and8x5fF
output loads. All8742 MOS terminal-pair screens are streamed at native points.

Physical cut: after complete first receiving inverters in each reference driver,
at GNPA/GPPA/GNNPRE/GPNPRE (32 nodes). Their two actual output drains remain;
two downstream gate terminals per node are removed. Drains solve natively under
zero external fanout: no ideal clamp, arbitrary capacitance or assumed slew.
manifest.json lists every retained/removed terminal and exact source identity.
This is a conditional load boundary, not complete reference-driver loading.

The reference request SR, delayed capture, ACK, all8 muxes/capture registers and
complete BBM cells remain to keep real PHI_U/D/CODE receiving dynamics. All8
capture reset ports are conditioned by declared SAMPLE_INT; preset sequencing
and external SAMPLE/RST_DONE handshake are excluded. First-arm input is held
+0.25LSB after18.1ns temporary initializer release; bottom rails remain ideal.
SAMPLE_INT falls20--20.1ns. Full native token/ACTIVE and RAW/DEC/PHI_W/PHI_U/
SR/QUIET/CMP_CLK feedback generates the eight decisions without fixed clocks.
100ns endpoint is an observation timeout, never a clock/reset control signal.

feedback_analyze.py streams native ASCII, deduplicates terminal-pair extrema,
records every timing/current row only for the selected timing columns, verifies
each token's write/update/reset and measured pre-next-clock recovery. Missing,
duplicate or wrong writes are reported as failures, never empty-list success.
Native logs/CMI/warnings retained. No noise/MC/PEX/PVT or final ADC accuracy claim.
Derived output hard cap29MiB leaves headroom under32MiB total collection target;
do not collect raw PSF. Simulation raw-output budget2048MiB is separate.
Parent alone registers/submits/analyzes/collects through managed serial execution.
'''

if __name__=='__main__':prepare()
