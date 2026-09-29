# T28 bottom-plate top-clamp width screen

## Decision

Narrowing the four NMOS top/split-node clamps improves the **nominal raw**
held differential error in the full 5+5 differential CDAC, but this is not
yet a usable transistor solution. The W=185-nm point has only 5.22-uV
margin to the 0.439-mV target at the extreme input. Every simulated case
retains T28 core-device SOA warnings; the extreme-input warnings include
the clamps and the unchanged bootstrap cells. The experimental fixture still
has 22 complete
bottom-path bootstrap pumps, versus two in the top-path comparison.

## Fixture and provenance

- `SAR_ADC_T28`, bound to `tsmcN28`; T28 `nch_mac` L=30 nm top/split clamps,
  with four devices per experimental CDAC. W500 uses Wfg=250 nm and simM=2;
  W250, W200, W185, and W100 use a single same-named Wfg and simM=1.
- Each width has separate CDAC schematic/symbol and testbench schematic OA
  cellviews. Readback shows 93 CDAC and 21 testbench instances and zero check
  markers per variant. The existing `sar_bootstrap` and prior fixtures were
  not edited. Spectre decks derive from the exact OA-exported netlist; only
  existing testbench design variables, save statements, and analysis controls
  are filled locally. The raw exports, hashes, Spectre decks/results, warnings,
  and metrics remain under ignored
  `output/bootstrap_bottom_plate_clamp_width_screen/w{width}/`.
- Spectre 21.1 transient, T28 OA-exported embedded-usage model include
  with `ttmacro_mos_moscap`, TT passive sections, `pre_simu`, and
  `noise_worst`; 0.9-V supply, 27 C, VCM=0.45 V, two 50-ohm input sources,
  static Vdiff around the sample edge, 0.5-ns clamp-before-bootstrap release,
  and held differential error measured at 270 ns. Saved waveforms include
  input, bottom switch, top/split CDAC, and clock/reference-phase nodes.
  The reference handoff is unchanged. This is a static-input nominal transient screen, not PVT,
  mismatch, moving-input aperture, or physical-code-linearity validation.

## One-factor width result

| Clamp total W | Tested Vdiff | Maximum absolute raw held error | Relative to 0.439 mV |
| --- | --- | ---: | --- |
| Ideal zero-parasitic clamp, prior | five points | 0.00790 mV | passes only as ideal limit |
| T28 W1000, prior | five points | 2.0960 mV | fails |
| T28 W500 | −0.8, 0, +0.8 V | 1.0533 mV | fails |
| T28 W250 | −0.8, 0, +0.8 V | 0.53152 mV | fails |
| T28 W200 | −0.8, 0, +0.8 V | 0.44865 mV | fails by 0.00965 mV |
| T28 W185 | −0.8, −0.4, 0, +0.4, +0.8 V | 0.43378 mV | nominal pass by 0.00522 mV |
| T28 W100 | −0.8, 0, +0.8 V | 2.5385 mV | fails; reset becomes weak |

The W500-to-W185 trend is consistent with reducing clamp off-parasitic
loading, but it does not uniquely identify the error source. W100 reverses
the trend: immediately before clamp release at −0.8 V, the top differential
was about −2.375 mV and the split-node differential about −3.35 mV, versus
about −0.0007/−0.0015 mV for W250. Its B9 acquisition error is also 40.2 uV,
versus approximately 6.6–7.1 uV for W185–W500. Thus a clamp can become too
weak to reset the full network even as its off parasitics fall. Fitted gain
and post-fit residual are diagnostics only; the guardrail applies to the
uncalibrated raw held error.

For the five W185 inputs, maximum B9 acquisition error was 7.127 uV;
maximum bottom-path common-mode shift was 0.13778 mV; maximum differential
clamp-release step was 2.741 uV; and maximum later hold drift was 9.090 uV.
The fitted bottom-path gain-error slope was −0.05337% and the maximum
post-fit residual 13.67 uV. Neither calibration nor common-mode rejection
was credited against the 0.439-mV raw gate. Exact OA-exported `input.scs`
SHA-256 values are W100 `1634e5f4f630b56e423183f704fc8fd6655cf324e4d045a376746f2dd75743fc`,
W185 `4347bab10682b2d5372f1f3b196fbf1556a86587a053e67b2ee5982c13afb89d`,
W200 `140dd6a2a595bcf4bf76b584b63ac24f3553bd2d17858592d75fcf9ad03d58e8`,
W250 `3b23c6eae60f04398b2ea86ce1d25432294fd3afe3724a8666e788fbd7d7508b`,
and W500 `06c4d0dafcd1817676fedf8a7b2de7cdce1416c427322adc3fe40dcb61518a8b`.

The W185 −0.8-V run already reports clamp `Vgd` at least −1.04032 V against
the T28 model's 0.990-V terminal limit, plus bootstrap `Vgb`, `Vbs`, `Vbd`,
`Vds`, and `Vgs` violations and over two million suppressed warnings. The
CDF's Wfg default is 100 nm but does not expose a minimum value; neither
100 nm nor 185 nm is established here as foundry-approved for this use.

## Next bounded target

Do not integrate this CDAC fixture into the ADC or claim its nominal pass
as sign-off. First separate the clamp's reset resistance from its off-state
capacitance/injection in an isolated test, while redesigning the bootstrap
drive for verified terminal-voltage SOA. A shared boosted-gate generator
with separately timed bottom switches is worth a *separate* architecture
study because the current 22 pumps carry 6.6 pF of nominal internal pump
capacitor inventory, but that inventory is not measured clock capacitance.
Only after a reliable switch/clamp topology has raw error margin should it
advance to PVT, mismatch, physical 1024-code transfer, noise, and clock-load
validation. The ideal analytical binary-weight oracle is not a transistor
DNL/INL result.
