from dataclasses import asdict
from common import LIB, dump
from virtuoso_bridge import VirtuosoClient

def main():
    c = VirtuosoClient.from_env(profile='t28_io')
    lib = c.library.get(LIB)
    assert lib.path == '/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28'
    assert lib.technology_library == 'tsmcN28'
    dump('preflight/library.json', asdict(lib))
    dump('preflight/windows.json', c.list_windows())
    for cell in ['sar_bootstrap_canvas_flat_8b', 'sar_strongarm_t28',
                 'cdac8_unit', 'cdac8_device_nominal'] + [f'cdac8_bank_{1<<b}' for b in range(8)]:
        dump(f'preflight/{cell}.json', c.schematic.read(LIB, cell, param_filters=None, include_positions=True))
    targets = ['cdac10_dr_bank256', 'cdac10_dr_nominal', 'cdac10_dr_literal',
               'cdac10_dualrail_controller', 'cdac10_dualrail_input', 'cdac10_dualrail_comparator',
               'tb_cdac10_dr_nominal', 'tb_cdac10_dr_literal', 'tb_cdac10_dr_strongarm', 'tb_cdac10_dr_ideal_sample']
    targets += [f'cdac10_dr_sw_b{b}' for b in range(9)]
    for cell in targets:
        r = c.execute_skill(f'ddGetObj("{LIB}" "{cell}")')
        assert not r.errors and r.output.strip() == 'nil', (cell, r)
    print('PREFLIGHT_OK', lib.path, lib.technology_library, flush=True)

if __name__ == '__main__':
    main()
