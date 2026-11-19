# Circuit Design

The top-level master is `sar_adc8_join_r4`. Use the DUT file for the complete include chain and the manifest for ports, subcircuit ownership, and provenance. [ADC top](top/adc_top.scs) · [DUT entry point](dut.scs) · [Design manifest](manifest.json)

| Module | Implementation |
| --- | --- |
| Bootstrap sampling | [bootstrap.scs](xtor/bootstrap/bootstrap.scs) |
| Eighteen MOM capacitors and bit-scaled reference switches | [cdac.scs](xtor/cdac/cdac.scs) |
| 11-MOS StrongARM | [comparator.scs](xtor/comparator/comparator.scs) |
| Asynchronous SAR with a native reset OR at the data D input | [reset_data_or_std_delay.scs](xtor/sar/reset_data_or_std_delay.scs) |
| Minimal reference driver and shared idle control | [minimal_msb_d2.scs](xtor/reference/minimal_msb_d2.scs) · [Design notes](xtor/reference/minimal_direct.md) |
| Qualified standard-cell delay chains | [delays_std.scs](xtor/clock/delays_std.scs) |
| Native standard-cell wrappers | [standard_cells.scs](xtor/common/standard_cells.scs) |

Frozen B preserves the byte-level inputs for reproducing its measured cases. The current modular view uses the minimal MSB D2 reference driver and the SAR data-reset OR. Use the manifest for exact definitions and reachability. The previous reference implementation is in `xtor/reference/reference.scs`. Existing results retain their original source digests. [Frozen B DUT](frozen/b/dut.scs)

The PDK and native standard-cell libraries are stored on the server. Each test deck specifies the model sections.

The current RNL views include the standard delay chains and the native reset OR. The exported drawings and the electrical source use the same device parameters. Drawing records are `// @RNL` comments in source netlists. The viewer supports hierarchy navigation, zoom, source browsing, and SVG export. The offline page can be opened directly. The RNL manifest records sources and digests. Spectre consumes the text circuit and OA synchronization has its own evidence. [RNL guide](../docs/schematics/README.md) · [Symbols](rnl/sar8.rnl) · [Offline viewer](../docs/schematics/index.html) · [Drawing manifest](rnl/manifest.json) · [Candidate conventions](xtor/README.md)

The Verilog-A and Python views approximate B timing and follow the external interface. Use them for algorithms, error parameters, and protocol cross-checks. Native measurements belong to their respective physical inputs. [Behavioral model guide](behav/README.md)
