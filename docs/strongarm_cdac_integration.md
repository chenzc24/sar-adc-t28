# Full split-CDAC to StrongARM interface diagnostic

## Scope and source of truth

The new, independent `SAR_ADC_T28/tb_sar_cdac_strongarm_diag/schematic`
connects `sar_strongarm_t28` input gates directly to the comparator-side
`TOPP_BP`/`TOPN_BP` nodes of the existing
`sar_cdac_bottom_plate_clamp_w185_eval_10b`. The latter is the full 5+5
split CDAC, not the earlier single 219.535-fF hold capacitor. Its original
bottom-plate sampling, W185 top/split clamps, reference network and 22
bootstrap paths are retained. The testbench adds only the StrongARM, its
clock source and 5-fF loads on each comparator output. Neither source DUT
was edited. OA readback found 25 testbench instances and zero schematic
markers; the exported netlist explicitly contains
`XCMP (COMP_CLK CMP_OUTN CMP_OUTP VDD TOPN_BP TOPP_BP 0)`.

The exact OA export SHA-256 is
`046ff86701d1a8e7bc6973be5c8885d64d844fbc67cc7ea150cee78ffa02fe28`.
The included CDAC and comparator subcircuits match their earlier validated
exports, with respective SHA-256 values
`d1813f56b8bbe568e71a91d9a8c448314c7aa0c4a7c444141fdc85b758e8e4b8`
and `e7effa6aeeac3dd126bf9d3e062009f83138a63f01cc7779cf25a9070c2b6e82`.
Only the OA-exported design variables and Spectre analysis/save statements
were supplied in the derived decks; device networks and subcircuits were not
rewritten. The ignored `output/strongarm_cdac_integration/` folder retains
readback, netlist, decks, logs, PSF and `summary_all.json`.

## Timing and metric

All six noise-free Spectre 21.1 transient runs used T28
`ttmacro_mos_moscap`, 0.9-V supply, 27 °C, approximately 0.45-V input
common mode, and 5-ps maximum step. Sampling begins at 211 ns; the clamp
opens at 249.5 ns, bottom bootstrap at 250 ns, base/reference connection at
252 ns, and comparator clock rises at 255 ns with a 20-ps edge. The
comparator-disabled control holds that clock at 0 V while leaving the same
CDAC and input. Source differential settings were ±0.439453125 mV and
zero. The output decision is the first signed 0.45-V output differential
crossing within 1.5 ns of the comparator clock's 0.45-V crossing. The
clock-induced input disturbance is the on-minus-off `TOPP_BP−TOPN_BP`
differential, with its preclock baseline removed. It measures a dynamic
interface effect, **not** a direct ADC conversion-error or input-offset
value.

| Applied source `VINP−VINN` | Preclock CDAC `TOPP−TOPN` | Clock-induced peak | At output decision | Decision delay | Result |
| ---: | ---: | ---: | ---: | ---: | --- |
| +0.439453 mV | −0.438531 mV | −0.374181 mV | −0.365124 mV | 224.116 ps | correct polarity |
| −0.439453 mV | +0.438531 mV | +0.374181 mV | +0.365124 mV | 224.116 ps | correct polarity |
| 0 | approximately 0 | +0.375136 mV | not scored | not scored | numerical symmetry-breaking; no correct polarity exists |

The nonzero-source peak occurs around 255.232 ns, close to the output
decision at 255.234 ns. At 256.5 ns, the differential on-minus-off residual
has decayed to ±0.000595 mV (about 0.595 µV). Thus the CDAC recovers later,
but its disturbance is **still large at the instant of decision**. The
disturbance follows the selected latch polarity. The zero-input control
develops a comparable differential transient despite essentially zero
preclock differential, so the observation is principally decision-dependent
latch feedback, not evidence of a pre-existing 0.375-mV static error. A
deterministic zero-input latch state selected by numerical asymmetry is not
an offset, yield, or accuracy measurement.

The 0.374-mV full-CDAC peak is about 2.21 times the earlier 0.169-mV
single-capacitor fixture result. It happens to lie 0.065 mV below the
provisional 0.439-mV peak-disturbance guardrail, but that narrow comparison
does not approve the comparator: the earlier fixture had a different
impedance/timing, and post-initiation latch feedback need not be equivalent
to a pre-decision input error. The W185 CDAC's own separate full-scale raw
held-error screen was 0.43378 mV against its 0.439-mV target; this
near-limit result is not requalified by the present small-input test.

## Acceptance boundary and next design work

All six Spectre runs completed with zero errors. Each reports model
terminal-stress warnings (`CMI-2751/2752/2753/2755/2756`) in existing
bootstrap/top-bootstrap paths; the positive enabled run had 29 total
warnings, including four PDK scoped-`scalefactor` warnings. These SOA
warnings are a **physical-design blocker**, even though nominal transient
function resolves. The existing StrongARM standalone transient-noise and
local-mismatch screens also fail their allocated 0.316-mV RMS noise and
0.439-mV offset targets; this deterministic interface screen does not
supersede those results. No transient noise, Monte Carlo, PVT, bit-to-bit
reference switching, full SAR conversion, layout, DRC/LVS or PEX was tested
here.

The next useful bounded work is to replace the overstressed bootstrap paths
in a separate, protected CDAC variant, then repeat this exact interface
bench and add a near-zero overdrive/noise/mismatch sweep with the full CDAC.
In parallel, resize or revise the StrongARM input/regeneration devices to
close noise and offset without losing the 1.5-ns decision window. A
pre-amplifier remains an architectural option only if that trade-off cannot
close with the direct-input comparator; this result alone does not justify
adding it.

## Reproduction

With Bridge `t28_io` and the remote Virtuoso/Spectre session available,
from the repository root:

```powershell
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_cdac_integration.py --stage export
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_cdac_integration.py --stage analyze-existing
```

`--stage run` executes the six simulations anew. The creator script refuses
to overwrite the existing OA diagnostic cell; it is for initial creation
only. The analyzer verifies the saved decks against the exact export and
requires Spectre zero-error completion before reusing PSF data.
