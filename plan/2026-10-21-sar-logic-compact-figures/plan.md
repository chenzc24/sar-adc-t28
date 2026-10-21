# Compare native SAR transfer timing in one compact period

User requests two smaller, focused old/new timing figures, each one period,
same plotting conventions, only actual necessary circuit signals. Target is
the SAR Logic section's two timing embeds in Report/Wrap-up & Experience.md.
Starting HEADb00c0f4, exp/cdac-flat8-device. User edits remain in the report's
other sections; all other dirty note moves and cdac10_dualrail work read-only.
Own only the two embeds and their brief measurement caption, a new offline
scripts/reporting/sar_logic_compare.py, Obsidian_docs/assets/sar_logic_compare/
PNG/SVG/provenance, this plan and one append to plan/log.md. Remote OA: none.

Read old/new controller wiring and accepted raw waveform/summary readers.
Read-only inputs: output/sar8_async_impl/{waves,results,decks}/
two_cycles_keynodes_aps_01 and output/sar8_simple/{waves,results,contexts}/
two_cycles_simple_v2_aps; source reports/verification summaries. Both TT/.9V/
27C native controller with ideal analog plant, first input+.123V and code145.
No new simulation, no topology/timing/model changes, no image editing or GUI.
Use matplotlib to generate scientific plots directly from saved raw samples.

Plot one SAMPLE-rise-to-rise100ns period, common time origin, x-scale, voltage
normalization, fonts and bus notation. Common actual lanes: SAMPLE,CMP_CLK,
CAPTURE/PHI_W,ADVANCE/PHI_U,WORK/D[7:0]. Old additionally shows its existing
COMMIT and DOUT bank; no fabricated equivalent in new. Exclude observational
token/trial words, ideal analog voltages, status/deadline/fault monitors and
irrelevant internal guards. Raw voltage shape retained; bus decodes physical
pin voltages atVDD/2, not ideal ADC arithmetic. Label transient codes only
where legible; no final-code inference before the actual data settles.

Validate source/result hashes, finite monotonic waves, native pin mapping,
eight compare/write/update edges per frame, actual output145 and publication
order. Existing results have different solver maxsteps; disclose in provenance,
do not promote speed/PVT/SOA qualification. Check output dimensions/text
extents, inspect PNGs, preserve report outside owned changes, verify embeds,
SVG/XML and diff-check. Scope stage report edits only, preserve unrelated user
edits. Commit docs: redraw compact one-period SAR timing comparison. No push.

## Outcome

Generated old seven-lane/new five-lane figures,1680x772/1680x600 pixels, each
100ns, report display width640. Working/output words decode the actual MOS
register pins. Excluded optional observers and nonexistent new publication
bank. Existing image files preserved. Scope caption identifies TT/.9V/27C,
same sampled input+.123V and actual time origin; originals use200/50ps maxstep,
recorded in provenance, not claimed as a new numerical timing comparison.

Both cases pass eight compare/write/update counts, captured-word sequence and
final145; old COMMIT follows last update. Runner deck hashes use LF and match
after normalizing local CRLF; raw local hashes are separately retained. Input
is constant during acquisition, not necessarily at the far end of the frame
where the next input PWL begins. These initial provenance assertions were
corrected without modifying sources. Full sample/finite/text bounds, py_compile,
SVG/XML, image hashes/dimensions and report UTF-8/YAML/embed checks pass. Both
final images visually inspected. Unowned note text matches starting version.
Scoped staged review/commit only; no simulation/OA/GUI or push.
