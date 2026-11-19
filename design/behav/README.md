# Modular Behavioral Models for B

The models use the shared specification. Their B references and mixed-hierarchy tests have the scope recorded in their evidence. Use native transistor-level runs to qualify a physical baseline. [Shared specification](../../specs/arch.json)

| Function | Python | Verilog-A |
| --- | --- | --- |
| Configuration and results | [config.py](python/config.py) | [b_defaults.vh](veriloga/b_defaults.vh), generated from the specification |
| Sampling | [sampler.py](python/sampler.py) | [sampler.va](veriloga/sampler.va) |
| CDAC | [cdac.py](python/cdac.py) | [cdac.va](veriloga/cdac.va) |
| Comparator | [comparator.py](python/comparator.py) | [comparator.va](veriloga/comparator.va) |
| Asynchronous SAR | [sar.py](python/sar.py) | [sar.va](veriloga/sar.va) |
| Reference control and delay | [reference.py](python/reference.py) | [reference.va](veriloga/reference.va) |
| Asymmetric RC and clear delays | Separate characterization settings | [timing.va](veriloga/timing.va) |
| ADC assembly | [sar_adc.py](python/sar_adc.py) | [sar_adc_b.va](veriloga/sar_adc_b.va) |

The Python top level accepts separate `sampler/cdac/comparator/sar/reference` implementations and defaults to those listed above. The public imports are `AdcSpec`, `AnalogConfig`, `FrameResult`, and `SarAdcModel`. The numerical model uses effective bit weights and a first-order trial-settling approximation. It retains the event and code definitions for the original eight scenarios and supports algorithm, error-budget, and calibration studies.

```python
from design.behav.python import SarAdcModel, AnalogConfig
from design.behav.python.sampler import Sampler

adc = SarAdcModel()
frame = adc.convert(0.123)
sampler = Sampler(AnalogConfig(), tau_s=1e-9)
held = sampler.acquire(0.2, duration_s=40e-9)
frame = adc.convert(held)
```

Python `convert(vin)` takes the ideal differential value at sampling close. To study a finite sample window, first obtain the settled voltage with `acquire` or inject a `capture` implementation with tracking history. The independent `acquire` time constant applies only to that acquisition. The Verilog-A sampler connects directly to a time-varying source and capacitor network.

## Electrical Verilog-A Models

The Verilog-A top level connects all modules and uses B's 15-port order, with local supply names `VDD/VSS`. Each `.va` source defines its interface, parameters, and constraints.

- The sampler uses finite on- and off-resistance. The external capacitor stores charge on the CDAC top plate. Configure gain, offset, and approximate per-frame noise charge injection.
- Each CDAC side has 255 binary-weighted unit capacitors and one unit dummy. The model connects actual top-plate and reference nodes through `C·ddt(V)` and finite switch resistance. Set weight errors from LSB to MSB.
- The comparator precharges both outputs in the low phase and resolves after an input-dependent delay in the high phase. The model includes input capacitance and output resistance. It supports offset, noise, and a forced stall.
- The SAR consumes the comparator outputs and issues writes, reference updates, and the next comparison. New sampling cancels older pending events. The module uses the existing public interface without additional BUSY, VALID, or EOC ports.
- The reference captures D and CODE twice. It turns off the switches and waits for dead time before applying the next state. Its preset code is 128. The timing module supplies finite propagation times and edge rates.

The default unit capacitance is about 4.00407 fF, a constant-capacitance approximation taken from low-frequency characterization of the same geometry. The behavioral defaults are 50 Ω sampler resistance, 10 kΩ unit reference switch resistance, 100 Ω output resistance, 2 fF comparator input capacitance, and 100 ps non-overlap. The default noise is zero. Python and Spectre use independent random streams. Inject external Verilog-A reference noise through the testbench source. In Python, reference noise is a per-decision numerical parameter.

Python `weight_errors` changes effective threshold coefficients. Verilog-A `weight_error0..7` changes capacitors and therefore also changes total capacitance and load response. Extract effective coefficients from the electrical model before comparing nonideal weights.

Use transistor-level evidence for physical Bootstrap startup, nonlinear MOM behavior, kickback, PVT and native mismatch, terminal voltages, power, and PEX. The finite R/C and initialization in Verilog-A describe its own startup. Compare numerical trial timing and electrical network timing within their respective models.

The behavioral CDAC gate inputs sense voltage. Use `control_xtor` for control interfaces and function, and the transistor-level `current` view for real gate settling and drive power. Assign independent `noise_seed` values to Verilog-A instances when enabling noise. Noise statistics remain unqualified for this round.

## Module Selection and Testing

The view registry is the configuration source. `current` uses the current transistor-level design. `frozen-b` selects the historical regression. Mixed views use B's top-level connectivity and select implementations in generated test packages. [View registry](../../specs/views.json)

| View | Transistor-level implementation | Other core modules |
| --- | --- | --- |
| `behavioral` | Native peripheral loads | Verilog-A |
| `comparator_xtor` | Comparator | Verilog-A |
| `cdac_xtor` | CDAC and switches | Verilog-A |
| `sampler_xtor` | Bootstrap sampler | Verilog-A |
| `control_xtor` | SAR, reference control, and actual delays | Verilog-A |

A generated wrapper adapts the three-terminal Bootstrap with global supplies to the five-port sampler model. Other modules use their declared scalar port order. Use the existing Virtuoso connection for native work. These packages select the text netlist views.

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m tools.saradc prepare tt_short --view comparator_xtor --run-id sar8-comp-mixed-v1
.venv/Scripts/python.exe -m tools.saradc behav sim --run-id sar8-modules-v3
.venv/Scripts/python.exe -m tools.saradc behav follow --run-id sar8-modules-v3
```

`follow` waits once for a registered run, starts analysis when simulation succeeds, and collects results. It retains a failure for review. `status / analyze / collect` also work individually.

Use the behavioral testbench guide for conditions and the results index for measured evidence. The model audit tracks historical 10-bit, external bit-clock, and experiment-specific models. [Testbench guide](../../tb/behav/README.md) · [Results](../../results/behav/README.md) · [Model audit](../../results/behav/model_audit.json)

Override any of the six modules after selecting a view, for example `--view current --view comparator=va --view reference=va`. `sar_xtor / reference_xtor / timing_xtor` provide separate views. [Six standalone block tests](../../tb/blocks/README.md)

`timing.va` retains independent rising and fast reset delays for RC and clear. See the `timing_approximations` in `specs/views.json` for values and sources. The source is a standalone TT receiving-gate characterization. Full SAR fanout and PVT timing need native evidence. The archived `sar8-modules-v3` result applies to its original models and selections. Use each new run receipt for its own evidence.
