"""Focused native-stream products/events test including a frame boundary."""
import hashlib,json,subprocess
import numpy as np
from loaded import ROOT,parser_source

def main():
    folder=ROOT/'output/sar8_physical_repair/loaded_parser_fixture';folder.mkdir(exist_ok=True)
    source=parser_source()
    portable=source.replace('#include <sys/resource.h>',
        'struct rusage { long ru_maxrss; }; const int RUSAGE_SELF=0; int getrusage(int,rusage* u){u->ru_maxrss=0;return 0;}')
    (folder/'stream.cpp').write_text(portable)
    subprocess.run(['C:/Program Files/mingw64/bin/g++.exe','-O2','-std=c++11',str(folder/'stream.cpp'),'-o',str(folder/'stream.exe')],check=True)
    fixture='SWEEP\n"time" "time"\nTRACE\n"vdd!" "V"\n"a" "V"\n"p" GROUP 1\n"i:1" "I" PROP(\n"units" "A"\n)\nVALUE\n'
    fixture+='"time" 0\n"vdd!" 1\n"a" 0\n"p" -1\n'
    fixture+='"time" 1e-12\n"a" 9\n"time" 2e-12\n"a" 0\n'
    fixture+='"time" 5e-8\n"p" -2\n"time" 15e-8\n"p" -4\n"a" 1\n'
    fixture+='"time" 2e-7\n"p" -5\nEND\n'
    (folder/'fixture.psf').write_text(fixture)
    (folder/'selected.txt').write_text('vdd!\na\ni:1\n');(folder/'pairs.txt').write_text('0 a\n')
    (folder/'products.txt').write_text('supply vdd! i:1\n');(folder/'events.txt').write_text('a\n')
    subprocess.run([str(folder/'stream.exe'),str(folder/'fixture.psf'),str(folder/'selected.txt'),str(folder/'pairs.txt'),str(folder/'wave')],check=True)
    meta=json.loads((folder/'wave.meta.json').read_text())
    power=np.loadtxt(folder/'wave.products.tsv',usecols=(1,2))
    # Trapezoids on all native samples, with one boundary interpolated at 100ns.
    assert np.isclose(power[0,1],-1.99999e-7,rtol=0,atol=1e-20),power
    assert np.isclose(power[1,1],-4e-7,rtol=0,atol=1e-20),power
    peak=np.loadtxt(folder/'wave.stress.tsv');assert peak[1]==9 and peak[2]==1e-12
    ev=np.loadtxt(folder/'wave.events.tsv',usecols=(1,2));assert len(ev)==3
    assert np.isclose(ev[-1,1],100e-9,rtol=0,atol=1e-22)
    assert meta['native_points']==6 and meta['points']==4
    result=dict(passed=True,all_native_power=True,frame_boundary_split=True,sparse_GROUP_PROP=True,
                hidden_spike_stress=True,native_events=True,parser_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'verification/sar8_physical_repair/loaded_parser_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
