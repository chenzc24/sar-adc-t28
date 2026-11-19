# Testbenches

The table lists templates for previously verified test conditions. Daily runs use the current transistor-level design. Select frozen B explicitly for its regression. [Verilog-A and Python tests](behav/README.md)

Each standalone transistor-level or Verilog-A block test uses the module's actual interface and declares its native load and environment substitutes. The schematic viewer can also show the generated testbench. [Standalone block tests](blocks/README.md) · [Schematic viewer](../docs/schematics/index.html)

The test files live in this directory. The registry records input digests, historical identities, conditions, and budgets. [Test registry](../specs/tests.json)

| Case | Entry point |
| --- | --- |
| `tt_short` | [Short transient](top/short/test.scs) |
| `tt_fft1024` | [FFT test](top/fft/test.scs) |
| `tt_static_low` | [Low-code static test](top/static/test.scs) |
| `mc_cold_ss` | [SS-cold Monte Carlo](top/mc_ss_cold/test.scs) |
| `mc_cold_ff` | [FF-cold Monte Carlo](top/mc_ff_cold/test.scs) |
| `mc_comparator_tt` | [Comparator Monte Carlo](blocks/comparator/test.scs) |
| `mc_cdac_tt` | [CDAC Monte Carlo](blocks/cdac/test.scs) |

`test.scs` defines models, analysis, and saves. `tb.scs` defines stimulus, the actual load, and the DUT instance. Verilog-A observers are in `common/veriloga/`. Measurement code is in `tools/saradc/measure/`.

The ADC testbench uses 50 Ω input and reference source resistance, 4 pF reference bypass, and a 5 fF digital load per output. The external clock starts with 60 ns low and 40 ns high. Read the actual deck for exact values and model sections.

`tt_static_low` keeps the verified first three transitions. The completed full-code measurements contain 255 transitions and 256 code centers. Trace the remaining segments through historical run definitions in the workspace.

`prepare CASE --seed N` generates one sample from its MC template. The closed-loop local-mismatch cases cover the comparator and CDAC. The deck selects the native MOS and MOM statistical models. The default `--view current` binds the current design. Use `--view frozen-b` for the original regression inputs. The standalone comparator case replaces its embedded comparator definition. The CDAC bit-weight fixture uses the geometry and multiplicities of the current 18 MOM instances. Its scope is standalone statistical characterization.

A mixed view such as `tt_short --view comparator_xtor` keeps the selected module transistor-level and uses electrical Verilog-A models for the other core modules. [View registry](../specs/views.json)
