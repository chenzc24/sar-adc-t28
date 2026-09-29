# T28 StrongARM input-pair scaling screen

## Change and provenance

This is one controlled transistor-sizing iteration, **not a replacement of
the baseline** `sar_strongarm_t28`. Two independent OA comparators and
standalone benches were created: `sar_strongarm_t28_f2` / `tb_sar_strongarm_t28_f2`
and `sar_strongarm_t28_f4` / `tb_sar_strongarm_t28_f4`. Both have the same
11 T28 MOS masters, terminals, `Wfg`, `L`, tail, latch and reset devices as
the first-pass comparator. Only the `MNINP/MNINN` finger count changed from
1 to 2 or 4 at `Wfg=1 µm`, `L=30 nm`. Thus each input device nets as
`w=2u,nf=2` or `w=4u,nf=4`; the baseline is `w=1u,nf=1`. OA readback found
11 comparator devices, eight bench instances and zero schematic markers
for each candidate. The source comparator and its full-CDAC integration
bench were not edited.

Bridge 0.8.0 `t28_io` exported the exact candidate OA netlists. SHA-256
for f2/f4 exports is respectively
`824205205b8fa6b3836e54451aabc762a67471a3d15c16fa55e03e8f882dbd3a`
and `131ce52cb4f9a08d9e4a9c7dfe59d21d37f1ff26439b458957e2f5746e2ed1de`.
Comparison against the first-pass export verified that all nine other MOS
instance statements are byte-identical, and only the two pair devices'
finger-related geometry changes. Derived Spectre decks supplied bench
variables and analysis statements, with no DUT netlist edits. Raw decks,
logs, PSF, model-sampling files, and metrics remain ignored under
`output/strongarm_input_pair_scaling/{f2,f4}/`.

## Screen and results

All simulations used Spectre 21.1 and the T28 PDK. Nominal function and
transient noise used TT, 0.9 V, 27 °C, 0.45-V input common mode, 5-fF load
per output, a 20-ps clock edge, and ±0.439453125-mV differential input.
The clock period was 5 ns and a valid decision crossed signed 0.45-V output
differential by 1.5 ns. Transient noise used the same 1-kHz–10-GHz band and
seed 271828 as the earlier baseline, but only 48 cycles per input. Baseline
noise below is the **first 48 decisions** of its previously saved 96-cycle
runs, not a newly rerun test. Local-MC used the correct foundry
`TTGlobalCorner_LocalMC_MOS_MOSCAP` section, seed 314163, 16 draws per
input and matched positive/negative parameter samples within each candidate.
The baseline local-MC comparison is its first 16 of 32 saved draws; the
different run lengths mean cross-design random draws are not proven
identical even with the same seed.

| Input-pair fingers | Nominal decision delay, both signs | Noise wrong, ± inputs (96 total) | Paired local-MC draws inside ±0.439-mV bracket |
| ---: | ---: | ---: | ---: |
| 1, original | 223.35 ps | 23/96 (first 48 per sign) | 3/16 (first 16 of 32) |
| 2, f2 | 161.53 ps | 24/96 (14 positive, 10 negative) | 1/16 |
| 4, f4 | 133.73 ps | 17/96 (10 positive, 7 negative) | 0/16 |

All candidate runs completed with zero Spectre errors, resolved all
deterministic ± inputs, and had no unresolved noise or mismatch decisions
at the sampled time. Both candidate local-MC runs reported 66 random
variables and 19 defined mismatch parameters. Positive and negative runs
within each candidate shared the same sampled-parameter SHA-256, and
the early output-difference span was 0.73–1.23 V, confirming active
statistical variation rather than the previously discovered inert MC
section. Nominal TT logs showed four PDK `SFE-1131` scoped-`scalefactor`
warnings but no `CMI-275x` terminal-voltage warnings in the checked
candidate standalone cases. This does not clear the separate CDAC
bootstrap SOA issue.

## Interpretation and decision

Larger input-pair area accelerated nominal regeneration here. f4 showed
fewer wrong noise decisions than the same-length baseline subset, but 17/96
is still 17.7% at ±0.439 mV; under the *unverified* zero-offset Gaussian
binary-decision interpretation it corresponds to roughly 0.474-mV
effective input noise, above the provisional 0.316-mV RMS allocation.
The target would imply about 8.2% wrong at this input under that same
assumption. Sampling uncertainty and correlated cycles prevent claiming a
statistically established noise improvement from this small screen.

Crucially, neither enlarged-input-pair candidate closed the provisional
untrimmed offset bracket. The 16-draw local-MC result is far too small for
yield or tail claims, but it does **not** support promoting f2 or f4 to the
design baseline. A change in latch/reset-device mismatch contribution,
time-varying regeneration, or another dynamic mechanism may dominate; this
screen does not isolate the cause. Increasing input fingers also raises
input capacitance and may change kickback when connected to the full CDAC;
that integrated effect was **not measured** for f2/f4. No PVT, power,
common-mode, full-CDAC, full-SAR, layout, DRC/LVS or PEX acceptance follows.

Retain `sar_strongarm_t28` as the comparison baseline. The next bounded
iteration should identify the dominant offset contributors (for example,
controlled input-pair versus latch/reset mismatch contribution and a
continuous input-referred offset search), then adjust the responsible
devices/topology and recheck noise, offset, timing and CDAC kickback. Do
not add a preamplifier solely on the evidence of this one sizing sweep.

## Reproduction

The creator refuses to overwrite existing OA cells. With Bridge `t28_io`
available, export or rerun an existing candidate from the repository root:

```powershell
$env:VB_DISABLE_CONTROL_MASTER='1'
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_input_pair_scaling.py --candidate f4 --stage export
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_input_pair_scaling.py --candidate f4 --stage pvt
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_input_pair_scaling.py --candidate f4 --stage noise
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_strongarm_input_pair_scaling.py --candidate f4 --stage mismatch
```

Use `--candidate f2` for the other variant. The first export attempt met an
SSH ControlMaster download error; disabling connection reuse then exported
successfully. Its first strict netlist check correctly exposed the PDK's
`Wfg × fingers` to total-`w` translation; the checker was corrected to
require the actual `w=2u/nf=2` or `w=4u/nf=4` statements before any result
was accepted.
