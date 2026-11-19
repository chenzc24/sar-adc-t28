# Behavioral Model Verification for B

The Python numerical and electrical Verilog-A models have their own evidence scopes. The `sar8-modules-v3` evidence on this page applies to its original module selections. The block results cover the later per-module selections, asymmetric RC and clear models, and standalone tests. [Block results](../blocks/README.md)

- All 16,400 existing deterministic records matched for codes, counts, and event times. [Numerical regression](modules_python.json)
- [Native module and mixed tests](modules_native.json) · [Provenance](modules_provenance.json) · [Run state](modules_status.json) · [Original warnings](modules_warnings.txt)
- [Model audit with historical locations, current sources, and digests](model_audit.json)

Simulation and analysis completed for `sar8-modules-v3` with zero failures and 42 independent output-pin reads.

| View | Result |
| --- | --- |
| `current` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `behavioral` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `comparator_xtor` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `cdac_xtor` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `sampler_xtor` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `control_xtor` | First frame and low, mid, and high codes matched, with eight comparisons and reference updates |
| `stuck` | Forced stall detected and reported as an incomplete conversion |

Sampler tracking and hold passed. Comparator positive and negative inputs with a 10 mV offset and reset also passed. In the fully behavioral core, the eight reference gate waveforms showed no simultaneous NMOS and PMOS turn-on.

The runs reported `CMI-2751`, `CMI-2752`, `CMI-2753`, `CMI-2754`, `CMI-2755`, `SFE-1131`, `SFE-2453`, `SPECTRE-16780`, `SPECTRE-16881`, and `VACOMP-2435`. Raw logs are in the collection directory in the run receipt and on the server. Use dedicated evidence for terminal-voltage reliability and analog accuracy.

The first measurement failed because instance-name capitalization omitted internal saved signals and a comparator probe was in reset. The second run exceeded the 768 MiB disk budget. The next run removed unused digital-output saves and used 1536 MiB for disk and 1024 MiB for RSS. [First measurement failure](modules_initial_failure.json) · [Resource failure](modules_resource_failure.json)

The test covers TT function, module interfaces, and events. The Verilog-A parameters approximate capacitance, input and drive, and delay. Use the transistor-level current view for Bootstrap startup, gate charge, PVT and native mismatch, terminal voltages, power, and PEX.

The 16,400-frame native cross-check applies to an earlier ADC macro source. Use its archived provenance for the scope. The numerical model matches B's 256 measured centers and ten TT short-test codes. Its largest timing difference at TT is about 0.13 ns. Ideal-source quantization differs from B's high-frequency codes by up to 3 LSB. [Historical native cross-check](native_crosscheck.json) · [Historical provenance](native_provenance.json) · [Numerical scope](python_crosscheck.json)
