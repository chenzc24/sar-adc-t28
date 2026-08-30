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

Start with an ideal switch for system verification. Characterize a transmission-gate implementation next; introduce a bootstrapped switch only if settling or linearity cannot satisfy the 10-bit target.

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
