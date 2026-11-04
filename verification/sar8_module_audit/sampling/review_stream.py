"""Review collected compact sampling data; native events, compact analog estimates."""
import argparse
import json
from pathlib import Path


def summarize(events, at, names):
    held=141.8e-9
    events={k:sorted(v) for k,v in events.items()}
    seq=events.get(names['seq_sample'],[])
    closes=[t for t,up in seq if not up and t>=141e-9]
    close=closes[0] if closes else None
    opens=[t for t,up in seq if up and 101e-9<=t<(close if close is not None else held)]
    opening=opens[-1] if opens else None
    diff=lambda t:at(names['top_p'],t)-at(names['top_n'],t)
    source=lambda t:at(names['vin_p_source'],t)-at(names['vin_n_source'],t)
    after=close is not None and close<held
    pre=close-.2e-9 if close is not None else None
    evidence={key:[dict(time_ns=t*1e9,up=up) for t,up in events.get(names[key],[])]
        for key in ['sample','sample_int','sample_and','sample_match','qual','seq_sample','cmp_reset']}
    initial={key:at(names[key],0) for key in evidence}
    return dict(status='diagnostic_only',
        actual_close_ns=None if close is None else close*1e9,
        actual_open_ns=None if opening is None else opening*1e9,
        actual_acquisition_ns=None if opening is None or close is None else (close-opening)*1e9,
        opening_observed=opening is not None,
        normal_sampling_evaluable=opening is not None and after,
        held_time_ns=141.8,held_after_actual_close=after,
        raw_held_diff_mv=diff(held)*1000,
        raw_held_source_error_mv=(diff(held)-source(held))*1000,
        held_error_for_sampling_mv=(diff(held)-source(held))*1000 if after else None,
        preclose_time_ns=None if pre is None else pre*1e9,
        preclose_error_mv=None if pre is None else (diff(pre)-source(pre))*1000,
        net_turnoff_change_mv=None if pre is None or not after else (diff(held)-diff(pre))*1000,
        native_clock_events=evidence,initial_clock_levels_v=initial,
        boot_at_held={side:dict(g_minus_vin_v=at(names['boot_'+side+'_g'],held)-at(names['vin_'+side],held),
            cboot_v=at(names['boot_'+side+'_btop'],held)-at(names['boot_'+side+'_bbot'],held)) for side in ['p','n']},
        reset_at_held_v=at(names['cmp_reset'],held),
        analog_value_provenance='20ps compact linear interpolation; native events are separate',
        filtered_history_interpretation='If source short-low transitions exist but SEQ opening does not, preserve absent edge; no acquisition duration or normal-pass inferred',
        startup_accuracy_pass=None,droop_pass=None)


def main():
    p=argparse.ArgumentParser();p.add_argument('derived',type=Path);p.add_argument('--mapping',type=Path,required=True)
    a=p.parse_args()
    import numpy as np
    mapping=json.loads(a.mapping.read_text());meta=json.loads((a.derived/'wave.meta.json').read_text())
    assert meta['PSF_END'] and abs(meta['last_time_s']-160e-9)<1e-15
    names=(a.derived/'wave.columns').read_text().splitlines()
    assert len(names)==meta['columns']
    assert (a.derived/'wave.bin').stat().st_size==meta['points']*len(names)*8
    wave=np.memmap(a.derived/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],len(names)))
    cols={n:i for i,n in enumerate(names)};times=wave[:,cols['time']]
    assert times[0]==0 and np.all(np.diff(times)>0) and times[-1]>=141.8e-9
    at=lambda n,t:float(np.interp(t,times,wave[:,cols[n]]))
    events={}
    for line in (a.derived/'wave.events.tsv').read_text().splitlines():
        name,up,t=line.split();events.setdefault(name,[]).append((float(t),int(up)))
    print(json.dumps(summarize(events,at,mapping['signal_map']),indent=2))


if __name__=='__main__':main()
