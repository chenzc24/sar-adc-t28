# Full-CDAC bootstrap sampling-order experiment

## Decision

The charge-conserving *bottom-plate sequence* is worth retaining as an
architectural option, but neither experimental implementation is ready to
promote. An ideal, zero-parasitic top clamp made the 0.5-ns-lead bottom-plate
path's maximum raw held error 0.00790 mV across five differential inputs,
versus 1.5320 mV for the top-plate baseline in the same full-CDAC fixture.
Replacing only that clamp with four T28 core NMOS devices yielded 2.0960 mV
at the ±0.8-V endpoints, above both the 0.439-mV allocation and the top-plate
baseline. Every transistor-containing case produced unresolved PDK SOA
warnings. The ideal-clamp result is not a physical-cell result.

This is a sampling/hold topology experiment, not a completed SAR ADC or a
production CDAC. The existing `sar_bootstrap` and production-planned cells
were not modified.

## OA sources and electrical fixture

| Variant | Experimental schematic | Clamp |
| --- | --- | --- |
| Ideal control | `SAR_ADC_T28/sar_cdac_bottom_plate_eval_10b` inside `tb_sar_bottom_plate_eval` | Four 10-Ω `analogLib` switches, infinite off resistance |
| T28 device | `SAR_ADC_T28/sar_cdac_bottom_plate_t28clamp_eval_10b` inside `tb_sar_bottom_plate_t28clamp_eval` | Four `tsmcN28/nch_mac`, L=30 nm, W=1 µm total, body at VSS |

Both CDAC schematics use the same differential 5+5 split, `Cu=6.86047 fF`,
31-Cu MSB array, 32-Cu LSB array including dummy, and `(32/31)Cu` bridge.
Each side has 11 input-driven bottom plates (10 bits and the dummy), each
connected by a copy of the existing T28 `sar_bootstrap`. The matched
top-plate baseline uses the existing `sar_cdac_macro_10b` and two copies of
the same bootstrap. Each testbench has separate 50-Ω differential sources for
the two paths. The four OA schematics read back with zero check markers;
the CDAC and testbench contain 93 and 21 electrical instances respectively.
The source of truth is the automatically exported OA Spectre netlist, not a
hand-built replacement subcircuit. The runner fills the four ADE design
variables, requests selected saves, and appends a transient analysis; it
does not edit device, connectivity, hierarchy, or PDK statements.

The ideal-control OA export SHA-256 is
`965cbc2f99712c0f5d72af0eefcf28abdf398340f31cff32d96a0e1fd36e50ac`;
the T28-clamp export is
`02c8ffc923915c279c1a316a1984e8cb677e6c3be06147a822f9d42aa36944ef`.
The generated decks, readback, waveforms, raw warnings, case CSV, analytical
summary, and phase traces are under ignored
`output/bootstrap_bottom_plate_eval/`.

Spectre 21.1 ran the exported `ttmacro_mos_moscap` plus the ADE-selected
resistor, capacitor, and ancillary model sections at VDD=0.9 V, VCM=0.45 V,
27 °C. Differential targets were −0.8, −0.4, 0, +0.4, +0.8 V at 0.45-V
input common mode (thus 0.05–0.85 V single-ended at the extremes). The input
changes at 205 ns; PHI samples from about 211 to 250 ns; the top and split
nodes are clamped until 0.5 ns before PHI falls; conversion-reference
switches close at about 252 ns; raw held error is read at 270 ns. Clock and
reference sources are ideal, and PDK noise was not enabled in this transient.

## Charge-conservation oracle

For one side, let `T` be the comparator top plate and `L` the split-array
node. With `CM=31Cu`, `CL=32Cu`, and `CB=(32/31)Cu`, the floating-node
capacitance matrix is

```text
[ CM+CB   -CB  ] [ ΔVT ]   [ ΣMSB Ci ΔVBi ]
[ -CB     CL+CB] [ ΔVL ] = [ ΣLSB Ci ΔVBi ]
```

During acquisition both `T` and `L` are held at VCM while all bottom plates
track `VIN`. Open the clamps first; open the bottom input switches second;
then move the bottoms to VCM. With ideal capacitors, both floating nodes move
by `VCM−VIN`, so `TOPP−TOPN = −(VINP−VINN)` before the SAR trials. Comparator
polarity therefore reverses relative to top-plate sampling. The matrix gives
exact binary trial weights: bit 9 = 1/2 of one-side reference movement through
bit 0 = 1/1024. A mathematical 1024-level static reference staircase is
monotonic with zero ideal DNL/INL and no missing codes. That calculation only
validates the ideal capacitor network; the Spectre fixture ties trial
references to VCM and does **not** measure physical 1024-code DNL/INL.

## Measured sampling results

All errors below are *raw*, without subtracting a fitted gain or offset.
The earlier 12.026-mV capacitor-to-ground test is a different load and is
not the baseline for this table.

| 0.5-ns clamp lead, TT/0.9 V/27 °C | Input set | Top-plate maximum | Bottom-plate maximum | B9 bottom-node acquisition maximum |
| --- | --- | ---: | ---: | ---: |
| Ideal top clamp | five points, −0.8 to +0.8 V | 1.5320 mV | 0.00790 mV | 0.00663 mV |
| T28 NMOS top clamp | five points, −0.8 to +0.8 V | 1.5351 mV | 2.0960 mV | 0.00663 mV |

The T28 clamp's zero-input differential error is essentially zero, while its
±0.8-V errors are equal and opposite. Its five-point fitted error slope is
−0.2602%, with 0.0288-mV maximum post-fit residual. The ideal-clamp
five-point slope was −0.000930%, with 0.000923-mV post-fit residual. These
fits are diagnostic and were not removed from the raw pass/fail values.
The T28 clamp also shifts held common mode down by roughly 0.66–0.74 mV.
Its single-ended top and split-node voltages at the clamp release show a
roughly 0.74-mV *common* step; the differential step largely cancels. The
remaining signal-dependent attenuation is consistent with the added NMOS
parasitic capacitances and finite off-state behavior, but this experiment
does not separate those causes quantitatively.

The bounded ideal-clamp timing screen kept the input constant near the edges:

| Clamp lead before PHI fall | Inputs checked | Maximum bottom raw error |
| --- | --- | ---: |
| 0.5 ns | all five | 0.007898 mV |
| 1.0 ns | ±0.8 V | 0.007898 mV |
| 2.0 ns | ±0.8 V | 0.007898 mV |

Changing this lead did not move the settled-input held result at displayed
precision. It does not validate a moving-input aperture or the physical
clamp's timing margin.

At −0.8 V, both paths were already tracking before clamp release. The
bottom-plate input node B9P−B9N was within 6.6 µV of target. After PHI falls,
the bottom-path top differential passes through a sizable transient (about
0.12 V at 250.2 ns) before the reference handoff, yet reaches its final
held value by about 252.3 ns. Thus a small final error does not imply small
intermediate excursions or a clean bottom-switch edge; comparator timing
must be measured after the reference transfer. The top-clamp release, not
the later bottom-switch opening, defines the ideal charge-sampling aperture.

## Limits and next target

The input is held static around the switching edges; this experiment does
not extract a physical effective aperture or its jitter sensitivity with a
time-varying input. The top-clamp edge is the charge-conservation aperture
only in the idealized sequencing argument. The commanded PHI-to-reference
handoff has about 2 ns of non-overlap, but branch currents were not saved;
absence of a transient source/reference short is not yet measured.

The bottom-path fixture instantiates 22 full bootstrap pumps versus two in
the top-plate comparator path. At 200-fF `CBOOT` plus two 50-fF pump
capacitors per instance, that is 6.6 pF versus 0.6 pF of *internal pump
capacitor inventory*, not a measured equivalent clock capacitance. The
ideal voltage clocks hide real clock-driver power and edge degradation.
Shared boosted-gate generation feeding separately timed bottom main devices
is a candidate for a later, bounded architecture study; the current 22-pump
schematic should not be adopted unchanged.

Spectre ended with zero errors but 34 printed warnings and roughly 2.2–2.6
million additional warnings suppressed per run. They include T28 core-device
terminal SOA violations (`CMI-2751` through `CMI-2756`) in the unchanged
bootstrap drivers. The added T28 clamp also trips `CMI-2754`: the printed
`Vgd` reaches at least −1.0526 V on `SCLAMPTOPN`, exceeding its 0.990-V
model limit during the input transition. The physical-clamp run's transient
summary records a 1.787-V maximum *node* voltage at `XBP.XB4P.P2`; this is
not a per-device terminal-voltage reconstruction. This experiment did not
measure every transistor's peak terminal stress or establish a permitted
foundry transient exception. The prior bootstrap study's approximately
1.787-V stress remains an independent blocker. Successful numerical
convergence is not reliability approval.

Do not promote either fixture or start global PVT/mismatch/extraction. The
next bounded targets are (1) a top clamp with measured off capacitance,
injection, and leakage below the raw 0.439-mV guardrail, preferably tested
with a shared-pump bottom-plate arrangement, and (2) protected bootstrap
drive or an allowed device class with resolved T28 terminal-voltage rules.
Only then run a physical full-code transfer, noise, PVT, and comparator timing
regression. The fitted-error numbers are diagnostics, not an authorized
calibration scheme.
