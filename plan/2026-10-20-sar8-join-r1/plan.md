# SAR8 R1: frozen native analog/control integration

## Goal and boundary

User authorizes freezing the agreed eight-bit circuit, creating the top-level
schematic and running joined Spectre simulation. R0 remains an immutable
selection record. R1 implements that selection, not a new circuit architecture:
Canvas Bootstrap, nominal T28 MOM flat CDAC, two-pass-MOS 3x reference banks
with ideal gate voltages, unchanged StrongARM and unchanged simple native
asynchronous controller. External SAMPLE is ideal; CMP_CLK/write/update remain
native. No PVT, mismatch, noise, resizing or reference-buffer design this round.

## Initial state and ownership

Branch exp/cdac-flat8-device; initial HEAD 20a4245. Untracked cdac10_dualrail
config, three models, scripts, verification and plan belong to other work and
are excluded. Existing user-open old eight-/ten-bit benches and controller
windows are read-only. No delegation. Bridge 0.8.0/t28_io CIW and Spectre were
healthy at preflight, remote llm_IO, library SAR_ADC_T28/tsmcN28.

Owned local: this plan; scripts/integration/join_r1*.py;
models/veriloga/sar8j_r1_refgate.va; config/sar8_join_r1.yaml;
verification/integration/test_join_r1.py and join_r1_results.json;
docs/sar8_join_r1.md and docs/figures/sar8_join_r1/; bounded status/log links.
Also owned: one .gitattributes line pinning the new reference-gate VA to LF,
so its tested byte hash survives Windows checkout. Other attributes untouched.
Generated output: output/sar8_join_r1/ only. R0 and all source decks are read-only.

Owned new remote objects, all in SAR_ADC_T28:
sar8j_r1_sw_b0..b7 (schematic/symbol), sar8j_r1_cdac (schematic/symbol),
sar8j_r1_refgate (symbol/veriloga), sar_adc8_join_r1 (schematic/symbol),
tb_sar_adc8_join_r1 (schematic). No existing module or PDK mutation.
If an owned name already exists without an ownership receipt, stop.

## Implementation

1. Verify the R0 source lock and live geometry/connectivity of the 23 selected
   native dependencies. Capture fresh library/windows/readbacks without editing.
2. Implement reference timing directly at the ideal gate boundary: cross-map
   the existing native requests; hold old reference choices at SAMPLE rise;
   restore midpoint after 2 ns with >=100 ps actual command BBM; hold midpoint
   through SAMPLE fall/init gap; follow valid native requests during conversion.
   Cancel old pending events on the next SAMPLE. Never inspect Vin for decisions.
3. Build new 3x pass-MOS leaves and nominal MOM array, then top and bench using
   supported schematic APIs. Keep Bootstrap, StrongARM and 21 native logic cells
   unchanged. Ideal gate sources affect only reference gates. No ideal DAC plant.
4. Read back all new schematics, check markers, export the saved bench with the
   supported netlister. Archive original export. Only add simulation parameters,
   model includes, save/analysis statements and scenario input sources; do not
   patch the DUT hierarchy. Verify frozen body/geometry signatures against R0.
5. Run nominal APS smoke, then two-frame/cross-input and carry/reset cases;
   fine-step recheck the worst observed point. Keep failed attempts and warnings.
6. Analyze native compare/write timing, eight decisions, stable output window,
   charge-equation residual, sampled error, BBM and port stress. Make timing
   plots with expected references and clearly marked sample/hold/read windows.

## Validation and acceptance

- R0 hashes unchanged; selected old cells unchanged before/after.
- Every new schematic has exact expected masters, pins, parameters and nets;
  no unresolved check markers; exported hierarchy corresponds to the schematic.
- Spectre result.ok required, unique result/export directories, TT/0.9 V/27 C.
- Per complete frame: eight resolved decisions/writes, stable code at 95--99 ns,
  code agrees with nominal quantization except explicitly identified boundary
  points; compare-before residual target <1.7578125 mV.
- Record actual reference deadtime, legal mutually exclusive gates and maximum
  terminal voltages, including existing 0.99-V core model-check boundary.
- A failed joined check is a result, not permission to resize or replace native
  modules. Diagnose and preserve evidence; do not claim qualification from older
  ideal-comparator/ideal-DAC tests. Any material repair needs explicit revision.

## Artifacts and commit policy

Local exact exports/readbacks/runs in output/sar8_join_r1; small curated metrics,
source fingerprints, report and plots tracked. No PDK includes/model bodies,
raw OA, credentials or license data committed. Scoped local commit after checks;
no push without user request. Final report distinguishes built/simulated/passed.

## Progress

- Preflight: status healthy; source windows left open and untouched.
- Implementation and simulation pending.
- Created all 12 new cells (8 leaves, array, gate VA, DUT, bench). Final
  schematic markers empty, exact connections/parameters read back. Export audit
  matches all 23 frozen native bodies and all pass-MOS CDF geometry.
- Initial import API differences and IC618 generated-function literal-stack
  limit were repaired only in the new build automation. Partial owned cells
  were retried; existing cells were not rebuilt. Errors/logs remain ignored.
- Control input +453.515625 mV: both frames code192, eight decisions, max
  compare error0.701372 mV, reference peak0.957538 V, nominal checks pass.
- +/-800mV: both frames correct codes14/241 and errors below0.807mV, but
  native SOA fails. Negative case reference peak about1.2421V during bit update;
  both polarities also expose StrongARM input stress. No limit suppression or
  circuit repair. Remaining bounded cases and a fine-step diagnosis pending.
- Later batch cases save10ps output strobes (same solver tolerances); original
  control is full-rate. Fine diagnosis remains full-rate with10ps maxstep and
  adds comparator X/Y/TAIL voltage observations, not circuitry.

## Outcome

- All11 APS runs completed result.ok;22 functional frames/176 native decisions
  and writes pass. Nine primary cases cover six static inputs and three
  cross-frame transitions. Fine negative-full/negative-half cases also retain
  correct codes. Latest write70.345641ns, fixed read95--99ns stable; maximum
  compare-before error0.806368mV versus1.7578125mV limit.
- NOT SOA qualified: only control passes combined checks. Fine reference
  VDB1.266776V at144.752751ns/N7.MN_LOW; comparator MNINN VGB1.250013V
  at144.753290ns. Negative-half reference1.266744V confirms the issue near
  midscale. These are TT/.9V/27C failures, not deferred PVT/MC. Model warnings
  remain enabled; repeated suppressed warning notices retained; no LTE warning.
- No simultaneous raw/gate enables at0.5VDD, minimum gate interval about100ps.
  This is NOT proof of zero physical reverse/body-diode current. Waveforms locate
  peaks at new-path turn-on near BBM end; coupling/skew/reference contributions
  need a new controlled experiment.
- Final new-cell schematic/VA readback agrees;11 schematics have zero final
  markers.23 old native dependencies unchanged before/after. Exact exported DUT
  hierarchy preserved in run wrappers. Two global supply/ground port warnings
  and inherited environment/PDK notices documented, not hidden.
- Curated verification/integration/join_r1_results.json holds source/VA/OA/deck
  fingerprints and comparisons; docs/sar8_join_r1.md and15 PNGs give results
  with expected references/read/hold windows. Raw exports/logs/PSF ignored.
- Seven focused tests pass; compilation/diff/link/source checks repeated at
  handoff. Scoped local commit; no push. No resizing, topology change, PDK
  edits, old OA replacement or unrelated cdac10 work included.
