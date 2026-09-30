# Architecture

## Baseline signal path

`VINP/VINN -> sampling network -> differential split CDAC -> StrongARM comparator -> SAR logic -> DOUT<9:0>`

## Behavioral golden model

The executable stage-2 model is `models/behavioral/sar_adc.py`. It accepts the
differential signal `VINP - VINN` over `[-0.9, 0.9] V`, performs ten explicit
MSB-first decisions, and returns both raw decision bits and unsigned codes.

At ideal accuracy a 5+5 split CDAC has the same binary transfer weights as a
10-bit array. The golden model therefore checks the algorithm and system
metrics without pretending to model bridge-capacitor ratio error, parasitics,
switching trajectory, or finite settling. Those effects enter when the CDAC
is characterized.

## Blocks

### Sampling network

The initial ideal-switch, transmission-gate, and bottom-plate experiments
are historical development stages. The selected 2026-09-30 circuit line is
**top-plate sampling**: two input bootstrap switches connect VINP/VINN to
the comparator-side CDAC top nodes during acquisition; CDAC bottom plates
start at VCM and are switched to references during SAR conversion. The
top-plate differential polarity is positive (`TOPP-TOPN ≈ VINP-VINN`).
The current split-GMAIN/early-turn-off result is a mixed T28-core/ideal-
steering Spectre bound, not a completed sampling cell. Device-level control
experiments and their unresolved stress/clock limits are tracked in
`docs/sampling_architecture_status.md`.

### CDAC

Use a fully differential 5+5 split array. Unit capacitance and bridge capacitance are not fixed until the available PDK capacitor cells have been identified and characterized for kT/C noise, mismatch, parasitic ratio error, and settling.

### Comparator

Use the existing 28 nm StrongARM topology as the starting point. Verify delay, input-referred offset/noise, metastability, kickback, and reset behavior across PVT before integration.

### SAR logic and timing

Use synchronous control with a nominal 200 MHz internal bit clock. Allocate approximately 40 ns for acquisition and 60 ns for ten comparisons plus output handoff.

### Reference network

Use ideal VREFP/VREFN/VCM sources for the architectural baseline. Add reference source resistance, decoupling, and an optional buffer only after CDAC switching-current requirements are known.

## Stage-3 clocked Verilog-A contract

The local `sar_adc_ideal_10b` module is the executable timing contract between
the function-level Python golden model and later block-level or transistor
implementations. It is intentionally a single voltage-mode module so that
algorithm and timing can be verified before analog hierarchy is introduced.

### Interface

- Analog inputs: `VINP`, `VINN`, `VREFP`, and `VREFN`.
- Timing inputs: `CLK_SAMPLE` and `CLK_SAR`.
- Control and supplies: active-low `RST_N`, `VDD`, and `VSS`.
- Outputs: `DOUT<9:0>`, `BUSY`, and `VALID`.

`CLK_SAMPLE` is high during acquisition. Its falling edge captures
`V(VINP,VINN)`, clears `VALID`, and asserts `BUSY`. Each subsequent rising
edge of the nominal 200 MHz `CLK_SAR` resolves one bit, MSB first. The tenth
decision deasserts `BUSY` and asserts `VALID`, which remains high until the
next sample. With the nominal phases, conversion takes 47.5 ns and remains
inside the 60 ns conversion allocation.

The core exposes the SAR clock so the conversion state machine can be tested
without simultaneously designing clock generation. A later `sar_clock_gen`
may internalize this clock at the integrated top level.

### Nonideality controls

The ideal transfer is recovered when all nonideality parameters are zero.
Optional controls provide comparator offset, per-conversion sampling noise,
per-decision comparator and reference noise, ten explicit effective CDAC
weight errors, and a residual CDAC settling fraction. Fixed integer seeds make
the random contributions reproducible. Sample-clock jitter remains a
testbench stimulus because it changes the acquisition instant rather than the
ADC transfer calculation.

The nonideality controls are architectural sensitivity mechanisms. They do
not claim transistor-level independence, physical capacitor mismatch
statistics, comparator noise bandwidth, or reference-network memory.

## Stage-4B CDAC/reference first-order contract

The first module-level dynamic fixture treated the ideal 5+5 split array as a
conservative `Cside = 33*Cu` load per comparator side. A conservative independent
two-side kT/C estimate sets a nominal lower bound of `Cside = 82.787 fF` and
`Cu = 2.509 fF` at 300.15 K for the allocated 0.316406 mV RMS sampling noise.
This is not a matching- or layout-qualified capacitor size.

During conversion, the reference and selected CDAC switch are reduced to the
first-order Thevenin path `Rref + Ron`. The permitted sum is parameterized by
Cu and the settling portion of the 5 ns bit cycle. For example, the
characterized 6.86047 fF comparison point gives `Cside = 226.396 fF` and
permits 1.593 kΩ at 3 ns for the 0.25 LSB residual guardrail. Neither 3 ns nor
that capacitor is frozen.

The tracked analytical sweep and four correlated Spectre transients are
documented in `docs/cdac_reference_settling.md`. Code-dependent reference
memory, physical switch nonlinearity, reference/switch noise, mismatch,
charge injection, comparator kickback, and parasitics remain later-stage
transistor- and extracted-level work.

## Stage-4 module first-order closure

The remaining phase models are documented in
`docs/module_first_order_models.md`. At the 6.86047 fF comparison point, the
40 ns acquisition phase permits `Rsource + Ron <= 21.242 kΩ`, while a 3 ns
conversion-settling allocation permits `Rref + Ron <= 1.593 kΩ`. The latter is
the tighter switch/reference constraint.

For comparator timing sensitivity, a 20 fF regeneration node must provide
`gm_eff >= 92.42 uS` to amplify a 0.25 LSB initial differential to 0.45 V in
1.5 ns. The clock's tracked 20 ps RMS jitter produces 0.182464 LSB RMS error at
4.5 MHz and -1 dBFS. These values close the first-order constraint layer but
do not replace transistor noise, offset, nonlinear switch, PVT, mismatch, or
post-layout verification.

## Stage-4C topology-aware electrical macro-model

The topology-complete pre-transistor model is documented in
`docs/electrical_macro_model.md`. Unlike the isolated first-order fixtures, it
solves the full differential 5+5 capacitor network, every bottom-plate and
sampling switch, local reference impedance/decoupling, dynamic comparator
regeneration/reset/kickback, and ten closed-loop SAR decisions in one Spectre
transient.

The canonical split network is a 31-Cu active MSB array, a 32-Cu LSB array
including its dummy, and a `(32/31)Cu` bridge. Its exact comparator-side load
is `32Cu = 219.53504 fF` at the tracked `Cu=6.86047 fF`, while the older 33-Cu
fixture remains a conservative historical envelope. Six nominal code centers
complete in 49.52 ns, reproduce the charge-model code exactly, and keep every
pre-compare settling residual below 0.102 LSB.

This stage fixes the macro topology and phase interactions, not transistor
dimensions. Random noise remains a separate budget regression, and PDK PVT,
mismatch, nonlinear switch behavior, reliability, and extraction remain open.
