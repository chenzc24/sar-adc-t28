"""Local source-bound calculations; every prediction is conditional, not Spectre."""
import hashlib,json,math
from pathlib import Path
OWN=Path(__file__).resolve().parent;BASE=OWN.parent;REF=BASE.parent;ROOT=REF.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    summary=BASE/'comparison/comparison.json';d=read(summary)['source_runs']['D1P25']
    native=ROOT/'output/managed_execution/runs'/d['run']/'collected/derived/result.json'
    assert sha(native)==d['result_sha256']
    events=d['RC1_events']['events'];p,n=events['HD_positive'],events['HD_negative']
    cp=p['leading']['charge_C']['C1']/(p['leading']['RC1_stop_V']-p['leading']['RC1_start_V'])
    cn=n['leading']['charge_C']['C1']/(n['leading']['RC1_stop_V']-n['leading']['RC1_start_V'])
    assert cp>0 and cn>0 and abs(cp-cn)/cp<.001
    cap_estimates=[cp,cn];cp=(cp+cn)*.5
    r=sum(p['observed_R1_ohm_range'])/2
    charge=read(native)['cell_measurements']['HD_actual_native_port_exchange']['phases']['CODE_fall']
    previous=[]
    for case,filename,supply in [('FF','io_cell_ff_comparison',.99),('SS','io_cell_ss_comparison',.81)]:
        file=REF/'generated'/filename/'comparison.json';x=read(file)['source_runs']['io']
        folder=ROOT/'output/managed_execution/runs'/x['run']/'collected'
        receipt=read(folder/'collection_receipt.json');assert not receipt['skipped']
        for f in receipt['files']:
            source=folder/f['name'];assert source.stat().st_size==f['bytes'] and sha(source)==f['sha256']
        source=folder/'derived/result.json';expected=x.get('result_sha256',x.get('source_result_sha256'))
        assert sha(source)==expected
        v=x['node_extrema']['xdut.gnndrv'];actual=read(source)['voltage_and_current_extrema']['xdut.gnndrv']
        assert (v['min_V'],v['max_V'])==(actual['min'],actual['max'])
        alpha_max=min(supply/(2*v['max_V']-supply),supply/(supply-2*v['min_V']))
        previous.append(dict(corner=case,supply_V=supply,run=x['run'],result_sha256=expected,comparison_sha256=sha(file),
            old_IO_node_extrema_V=[v['min_V'],v['max_V']],maximum_alpha_to_keep_pin_in_rails_for_these_endpoints_only=alpha_max,
            projected_alpha_half_pin_V=[.5*v['min_V']+.25*supply,.5*v['max_V']+.25*supply],
            not_a_bound_for_new_interface=True))
    cap=4*cp
    calculations=dict(observed_C1_charge_over_voltage_F=cp,
        positive_negative_Q_over_deltaV_estimates_F=cap_estimates,
        Q_over_deltaV_note='Approximate total-port native trapezoid estimates, not an exact constant intrinsic capacitance',observed_R1_midrange_ohm=r,
        guard=dict(series_R_units=1,upper_R_units=2,lower_R_units=2,shunt_C1_units=4,
            stiff_IO_alpha=.5,stiff_IO_DC_levels_fraction_VDD=[.25,.75],shunt_capacitance_estimate_F=cap,
            stiff_IO_no_NAND_C_tau_s=r*.5*cap,stiff_IO_no_NAND_C_1percent_s=math.log(100)*r*.5*cap,
            finite_Ron_no_NAND_C_tau_range_s=[r*.5*cap,r*cap],
            observed_old_HD_absolute_gate_charge_C=charge['absolute_net_charge_C']['NAND_input_G'],
            frozen_charge_over_new_C_only_V=charge['absolute_net_charge_C']['NAND_input_G']/cap,
            no_new_charge_bound_or_timing_qualification=True,
            stiff_IO_bias_power_W={str(v):3*v*v/(8*r) for v in [.81,.9,.99]},
            hypothetical_30_70_input_Ron_upper_ohm=r*.5,
            hypothetical_30_70_is_not_verified_library_requirement=True,
            loaded_low_level_equation='VDD*(R+Ron)/(2*(2*R+Ron))',
            loaded_high_level_equation='VDD-loaded_low; only ohmic Ron illustration',
            VIH_VIL='unknown; must not replace by halfVDD timing threshold'),
        positive_RC1_clear_D_leading_charge_C=p['leading']['charge_C']['MP_CLEAR_D'],
        negative_RC1_clear_D_leading_charge_C=n['leading']['charge_C']['MP_CLEAR_D'],
        worst_negative_concurrent=d['negative'],old_IO_counterexamples=previous)
    case=read(OWN/'candidate/package_review.json')['cases'][0]
    assert case['recipe_sha256']==sha(ROOT/case['recipe'])
    for f in case['files']:
        source=ROOT/f['source'];assert source.stat().st_size==f['bytes'] and sha(source)==f['sha256']
    result=dict(kind='existing_results_and_conditional_algebra_not_new_simulation',acceptance_pass=None,
        source_native_result_sha256=sha(native),source_comparison_sha256=sha(summary),calculations=calculations,
        candidate=case,registered=False,remote_started=False,
        decision='Prepare only option B as one composite interface topology factor; no individual-device causal attribution. Original full-swing HD contract remains separately measured.')
    (OWN/'evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('OPTIONS_EVIDENCE_READY',case['recipe_sha256'],'C1_fF',cp*1e15,'guard_ideal_tau_ps',r*.5*cap*1e12,'bias_uW',3*.99*.99/(8*r)*1e6)


if __name__=='__main__':main()
