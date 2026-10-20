# Eight-bit device CDAC: native OA is the circuit source

No hand-patched final DUT or proprietary PDK model is tracked here.
`scripts/cdac8_device/oa.py` constructs the owned cells in `SAR_ADC_T28` through
supported APIs. `run.py` consumes their saved native Spectre exports and changes
only testbench variables, stimulus variants explicitly labeled in code,
numerical options, analyses and saved signals.

Generated exports, exact deck hashes, Spectre logs/PSF, model metadata, local
mismatch statistics and waveforms are in `output/cdac8_device/`. Exports under
`oa_netlists/<cell>/<revision>/input.scs` are immutable evidence. `audit.py`
compares fresh exports and unchanged historical dependencies. A solver's
`ok` is not a performance, device-stress or layout acceptance gate.

See [the device report](../../docs/cdac_flat_8b_device.md) for results and
explicit abstraction boundaries. In particular the 512-independent-unit array
is distinct from the nominal parallel-multiplier acceleration view. Only the
former is used for local capacitor mismatch.
