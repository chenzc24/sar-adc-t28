"""Python2-compatible bounded adapter around the existing native stream reducer."""
from __future__ import print_function
import argparse
import csv
import json
import os
import subprocess
import sys


def read_samples(path):
    with open(path) as f:
        return [dict((k, v if k in ['kind','label'] else float(v)) for k,v in row.items())
                for row in csv.DictReader(f, delimiter='\t')]


def summarize(mapping, samples, events, levels, products):
    result=[]
    for cycle in mapping['cycles']:
        i=cycle['index'];lo=cycle['start_ns']*1e-9;hi=lo+40e-9
        writes=[x for x in samples if x['kind']=='write_rise' and lo<=x['time_s']<hi]
        fixed=dict((x['label'],x) for x in samples if x['kind']=='fixed')
        before=fixed['pre_compare_'+str(i)]
        preupdate=fixed['pre_update_'+str(i)]
        late=fixed['pre_fall_'+str(i)]
        raw=[]
        for x in writes:
            bit=int(x['xdut.xctrl.data']>.5*x['vdd!'])
            dataedges=[e['time_s'] for e in events if e['node']=='xdut.xctrl.data' and e['time_s']<=x['time_s']]
            raw.append(dict(time_s=x['time_s'],DATA_v=x['xdut.xctrl.data'],
                DATA_half_supply_bit=bit,DATA_matches_expected_at_write=(bit==cycle['expected_DATA']),
                DATA_last_half_crossing_before_write_s=max(dataedges) if dataedges else None,
                DATA_expected_bit=cycle['expected_DATA'],D0_at_write_v=x['d0'],
                PR_v=x['xdut.xctrl.xtim.pr'],NR_v=x['xdut.xctrl.xtim.nr'],
                COMP_P_v=x['xdut.comp_p'],COMP_N_v=x['xdut.comp_n']))
        resetnodes=['xdut.comp_p','xdut.comp_n','xdut.xcomp.x','xdut.xcomp.y']
        result.append(dict(index=i,expected_DATA=cycle['expected_DATA'],expected_D0=cycle['expected_D0'],
            writes=raw,write_count=len(raw),
            clock_crossings=[x for x in samples if x['kind'] in ['clock_rise','clock_fall'] and lo<=x['time_s']<hi],
            native_half_supply_crossings=[x for x in events if lo<=x['time_s']<hi],
            pre_update_reset_levels_v=dict((n,preupdate[n]) for n in resetnodes),
            pre_compare_reset_levels_v=dict((n,before[n]) for n in resetnodes),
            pre_update_all_above_90pct=all(preupdate[n]>=.9*preupdate['vdd!'] for n in resetnodes),
            pre_compare_all_above_90pct=all(before[n]>=.9*before['vdd!'] for n in resetnodes),
            reset90_crossings=[x for x in levels if lo<=x['time_s']<hi],
            D0_before_diagnostic_fall_v=late['d0'],
            D0_before_diagnostic_fall_half_supply_bit=int(late['d0']>.5*late['vdd!']),
            D0_matches_expected_by_diagnostic_fall=(int(late['d0']>.5*late['vdd!'])==cycle['expected_D0']),
            observation_window_is_not_allocated_latency_budget=True))
    return dict(status='native_diagnostic_observations_not_qualification',cycles=result,
        VDD_energy_j=-sum(x['integral'] for x in products),energy_interval_s=[0,260e-9],
        native_event_threshold='0.5 instantaneous VDD',reset_measurement_level='0.9 instantaneous VDD; no new reset-time gate',
        DATA_D0_bit_threshold_scope='logic observation only; not a characterized receiver noise margin',
        timing_budgets_approved=False,all_performance_pass=None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();inp=os.path.join(a.run_dir,'inputs');out=a.output_dir
    subprocess.check_call([sys.executable,os.path.join(inp,'loaded_remote.py'),
                           '--run-dir',a.run_dir,'--output-dir',out])
    mapping=json.load(open(os.path.join(inp,'mapping.json')))
    samples=read_samples(os.path.join(out,'wave.samples.tsv'))
    def eventfile(name):
        rows=[]
        for line in open(os.path.join(out,name)):
            node,up,at=line.split();rows.append(dict(node=node,up=int(up),time_s=float(at)))
        return rows
    events=eventfile('wave.events.tsv');levels=eventfile('wave.reset90.tsv')
    products=[]
    for line in open(os.path.join(out,'wave.products.tsv')):
        name,interval,integral=line.split()
        assert name=='VDD' and int(interval)==0
        products.append(dict(name=name,integral=float(integral)))
    assert len(products)==1
    result=summarize(mapping,samples,events,levels,products)
    json.dump(result,open(os.path.join(out,'diagnostic.json'),'w'),indent=2)
    total=sum(os.path.getsize(os.path.join(root,n)) for root,dirs,files in os.walk(out) for n in files)
    assert total<=mapping['compact_collection_max_bytes'],('compact output limit',total)
    print('COMPARATOR_DIAGNOSTIC_OK bytes',total)


if __name__=='__main__':main()
