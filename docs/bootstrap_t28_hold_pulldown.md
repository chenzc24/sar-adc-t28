# T28 GMAIN hold pull-down: first full-CDAC iteration

Date: 2026-09-30. This is a **copied-netlist partial transistor-level
screen**, not a revised Virtuoso schematic or a completed bootstrap switch.
The exact full-CDAC OA export and protected-bootstrap transformation are
those documented in `docs/bootstrap_full_cdac_isolation.md`. In its
ideal-clamp, `GMAIN=VSS` deck, the only electrical change is replacing the
single ideal `SHOLD` relay definition with
`MN14 (GMAIN OFF_MAIN VSS VSS) nch_18_mac`. Because the subcircuit is called
24 times, the change affects 22 bottom-input and two top-control switches.
`STRACK` from the boost node `G` to `GMAIN` remains an ideal relay. The
inherited netlist comment immediately before `STRACK` refers to the earlier
two-relay source and is superseded by the actual `MN14` instance line.

`MN14` uses the already-exported T28 1.8-V NMOS `MN7` geometry as a
starting template: `l=150 nm`, `w=320 nm`, `nf=1`, with `multi=4, 16, 64`
screened. Its gate is driven by the existing ideal 0/0.9-V `OFF_MAIN`
source; drain is `GMAIN`, source/body are `VSS`. The original CDAC,
ideal top/split clamp, PHI/PHIB/BASE timing, 50-ohm input sources, and
model includes were unchanged. The simulation is Spectre 21.1,
TT MOS/resistor/capacitor sections of the exported T28 model,
0.9-V supply, 27 C, 285-ns transient with 10-ps maximum step. This is a
deterministic static-input screen; the exported `noise_worst` model include
does not mean transient noise was enabled.

## Measured result

The bottom-plate raw-error oracle after BASE/VCM handoff is
`-(TOPP_BP-TOPN_BP) - Vdiff`. The top-control oracle is
`(TOPP_TOP-TOPN_TOP) - Vdiff`. Both are read at 270 ns. A negative
`Vdiff` merely exchanges the P/N roles. Intermediate floating-node
voltages before BASE handoff are **not** final ADC errors.

| `MN14` multi | `Vdiff` (V) | Bottom raw error (mV) | Top-control raw error (mV) | Latest B9 `GMAIN<0.1 V` (ns) | Suppressed warnings |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | -0.8 | +0.004222 | +6.821762 | 250.454 | 1,338 |
| 4 | -0.4 | +0.001830 | +3.355530 | 250.445 | 550 |
| 4 | 0 | approximately 0 | approximately 0 | 250.439 | 550 |
| 4 | +0.4 | -0.001830 | -3.355530 | 250.445 | 550 |
| 4 | +0.8 | -0.004222 | -6.821762 | 250.454 | 1,338 |
| 16 | +0.8 | -0.004236 | -6.780879 | 250.406 | 5,512 |
| 64 | +0.8 | -0.004297 | -6.700250 | 250.395 | 11,010 |

The five-point `multi=4` bottom maximum is 0.004223 mV, below the
0.439-mV deterministic allocation and close to the previous *ideal*
`SHOLD` result of 0.004218 mV. At +0.8 V the representative high-side
MN11 270-ns drain current is about -0.0000218 uA, versus -6.25772 uA
for the rejected `GMAIN=VIN` candidate. The corresponding 50-ohm input
source current is +0.000611 uA instead of +68.8353 uA. This confirms
that the sustained reverse-conduction mechanism was suppressed in the
screened hold state. It does **not** prove absence of transient injection.

For `multi=4` at +0.8 V, the high-/low-side representative `GMAIN`
crosses below 0.1 V at 250.454/250.428 ns, giving 0.846/0.872 ns before
the 251.3-ns BOOT reset edge. `GMAIN` is still high at 250.34 ns because
`OFF_MAIN` has not finished rising; a single early checkpoint would give
the wrong conclusion. Increasing `multi` brings the crossing to
250.406/250.399 ns (`16`) and 250.395/250.389 ns (`64`), but hardly
changes held bottom error. It adds device capacitance and dramatically
increases printed/suppressed stress-warning activity. `multi=4` is only
the least-loaded next-screen candidate, **not** a frozen layout size.

## Limits and next circuit decision

All seven transients completed with zero Spectre errors and phase-order
checks passed. Each printed four pre-existing duplicate-model `SFE-1131`
warnings and ten CMI examples. At `multi=4`, printed CMI examples name
top-control `MP8`; at `multi=16/64`, some printed examples also name CDAC
bootstrap `MP8`. The simulator suppressed hundreds to thousands more
warnings, so their full device distribution is unknown. The representative
`MN14` sampled terminal peaks across the five-point `multi=4` sweep are
`|VDS|, |VGD| <= 1.578 V` and `|VGS| <= 0.9 V`; these are waveform
diagnostics, **not** foundry SOA clearance. The physical T28 clamp result
from the preceding experiment still fails, and was not improved here.

Most importantly, the top-control raw error remains as large as
6.822 mV, over the 0.439-mV allocation. The previous ideal-`SHOLD`
top-control endpoint was 8.753 mV; a modest change in that error from
adding `MN14` parasitics is not a top-path fix. `STRACK`, the `OFF_MAIN`
driver, clamp, and reference switches remain idealized. There is no
noise, mismatch, PVT, dynamic-input, extraction, next-cycle acquisition,
or full ADC performance claim.

**Decision:** retain separate main-gate control and off-before-reset
timing as the working architecture. Do not promote this netlist to OA or
claim sampling-block signoff. Next isolate why the top-control path and
physical clamp fail, then replace the remaining ideal `STRACK`/clock
drive with a stress-safe T28 circuit and rerun acquisition, full-range,
PVT and warning analysis. The exact generated decks, PSF, logs and case
JSON remain under ignored `output/bootstrap_t28_hold_pulldown/`; the
reproducer is
`scripts/characterization/screen_bootstrap_t28_hold_pulldown.py`.
