"""Focused candidate invariants and native parser fixture; no remote execution."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from prepare import ROOT,BASE,mapping

run=sys.argv[1];folder=ROOT/'output/sar8_physical_repair'/run
source=(BASE/'dut.scs').read_text();dut=(folder/'dut.scs').read_text()
old=mapping(source);new=mapping(dut)
models=['nch_mac','pch_mac','nch_18_mac','pch_18_mac']
assert {k:v for k,v in old.items() if v['model'] in models}=={k:v for k,v in new.items() if v['model'] in models}
assert len(new)-len(old)==32
assert all(new[k]==v for k,v in old.items() if v['model']!='rupolym')
assert (BASE/'r4_perf_monitor.va').read_bytes()==(folder/'r4_perf_monitor.va').read_bytes()
test=ROOT/'output/sar8_physical_repair/parser_fixture';test.mkdir(exist_ok=True)
parser=(folder/'stream.cpp').read_text()
# Windows-only resource-reporting shim; parsing/export/peak algorithms unchanged.
portable=parser.replace('#include <sys/resource.h>',
    'struct rusage { long ru_maxrss; }; const int RUSAGE_SELF=0; int getrusage(int,rusage* u){u->ru_maxrss=0;return 0;}')
(test/'stream.cpp').write_text(portable)
subprocess.run(['g++','-O2','-std=c++11',str(test/'stream.cpp'),'-o',str(test/'stream.exe')],check=True)
(test/'fixture.psf').write_text('SWEEP\n"time" "time"\nTRACE\n"A" "V"\n"P" GROUP 1\n"I:1" "I" PROP(\n"units" "A"\n)\nVALUE\n"time" 0\n"A" 0\n"P" 1\n"time" 1e-12\n"A" 9\n"time" 2e-12\n"A" 0\n"time" 11e-12\n"P" -2\n"time" 12e-12\n"A" 1\nEND\n')
(test/'selected.txt').write_text('a\ni:1\n');(test/'pairs.txt').write_text('0 a\na i:1\n')
subprocess.run([str(test/'stream.exe'),str(test/'fixture.psf'),str(test/'selected.txt'),str(test/'pairs.txt'),str(test/'wave')],check=True)
meta=json.loads((test/'wave.meta.json').read_text());peak=np.loadtxt(test/'wave.stress.tsv')
data=np.fromfile(test/'wave.bin',dtype='<f8').reshape((-1,3))
assert meta['native_points']==5 and meta['points']==3
assert peak[0,1]==9 and peak[0,2]==1e-12
assert np.allclose(data,[[0,0,1],[11e-12,0,-2],[12e-12,1,-2]],rtol=0,atol=1e-25)
assert 9 not in data[:,1], 'Fixture must hide narrow peak from plot yet retain it in stress'
res=dict(passed=True,run_id=run,source_MOS_unchanged=True,added_caps=32,
    monitor_unchanged=True,sparse_GROUP_current_PROP_fixture=True,unexported_spike_measured=True,
    full_native_points=5,compact_points=3,
    parser_sha256=hashlib.sha256(parser.encode()).hexdigest(),resource_reporting_shim_only=True)
(ROOT/'verification/sar8_physical_repair'/('validation_'+run+'.json')).write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
