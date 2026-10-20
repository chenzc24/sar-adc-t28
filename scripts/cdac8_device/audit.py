"""Final readback and fresh-native-netlist identity; never patch an OA DUT."""
from __future__ import annotations
import re
import argparse
from common import OUT,ROOT,LIB,dump,load,sha
from oa import VirtuosoClient,READONLY,check,export

def canonical(text):
    return '\n'.join(x for x in text.splitlines() if not x.startswith('// Generated on:'))

def main(export_tag='final_audit'):
    c=VirtuosoClient.from_env(profile='t28_io')
    info=c.library.get(LIB)
    assert info.path=='/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28' and info.technology_library=='tsmcN28'
    preserved=[]
    for cell in READONLY:
        data=c.symbol.read_ports(LIB,cell) if cell=='sar_macro_controller_8b' else c.schematic.read(LIB,cell,param_filters=None,include_positions=True)
        assert data==load(f'oa/{cell}_before.json'),cell
        preserved.append(cell)
    cells=['cdac8_unit_candidate_'+x for x in 'abc']+['tb_cdac8_unit_char','cdac8_unit']
    cells += ['cdac8_bank_'+str(n) for n in (1,2,4,8,16,32,64,128)]
    cells += ['tb_cdac8_caps','cdac8_caps_ideal_switch']+['cdac8_ref_switch_b'+str(b) for b in range(8)]
    cells += ['cdac8_device','tb_cdac8_switch_char','tb_cdac8_device','tb_cdac8_sampling','tb_cdac8_sar','cdac8_device_nominal','tb_cdac8_nominal','tb_cdac8_nominal_sar','tb_cdac8_safephase','cdac8_ref18_b7','tb_cdac8_ref18_char','tb_cdac8_ideal_input']
    for cell in cells:
        # Detect unexpected changes before Check & Save can overwrite evidence.
        current=c.schematic.read(LIB,cell,param_filters=None,include_positions=True)
        assert current==load(f'oa/{cell}.json'),f'Unexpected owned-cell drift: {cell}'
        check(c,cell,symbol=False)
    for cell in ('cdac8_controller','cdac8_device_sequence'):
        ports=c.symbol.read_ports(LIB,cell);assert ports
        assert c.execute_skill(f'ddGetObj("{LIB}" "{cell}" "schematic")').output.strip()=='nil'
        remote=f'/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{cell}/veriloga/veriloga.va'
        r=c.ssh_runner.run_command(f"sha256sum '{remote}'",timeout=30)
        assert r.stdout.split()[0]==sha(ROOT/'models/veriloga'/f'{cell}.va'),(cell,r.stdout)
    exports=[]
    for cell,tag in [('tb_cdac8_unit_char','forced_mismatch'),('tb_cdac8_caps','initial'),('tb_cdac8_device','prep'),('tb_cdac8_safephase','initial'),('tb_cdac8_ref18_char','initial'),('tb_cdac8_ideal_input','initial')]+[(x,'balanced') for x in ('tb_cdac8_switch_char','tb_cdac8_sampling','tb_cdac8_sar','tb_cdac8_nominal','tb_cdac8_nominal_sar')]:
        target=OUT/'oa_netlists'/cell/export_tag/'input.scs'
        if not target.exists():export(c,cell,export_tag)
        baseline=OUT/'oa_netlists'/cell/tag/'input.scs'
        equal=canonical(target.read_text())==canonical(baseline.read_text())
        assert equal,cell
        exports.append({'cell':cell,'compared_tag':tag,'equal_except_timestamp':equal,'sha256':sha(target)})
    literal=(OUT/'oa_netlists/tb_cdac8_sampling/balanced/input.scs').read_text()
    for count in (1,2,4,8,16,32,64,128):
        body=re.search(rf'(?ms)^subckt cdac8_bank_{count} .*?^ends cdac8_bank_{count}$',literal)[0]
        assert len(re.findall(r'(?m)^\s*XU\d+ ',body))==count
    unit=re.search(r'(?ms)^subckt cdac8_unit .*?^ends cdac8_unit$',literal)[0]
    assert 'cfmom_2t' in unit and 'multi=1' in unit and 'mismatchflag=1' in unit
    top='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs'
    model_hash=c.ssh_runner.run_command(f"sha256sum '{top}'",timeout=30).stdout.split()[0]
    assert re.fullmatch('[0-9a-f]{64}',model_hash)
    dump('audit.json',{'zero_marker_schematics':cells,'va_cells_without_dummy_schematic':['cdac8_controller','cdac8_device_sequence'],
        'readonly_equal':preserved,'fresh_exports':exports,'literal_independent_units':512,'va_source_equal':True,
        'model_top_sha256':model_hash,'model_top':top})
    print('AUDIT_OK',len(cells),'schematics;',len(exports),'fresh exports')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export-tag',default='final_audit')
    args=parser.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',args.export_tag)
    main(args.export_tag)
