"""Generate and run 8-bit clocked ideal/noisy VA, with compact sampled output."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import ROOT, OUT, LSB, stage, run_batch

MODEL = ROOT / "models/veriloga/sar_adc_ideal_8b.va"


def deck(case):
    n = 2048 if case == "static" else 16384
    stop = 195e-9 if case == "timing" else n * 100e-9
    lines = ["// SAR_ADC_T28 clocked eight-bit flat golden model testbench",
             "simulator lang=spectre", "global 0",
             "VVDD (vdd 0) vsource dc=.9 type=dc", "VVSS (vss 0) vsource dc=0 type=dc",
             "VREFP (vrefp 0) vsource dc=.9 type=dc", "VREFN (vrefn 0) vsource dc=0 type=dc",
             f"VRST (rst_n 0) vsource type=pwl wave=[0 0 5n 0 10n .9 {stop:.14g} .9]",
             "VSAMPLE (clk_sample 0) vsource type=pulse val0=.9 val1=0 delay=40n rise=20p fall=20p width=60n period=100n",
             "VSAR (clk_sar 0) vsource type=pulse val0=0 val1=.9 delay=42.5n rise=20p fall=20p width=2.5n period=5n"]
    if case == "timing":
        lines.extend(["VINP (vinp 0) vsource type=pwl wave=[0 .675 50n .675 60n .2255 195n .2255]",
                      "VINN (vinn 0) vsource type=pwl wave=[0 .225 50n .225 60n .6745 195n .6745]"])
    elif case == "static":
        low, high = .9 / (2*n), .9 - .9 / (2*n)
        end = 40.01e-9 + (n-1) * 100e-9
        lines.extend([f"VINP (vinp 0) vsource type=pwl wave=[0 {low:.14g} 40.01n {low:.14g} {end:.14g} {high:.14g} {stop:.14g} {high:.14g}]",
                      f"VINN (vinn 0) vsource type=pwl wave=[0 {high:.14g} 40.01n {high:.14g} {end:.14g} {low:.14g} {stop:.14g} {low:.14g}]"])
    else:
        freq = 10e6 * 7373 / n
        peak = .45 * 10**(-1/20)
        lines.extend([f"VINP (vinp 0) vsource type=sine sinedc=.45 ampl={peak:.14g} freq={freq:.14g}",
                      f"VINN (vinn 0) vsource type=sine sinedc=.45 ampl={-peak:.14g} freq={freq:.14g}"])
    ports = " ".join(f"dout_{b}" for b in range(7, -1, -1))
    noise = (f" sampling_noise_rms_v={.18*LSB:.14g} comparator_noise_rms_v={.18*LSB:.14g} reference_noise_rms_v={.12*LSB:.14g}"
             if case == "allocated_noise" else "")
    lines.extend([f"IADC (vinp vinn vrefp vrefn clk_sample clk_sar rst_n vdd vss {ports} busy valid) sar_adc_ideal_8b{noise}",
                  "simulatorOptions options reltol=1e-5 vabstol=1e-7 iabstol=1e-13 temp=27 tnom=27",
                  f"tran tran stop={stop:.14g} errpreset=conservative" + (" maxstep=1n" if case == "timing" else " strobeperiod=100n strobedelay=90n strobeoutput=strobeonly"),
                  "saveOptions options save=selected",
                  f"save valid busy clk_sample clk_sar {ports}",
                  f'ahdl_include "{MODEL.name}"'])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", choices=("timing", "static", "dynamic", "allocated_noise"), default=["timing", "static", "dynamic", "allocated_noise"])
    args = parser.parse_args()
    jobs = [stage("va8_" + c, deck(c)) for c in args.cases]
    run_batch(jobs, "veriloga", includes=[MODEL], workers=2)


if __name__ == "__main__":
    main()
