"""Recover the register pin power in the preserved FF-hot output switching transient."""
from __future__ import division
import argparse
import json
import math
import os

from native_stream import samples


def read(path, stride):
    last = None
    for i, (t, row) in enumerate(samples(path)):
        last = t, row['va_dvdd:p'], row['xout.dvdd_reg'], row['vss_chip']
        if i % stride == 0:
            yield last
    if last is not None and i % stride:
        yield last


def reconstruct(rows):
    vb, rb, lb = .99, .0666667, 6.66667e-10
    ring, register, esr, cap = 5.617, 16.1, 4.08, 52.4e-12
    weight = register/(ring+register)
    tau = (ring*weight + esr)*cap
    derivative = weight*lb
    coeff = derivative/tau
    gc = 1/ring+1/register+1/esr
    power = [0., 0.]
    dur = [0., 0.]
    windows = [(70e-9,170e-9),(170e-9,270e-9)]
    old = next(rows)
    if abs(old[0]) > 1e-15:
        raise ValueError('Missing DC initial point')

    def forcing(row):
        _, i, vr, vg = row
        return weight*(vb-rb*i) + (1-weight)*vr - vg + coeff*i

    def load(row, z, didt):
        _, i, vr, vg = row
        chip = vb-rb*i-lb*didt
        vc = z-coeff*i+vg
        junction = (chip/ring+vr/register+vc/esr)/gc
        return (vr-vg)*(junction-vr)/register

    z = forcing(old)
    for row in rows:
        t0, i0, _, _ = old
        t1, i1, _, _ = row
        dt = t1-t0
        if dt <= 0:
            raise ValueError('Times out of order')
        x = dt/tau
        mix = -math.expm1(-x)
        f0, f1 = forcing(old), forcing(row)
        update = (1-mix)*z + mix*f0 + (1-mix/x)*(f1-f0)
        didt = (i1-i0)/dt
        p0, p1 = load(old,z,didt), load(row,update,didt)
        for j,(a,b) in enumerate(windows):
            start, stop = max(a,t0), min(b,t1)
            if start < stop:
                fraction = ((start+stop)/2-t0)/dt
                power[j] += (p0+fraction*(p1-p0))*(stop-start)
                dur[j] += stop-start
        old, z = row, update
    if any(abs(b-a-d) > 1e-12 for (a,b),d in zip(windows,dur)):
        raise ValueError('Incomplete original voltage trace')
    return dict(energy_J=power,register_uW=[e/d*1e6 for e,d in zip(power,dur)])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('--run-dir','--source-run-dir','--output-dir'):
        p.add_argument(name,required=True)
    a=p.parse_args()
    tb=open(os.path.join(a.source_run_dir,'inputs','test.scs')).read()
    periphery=open(os.path.join(a.source_run_dir,'inputs','sar8_output_path.scs')).read()
    netlist=tb+'\n'+periphery
    proof=['VDVDD_SRC (DVDD_BRD 0) vsource dc=SUP type=dc', 'parameters SUP=0.99',
           'VA_DVDD (DVDD_BRD DVDD_A) vsource dc=0 type=dc',
           'LBND_DVDD (DVDD_A DVDD_B) inductor l=6.66667e-10',
           'RBND_DVDD (DVDD_B DVDD_CHIP) resistor r=0.0666667',
           'RDVDD_RING (DVDD DVDD_J) resistor r=5.617',
           'RDVDD_REG (DVDD_J DVDD_REG) resistor r=16.1',
           'RDVDD_DEC (DVDD_J DVDD_DEC) resistor r=4.08',
           'CDVDD_DEC (DVDD_DEC VSS) capacitor c=52.4p']
    if any(x not in netlist for x in proof):
        raise ValueError('Frozen supply network differs')
    path=os.path.join(a.source_run_dir,'raw','tran_short.tran.tran')
    rates=[dict(stride=k, **reconstruct(read(path,k))) for k in (1,2,4)]
    with open(os.path.join(a.output_dir,'result.json'),'w') as out:
        json.dump(dict(source='sar8-ffh-loaded-io-energy-a',waves=rates,windows_ns=[[70,170],[170,270]]),out,indent=2)


if __name__=='__main__':
    main()
