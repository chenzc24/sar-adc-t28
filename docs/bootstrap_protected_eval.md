# Mixed-voltage bootstrap screening experiments

## Decision

Two independent transistor-level OA experiments were built. The second
candidate clears the **nominal Spectre model-warning screen** at TT/0.9 V/27 C,
but neither candidate meets the raw differential held-error allocation of
0.439 mV. Neither is a reliability-qualified nor a production sampling switch.
The existing `SAR_ADC_T28/sar_bootstrap` was not modified.

## OA and source-of-truth

| Candidate | DUT / testbench in `SAR_ADC_T28` | Difference from baseline |
| --- | --- | --- |
| Initial | `sar_bootstrap_protected_eval` / `tb_sar_bootstrap_protected_eval` | MN1/2/3, MN7/13 use `nch_18_mac`; MN11 uses `nch_18_dnw_mac` |
| Full control | `sar_bootstrap_protected_full18_eval` / `tb_sar_bootstrap_protected_full18_eval` | Also moves MN5 to `nch_18_mac` and MP4 to `pch_18_mac` |

Each DUT schematic and its differential testbench read back with zero check
markers. Both symbols preserve the baseline six-port interface. The automatic,
unedited OA Spectre exports were hashed as follows:

- Initial: `a14670cb13ffd5178d309b5966ad4850cf0c8ec15d6b2e248dfb58a893f3e820`
- Full control: `f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d`

The exports confirm the PDK classes and all 12 D/G/S/B mappings per DUT.
`nch_18_dnw_mac` is the selected MN11 OA master, but netlists as the
`nch_18_mac` electrical model with its B terminal tied to VIN. That mapping
does not establish the layout's well/substrate reliability. The 1.8-V devices
used L=150 nm and Wfg=320 nm; MN11 used 28 parallel fingers (8.96 um total),
while the other replaced devices used four (1.28 um total). Pump and bootstrap
capacitors remained ideal 50/50/200 fF. No hand-written replacement DUT
netlist was simulated: the runner only changes `saveOptions` and appends
transient/save statements to each exact OA export.

## Nominal electrical screen

Spectre 21.1 used the OA-selected T28 model includes with the
`ttmacro_mos_moscap` section, VDD=0.9 V, 27 C, ideal complementary clocks,
50-ohm differential input sources, and 219.5-fF loads on each output. The
input steps while the switch is off to VINP/VINN=0.85/0.05 V; PHI then
acquires from about 211 to 250 ns. Transient maximum step was 5 ps; the
acquisition check was at 249.8 ns and raw hold check at 270 ns. Spectre
completed both cases with zero errors.

| Candidate | Acquisition error | Raw held error | Retained `CMI-275x` | Driven-cycle terminal screen |
| --- | ---: | ---: | ---: | --- |
| Initial | -0.000559 mV | -8.972 mV | 20, plus suppressed repetitions | Fails: MP4 up to 1.075 V; MN5 up to 1.025 V |
| Full control | -0.000374 mV | -8.755 mV | 0 | Passes diagnostic warning levels |

The full-control case's largest reconstructed core-device terminal difference
was 0.911 V (MN12 `Vgd`); its largest 1.8-V-device difference was 1.756 V
(pump MN1/MN2 `Vgb`/`Vbs`). All six D/G/S/B terminal differences on both
sides were reconstructed: 144 metrics per case. The diagnostic comparisons
were 0.99 V for core models and 1.98 V for nominal 1.8-V models, consistent
with the model guide's default warning-ratio explanation. **These are not
foundry-approved transient-voltage/duration or lifetime limits.** DNW
substrate and extracted-layout stress remain outside this four-terminal
waveform audit.

The initial prototype's Spectre log retained 20 `CMI-275x` examples and
reported 698 further warnings suppressed. The full-control case had no
`CMI-275x` lines; its four remaining non-SOA Spectre warnings concern model
scope-option redefinitions. Zero model warnings are a screen result, not
proof of a reliable device.

Against the earlier matched-condition baseline's approximately 12.026-mV
raw differential error, the full-control prototype reduces the magnitude by
about 27%, yet remains roughly 20 times the 0.439-mV budget. The earlier
gate-ablation evidence implicates the turn-off/driver path, but this screen
does not uniquely identify which new device or parasitic causes the remaining
8.755 mV. A true next topology should separate the boosted-gate path from
the hold node before discharge, then evaluate controlled turn-off timing and
bottom-plate charge transfer. Merely substituting more 1.8-V devices is not
an acceptance route.

## Limits and artifacts

Only one static-input, one-corner differential case was run per candidate.
No moving-input aperture, PVT, mismatch, noise, extracted parasitics,
layout, DRC/LVS, foundry transient-duration rule, or lifetime signoff was
tested. Do not promote either cell into `sar_sample_switch` or the full CDAC.

Readback, automatic OA exports, generated decks, raw PSF, Spectre logs, and
ranked JSON summaries are under ignored `output/bootstrap_protected_eval/`
and `output/bootstrap_protected_eval/full18/`. The local source is the
candidate creator, exact-export runner, and their two YAML configurations.
