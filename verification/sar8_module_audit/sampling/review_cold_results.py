"""Bounded review of existing cold controls and their two hot counterparts."""
import hashlib
import json
from pathlib import Path
import re

import numpy as np

import builder as b
from review_results import read_case

HERE=Path(__file__).resolve().parent
OUT=HERE/'cold_results'


def inspect_case(case,temp,expected_sha):
    root=b.ROOT/'output/managed_execution/runs'/('sar8audit-sample-v2-'+case)
    frozen=(root/'inputs/test.scs').read_bytes()
    assert b.sha(frozen)==expected_sha
    package=json.loads((HERE/'stream_package/package_manifest.json').read_text())
    for name in ['fixture_dut.scs','mapping.json','stream.cpp']:
        assert b.sha((root/'inputs'/name).read_bytes())==package['files'][name]['sha256']
    receipt=json.loads((root/'collected/collection_receipt.json').read_text())
    for item in receipt['files']:
        h=hashlib.sha256()
        with (root/'collected'/item['name']).open('rb') as stream:
            for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
        assert h.hexdigest()==item['sha256']
    log=(root/'collected/spectre.out').read_text(errors='replace')
    observed=[float(t) for t in re.findall(r'(?m)^\s*temp = (-?\d+(?:\.\d+)?)',log)]
    assert observed and all(t==temp for t in observed),(case,observed)
    assert 'spectre completes with 0 errors' in log
    r,w=read_case(case)
    r['native_temperature_c']=temp
    r['native_temperature_log_occurrences']=observed
    r['receipt_and_frozen_input_SHA_verified']=True
    r['net_turnoff_delta_mv']=r['raw_held_source_error_mv']-r['preclose_error_mv']
    r['native_warning_codes']=sorted(set(re.findall(r'(?:WARNING|Warning) \(([A-Z]+-\d+)\)',log)))
    for snap in r['snapshots'].values():
        for side in ['p','n']:
            snap[side]['main_total_drain_ua']=sum(snap[side][n+'_drain_ua'] for n in ['Mmain','Mmain_U1'])
    x=np.linspace(55,143,4401)
    cache={'time_ns':x}
    for key in ['top_p','top_n','vin_p','vin_n','seq_sample','boot_p_btop','boot_p_bbot','boot_p_g','boot_p_ctrl']:
        cache[key]=np.interp(x*1e-9,w['t'],w['matrix'][:,w['indices'][w['names'][key]]])
    mapping=json.loads((HERE/'compact_v2/boundary_loads.json').read_text())['device_mapping_without_geometry']
    labels={m['instance']:m['label'].lower() for m in mapping}
    current=np.zeros(len(x))
    for device in ['Mmain','Mmain_U1']:
        node='xf.'+labels['XDUT.XBOOTP.'+device]+':1'
        current+=np.interp(x*1e-9,w['t'],w['matrix'][:,w['indices'][node]])*1e6
    cache['main_p_ua']=current
    w['matrix']._mmap.close()
    return r,cache


def plot(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(5,2,figsize=(12,11.5),layout='constrained')
    settings=[('low40','low40cold','Finite 40 ns external low'),
              ('long','longcold','Low-phase DC equilibrium; no finite duration')]
    for col,(hot,cold,title) in enumerate(settings):
        axes[0,col].set_title(title,fontsize=10)
        for case,color,style,label in [(hot,'#c35a3c','-','125 C'),(cold,'#246f9c','--','-40 C')]:
            r,w=cases[case];x=w['time_ns']
            ys=[w['boot_p_btop']-w['boot_p_bbot'],w['boot_p_ctrl'],
                w['boot_p_g']-w['vin_p'],w['main_p_ua'],
                (w['top_p']-w['top_n']-np.interp(x,[0,100.2,100.3,160],[.81,.81,-.81,-.81]))*1000]
            for row,y in enumerate(ys):
                axes[row,col].plot(x,y,color=color,ls=style,label=label,lw=1.5)
                if row:
                    axes[row,col].axvline(r['actual_open_ns'],color=color,ls=':',lw=.8)
                    axes[row,col].axvline(r['actual_close_ns'],color=color,ls=':',lw=.8)
        axes[0,col].axhline(.81,color='#777',ls=':',lw=.8)
        axes[2,col].axhline(0,color='#777',lw=.8)
        axes[4,col].set_yscale('symlog',linthresh=1)
        axes[4,col].axhspan(-1.7578125,1.7578125,color='#79b991',alpha=.16)
        axes[0,col].set_xlim(55,143)
        for row in range(1,5):axes[row,col].set_xlim(99,143)
        for row in range(5):
            axes[row,col].grid(alpha=.18)
        axes[0,col].legend(loc='best',ncol=2,fontsize=8)
        axes[4,col].set_xlabel('Absolute time (ns)')
    for row,label in enumerate(['P Cboot (V)','P CTRL (V)','P G - VIN (V)',
                                 'P main drain current (uA)','Differential error (mV)']):
        axes[row,0].set_ylabel(label)
    fig.suptitle('SS / 0.81 V | cold versus hot | same compact sampling devices and loads\n'
        'Full CDAC, fixed Q128 reference preset, N4 reset; no noise, mismatch or PEX\n'
        'Dotted: native actual opening/closing; analog curves: 20 ps compact estimates',fontsize=11)
    fig.savefig(OUT/'cold_hot_comparison.png',dpi=170)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    cold=json.loads((HERE/'cold_controls/manifest.json').read_text())
    finite=json.loads((HERE/'finite_history/manifest.json').read_text())
    stream=json.loads((HERE/'stream_package/package_manifest.json').read_text())
    expected={'low40':next(x for x in finite['variants'] if x['case']=='low40')['deck_sha256'],
              'long':stream['cases']['long']['sha256']}
    expected.update({x['name']:x['deck_sha256'] for x in cold['cases']})
    cases={}
    for case,temp in [('low40',125),('long',125),('low40cold',-40),('longcold',-40)]:
        cases[case]=inspect_case(case,temp,expected[case])
    result=dict(scope='existing SS hot/cold finite40 versus low-DC diagnostic controls',
        cases={k:r for k,(r,_) in cases.items()},
        minimum_precharge_time_ns=None,
        conclusion='cold finite40 history leaves reduced pump voltage and incomplete acquisition; cold low-DC precharged control establishes within the same formal sample contract',
        no_new_run_or_circuit_edit=True,
        limitation='low-DC equilibrium is not a measured finite-precharge duration; fixed preset/reset fixture is not the closed-loop ADC')
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    plot(cases)
    for case,(r,_) in cases.items():
        print(case,{k:r[k] for k in ['native_temperature_c','actual_acquisition_ns',
            'preclose_error_mv','net_turnoff_delta_mv','raw_held_source_error_mv','stress_failed_pairs']})


if __name__=='__main__':main()
