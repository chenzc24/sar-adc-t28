"""All-native paired-history metrics and bounded60-column export. Py2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import sys
sys.dont_write_bytecode=True
import history_export as export

base=export.base
s=base.s
MIB=1024*1024


def history_finalizer(cfg,original):
    h=cfg['history_case'];expected=h['expected_DATA_by_cycle'];targets=h['nominal_diff_by_cycle_v']
    def finalize(c,obs,where):
        original(c,obs,where)
        index=c['index'];token=c['token_bit'];bit=expected[index] if index<len(expected) else None
        wanted=[0]*8
        for j,value in enumerate(expected[:index+1]):wanted[7-j]=value
        c.pop('stored_bit_matches_positive_input',None)
        c.update(expected_DATA=bit,expected_D_bits_after_write=wanted,
            held_target_error_before_compare_v=None if index>=len(targets) else c['pre_compare']['input_diff_v']-targets[index],
            stored_bit_matches_history=bit is not None and c['stored_bit_after_recovery']==bit,
            all_D_bits_match_token_history=token is not None and obs['D_bits']==wanted,
            actual_precompare_sign_bit=(1 if c['pre_compare']['input_diff_v']>0 else 0 if c['pre_compare']['input_diff_v']<0 else None),
            nominal_target_diff_v=targets[index] if index<len(targets) else None)
        c['protocol_pass']=(token is not None and bit is not None and len(c['writes'])==len(c['updates'])==len(c['resets'])==1
            and c.get('clock_fall_half_s') is not None and c['stored_bit_matches_history'] and c['all_D_bits_match_token_history']
            and c['writes'][0]['DATA_bit']==bit and c['writes'][0]['token_bits']==[token]
            and c['actual_precompare_sign_bit'] is not None and c['writes'][0]['DATA_bit']==c['actual_precompare_sign_bit']
            and c['writes'][0]['time_s']<c['updates'][0]['time_s']<=c['resets'][0]['time_s']<=c['clock_fall_half_s'])
    return finalize


class Phase(object):
    def __init__(self,cfg):
        self.cfg=cfg;self.previous=None;self.pt=None;self.armed=False;self.events={};self.stats={};self.witness=set()
        self.start=None;self.plateau=None;self.phase_clock_max=0.;self.phase_write_max=0.;self.phase_update_max=0.;self.phase_sample_max=0.
        self.init_off_max=0.;self.bottom_cm_error=0.;self.init_current_after_step=0.;self.pre_second=None
        self.last_low=None;self.pre_inputs=[]

    def row(self,t,v):
        cfg=self.cfg;r=cfg['roles'];h=cfg['history_case'];rail=v[r['rail']]
        bp,bn=v['bot_p'],v['bot_n'];q=(bp-.45)/h['bottom_P_step_v']
        if v[r['clock']]<=.1*rail:
            self.last_low=dict(time_s=t,TOPP_v=v['topp'],TOPN_v=v['topn'],bottom_P_v=bp,bottom_N_v=bn,
                input_diff_v=v['topp']-v['topn'],input_cm_v=.5*(v['topp']+v['topn']))
        self.bottom_cm_error=max(self.bottom_cm_error,abs(.5*(bp+bn)-.45))
        self.init_off_max=max(self.init_off_max,abs(v[r['init']]) if t>=cfg['release_end_s'] else 0.)
        for name in ['bot_p','bot_n','hist_mark']:s.extreme(self.stats,name,v[name],t)
        if self.start is None and q>1e-9:
            self.start=dict(time_s=t,progress=q,TOPP_v=v['topp'],TOPN_v=v['topn']);self.witness.add(t)
        if self.start is not None and self.plateau is None:
            self.phase_clock_max=max(self.phase_clock_max,abs(v[r['clock']]))
            self.phase_write_max=max(self.phase_write_max,abs(v[r['write']]))
            self.phase_update_max=max(self.phase_update_max,abs(v[r['update']]))
            self.phase_sample_max=max(self.phase_sample_max,abs(v[r['sample']]))
        if self.plateau is None and self.start is not None and abs(q-1.)<=1e-9:
            self.plateau=dict(time_s=t,progress=q,TOPP_v=v['topp'],TOPN_v=v['topn']);self.witness.add(t)
        if self.plateau is not None:self.init_current_after_step=max(self.init_current_after_step,abs(v['vsense_p:1']),abs(v['vsense_n:1']))
        if self.previous is not None:
            p=self.previous;pt=self.pt;pr=p[r['rail']]
            a=p[r['clock']]-.5*pr;b=v[r['clock']]-.5*rail
            if a<0<=b and pt+(-a/(b-a))*(t-pt)>=cfg['sample_fall_end_s']:
                if len(self.pre_inputs)>=2000:raise ValueError('History precompare witness cap')
                self.pre_inputs.append(self.last_low)
            specs=[('first_update',p[r['update']]-.5*pr,v[r['update']]-.5*rail,1),
                ('trigger_mark',p['hist_mark']-.5*pr,v['hist_mark']-.5*rail,1)]
            if self.armed:specs.append(('first_armed_clock_fall10',p[r['clock']]-.1*pr,v[r['clock']]-.1*rail,-1))
            pq=(p['bot_p']-.45)/h['bottom_P_step_v']
            specs += [('bottom_progress_%s'%name,pq-level,q-level,1) for name,level in [('10',.1),('90',.9),('999999',.999999)]]
            for name,a,b,direction in specs:
                crossed=(a<0<=b) if direction==1 else (a>0>=b)
                if crossed and name not in self.events:
                    f=-a/(b-a);self.events[name]=dict(time_s=pt+f*(t-pt),before_native_s=pt,after_native_s=t)
                    self.witness.update([pt,t])
                    if name=='first_update':self.armed=True
        self.previous,self.pt=dict(v),t

    def finish(self,result):
        h=self.cfg['history_case'];cycles=result['cycles']
        second=cycles[1] if len(cycles)>1 else None;pre=second['pre_compare'] if second else None
        # Absolute TOP values are used directly, never corrected to the nominal target.
        out=dict(events=self.events,bottom_extrema=self.stats,first_motion_native=self.start,first_plateau_native=self.plateau,
            actual_precompare_inputs=self.pre_inputs,
            bottom_common_mode_max_error_v=self.bottom_cm_error,initializer_control_after_release_max_v=self.init_off_max,
            initializer_current_after_step_max_abs_a=self.init_current_after_step,
            during_motion_max_v=dict(clock=self.phase_clock_max,write=self.phase_write_max,update=self.phase_update_max,sample=self.phase_sample_max),
            nominal_initial_diff_v=h['nominal_diff_by_cycle_v'][0],nominal_second_diff_v=h['nominal_diff_by_cycle_v'][1],nominal_common_mode_v=.45,
            charge_coupling=dict(alpha=255./256.,P_bottom_step_v=h['bottom_P_step_v'],N_bottom_step_v=-h['bottom_P_step_v'],
                ideal_delta_diff_v=2.*255./256.*h['bottom_P_step_v'],ideal_delta_common_mode_v=0.,
                P_injected_charge_over_Cunit_V=255.*h['bottom_P_step_v'],absolute_Cunit_not_assumed=True),
            phase_valid=False,second_actual_precompare=None,comparison_boundary='Last native CLK<=0.1VDD before the second half-rise; no normalization',
            stimulus_boundary='TB senses PHI_U/CLK only; changes255-unit MOM bottom rails once; dummies fixed, no TOP/clock/token drive')
        if pre:
            observed=self.pre_inputs[1] if len(self.pre_inputs)>1 else None
            if observed is None or observed['time_s']!=pre['time_s']:raise ValueError('Independent precompare phase witnesses disagree')
            actual_sign=1 if pre['input_diff_v']>0 else 0 if pre['input_diff_v']<0 else None
            out['second_actual_precompare']=dict(pre,nominal_target_error_v=pre['input_diff_v']-h['nominal_diff_by_cycle_v'][1],
                expected_sign_bit=h['expected_DATA_by_cycle'][1],actual_sign_bit=actual_sign,
                absolute_TOPP_v=observed['TOPP_v'],absolute_TOPN_v=observed['TOPN_v'],
                actual_bottom_P_v=observed['bottom_P_v'],actual_bottom_N_v=observed['bottom_N_v'],
                independent_ideal_diff_at_actual_bottoms_v=h['nominal_diff_by_cycle_v'][0]+255./256.*(observed['bottom_P_v']-observed['bottom_N_v']),
                independent_ideal_CM_at_actual_bottoms_v=.45+255./512.*(observed['bottom_P_v']+observed['bottom_N_v']-.9))
        ready=cycles[0].get('first_reset_ready_native') if cycles else None
        out['phase_valid']=bool(pre and ready and self.start and self.plateau and 'first_armed_clock_fall10' in self.events
            and ready['time_s']<self.start['time_s']<self.plateau['time_s']<pre['time_s']
            and max(self.phase_clock_max,self.phase_write_max,self.phase_update_max,self.phase_sample_max)<.09
            and self.init_off_max<1e-10 and self.bottom_cm_error<1e-9)
        sign_bit=(1 if pre['input_diff_v']>0 else 0 if pre['input_diff_v']<0 else None) if pre else None
        out['second_write_matches_actual_sign']=bool(second and len(second['writes'])==1 and sign_bit is not None and second['writes'][0]['DATA_bit']==sign_bit)
        out['second_actual_sign_matches_nominal']=bool(sign_bit is not None and sign_bit==h['expected_DATA_by_cycle'][1])
        out['interpretation']='Nominal0.25LSB is a charge-conservation target, not a forced TOP voltage. Actual residual/CM and any target error remain unnormalized; input gate charge/parasitics are not compensated.'
        return out


def analyze(run,output):
    run,output=[os.path.realpath(p) for p in [run,output]]
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):raise ValueError('Expected new run/derived')
    cfg=s.read(export.safe(run,'inputs/measurement.json'));state=s.read(export.safe(run,'simulation.state.json'));native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):raise ValueError('Native simulation incomplete')
    for n,h in cfg['required_input_sha256'].items():
        if s.digest(export.safe(run,'inputs/'+n))!=h:raise ValueError('Frozen input differs: '+n)
    with open(export.safe(run,'raw/logStatus')) as f:
        if not re.search(r'\btran_feedback\s+PASS\b',f.read(65536)):raise ValueError('Native transient PASS missing')
    log=export.safe(run,'spectre.out')
    if os.path.getsize(log)>2*MIB:raise ValueError('Native log cap')
    with open(log,'rb') as f:blob=f.read()
    text=blob.decode('ascii')
    if 'allpub' in text:raise ValueError('Unexpected allpub')
    for count,kind in [(len(cfg['voltage_saves']),'voltage'),(len(cfg['current_saves']),'current')]:
        if not re.search(r'save\s+%d\s+\(%s\)'%(count,kind),text):raise ValueError('Native save counts differ')
    match=re.search(r'Number of accepted tran steps\s*=\s*(\d+)',text)
    if not match:raise ValueError('Native accepted-step footer missing')
    files=[n for n in os.listdir(os.path.join(run,'raw')) if n.endswith('.tran.tran')]
    if len(files)!=1:raise ValueError('Expected one native ASCII file')
    raw=export.safe(run,'raw/'+files[0]);before=os.stat(raw);out=s.Output(output,29*MIB)
    with open(os.path.join(output,'spectre.original.log'),'wb') as f:out.emit(f,blob)
    phase=Phase(cfg);old_psf=s.PSF;old_final=base.finalize;old_zlib=base.zlib
    class ObservedPSF(old_psf):
        def rows(self):
            for t,v in old_psf.rows(self):phase.row(t,v);yield t,v
    try:
        s.PSF=ObservedPSF;base.finalize=history_finalizer(cfg,old_final);base.zlib=export.MetricsOnlyZlib()
        result=base.reduce(raw,cfg,export.MetricsOutput(out))
    finally:s.PSF=old_psf;base.finalize=old_final;base.zlib=old_zlib
    placeholder=os.path.join(output,'wave.native.f64le.gz')
    if os.path.getsize(placeholder)!=0:raise ValueError('Unexpected unbounded first-pass export')
    os.remove(placeholder)
    if result['native_points']!=int(match.group(1))+1:raise ValueError('Native point count differs')
    result['history_stimulus']=phase.finish(result);result['history_case']=cfg['history_case']
    old_witness=export.witnesses
    def combined(result,cap):
        t=old_witness(result,cap)|phase.witness
        if len(t)>cap:raise ValueError('History witness cap exceeded')
        return t
    try:
        export.witnesses=combined
        serial=result['waveform']['uncompressed_sha256'];result['waveform']=export.export_native(raw,cfg,result,out,cfg['export_policy'])
    finally:export.witnesses=old_witness
    after=os.stat(raw)
    if (before.st_size,before.st_mtime)!=(after.st_size,after.st_mtime):raise ValueError('Raw changed between passes')
    result.update(all_native_metrics=True,two_full_native_passes_match=True,full_native_metric_serialized_sha256=serial,
        history_assessment_valid=bool(result['protocol_eight_pass'] and result['history_stimulus']['phase_valid'] and result['history_stimulus']['second_actual_sign_matches_nominal'] and result['history_stimulus']['second_write_matches_actual_sign']),
        measurement_sha256=s.digest(export.safe(run,'inputs/measurement.json')),native_warning_codes=native.get('warning_codes'),
        native_effective_settings=native.get('effective_settings'),simulator_version=native.get('version'),original_simulator_log_sha256=s.digest(log),
        collection_budget=dict(derived_cap_bytes=29*MIB,total_cap_bytes=32*MIB,wave_cap_bytes=14*MIB))
    result['measurement_methods']['history']='Input history/charge source phase measured at every native point; actual second TOPP/TOPN/DM/CM not normalized. Expected D history adapted only.'
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('Analysis RSS cap')
    result['derived_bytes_before_result']=out.bytes;out.json('result.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);resource.setrlimit(resource.RLIMIT_AS,(240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard),hard))
    r=analyze(a.run_dir,a.output_dir)
    print('COMPARATOR_HISTORY_NATIVE_ANALYSIS_OK',r['native_points'],'history_assessment_valid',r['history_assessment_valid'])


if __name__=='__main__':main()
