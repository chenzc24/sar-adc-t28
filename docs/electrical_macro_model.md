# Topology-aware electrical macro-model

## Purpose and abstraction boundary

This is the complete **pre-transistor electrical macro-model** for the chosen
10-bit differential 5+5 split SAR architecture. “Complete” means that the
sampled nodes, every binary capacitor, bridge/dummy capacitors, bottom-plate
switches, reference memory, comparator regeneration, kickback path, reset,
and closed-loop SAR decisions coexist in one KCL/KVL simulation. It does not
mean PDK transistor, mismatch, PVT, reliability, or extracted-layout closure.

The executable source of truth is the curated Spectre hierarchy:

- `netlist/dut/sar_macro_10b.scs`: differential CDAC, switches, references,
  sampling paths, and dynamic comparator;
- `models/veriloga/sar_macro_controller_10b.va`: ten-decision event
  controller with statically unrolled electrical ports;
- `netlist/tb/tb_sar_macro_nominal.scs`: parameterized transient testbench;
- `scripts/analysis/run_electrical_macro_model.py`: capacitance-matrix oracle,
  stimulus generation, Spectre execution, waveform extraction, and gates.

The OA cells are a reviewable electrical mirror. The top-level OA testbench
netlists successfully, while the curated deck remains canonical because it
contains the closed-loop controller and deterministic result extraction.

## CDAC topology and charge model

Each side contains a 31-Cu MSB array, a 31-Cu active LSB array plus one-Cu
dummy, and a `(32/31)Cu` bridge. With no explicit parasitic capacitance, the
two-node capacitance matrix is

```text
[ 31Cu + Cbridge       -Cbridge ]
[     -Cbridge     32Cu+Cbridge ]
```

Inverting this matrix gives exactly the binary comparator-node couplings
`1/2, 1/4, ..., 1/1024`, unity total/base coupling, and an effective
comparator-side capacitance of `32Cu`. At the tracked comparison point
`Cu=6.86047 fF`, this is `219.53504 fF`.

The earlier isolated first-order fixture used `33Cu = 226.396 fF`. That value
is retained as a conservative historical load envelope; it is not the exact
load of the canonical split topology.

## Dynamic blocks

The acquisition path uses `Rsource=5 kOhm`, a `1 kOhm` relay-equivalent sample
switch, and the explicit CDAC. Each bottom plate has separate sample,
reference-zero, and reference-one switches with `Ron=1 kOhm` and
`Roff=1 TOhm`. The local references are driven through `100 Ohm` and have
`2 pF` decoupling, so code-dependent charge demand and reference recovery are
solved rather than inserted as a final scalar error.

The comparator contains an input transconductor (`60 uS`), differential
positive feedback (`100 uS`), a `20 fF` differential regeneration node,
reset switches, common-mode return, a configurable systematic offset, and a
direct kickback capacitance (`0.05 fF` nominal per side). The controller reads
the actual electrical comparator polarity at each latch edge.

The sample edge applies the MSB trial immediately. Bits 8 through 0 then use
explicit trial pulses. Every bit receives 3 ns CDAC settling followed by a
1.5 ns compare window; ten latches finish 49.5 ns after sampling, inside the
60 ns conversion allocation.

## Nominal Spectre results

Spectre 21.1 completed all eleven curated transients with zero simulator
errors. The six nominal code-center cases all matched both the ideal and
charge-conservation models:

| Target code | Spectre code | Max pre-compare residual | Max reference droop |
|---:|---:|---:|---:|
| 64 | 64 | 0.1019 LSB | 26.22 mV |
| 256 | 256 | 0.0583 LSB | 25.99 mV |
| 511 | 511 | 0.0583 LSB | 25.99 mV |
| 512 | 512 | 0.0582 LSB | 25.99 mV |
| 768 | 768 | 0.0873 LSB | 25.99 mV |
| 959 | 959 | 0.1019 LSB | 25.99 mV |

All nominal comparisons exceeded the 0.45 V resolution criterion, had the
correct sign, and stayed below the 0.25 LSB settling allocation. The nominal
ideal capacitance matrix has zero missing codes and only floating-point-level
DNL/INL.

## Sensitivity cases and interpretation

- Raising `Rref` to 500 Ohm and bottom-switch `Ron` to 1.8 kOhm produces
  2.697 LSB maximum settling error and one unresolved comparison. The final
  center-point code happens to remain 768; that does not make the case pass.
- Adding assumed `Ctop=5 fF` and bridge-node `Cpar=3 fF` changes the charge
  model and Spectre together: ideal centers 256/512/768 convert to
  250/512/774. Across the analytical transfer this illustrative assumption
  gives about `+/-11.58 LSB` INL. These capacitances are sensitivity inputs,
  not extracted PDK values.
- Increasing direct kickback to 1 fF changes code 768 to 769, creates
  1.739 LSB pre-compare error, and flips the last decision relative to the
  steady residual. This confirms that kickback is injected dynamically
  through capacitance, not added as an arbitrary output code.

## What remains for transistor design

The macro-model establishes topology, timing, and parameter sensitivities. It
does not freeze `Cu`, switch dimensions, a reference buffer, or comparator
device sizes. Random sampling/comparator/reference noise remains in the
separate top-down budget experiment; it is not double-counted in this
deterministic electrical closure. The next layer replaces one macro at a time
with PDK devices and adds nonlinear Ron, charge injection, clock feedthrough,
device/capacitor mismatch, PVT, Monte Carlo, and extracted parasitics.

Run the analytical and remote electrical regressions with:

```powershell
.venv\Scripts\python.exe scripts\analysis\run_electrical_macro_model.py

E:\bridge-Agent-T28\virtuoso-bridge-lite\.venv\Scripts\python.exe `
    scripts\analysis\run_electrical_macro_model.py --spectre --profile t28_io
```
