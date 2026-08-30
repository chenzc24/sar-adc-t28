# Architecture

## Baseline signal path

`VINP/VINN -> sampling network -> differential split CDAC -> StrongARM comparator -> SAR logic -> DOUT<9:0>`

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

