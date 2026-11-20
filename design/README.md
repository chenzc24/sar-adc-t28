# Circuit Design

The top-level master is `sar_adc8_join_r4`. Use the DUT file for the complete include chain and the manifest for ports, subcircuit ownership, and provenance. [ADC top](top/adc_top.scs) · [DUT entry point](dut.scs) · [Design manifest](manifest.json)

| Module | Implementation |
| --- | --- |
| Bootstrap sampling | [bootstrap.scs](xtor/bootstrap/bootstrap.scs) |
| Eighteen MOM capacitors and bit-scaled reference switches | [cdac.scs](xtor/cdac/cdac.scs) |
| 11-MOS StrongARM | [comparator.scs](xtor/comparator/comparator.scs) |
| Single-edge asynchronous SAR with registered per-bit delay taps | [single_edge.scs](xtor/sar/single_edge.scs) |
| Native-cell reference decoder and gate drives | [single_edge_d2.scs](xtor/reference/single_edge_d2.scs) |

The SAR, the reference word and the top instantiate native standard cells directly; there are no gate wrappers. Frozen B preserves the byte-level inputs for reproducing its measured cases. Earlier design versions were removed after commit `c46d9d6`; their results retain their original source digests. [Frozen B DUT](frozen/b/dut.scs) · [Adoption report](../results/design/sar_single_edge_adoption_20261120.md)

The PDK and native standard-cell libraries are stored on the server. Each test deck specifies the model sections.

The RNL views cover the single-edge SAR, the reference word and the top. The exported drawings and the electrical source use the same device parameters. Drawing records are `// @RNL` comments in source netlists. The viewer supports hierarchy navigation, zoom, source browsing, and SVG export. The offline page can be opened directly. The RNL manifest records sources and digests. Spectre consumes the text circuit and OA synchronization has its own evidence. [RNL guide](../docs/schematics/README.md) · [Symbols](rnl/sar8.rnl) · [Offline viewer](../docs/schematics/index.html) · [Drawing manifest](rnl/manifest.json) · [Candidate conventions](xtor/README.md)

The Verilog-A and Python views approximate B timing and follow the external interface. Use them for algorithms, error parameters, and protocol cross-checks. Native measurements belong to their respective physical inputs. [Behavioral model guide](behav/README.md)
