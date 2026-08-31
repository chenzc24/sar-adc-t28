# Bootstrapped main-switch PVT screening

## Outcome

The plain rail-to-rail transmission gate was replaced at the architecture
screening level by a bootstrapped NMOS main switch. All 27 real-PDK Spectre
jobs completed across SS/TT/FF, 0.81/0.90/0.99 V, and -40/27/125 C. The 18
device candidates produced 486 complete Ron curves and 486 off-state leakage
measurements; 14 candidates met `max Ron <= 1 kOhm` at every tested operating
point.

This establishes that the boosted-main-switch architecture is electrically
viable. It does not yet establish a reliable transistor-level bootstrap
driver or freeze a production switch.

## OA fixtures and method

Three intentionally small characterization schematics were created and
automatically exported from `SAR_ADC_T28`:

- `tb_bootstrap_core_main_char`: `tsmcN28/nch_mac`, body at VSS
- `tb_bootstrap_dnw_main_char`: `tsmcN28/nch_dnw_mac`, body at the lower signal terminal
- `tb_bootstrap_18_main_char`: `tsmcN28/nch_18_mac`, body at VSS

Each fixture contains one real PDK transistor, three DC sources, and ground.
The on-state command is the ideal screening relation
`Vgate = Vin_common_mode + VDD`; a 1-mV differential probe extracts Ron while
common mode sweeps from 1 mV to `VDD-1 mV`. The off fixture applies the full
VDD signal stress with gate at zero. The Spectre batch decks mechanically
replicate the transistor statements from the OA-exported netlists and retain
their SHA-256 hashes.

The ideal gate source is deliberate: it separates the main transistor choice
from finite bootstrap-capacitor droop, driver loss, non-overlap timing, charge
injection, and clock feedthrough. Those effects belong to the next transient
driver target.

## Key results

| Candidate | Worst Ron | Worst Ron corner | Ron flatness at worst corner | Maximum off leakage | Result |
|---|---:|---|---:|---:|---|
| core, L30/W0.75 | 770.8 Ohm | SS/0.81 V/125 C | 14.3% | 756 nA | minimum-width core pass |
| DNW, L30/W0.75 | 668.1 Ohm | SS/0.81 V/125 C | approximately zero | 756 nA | minimum-width overall pass |
| core, L40/W1 | 645.2 Ohm | SS/0.81 V/125 C | 17.3% | 200 nA | lower-leakage core option |
| DNW, L40/W1 | 542.5 Ohm | SS/0.81 V/125 C | approximately zero | 200 nA | balanced option |
| core, L60/W2 | 395.5 Ohm | SS/0.81 V/125 C | 20.8% | 144 nA | long-channel core option |
| DNW, L60/W2 | 321.2 Ohm | SS/0.81 V/125 C | approximately zero | 144 nA | preferred electrical seed |
| 1.8 V, L150/W8.96 | 964.5 Ohm | SS/0.81 V/-40 C | 69.1% | 65.3 nA | minimum-width 1.8-V pass |

The DNW L60/W2 point is the preferred electrical seed for the next driver
iteration. Relative to DNW L30/W2 it reduces the measured worst off leakage
from 2.017 uA to 143.8 nA (about 14 times) while retaining a 321.2-Ohm worst
Ron. Its body-tracked DC fixture also removes the common-mode Ron variation.
This is a sizing seed, not a final choice: dynamic body/junction behavior,
layout cost, capacitance, and charge injection remain unmeasured.

The 1.8-V device offers the lowest leakage among the globally passing points,
but needs 8.96 um width, only narrowly passes the Ron limit, and has much worse
common-mode flatness. It remains a reliability-oriented fallback rather than
the primary performance seed.

## Voltage-stress boundary

At the highest tested supply, the ideal gate command reaches 1.979 V absolute.
All families remain at approximately 0.9905 V maximum commanded `|VGS|` and
0.99 V `|VGD|`/`|VDS|`. The grounded-body core and 1.8-V fixtures reach 1.979 V
commanded `|VGB|`; the DNW body-tracking fixture limits `|VGB|` to about
0.9905 V.

These numbers are observations, not reliability sign-off. A foundry-approved
terminal-voltage rule set and a transient driver waveform are required before
any core-device bootstrap can be accepted. Spectre emitted model-limit warnings
at the upper commanded terminal differences; the run had zero numerical or
netlisting errors, but those warnings are an explicit blocker to declaring the
core/DNW option reliable.

## Next transistor-level target

Build the actual bootstrap driver around the DNW L60/W2 electrical seed and
retain the 1.8-V option as a comparison. The schematic must include the
bootstrap capacitor, precharge and transfer devices, gate discharge/clamp,
non-overlap clock phases, explicit body/well connections, and representative
input/CDAC loading. Transient PVT validation must then measure acquisition
error, gate droop, peak terminal voltages, charge injection, feedthrough,
off-state leakage, and failure recovery before the production sampling-switch
cell is frozen.
