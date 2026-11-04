"""Specific sequential review of the approved 2/10/40ns finite histories."""
import hashlib
import json
from pathlib import Path

import numpy as np

import builder as b
from review_results import read_case

HERE=Path(__file__).resolve().parent
OUT=HERE/'finite_results'
FROZEN=HERE/'finite_history/manifest.json'


def verify_case(case,meta):
    root=b.ROOT/'output/managed_execution/runs'/('sar8audit-sample-v2-'+case)
    receipt=json.loads((root/'collected/collection_receipt.json').read_text())
    total=0
    for item in receipt['files']:
        path=root/'collected'/item['name'];h=hashlib.sha256()
        with path.open('rb') as stream:
            for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
        assert path.stat().st_size==item['bytes'] and h.hexdigest()==item['sha256']
        total+=item['bytes']
    assert total<32*1024**2
    assert b.sha((root/'inputs/test.scs').read_bytes())==meta['deck_sha256']
    frozen=json.loads((HERE/'stream_package/package_manifest.json').read_text())
    for name in ['fixture_dut.scs','mapping.json','stream.cpp']:
        assert b.sha((root/'inputs'/name).read_bytes())==frozen['files'][name]['sha256']
    return total


def extract(case,meta,short_reference):
    total=verify_case(case,meta)
    r,w=read_case(case)
    initial=r['snapshots']['DC']
    keys=['g','btop','bbot','ctrl','greset','clksb','vin_v','top_v']
    delta=max(abs(initial[side][key]-short_reference['snapshots']['DC'][side][key])
              for side in ['p','n'] for key in keys)
    r['initial_DC_max_abs_delta_vs_frozen_short_v']=delta
    r['initial_DC_compared_keys']=keys
    r['receipt_all_hashes_verified']=True
    r['frozen_input_hashes_verified']=True
    r['external_low_plateau_ns']=meta['timing']['external_low_plateau_ns']
    assert r['held_after_actual_close'] and r['opening_observed']
    assert delta<1e-6
    r['historical_static_diagnostic_screen']=dict(limit_mv=1.7578125,
        preclose=abs(r['preclose_error_mv'])<1.7578125,
        held=abs(r['raw_held_source_error_mv'])<1.7578125,
        independent_startup_budget=False)
    cache={'time_ns':np.linspace(55,143,4401)}
    names=w['names']
    wanted=['seq_sample','top_p','top_n','vin_p','vin_n']
    wanted+=['boot_'+side+'_'+node for side in ['p','n'] for node in ['g','btop','bbot','ctrl']]
    at=w['at']
    for key in wanted:
        cache[key]=np.interp(cache['time_ns']*1e-9,w['t'],w['matrix'][:,w['indices'][names[key]]])
    rows=json.loads((HERE/'compact_v2/boundary_loads.json').read_text())['device_mapping_without_geometry']
    labels={x['instance']:x['label'].lower() for x in rows}
    for side in ['p','n']:
        currents=[]
        for instance in ['Mmain','Mmain_U1']:
            node='xf.'+labels['XDUT.XBOOT'+side.upper()+'.'+instance]+':1'
            currents.append(np.interp(cache['time_ns']*1e-9,w['t'],w['matrix'][:,w['indices'][node]]))
        cache['main_'+side+'_ua']=sum(currents)*1e6
        r['snapshots']['at110ns'][side]['main_total_drain_ua']=sum(
            r['snapshots']['at110ns'][side][n+'_drain_ua'] for n in ['Mmain','Mmain_U1'])
    # Avoid keeping all collected waveforms open/resident while plotting cases.
    w['matrix']._mmap.close()
    return r,cache


def plot(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'low2':'#c64e41','low10':'#b18016','low40':'#197f89'}
    fig,axes=plt.subplots(8,1,figsize=(11,14),sharex=True,layout='constrained')
    first=max(r['actual_open_ns'] for r,_ in cases.values())
    last=min(r['actual_close_ns'] for r,_ in cases.values())
    for row,(case,(r,w)) in enumerate(cases.items()):
        x=w['time_ns'];color=colors[case];label=str(r['external_low_plateau_ns'])+' ns external low'
        axes[0].plot(x,w['seq_sample']/.81*.65+row,color=color,lw=1.5)
        axes[1].plot(x,w['boot_p_btop']-w['boot_p_bbot'],color=color,label=label)
        axes[2].plot(x,w['boot_p_bbot'],color=color,label=label)
        axes[3].plot(x,w['boot_p_ctrl'],color=color,label=label)
        axes[4].plot(x,w['boot_p_g']-w['vin_p'],color=color,label=label)
        axes[5].plot(x,w['main_p_ua'],color=color,label=label)
        axes[6].plot(x,w['main_n_ua'],color=color,label=label)
        # Source is +.81V before the original100.2-100.3ns reversal.
        source=np.interp(x,[0,100.2,100.3,160],[.81,.81,-.81,-.81])
        axes[7].plot(x,(w['top_p']-w['top_n']-source)*1000,color=color,label=label)
    axes[0].set_yticks([.325,1.325,2.325],['2 ns','10 ns','40 ns'])
    axes[0].set_ylabel('SEQ_SAMPLE\n0/.81 V each row')
    axes[1].set_ylabel('P Cboot (V)');axes[1].axhline(.81,color='#777',ls='--',lw=.8)
    axes[2].set_ylabel('P BBOT (V)')
    axes[3].set_ylabel('P CTRL (V)')
    axes[4].set_ylabel('P G - VIN (V)');axes[4].axhline(0,color='#777',lw=.8)
    axes[5].set_ylabel('P main drain\ncurrent (uA)')
    axes[6].set_ylabel('N main drain\ncurrent (uA)')
    axes[7].set_ylabel('Differential\nerror (mV)')
    axes[7].set_yscale('symlog',linthresh=1)
    axes[7].axhspan(-1.7578125,1.7578125,color='#6c9',alpha=.18)
    for ax in axes:
        ax.axvspan(first,last,color='#777',alpha=.07)
        ax.axvline(100.25,color='#666',ls=':',lw=.8)
        ax.grid(alpha=.18);ax.set_xlim(55,143)
    axes[1].legend(loc='upper left',ncol=3,fontsize=8)
    axes[-1].set_xlabel('Absolute time (ns) | dotted: original input reversal; gray: common actual acquisition interval')
    fig.suptitle('Finite low-history experiment | SS / 0.81 V / 125 C | 8-bit CDAC, N4 reset\n'
        'Same high-DC initial state, devices, loads and input; external low plateau = 2 / 10 / 40 ns\n'
        'Native clock events; 20 ps compact analog estimates | no noise, mismatch or PEX',fontsize=11)
    fig.savefig(OUT/'finite_history_rows.png',dpi=170)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    manifest=json.loads(FROZEN.read_text())
    refs=json.loads((HERE/'result_review/results.json').read_text())['cases']
    cases={}
    for meta in manifest['variants']:
        cases[meta['case']]=extract(meta['case'],meta,refs['short'])
    finite=[abs(r['raw_held_source_error_mv']) for r,_ in cases.values()]
    including_short=[abs(refs['short']['raw_held_source_error_mv'])]+finite
    data=dict(scope='three finite external plateaus from the same high-DC state',
        cases={k:r for k,(r,_) in cases.items()},
        separate_references={key:{n:r[n] for n in ['actual_open_ns','actual_close_ns','observed_low_interval_ns',
            'preclose_error_mv','raw_held_source_error_mv']} for key,r in refs.items()},
        monotonic_sampled_finite_abs_held_error=all(a>=z for a,z in zip(finite,finite[1:])),
        monotonic_with_0p1ns_finite_control=all(a>=z for a,z in zip(including_short,including_short[1:])),
        smallest_tested_finite_plateau_passing_static_guard_ns=40,
        minimum_required_plateau_ns=None,
        interval_statement='10ns external plateau failed and40ns passed at tested conditions.10-40ns is a candidate refinement region, not a proven minimum-time interval.',
        no_new_run_or_input_edit=True)
    (OUT/'results.json').write_text(json.dumps(data,indent=2)+'\n')
    plot(cases)
    for case,(r,_) in cases.items():
        print(case,{k:r[k] for k in ['external_low_plateau_ns','observed_low_interval_ns',
            'preclose_error_mv','raw_held_source_error_mv','initial_DC_max_abs_delta_vs_frozen_short_v']})


if __name__=='__main__':main()
