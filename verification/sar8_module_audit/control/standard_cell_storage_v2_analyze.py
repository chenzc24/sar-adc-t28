"""V2 selected-current coverage adapter; frozen functional/stress reducer reused."""
from __future__ import print_function

import standard_cell_full_analyze as frozen


def add_coverage(result,cfg):
    coverage=cfg['selected_current_coverage']
    if cfg['kcl_terms'] or cfg['critical_kcl_nodes'] or result['node_kcl']:
        raise ValueError('V2 declares no complete KCL measurement; refusing inconsistent coverage')
    if set(coverage['selected_current_names'])!=set(cfg['current_saves']):
        raise ValueError('Selected-current coverage differs from saved set')
    result['terminal_current_coverage']=coverage
    result['unsaved_terminal_currents_status']='unknown/unmeasured; not zero, not inferred from voltage correctness'
    result['KCL_coverage']=dict(status='unmeasured',complete_node_KCL_count=0,
        whole_fixture_KCL_pass=None,reason='Required incident gate/body/source/return currents deliberately not all saved; no partial sums presented as KCL.')
    result['current_interpretation']='Only selected native total terminal currents, positive into device. No unsaved current, whole-device current or full-node KCL inference.'
    result['voltage_terminal_screen_coverage']=dict(voltage_traces=len(cfg['voltage_saves']),
        observed_MOS=len(cfg['observed_mos']),simultaneous_pairs=len(cfg['stress_voltage_pairs']),
        all_original_voltage_and_physical_pairs_preserved=True)
    return result


def main():
    original=frozen.native.summarize
    def reduced(path,cfg,output):
        return add_coverage(original(path,cfg,output),cfg)
    frozen.native.summarize=reduced
    try:frozen.main()
    finally:frozen.native.summarize=original


if __name__=='__main__':main()
