# Module and Mixed-Hierarchy Tests

Numerical module tests exercise public interfaces, including finite sampling settling, bit weights, comparator offset and delay, reference non-overlap, module replacement, and current and frozen packaging. The existing quantization and protocol tests cover the ADC. [Module tests](../../tests/test_modules.py) · [ADC tests](../../tests/test_behavioral.py)

`python -m tools.saradc behav prepare --run-id ID` creates a native test package under `work/behav/ID`. `behav sim` submits it through the same managed executor. Use the shared generator and analyzer for these cases. [Generator](../../tools/saradc/modular.py) · [Analyzer](../../tools/saradc/measure/analyze_modules.py)

Native tests cover the following conditions.

- Six low, mid, and high codes, including the first frame, across the current all-transistor design, the all-behavioral core, and transistor-level comparator, CDAC, sampler, and control/reference substitutions.
- A deliberately stalled comparator. Verify the partial code and exact stalled bit.
- A sampling switch with a 1 pF load. Observe tracking, close, and hold after the input moves.
- A comparator with 20 fF per output. Check positive and negative decisions, offset polarity, and reset of both outputs.
- Reference controls for all bits. Check for simultaneous NMOS and PMOS turn-on. Use public CMP_CLK and PHI_U waveforms to check per-bit events.

The mixed ADC short test uses 50 Ω input and reference impedance per terminal, 4 pF reference bypass, 5 fF output loads, and B's normal 60 ns low and 40 ns high external clock. The independent observer reads all eight output voltages 55 ns after sampling closes. [Verilog-A observer](observer.va)

Verilog-A resistances, capacitances, and delays are explicit approximations. Use the test for its covered interface and protocol, with separate evidence for analog accuracy, PVT, native mismatch, power, and terminal voltage. Keep original warnings, failed runs, and frozen provenance. [View configuration](../../specs/views.json)
