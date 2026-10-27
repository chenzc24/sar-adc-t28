# Maintenance Log

## 2026-10-20 - Freeze and join SAR8 R1 native analog and async logic

- User confirmed current clocks/Canvas Bootstrap/eight-bit line and authorized
  freeze, top-level construction and joint simulation. Preserved R0 selection
  and all old native modules. Built12 new SAR_ADC_T28 cells:8 two-pass-MOS3x
  reference leaves, grouped native MOM array, ideal reference-gate VA, DUT
  sar_adc8_join_r1 and tb_sar_adc8_join_r1. External SAMPLE ideal; compare/write/
  update native; no ideal DAC/sign comparator. No EOC/new native control state.
- Final11 schematic readbacks and VA hash match; zero final schematic markers;
 23 native dependencies unchanged before/after. Exported native bodies and
  pass-MOS CDF geometry match frozen sources. Run wrappers preserve DUT bodies.
  IC618 import-argument and literal-stack build issues repaired only in owned
  automation/partial new cells; ignored diagnostic logs retain failed attempts.
- 11 result.ok APS TT/.9V/27C runs:9 two-frame static/carry/full-reversal cases
  plus2 maxstep10ps/full-rate repeats.22 functional frames,176 resolved native
  compare/write events, correct stable read-window words, midpoint/mapping and
  token order pass. Max pre-compare error .806368mV <1.7578125mV; final write
  <=70.345641ns/frame, fixed read95--99ns. Raw/gate enables nonoverlapping at
  half-supply, minimum opposite-rail gap~100ps; not proof of zero device current.
- SOA FAIL: only control meets combined gates. Worst reference N7.MN_LOW VDB
 1.266776V at144.752751ns; comparator MNINN VGB1.250013V at144.753290ns.
  Negative-half reference1.266744V confirms midscale exposure. Warnings and
  suppressed-repeat notices retained; no model-limit changes/LTE warning.
  Correct code is not qualification; PVT/MC/noise/FFT/full-code/power/layout deferred.
- Frozen config/report/193kB metric-and-source manifest plus15 PNGs tracked;
  generated exports/PDK paths/logs/PSF/VA readbacks ignored. One .gitattributes
  line preserves tested gate-VA LF bytes. Seven focused tests, Python compile,
  source hashes, link/figure inspection and diff checks pass. Local scoped
  commit, no push; unrelated untracked cdac10 work and user windows preserved.

## 2026-10-20 - Prepare one 3x ideal-gate SAR8 integration candidate

- User selected corrected P/N mapping, unified physical sampling/reference
  initialization, and 3x pass switches with ideal gate voltages. Prepared
  SAR8_JOIN_R0_3X_IDEAL_GATE contract/report/source lock, not a new circuit run.
- Live read-only t28_io capture matches prior connectivity, geometry and ports
  for 21 simple_v2 native control cells plus Bootstrap/StrongARM. No OA saves,
  exports, new cell/top, driver replacement or simulation; historical and
  unrelated untracked cdac10_dualrail work preserved.
- Locked 15 source files, native subckt digests and all 6 existing 3x result/deck
  references. 3x means P/N integer multiplicity 3*2^bit, not resizing Bootstrap
  or comparator. 3x two-MOS reference leaves remain netlist-only; old OA driver
  cells are not mislabelled as the chosen ideal-gate version.
- Contract crosses native P/N selection banks to physical reference requests,
  defines PMOS-gate inversion, and restores midpoint after 2 ns inside SAMPLE
  with BBM. Retains midpoint over sample-fall/init gap. Shared 100-ps SAMPLE and
  39.9-ns pulse width preserve 40 ns between midpoint crossings; native controller
  old 20-ps fixture results do not qualify the changed joined boundary.
- Four focused contract checks cover 256 code mappings/charge/code centers,
  gate disable/forbidden overlap, exact3x/native selection and sample/midpoint
  consistency. Python compile, YAML/JSON/source-hash/link/diff checks pass.
- Added config/sar8_join_r0.yaml, docs/sar8_join_r0.md, repeatable read-only
  capture/pin checker and small source manifest. Adapter/top explicitly still
  unimplemented; not a claimed integration or device qualification. Scoped
  local preparation commit; no push or experience extraction.

## 2026-10-20 - Implement the user-approved minimal asynchronous SAR timing

- New target SAR_ADC_T28/sar_logic_8b_async_simple:21 native schematic/symbol
  cells and two benches. One sampling control, local compare/write/update,
  bit chain, eight SAR slices and P/N driver banks. One clock SR,16 DFFs;
  recursively1476 MOS/257 explicit ideal caps/70 ideal resistors. No old
  handshake/status/deadline/EOC or output bank. Old/user-open cells preserved.
- Final v2 thirteen result.ok Spectre21.1.0.509.isr12 APS cases pass the bounded
  code/event/nonoverlap/data-before-reset/read-window assertions. Two normal
  frames145/85 with exactly8 comparisons/writes/updates; same at maxstep10ps.
  Representative0/255/85/170, variable delay, SS/FF, sample abort/restart,
  stuck frame/recovery and unchanged real StrongARM are separately scoped.
  All use ideal sampled DAC; only StrongARM fixture uses a native comparator.
- TT v1 PHI_W=-105.802mV and CMI warnings repaired with a stronger local output
  buffer (accepted CDF sizes N2um/P3um, not the rejected4um P finger). V2
  minimum=-41.105694mV, tight-step=-41.105690mV, nominal no CMI. Preserve v1
  evidence; sensitivity is not a unique coupling root-cause proof.
- SS representative last write74.078ns, StrongARM70.309ns. FF.99V functional
  code correct but30 printed CMI warnings plus13,031,246 suppressed: device
  safety is NOT passed. No model-limit changes. Fixed read timing, ideal RC
  mapping/tolerance/layout and full physical integration/noise/MC/power remain
  open; no native256-code sweep or ADC performance/qualification claim.
- Exact OA source/readback, immutable export/deck/wave hashes, shared-control
  and unchanged-StrongARM checks; actual-export functional abstraction passes
  256 words/eight stuck recovery positions. Abstract tests do not replace
  native margins. Remote plant source hash equals local after runs. Raw
  artifacts output/sar8_simple; curated metrics/cell list verification/sar8_simple;
  four timing figures and report docs/sar8_simple_async.md.
- Active control pointer/docs updated; targeted compile/model/YAML/JSON/link/
  diff and owned review checks pass. Four figures visually inspected; new
  top/timing/bit schematic windows opened for review. Local scoped commit;
  no push requested. Concurrent CDAC10/PN-ratio work excluded.

## 2026-10-20 - Two complete asynchronous sampling periods and key-node diagrams

- User requested two complete sampling periods and all key timing nodes after
  the undershoot discussion. Added one nominal APS observation run with the
  unchanged recovery hierarchy, ideal sampled ADC/comparator plant, 202-ns stop
  and 88 explicit voltage saves. Only VIN stimulus/save list/stop changed;
  no OA, PDK, circuit, control-contract or existing-evidence mutation.
- Actual SAMPLE edges 1.01/101.01/201.01 ns delimit two 100-ns periods. Input
  .123 V then -.3 V differential gives145 then85, eight decisions/captures/
  advances each. VALID87.349605/187.373284 ns; old DOUT retained in acquisition.
  Full saved traces finite, exact simulated/native subcircuit equality checked.
- Preserve failures: first reset-boundary CAPTURE -86.541 mV at101.125 ns,
  closing context after period2 -111.316 mV at201.126 ns; CMI starts201.114 ns,
  25 printed/15565 suppressed warnings. Correct words do not waive SOA;
  no root-cause isolation, circuit repair or qualification is inferred.
- Added18 inspected PNG diagrams, seven scalable SVGs and an indexed guide
  docs/sar8_async_two_cycles.md. Includes raw state/control groups, all bit
  banks/reference selections, single-bit detail, both boundary zooms and the
  old fault scenario explicitly labelled as a separate run. Measured voltages
  and threshold-decoded buses are distinguished; no invented internal waveform.
- Reproducible source scripts/sar8_async/two_cycles.py, small provenance JSON
  verification/sar8_async/two_cycle_summary.json, raw output/sar8_async_impl/.
  Checked peak-preserving display reduction,88-node coverage, labels/bounds,
  Python compile, JSON/SVG/links and scoped diff. Concurrent inventory/reset
  commits and all unrelated ten-bit sources/windows preserved. Local bounded
  documentation commit, no push.

## 2026-10-20 - Current progress and local Virtuoso design inventory

- User requested a consolidated progress/file map. Added docs/project_status.md,
  README entry, complete linked local/cell lists, CSV tables, generated-output
  roots and a timestamped snapshot under docs/inventory/2026-10-20.
- Read-only bridge status and exact library/technology verification succeeded;
  DD listing found 170 cells with 159 schematic, 114 symbol, 11 veriloga views,
  no layout/maestro. Manifest has 143 entries: 42 actual cells are unregistered,
  15 planned/local-model entries are not remote OA cells. Manifest unchanged.
- Eight schematic reads confirm two partial integration lines: native analog
  chain with VA sequencing, versus native async controller/StrongARM with an
  ideal sampled-DAC plant. Neither is relabelled as the final native async ADC.
- Separated active eight-bit sources, historical 5+5/bottom-plate/GMAIN work,
  reset/dual-rail candidates and ongoing ten-bit/two-cycle work. Preserved all
  concurrent sources and reports. No OA save/category change, file relocation,
  deletion, circuit rewrite, new simulation, connection repair or push.
- Added scripts/maintenance/project_inventory.py for repeatable read-only
  metadata capture, local source listing and bounded checks. Remote capture
  freshness is separate from local refresh; raw readbacks remain ignored under
  output/project_inventory/2026-10-20. No PDK/OA/model contents committed.
- Validation: complete/unique CSV rows, actual/manifest/view/count consistency,
  linked-file existence, Python compile and diff checks. Scoped local
  documentation/tooling commit; no experience extraction.

## 2026-10-20 - Executable asynchronous SAR and native modular gate prototype

- Added event-driven eight-bit reference, independent-noise/jitter sensitivity,
  five focused tests, actual-export functional interpreter, OA builders and
  Spectre harness under sar8_async. No external high-speed bit clock.
- New SAR_ADC_T28: 26 native schematic/symbol cells, three bench schematics,
  plant VA/symbol. Top sar_logic_8b_async has1742 native MOS plus explicit ideal
  R/C. Exact connections/parameters and29 schematic zero-marker checks pass;
  fresh saved exports match simulation, unchanged comparator and VA SHA verified.
- Distinguish PUBLISH request, qualified COMMIT and delayed VALID. Move native
  cutoff88->89ns based on measured delay, retain100ns frames/90ns PREPARE.
  Fix a native fault-recovery race by clearing old FAULT during acquisition.
  Preserve all failing versions and analog/historical/concurrent dependencies.
- Ideal2048 ramp: no missing codes, DNL/INL0; coherent4096/bin1843 gives48.7529dB
  SNDR/7.8061ENOB. Allocated noise plus20ps sampling jitter gives45.9121dB/7.3342.
  All256 patterns +16 fault positions pass the exported-netlist event abstraction,
  not transistor simulation. User chose no hours-scale full256 native sweep.
- Final17 integrated native runs plus4 unchanged-unit runs execute successfully
  with complete finite traces. TT APS5ps: code145, eight ordered events,
  VALID87.349ns, no select overlap, <=17.611ps APS/AX difference. Real unchanged
  StrongARM gives145/14/241; nominal VALID86.419ns. Fault retention/recovery,
  reset, duplicate start and timeout protections work; DFF reset controls pass.
- NOT QUALIFIED: SS0.81V125C deadline miss (AX/APS), multiframe CAPTURE -0.111V
  undershoot/CMI (APS confirmed), FF0.99V and large-negative StrongARM SOA.
  Correct codes do not waive device failures. Delay R/C still ideal; no physical
  CDAC integration, power/noise/MC/layout/PEX sign-off or full ADC qualification.
- Evidence output/sar8_async_impl; report docs/sar8_async_implementation.md,
  three inspected figures and verification/sar8_async/summary.json. Top/seq/DFF
  review windows remain open; unrelated GUI/windows and ten-bit dirty files
  preserved. Focused tests, Python compile, YAML/readback/export/diff checks;
  bounded local implementation commit, no push.

## 2026-10-20 - Asynchronous SAR architecture selected

- User replaced the fixed-bit synchronous proposal with asynchronous SAR.
  Added config/sar8_async_timing.yaml and docs/sar8_async_logic.md; selected
  asynchronous control in the active eight-bit spec. Existing clocked
  fixtures and unrelated untracked dual-rail work remain unchanged.
- Defined frame-independent deadline, comparator fresh-result/reset handshake,
  separate capture and token advance, stable output bank, fault/abort policy
  and nine module cell contracts. No new executable gate/VA/OA implementation.
- Callable MCP reconnected with a fresh private Claim. Added SAR8A_REVIEW,
  SAR8A_HANDSHAKE, SAR8A_CELLS and SAR8A_TIMING; changed project top to the
  async review, preserved prior eight documents and renamed old review entry.
  Four exported PNGs visually inspected; canonical project readback confirms
  document identities/top and unchanged drawing/electrical content in all
  eight old documents. SVGs tracked; full backup in output/sar8_async/.
- YAML and budget arithmetic pass: 86.9-ns reference completion, 88-ns planned
  cutoff; constructed example 79.77 ns, not measured waveforms. Existing
  active/history spec test passed. No gate, analog, PVT or OA validation claim.
- YAML/SVG syntax and diff checks passed. Remote OA unchanged; user continues
  to defer Virtuoso work. Scoped local commit; no push requested.

## 2026-10-20 - Canvas-first eight-bit SAR logic proposal

- User deferred the unavailable live CIW and requested Canvas topology first.
  Connected the exact Analog Canvas HTTPS origin through callable MCP 0.17.75;
  no credentials were stored. No OA mutations or baseline replacements.
- Added eight review/electrical Cells, eight hierarchical bit slices, working
  and output registers, one-hot sequence, reset-priority state, ready/fault
  handling, latched clock gates and reference non-overlap topology.
- Read the active eight-bit device phase contract; drew a 100-ns expected
  frame with final result publication at commanded 82.5 ns. Figures are
  explicitly expected, not measured T28 waveforms.
- Six fresh electrical MCP verifies: zero structural errors; port display
  stubs/visual clearance warnings remain. Actual exported ideal gate graph
  passes 256-word, eight-fault-position and reset/retention/clock Boolean
  checks (27 registers, 187 gates). No analog delay/PVT/BBM proof claimed.
- Tracked timing config, report, two SVGs, ideal netlist and Boolean checker.
  Ignored full Canvas/PNG exports remain in output/sar8_logic/. Native
  implementation is deferred; scoped local commit, no push requested.

## 2026-10-20 - Unchanged T28 StrongARM baseline for the eight-bit ADC

- Target: `plan/2026-10-20-strongarm8-baseline/plan.md`; preserved concurrent
  CDAC-reset and native-logic work. Added bounded comparator config, runners,
  analysis, testbench-only binary-search VA, tests, report and five figures.
- Fresh read-only OA exports/readbacks identify the same 11-MOS T28 comparator
  in standalone and current CDAC fixtures; no OA edits, rewiring or resizing.
  All 125 accepted job DUT/deck hashes match. Native Spectre 21.1 APS, not EVAS
  or the Canvas display/default SKY130 models, solved the transistor circuit.
- Completed 94 deterministic, 19 physical-noise, three mismatch, three held-C
  and six CDAC A/B tasks. Nominal delay 191 ps; PVT timing 46/54 pass, four
  failing PVT points. All 18 high-supply PVT runs retain CMI stress warnings.
- Local-MC 128 uncensored threshold brackets: 0.25-mV resolution, approximate
  sigma 12.730 mV, mean -1.945 mV, 16/128 fully within +/-1.758-mV comparison
  guard; not an approved yield criterion. Dense/binary/full first-four brackets
  and saved random-parameter records match. Full binary history not measured.
- Nominal noise CDF estimates 0.652 mV at 10 GHz and 0.745 mV at 30 GHz;
  both below allocation, bandwidth/PVT/joint-statistical qualification open.
  Current fixed-code native CDAC differential disturbance about 0.039 mV at
  decision and 0.120 mV peak, not complete SAR-code/FFT acceptance.
- Rejected early strobe setups and the interrupted dense 128-draw attempt
  remain raw evidence, excluded from accepted results. A CIW-help query hung;
  only exact owned helper processes were ended, never Virtuoso. User deferred
  display/reconnection repair; final live CIW readback deferred explicitly.
- Five focused tests, compile/YAML checks, complete/finite waveforms, 125-deck
  audit, tighter numerical controls and visual inspection passed. Report:
  `docs/strongarm8_baseline.md`; ignored evidence: `output/strongarm8_baseline/`.
  Circuit qualified=false. Scoped local commit; no push or experience entry.

## 2026-10-20 - CDAC reset timing and native gate drive, bounded experiment

- Target: `plan/2026-10-20-cdac-reset-timing-drive/plan.md`; clean 665594d on
  `exp/cdac-flat8-device`. User explicitly defers Bootstrap acquisition.
- Added isolated source/config/report/figures and 13 new OA schematics:
  eight reference-switch driver cells, nominal/literal arrays, three benches.
  Historical CDAC/Bootstrap/PDK and input clock were not modified.
- Completed 24 result.ok native APS runs: 18 diagnostic copies and six exact
  saved-OA exports. Original-point worst reset terminal 1.012168 V; 2x/4x
  pull-down 0.980651/0.982106 V. The 4x OA retains -0.201700-mV fixed128 hold
  error, 0.386133-mV loop comparison error; native StrongARM fixture 0.583577 mV.
- All checked final codes and final reset levels pass their respective gates,
  but cross-input positive/negative stress still fails. 4x -0.8-V reset worst
  1.055154 V. The unmodified negative-input baseline already has 1.072523-V
  conversion-phase Vbd. No broad PVT/FFT/MC/noise/layout or acceptance claim.
- Final remote audit: 14 old dependency readbacks identical, 13 schematics
  zero markers, three final native exports equal primary except timestamp;
  two remote VA hashes equal unchanged local sources. Nominal diagnostic/OA
  and aggregate/literal waveforms correlate; no Monte Carlo equivalence claim.
- Harness checks caught missing analysis NumPy in bridge venv (use project
  Python), PSF `units` metadata, a continued-master parser omission, a
  StrongARM-only CKB parameter absence and a synthetic-test typo. Fixed before
  accepting metrics; no simulator read-in/convergence failure counted as pass.
- Generated evidence remains ignored under `output/cdac8_reset/`; no PDK,
  raw OA or model contents staged. Five focused tests, Python compilation,
  YAML parse, plot inspection and diff checks passed before the scoped local
  commit. No merge/push. Experiment complete; circuit acceptance open.

## 2026-10-20 - First device-level eight-bit flat CDAC, acceptance open

- Target: `plan/2026-10-19-eight-bit-device-cdac/plan.md`; clean base
  4ced90a on `exp/top-plate-gmain-t28`. Isolated work on
  `exp/cdac-flat8-device`. No unrelated user edits were overwritten.
- Implemented native MOM unit/banks/512-unit differential CDAC, native
  reference switches and gate inverters, test/control VA, exact-OA runners,
  PSF/ADC analysis, curated figures, config/report/tests and manifest updates.
  Previous 8/10-bit circuits, Bootstrap and StrongARM remain read-only.
- MOM selection: 4.004 fF, 1.025 pF/side. Default Model MC was inactive;
  only verified mismatch=1 statistics count. Accepted 200 independent-array
  MC runs have 512 random variables, worst weight-oracle DNL/INL
  0.10243/0.06555 LSB. This is not switched MC, layout matching or yield.
- Reference W/L experiment changed sqrt-weight scaling to proportional
  multiplicity. Twenty-seven MOS DC cases and thirteen input/PVT transients
  characterize the retained core-device candidate. Nominal 256-code DAC
  DNL/raw INL 0.000741/0.093465 LSB; all 256 ADC code-center outputs agree.
- Complete native APS 1024-point coherent run: 48.7595-dB SNDR,
  7.8072-bit ENOB, 64.9367-dB SFDR, about 58 minutes, result.ok. Native sampler
  and CDAC/reference MOS are real; comparator/controls/finite-R references
  remain stated abstractions. No physical transient noise was enabled.
- Candidate remains NOT qualified. Reference reset shows core terminal
  stress (example bit-5 bottom 1.01151 V at 490.234 ns vs 0.99-V model
  limit). Phase/slew/TG-multiplier experiments and real StrongARM interface
  are not promoted by a correct final code. A 1.8-V MSB-only candidate fails
  VCM Ron at SS/0.81 V/-40 C (4.54 Mohm), so no ref18 array was built.
- Another independent failure: first SS/0.81-V/-40-C full-swing sample
  -27.406 mV, later repeat -0.186 mV. Same literal native CDAC with only
  input Bootstrap replaced by 150-ohm relay gives -0.001734 mV. Keep the
  original Bootstrap unchanged; large-signal acquisition needs a new round.
- Final OA audit: 35 new schematics zero markers, 2 semantic symbol/VA cells,
  11 native export comparisons equal except generation date; six historical
  dependencies equal; VA bytes equal. Parent extraction OSSHNL-109 was fixed
  by owned hierarchy Check & Save, never by patching final DUT connectivity.
- Handoff recheck on the morning of 2026-10-20 stopped at library read:
  CIW/RAMIC endpoint 127.0.0.1:65490 refused connection. No OA mutation or
  forced application restart followed. The audit above is the last saved
  successful audit, not a claim of current bridge availability; reload the
  bridge before further remote circuit work.
- Original APS is the primary dynamic evidence. AX pilot is only a numerical
  acceleration check; its preset overrides numerical options, not a valid
  substitute for fine-step stress measurements. An optional extended AX
  launcher did not leave a completed API result; final process readback
  shows no such active Spectre jobs. It is not counted as accepted evidence.
- Validation: Python syntax/focused contracts, YAML, evidence consistency,
  generated-figure inspection and diff hygiene. Evidence audit explicitly
  reports performance failures; a successful audit exit is not circuit pass.
  Physical noise/MOS MC/ADC threshold DNL/buffer-clock implementation/layout
  signoff remain open, recorded rather than fabricated.
- Scoped .gitattributes to the two new VA files: LF preserves tested hashes
  on Windows checkouts. The exact tested controller terminal blank line is
  retained with a per-file EOF-whitespace exception; no global Git setting
  or historical source normalization is changed.
- Artifacts: `output/cdac8_device/`; durable
  `docs/cdac_flat_8b_device.md` and `docs/figures/cdac8_device/`. Scoped local
  commit under the target policy; no push, no merge, no experience extraction.

## 2026-10-19 - Eight-bit flat migration through native full-load sampling

- Target: `plan/2026-10-19-eight-bit-flat-migration/plan.md`. Clean starting
  branch `exp/top-plate-gmain-t28`, HEAD c5d6c08, ahead five. No user edits
  overlapped. Active spec changed to eight-bit flat; original spec copied
  intact to `config/design_spec_10b.yaml` (SHA256 38d03e97...5ce07fd).
- New dedicated eight-bit VA/controller, exact-OA run generators, analyzers,
  RC constraints, evidence audit, figures and focused regressions. Routed
  historical ten-bit noise/test consumers explicitly to the archived spec.
  README/architecture/budget/sampling status/manifest updated. Existing
  interactive review frozen/labeled ten-bit to prevent mixed-bit thresholds;
  changed report fingerprints intentionally remain requiring review.
- Remote preflight: bridge 0.8.0, `t28_io`, correct CIW/library/tsmcN28 and
  Spectre 21.1.0.509. Created seven SAR_ADC_T28 cells: flat CDAC, eight-bit
  controller (symbol/VA only), comparator macro copy, macro TB, native sized
  bootstrap copy, matched bootstrap TB and real StrongARM interface TB.
  All six electrical schematics finish with zero markers. No floating
  controller schematic placeholder. Preserved unrelated windows/PDK.
- Six read-only dependencies have equal before/after API readbacks. Three
  final saved-OA exports equal the primary simulated hierarchy except date;
  downloaded controller VA equals local bytes. Primary simulations only
  assign design variables/options/analysis/save, never repair DUT connectivity
  inside a run netlist. Separate old-branch-removal diagnostic is explicit.
- 49 accepted Spectre runs: four VA, four RC, thirteen closed-loop macro,
  sixteen bootstrap, twelve StrongARM on/off interface. Negative controls
  intentionally fail accuracy/thermal gates, not solver execution. Python
  and VA cover 256-code ramp; 16384-point ideal VA correlates every code.
  Ideal/noisy VA ENOB 7.804970/7.329375; no physical-noise claim.
- Macro: ten nominal/transition inputs pass, 39.52-ns conversion and maximum
  0.003207-LSB settling error. Slow reference/high relay R fails 4.40758 LSB;
  top parasitic/kickback single-point sensitivities characterized separately.
- Native 0.5-um failed larger-load acquisition; independent 1-um copy passed
  five points, held error <=0.126413 mV against 1.7578125-mV gate. Tighter
  precision differs <=0.00845 uV. Candidate-only extremes have zero CMI or
  suppressed warnings, four inherited SFE-1131 each; old core warnings remain.
  Main terminal-difference audit is bounded, not full foundry reliability.
- Selected real StrongARM on/off interface: +/-0.25-LSB decisions correct
  within 1.5 ns, peak differential kickback <=0.051338 mV. Zero-input numerical
  resolution is not an offset measurement. Full transistor ADC, PDK CDAC,
  buffer, power, PVT/MC, physical noise and layout are not closed.
- Evidence: `output/eight_bit_flat/` including raw PSF/logs/decks, source
  hashes, all accepted result paths, readbacks, inspected three figures and
  `final_manifest.json`. Durable report: `docs/eight_bit_flat_migration.md`.
- Validation: six focused eight-bit tests, two directly affected ten-bit
  behavioral tests, 23 review dependency tests, review build check, full
  49-run evidence audit, Python compile, YAML parse, full scoped diff check.
  Local migration commit prepared; no push authorized or performed.

## 2026-09-30 - Visible overview derivation

- Restored an always-visible four-step LSB/quantization → ENOB/SNDR → total
  error → analog remainder derivation inside the main ADC graph.
- Added short module allocation formulas, retaining provisional allocations
  and separating deterministic limits from RMS noise. Shared numeric registry
  supplies results; no specification or experiment changes.
- Build, formulas, 23 tests, JS syntax and diff checks pass. Browser confirms
  both routes and visible formulas; click automation was inconclusive.
- Preview: output/review/math-overview-preview.png. Local commit only, no push.

## 2026-09-30 - Review active top-plate freeze

- Refreshed global/sampling/CDAC progress for top-plate-only architecture,
  physical complementary hold path and six-device PGATE driver.
- Recorded 522aa0f provisional freeze, 0.605518-mV five-point maximum and
  unchanged failing 0.439-mV allocation. Kept PGATEB/well risk and ideal
  STRACK/clock/reference boundaries; did not resume experiments.
- Retained bottom-plate experiments and earlier comparison image as history;
  removed obsolete VSS-off schematic links from current top-plate stages.
- Validation: 23 tests, build/diff checks and browser five-point table/flow,
  no console errors. Preview: output/review/topplate-progress-preview.png.
- Local frontend/data commit only; no OA changes, simulation or push.

## 2026-09-30 - Provisional sampling baseline freeze

- Recorded user acceptance of circuit revision 522aa0f with 0.605518-mV
  five-point nominal error as a provisional stage baseline. Retained
  topology, sizes and timing; paused further experiments.
- Updated active architecture status, PGATE report and design decision
  log. Original 0.439-mV allocation, measured results and open reset/well
  risks preserved. No circuit, simulation, PDK or remote OA changes.
- Validation: scoped documentation review and git diff --check. Local
  commit: `docs: freeze provisional top-plate sampling baseline`.
  Circuit revision was previously pushed; this documentation update is
  local only, with no push or merge in this target.

## 2026-09-30 - First T28 PGATE local driver (netlist only)

- Added generator/analyzer and circuit report for six thick-oxide driver
  devices per side, replacing only ideal PGATE steering. Kept multi=4
  hold path, external timing and STRACK baseline fixed; updated active
  status/design notes. No OA, PDK or prior export modifications.
- Five TT/0.9-V/27-C Spectre runs completed with zero errors, four
  inherited SFE-1131 warnings each, no CMI or suppressed warnings.
  Worst raw error 0.605518 mV versus 0.842425 mV matched control;
  still fails 0.439 mV. PGATEB reset exposes 0.497386-V positive
  PMOS drain/body bias; this candidate is not reliability-cleared.
- Two transport failures on -0.4 V were excluded; a final bounded retry
  retrieved complete results. No indefinite retries or OA fallback.
- Validation: compile, five-input generator/boundary checks, deck delta
  review, per-run hash and PSF validation, zero-error logs, diff check.
  Artifacts: output/top_plate_pgate_driver/. Report:
  docs/top_plate_pgate_driver.md. Scoped local commit:
  `test: implement T28 top-plate PGATE driver`; no push.

## 2026-09-30 - Return to top-plate sampling and screen T28 GMAIN hold path

- Selected top-plate sampling as the sole active design line; marked the
  bottom-plate reports historical and added one current-status source in
  README/architecture/design notes. No old data or OA cells were deleted.
- Created exact-hash top-plate-only copied decks from the prior OA export,
  removing only the unrelated XBP testbench instance/auxiliaries. Spectre
  21.1 reproduced the ideal-relay +0.8-V bound at 0.174102 mV versus
  0.174132 mV in the mixed fixture. Fourteen zero-error TT/0.9-V/27-C
  transients screened single T28 NMOS/PMOS pass devices and their parallel
  combination. Single devices failed opposite input endpoints; the
  complementary `multi=4` path passed ±0.8 V but failed ±0.4 V at
  ±0.842425 mV. Smaller `multi=1/2` remained above 0.439 mV at +0.4 V.
- No remote OA/PDK modifications. Raw decks, PSF, logs and JSON remain
  ignored under `output/top_plate_gmain_first_device/`. Current mixed
  physical/ideal boundary and unresolved control/accuracy/SOA are in
  `docs/top_plate_gmain_device_screen.md` and
  `docs/sampling_architecture_status.md`.
- Validation: Python compile, exact export/deck contracts, bounded changes,
  Spectre completion, finite/aligned PSF, phase ordering, terminal/current
  readback and warning inventory, per-case JSON reanalysis, owned diff and
  `git diff --check`. Commit locally as
  `test: start T28 top-plate GMAIN hold device`; no push requested.

## 2026-09-30 - Screen T28 GMAIN hold pull-down in full CDAC

- Replaced only the copied-netlist ideal `SHOLD` relay with a real T28
  `nch_18_mac` NMOS, sweeping multiplicity 4/16/64 while retaining ideal
  `STRACK`, clamp and clock driver. No OA or PDK changes.
- Seven zero-error Spectre 21.1 transients: five inputs at `multi=4`,
  +0.8 V at `multi=16/64`. Five-point bottom maximum raw error was
  0.004223 mV and representative gate-off margin before reset at least
  0.846 ns. Top-control error still reached 6.822 mV. Printed MP8 SOA
  warnings and 550-11,010 suppressed warnings prevent signoff.
- Validated hashed OA-source and ideal-control deck identity, a bounded
  deck diff, phase order, saved terminal currents, source-current reduction,
  warning inventory, Python compile and per-case JSON reanalysis. Results
  and raw logs are ignored under `output/bootstrap_t28_hold_pulldown/`;
  curated evidence is in `docs/bootstrap_t28_hold_pulldown.md`.
- Commit policy: `test: screen T28 bootstrap hold pull-down`; local only,
  no push requested.

## 2026-09-30 - Review maintainability boundaries

- Moved graph composition from browser code into one declarative graph source;
  build resolves analysis, figure, experiment and topology references. Retired
  obsolete flow and combined topology files (recoverable through Git).
- Split presentation formatting and static-diagram adapter; separated topology
  reasoning from image coordinates. Added reviewed evidence/connectivity baselines
  and read-only --impact reporting, with affected-node review status.
- Validation: 22 focused tests, formula regression, JS/build/diff checks, 31-node
  migration comparison and browser navigation/device-selection smoke pass.
- No OA, Canvas connection, simulator or experimental result changes. Screenshot:
  output/review/refactor-preview.png. Concurrent circuit plan preserved.
- Commit policy: refactor: separate review data rendering and impact checks;
  local only, no push requested.

## 2026-09-30 - Screen protected bootstrap in full CDAC

- Target: integrate the independent OFF_MAIN-before-reset protected-bootstrap
  copied netlist into the exact full 5+5 CDAC exports and compare top/bottom
  paths, ideal/T28 top clamps, and VIN/VSS ideal main-gate hold biases.
- Local changed areas: bounded plan, exact-hash copied-deck generator and
  analyzer, result report, design-log entry, and this log. Fifteen decks,
  logs, PSF, and per-case/aggregate JSON remain ignored under
  `output/bootstrap_full_cdac_isolation/`.
- Remote OA changes: none. Original OA exports and PDK files remained
  read-only. Spectre 21.1 ran only generated copied decks via `t28_io`.
- Validation: fifteen zero-error TT/0.9-V/27-C transients, hashed source
  checks, 24-call/full-CDAC deck-contract checks, finite waveform reads,
  phase-order checks, targeted MN11/reference/source-current probe,
  warning inventory, Python compile, JSON reanalysis, and owned diff review.
  With ideal clamp, VIN-relative hold failed at ±0.8 V by 6.261925 mV;
  ideal VSS-off hold reduced five-point bottom raw error to 0.004218 mV
  maximum, but printed MP8 SOA warnings. T28 clamp + VSS-off still had
  -7.538001 mV raw error and printed clamp SOA warnings. No OA promotion.
- Commit policy: `test: screen protected bootstrap in full CDAC`; local
  commit only, no push requested.

## 2026-09-30 - Simplify topology review copy

- Removed repeated disclaimers and duplicate headings; moved assumptions/version
  metadata into a disclosure. Retained phase conditions and connection/inference/
  verification content. No netlist, image, simulation or remote changes.
- Build, JS syntax, diff check and browser visual inspection passed.
- Screenshot: output/review/topology-compact-preview.png. Local commit only;
  style: simplify topology review copy. No push.

## 2026-09-30 - Static Bootstrap topology linkage sample

- Preserved user-supplied netlist/image separately from the T28 DUT; added 15
  instance anchors, five groups, four phases and three typed analysis topics.
  Device selection displays body-inclusive terminals and reverse topic links.
- Sampling review entries open a scoped static-image dialog; no actual Canvas
  connection or remote OA mutation, and no simulation/model-validity claim.
- Validation: 18 focused tests, build/JS/diff checks; browser keyboard phase/group/
  device/topic navigation, image highlights, Escape and narrow layout verified.
  Pointer automation remains outside acceptance. Preview: output/review/topology-preview.png.
- Commit locally as feat: add bootstrap topology review sample; no push requested.

## 2026-09-30 - Screen bootstrap turn-off charge

- Target: distinguish ideal-relay control-clock timing from actual MN11 gate
  slew, and measure held-load sensitivity and charge balance for the
  independent OFF_MAIN-before-reset candidate.
- Local changed areas: one bounded plan, copied-netlist generator/analyzer,
  result report, design-log entry, and this log. Nine exact decks, logs, PSF,
  and JSON are ignored under `output/bootstrap_turnoff_charge_screen/`.
- Remote OA changes: none; the original hashed OA export and PDK stayed
  read-only. Spectre 21.1 ran only copied decks via `t28_io`.
- Validation: nine zero-error TT/0.9-V/27-C transients, finite PSF, output
  KCL and load-charge checks, deck-diff review, zero printed CMI warnings,
  and no diagnostic terminal-level crossings. The 1-ohm relay makes a
  1.6-ps actual gate edge despite a 100-ps clock. Raising SHOLD resistance
  to 20 kohm stretches gate fall to 293 ps but worsens held error to
  -2.647 mV. No case meets the 0.439-mV raw-error gate.
- Commit policy: `test: screen bootstrap turn-off charge`; no push requested.
- Unrelated untracked Canvas-review paths and a modification to
  `scripts/review/build.py` appeared during execution and were left untouched.

## 2026-09-30 - Node analysis and result-figure entries

- Added 24 module-node analysis lists, six scoped/hash-pinned figure bindings,
  embedded image dialog and tighter module layout. Local review sources/build/
  focused tests only; remote OA and ongoing circuit experiments untouched.
- Validation: 17 Python tests, formula regression and syntax checks pass. Browser
  verified all figure loads and keyboard navigation/dialog behavior, node coverage,
  and narrow layout. Automated pointer input did not actuate controls this session;
  pointer acceptance remains unconfirmed. No simulation rerun.
- Artifacts: output/review/index.html, node-analysis-preview.png, figure-preview.png.
- Commit policy: feat: add node analysis and result figures; local only, no push.

## 2026-09-30 - Consolidate review into module branch maps

- One global map now opens five module branches combining constraints, progress,
  results and next actions. Details expand inside nodes; Canvas slots stay with
  their module. Removed separate tabs, block-map panel and bottom detail panel.
- Owned changes: review/app, review README and bounded target plan. No remote
  OA changes, simulation, evidence refresh or source-lock acknowledgment.
- Validation: 13 data tests, formula regression, JS syntax, branch navigation,
  inline expansion, narrow local scrolling and browser error check passed.
- Generated preview: output/review/index.html; loopback port 8765. Local commit
  policy: feat: consolidate review into module branch maps; no push requested.

This file records factual project maintenance. Circuit and architecture
decisions remain in `docs/design_log.md`; reusable lessons require a separate
human-triggered note in `docs/experience/`.

## 2026-09-30 - Isolate bootstrap output before reset

- Target: test the independent OFF_MAIN-before-PHIB-reset sequence on the
  existing full-control bootstrap export, including a no-reset control and
  a short VIN-step isolation challenge.
- Local changed areas: one bounded plan, exact-export copied-netlist
  generator/analyzer, result report, design-log entry, and this maintenance
  entry. Six decks, PSF/logs and JSON are ignored under
  `output/bootstrap_isolate_before_reset/`.
- Remote OA changes: none; direct-SSH Spectre 21.1 ran copied decks only.
  Original OA, original hashed netlist and PDK files stayed read-only.
- Validation: six zero-error TT/0.9-V/27-C transients, hash check, finite
  aligned waveforms, source-resistor and MN11/load KCL, full-transient
  PDK-terminal diagnostic comparison, zero printed CMI warnings, Python
  compile, JSON parse and owned diff check. Delayed PHIB reset sequence contributes
  about +0.080 mV after a -2.53-mV turn-off error; best held error remains
  -2.452 mV, failing the 0.439-mV gate. Ideal relays are not physical T28.
- Commit status: commit locally as
  `test: isolate bootstrap output before reset`; no push requested.

## 2026-09-30 - Simplify review into block-linked flow diagrams

- Target: respond to user review by replacing the flat, document-centric UI
  with explicit circuit correspondence and connected derivation/progress graphs.
- Local changes: review frontend, extracted flow content and latest A/B summary,
  public-payload filtering, focused tests, maintenance guide and target plan.
  Repository document links, raw source viewer, sidebar, hashes and scenario
  controls were removed from the frontend. Internal provenance stays in source
  data/build checks; generated HTML/data contains no report documents or paths.
- The separate committed `e0c12e7` A/B report was read and summarized without
  modifying any circuit-target file. Ideal split-gate -2.482-mV results are
  explicitly mechanism bounds, not implemented T28 acceptance.
- Validation: 13 Python contract tests; existing formula/observation gates;
  Python compile and JS syntax. Browser checked global and Bootstrap flow views,
  node/block highlighting and explanations, no document links/viewer, no edge
  crossing unrelated Bootstrap nodes, and 390px graph-local scrolling without
  page overflow. No browser errors/warnings in the inspected log.
- Remote OA/Canvas changes: none; no simulation. Existing loopback preview
  remains available at port 8765. Local commit only; no push requested.

## 2026-09-30 - Screen bootstrap netlist A/B variants

- Target: rapidly test hold-leakage removal, PHIB timing, and ideal
  source-relative main-gate steering on an exact OA-exported full-control
  bootstrap netlist.
- Local changed areas: target plan, one controlled variant generator/runner,
  result report, bounded design-log entry, and this maintenance entry.
  Eight copied decks, Spectre logs/PSF, and JSON remain ignored under
  `output/bootstrap_netlist_fast_ab/`. The unrelated design-review
  workbench was left untouched.
- Remote OA changes: none; all simulations used direct SSH Spectre 21.1 and
  left OA, original export, and PDK models read-only.
- Validation: original SHA-256 checked; eight TT/0.9-V/27-C transients
  completed with zero Spectre errors; finite/aligned waveforms, input
  source-resistor balance, output-node KCL, full-transient MOS terminal
  diagnostic limits and printed CMI warnings reviewed. All variants fail
  0.439-mV raw held-error target. The body-only core variant also has
  five printed CMI warnings; ideal-relay bounds are not T28 implementations.
- Commit status: commit only this target locally as
  `test: screen bootstrap netlist A/B`; no push requested.

## 2026-09-30 - Add local design review workbench v1

- Target: link formal benchmark constraints, module workflow and a future
  Analog Canvas slot in a maintainable local review interface.
- Local changed areas: `review/` source/data/fingerprints/maintenance guide,
  `scripts/review/build.py`, focused `verification/review/` checks, README,
  target plan and this entry. Generated self-contained HTML/data remain ignored
  under `output/review/`. Existing specs and circuit reports remain read-only.
- Content: 13 metric nodes, 12 steps and eight evidence records; sampling and
  Bootstrap form the vertical slice. Other modules explicitly retain partial
  coverage. September 30 current-path diagnosis is not presented as a repair.
- Validation: ten Python contract tests, Node benchmark/formula/gate/scenario
  checks, Python compile, JS syntax and diff checks. Browser-tested all three
  views, module/evidence links, embedded source reading, candidate/reset and
  320/390-pixel no-overflow layouts. No captured browser errors/warnings.
  The in-app browser disallows file URLs; no bypass was attempted. The verified
  preview is loopback-only at port 8765. No external frontend assets are needed.
- Remote OA/Canvas changes: none; historical netlist hashes are explicitly
  not a fresh readback. Concurrent bootstrap fast-A/B files are unrelated and
  excluded from this commit. No simulator was run for this frontend target.
- Commit policy: local `feat: add local ADC design review workbench`; no push.

## 2026-09-30 - Audit full-control bootstrap turn-off currents

- Target: distinguish turn-off output charge error from unintended hold input
  loading in the existing full-control mixed-voltage bootstrap fixture.
- Local changed areas: target plan, one exact-export transient-current probe
  script, audit report, bounded design-log entry, and this maintenance entry.
  New Spectre deck, log, PSF, and JSON remain ignored under
  `output/bootstrap_current_path_audit/`.
- Remote OA changes: none. The bridge tunnel was down at start, so the
  existing hashed OA export was simulated via direct SSH Spectre; no OA cell
  or PDK model file was edited.
- Validation: exact source SHA-256, Spectre 21.1 zero errors, 62 aligned
  finite saved signals (including terminal currents), source-resistor/device
  current balance, load-charge/KCL balance, JSON parse, Python compile, and
  owned diff review. The input-loading path is confirmed; unique parasitic
  attribution for turn-off charge still requires a distinct OA topology test.
- Commit status: commit only this audit locally as
  `test: audit bootstrap turn-off current paths`; do not push without request.

## 2026-09-29 - Screen independent mixed-voltage bootstrap candidates

- Target: build separately named OA experiments to address known bootstrap
  terminal-stress paths and measure stress and raw sample/hold error together.
- Local changed areas: target plan, two candidate YAMLs, OA creator,
  exact-export Spectre runner, result report, manifest, design log, and this
  entry. Generated readback, OA exports, decks, PSF, and logs remain ignored.
- Remote OA changes: created only the two experimental bootstrap
  schematic/symbol cells and their two differential schematic testbenches.
  All four schematics read back with zero check markers; existing bootstrap,
  CDAC, comparator, and PDK cells were not modified.
- Validation: two TT/0.9-V/27-C Spectre 21.1 differential transients completed
  with zero errors. The first retained 20 SOA warning examples and failed
  raw hold at -8.972 mV. The second had zero `CMI-275x` warnings and 144
  terminal metrics below diagnostic comparison levels, but failed raw hold
  at -8.755 mV versus 0.439 mV. Exact OA netlist hashes, model mappings,
  and source/readback correspondence were checked. No reliability signoff,
  PVT, noise, layout, or full-CDAC acceptance is claimed.
- Commit status: commit this target locally on
  `exp/bootstrap-protected-eval`; do not push without request.

## 2026-09-29 - Integrate T28 StrongARM with full split CDAC

- Target: diagnose the direct comparator/CDAC electrical interface, including
  on/off-clock controls at positive, negative and zero small differential input.
- Local changed areas: target plan, YAML conditions, OA creator, exact-export
  Spectre runner, result report, cell manifest, and this log. OA export, PSF,
  decks, readback, and six run logs remain ignored under
  `output/strongarm_cdac_integration/`.
- Remote OA change: new `SAR_ADC_T28/tb_sar_cdac_strongarm_diag/schematic`
  only. Existing W185 CDAC, StrongARM, bootstrap cells, and PDK were read-only.
  The new schematic has 25 instances and zero markers; exact netlist export
  connects StrongARM input gates to the full CDAC comparator-side top plates.
- Validation: six TT/0.9-V/27-C Spectre 21.1 runs completed with zero errors;
  matched ±0.439453-mV cases resolved in 224.116 ps with correct polarity.
  A/B clock-induced peak was 0.374181 mV, still 0.365124 mV at decision.
  Zero-input control showed a 0.375136-mV latch-dependent kickback but has
  no correctness verdict. Exact OA/source hashes, PSF coverage, Python/YAML
  and owned diff were checked. Existing bootstrap SOA warnings remain a
  physical-design blocker; no noise, mismatch, PVT, or full-conversion
  acceptance is claimed.
- Commit status: commit only this target as
  `test: integrate T28 StrongARM with split CDAC`; no push requested.

## 2026-09-29 - Map bootstrap terminal stress

- Target: locate complete-driver transistor terminal overstress before
  selecting an independently named protected bootstrap topology.
- Local changed areas: target plan, read-only OA-export/waveform audit script,
  result report, design log, and this maintenance entry. Ranked JSON and CSV
  remain ignored under `output/bootstrap_soa_map/`.
- Remote OA changes: none. All `SAR_ADC_T28` cells and PDK files were
  read-only; the healthy `t28_io` bridge and Spectre 21.1 were checked.
- Validation: exact OA-export SHA-256 and successful baseline-run identity;
  12 source-parsed MOS devices per differential side, six terminal pairs each
  (144 metrics), finite and aligned saved waveforms, and 19 Spectre SOA
  warning witnesses consistent within 20 mV. The driven cycle showed up to
  1.787 V on pump devices, 1.674 V in control/discharge, and 1.148 V `Vgd`
  on the main switch. Python compiled, generated JSON parsed, and the owned
  diff was checked. This is a model-warning screen, not foundry sign-off.
- Commit status: commit only this target as
  `test: map bootstrap terminal stress`; push was not requested.

## 2026-09-29 - Verify first-pass T28 StrongARM noise and interfaces

- Target: screen transistor-level comparator noise, local mismatch, selected
  PVT/output loads, and finite-input kickback against initial SAR budgets.
- Local changed areas: dedicated plan, YAML configuration, read-only OA-export
  and Spectre verification script, and result report. Raw exports, decks,
  Monte Carlo samples, PSF, and logs remain under ignored
  `output/strongarm_t28_verification/`.
- Remote OA changes: none. The exact 11-T28-MOS DUT netlist hash matched the
  first-pass baseline; only temporary Spectre analysis decks were derived.
- Validation: Spectre 21.1 noise, mismatch, PVT, and kickback runs; source
  hash/section checks and PSF parsing. Noise was 51 wrong decisions in 192
  near-threshold cycles. Corrected local-MC mismatch had 27 of 32 paired
  draws outside ±0.439 mV. Four deterministic PVT/load points met 1.5 ns,
  with FF/0.99-V device-voltage warnings. The 219.535-fF kickback fixture
  stayed below 0.439 mV; 50 fF exceeded it. An earlier MC model-section
  choice was found inert and its 48 apparent passes were invalidated.
- Commit status: commit only this target's files as
  `test: screen T28 StrongARM noise mismatch and loading`; no push requested.

## 2026-09-29 - Screen bottom-plate top-clamp widths

- Target: hold the full-CDAC bottom-plate fixture and 22 bootstrap pumps
  fixed while testing narrow T28 top/split clamp widths against the raw
  0.439-mV held-error gate; a bounded W185 probe was added after W200
  narrowly missed. No shared-boost construction or PVT was authorized.
- Local changed areas: plan, width configuration, independent OA creator,
  backward-compatible Spectre runner/analyzer options, cell manifest,
  result report, design log, and this maintenance entry. OA exports, source
  hashes, readback, decks, PSF, warnings, metrics, and plots remain under
  ignored `output/bootstrap_bottom_plate_clamp_width_screen/`.
- Remote OA changes: created only five independently named experimental CDAC
  schematic/symbol pairs and five testbench schematics, W500/W250/W200/W185/
  W100. Readback found 93 CDAC and 21 testbench instances and zero markers
  per variant; the technology remained `tsmcN28`. Existing bootstrap,
  prior CDACs, macro, PDK, and StrongARM cellviews remained read-only.
- Validation: exact OA Spectre exports had separate SHA-256 hashes and
  verified four T28 clamp sizing/connectivity statements plus the 22+2
  bootstrap hierarchy. Three TT/0.9-V/27-C static-input transients completed
  for each W500/W250/W200/W100 variant; all five completed for W185, with
  zero simulator errors. The W185 maximum raw error was 0.43378 mV, a
  5.22-uV nominal margin; all cases retain device SOA warnings, so physical
  acceptance is blocked. An OA-export formatting difference (`185.00n`)
  initially tripped the runner's strict width regex before simulation; the
  regex was corrected and the identical hashed export was used. Python
  syntax, YAML parsing, readback, metrics, and owned diff were checked.
- Commit status: commit only this target's files as
  `test: screen bottom-plate clamp width`; push was not requested.

## 2026-09-29 - Start T28 StrongARM transistor-level design

- Target: create an isolated first-pass 11-MOS `tsmcN28` StrongARM comparator,
  symbol, and transient testbench; measure nominal polarity, reset, and
  near-threshold resolution without claiming statistical closure.
- Local changed areas: this target's plan, OA creation/readback automation,
  exact-export Spectre runner, and focused result report. Generated OA
  export, PSF, JSON, and run decks remain under ignored
  `output/strongarm_t28_first_pass/`.
- Remote OA changes: created only `SAR_ADC_T28/sar_strongarm_t28` schematic
  and symbol and `SAR_ADC_T28/tb_sar_strongarm_t28` schematic. Readback
  verified 11 T28 MOS, pin/terminal/size connections, and zero markers in
  both schematics. Existing macro, active bottom-plate cells, PDK, and
  Analog Canvas remained read-only.
- Validation: exact OA netlist SHA-256
  `628f493c46c7c4df1e5e6262ab563c466958fd7ce182489515c507f3689be581`;
  six TT/0.9-V/27-C Spectre 21.1 transients completed with zero errors.
  ±0.439453-mV input gave correct polarity, complete reset, and 223.35-ps
  signed 0.45-V output resolution against the nominal 1.5-ns window.
  Initial local SSH export and input-parameter declaration errors were
  diagnosed and repaired; one testbench instance/signal name collision was
  removed before the final full rerun. Four PDK scoped-`scalefactor`
  warnings remained. Noise, mismatch, PVT, kickback, and layout are open.
- Commit status: commit only owned files as
  `feat: add T28 StrongARM first-pass schematic and testbench`; push was
  not requested.

## 2026-09-29 - Evaluate bootstrap bottom-plate sampling

- Target: compare same-bootstrap top-plate and true bottom-plate sampling in
  matched full differential 5+5 CDAC fixtures, then test a T28 top clamp.
- Local changed areas: target plan, parameterized OA creator, exact-export
  Spectre runner, analytical/phase analyzer, configuration, result report,
  cell manifest, design log, and this maintenance entry. Generated netlists,
  PSF, warnings, CSV/JSON, and SVG remain ignored under
  `output/bootstrap_bottom_plate_eval/`.
- Remote OA change: created only the two experimental CDAC schematic/symbol
  cells and their two testbench schematics named in the target plan. Readback
  found 93/21 electrical instances and zero markers per variant; exact OA
  exports contain 22 bottom plus two top copies of the existing bootstrap.
  Existing bootstrap and macro-model OA objects remained read-only.
- Validation: 9/9 ideal-clamp and 5/5 T28-clamp TT/0.9-V/27-C Spectre cases
  completed with zero simulator errors from separately hashed OA exports.
  An initial 1-ns result download failed at the Windows transport/rename
  stage; the exact case reran successfully. The analytical matrix gives
  ideal binary bit weights and monotonic 1024-level transfer, explicitly not
  a transistor-level physical DNL/INL claim. Python compiled; YAML parsed;
  both phase SVGs parsed; OA markers, hashes, selected netlist statements,
  and raw error metrics were checked. Every transient retains SOA warnings.
- Decision: the ideal clamp reduced the matched raw held error from 1.5320
  to 0.00790 mV, but the T28 NMOS clamp yielded 2.0960 mV versus the
  0.439-mV guardrail and itself triggered a `Vgd` SOA warning. Do not
  promote this physical candidate, start PVT/mismatch, or claim a verified
  physical code ramp. Next isolate clamp parasitics and reduce the 22-pump
  implementation while independently resolving bootstrap/clamp SOA.
- Commit status: ready to commit as
  `test: evaluate bootstrap bottom-plate sampling`; push was not requested.

## 2026-09-29 - Plan bootstrap sampling topology comparison

- Target: define the next bounded switch experiment after the held-error
  ablation and ineffective discharge-device resizing.
- Local change: added `plan/2026-09-29-bootstrap-bottom-plate-evaluation/plan.md`
  with a full-CDAC top-plate baseline, true bottom-plate sampling comparison,
  aperture and raw-error measurements, and an independent SOA gate.
- Remote OA change: none. No new simulation was run for this planning target.
- Validation: reviewed the existing macro connectivity and bootstrap reports;
  checked the plan's owned paths, numerical gates, and `git diff --check`.
- Status: plan ready for execution; no sampling-topology decision has been
  made. The planning change is committed locally and not pushed.

## 2026-08-31 - Screen bootstrap-driver error reduction

- Target: determine whether MN7/MN10 discharge strength, MP8 sizing, or
  external non-overlap can repair the complete bootstrap driver's held error
  before any OA edit.
- Local changed areas: audited diagnostic configuration, exact-export Spectre
  runner, analyzer/plots, result report, target plan, design log, and this log.
- Remote OA change: none. All generated decks assert the existing OA-export
  hash and restrict subcircuit edits to declared instance multipliers.
- Validation: 13/13 one-factor, 8/8 final combination, and 24/24 confirmation
  Spectre cases succeeded. One intermediate SSH upload reset was explicitly
  retained and its exact case reran successfully. Baseline 12.026 mV was
  reproduced; the reasonable and extreme candidates reached only 10.298 and
  9.097 mV. Python/YAML, provenance, result assertions, and both plots passed.
- Decision: do not update OA. Stronger discharge removes the later gate event
  but not the dominant immediate turn-off step, while reducing sample VGS and
  leaving 1.787-V/SOA concerns intact. Next evaluate independent isolation and
  charge-cancellation topology.
- Commit status: ready to commit as
  `test: screen bootstrap driver error reduction`; push was not requested.

## 2026-08-31 - Isolate bootstrap held-sample error

- Target: separate the selected main DNW switch's deterministic turn-off error
  from the complete bootstrap driver's contribution before changing OA or
  expanding PVT.
- Local changed areas: one diagnostic matrix, reproducible Spectre runner,
  analyzer/plots, focused result report, target plan, design log, and this log.
- Remote OA change: none. The analysis preserves the exact automatic OA export
  hash and exact main-device statement; all `SAR_ADC_T28` cellviews remained
  read-only.
- Validation: 40/40 Spectre 21.1 cases completed at TT/0.9 V/27 C. The complete
  differential pair reaches 12.026-mV raw error and -1.510% gain error; the
  absolute-off isolated main reaches 1.390 mV and -0.173%. The driver-added
  fitted term is -1.337%. Both generated plots were visually inspected and
  deterministic case/provenance/result assertions passed.
- Decision: correct the driver discharge/isolation/non-overlap path before
  another main-width sweep or global PVT. Raw 0.439-mV compliance and the
  separate approximately 1.79-V SOA issue remain open.
- Commit status: ready to commit as `test: isolate bootstrap held-sample error`;
  push was not requested.

## 2026-08-31 - Prototype transistor bootstrap driver

- Target: create and correlate the first finite-capacitor transistor-level
  bootstrap sampling switch before global PVT or production-cell design.
- Local changed areas: bootstrap OA create/readback/export automation,
  nominal and width-screen configurations, Spectre runner/analyzer, design
  documentation, manifest, target plan, and this log.
- Remote OA change: created only `SAR_ADC_T28/sar_bootstrap/schematic+symbol`
  and `tb_sar_bootstrap_transient/schematic`. Exact readback confirms the Abo
  NMOS multiplier, all B/D/G/S connections, dynamic input step, symbol ports,
  and zero check markers in both schematics.
- Validation: 9/9 nominal Cboot/input jobs and 12/12 main-width jobs completed
  in Spectre 21.1 from one unedited OA export hash. Acquisition, gate
  overdrive, and Cboot droop pass, but nominal held error reaches 6.463 mV
  versus 0.439 mV. The 2-um main switch remains the best screened seed.
- Blockers: core-device SOA warnings reach about 1.79-V terminal differences,
  and the signal-dependent held error is not fixed by main-switch width.
  Global PVT and production freeze are deliberately deferred.
- Commit status: ready to commit as
  `feat: prototype transistor bootstrap driver`; push was not requested.

## 2026-08-31 - Screen bootstrapped main switch

- Target: test the new bootstrapped-NMOS architecture at the main-switch level
  before building its transistor-level clock/charge driver.
- Local changed areas: PVT/device matrix, three OA create/export tools, batched
  Spectre runner, analysis/Pareto reporting, PDK mapping, manifest, target plan,
  and design documentation.
- Remote OA change: created only `tb_bootstrap_core_main_char`,
  `tb_bootstrap_dnw_main_char`, and `tb_bootstrap_18_main_char` schematics in
  `SAR_ADC_T28`. Each has one real PDK MOS and three sources with explicit body
  connection; existing SAR cellviews were not modified.
- Validation: 27/27 Spectre jobs completed with zero failures, producing 486
  Ron curves and 486 leakage measurements. Fourteen of 18 candidates met the
  global 1-kOhm Ron target. DNW L60/W2 is the preferred electrical seed at
  321.2-Ohm worst Ron and 143.8-nA maximum leakage.
- Scope boundary: the drive was ideal `Vgate=Vin+VDD`; no finite bootstrap
  capacitor, transient driver loss, foundry reliability sign-off, or production
  switch is claimed.
- Commit status: ready to commit as `feat: screen bootstrapped main switch`;
  push was not requested.

## 2026-08-31 - Screen transmission gate across PVT

- Target: compare standard- and high-VT plain transmission gates across the
  verified SS/TT/FF, supply, and temperature grid before creating a production
  sampling switch.
- Local changed areas: PVT configuration, audited corner/device mappings,
  high-VT OA create/export automation, batched Spectre runner, analysis and
  design documentation, manifest, target plan, and this log.
- Remote OA change: created only
  `SAR_ADC_T28/tb_tg_switch_hvt_char/schematic`. Readback confirmed the two
  intended HVT MOS devices, five sources, six nets, body ties, and no floating
  terminals; existing SAR cellviews were not modified.
- Validation: 27/27 batched Spectre jobs completed with zero errors, covering
  216 Ron curves and 216 off-leakage measurements. The batching exactly
  reproduced the independent TT nominal Ron and leakage. No candidate passed
  all PVT points; the target reports the bounded no-solution rather than
  relaxing 1 kOhm.
- Decision: do not create a production plain-TG sampling switch. The next
  target is a reliability-aware bootstrapped NMOS sampling switch; CDAC
  bottom-plate switches remain separate.
- Commit status: ready to commit as `feat: screen T28 switch across PVT`;
  push was not requested.

## 2026-08-31 - Characterize T28 transmission-gate switch

- Target: begin transistor-level CDAC/sampling design with a bounded PDK
  transmission-gate Ron and leakage fixture.
- Local changed areas: switch-characterization configuration, OA
  create/export automation, Spectre runner, analysis/reporting script, design
  documentation, manifest, target plan, and this log.
- Remote OA change: created only
  `SAR_ADC_T28/tb_tg_switch_char/schematic` with verified
  `tsmcN28/nch_mac` and `pch_mac` devices. Readback confirmed the two parallel
  channels, complementary gate sources, and explicit body connections. The
  unrelated unsaved ISCAS IO-ring session and dialog were not touched.
- Validation: the automatic OA export preserved the topology; all 12 TT/27-C
  Spectre Ron cases completed with zero errors. Four met the 1-kOhm limit. The
  minimum-width passing seed is `Wn=Wp=2 um, L=30 nm`, with 911.4-Ohm maximum
  Ron and 36.0-nA full-stress off leakage. It remains intentionally unfrozen
  pending PVT, leakage/hold, and transient error checks.
- Commit status: ready to commit as
  `feat: characterize T28 transmission-gate switch`; push was not requested.

## 2026-08-30 - Repair OA electrical macro-model loop

- Target: replace the floating structural OA top with an executable nominal
  closed-loop SAR electrical macro testbench.
- Local changed areas: controller scalar port contract, OA builder, focused
  contract test, electrical-macro documentation, manifest, target plan, and
  this log.
- Remote OA changes: created `sar_macro_controller_10b/symbol+veriloga` and
  rebuilt the owned CDAC, sampling, comparator, and top schematics. No
  placeholder controller schematic remains. Unrelated libraries, PDK data,
  and the unsaved `PLAYGROUND_AMP/canvas_test` window were untouched.
- Validation: all four schematic check-marker counts are zero; OA readback
  and automatic Spectre export contain the complete controller/CDAC path;
  Spectre 21.1 completed the unmodified exported circuit with zero errors.
  The code-768 case returned 768, asserted `VALID` after 49.5201 ns, stayed at
  0.08735 LSB maximum pre-compare residual, and resolved all ten decisions
  with the correct sign. The remaining five Spectre warnings are external
  AHDL/PDK environment notices.
- The full 11-case correlated Spectre regression also passed execution after
  the shared controller update. All six nominal code centers remained exact
  and below 0.25 LSB; the deliberate slow-RC, parasitic, and 1-fF-kickback
  cases continued to expose their expected resolution, code, and sign
  failures.
- Commit status: ready to commit as `fix: close OA SAR macro-model loop`; push
  was not requested.

## 2026-08-30 - Complete topology-aware electrical macro-model

- Target: replace isolated phase fixtures with one closed-loop pre-transistor
  electrical model for sampling, differential 5+5 CDAC switching, reference
  memory, comparator regeneration/reset/kickback, and SAR sequencing.
- Local changed areas: one parameter contract, electrical DUT and testbench,
  unrolled Verilog-A controller, analytical/Spectre runner, focused regression,
  architecture/result documentation, OA generator, manifest, and target plan.
- Remote OA changes: created only `sar_cdac_macro_10b`,
  `sar_sampling_macro`, `sar_comparator_macro`, their symbols, and
  `tb_sar_macro_transient` in `SAR_ADC_T28`. Existing OA cells, PDK content,
  and the unsaved `PLAYGROUND_AMP` schematic remained untouched.
- OA correction: enlarged CDAC switch spacing and replaced the compact
  generated CDAC symbol with a wide-pitch review symbol after readback exposed
  adjacent terminal-stub shorts. Final connectivity readback is clean and the
  hierarchical Spectre netlist exports successfully.
- Validation: exact capacitance-matrix/static regressions, eleven Spectre 21.1
  transients, waveform/metric extraction, focused tests, OA parameter/net
  readback, symbol-port audit, Check and Save, hierarchical netlist export,
  and visual review.
- Results: the canonical split load is `32Cu=219.53504 fF`. Six nominal code
  centers were exact with <=0.102 LSB settling residual and 49.52 ns latency.
  Deliberate slow-RC, assumed-parasitic, and 1-fF-kickback cases exposed
  expected failures.
- Scope limit: no PDK block or dimensions are frozen; random noise, nonlinear
  device effects, PVT, mismatch, reliability, and extraction remain open.
- Commit status: ready to commit as
  `feat: add topology-aware SAR macro-model`; push was not requested.

## 2026-08-30 - Complete module first-order models

- Target: close the abstraction layer between the behavioral ADC and
  transistor blocks with sampling acquisition, comparator regeneration, and
  clock-jitter sensitivity models.
- Local changed areas: tracked model inputs, two ideal Spectre decks, unified
  analysis/simulation runner, focused regression, architecture and result
  documentation, cell manifest, target plan, and this log.
- Remote OA changes: created only
  `SAR_ADC_T28/tb_sampling_acquisition/schematic` and
  `tb_comparator_regeneration/schematic`. Existing OA cells, PDK content, and
  the unrelated unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: both schematic readbacks and Virtuoso netlist exports, six
  Spectre 21.1 transients, analytical correlation, parametric grid/plot
  generation, and focused pass/fail/jitter tests.
- Results: at Cu=6.86047 fF, 40 ns acquisition permits 21.242 kΩ total source
  plus switch resistance. A 20 fF comparator regeneration node requires
  92.42 uS effective gm for a 1.5 ns decision from 0.25 LSB. The tracked clock
  point produces 0.182464 LSB RMS jitter error.
- Scope limit: comparator noise/offset, nonlinear switch behavior, charge
  injection, reference memory, PVT, mismatch, and extracted parasitics remain
  transistor-level work; no production device dimensions were frozen.
- Commit status: ready to commit as
  `feat: complete module first-order models`; push was not requested.

## 2026-08-30 - Establish CDAC/reference settling envelope

- Target: translate the sampling-noise and deterministic-settling allocations
  into a parameterized first-order feasibility envelope for the 5+5 split
  CDAC, reference path, and switch.
- Local changed areas: tracked YAML inputs, ideal Spectre deck, analytical and
  simulation runner, focused regression, architecture/design report, cell
  manifest, target plan, and this log.
- Remote OA changes: created only
  `SAR_ADC_T28/tb_cdac_ref_settling/schematic` from analogLib pulse,
  resistor, capacitor, and ground instances. PDK content and the unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: schematic connectivity/parameter readback, Virtuoso Spectre
  netlist export, four Spectre 21.1 transient runs, analytical correlation,
  1,440-point local grid generation, two focused tests, and plot inspection.
- Results: kT/C imposes `Cu >= 2.509 fF` in the parasitic-free 33-Cu
  equivalent. For Cu=6.86047 fF and a 3 ns window, total `Rref + Ron` must be
  at most 1.593 kΩ. Four Spectre residuals matched the analytical model within
  the specified 1% or 1 uV tolerance.
- Scope limit: no production capacitor or switch was selected; nonlinear Ron,
  reference memory/noise, switching trajectory, mismatch, charge injection,
  kickback, PVT, and parasitics remain open.
- Commit status: ready to commit as
  `feat: establish CDAC reference settling envelope`; push was not requested.

## 2026-08-30 - Establish T28 primitive characterization

- Target: create verified NMOS, PMOS, and MOM characterization schematics and
  obtain the first nominal PDK sizing data.
- Local changed areas: PDK/characterization mappings, reproducible audit,
  schematic creation, netlist export, Spectre run and extraction scripts,
  characterization report, cell manifest, target plan, and this log.
- Remote OA changes: created only `SAR_ADC_T28/tb_nmos_char/schematic`,
  `tb_pmos_char/schematic`, and `tb_cap_char/schematic`. The PDK and unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: bridge/CIW/Spectre health, PDK terminal/CDF audit, schematic
  connectivity and parameter readback, Virtuoso netlisting, three Spectre
  runs, PSF extraction, CSV/JSON generation, visual plot inspection, and six
  existing system regression tests.
- Results: 181-point nominal DC sweeps for each core MOS and a 141-point MOM
  AC sweep all completed with zero errors. At full 0.9 V bias, NMOS/PMOS
  currents are 728/615 uA per um. The 35.6304 fF MOM CDF value correlates to
  35.6355 fF in Spectre, a 0.0143% difference.
- Scope limit: one TT geometry/bias only; no PVT, output/length sweep, noise,
  Monte Carlo, mismatch, or extracted parasitics. The MOM fixture is not a
  final CDAC unit selection.
- Commit status: ready to commit as
  `feat: establish T28 primitive characterization`; push was not requested.

## 2026-08-30 - Record Verilog-A noise-injection learning

- Target: record the reviewed distinction between RMS parameters, event-level
  random realizations, and physical continuous-time noise modeling.
- Local changed areas: one learning note, its bounded plan, and this log.
- Remote OA changes: none; all remote state remained read-only.
- Validation: numerical cross-check against the design spec and fixed-seed
  Spectre summary, targeted Markdown inspection, owned-path review, and
  `git diff --check`.
- Commit status: ready to commit as
  `docs: record Verilog-A noise injection learning`; push was not requested.

## 2026-08-30 - Validate allocated Verilog-A random noise

- Target: enable the stage-1 sampling, comparator, and reference/switching
  random-noise allocations in a separate fixed-seed Verilog-A dynamic deck.
- Local changed areas: allocated-noise testbench, analysis and focused test
  support, verification/design records, target plan, and this log.
- Remote OA changes: none; all libraries, PDK content, and the unrelated
  unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Validation: Spectre 21.1 completed 16,384 conversions with zero errors;
  Python compilation, four focused tests, YAML parsing, and diff checks
  passed.
- Results: 58.059 dB SNDR, 87.453 dB SFDR, and 9.352 bit ENOB versus a
  58.066 dB partial RSS prediction. Of 16,384 codes, 3,641 differed from the
  ideal sequence, all by one LSB, with -0.001 LSB mean error.
- Scope limit: clock jitter, unmodeled distortion, comparator offset, and
  CDAC settling were not included because they are not equivalent to the
  three enabled independent random sources.
- Commit status: ready to commit as
  `feat: validate allocated Verilog-A noise budget`; push was not requested.

## 2026-08-30 - Implement clocked Verilog-A SAR baseline

- Target: add the stage-3 cycle-accurate 10-bit fully differential Verilog-A
  model, curated timing/static/dynamic decks, and Python correlation flow.
- Local changed areas: Verilog-A model, three Spectre-format testbenches,
  EVAS dependency pin, run/analysis automation, focused tests, architecture
  and verification documentation, manifest, and target plan.
- Remote OA changes: none. The `SAR_ADC_T28` library, PDK, active CIW, and an
  unrelated unsaved `PLAYGROUND_AMP` schematic remained read-only.
- Local validation: EVAS 0.7.0 Python backend compiled the model with zero
  lint diagnostics and produced codes 768 and 256 for the held-input timing
  vectors; both conversions completed in 47.5 ns. Source-contract tests and
  1024-code/16,384-sample analysis regressions passed.
- Remote validation: configured the bridge's generic Cadence startup file to
  `/home/cshrc/.cshrc.cadence.IC618SP201`, matching the working `t28_io`
  profile. Spectre 21.1 then compiled the AHDL model and completed timing,
  8,192-sample static, and 16,384-sample coherent-sine runs with zero errors.
  Timing produced codes 768 and 256 with 47.5 ns conversion latency. Static
  analysis produced zero missing codes and zero ideal DNL/INL. Dynamic
  analysis produced 60.954 dB SNDR, 82.213 dB SFDR, and 9.833 bit ENOB, with
  0.001 dB SNDR delta from the Python golden result.
- Correlation correction: aligned the Python dynamic stimulus time with the
  actual 0.45 V crossing at the midpoint of the testbench's 20 ps sampling
  edge. The resulting 10 ps correction reduced code mismatches from 1,362 to
  zero; every mismatch before correction was only one LSB.
- Commit status: committed locally as
  `feat: add clocked Verilog-A SAR baseline`; push was not requested.

## 2026-08-30 - Record error-budget learning

- Target: record the human-requested learning process behind the first
  top-down module error allocation.
- Local changed areas: one note under `docs/learning/`, its target plan, and
  this maintenance entry.
- Remote OA changes: none; all Virtuoso and PDK state remained read-only.
- Validation: numerical cross-check against the tracked design spec and
  behavioral summary, targeted Markdown inspection, owned-path review, and
  `git diff --check`.
- Commit status: ready to commit as
  `docs: record top-down error budget learning`; push was not requested.

## 2026-08-30 - Complete behavioral baseline

- Target: complete the system error budget and bit-accurate ideal model for
  the default 10-bit, 10 MS/s fully differential SAR ADC.
- Local changed areas: design spec, dependency pin, behavioral model, unified
  analysis runner, focused system regression, architecture/verification/error
  budget documentation, and target plan.
- Remote OA changes: none; `SAR_ADC_T28` and all Virtuoso state remained
  read-only.
- Validation: YAML parse, Python compile, two focused regression tests, full
  1024-code ramp, 16,384-sample near-Nyquist coherent sine, JSON/plot artifact
  generation, and visual plot inspection.
- Results: zero missing codes and zero ideal DNL/INL; 60.953 dB SNDR,
  82.033 dB SFDR, and 9.833 bit ENOB at -1 dBFS; allocated error budget
  projects 9.140 bit ENOB with 0.844 dB SNDR margin.
- Commit status: ready to commit as `feat: add SAR ADC behavioral baseline`;
  push was not requested.

## 2026-08-30 - Adopt SAR ADC Agent workflow

- Target: adapt the portable plan-log-experience kernel for a split local Git
  and remote Virtuoso OA project, then publish the repository.
- Local changed areas: root Agent rules, project README, target planning,
  maintenance-log, and experience-note templates.
- Remote OA changes: none; `SAR_ADC_T28` remained read-only for this target.
- Validation: documentation diff checks, targeted rule-presence checks, owned
  path review, Git state review, and GitHub remote verification.
- Commit status: ready to commit as `chore: adopt SAR ADC agent workflow` and
  push to the user-authorized `chenzc24/sar-adc-t28` repository.

## 2026-08-30 - Create remote Virtuoso library

- Target: create an empty remote `SAR_ADC_T28` OA library.
- Local changed areas: idempotent library creation script, cell manifest, and
  design log.
- Remote OA changes: created `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`
  and bound it to `tsmcN28`; no cells were created.
- Validation: bridge/API readback verified library name, path, and technology;
  filesystem inspection showed only OA library metadata.
- Commit status: committed in `f60725f`.

## 2026-08-30 - Scaffold SAR ADC project

- Target: establish the local SAR-ADC repository and default design skeleton.
- Local changed areas: configuration, architecture and verification docs,
  model/netlist/script/verification directories, artifact boundaries, and Git
  ignore policy.
- Remote OA changes: none in this target.
- Validation: Python automation compiled and the initial repository state was
  reviewed.
- Commit status: committed in `069bd7f`.

## 2026-09-30 - Review sampling causal history

- Reorganized the sampling panel into eight key nodes, two current design
  branches and joint acceptance; refreshed global/CDAC summaries.
- Curated reset-isolation, edge/load and full-CDAC evidence. Node details now
  show methods, conditions and result tables without repository document links.
- Kept lumped-load and full-CDAC fixtures distinct; retained ideal-control and
  stress qualifications, and the separate static Canvas sample.
- Validation: 22 focused tests, formula regression, build/check, JS syntax and
  diff check passed. Browser verified result table, figure/topology entries and
  branch layout with no console errors. Preview: output/review/sampling-flow-preview.png.
- Remote OA changes: none. Local scoped commit; no push. Concurrent circuit
  files and its separate maintenance-log entry are excluded.

## 2026-09-30 - Compact review presentation

- Reduced card padding, duplicate heading chrome and action rows; preserved all
  visible reasons and all 31 nodes' detailed content and evidence bindings.
- Moved method/experiment tables to a shared dialog, keeping flow geometry
  stable. Promoted sampling numerical comparisons into the main diagram.
- Validation: 22 tests, formulas, build, JS syntax, diff check; browser verified
  desktop/narrow layout, dialogs, figures, topology, Escape and no console errors.
- Artifact: output/review/compact-preview.png. No circuit/OA changes or push;
  local commit: style(review): compact flow layout and experiment details.

## 2026-09-30 - Stage-specific isolation diagram

- Added supplied isolated-GMAIN drawing and exact draft netlist as a separate
  static topology snapshot; retained original pre-isolation diagram.
- Bound isolation and later relevant sampling nodes to the new version, with
  MN11/net1 and Cu/VOUT/VCM readback. TRACK/OFF remain drawing-only, not invented
  netlist devices; Cu is not represented as a complete CDAC.
- Validation: 23 tests, build, JS syntax and diff check; browser verified old/new
  diagrams, MN11/Cu selection and no console errors. Preview:
  output/review/isolated-diagram-preview.png.
- No remote OA edits or simulation. Scoped local commit; no push. Unrelated
  top-plate GMAIN device experiment files preserved.

## 2026-09-30 - GMAIN result comparison image

- Added user-provided top-plate comparison image to the GMAIN safety node,
  with 0.8 V input, 270 ns measurement and partial-transistor caption.
- Stored original PNG in review/assets with reviewed SHA-256; builder accepts
  this bounded curated-image directory as well as existing output figures.
- 23 tests/build/diff checks pass; browser image dialog verified. Preview:
  output/review/gmain-comparison-preview.png. No OA/simulation or push.
- Preserved pre-existing full_cdac need-review state and unrelated circuit work.

## 2026-10-19 - Canvas 0.5-um bootstrap on the full differential CDAC

- Created `SAR_ADC_T28/sar_bootstrap_canvas_cdac_t28/{schematic,symbol}` by OA
  copy of the selected native source minus standalone Cs, and new
  `tb_bootstrap_canvas_full_cdac/schematic` with two separate full differential
  5+5 CDAC paths and matched source/clock/reference boundary conditions.
- Exact OA-export comparison proves both old bootstrap/CDAC definitions are
  historical-identical and new native candidate is source-identical minus Cs.
  Two new schematics have zero markers; 1-Tohm inverter monitor terminations
  resolved initial unloaded-output markers. No original cell/PDK was changed.
- Completed 14 result.ok Spectre transients: five-point primary comparison,
  two tighter-accuracy cases, two isolated candidate warning checks, and five
  reset-crossing-aligned control cases. Primary worst raw held differential
  error: original 1.535561 mV, native 0.393871 mV (74.35% smaller), all native
  points nominally within 0.439 mV with only 45.13 uV worst margin. No fitting,
  PVT, noise, mismatch or complete-ADC acceptance is claimed.
- Tighter accuracy agrees within 0.105 uV; candidate-only logs have zero CMI
  or suppressed warnings and four inherited SFE-1131 each. Old core-device
  SOA warnings remain. Reset-crossing alignment gives original worst
  1.632060 mV/native 0.393861 mV: gain is not just an earlier reset. Internal
  waveform shape/topology differs, so no one-factor W/L claim is made.
- Saved OA final export matches the primary simulated hierarchy except date;
  all three read-only dependencies have identical before/after API readbacks.
  Report: `docs/canvas_bootstrap_full_cdac.md`; source/analysis scripts and
  manifest updated; provenance, raw logs/PSF, metrics and inspected three
  figures under ignored `output/canvas_full_cdac/`.
- Validation: finite complete waveforms, edge/consistency assertions, YAML
  parse, Python compile, rendered figure inspection and diff checks. Scoped
  local commit; no push.

## 2026-10-19 - Native T28 bootstrap from the user's Canvas topology

- Source: connected Analog Canvas `Bootstrap switch/dut`, revision 357,
  structure revision 32; captured its topology/placement/routes without editing
  the Canvas. User selected native T28 1.8-V devices and clarified that custom
  drawing/device wrappers were not desired.
- Created `SAR_ADC_T28/sar_bootstrap_canvas_t28` schematic/symbol and
  `tb_bootstrap_canvas_t28` schematic. DUT has twelve actual `tsmcN28`
  MOS (ten bootstrap plus a two-MOS physical inverter) and two analogLib caps.
  Verified the original ten MOS body/terminal connections, capacitors and clock
  inverter. No existing project cell or PDK was changed.
- Ran seventeen accepted nominal Spectre transients from exact OA exports:
  all-1-um baseline, 0.5-um and 0.32-um main-switch widths, 0.32-um plus stronger
  reset, then the selected five-input rerun. Selected Mmain W/L=0.5 um/150 nm;
  remaining MOS 1 um/150 nm, Cboot=Cs=1 pF. Worst tested single-ended held error
  improved from 0.554224 to 0.302735 mV; selected worst acquisition error is
  0.056856 mV. The 0.32-um main fails acquisition (3.307791 mV); stronger reset
  did not recover it. No fitting/calibration was applied.
- Final Check & Save: zero markers. Final saved OA netlist equals the selected
  five-point simulated export except generation timestamp. Five final runs
  have no printed CMI/suppressed warnings and retain four model SFE-1131
  warnings each. Sampled MOS terminal-difference peak is 1.75435 V; no PVT,
  mismatch/noise/layout/full-CDAC acceptance is claimed.
- Corrected Windows OpenSSH ControlMaster use process-locally after a download
  failure; repaired three harness read-in failures before accepting baseline.
  Retired six mistaken wrapper/drawing cells created earlier in this target
  after checking exact ownership/saved state. Their source/readbacks are in
  ignored output and can reconstruct them; they were not simulated.
- Evidence/report: `output/canvas_bootstrap_t28/` and
  `docs/canvas_bootstrap_t28.md`; source topology in
  `config/canvas_bootstrap_topology.json`; two new native cells registered in
  `virtuoso/cell_manifest.yaml`. Validation: native OA readback,
  seventeen result.ok transients, fresh-export equivalence, rendered figure
  inspection, Python compile and diff checks. Scoped local commit; no push.

## 2026-10-20 - Independent eight-bit dual-rail CDAC candidate and hard-failure audit

- User clarified eight bits; Canvas is only a topology reference. Built a
  complementary binary SAR characterization fixture, not strict one-sided
  monotonic switching and not a replacement of the selected asynchronous
  controller. Preserve all old baselines, original Canvas and concurrent async
  sources; no Bootstrap/StrongARM/MOM dependency edits.
- New native SAR_ADC_T28 OA: cdac8_dr_sw_b0..b7, cdac8_dr_nominal/literal,
  four tb_cdac8_dr_* schematics, three cdac8_dualrail_* VA/symbol views. The
  array has 512 independent MOM units in literal form, 128 native reference/
  driver MOS, two references, no VCM branch; sample high words P=01111111,
  N=10000000. Restore active code128 inside the next sampling phase.
- Eighteen result.ok APS transients total: five initial smoke/quick and thirteen
  final-source checks. Nine held-input codes correct; worst final comparison
  residual .358645 mV. Nominal/literal/ideal-sampler/StrongARM main-input
  residuals .340652/.340652/.071996/.570838 mV respectively. Actual StrongARM
  outputs resolve at that one input; no full-ADC qualification is inferred.
- All nine cross-input core screens FAIL despite correct codes. Worst is
  1.399620 V |Vbd| at XCDAC.XSN5.MN_LOW, 203.128786 ns, -0.5-LSB input during
  127->128 restore. Separate -0.8-V SAR switch spike is 1.231041 V at
  47.628927 ns. Real CMI and suppressed warning counts retained. Stop only two
  exact owner/PID/command-verified long runs on this TT hard gate; static/sine
  are interrupted at 8.08253/7.95263 us, not complete or accepted. No native
  full static/FFT/PVT/noise/MC/layout acceptance or baseline replacement.
- Fourteen saved OA schematics have zero markers. Final fresh exports match
  simulated hierarchies; three VA remote/local SHA256 values equal; twelve
  read-only dependencies unchanged. Native blocks in analysis wrappers are
  byte-identical to OA exports. Initial VA transition-warning fix is versioned
  separately, with original sources/results retained.
- Canvas CDAC8_DR_Review rev24 and CDAC8_DR_REF_Topology rev27 are fully wired
  review abstractions with native leaf model names/sizes, zero diagnostics and
  equal expected logical topology. Original dut remains revision266. No PDK
  model bodies uploaded; Canvas is review, Spectre is native simulation.
- Report docs/cdac8_dualrail.md, five inspected figures and small metrics
  summary; raw evidence output/cdac8_dualrail/. Eight focused tests pass;
  Python compile/YAML parse/diff checks. Bounded local commit, no push.

## 2026-10-20 - Normal versus half-LSB reference-restore timing figures

- Replotted completed final_nominal / clean_va_input_-3516 only, no simulation,
  circuit, OA or Canvas changes. Same native DUT/VA/context except static input.
  Extended shared-scale overview from 100 to 245 ns and added 202.94..203.50-ns
  zoom with controls/native gate, same BN5 bottom, rails and MN_LOW port stress.
- Saved selects/DOUT verify 192->128 changes one bit, 127->128 changes eight.
  Marked BN5 (N-side bit5, 32Cu), XCDAC.XSN5.MN_LOW drain, at 1.399620 V and
  203.128786 ns. It occurs inside next sampling (201.05..241.05 ns), after
  restore command 203.01 ns/new-rail logic edge start 203.11 ns, not SAR compare.
  At peak PHI=.9 V and BUSY=VALID=0; |Vbd|=1.399620 V, |Vds|=1.396209 V.
  Normal same MOS max |Vbd|=.077786 V in zoom is not the normal global worst.
- Added compare_restore.py, two PNGs, small source/wave-hash/context/peak JSON,
  and bounded report/plan updates. Original raw results and figures untouched.
  Native terminal mapping, deck/VA/source equality, finite complete waveforms,
  word/phase/retained-peak assertions, Python compile and diff checks pass.
  Both figures visually inspected; removed overlapping legends/annotations.
  Scoped local commit only, no push; unrelated history/concurrent work excluded.

## 2026-10-20 - Remove reference-switch driver MOS as a controlled diagnostic

- Six completed result.ok APS transients, exact retained Bootstrap/MOM/VA
  source bodies, TT/.9V/27C, 300ns, no physical transient noise. Netlist-only:
  remove six driver MOS per leaf; retain PMOS-high/NMOS-low unchanged at 1x;
  ideal VCVS supplies correct gate polarities. Reference/driver count128->32,
  original100ps logical blanking/20ps command edges and 127->128 preserved.
  No OA/Canvas/installed VA/PDK or baseline changes.
- Fresh native replay exactly reproduces 1.399620V. Same-size direct gates
  reduce BN5 restore peak to .918698V, restore worst port .925287V, but SAR
  worst MP_HIGH Vgd remains1.040451V (BN5=-.140451V, gate=.9V). Half/double
  pass multiplicity give global peaks1.079517/.983908V respectively; cannot
  conclude that weaker conduction is the remedy. Multiplicity also changes
  parasitics, and fractional .5x is only sensitivity analysis.
- Native gate50% skew4.097ps becomes0 under ideal gates; removing drivers also
  changes output impedance/parasitic interactions, so no single-cause delay
  claim. 2x fine maxstep10ps gives .983907774V (delta-.511uV), residual-error
  delta+.129uV; about6.09mV screen margin only at this TT input. All six codes
  correct. Native/half/direct1 CMI/suppressed warnings preserved; double/fine/
  positive-input control have zero CMI/suppressed warnings; all have zero LTE
  relaxations. No cross-input/PVT/noise/MC/layout/full-ADC qualification.
- Native leaf-edit invariants, source/staged-VA/deck hashes, complete finite
  waves,128/32-MOS reconstruction and ideal gate equations verified. Fixed a
  preparation-only OA-common-VA-filename staging guard before native runs.
  Added two scripts, bounded plan/report, two inspected phase comparison
  figures and small metrics; raw output/cdac8_no_driver/. Python compile,
  focused assertions and diff checks pass. Scoped local commit; no push.

## 2026-10-20 - Independent reference PMOS/NMOS multiplicity factorial

- Nine result.ok native APS runs: P/N (1,1)/(2,1)/(1,2)/(2,2) at -0.5LSB
  and +453.515625mV, plus negative P2N2 maxstep10ps. Same TT/.9V/27C/300ns,
  native Bootstrap/MOM/R50ohm-C4pF references, ideal gates/sign comparator,
  100ps blanking/20ps edges. Only integer P/N multi factors and current saves
  change; unit W/L remains P175/30nm,N150/30nm. No OA/Canvas/VA/PDK or baseline
  changes; separate asynchronous implementation is not replaced or qualified.
- Negative P1N1/P2N1/P1N2/P2N2 BN5 minima -140.452/-17.866/-140.340/-83.908mV.
  Only-P improves this local symptom ~87%, but SAR worst is1.083153V on P-side
  XSP6.MN_LOW and restore1.126315V on XSN6.MN_LOW. Only-N SAR/restore worsens
  to1.141965/1.218550V. P2N2 alone clears current SOA checks at both inputs,
  with negative .983908V and positive .956943V; no full-input/PVT qualification.
- All nine codes127/192 correct; maximum pre-compare residual .405704mV below
  .25LSB1.7578125mV. Native terminal-current saves succeed on12 selected pass
  drains; current includes displacement. Only-P/only-N change actual bottom
  response, not ideal gate timing. No sole-Ron or universal ratio conclusion.
- All32 reference MOS/five port pairs checked in SAR/restore/global windows.
  Negative P1N1/P2N1/P1N2 CMI15 each, suppressed6780/5666/8465; P2N2 and
  positives zero, all LTE0. Native logged v*_max990mV confirms model SOA basis,
  not breakdown/lifetime qualification. Fine P2N2 .983907740V differs-.493uV,
  residual+.112uV. Fresh old-control replay peak deltas below1.46uV.
- Source reversibility, unchanged other native blocks, pinned deck/VA/wave
  hashes, finite complete data,16 ideal gate pairs,12 current channels, code/
  budget/SOA and fine-step assertions pass; Python compile and diff checks.
  Three timing figures visually inspected. Report docs/cdac8_pn_ratio.md;
  curated figures/metrics docs/figures/cdac8_pn_ratio/; raw output/cdac8_pn_ratio/.
  Unrelated historical cdac10/simple-async paths untouched. Scoped local commit,
  no push; no size freeze or baseline promotion.

## 2026-10-20 - Expand all SAR8 token/stored bits and observed approximation

- Offline-only postprocessing of pinned two_cycles_simple_v2_aps: native TT/
  .9V/27C controller with ideal sampling/DAC and variable-delay comparator.
  Wave SHA0064220c...046e unchanged. No OA/Canvas/VA/PDK mutations or new runs;
  raw waves, old plots and unrelated concurrent CDAC10 files preserved.
- New bitwise.py derives16 write decisions from actual token, CODE, DATA,
  stored word and P/N control waves. Eight writes per frame, ordered one-hot
  selections, pre/post-capture bits, comparator sign, final145/85 and DAC
  arithmetic within1e-8V pass. Trials128/192/160/144/152/148/146/145 and128/64/
  96/80/88/84/86/85; final residues+3.46875/+2.34375mV at1LSB7.03125mV.
- Detail two-column and full-two-period figures show4 phase lanes plus all8
  token and8 stored bits, DAC and residual; raw digital excursions retained.
  Reference-disconnected/inconsistent ideal-plant intervals shown as gaps,
  not physical capacitor settling. Both PNGs visually inspected for labels,
  overlaps and clipping. Added doc reading guide and provenance/decision JSON.
- Python compile, focused execution, JSON/SVG parses and scoped diff checks
  pass. Artifacts docs/figures/sar8_simple/bitwise_*.{png,svg} and
  verification/sar8_simple/bitwise_approximation.json. Scoped local commit;
  no push. No additional physical ADC/PVT/SOA qualification claimed.

## 2026-10-20 - Rebuild one clean SAR8 simple Canvas hierarchy

- Claimed exact-origin MCP0.17.75, scoped to the user's existing Circuit.
  Backed up full old12-page Project before replacement; removed its sync/
  handshake/review pages as requested. Current21 cells only, with explicit8
  SAR slices and separate P/N banks; top selected/fit, cloud yc3a7geyrf save
  revision2. No Gallery publication, OA/PDK/VA changes or new simulation.
- New offline canvas.py derives complete connectivity from the unchanged
  simple CMOS hierarchy:163 direct definition instances, all formal terminals,
  real model/child bindings and RC/MOS parameters. Native gate symbols bind
  internal CMOS cells; state/MUX/delay blocks expand. Named shared connections
  are actual bound electrical labels, not drafting text. Added short local
  orthogonal chains without changing electrical membership.
- Native compare: equal across21 cells, zero device/target/connection/binding/
  parameter differences; port order deliberately ignored. Final diagnostics
  zero errors/warnings in every Cell. All21 PNGs exported and visually reviewed;
  top SVG and full pre/post Project backups in output/sar8_simple_canvas/.
- Fixed an atomic label-order rejection and visual collisions/dangling label.
  One top PNG export disconnected during concurrent reads; fresh status
  attached, sequential retry passed. No uncertain mutation replay. Final cloud
  Save/export and structural comparison confirmed. Python compile/focused
  generator, JSON/SVG/hash and diff checks pass; evidence
  verification/sar8_simple/canvas.json, guide docs/sar8_simple_canvas.md.
- Generic raw T28 model names are not installed PDK models; diagram equality
  does not requalify FF SOA, delays or physical ADC integration. Unrelated
  CDAC10/uniform-scale work preserved. Scoped local commit only, no push.

## 2026-10-20 - Uniform CDAC reference-switch scale2x/3x/4x

- 17 completed result.ok native APS transients:five static inputs (-.8V,
  -.5LSB,+.5LSB,+453.515625mV,+.8V) at factors2/3/4, plus positive-full3x/4x
  maxstep10ps. TT/.9V/27C/300ns; same native Bootstrap/MOM, reference50ohm/4pF,
  input50ohm,100ps blanking/20ps ideal gates and VA sign comparator/control.
  All subckts unchanged; only global scale/input values, gate-current saves
  and optional maxstep differ. No OA/Canvas/PDK/installed-VA or baseline writes.
- Codes14/127/128/192/241 all correct and all residuals within .25LSB1.7578125mV.
  Core-SOA passes3/5 at2x,5/5 at3x and4x. 2x true model CMI at both full inputs:
  negative1.026090V (XSP2.MP_HIGH Vbd,203.129050ns), positive1.019582V
  (XSN1.MP_HIGH Vgd,103.130169ns), both restore. Printed5/10, suppressed322/1961;
  every other run CMI/suppressed0 and all17 LTE0. Execution success is not SOA
  or ADC qualification.
- Grouped worst ports2x/3x/4x=1.026090/.982771/.959974V; max residuals
  .439913/.521631/.601917mV. Nominal3x/4x margins about7.2/30mV. More width not
  uniformly better: negative-half3x .951155V versus4x .953468V, different phase.
  Recommend4x for next bounded diagnostic, no adoption/freeze/full-input/PVT.
- All32 reference MOS/five pairs,16 gate equations,32 gate and12 drain current
  vectors checked. Absolute gate charge maxima .560739/.841598/1.125214pC/cycle
  (200..300ns) are ideal-driver load proxies, not physical clock power. Largest
  rail disturbance180.231/191.986/201.455mV and source peak3.605/3.840/4.029mA.
  4x improves SOA but costs gate load/reference disturbance and residual error.
- Fresh2x replay within .002uV; fine3x/4x peaks .982777430/.959968403V,
  delta+6.134/-5.621uV, residual+.000912/-.012373uV, gate charge-6.44/+2.74ppm.
  Source reversibility, subckt immutability, source/deck/VA/wave hashes,
  finite complete data, focused code/error/SOA/current/gate/fine assertions,
  Python compile and diff checks pass. Two timing/summary PNGs visually checked.
- Report docs/cdac8_uniform_scale.md; curated docs/figures/cdac8_uniform_scale/;
  raw output/cdac8_uniform_scale/. Concurrent bitwise/simple-Canvas and historical
  cdac10 work untouched. Scoped local commit, no push. No actual-driver,
  noise/MC/StrongARM/Bootstrap-internal/layout/lifetime qualification claimed.

## 2026-10-20 - SAR8 ideal reference handoff alignment versus frozen R1

- Netlist-only two-case native Spectre21.1 APS experiment, TT/.9V/27C/200ns,
  maxstep10ps/full solver output. Shared ideal commit after native request word
  stable200ps; changed banks simultaneous off,100ps later on,20ps gate edges.
  Unchanged banks stay on. All native subckt bodies and top connections outside
  the16 ideal gate statements identical to R1. All OA/PDK/R1 sources read-only.
- Both result.ok; four functional/error frames,32 compares/writes/updates,
  correct14/14 and127/127 codes, expected mapping and token order. Worst errors
  .807895/.560789mV below1.7578125mV; not an error improvement. Gate threshold
  on/off spreads zero at saved precision, minBBM100ps/no overlap.
- Conversion reference stress1.266776->.951088V (-.8V),1.266744->.951079V
  (-halfLSB); negative-full comparator1.250013->.950686V, TOPPmin
  -.344390->+.038165V. Original conversion spike removed in these two cases.
  Alignment also masks transient all-off raw requests and fixes actualBBM100ps;
  no orthogonal attribution of skew versus blanking/absolute delay attempted.
- Negative-full sampling restore still fails: comparator/TOPN1.136126V at
  103.173270ns versus R1 1.136124V. Pre-existing separate issue, not repaired.
  Whole-run reference max.974975V; no reference CMI. Ten printed comparator
  CMI and suppressed repeats retained. Negative-half0CMI. Seven unchanged
  config warnings each;0LTE. No adoption, new freeze or nominal signoff claim.
- Report docs/sar8_reference_alignment.md; two visually reviewed PNGs;
  exact contexts/decks/logs/PSF/waves in output/sar8_reference_alignment/;
  curated hashes/frames/phase stress in verification/integration/.
  Four focused tests, Python compile, frozen R1 source/hash/native-graph
  checks and diff-check. Scoped local commit only, no push. Unrelated
  cdac10_dualrail untracked work preserved. No remote OA mutation.

## 2026-10-20 - Adopt aligned reference timing in saved SAR8 R2 OA

- Restored t28_io tunnel; correct thu-wei CIW cwd/user and Spectre21.1 healthy.
  Created only SAR_ADC_T28/sar8j_refcommit and sar8j_aligned_refgate symbol/VA,
  sar_adc8_join_r2 schematic/symbol and tb_sar_adc8_join_r2 schematic. Model
  bodies exactly split from tested alignment VA, no semantic edits. Top112/TB26
  instances, declared connectivity/params, zero check markers and remote VA
  byte readback pass. No floating-pin placeholder schematics. New R2 window17
  opened; previous16 windows left open. Existing34 frozen OA fingerprints match
  before/after; R1/native cells unchanged. No transistor/CDF dimension changes.
- Fresh saved-OA export: all32 native subckt bodies match R1, new top112
  electrical statements match prior tested aligned top. Kept raw export intact;
  simulation wrapper changes only variables/analysis/save/include locations.
  Real reference50ohm/4pF retained; shared ideal commit stable200ps,100ps BBM,
  20ps gate edges. Adopt R2 as active development baseline, not new qualified
  freeze or physical timing synchronizer. Config and project-status pointer set.
- Two native APS result.ok/200ns/maxstep10ps/full-rate TT/.9V/27C runs;
  four frames, correct14/127 outputs,8 comparisons/writes/updates each,
  mapping/token/decision/error gates pass. Conversion reference maxima
  .951087854/.951079392V, comparator.950686254/.951472542V, max compare
  errors.807894577/.560789168mV. Numerical metric differences from prior
  netlist-only aligned experiment are zero.100ps BBM, no overlap/threshold skew.
- Negative-full acquisition failure retained: TOPN/comparator1.136126200V at
  103.173270ns;10 printed CMI and suppressed repeats. Half-LSB0CMI; each has7
  configuration warnings;0LTE. No PVT/noise/MC/FFT or transistor-clock claim.
- Five focused tests (including frozen R1 sources), Python compile, graph/RC,
  VA split/byte/readback/export and full-rate functional/stress checks pass.
  Curated verification/integration/join_r2_results.json, docs/sar8_join_r2.md;
  raw evidence output/sar8_join_r2/. Final diff-check and scoped local commit;
  no push. Unrelated untracked cdac10_dualrail work preserved.

## 2026-10-20 - SAR8 earlier reference restoration, netlist-only

- Two fresh native Spectre21.1 APS runs, restore_guard100ps/500ps versus exact
  full-rate fingerprint-checked R2 nfull2ns baseline (reused, not rerun). Same
  -800mV two-frame input, TT/.9V/27C,200ns/maxstep10ps/full solver output,
  reference50ohm/4pF and input50ohm. Only16 per-instance timing parameters added;
  native topology/sizes, source VA bytes and R2 sources/deck/wave unchanged.
- Second-acquisition TOPNmax .867565/.954677/1.136126V and TOPPmin
  +.020513/-.013663/-.148911V (100ps/500ps/2ns). Fresh cases remove .99V
  comparator/reference six-pair violations:0CMI,0LTE/seven config warnings each.
  500ps still crosses 0-0.9V supply rails slightly;100ps gentler at top/comparator,
  but reference peak .971532V is slightly higher than500ps .968864V.
- Actual restore new-on101.260/101.660/103.160ns,100ps BBM/no overlap, zero
  changed-bank enable/disable skew at saved precision. R2 conversion200ps stable
  commit unchanged. No ideal reference-source substitution or transistor resize.
- Held differential sample errors .200475/.200482/.200639mV; first-precompare
  .200486/.200495/.200696mV. All six comparison-evidence frames native14/14,
  eight compares/writes/updates and mapping/decision checks pass; worst conversion
  error .807895mV<1.7578125mV. Only four frames are fresh simulation evidence.
- Four focused tests and Python compile pass. Fixed test UTF-8 source reading,
  not curated fingerprints; verified only16 timing changes and unchanged R2.
  Two PNGs visually checked; report docs/sar8_restore_guard.md, curated evidence
  verification/integration/restore_guard_results.json; raw output/sar8_restore_guard/.
  Final diff-check/review and scoped local commit, no push. No remote OA changes
  or active-version/freeze updates. Unrelated cdac10_dualrail work preserved.
- Single negative-full nominal case only;100ps is a candidate for subsequent
  positive/reversing-input/previous-code checks, not broad PVT/MC/noise/lifetime
  qualification. Entire-device/bootstrap-internal SOA not established by this scan.

## 2026-10-20 - SAR8 100ps restore candidate across input polarity and frame history

- t28_io CIW/Spectre healthy. Three fresh native Spectre21.1 APS200ns/maxstep10ps
  full-rate TT/.9V/27C runs: +.8/+.8,-.8/+.8,+.8/-.8V. Cross-frame PWL input
  ramp100.8..100.9ns, before second SAMPLE101.05ns;40ns acquisition retained.
  Only VDIFF/two input-source statements differ from exact100ps candidate;
  topology/sizes/MOM/3x reference devices/50ohm+4pF reference/50ohm input,
  VA bytes,100ps BBM/20ps edges/200ps conversion commit unchanged.
- All result.ok,0errors/7 unchanged config warnings/0CMI/0LTE. Correct241/241,
  14/241,241/14, six frames/48 compares+writes+updates; native mapping/token/
  decision/read-window gates pass. Full PWL source waveforms verified. Actual
  restore off/on101.16/101.26ns,100ps minBBM/no overlap/zero threshold skew.
  Initial-DC GminDC diagnostics retained for all cases; extra Bad pivoting notice
  in p_to_n (5/5/6 total notices). No transient convergence failure; solver
  settings untouched. Initial-DC/startup reliability not qualified by frame checks.
- Whole-run reference peaks .987137/.966629/.986687V, comparator .950686V each.
  Both top nodes stay0-0.9V in second acquisition; input-edge window adds no
  overlimit. Reference tight cases are N3 MP_HIGH VGD near101.2687/101.2686ns,
  only2.863/3.313mV below.99V. Bounded nominal pass, not robust SOA signoff.
- Held differential error maxima .200474/.200461/.200462mV; first compare
  .200485/.200469/.200470mV. Preoff<.001mV; worst later comparison residual
  .806456/.807895/.807889mV<1.7578125mV. Signed held residual follows input
  polarity; no frame-history error degradation at full40ns acquisition.
- Six PNGs visually reviewed; docs/sar8_restore_cross_input.md, curated
  verification/integration/restore_cross_input_results.json; raw contexts/decks/
  logs/PSF/waves output/sar8_restore_cross_input/. Prior negative-full evidence
  reused only as context. Four focused tests, Python compile, immutable R2/prior
  fingerprints and diff-check/review pass. Scoped local commit; no push.
- No remote OA mutation, active baseline update, transistor resize, noise/MC/
  PVT/layout/lifetime qualification. Candidate remains netlist-only100ps;
  reference-margin concern remains explicit. Unrelated cdac10_dualrail preserved.

## 2026-10-20 - SAR8 reference slew sweep for restoration margin

- Verified t28_io CIW/Spectre21.1. Eight fresh APS200ns/maxstep10ps/full-rate
  TT/.9V/27C cases, edge_s50/100ps across -.8/-.8,+.8/+.8,-.8/+.8,+.8/-.8V.
  Reused four fingerprint-checked20ps baselines. Only16 per-instance edge
  parameters added; deleting them restores corresponding baseline text exactly.
  All topology/sizes/VA/100ps restore+BBM/200ps commit/reference50ohm+4pF/
  input50ohm/stimulus/model/save/tolerance context unchanged. Parameter affects
  restoration AND conversion. No OA or active-baseline mutations.
- All eight result.ok,0errors/0CMI/0LTE/seven existing config warnings. Initial
  GminDC diagnostics and p_to_n Bad pivoting notices retained; no solver changes.
  Sixteen fresh frames/128 comparisons+writes+updates pass native codes/mapping/
  sign/token/read windows. Twenty-ps control adds eight reused evidence frames.
- Pfull N3 VGD .987137->.933042->.912284V; bottom -87.137->-33.042->-12.284mV,
  GP=GN=.9V unchanged. Worst whole-run reference across four inputs
  .987137/.944611/.939290V (20/50/100ps), min margin2.863/45.389/50.710mV.
  Positive worst moves to N0/N4 low-NMOS VDS;100ps overall worst n_to_p P7
  low-NMOS VDS. Comparator .950686V dominates combined slow-ramp scan,
  margin39.314mV. Not all node/input-relative overshoots improve monotonically.
- Max held |diff| about.200475/.200474/.200474mV; first compare about.200486/
  .200485/.200485mV. Worst later compare .807895/.808021/.808251mV versus
  1.757813mV screen. Actual restore on101.260/101.275/101.300ns;50% BBM100ps,
  no50%/1% gate overlap;1% gaps80.4/51/2ps. Not direct transistor-current proof.
- Three PNGs visually checked; docs/sar8_reference_edge_slew.md; curated
  verification/integration/reference_edge_slew_results.json. Raw decks/contexts/
  PSF/logs/waves/snippets output/sar8_reference_edge_slew/. Three focused tests,
  Python compile, baseline/source/wave fingerprints and diff review/check pass.
  Local scoped commit only, no push. All unrelated cdac10_dualrail work untouched.
- Recommend50ps subsequent candidate, not adopted/frozen;100ps lower reference
  stress but little added combined margin and no full gate-endpoint pause. No
  physical driver/PVT/MC/noise/layout/lifetime or all-Bootstrap-internal claim.

## 2026-10-20 - SAR8 R3 saved-OA timing adoption and fresh confirmation

- Restored the existing t28_io tunnel; verified live CIW/library/technology and
  Spectre21.1 without restarting Virtuoso. Created only
  SAR_ADC_T28/sar_adc8_join_r3 schematic+symbol and tb_sar_adc8_join_r3 schematic.
  Top112/TB26 instances, zero final markers.16 ideal gates explicitly100ps
  restore_guard_s/50ps edge_s; unchanged100ps BBM/200ps commit. Shared gate
  base CDF exposes two params with original2ns/20ps defaults; existing CDF
  parameter and both VA byte hashes unchanged. R2 gates read back2ns/20ps.
- Native topology, sizes, all other instance params/connectivity/placement,
  MOM/3x switches/Bootstrap/StrongARM/native async logic and ref50ohm+4pF/
  input50ohm unchanged.36 historical native/R1/R2 surface checks pass before,
  after creation and after simulation. Two independent saved-OA exports audit
  identically to tested50ps candidate after top-name normalization. Raw exports
  retained; wrappers change only stimulus/analysis/includes, not DUT.
- Four FRESH APS TT/.9V/27C200ns/maxstep10ps/full-rate runs, all result.ok and
  finite/complete; -.8/-.8,+.8/+.8,-.8/+.8,+.8/-.8V. Codes14/14,241/241,
  14/241,241/14;8frames/64 native compares+writes+updates. Native sign/token/
  physical mapping/midpoint/read-window gates and sample-error checks pass.
  Compared key errors/stresses against prior50ps candidate: all deltas zero.
- Reference32MOS/StrongARM11MOS six-pair scans peak.944611/.950686V<.99V,
  margins45.389/39.314mV. Held diff error max.200474mV, first compare.200485mV,
  worst all compares.808021mV<1.7578125mV. Pfull N3 VGD.933042V/bottom
  -33.042mV. Restore50% off/on101.175/101.275ns,100ps BBM; no1%/50% overlap,
  1% gate gap51ps, not direct branch-current proof.
- All0errors/0CMI/0LTE,7 unchanged configuration warnings each. GminDC initial
  notices retained, p_to_n also Bad pivoting notice (6total vs5others); solver
  unchanged. Raw OA/readbacks/exports/decks/logs/PSF/waves output/sar8_join_r3/;
  tracked config, results manifest, report and one visually checked overlay.
  Three focused tests, Python compile, diff-check/review pass. R3 opened in
  Virtuoso, existing user windows preserved; current project entry updated.
- Local scoped commit only; no push requested. R1/R2 sources/evidence remain
  immutable. Unrelated untracked cdac10_dualrail work untouched/excluded. This
  adopts a nominal development baseline, not full-code/FFT, PVT, noise,
  mismatch, actual timing-driver, complete Bootstrap SOA or layout/lifetime
  qualification.

## 2026-10-20 - SAR8 R3 performance measurement setup and long-run start

- IN PROGRESS, not measured full performance. Read-only fresh R3 OA export
  matches b742ed4 R3 native subcircuits and explicit100ps/50ps gates; no OA,
  size/topology/model/control/reference-network change. TT/.9V/27C, no physical
  transient noise or mismatch. Unrelated untracked cdac10_dualrail preserved.
- Single/four-thread APS2frame lean-save pilots result.ok, code241 at all
 90/95/98ns windows; settled-top delta<0.2nV vs R3 full-rate result. Same
  conservative/10ps/reltol1e-5/vabstol1e-8/iabstol1e-13. Runtime312/171s,
  so select4threads per job, max4 concurrent. Warned user day-scale runtime.
- Testbench-only passive VA counts8CMP edges and checks90/98ns code stability,
  clock low, rail validity. Output-feedback VA searches real ADC transitions,
  not ideal ADC replacement. Static±.25LSB brackets with6 bisections ->1/128LSB
  interval, all255 edges in4jobs; exclude saturated codes0/255 from width DNL.
  Continuous1024-point k461/-1dBFS sine plus4warmup, direct FFT + toolbox check,
  measured-SNDR ENOB primary. Internal W/U are not separately observed.
- Corrected two strobe-delay input failures and two leading-dot VA compiler
  failures; all raw failure evidence retained. Superseded2 single-thread v2
  measurement jobs stopped by exact verified owned child PIDs only. v3
  observer snapshot variables avoid delayed-strobe off-by-one messages.
  Queued testbench files are content-addressed immutable snapshots.
- v3 static9frame/two-edge and sine5frame measurement smokes result.ok,
  measured counts/stability/rails and bracket/source checks pass. Static has
  one LTE relaxation at666.991ns in native async reference control; disclosed,
  retained, final report flags numerical warnings rather than numerical signoff.
  This is functional measurement verification, not a DNL or SNDR result.
- FULL batch started22:59:35local, one-shot flow session25763, max4workers.
  Output/status/decks/logs/PSF/waves/provenance output/sar8_r3_performance/;
  auto-analysis writes report.md/summary.json/figures there on genuine completion.
  No periodic notification or auto-push. Keep local runner and SSH available.
- Setup-only curated verification/integration/r3_performance_setup.json,
  config, docs, scripts, VA, plan;3 focused math/identity tests and compile/diff
  checks pass. Local checkpoint commit, no push. Final DNL/INL/SNDR/ENOB are
  NOT available; target plan intentionally remains in progress for later review.

## 2026-10-20 - R3 original-history 12 frame anomaly diagnosis

- Completed diagnosis, NOT repair/signoff. No remote OA, topology, sizes, timing,
  native subcircuits, PDK, R3 gate VA or long-performance-campaign source change.
  Existing4long jobs left running. Unrelated untracked cdac10_dualrail preserved.
- Parent static_065_128 exact deck/include hashes and partial native log/PSF
  retained. A shortened1.2us comparison attempts parent defaults but APS still
  reports step1.2ns, unlike parent51.6ns; codes/history diverge and LTE appears.
  Retained as numerical-sensitivity comparison, not successful reproduction.
- Primary keeps parent51.6us stop and exact stimulus/monitor snapshots, adds
  passive VA timer invoking documented Cadence $cds_finish_current_analysis(0)
  at1200ns. All reported solver params match parent except outputstart. APS4,
  maxstep10ps/conservative/effective reltol1e-6, TT/.9V/27C, no noise/mismatch.
  result.ok,0errors/12warnings/7notices,5printedCMI-2754 + suppression, no LTE.
- All12inputs/searches/codes/counts match parent:64,64,64,64,64,65,64,65,1,65,
  65,65. Visible4frames each8compares/writes/updates. Native662464accepted steps,
  compute1148.8s/transfer32.7s/parse77.7s;66signals217838points800-1200ns.
- Confirmed frame8 acquisition midpoint miss: observed bit7/6 physical gates
  stay in previous-state pattern throughout801.05-841.05ns. Old PMOS off50%
  841.075ns/newon841.175ns after sampling ends. Held offset-442.8505mV(-62.983LSB)
  consistent with inferred65->128 late restore(-442.96875mV), not all-bank direct
  measurement. Nextframe midpoint correct. MNINP VGD-.99914984V at841.193394ns
  comes from TOPP-.099607V,Y.899543V while comparator clocklow. First compare
  843.698ns. bit6 residual-435.9496mV vs ideal+7.4707mV; DATA/write847.628557ns
  correctly record0. No D6 rising/falling loss. Lastbit0write870.186903ns; read1
  at898ns. Wrong held charge precedes conversion; R3_circuit_pass=false.
- Suspect shared ideal gate VA bidirectional-cross/instant-level SAMPLE phase
  inference; internal flags not saved, exact software branch remains unproven.
  No event-handler fix, clock/sizing sweep or PVT expansion attempted.
- Added replay/analysis scripts, passive stop VA,2focused tests, Chinese report,
  four inspected timing figures and concise provenance/metrics JSON. Output
  binding corrected before curating independent analyses; all raw data preserved
  under output/r3_anomaly_replay/, primary original_stop/. Shared full-batch
  analysis untouched; any resulting metrics remain fault diagnostics until fix.
- Syntax/targeted tests/diff review/check; scoped local commit only, no push.

## 2026-10-21 - R3 reference timer callback repair B

- Completed bounded12frame native repair validation, not full ADC signoff.
  Native SAR/Bootstrap/comparator/CDAC/reference switches, topology and W/L,
  R3 clock waveforms,100ps restore/BBM and50ps gate edges unchanged. No remote
  OA, shared original VA or running full-characterization source/job changes.
  Unrelated untracked cdac10_dualrail files preserved and excluded.
- Original input bisection follows actual ADC outputs; freeze its original
 12frame input-history branching in a testbench-only VA snapshot for fair A/B.
  Actual native comparator/SAR decisions and logs remain real, not forced codes.
  Retain original51600ns declaredstop and passive1200nsfinish, APS4/conservative/
 10ps; all native reported solver parameters match the original replay.
- Passive original A reproduces all12codes including frame8code1,217838point
  time grid and49common saved waveforms exactly, maximum difference0. Native
  result.ok,0errors/12warnings/7notices; CMI retained. Direct state evidence:
  sampling enters801.050000250055ns, restore books801.150000250056ns; valid
  callback801.150000090759ns is0.159297fs early. Redundant >=deadline-1e-18
  rejects it for all16banks; restored stays0, no retry until sampling ends.
  This supersedes the earlier unverified SAMPLE-cross level hypothesis.
- Phase-only candidate b stillfails: frame8code2, held-442.320735mV, CMI.
  An intermediate event-owned b2 unit exposes omitted sample-fall interlock
  release;48/96 conversion-request checks fail, no full ADC b2 run. All failed
  variants/raws preserved; final b3 restores the interlock and uses explicit
  SAMPLE directions, COMMIT notifications and event-owned restore/turnon with
  pending flags, never re-rejecting a timer by absolute floating-point time.
  Read installed Cadence21.1 timer docs via SSH, no blocking CIW help process.
- Four native small units result.ok. A/final b3 pass96acquisition and96conversion
  checks, no command overlap,96rise/96fall; their saved waveforms are identical.
  Final B=b3 native12frames result.ok,0errors/7warnings/6notices, no CMI/LTE.
  Codes64,64,64,64,64,65,64,65,65,65,65,65; all12frames8compares and observed
 4frames8write/8update. Complete384phase/192restore events;32early callbacks
  correctly handled. No gross outlier; all16bank midpoint gates and bottoms
  correct before hold. Real source history and native DUT statements unchanged.
- Frame8 held error-442.850497mV ->+.101355mV(.014415LSB), handoff MNINP maximum
  |VGD|.999150V ->.671722V,898ns output1->65. Frames8..11 held+.101302..+.101355mV,
  all below.25LSB=1.7578125mV. Saved comparator input-pair VGS/VGD/VDS max.886745V
  below.99V screen; not whole-chip lifetime qualification. Remaining7warnings
  are original AHDL/global-terminal/PDKscalefactor messages, explicitly retained.
- Added isolated model snapshots, preparation/run/analysis,3focused tests,
  provenance/metrics verification/integration/r3_refgate_events_results.json,
  docs/r3_refgate_events.md and3inspected timing figures with expected baselines.
  Raw logs/PSF/decks/pickles output/r3_refgate_events/ ignored. B trace85signals/
 218631points800-1200ns;0-800ns fully solved. Final compute1154s,transfer27.5s,
  parse95.2s. Earlier original full static/sine results remain fault diagnostics,
  cannot be relabelled repaired performance; no automatic long-batch restart.
- Syntax,3focused identity/history/event parsing contracts, curated source/figure
  hash checks, diff-check and scoped review. Local commit only, no push. B remains
  a separate netlist/VA candidate, not silently adopted into frozen R3 OA.

### 2026-10-21 Adopt verified B reference events into current R3 OA

- User authorized B synchronization, unchanged native topology/sizes/precision,
  and discussion of shorter fault-finding tests rather than full campaigns.
  Plan: plan/2026-10-21-r3-b-oa-adoption/plan.md. Unrelated cdac10_dualrail work
  preserved; no process cancellation, Virtuoso restart, forced unlock or push.
- Recovered stale local post-reboot tunnel via normal warm; healthy t28_io,
  matching thu-wei/llm_IO CIW and native Spectre21.1. Read-only cached dependency
  locks recorded and retained. Writable top schematic unlocked and GUI-closed.
- Added SAR_ADC_T28/sar8j_aligned_refgate_b symbol/veriloga/CDF; exact verified
  b3 body, module name only changed. Copied symbol pins/geometry and exposed
  CDF equal old gate. Old shared gate and R1/R2 historical meanings preserved.
- Changed exactly16 ideal gate master bindings in sar_adc8_join_r3/schematic.
  API readback: all other fields/parameters/connectivity/positions equal; TB
  unchanged,36 native/historical dependency surfaces unchanged, zero markers.
  Fresh OA netlists: every native subcircuit text equal, top named electrical
  statements equal after only gate-name normalization. Header replacement
  reorders top gate statements; no full-ADC time-grid equivalence claimed.
- Native import unit uses OA-downloaded VA, same APS4/conservative/10ps settings.
  result.ok,0errors/1oldAHDLwarning/6notices.20saved waveforms/121443timepoints
  exactly equal previous verified B unit, including96acquisition+96conversion
  checks. Compute11.63s,total27.50s. No new whole-ADC replay or full campaign.
- Added source/import automation, concise verification receipt and adoption/
  short-test discussion docs; corrected current project-status entry. Raw
  exports/logs/unit waveforms under ignored output/r3_b_oa/. No PDK/OA binaries
  committed. Source/receipt check,syntax,diff-check and scoped review performed.
  Local commit policy: fix: adopt verified reference gate B in Virtuoso; no push.

### 2026-10-21 Launch B one-period sine transient and monitor

- User approved500kHz sine,10MS/s,4startup+20observed frames,24total/2.4us;
  requested progress attention. Plan2026-10-21-b-sine-one-period. No FFT,
  full-code,PVT,mismatch,noise,topology/WL/precision edits or OA mutation.
- Read current B top/TB and36native/historical surfaces, matched adoption;
  fresh OA netlist and remote B/commit VA hashes verified. Independent config,
  immutable input snapshots/deck,44continuous saved signals and passive probe.
  Native SAR/StrongARM/Bootstrap/MOM/3xreference switches and rail impedances
  unchanged. Preserve prior51.6us declared stop-dependent defaults; existing
  observer ends normally at2.4us. All24frames including startup are solved/saved.
- Hidden local runner started08:58:59local, worker34600. Native solver281826,
  exact scratch00a444e1; bind actual solver by unique deck path, not launcher
  PID receipt. At09:02:24,2/24frames complete,8compares and stable final readouts,
  no CMI/LTE at that snapshot. First startup hold probe-1.71836mV retained,
  not extrapolated to all measured inputs or performance pass.
- Added time-domain analysis/plot pipeline (not yet executed on final data),
  code-vs-sampled-input and real conversion timing, parameter/stress/hold checks.
  Progress artifacts output/b_sine_period/. Current-status entry updated.
- Created and read back heartbeat `b`, current thread, every5minutes; meaningful
  milestones/errors/completion only, pause when finished, no duplicate runs or
  automatic circuit changes. Full result, figures and final local result commit
  pending; this commit records validated setup and launch only. No push.
- Subsequent first3startup frames24/44/72 all8compares/valid. Raw held probes
  -1.71836,-2.92038,-3.83207mV; latter two above original.25LSB budget. Early
  finding disclosed; do not hide with aperture alignment or infer20-frame pass.
  Native precision readback matches prior B except intentional outputstart0
  (vs800ns) to retain startup. Actual sample-aperture timing remains to inspect.

### 2026-10-21 Complete B one-period sine transient

- Completed the sole authorized500kHz/.8Vpeak/.45VCM/10MS/s native case,
  4startup+20observedframes,2.4us. Same adopted B OA export, native topology,
  W/L,50ohm inputs/50ohm+4pF references and APS4/conservative/10ps precision.
  No OA writes, duplicate launch, new campaign, PVT/noise/mismatch or push.
- result.ok,0errors/7warnings/7notices. All24frames have8compare/write/update,
  stable90/98ns output;24passive probes match saved source/held/error within
  .1uV.20observedpoints show maxcodeerror1,no >1code outlier. Held error
  maximum4.464648904mV(.635LSB);14/20exceed1.7578125mVbudget, FAIL.
  Comparator inputpair terminalmax.898006456V<.99Vscreen,noCMI/LTErelaxation;
  retain original7warninglines, not whole-chip signoff or ENOB qualification.
- Existing continuous waveform locates large error before turnoff. Worst
  frame4 at440.05ns,SAMPLEhigh,mainG-input~.893V: source100.391258mV,
  pin100.262587mV,TOP95.673304mV;TOP-source-4.717954mV,TOP-pin-4.589283mV.
  Source50ohm accounts-.128672mV only. Held441.65ns differs-4.464649mV from
  nominal441.05ns source. Slope-equivalentlag1.780792ns is diagnostic only;
  no source-phase correction, budget relaxation or automatic circuit changes.
- Native solver26m43s;bridge execution1605.85s,download76.39s,parse211.58s,
  bridge total1899.17s.44signals/1326793points,2.01GBrawASCII and waveform
  hashes preserved under ignored output/b_sine_period/. Solver readback same
  as prior B except intentional startup-saving outputstart0 instead of800ns.
- Refined only planned analysis/plots: step-aligned actual/ideal readouts,
  ±.25LSBheld budget, phase legend, tracking diagnostics, log-wave crosscheck,
  reproducible curated JSON/figure copy. Both final timing figures visually
  checked with real baselines and no hidden delay fitting. Report and small
  verification receipt added; current-status entry updated. Scoped source,
  syntax,hash/count/precision checks and diff review; local result commit only.
  Read back monitor id b; pause after final delivery, no unrelated automation.

### 2026-10-21 Decompose existing B sine error without simulation

- User authorized existing-waveform-only delay/gain/remainder and turnoff
  analysis. Plan2026-10-21-b-sine-error-decomposition; parent61dcdb4. No
  simulator/remote call, OA/model/clock/WL/precision edits, new experiments,
  heartbeat change or push. Unrelated cdac10_dualrail work preserved.
- New independent NumPy offline script verifies original B provenance, SHA,
  result.ok,44signals/1326793points and20observedframes. Fits DC+sin/cos,
  obtains heldgain.99974184572(-.02581543%),equivalentlag1.781261225ns.
  Rawpeak4.464649mV remains failed originalbudget. AfterDC/fundamental fit,
  held remainderpeak8.259512uV/RMS5.604440uV,H3projection7.892781uV.
- Uniform preedge localcubic extrapolation5ns..-.15ns versusheld+.6ns gives
  turnoff-related incrementpeak327.692875uV; its DC/fundamental-removed
  remainderpeak6.009549uV/RMS4.421882uV. Pretracking remainderpeak2.789366uV,
  equivalentlag1.890314730ns,gain-15.872503ppm;109.05ps lagreduction is not
  unique aperture. Commonmode increment-.447..-.464mV; savedMSBgatesconstant,
  bottomnodes~.10mVperturbation. Not a pure channelcharge-injection extraction.
- 3/5/8ns quadratic/cubic extrapolation sensitivitymax.122205uV; cubic<.001uV,
  5/20psuniformresampling robust. Quietprecompare+.6..2ns holds to.014624uV,
  near numericprecision, not longtermleakage. Exact decomposition reconstruction,
  synthetic delay/gain/DC/H2/H3 recovery and source-before/after SHA checks pass.
- Added independent report/metrics/two figures and narrow projectstatus entry.
  Keep fixed-frequency/amplitude/history/alias/numerical ambiguity with claims;
  signal-linear injection can remain in fitted phase/gain. No ADC SNDR/ENOB
  claim or corrected-budget pass. Focused syntax/result/figure checks and scoped
  local commit only; original B run data/report/acceptance conclusions intact.

### 2026-10-21 Launch main-W-only B short sine comparison

- User authorized1x/2x/3x mainW only, unchanged topology,L,CDAC,timing and
  precision; no fullcode. Plan2026-10-21-b-sine-main-w,parent00f25a6.
  Existing1x completed24frame native sine/decomposition reused, no duplicate
  run; source/deck/include hashes validated. Unrelated cdac10_dualrail preserved.
- Healthy0.8.0/t28_io,thu-wei/llm_IO/userchenzc_intern25,Spectre21.1. Current
  B top/TB and36dependency surfaces match snapshots. Read-only, no OA writes.
  Prior PDK-generated320nm/500nm/1um/2um geometry validates AD/AS=W*155nm,
  PD/PS=2*(W+155nm),all other model/spacing/stress parameters constant.
  Independent2/3um decks change only Mmain W and4width-derived quantities;
  both P/N physical main instances share that subcircuit. No stale parasitics.
- Same500kHz/.8Vpeak/.45VCM/10MS/s,4warmup+20observed,24frames/2.4us;
  declared51.6us stop andpassivefinish preserved,44continuous saves, sameVA,
  MOS/CDAC/StrongARM/nativeSAR and50ohm input/50ohm+4pFreference networks.
  APS4/conservative/10ps/reltol/vabstol/iabstol/gear2only unchanged.
- Hidden coordinator10:22:11local,actualPID44712; two native jobs,at most2
  concurrent compute, serial localPSFparse to avoid two~14GBparser peaks.
  Inspected pinned0.8.0 remote-run/result-assembly helpers, native command
  same as public adapter, no bridge package edit. W2a400dc73/PID137806,
  W336fde9f4/PID137807. At10:26both2/24,8compares/stable,noCMI/LTEyet.
- Added config/prepare/check/run/status and comparable analysis;1x baseline
  extraction exactly reproduces committed delay/gain/remainder. Python compile,
  bounded geometry/input/source/precision contracts pass. Full results/plots
  pending, no qualified candidate or automatic OA replacement claimed.
  Scoped launch commit only, no push or new automation; old heartbeat untouched.

### 2026-10-21 Establish reader-facing Obsidian notes

- User requested a separate `Obsidian_docs/`, not bulk migration of technical
  reports. Plan2026-10-21-obsidian-curated-notes, starting HEAD4958ad1. Preserved
  existing docs, untracked cdac10_dualrail work and concurrent main-W testing;
  later untracked docs/b_sine_main_w.md is also outside ownership.
- Added 首页, 设计流程复盘 and 当前设计 Markdown notes. Separate curated narrative
  from engineering evidence; retain failures/ideal boundaries and explicitly
  date the R3+B snapshot. Main-W2/3 are recorded as launched, not qualified or
  adopted. Source paths are repository-relative, not misleading vault links.
- Added one README entry and scoped ignores for this vault's .obsidian/ and
  .trash/ only. No report moves/copies, image duplication, plugins, personal
  vault/settings/registry, OA, model, simulator or automation changes.
- Strict UTF-8/YAML checks, all wiki links, source existence and ignore behavior
  pass. Initial Windows stdin encoding mismatch resolved by python -X utf8,
  no content change. Diff-check and bounded staged review performed; local
  documentation commit only, no push. Open the new folder manually as a vault.

### 2026-10-21 Fill five eight-bit Obsidian notes

- User established Head/Spec/Result/Revision/Wrap-up & Experience and requested
  clear, concise eight-bit-only content. Plan2026-10-21-obsidian-eight-bit,
  starting HEADe9e92ad. Preserved filenames and the user's original-note moves;
  old broad history stays recoverable in Git and unchanged engineering reports.
- Filled overall architecture/current ideal boundaries, eight-bit budget and
  verification flow, condition-bound results, seven iteration decisions and
  six linked lessons. Corrected README vault entry. No new figures or hierarchy.
- Kept behavior/macro/native joint performance separate. R3-before-B and B
  history/sine data are explicitly distinct. Raw4.464649mV sampling failure is
  retained; fitted residual is not a substituted pass. Main-W2/3 remain pending
  reviewed evidence, not adopted sizes or newly monitored jobs.
- Inspected saved B export to resolve an evidence-description inconsistency:
  joint MOM uses18 multi groups, not512 independent declarations. Independent
  units belong to the separate capacitor mismatch fixture. Notes use the export
  evidence; source reports are outside scope and unchanged.
- Full note readback, UTF-8/YAML,31wiki links/heading anchors,19source paths,
  budget arithmetic, eight-bit scope and diff-check pass. Scoped staged review
  and local documentation commit; no push, OA, simulator, PDK, GUI or settings
  changes. Concurrent main-W plan/run/analyzer and cdac10_dualrail stay excluded.

### 2026-10-21 Complete main-W-only B short sine comparison

- Completed planned1/2/3ummain sweep, L150nm,nf1; only W-derived AD/AS/PD/PS
  change.1x reused;2x/3x nativeAPS4/conservative/10ps andsame reported solver
  parameters,500kHz/.8V/.45VCM/10MS/s,4+20frames. No OA adoption or newfullcode.
- Both newruns zeroerrors,result.ok true,24frames each with8compare/write/
  update andstablefinalcode. Localparse sequential315.60/240.98s. Fullraw/log
  complete; optionalW2.ic/W3.fc/W3.ic SFTP andtwo post-download cleanup sessions
  stalled. Verified exactparents/paths andstopped onlythose localchildsessions,
  no Spectre/coordinator kill or rerun. Optionalfiles incomplete/scratchcleanup
  unconfirmed, originalraw retained. Statuslocal-log fallback fixescleanup race.
- Heldlag1.781261/.881995/.574213ns,gain-.025815/-.047062/-.068613%; rawpeak
  4.464649/2.241513/1.518989mV,14/10/0observedpoints outsideoriginalbudget.
  3xbest raw in thiscase, not adopted. Heldnonfundpeak8.260/13.835/21.430uV;
  turnofftotalpeak.327693/.460335/.624287mV andnonfund6.010/13.088/21.048uV.
  Trackingnonfund2.789/.907/.487uV improves, indicatingturnoff-related tradeoff.
- W2oneSPECTRE-16780LTErelaxation at1759.41ns,nativeSARXD_ON1.AB,17.76ns
  afterframe17heldread; laterinfluence not ruled out. NoCMI-2754, W1/W3noLTE.
  Configunchanged != no localnumericalrelaxation.8/7nativewarnings retained.
- Addedreport,curatedmetrics/3visuallyreviewedfigures andnarrowprojectstatus.
  Reproduced1x,hash/source/geometry,sourcehistory/sampletimes,24probe/readback,
  mathreconstruction/orthogonality/synthetic andwindowsensitivity<=.123uV pass.
  Saveddeck confirms18MOMmultigroups/512equivalentunits, not512independent
  declarations; correctedthisreportdescriptiononly. NoPVT/mismatch/noise/full
  ADC qualification or pureinjectionclaim. Scopedlocalcommit,no push or new
  automation; unrelatedObsidian/cdac10_dualrail work preserved.

### 2026-10-21 Polish illustrated Obsidian wrap-up report

- Preserved the user's five sections and six images in Report/Wrap-up &
  Experience.md. Condensed prose, paired reference/topology figures and kept
  dense SAR timing plots vertically stacked at full width. Explicitly retained
  the plots' ideal analog testbench boundary; no new circuit results.
- Plan2026-10-21-obsidian-report-layout, starting HEAD640bd51. Included only
  this report's move, its six unchanged PNG dependencies and plan/log. Other
  Rvision moves/Spec edits, Report20261021 stub and cdac10_dualrail work remain
  untouched and unstaged. No OA, simulator, image, theme or plugin changes.
- Strict UTF-8/YAML, six embed targets, five sections, protected facts and six
  original SHA256 hashes pass. Unslop preservation5/5 passes; English-only
  scan/diff advisories were reviewed against Chinese prose and layout markup.
  Inspected the full Obsidian reading-mode rendering for alignment, overflow,
  timing-figure size and section spacing. Scoped diff-check/review before local
  documentation commit; no push requested this turn.

### 2026-10-21 Explain illustrated wrap-up iterations

- User requested repository-backed explanations for report sections2–5, not
  captions alone. Plan2026-10-21-wrapup-evidence, starting HEAD5fcf073.
- Explained historical Bootstrap sizing/stress/current-path/isolation work,
  native Canvas replacement and separate eight-bit load/dynamic width results.
  Explained SAR handshake protections, timing/recovery costs, simplification
  and removed guarantees. Added dated file-inventory discrepancy, R3+B entry,
  twelve-frame timer fix and inactive capacitor mismatch lesson.
- Retained section1, all six image embeds and five-section layout. Added14
  folded repository evidence links; no new simulation claims, image changes,
  GUI actions, OA operations or other note edits. Historical/ideal and native
  boundaries, unadopted3um candidate and remaining FF stress are explicit.
- UTF-8/YAML, preserved section1/embeds, all14 source paths, preservation6/6
  and diff-check pass. English scanner advisories reviewed manually against
  Chinese prose and requested expansion. Scoped local documentation commit;
  no push. Unrelated user note moves/drafts and cdac10_dualrail remain excluded.

### 2026-10-21 Add waveforms and concise eight-bit Result

- User requested figures/data and simplification. Plan2026-10-21-result-figures,
  starting HEAD4bee1fb. Edited only relocated Rvision/Result.md, its old-path
  deletion, new assets/result8 dependencies and plan/log; other notes unchanged.
- Retained six heading anchors and core data, shortened repeated prose, added
  nine original waveform/measurement PNGs with captions and two folded
  diagnostics. Manifests preserve sources/reports/hashes; two formerly ignored
  migration PNGs are now durable vault assets. All copies byte-identical.
- Replaced pending width status with completed1/2/3um comparison; retained1um
  OA adoption, raw budget failure, fitted-residual boundary,2um LTE caveat and
  incomplete whole-ADC qualification. No reruns, OA, GUI, theme or image edits.
- UTF-8/YAML, six anchors, embed/wiki/source targets, nine SHA256 pairs and
  strict preservation107/107 pass. All figures visually reviewed. English
  scanner/large-diff advisories manually checked against Chinese prose and
  requested restructure. Full scoped review/diff-check before local commit;
  no push. Other user relocations/drafts and cdac10_dualrail remain unstaged.

### 2026-10-21 Launch B high-frequency main width comparison

- User authorized4.5MHz,-1dBFS,mainW1/2/3um only,unchanged topology,L,CDAC,
  external timing andprecision; no fullcode orautomaticOAadoption. Independent
  plan2026-10-21-b-hf-main-w preserves all500kHzsources/results andusernote/
  cdac10_dualrail dirtywork. No newautomation orpush.
- Initial bridge tunnel down;one scoped0.8.0/t28_iostart restoreddaemon/CIW/
  Spectre21.1. Read-onlyBtop/TB and36dependencies matchbaseline,libtsmcN28 and
  CIWthu-wei/llm_IO verified. NoOAwrite. Exactnewsourcepeak.9*10**(-1/20),
  perleg.401062922V,phases-72/108 unchanged;20samples cover9cycles/2us.
- Three newnative24frame/2.4usjobs,APS4/conservative/10ps andsame44continuous
  saves/declared51.6usfinishdefaults/5VAobservers. Only sources andMmainW-derived
  AD/AS/PD/PS change. Geometry,inputs/include/sourceSHA,frequency-aware synthetic
  lag/gain/DC/H2/H3 andprior500kHzmath equivalence pass. Phase-only diagnostic
  retainsgain; rawbudget remains unchanged. Cubicpreedge extrapolation includes
  highfrequencywindow/degree sensitivity,not a purecharge-injection claim.
- Atmost2compute/download workers,1localparser; thirdcompute may overlapparse.
  Scopedtransport bounds avoid prioroptionalSFTP indefinitewait; sameinspected
  bridge nativeCLI/result.ok implementation, no packageedit or solver/savetrade.
  Fake-runner transfer-isolation/required-data-retention check passes.
- Launched13:20:04local,launcher31348/coordinator13112. W1b4ed7f44/Spectre322222,
  W27ca28707/Spectre322218;W3queued. At13:20:34bothnativeactive0/24. Results/
  recommendation pending. Addedsource/config/status andlaunchplan; scopedlocal
  commit only. Globaldiffcheck saw unrelatedusernote trailingwhitespace, left
  untouched; owned-path check clean.

### 2026-10-21 Present final result figures and bench context

- User requested top-plate CM/DM, separate minimal timing rows, final-design
  figures without iteration clutter, and environment/module status on every
  figure. Plan2026-10-21-result-final-figures, starting HEAD53722d8.
- Replotted seven saved-data results to PNG/SVG with provenance: electrical
  macro, selected1um sampling, selected MOM local-MC, adopted initial StrongARM,
  simple_v2 SAR, current R3+B conversion and1um continuous input. CM=(P+N)/2,
  DM=P-N; original analog clocks retained. Normal CM scale avoids magnifying
  numerical noise. All headers state conditions, native/ideal/macro/disconnected
  modules and random-effects status. No reference-error panel or old versions.
- Result keeps six anchors and user comparator-table formatting; removed prior
  nine embeds and iteration tables/candidate curves, retaining source reports
  and archived assets. Concise note now about3900 characters versus5458. Raw
  4.464649mV/14-of-20 failure remains; code correctness is a separate result.
- Plot execution/compile, CM/DM algebra,8/8/8 edges,192/145/142 codes, displayed
  191.3676ps cycle, MOM statistics, input/image/generator hashes and Markdown/
  YAML/embeds pass. Seven final images visually reviewed after refinements.
  Selected-only Bootstrap error differs from paired original by3.62nV and
  rounds to the same-.1264mV; this source distinction is recorded.
- Only Result,new reporting script/assets and plan/log staged for local commit.
  No simulation, OA, GUI, image editing or push; dirty Wrap-up, pending HF source/
  report, user note moves and cdac10_dualrail remain excluded.
- SVG serialization whitespace normalized after diff-check, with identical
  PNG hashes and valid XML. Staged check passes; global unstaged check reports
  only pre-existing user Wrap-up line13 trailing space, preserved as-is.

### 2026-10-21 Shorten Bootstrap wrap-up to core results

- Followed the user's manual reduction: paired topology figures, one old and
  one new statement, one500kHz width-result table and adoption/tradeoff line.
  Corrected0.126mV attribution to eight-bit flat/1um rather than split/0.5um.
- Plan2026-10-21-wrapup-bootstrap-concise, starting HEAD653e509. Owned only
  section2 of the report and plan/log. Text outside section2 and both image
  embeds match the user's starting version; source values checked.
- Staged a section-only patch; other user report changes, note moves/drafts,
  HF-width work and cdac10_dualrail remain unstaged. Scoped diff-check passes;
  existing section1 whitespace is preserved. Local commit, no push, GUI,
  simulation, image or OA change.

### 2026-10-21 Complete B 4.5MHz main width comparison

- Completed approved1/2/3ummain sweep at4.5MHz,-1dBFS,.8021258443Vdiffpeak,
  .45VCM/10MS/s,4+20frames/9observedcycles,TT/.9V/27C. Onlysourcefreq/amplitude
  andW-derivedAD/AS/PD/PS differ fromprotectedBtemplate. NoOA/spec/push changes.
- Allthree nativezeroerrors/7existingwarningseach,result.ok true,24frames
  each8compare/write/update andstable90/98codes,noCMI-2754/LTErelaxation.
  Reportedsolverparams identical toB.44continuoussignals,~1.327Mpointseach;
  sameAPS4/conservative/10ps/gear2only. Threecomputejobs,atmost2parallel,
  serializedparse325.57/328.06/294.34s. Sixmissingoptional.ic/.fc skipped,
  fullraw/log saved,all3ownscratchcleanup rc0; no manualprocesskill/rerun.
- Heldlag1.783592/.882235/.574250ns,gain-.153617/-.082646/-.085977%; residual
  peak158.561/54.505/40.619uV,RMS110.741/38.200/29.250uV. Phase-onlyamplitude
  peak.195338/.100217/.102888LSB retainsgain. Originalraw40.091849/19.834526/
  12.889723mV,all20/20failold.25LSBgate. Keep thisfailure distinct fromdiagnosis.
- Recommend2x engineeringcandidate: roughlyhalfphase-alignedamplitudeerrorvs1x;
  3xgain worse andonly.001975LSBfurtherresidualpeak improvement.1xnominal
  residual still has8bitmargin; not proved incapable, not auniquerequiredsize.
  No2xOAadoption ornewacceptancecriterion. NoENOB/SNDR/DNL/INL/PVT/powerclaim.
- Highfreqtrackingresidual156.309/42.335/20.205uV versus turnoff17.095/18.399/
  22.942uV explainschangedattribution from500kHz. Cubicpreedgewindow<1.34uV,
  quadratic~90uV sensitivityretained,primaryheldfit unaffected. Nativecodeerror
  vsnominal6/3/2,vsheld1/1/1; do not labelallnominalcodeerror logicfailure.
- Frequency-aware synthetic/500kHz equivalence,inputs/SHA/geometry,sourceanalytic
  samples/acrosswidthhistories,24probes/events,fitorthogonality/reconstruction
  and4visuallyreviewedfigures pass. Heldmarkers useactual+.6nsread; actualand
  idealcode readat+98ns. Curatedmetrics/report/figures/status andlocalcommit
  only, olddata andotherusernote/plan edits preserved, no newautomation.

### 2026-10-21 Condense SAR logic and workflow wrap-up

- User requested sections3–5 in the concise Bootstrap style. Retained old/new
  SAR statements, both timing figures,26/21cell and1742/1476MOS comparison,
  thirteen-case functional result and FF/partial-code limits.
- Reduced project structure to the dated15/42inventory discrepancy and local/
  remote/current-entry table. Timer fix retains12-frame history and frame9
  code1→65/error-442.850→+.101mV; kept inactive mismatch and short-run lesson.
- Plan2026-10-21-wrapup-sections345, starting HEAD52feb04. Sections1–2, source
  list and all six embed strings match starting text; owned section text1295
  to1025characters after line-ending normalization. UTF-8/YAML, headings,
  image targets, source data and scoped diff-check pass.
- Only sections3–5 and this log append are staged with the plan. Existing user
  report edits, concurrent HF log/status/results and other work remain outside
  the commit. No GUI, simulation, OA, image changes or push.

### 2026-10-21 Redraw focused one-period SAR comparison

- User requested smaller matched old/new timing figures with only necessary
  real transfer nodes. Added offline sar_logic_compare.py and two PNG/SVGs
  plus provenance. Each plots one100ns SAMPLE-rise-to-rise period atTT/.9V/
  27C,+.123V; shared xscale/fonts/voltage normalization/decimal bus notation.
- Old seven lanes: SAMPLE,CMP_CLK,CAPTURE,ADVANCE,W[7:0],COMMIT,D[7:0].
  New five: SAMPLE,CMP_CLK,PHI_W,PHI_U,D[7:0]. All from saved native voltage
  nodes; no token/trial/status/analog observer lanes or invented new output
  bank. Replaced only two report embeds and their brief scope/key caption.
- Both original results ok; LF-normalized deck hashes match runner records
  (local downloads areCRLF), waveform/provenance hashes retained.8compare/
  write/update per period, old1COMMIT after last update, physical register
  writes128/128/128/144/144/144/144/145 and final145 verified. Input assertion
  covers acquisition: source begins next-frame transition just before next
  SAMPLE midpoint, so whole-period constant-input assertion was inappropriate.
- Old/new maxsteps200/50ps disclosed in provenance; this is transfer-flow
  illustration, no new speed/SOA qualification. Actual min/max display samples
  and transient bus intervals retained, no ideal square-wave reconstruction.
  FinalPNG dimensions1680x772/1680x600, report width640; images visually checked.
- Compile, finite/monotonic traces, text bounds, PNG/SVG/hashes, UTF-8/YAML/
  embeds and exact unowned-report text pass. Scoped diff-check/review and local
  commit only. No simulation, OA, image editing, GUI or push; old figures and
  user note edits elsewhere preserved.

### 2026-10-21 Separate sampling acceptance and retain nominal1x

- User authorized revised acceptance and a saved-data1/2/3x review, explicitly
  no new simulation. Added config/sampling_acceptance.yaml and a standalone
  analysis script/result, report and narrow status/budget/history notice.
  design_spec receives only a policy comment; parsed values are unchanged.
- Fixed equivalent delay is characterized separately from jitter, gain/DC and
  nonfundamental remainder. Provisional gain endpoint allowance is .25LSB;
  .15LSB RMS remains a shared system reserve, not an exclusive sampling budget.
  Joint .25LSB peak screen retains gain/DC and uses one500kHz-derived delay per
  width unchanged at both measured frequencies. No per-frame time warping or
  physical gain/clock calibration. CDAC/comparator and full-ADC gates unchanged.
- At4.5MHz1/2/3x gain endpoint errors .196630/.105786/.110051LSB, common-delay
  joint peaks .194082/.100311/.102902LSB and nonfundamental RMS .015750/
  .005433/.004160LSB. At500kHz joint peaks .030324/.055089/.080485LSB.
  Retain1x nominal baseline;2x improves margin but is not required by current
  nominal evidence. Supersedes prior2x recommendation, preserves its raw data.
- Source SHA and original metrics unchanged, all6 saved records24frames/8/8/8
  and stablecodes. Oldraw exceedances14/10/0 and20/20/20, lowfrequency2x LTE
  warning retained. Synthetic delay/gain/DC/H2/H3 recovery, failing gain/DC
  cases, exact reconstruction, repeatable JSON, compile, UTF8/YAML/links and
  unchanged system values pass. No PVT/noise/mismatch/fullcode/FFT/power claim.
- Followed write-page clarity guidance for local engineering prose; did not
  create a cloud Page. Unrelated note/code changes and the independently
  committed SAR timing comparison remain outside this target. Scoped local
  commit only, no push, automation or OA change.

### 2026-10-21 Add classical sine/code staircase to Result

- User wanted a more intuitive relationship between original sine and codes.
  Plan2026-10-21-result-staircase, starting HEAD1fe7174. Added standalone saved-
  data plotting script, PNG/SVG/provenance and Result section6 embed; old raw
  error plot is folded, prior data/figures/generators unchanged.
- Reconstructed bin-center voltage from actual final codes with dual voltage/
  unsigned-code axes. Upper panel uses sampling-time alignment, lower panel
  actual98ns read timing with56.95ns delay. Both explicitly display ZOH read
  samples, not the internal SAR register or a new output bank/DAC. Frame3
  supplies the pre-first-update interval; all20 observed codes remain visible.
- Compile/run,24 actual D-pin code reads, inverse mapping,100ns spacing,
  56.95ns delays, source/output SHA256, SVG/XML, UTF8/YAML/links and scoped
  diff-check pass; PNG visually inspected. Original4.464649mV/14-of-20 raw
  measurements preserved. No simulation/OA/GUI operation, performance update,
  push or unrelated note/code edits. Scoped local documentation commit only.

### 2026-10-21 B1x short integration steps0/1

- User authorized only read-only baseline audit and bounded short checks,
  preserving all original12 anomaly frames fromt0; no long campaign, PVT,
  mismatch or circuit/precision changes. Plan2026-10-21-b-short-acceptance;
  prepared sources committed1fe7174. Unrelated notes/cdac10 work preserved.
- Spectre/Virtuoso skills select native APS and supported read-only OA APIs;
  EVAS cannot replace this PDK hierarchy. One scoped tunnel start restored
  healthy0.8.0/t28_io. ExactCIW/tech/top/TB/36dependencies/currentBVA verified;
  native blocks, W1um/L150nm, ideal clocks, CDAC/3xrefs/50ohm/4pF and all
  reported solver parameters match B. No OA write or schematic/netlist drift.
- Three cases12/16/16frames, at most2APS4 and1localparser, exactscratch/PID/log
  receipts; fullnative0..1200/1600/1600ns, all result.ok. Complete original
  history output64,64,64,64,64,65,64,65,65,65,65,65; frame9 no longer oldcode1.
  Boundary-exact frame7 remains adjacent64/65 ambiguity, not a gross jump.
  Both directed sets match all ideal codes, covering signed large transitions,
  0/255 centers,127/128 alternation and±.25LSB aroundk1/32/64/128/192/255.
- 44frames,352compare/write/update each, MSBfirst and compare<write<update<
  nextcompare, stable90/98ns codes/rails;1408phase/704restore events handled.
  Completion29.460006..29.928026ns, maxrawheld.234215mV and precompare.118632LSB.
  All67analogMOS/6terminalpairs fulltime pass separatecore.99V/IO1.98V
  engineering screens; reference/comparator/IO peaks.947124/.952012/1.790505V.
  Not all logic-terminal or foundry-lifetime coverage. Native0errors/7known
  warnings each; noCMI/LTE/convergence failure, warnings retained/explained.
  InitialDC gmin notices and directedDC bad-pivot notices retained (oldB had
  both); footer5/6/6notices, not all5. No solver adjustment or native rerun,
  no physical power-on qualification.
- All38targetcurrents saved. WarmVDD.079727/.080071/.080004mW and reference
  .020743/.014247/.016287mW. Signedenergy separates startup/warm/observed and
  acquisition/conversion-accounting/other; idealdriver delivery/recovery and
  externalinput separated. Realclock/refdriver/refbuffer overhead missing,
  so no realwholeADC<=1mW qualification. No FFT/DNL/INL/ENOB claim.
- Native136-signalASCII exceeds safe whole-file parser RAM. Local bounded
  float64 streaming preserves2434483points/delta values and rawfiles. Fixed
  TRACE current PROP metadata parsing before consumption; bundled/synthetic/
  real2048point/schema checks pass, actual parser/source/wave hashes recorded.
  No solver, rawdata, saves or precision relaxation and no native rerun.
- Power sign/unit/window self-check, source/history/native/solver assertions,
  code/timing/stress/energy analysis,5figure visual review/provenance, compile,
  UTF8/YAML/JSON/links and focused diff review. Curated results/report/figures
  plus narrow status/log; local scoped results commit only, no push. Pages
  skill improved measured-vs-model-limit wording in the local report; no cloud
  Page or new automation, no old R3 long-task restart, no experience extraction.

### 2026-10-21 Review wrap-up and illustrate reference timer failure

- User requested review of their edits and a concise illustrated explanation
  of section5. Plan2026-10-21-wrapup-timer-review. Read the latest note and
  historical/selected circuit evidence; preserve all user text outside section5.
- Verilog-A skill/events reference guided the distinction between a scheduled
  callback and the model's redundant absolute-time guard. Explained0.159fs
  early callback rejection, missed40ns acquisition, late reference restoration
  and held-charge disturbance; unchanged native devices and nominal timing.
- Added a saved-data-only reporting script, Chinese PNG/SVG and provenance.
  Hash-verified A/b3 waveforms reproduce frame9errors-442.8504966/+0.1013553mV
  at841.65ns and actual codes1/65 at898ns. N7 target is VREFP, not all platesVCM.
  Full acquisition and handoff zoom share actual saved signals and baselines.
- Waveform/receipt/curated hashes, AST/execution, image visual review, SVG,
  UTF8/YAML, new links and outside-section preservation pass. Scoped staged
  diff check excludes the user's existing section1 trailing whitespace.
  Local scoped documentation commit only; no simulation, OA/GUI change or push.

### 2026-10-21 Refocus wrap-up section5 on early detection

- User requests the broader lesson of AI-assisted short tests and monitoring,
  with timer only as an example. Rewrote section5 in two concise paragraphs,
  explicitly locating the defect in the ideal reference-control VA model and
  stating that this control logic has not been implemented at transistor level.
- Retained the existing actual-waveform figure and shortened its caption.
  Other sections/user edits unchanged; UTF8/YAML, link and scoped diff checks.
  Local section-only commit; no circuit, simulation, image, GUI or push action.

### 2026-10-21 Launch B1x coherent512 dynamic capture

- User authorized one4warm+512observed capture at10MS/s,near4.5MHz,-1dBFS,
  no PVT/mismatch or circuit/precision changes; whole-batch analysis and
  anomaly-only interruption. Plan2026-10-21-b-dynamic-512, frozen7875a3a.
  N512/k231 yields4511718.75Hz, actual/declared51.6us, source phases retained.
- Spectre/Virtuoso skills keep nativeAPS4 and supported read-only OA checks;
  top/TB/36dependencies/currentBVA verified unchanged, healthy0.8/t28_io.
  No old native bridge job; no OA write, no DUT replacement, no VA edit.
  EVAS is not used because it cannot solve this PDK MOS/subckt hierarchy.
- Full136continuous signals retained, notstrobeonly. Remote~409GiBfree;
  local~65GiBfree. Estimated native~130GiB, gzip1.5ratio.2591 predicts~34GiB.
  Exact remote gzip/SCP/gzip/SHA fixture passes (not a simulation), frame
  stream/PROP/boundary/native0/4/8/15energy+held equivalence, FFT/ADCToolbox/
  gain/delay/alias/Nyquist math self-checks, compile/source hashes pass.
  Whole-run arrays/uncompressed files are not expanded on local E:.
- Exactly one hidden launch at17:32:12local: coordinator62600, Spectre4639,
  scratchcf76d807; initial2/516frames8compares/valid/noCMI/LTE/grossalarm.
  Actual APS4/effective solver parameters and all136finite saved traces read
  back from live log/PSF. Startup-query helper dependency corrected locally
  only; native unchanged and not restarted. Local watch checks120s, exact
  owned-process TERM only for stated clear anomalies; expectedfixedlag not
  a raw-held-voltage abort. No automatic native retry or extra experiment.
- Reused heartbeatb only, new512scope/15min/ACTIVE verified from tool andTOML;
  quiet normal progress, notify clearfailure/action/finalcompletion. Other
  automations untouched; no archive. Whole-batch reducer/analyzer run after
  native completion, then human-visible figure/metric review and curation.
  Current status is running, not qualified or completed. Real driver/buffer
  power and thermal noise/PVT/fullcode remain outside this capture. Report
  follows document-skill separation of measured metrics and model limits.
- Scoped source and launch documentation commits only, no push. Existing
  Obsidian/cdac10 edits and independently committed timer-review report remain
  outside this target; current design/oldresults/PDK all preserved.

- Post-launch local-only parser audit corrected premature1fs-tolerance frame
  flush near stop; close-boundary/EOF-roundoff synthetic checks and native
  power/held equivalence pass. Full native data are untouched, still running;
  preserve initial launch hash and record actually used reducer hash later.
  No topology/timing/precision/input/native restart or other task changes.

- Initial7/516frames show oneSPECTRE16780 at566.964ns on nativeSAR internal
  XDUT.XCTRL.XBPP.XB0.X005.N; legal8compares/stablecodes/noCMI/grossalarm.
  Retain and disclose this precision notice, continue unchanged under the
  frozen cumulative>=3LTE stop rule; no clean-precision qualification claim.

### 2026-10-21 B512 collection failed while original Spectre remained active

- At10:55:21UTC coordinator62600 exited and flow=failed. Original SSH
  execution disconnected, then the compression command asserted on another
  connection reset. Bridge download was attempted after nonzero execution
  return without this wrapper verifying native completion; compressing_native
  was premature, not evidence of finished516frames. Status-query timeout
  errors also retained. No transport source or live circuit repair attempted.
- Independent fresh read10:56:11UTC binds original4639 to exactcf76d807/deck:
  still running,78/516frames/74observed, valid8comparisons/stablecodes, noCMI
  orfatal, same1LTE. Native raw~21.15GB growing; earlygzip~3.69GB is partial,
  not accepted or analyzed. No result.ok/completion/SHA/FFT claim. Snapshot
  and full failure logs retained inoutput/b_dynamic_512, factual incomplete
  result curated inverification/integration/b_dynamic_512_results.json.
- No kill, restart, new simulation, solver/circuit/OA edit or remote cleanup.
  Paused only heartbeatb through app tool; exactid/thread/status read back.
  User direction requested before reattaching monitoring/collection to the
  same original job. Native process not declared failed and data preserved.
- Document skill keeps collection failure separate from circuit performance.
  Local scoped report/plan/results commit only, no push; unrelated dirty
  Obsidian/cdac10 work preserved. Focused JSON/identity/readback/diff checks.

### 2026-10-21 Repair B512 monitoring and collection without native restart

- User explicitly authorized repair. Existing target plan expanded before
  edits; exact4639/cf76d807 only, shared bridge/PDK/OA and unrelated work
  remain read-only. Add a reattachment coordinator with no native launch path,
  a uniquely locked detached gzip/hash worker, short bounded SSH queries,
  resumable64MiB download checkpoints and per-range/final SHA checks.
- Refuse compression while native lives or without complete516 measurement/
  probe history and normal zero-error footer. Preserve early partialgzip;
  use a separate recovery_v1/full.tran.tran.gz. Stream SHA in1MiB blocks
  instead of the inherited read_bytes hashing of an estimated34GiB file.
- Preserve lost original OS exit status asunknown/result.ok=false; only a
  complete separately gated recovered capture may proceed to conditional
  offline reduction. Propagate execution provenance and a failed execution
  qualification, never fabricate native rc0 or remove the known LTE notice.
- Five focused offline tests, Python compile, old native-frame reducer and
  FFT/ADCToolbox self-checks pass.1,560,000byte exactscratch fixture download
  matches expected SHA, remote worker sh-n passes, remote deck/5include hashes
  match immutable inputs and originalPID/startticks1449028686 remain active.
  No new circuit test, native kill/restart, OA write or data cleanup.
- Preparation source commit only, no push. Hidden local watch launch and
  sameheartbeatb reactivation follow verified preparation; launch readback
  will be recorded separately, not inferred from test success.

- Preparation committed1e53989; one hidden reattachment at19:08:29local,
  launcher40508/actualwatch37044. Flowrunning_native_recovered; original
  Spectre4639/startticks1449028686 retained,90/516frames/86observed, same1LTE,
  noCMI/invalid/grossalarm and recovery error log empty. Reused onlyheartbeatb
  with repair provenance and conditional analysis rules, tool+TOML ACTIVE
  readback confirmed. Docs/results now distinguish live recovery from old
  collection failure; original launch/failure snapshots retained. No push.

- Offline runtime compatibility follow-up made complete_gate pure standard
  library for projectPython (no bridge installed), without changing any
  completion criterion. Isolated atomic pending names prevent concurrent
  status writers colliding; a focused Windows test exposed transient replace
  sharing errors, now covered by bounded<1s PermissionError retries. Six
  focused cases and three offline-environment cases pass after that fix.
  Loaded collector remains1e53989, no process restart; future reducer imports
  corrected guard. Native progress90->92->93 with no new alarms/error output.

### 2026-10-21 Enforce remote-only results and audit historical storage

- User prohibited full waveform downloads and explicitly requested remote
  analysis/metrics+figures only, progress attention and a no-delete cleanup
  list. Plan updated first; unrelated dirty work preserved. New data policy
  disables PSF/gzip/pickle transfer and old local collector/packing entry;
  boundedJSON1MiB/PNG4MiB/batch20MiB limits, no native rerun or cleanup.
- Read-only remote status helper executes on existingPython2.7.5, returns
  ~2KiB metrics only. Original4639/all matching native absent;95/516frames,
  rawlast9.556070994us/25,599,275,008bytes, no completionfooter.2LTE, no
  invalid/gross/CMI/fatal record; cause/OSexitstatus unknown and no automatic
  interruption receipt. No raw/log download, remote dependency installation,
  circuit/solver/OA write, native restart or deletion. Full remote dynamic
  analysis unavailable for incomplete capture; ask rerun direction, keepb
  paused instead of claiming resumed progress. Exact frozen deck hash passes.
- Two focused policy/size/legacy-collector refusal tests pass. Metadata-only
  local audit:output106.947GiB;236files>100MiB total81.332GiB. SHA-identical
  JSON pair814,368,482bytes each;10same-case-PSF pickle candidates5.611GiB;
  raw57.007GiB is not expendable cache. Checklist includes regression/cache
  dependencies and unique-evidence risks. No files moved/deleted or bulk copy.
- Document skill separates verified status from full-analysis readiness,
  and cleanup candidates from authorization. Local focused commit/no push.

### 2026-10-21 Implement SAR8 R4 native reference control and integration

- Bounded transistor/device candidate in35 new SAR_ADC_T28 cells; old R3,
  Bootstrap, CDAC, comparator and controller full readbacks remain identical.
  Added eight native reference DFFs, real nonoverlap/buffers/PDK gate resistors,
  and physical MOM/resistor replacements; no internal behavioral control.
- Preserved failed iterations: fast-driver stress; narrow UPDATE filtered by
  the capture RC; clocked startup initialization; floating-top simultaneous
  opposite rail handoff. Legal five-Series-segment CDF replaces a rejected
  overlong resistor request. Final single-SR two-phase control captures actual
  D before next CODE; no ideal timer, input oracle, or ADC topology change.
- Unit208ps:18/18 words and16 phase pairs correct. Final full4-frame TT0.9V27C
  codes145/14/241/14,8 compare/write/update each,64 reference captures correct,
  stable valid outputs; conversion29.951..29.995ns, held max0.202295mV,
  precompare0.147335LSB. All67 analog six-pair voltage screens pass; reference/
  comparator/IO peaks0.962484/0.950655/1.751582V. Native0errors/7existing
  PDK-global warnings/5notices; noCMI/LTE, no precision relaxation.
- Zero markers/exact owned OA readbacks, full-CDF run/curated DUT identical
  to native OA export. Report/config,320KiB curated results, two final figures,
  reusable DUT/TB/run netlists and scoped scripts saved. R4 opened for review;
  R3 remains baseline. Full-code/FFT/PVT/noise/mismatch/area/layout and system
  supply/reference-buffer/IO qualification not claimed. Source-power windows
  are recorded, not an overall1mW signoff.
- Five focused tests, Python compile, YAML parse and scoped diff checks pass.
  User Obsidian/cdac10 work preserved; existing wrap-up trailing space left
  untouched. Failed raw evidence retained in ignored output. Local scoped
  commit; no push.

### 2026-10-21 Delete explicitly approved local historical waveforms

- User confirmed permanent removal of the proposed 39.93 GiB historical batch.
  Bounded plan preceded changes. Frozen 202 files / 42,877,383,874 bytes under 19
  literal historical output roots; no tracked targets, reparse points, active
  referencing local processes, recursive deletion, recycle-bin or backup copy.
- Removed only approved large PSF/waveform JSON/CSV/pickle from old 10-bit models,
  early Bootstrap, obsolete 26-cell handshake, R1/R2 timing sweeps and W2/W3.
  All 202 absent; 8,281 retained files' content+metadata aggregate SHA identical
  before/after; 8 explicit baseline/evidence hashes pass. Kept source/netlists,
  logs/metrics/figures, B/W1 short tests, anomaly and B512 failure records,
  selected controller, R3 and new R4/cdac10 work. No remote access or simulation.
- E free 53.943497->93.875572 GiB; net 39.932076 GiB versus 39.932676 GiB file
  contents (filesystem/concurrent changes). Receipt in
  `verification/storage/2026-10-21-history-cleanup.json`; cleanup report and
  status note identify irreversible waveform loss and historical reanalysis
  dependencies. No verified backup; new detailed analysis may need rerunning.
- PowerShell syntax/dry-run and focused completion/absence/receipt validation;
  scoped diff review/local commit only, no push. Unrelated dirty work retained.

### 2026-10-21 R4 full-code and coherent-sine characterization — running

- Live OA export matches the frozen R4 DUT; no schematic/device changes.
  Added isolated external stimulus/observer, immutable cases, analysis and
  report automation under sar8_r4_performance. Existing Obsidian/cdac10 work
  and concurrent cleanup commit3577987 remain untouched.
- Four-frame APS/CX/AX comparisons and static/dynamic measurement smokes
  completed. CX4 took101.186s versus APS1407.687s; same145/14/241/14 codes,
  max held difference2.16251microvolts. Effective settings differ, so this is
  not an equal-tolerance speedup claim. Three independent metric/source tests
  pass; direct FFT agrees with ADCToolbox on the32-point smoke.
- Continuous-sine smoke has CMI2751/2753/2755 reference-switch warnings around
  acquisition initialization despite valid frame counts; preserve as an
  electrical failure. Do not promote the short-record metrics to final results.
- Production started23:21CST: eight static ranges cover255transitions and
  all256code centers; one continuous1024-point sine at4.501953125MHz/-1dBFS.
  Four native CX jobs concurrently, four threads each, no transient noise/MC.
  flow_status.json is the exact state; setup.json is the small tracked checkpoint.
- Full metrics/figures are pending. Current-thread heartbeat r4 checks every
  30minutes and will review results/plots and finish the scoped log/commit.
  No full-run pass claim, baseline adoption, local commit or push at this stage.

### 2026-10-21 Second approved local waveform cleanup

- User explicitly confirmed the second 395-file historical batch; bounded
  plan preceded changes. Reused first cleanup guards with a new receipt,
  26 literal roots, >=5 MiB waveform-only names and exact byte/count gate.
- Permanently removed 33,847,727,848 B / 31.523153 GiB from old CDAC sweeps,
  initial CDAC transient/PVT, pre-B R3/edge timing, old sampling and macros.
  All 395 absent; 13,781 retained files' content/metadata digest and eight
  protected baseline/evidence hashes pass. Kept netlists/logs/metrics/figures,
  current B/W1 and short tests, anomaly/B512 evidence, R4 and active R4
  performance, selected controller and unrelated cdac10/user work.
- E free93.828037->125.351818 GiB, net31.523781 GiB. No remote connection,
  download, backup copy, simulation or process stop. New detailed historical
  analysis may need re-simulation; no verified raw backup or Git restoration.
- Second receipt: `verification/storage/2026-10-21-history-cleanup-2.json`;
  cumulative report: 597 files / 71.455829 GiB. Focused syntax/dry-run and
  receipt/absence/retention checks pass. Local scoped commit only, no push;
  existing uncommitted R4 log entry preserved and excluded from this commit.

### 2026-10-22 R4 performance SSH-loss recovery — running

- First batch lost SSH transport: four result downloads failed, four later
  uploads failed. Read-only audit found no remaining Spectre process. Preserved
  all failed transport receipts, original netlists and remote native output.
- Recovered original sine1028frames and static001_032: native logStatus PASS,
  complete PSF END/time range, exact DUT identity, independent output decoding.
  Sine lacks the whole-process final zero-error summary/exit code; this remains
  explicit in a separate recovered_result receipt, not a rewritten original.
  Static001_032 has native zero-error completion; all32brackets valid.
- Full1024-point sine: SNDR48.728620dB, ENOB7.802096bit, SFDR65.592698dB;
  direct FFT agrees with ADCToolbox within7.11e-15dB. Frame checks pass and
  no transient numerical diagnostics. CMI2751/2753/2755 persist: not qualified.
- Added owned recover.py and analysis/status provenance support. Six fresh
  static cases use byte-identical decks:033_064,097_128,129_160,161_192,
  193_224,225_255. First `_r1` wrappers (PID120522) failed input lookup:
  Cadence csh startup resets cwd; CMI2011/exit2, no ADC transient executed.
  Kept r1 receipts. Fixed post-source cwd/absolute paths in fresh `_r2`
  wrappers, detached batch PID142976, first4 then remaining2, fourthreads/job.
  Remote stdout/exit files survive client disconnection. Recovery manifest
  is output/sar8_r4_performance/recovery_20261022_r2.json.
- Use recover.py collect at future heartbeats, never restart old flow or
  initialize again. Full static metrics/figures/review/commit remain pending.
  Focused3tests and source compile checks pass. No circuit/PDK/OA mutation,
  baseline change, commit or push; unrelated edits and cleanup preserved.

### 2026-10-22 R4 reference-switch stress diagnosis

- Independent450ns CX1 replay of unchanged R4 and continuous-sine history;
  no OA/PDK/circuit edits or interference with the active static batch.
- Native0errors/18warnings, CMI reproduced, first4codes match long run.
  DUT/deck/wave hashes checked;4004 adaptive samples saved from398ns.
- Acquisition/ref-reset handoff near401.358ns: BN6=1.006685V and
  BP6=-0.111292V, with PMOS body-drain stress1.011292V vs0.99V limit.
  CMP_CLK inactive. Coupling paths not yet separated by intervention.
- Report docs/sar8_r4_reference_stress.md, two inspected waveform figures,
  verification/sar8_r4_refstress/results.json and bounded scripts/plan.
  Effective maxstep4.5ns; local saved gap near peak<=3.248ps; no convergence
  or whole-record worst-case claim. Later gate-overvoltage still unresolved.
- Scoped compile, offline execution and diff checks; unrelated Obsidian
  trailing whitespace retained. Local scoped commit only, no push.

### 2026-10-22 R4 full-code and spectrum characterization — complete

- Collected all6 fresh recovery cases: exit0/native0errors/full PSF and exact
  frozen DUT. Original sine recovery qualification remains explicit; no
  whole-process exit code was invented. Original failures/r1 attempts retained.
- Nine final cases,3618frames:255 valid ordered transition brackets,256codes
  and256matching center probes; full1024-point sine. Independent output decode,
  measured-frame edge counts8/8/8/16 and90–98ns stability pass.
- DNL±0.0234375LSB, raw transition error max0.12109375LSB, endpoint INL
  max0.02102768LSB, search bracket0.0078125LSB; gain error-0.0953494%.
  SNDR48.728620dB/ENOB7.802096bit/SFDR65.592698dB; FFT/ADCToolbox agree.
- Performance targets pass but electrical qualification fails: CMI in three
  static segments plus sine. Initial DC relaxation in161_192 retained;
  no transient LTE/convergence diagnostics. EffectiveCX tolerances recorded,
  no equal-accuracy speedup claim; no PVT/MC/noise/layout qualification.
- Report docs/sar8_r4_performance.md, three inspected figures, results.json
  and setup.json. Clarified SAMPLE50% time marker vs physical aperture;
  static transfer now uses measured transition brackets. Three focused tests,
  compile and all-case frozen-DUT audit pass. Scoped diff reviewed; unrelated
  Obsidian whitespace and10bit work preserved. No OA/PDK/baseline changes.
- Local scoped commit only, no push. Final delivery ends this monitoring
  purpose; remove only automation r4, preserving unrelated automations.

### 2026-10-22 R4 ADCToolbox diagnostic panel — complete

- Analyzed existing verified 1024 sine codes with ADCToolbox 0.9.1 using its
  12-tool dashboard structure, explicit rectangular/coherent FFT and 1.8-V
  full-scale normalization. No rerun, calibration, circuit or OA modification.
- Added reproducible toolbox_panel.py, curated metrics/source hash JSON,
  inspected 12-panel figure and Chinese per-panel/metric explanation.
- SNDR48.728620dB / ENOB7.802096bit / SFDR65.592698dB match prior FFT.
  H2–H5-excluded SNR48.799143dB, THD-66.658370dBc; residual RMS0.295170LSB.
- Compile/execution and six numeric consistency checks pass (prior metrics,
  direct SNR, Parseval, LSB scaling, harmonic reconstruction). Final image
  inspected. Scoped diff reviewed; user Obsidian/10-bit changes preserved.
- Distinguish fitted residuals from aperture error, static INL and physical
  noise/jitter. Reference CMI failures and original sine-run evidence limits
  retained. Local scoped commit only; no push or baseline replacement.

### 2026-10-22 R4 reference reset and sampling sequencing — experiment complete

- Compared frozen R4 with native T28 RC/MOS reset-first A and sample-first B.
  Only top-level sampling/reset routing and cloned sequencing cells changed;
  original analog sizes,3x reference banks, R4/PDK/OA remain unchanged.
- Three500ns CX cases:reference max1.011292/0.989420/1.022525V; five-frame
  codes identical, independent8/8/8/16 edge and output-stability checks pass.
  A delays Bootstrap rising control1.732ns and falling control~25ps; not an
  identical-aperture replacement. B rejected; A margin only0.580mV.
- Honored-options A500ns:actual10ps/reltol1e-7/10nV/100fA; reference max
  0.989263V, five-frame timing passes, no observed selected-device violations.
  Native zero-error/PASS/complete PSF; stopped owned LOCAL postprocessing only
  for3.916GB memory pressure. Task-local streaming reader exactly matches all
  129baseline vectors, retains731726precise points; recovery evidence explicit.
  No installed-tool changes, rerun or invented native exit status.
- A4.6us:46native-valid frames; saved24–45independently checked. First CMI
  501.359ns; saved2.398–4.6us worst P6 PMOS Vbd0.991464V, N3 NMOS Vgb
  0.990910V. N3 driver0.902865V with unchanged low Q3 establishes post-R gate
  overshoot. Code indices9/36 differ from old sine by+1/-1; no new FFT claim.
- Results remain electrical failures, not a fixed baseline. Proposed next
  target staged reference initialization / gate holding tests; not implemented.
  No current-path integral, full-logic stress/PVT/MC/PEX qualification claimed.
- Added concise report, three inspected figures, native fragments/provenance,
  analysis and recovery scripts and result summaries. Frozen hashes, script
  compilation/execution and scoped diff checked. User Obsidian/10bit work
  preserved; local scoped commit only, no push and no OA modification.

### 2026-10-22 R4 staged reference reset and gate holding — experiment complete

- Kept frozen R4, PDK, previous A/B cases and all OA unchanged. Added native
  per-bit reset sequencing; compared MSB-first/LSB-first with A, gate R/2,
  and final-driver2x. No ideal internal drive or new behavioral ADC logic.
- Five600ns screens completed: reference peaks0.991063/0.961044/0.945182/
  1.056698/0.995498V respectively. All six-frame codes/timing checks pass;
  A and the two drive-only variants still fail electrical screening.
- Selected MSB-first:4.6us,724408points,46independently verified frames,
  45restart checks, no CMI and no six-pair violation among417selectedMOS.
  Reference worst P5 PMOS Vgb0.955838V at4001.388523ns,34.162mV margin.
- Strict300ns:467168points,3frames,10ps/1e-7/10nV/100fA, no CMI;
  reference0.945142V versus ordinary CX0.945182V at the short201ns event.
  Does not strictly recheck the long4001ns worst. Tightest selected core
  margin observed across these tests is10.741mV in reference drivers.
- Acquisition command width drops~38.29to33.85ns; falling edge shifts~27ps.
  Four +/-1 code changes versus A, six versus R4; no reused SNDR/ENOB claim.
  RST_DONE is a fixed-delay command marker, not analog completion feedback.
- Four gate-resistor current saves verified natively. At the501ns event,
  A GNN3=0.988165V versus pre-R driver0.902781V, +6.839uA leaves gate
  into resistor. MSB-first gate peak0.936066V and corresponding+2.797uA.
  Evidence supports coupling/finite gate holding, not a full parasitic-charge
  decomposition. R/2 improves that gate but worsens BN6 to1.056698V.
- Native exit0/zero errors/PASS, PSF END/exact signals/finite monotonic full
  duration and hashes checked. Long SCP timed out during anomalous elapsed
  wait; recovered the SAME9.01GB record via11hashed chunks, no native rerun.
  Strict5.81GB record also matches remote native SHA256. No installed bridge
  changes, unrelated process stops, raw overwrite or destructive cleanup.
- Added concise report, four visually inspected figures, native candidate
  fragments/provenance, scripts and curated numeric results. Frozen hashes,
  focused execution/compile checks and scoped diff review pass. No PVT/MC,
  noise/PEX/new full-code/FFT qualification, no baseline/OA promotion.
  User Obsidian and10bit changes preserved. Scoped local commit only; no push.

## 2026-10-22 — R4 reference initialization moved into preceding idle

- User requested restoring acquisition time while preserving its closing phase.
  Cloned native controller port/reference-reset logic; ACTIVE-low plus native RC
  guard starts MSB-first reset after final capture. SAR output stores still reset
  on original SAMPLE; no new ideal clock/behavioral drive or analog sizing change.
- Owned scripts/netlist/verification/docs/figures under sar8_r4_idle and target
  plan. Remote OA:none. Frozen R4, PDK, original sine deck and prior candidates
  unchanged. User Obsidian/10bit edits remain untouched; no baseline promotion.
- Native600ns/6frames,4600ns/46frames and honored200ns/2frames complete with
  exit0, logStatus PASS, zero errors and no CMI. Long741399points, strict324663;
  every saved point retained. Exact native file SHA256s verified after transfer
  for long9.72GB and strict4.25GB; no rerun or transfer recovery was required.
- Long46independent frames pass8/8/8/16clock checks and idle data retention;
  reference128 at startup/acquisition,45post-startup window checks pass. Reset
  occurs~76.1–80.7ns, at least3.815ns after last reference capture. Acquisition
  minimum38.262366ns versus33.848142ns; closing control moves at most11.094ps
  earlier, not mathematical equality or a physical-aperture equivalence proof.
- All445selectedMOS six-terminal-pair screens pass; other internals rely on CMI.
  Long reference0.955795153V at3976.416832ns (P5PMOSVgb), margin34.204847mV.
  Strict short reference0.945141089V; strict driver0.979259945V leaves10.740mV.
  The long-worst3976ns event has NOT been strictly replayed. No PVT/MC/noise/PEX
  or full-code/FFT qualification; existing R4 performance labels are not reused.
- Relative to old staged: frames16/32 each+1code, others identical. Fixed41.8ns
  held-differential changes+0.182895/+0.217379mV; no unique causal attribution.
  Relative A changes13/26; relative frozen R4 also9/36. Native/independent decode
  agree. Analog CDAC residue after idle reset is intentionally no longer valid
  for the completed conversion; digital data remains valid until next SAMPLE.
- Ordinary CX actualmaxstep6/46ns,1e-4/1uV/1pA; strict10ps/1e-7/10nV/100fA.
  Three final native-wave figures inspected, source/port/unchanged-leaf checks,
  focused compile/execution and scoped diff review pass. This entry accompanies
  the scoped local commit; no push, no unrelated changes staged.

## 2026-10-22 — Idle-tail full-code/sine characterization launched

- User requested full nominal static and 1024-point sine comparison against R4,
  using the idle-tail-reset candidate from 027b951. Candidate DUT hash retained;
  no sizing/topology change, PVT, mismatch, noise or PEX. Remote OA:none.
- New isolated scripts/verification/output namespace `sar8_idle_performance`,
  target plan `2026-10-22-idle-performance`. R4 results/sources, prior idle
  experiments, PDK, Obsidian and 10-bit user changes remain untouched.
- Native t28_io/Spectre preflight passed. Static boundary-128 smoke:15 valid
  frames, centers127/128 correct, valid [-54.931640625uV,0V] bracket; native
  exit0/PASS/END, zero errors/no CMI, no transient numerical diagnostic.
  DC Gmin/pivot notes preserved. PSF/deck hashes verified after collection.
- Focused syntax/fixture/scheduler checks pass: all9 new decks reduce exactly
  to original R4 deck text when swapping only the DUT back. Measurement
  contexts and VA model hashes match; candidate has49 subcircuits.
- Full immutable batch dispatched at23:32CST: one1028-frame sine plus eight
  static segments,3618frames total, four native lanes x four CX threads.
  Initial status confirms four running/five queued. No case restarted.
- One-shot hidden local collector started23:33CST; no new app automation.
  It only collects existing jobs and runs same-method FFT/ADCToolbox analysis
  after complete. Native jobs survive SSH/client loss. Raw and status files
  remain under output/sar8_idle_performance; local collector is bounded24h.
- Full metrics, CMI review and three final plot inspections are PENDING.
  Launch checkpoint committed separately; no final qualification claim,
  no R4/OA promotion and no push. Next turn must inspect existing launch and
  collector receipts, not run setup/full again.

## 2026-10-23 — Idle-tail result collection blocked by connectivity

- User requested collection of the completed nine-case batch. Earlier live
  inspection confirmed all native exit codes 0, 3618 total frame records,
  eight static completion markers and no CMI warning lines. No new run needed.
- Original local collector is absent; no completion receipt and no full-case
  partial downloads exist. Its termination cause is not established.
- Two bounded supported-bridge collection attempts failed while querying the
  first remote status, before downloading files. Independent TCP check to the
  configured jump host port22 also timed out after5s. Network/VPN/server root
  cause not determined; do not mislabel this as a Spectre/circuit failure.
- Native cases, PDK, OA, R4 baseline and user edits untouched. Exact nine-case
  preparation/source checks still pass. Final analysis/images remain pending;
  resume existing collect after access is restored, never relaunch.
- Scoped documentation checkpoint only; no push or baseline promotion.

## 2026-10-23 — Idle-tail full characterization recovered and reviewed

- Network restored; collected all9 existing cases, no native reruns. Exit0,
  PASS/END, full duration and remote/local PSF/deck hashes verified. Preserved
  stopped collector log and original cases. No OA/PDK/baseline changes.
- All3618 frames valid with independent output decode;255 valid ordered
  boundaries,256 centers correct/full code coverage;1024 measured sine codes.
- DNL +/-0.0234375LSB, max endpoint INL0.02102768LSB; SNDR48.759885dB,
  ENOB7.807290bit, SFDR65.153774dB. Versus R4:SNDR+0.031265dB,
  ENOB+0.005193bit, SFDR-0.438923dB;56/1024 codes differ by at most1.
- No CMI cases (R4:4), no transient numerical diagnostics; DC relaxation
  retained for static001_032,097_128,161_192. Effective settings match R4.
  FFT/ADCToolbox agree within6e-14dB. Nominal-only performance passes, not
  reliability sign-off. Three final figures visually reviewed.
- Generated scoped report/results, updated plan/status; owned diff checked
  for local result commit, no push. User Obsidian/10bit work untouched.

## 2026-10-23 — Idle candidate ADCToolbox and time fit

- Generated candidate 12-panel, chronological fit/readout/residual plot and
  phase-fold plot from unchanged 1024-code results. No simulation or OA work.
- Reused ADCToolbox 0.9.1; FFT checks, independent sine reconstruction,
  source-at-clock-edge validation and Python compile pass. All three PNGs
  visually inspected. Residual 2.067754 mV RMS, 0.294081 LSB.
- Clock-edge difference 28.402045 mV RMS is separated from fitted residual;
  equivalent phase lag 1.766137 ns is not identified as physical aperture delay.
- Added concise report and numeric provenance. Scoped diff checked for local
  commit, no push. Existing user Obsidian whitespace warning left untouched;
  unrelated Obsidian and 10-bit changes preserved.

## 2026-10-23 — Obsidian performance curation

- Added Rvision/8bit性能与ADCToolbox.md with nominal R4 comparison, twelve-panel
  reading guide, raw versus harmonic-relative phase and timing-fit explanation.
  Added Result navigation; preserved old R3 history and user's wrap-up edits.
- Copied five reviewed PNGs into vault assets; hashes identical and all local
  image/source links resolve. Readback and scoped diff check performed; no
  native Obsidian UI rendering check. No simulation, OA or circuit changes.
- User explicitly authorizes commit/push of these results; publication on the
  current branch includes ten existing analysis/experiment commits. Unrelated
  dirty files are excluded. Remote push outcome reported in the conversation.

## 2026-10-24 — Verified duplicate and cache cleanup

- User authorized first-stage cleanup only. Removed four gzip transfer copies
  after decompressed SHA256 matched retained PSF; removed 17 pickle caches
  after full native-data reconstruction and exact serialized-hash comparison.
- Removed 15,204,425,361 bytes; observed E free-space gain 15,204,466,688 bytes,
  free afterwards 95,974,932,480 bytes. Exact paths and hashes in verification/
  cache_cleanup_20261024{,_deleted}.json. 424 protected files hash-unchanged.
- Retained all PSF/NPZ, receipts/logs, final metrics/plots, user Obsidian and
  10-bit work. Kept seven unresolved refgate caches, passive AC cache and
  transport fixture. No recursive deletion, simulation or remote mutation.
- Added audit/recovery helper and exact-path PowerShell deletion guard.
  Fixed PickleBuffer hash handling before deletion; resumed audit checkpoints.
  Caches can be restored offline to original hashes; no recycle-bin copy.
  Syntax/scoped diff checks pass. Local maintenance commit only, no push.

## 2026-10-24 — PVT and mismatch plan only

- Drafted bounded pre-layout plan for frozen idle-reset candidate, with source
  identity/statistical activation, 27-point PVT short screens, comparator-first
  mismatch and conditional integrated characterization. No jobs launched.
- Explicitly distinguishes fixed references from ratiometric diagnostics,
  systematic offset budget from random-offset yield, and nominal MOM merging
  from independent-unit mismatch. Includes storage caps after cache cleanup.
- Read current specification, candidate timing/stress and old comparator/CDAC
  evidence. Only new plan and this log changed; local commit, no push.

## 2026-10-24 — Frozen SAR8 first five PVT risk points

- Executed the authorized version/model audit and five MOS PVT points on idle
  candidate 027b951 (DUT ef0fc74a3df306a366261bd5ce6bbe01f6b4386007c0b86c3150e09c28f976ea).
  Verified comparator topology/sizes, device inventory, actual model hashes,
  and fourteen remote/local deck identities. PDK read-only, remote OA none;
  CIW connection was unavailable, native t28_io SSH/Spectre was usable.
- Four native nMOS/MOM mismatch seeds showed physical current/capacitance
  variation; repeated seed matched exactly. Independent 512-unit CDAC nominal
  regression matched four historical codes, held difference <=17.2 uV.
  This is representative model activation, not integrated mismatch signoff.
- Ten 600 ns cases completed with exit 0, native PASS/PSF END and 60 frames.
  All frame counts, conversion deadlines, reference acquisition word, reset
  ordering, H/L nonoverlap and observed output-hold checks passed. SS/.81/-40
  had 76.6 mV held error after full reversal and code 23 instead of 12.
  FF/.99/125 had code 10 instead of 12 despite acquisition being established.
  Startup deviations were retained separately; no six-point FFT/INL/DNL claim.
- Both FF/.99 corners showed native CMI and selected core terminal overstress.
  Main CX actual reltol=1e-4/maxstep=6 ns. Two extra full-node 200 ns strict
  diagnostics were stopped after exact process checks to respect storage cap;
  exit 2, raw prefixes retained. Replacement selected-node 80 ns checks both
  completed: actual transient reltol=1e-7/maxstep=10 ps, representative peaks
  1.057992 V (cold) and 1.049920 V (hot); CMI persists. Not complete-frame or
  all-device refined verification. No circuit changes or additional matrix.
- Added isolated scripts, setup/audit/provenance/results, concise report and
  two inspected waveform figures under sar8_pvt_mismatch paths. All native
  samples used for selected-device stress, compact waveforms not decimated.
  Native PSF retained in task-only remote scratch, not long-term archive.
  New remote data 18,018,554,892 bytes (~16.78 GiB); local ~0.69 GiB. No deletion.
- Python compilation, focused native execution/analysis, source readback and
  scoped diff checks passed. Pre-existing Obsidian trailing whitespace is not
  changed. User Obsidian/10-bit work preserved. First-batch result gate failed;
  remaining PVT/MC stages remain open. Scoped local result commit only, no push.

## 2026-10-24 — SS cold Bootstrap acquisition diagnosis

- User requested TT comparison, cause localization and proposed changes only.
  Reused TT/.90/27, SS/.81/-40 and SS/.81/125 original native PSF, extracting
  all samples in 85–145 ns; complete source hashes match prior PVT evidence.
  New extraction files in separate scratch; no original file overwritten.
- Pump transfer is established by ~105 ns; cold P-side VGS ~.797 V, BTOP-G
  and BBOT-VIN only tens of uV at 110 ns. P TOP still .136221 V at 140 ns
  against .045 V target. Held error 76.559 mV versus TT .207 mV. Window
  difference ~.42 ns and pump-start difference ~.90 ns do not explain the
  sustained slow discharge. About 11 mV precharge deficit remains secondary.
- Three native DC diagnostics copied frozen Mmain W/L=1u/150n and all geometry.
  VS=.045, VB=0, VDS=.1/.4/.75; 31 VGS points .75–1.05 V, no ADC changes.
  Exit 0/PASS; actual reltol=1e-6. At VDS=.4, TT/.893-V VGS gives 101.22 uA,
  SS cold/.797 gives 20.19 uA. DC interpolated 110/120-ns current agrees with
  original net input return within ~.05 uA; not a direct Mmain transient-current
  probe or Vth extraction. Primary limit is large-signal main-switch drive.
- Proposed symmetric Mmain 2/3/4-u total-width sweep at fixed L, timing and CDAC,
  followed by pump resizing only if gate loading requires it; verify injection
  and stress across five points. No proposed redesign was implemented.
- Added report, three visually inspected figures, reproducible extraction/DC
  scripts and metrics/provenance. Fixed local import-name collision and PSF DC
  scalar parser before analysis. Python compile, source hash and scoped checks;
  no OA/PDK changes, no original data deletion. User dirty files preserved.
  Local task-only commit, no push; broader PVT/mismatch remains unqualified.

## 2026-10-24 — Mmain width sweep and selected five-point PVT

- Authorized isolated 2/3/4-um total-width experiment, retaining the original
  1-um control. Explicit identical 1u/150n MOS units in parallel on both sides;
  no other DUT, external timing, source, model or OA changes. Each candidate
  inverse-replaces to the frozen original DUT. No baseline promotion or push.
- Four SS/.81/-40 native six-frame bidirectional cases completed. Frames 1-5
  maximum absolute preclose/held errors (mV): 1u 82.263/76.559,
  2u .146/.298, 3u .006/.307, 4u .003/.360. Net turn-off changes are not
  isolated channel injection. Selected smallest eligible width 2u; all four
  timing/stress checks pass, only 1u fails post-startup static codes.
- Selected 2u original five-point static/sine regression submitted once, two
  native jobs at a time, four threads each. All 10 cases/60 frames completed
  and recovered. Post-startup held maxima TT/SS-cold/SS-hot/FF-cold/FF-hot:
  .405/.298/.289/.577/.518 mV, all below 1.758 mV; preclose max .1461 mV.
  Timing/idle checks pass; maximum conversion 41.044 ns. FF CMI remains,
  with selected core peaks 1.057558/1.049466 V against .99 V. FF hot still
  gives code 10 for -.81 V despite established sampling. Overall PVT gate
  fails; startup deviations retained separately, no new FFT/INL/DNL/MC claim.
- Two native-waveform/error figures inspected; ideal baselines, measurement
  times and model scope labelled. User Obsidian/10-bit changes untouched.
- Python compilation, focused analysis, all 14 remote/local deck hashes,
  exact original-stimulus restoration for PVT, unchanged original/model hashes
  and same effective solver settings verified. All 84 native frames complete.
  Raw PSF retained in isolated remote scratch (not durable project archive);
  new local data ~.87 GiB, remote ~16.83 GiB. No deletion or refined rerun.
  Scoped diff review and task-only local commit; no push or baseline replacement.

## 2026-10-24 — FF hot error-code timing diagnosis

- Read-only analysis of frozen 2u native TT/FF-cold/FF-hot static frame 1.
  Original reduced-wave hashes checked; independent 100-180ns caches retained.
  No remote operation, new simulation, DUT/PDK/OA change or baseline promotion.
- First divergent bit is bit2 at reference word12. TT/FF-cold/FF-hot TOP
  residuals +4.592/+4.984/-9.410mV. All 24 writes match comparator polarity;
  final codes12/12/10. FF-hot last100ps drift1.972uV; comparator 90/10 rails
  reached144.93ps before write. Not formal setup/hold or timing signoff.
- FF-hot reference already flat through120-140ns at .892289/.007714V;
  span .884575V predicts ideal code10 at -.81V. 50-ohm source drops imply
  ~154.2uA persistent rail current versus TT~2.6uA, not a measured individual
  MOS leakage. Evidence favors steady reference compression over short wait.
- Specific load branch and counterfactual tests remain unperformed. Proposed
  fixed-timing lower-Rref and fixed-reference longer-delay diagnostics, then
  branch-current localization; no causal claim tying CMI directly to code10.
  Two native waveform figures visually checked; Python/measurement checks
  and scoped local commit only, no push. User Obsidian/10-bit changes preserved.

## 2026-10-24 — FF hot reference-versus-wait causal controls

- User-authorized two immutable FF/.99V/125C six-frame native controls on the
  selected2um DUT: only RREFP/N50->1ohm; separately only quiet-delay C0/C1
  multi30->60. No other circuit, stimulus, sampling clock, model or OA edits.
  EVAS skill compatibility check excludes transistor simulation; native Spectre
  used. Original model/config hashes and license preflight passed.
- Frame1(-.81V) reference spans original/R1/quiet2:884.575/899.629/884.575mV;
  bit2 residuals -9.410/+4.139/-9.426mV; codes10/12/10. Actual bit2 update-to-
  compare intervals2.804866/2.804874/5.254101ns. Conversion28.545/28.543/48.137ns.
  This closes the requested causal comparison in favor of reference compression,
  not insufficient compare waiting, for this observed large-signal code error.
- Reference source current remains ~185.6uA per rail at1ohm versus154.2uA at50ohm;
  specific load/leakage branch still unmeasured. Sampling-close and held errors
  remain essentially unchanged. R1 codes[243,12,127,128,127,145] all accepted;
  quiet2 matches baseline[245,10,127,128,127,145]. Both native runs complete6frames,
  timing/idle checks pass. Quiet2 consumes19.592ns idle margin without benefit.
- CMI and saved core stress failures remain; no whole-ADC or full-PVT clearance.
  This is an ideal source impedance diagnostic, not an implemented reference
  buffer or replacement baseline. Raw PSF preserved; recovered native timing
  samples and hashes, no decimation of retained timing nodes, no deletion.
- Exact inverse source checks and remote deck hashes pass; same effective CX
  tolerances as baseline (reltol1e-4,maxstep6ns,gear2only). Focused Python checks
  and final figure inspection passed. Results in verification/sar8_ff_counterfactual/,
  figure in docs/figures/sar8_ff_counterfactual/. Scoped local commit only,
  no push; user Obsidian and10-bit work untouched.

## 2026-10-24 — Localize reference load to OFF-state channel leakage

- Five bounded native diagnoses on unchanged selected2um ADC: hot/cold FF.99V
  current-probed180ns runs, exact bit7 pair21-point DC controls, hot native OP.
  All exit0/PASS; model/source/remote deck hashes verified. No OA/PDK/production
  fix, baseline replacement or push. User Obsidian/10-bit changes preserved.
- At130ns, 32 MOS four-terminal probes close both reference-rail and bottom-node
  KCL (<1nA). Source154.219uA comprises135.281uA NMOS-OFF paths (87.72%) and
  18.938uA PMOS-OFF paths. Largest XSN7.MN_LOW path67.906uA; next XSP6 33.953uA.
  This is the weighted3x L30nm core switch array, not Bootstrap Mmain.
- XSN7 NMOS gate.501mV, externalVGS-7.213mV. Ideal0V gate only lowers pair load
  67.906->67.259uA(.952%). PMOS idealOFF improves.251%. Same hot bias at-40C
  gives.102849uA NMOS path; integrated cold reference load.2994uA is a distinct
  whole-array measurement with naturally different rail/gate biases.
- Native OP: NMOS intrinsicVGS-7.221mV,Vth140.268mV,ids67.896uA,ibd9.143nA,
  igidl~1e-14A. Below-threshold channel current dominates, not inadequate gate
  drive, persistent overlap, diode conduction or GIDL. isub is impact ionization
  in this model, not a subthreshold-current field. No claim of silicon validation.
- Proposed (not implemented) reference-switch L/low-leakage device selection,
  followed by W/Ron/dynamic tradeoff and actual reference drive budget; retain
  existing sample/bit timing. Existing CMI still open; longer L is not SOA repair.
- Probe-only inverse checks, remote receipts, independent scalar-DC parser
  crosscheck, Python compilation, KCL/gate checks and final figure inspection
  passed. Short-run CX maxstep1.8ns differs from baseline6ns; no equal-setting
  claim. All raw data retained, ~292MiB local/~253MiB remote. Evidence in
  verification/sar8_ref_load/, figure docs/figures/sar8_ref_load/; scoped commit.

## 2026-10-24 — Reference-switch L sweep and selected integrated PVT check

- Owned plan2026-10-24-sar8-ref-length, scripts/verification/output sar8_ref_length,
  and docs/figures/sar8_ref_length. Kept all user Obsidian/10-bit changes. No
  remote OA or PDK changes, no baseline replacement, no push; task-only commit.
- PDK read-only length-selector and W/L-bin audit confirms30/60/90nm for existing
  nch_mac/pch_mac W150/175nm. factor0.9 geometric scaling recorded with source
  hash. This is model-domain validity, not PCell/DRC signoff. Fixed OA-derived
  diffusion/LDE values for single-variable comparison; reconcile callbacks
  before any OA/layout promotion.
- Three first DC decks failed SFE-874 due truncated multiline MOS extraction;
  retained them, fixed parser and checked exact full-parameter Ron copies in
  immutable v2 decks. All3DC+5integrated final native runs exit0/PASS. Remote
  source, monitor, log, reduced artifacts and reducer hashes match local copies.
- FF/.99V/125C fixed-bias array load estimates L30/60/90 =154.219/11.000/4.052uA;
  bit7 Ron N/P=5.197/5.311,6.875/9.100,8.585/13.143ohm. W/nf/multi unchanged.
  Selected L90 by provisional10uA/rail target, not claimed globally optimal.
- Exact16-L-field substitution in8cells; inverse recovers original whole DUT
  and deck. Five PVT integrated cases retain2um Bootstrap, reference50ohm/4pF,
  sampling/compare/reset timing, models and native CX settings. No noise/mismatch.
- Integrated FF hot current154.219->5.008uA, span884.575->899.494mV; bit2 residual
  -9.410->+4.414mV, code10->12; positive code245->243. SS cold frame1 acquisition
  error+.0594->+.0600mV, negligible change. All30 timing/idle checks pass;
  post-startup preclose<=.146653mV, held<=.576399mV, maximum conversion41.012ns.
- Post-startup25/25 codes pass; overall27/30. Startup failures remain TT242,
  SS cold241, SS hot241(expected243). SS hot startup worsens242->241 while
  sampled error remains~-13.718mV; not evidence of new sampling degradation.
- FF native CMI remains. Cold stress failing pairs2008->2008, hot1727->1740
  (2670-pair .99V core guard); hot reference gate-body peak1.05515V at175.063ns.
  Leakage fix is NOT SOA fix; no complete-ADC acceptance or OA promotion.
- Inspected two final figures, compiled scripts, checked source hashes/inverse,
  native logs/frames/stress and scoped diff. Existing user Obsidian whitespace
  fails whole-tree diff-check but is outside scope and untouched. Kept raw
  outputs; ~.366GiB local generated data. Detailed results and limits in plan
  and verification/sar8_ref_length/integrated_comparison.json.

## 2026-10-24 — FF overvoltage location and proposed fixes

- Diagnosis only on frozen e94e802 L90 candidate, FF0.99V/-40C and125C. No new
  simulation, PDK/circuit/OA changes, baseline replacement or push. Preserved
  all user Obsidian and10-bit edits. Task-only local commit per repository policy.
- Read existing native full-resolution windows, validated receipts/source/native
  hashes and completed logs. Terminal mapping5340/5340 matches frozen netlist.
  Stress coverage is445 selected of1833 MOS, NOT full-ADC coverage.
- Reference XCDAC.XSN4.MN_LOW Vgb1.0510/1.0551V occurs during bit7 idle reset,
  before its own bit4 reset; driver-side gate remains~0.9915/0.9918V. Waveforms
  support cross-bit CDAC/drain-gate coupling plus weak fast gate holding.
- Driver XREF.XDRV0.GNNCN/GPNCN Vds1.0576/1.0335V spikes before output falls;
  ACTIVE receiver XIDLE.XN.MN Vgs1.0571/1.0494V at bit4-to-bit3 handoff;
  comparator MNLATP/MNLATN abs(Vbs)1.0453/1.0233V at evaluate clock rise.
  Negative Vbs represents positive X/Y overshoot, not negative X/Y voltage.
- All event VDD traces exactly0.99V, equal model core limit; no overshoot
  headroom. Inspected Bootstrap terminals stay below1.98V guard. Neither
  microscopic crossings nor codes passing justify ignoring native CMI.
- Exact ACTIVE injection branch and capacitance/current contributions remain
  unproven without added probes.3-4ps driver peaks have~0.17ps native steps
  but still require tighter-accuracy convergence before implementation decisions.
- Produced and viewed4 waveform figures. Saved peak inventory/events/provenance
  and focused validation. Plan separates measured facts from causal inference
  and proposes single-variable hold/slew/driver/comparator tests plus supply
  contract review, without silently lowering required FF acceptance voltage.
- Python compile, JSON/hash/phase/terminal checks and scoped diff reviewed.
  Results: plan/2026-10-24-sar8-ff-overvoltage/plan.md,
  verification/sar8_ff_overvoltage/, docs/figures/sar8_ff_overvoltage/.

## 2026-10-24 — Independent reference high-hold and idle bit7 slew controls

- Owned sar8_ref_gate_controls scripts/verification/output/figures and plan.
  Preserved unrelated Obsidian/10-bit edits. No OA/PDK/baseline changes, no push.
- 10native CX six-frame cases: null, high-hold100/25ohm at bit4 (scaled by bit
  weight), bit7 idle-only extra100/300ohm, each FF0.99V/-40C and125C. Helpers
  are ideal diagnostic conductances, NOT completed transistor keeper logic.
  All1833 native MOS pins/parameters and sampling source remain unchanged.
- All native runs exit0/PASS; remote source/helper/reducer/log/data hashes match.
  Effective CX reltol1e-4/maxstep6ns, not requested10ps deck limit. Null vs old
  peak difference<0.000315mV, held difference<0.000660mV, sample-edge<0.075ps.
- 60/60codes correct [243,12,127,128,127,145]; all timing/idle logic checks pass.
  All variants vs null sample-open delta<0.000037ps, close<0.000000009ps;
  helpers are off during established sample-high. No sampling-window tradeoff.
- Hot GNN4 bit7-event peak1.055147->0.992886/0.990733V with high holds. Global
  reference worst instead becomes PMOS |Vgb|~1.05310V (gate~-63.1mV). Cold
  GNN4 goes1.051037->0.992989/0.990758V; global~1.04723V. Later post-release
  GNN4 peak retained separately from original bit7 event; not silently omitted.
- Hot bit7 extra300ohm: GNP7 fall240.24->327.74ps, BN7 rise59.13->70.87ps,
  global reference peak1.055147->1.047886V. Cold214.65->298.58ps,56.38->68.73ps,
  global1.051037->1.046710V. Improvement but all retain CMI/overvoltage.
- All-bottom final settling ~3.539ns hot/~3.198ns cold; margin to next sample
  ~24.536/~27.068ns. Post-startup held error~0.517154/~0.576491mV unchanged.
- Exact real-switch overlap current not measured; logic H/L non-overlap is not
  zero-shoot-through proof. No full-code/FFT/noise/mismatch/PEX qualification;
  existing stress inventory445/1833MOS,2670pairs. Recommend complementary
  stable high/low holding then real asymmetric-driver implementation, not
  promotion of either present diagnostic variant.
- Inspected two final figures; compiled scripts, verified sources/receipts,
  60frame/code/timing checks, measurement-window refinement and scoped diff.
  Results and limitations in plan/2026-10-24-sar8-ref-gate-controls/plan.md and
  verification/sar8_ref_gate_controls/comparison.json. Task-only local commit.

## 2026-10-24 — Symmetric reference holding through all idle reset stages

- Owned sar8_ref_symmetric_hold scripts/verification/output/report/figures and
  target plan. Obsidian and10-bit work preserved; no OA/PDK/baseline changes.
- Four immutable CX cases, FF0.99V/-40C and125C, null vs finite symmetric
  400/2^bit-ohm ideal holds on all32 reference gates. Native1833 MOS unchanged.
  Release on native final-inverter command change, rearm at settled rail;
  no per-bit RST release, covers all subsequent bit resets. Not real keeper.
- All24 frames correct, native exit0/PASS and remote receipts match. Actual
  sampling sources identical, open/close differences<0.001ps vs null. No
  complementary hold overlap/command conflict or sampling/conversion holding.
- Idle gate excursions cold+61.031/-57.103->+1.010/-0.849mV; hot+65.136/
  -62.943->+0.963/-0.913mV. Old high-only history included in waveform comparison.
- Global reference peaks cold1.051031->1.046743V (XSP7.MP_HIGH Vbd, conversion),
  hot1.055136->1.035509V (XSN3.MN_LOW Vgb, conversion). Idle body-drain peaks
  remain1.046679/1.031700V from BN7 negative voltage. All retain CMI/SOA failure.
- All-bottom settling cold3.198->3.337ns, hot3.539->3.674ns; actual next-sample
  margin26.930/24.401ns. Held error~0.5764/0.5171mV unchanged. Max ideal helper
  current2.346mA, not real-keeper supply power. No full-code/FFT/PVT expansion.
- Corrected measurement-only hold window: release at SAMPLE_INT request precedes
  actual Bootstrap SEQ_SAMPLE opening; no circuit rerun/overwrite. Null vs
  original peak difference11.29uV, held5.79uV, timing<0.096ps; recorded explicitly.
- Inspected3final figures; compile, source/hash/24frame/timing/continuity checks
  and scoped diff reviewed. Effective CX reltol1e-4/maxstep6ns unchanged;
  445MOS/2670pair coverage, not all1833. Residuals need accuracy convergence.
- Report docs/sar8_ref_symmetric_hold.md; comparison and validation under
  verification/sar8_ref_symmetric_hold/. Task-only local commit, no push.

## 2026-10-24 — Locate bottom undershoot without changing the circuit

- Owned sar8_bottom_undershoot analysis/plots/verification/report and target
  plan. Read four frozen native FF null/symmetric-hold runs from0e495c0;
  no new simulation, OA/PDK/netlist edits, baseline promotion or push.
- Identified idle XSN7 BN7 and conversion XSP7 BP7 low-to-high handoffs:
  low-N gate falls first, then high-P gate falls before bottom recovers. Cold
  idle BN7 -31.68mV before P-fall -> -56.68mV at472.660ns; actual VREFN at
  peak -3.67mV. Hot idle -41.70mV / -5.96mV. Cold/hot conversion BP7 minima
  -56.74/-44.95mV. Null controls show essentially same mechanism.
- Direct two-MOS mappings verified; no later-bit full gate transition or
  active sampling edge in measured windows. Not only reference-rail droop,
  not a persistent50mV hold error. Native switch currents absent: coupling,
  channel charge and complementary-array contribution not quantitatively split.
- Eight native event windows/cache hashes/voltage identities/gate order and
  terminal mapping passed; compiled scripts and inspected2final figures.
  Effective CX accuracy limitation retained; no new convergence/SOA closure.
- Report proposes separate low-N slew, high-P timing and reference-R tests
  after current probes, preserving sampling edges and checking shoot-through.
  All are proposals only. Scoped diff reviewed for task-only local commit;
  unrelated Obsidian and10-bit changes preserved.

## 2026-10-24 — Start full native stress repair; remote access interrupted

- User authorized current stress repair plus digital-source clarification.
  New sar8_stress_closure target isolated from historical runs and user work.
  PDK/model hashes and native Spectre21.1 license passed via SSH; bridge tunnel
  initially down. No OA/PDK mutations or baseline promotion.
- Four200ns strict CX cases submitted once, cold/hot null vs native Rgate/4
  using parallel existing PDK resistors. No MOS geometry or source timing edits,
  no ideal keeper.1833MOS/10998terminal pairs/1073signals plus all32 reference
  switch four-terminal currents. Two concurrent jobs, four threads/job.
- Native cold baseline reached41.0583ns with CMI warnings, then independent
  SSH status timed out. Completion status unknown; no native jobs killed or
  duplicate submissions. Bridge startup did not confirm CIW connectivity.
- Digital audit confirms project-defined CMOS hierarchy using nch/pch_mac,
  rupolym and cfmom_2t, not standard digital cells. Native physical RC delay.
- Hash/invariant/probe coverage audits and compile/import checks passed.
  New waveform/current extraction, repair benefit, all-device SOA, full PVT,
  full-code/FFT and OA synchronization remain unverified. Plan stays incomplete.
- Scoped checkpoint commit only, no push. Preserve all Obsidian/10-bit dirt.

## 2026-10-24 — Network-restored recovery attempt; target reads still blocked

- Resumed exact four sar8_stress_closure jobs without resubmission. Jump SSH
  hostname succeeds; target authentication and delayed hostname succeed.
  Inherited30s status failed; isolated90s status deadline also expired.
- Added read-only direct SSH inspector with file-backed output and bounded90s
  deadline, avoiding login-shell and captured-pipe ambiguity. Both Python status
  and plain /bin/cat first exit_code timed out. SCP/SFTP returned no data;
  stopped only this attempt's local probe wrappers, no remote simulation.
- Jump-host same result path returned ENOENT, not a usable shared mount.
  Target session/resource/filesystem cause unconfirmed; no new native results,
  circuit changes, waveform overwrites, OA edits or repair qualification.
- Updated access evidence and incomplete plan; scripts compile, scoped diff
  checks pass. Task-only local diagnostic checkpoint, no push. User dirt intact.

## 2026-10-24 — Partial cold logs recovered; waveform retrieval blocked

- Successful direct snapshot confirmed rg4 cold native exit0,0errors/58warnings;
  rg1 cold post-transient summary and two measurement rows without exit marker;
  hot logs/exit markers absent. Current hot process state remains unknown.
- Subsequent90/180s direct queries,90s reducer prerequisite and90s SFTP log read
  timed out. Authentication works. Interactive SSH gave login banner but no
  shell-command result; closed only that probe. No raw writes, reducers launched,
  simulation restarts/termination or OA edits. Requested existing-terminal check.
- Log-only baseline codes243/12 agree with ideal +/-0.81V; held errors at
  41.8/141.8ns are-1.695/+0.577mV; conversion26.683/26.644ns is NOT settling time.
  Both cold tails show effective reltol1e-7,maxstep10ps,V/I abstol10nV/100fA.
  Enhanced stress/codes/settling comparison and all hot results still missing.
- Preserved snapshot, partial metrics and bounded file-backed recovery probes.
  Scoped script/JSON/diff validation; task-only checkpoint commit, no push.
  No circuit changes, baseline promotion or completion claim; user dirt preserved.

## 2026-10-24 — Reclaim verified remote historical waveforms

- User explicitly requested old remote waveform cleanup after memory pressure.
  Connection recovered. Read-only snapshot: home is NFS98% used, not tmpfs;
  available RAM~21GiB, SwapFree~87MiB, no user Spectre processes. No claim that
  stored waveforms explain the server's anonymous-memory use.
- New bounded cleanup plan owns14 exact historical raw files:10 reference-gate
  control scans and4 symmetric-hold cases. Checked local retained-result hashes,
  native completion/reduction markers, remote deck hashes, size/uid/inode/path,
  and active use; no candidate references. sshd/zombie exclusions recorded.
- Permanently removed only14 tran_perf.tran.tran files (16.272GiB allocated).
  Immediate shared-filesystem available space increased16.262GiB. Verified all
  absent and sources/logs/reduced outputs preserved. Full raw restoration requires
  rerun for unretained signals; final baselines and current experiments untouched.
- Protected four stress_closure cases now all exit0 and retain94,869,661,741bytes
  raw waveforms. No analysis/overvoltage pass inferred; no bulk load/download or
  new simulation. RAM/SWAP issue not resolved by this disk cleanup.
- Compiled maintenance script and validated manifest/scoped diff. Task-only local
  cleanup commit, no push, no OA/PDK/process/user-file modifications.

## 2026-10-25 — Sequential low-memory four-case recovery and comparison

- Recovered existing cold baseline/Rgate-quarter before hot pair. No Spectre
  launches, raw deletions, baseline promotion or OA/PDK edits. All native exit0
  and tran PASS; four capped512MiB workers ran one at a time. C++ parser peakRSS
  7540KiB each; all94.87GB source PSF preserved,0.755GB selected compressed waves
  transferred. Local memory-mapped analysis retains original time resolution.
- Validated sparse/GROUP1 fixture,1,200,097 samples/END/200ns/accepted-step counts,
  source deck hashes/raw stat identity, transfer SHA256, all10998 MOS terminal
  pairs and192 reference-pair waveform crosschecks per case. Independent native
  DUT diff confirms only320 PDK-resistor multiplier lines per pair changed.
- Cold reference peak1.05094→1.06561V and bottom-56.94→-75.61mV; hot1.05503→1.07207V
  and-45.03→-82.07mV. New hot hotspot BP3 follows RST7, VREFN positive26.40mV at
  the negative bottom peak. Rgate/4 improves max nominal-bottom settling by~50ps
  but worsens peak stress; do not promote it as a repair. Other-block stress persists.
- Each case14/14 updates settles inside1.7578mV before next compare; codes243/12,
  timing/idle checks pass, sampling edges/windows unchanged within0.001ps. Cold
  startup preclose error~1.978mV separately retained;200ns/two inputs is not full
  PVT/static/FFT/SOA closure. Actual CX reltol1e-7/maxstep10ps matches across pairs.
- Original lowercased save list invalidated requested MOS currents. Required
  voltages survived via allpub; current/charge attribution remains unavailable.
  No new simulation to fill this gap during recovery. Updated access_state and
  incomplete repair plan, report, four visually checked plots and compact metrics.
- Scripts compile, parser/pulse/settling fixtures and scoped diff checks pass.
  Protected Obsidian/10-bit/new management registry dirt unchanged; pre-existing
  Obsidian whitespace excluded. Task-only local commit; no push.

## 2026-10-25 — Register local sources, remote runs and live Virtuoso metadata

- Implemented management/project.yaml, designs.yaml, cells.yaml, historical run
  index and four active immutable-input snapshots. Added source/output/server
  inventories, discrepancy list, human status/usage pages and read-only CLI.
  Root README/AGENTS now point to the registry and distinguish legacy manifests.
- Recovered local Bridge tunnel after the user's graphical connection returned.
  Live t28_io CIW confirms SAR_ADC_T28 path and tsmcN28 binding,41 visible
  libraries,247 project cells (232schematic/183symbol/15VerilogA views).
  Registered119 actual cells omitted by legacy manifest;15 legacy entries absent.
- Supported schematic reader traversed68 unique project cells for R3/R4 and
  both TBs; closure counts35/41/36/42, no errors. This is dependency evidence,
  not an OA/netlist-equivalence or circuit-validation claim. No OA writes.
- Latest bounded low-priority server census observes256 exact references and60
  shallow directories,144 recorded references currently missing. Preserves
  historical/unknown states and separates other libraries and bridge runtime.
  No raw-waveform contents read, no simulation, deletion, move or user-process kill.
- Registered current four stream-analysis results and rejected Rgate/4 repair
  status from existing report. Independent stress/current-probe tasks,10-bit
  work and user Obsidian edits remain untouched; source counts stamped separately.
- Five focused fixtures, compile, registry source/recipe/uniqueness/dependency/link
  checks and scoped diff passed. Policy defaults are declared; legacy submitter
  enforcement, SSD allocation and WORK-library creation remain subsequent work.
  Scoped registration commit only, no push.

## 2026-10-25 — Unified SSD execution, collection and resource admission

- Added project.py register/submit/run-status/gate/analyze/collect and read-only
  legacy-collect; immutable input manifests, idempotent launch locks, fresh
  host+cgroup/swap/quota/load/disk admission and detached queue workers.
- Verified /server_local_ssd/chenzc_intern25/sar-adc-t28: uid596,0700,XFS,
  retained write/read probe, mapped local block device ROTA0. Raw remains SSD
  scratch: no administrator retention/backup guarantee established. OA/PDK and
  historical data untouched; no WORK-library creation or old-process kill.
- Implemented one heavy job at a time,<=4 Spectre threads, nice/idle I/O,
  per-process AS/file limits and group-RSS/time/output/disk watchdogs. Stop only
  verified new children; preserve failed partial output and unknown connection
  outcomes. Not host-wide sandboxing. Disabled staged/idle new batch launch;
  preserve historical recovery and already-uploaded jobs.
- Native RC smoke queued behind existing independent Spectre, then completed.
  Final double-client launch starts one worker only; repeat submission retains
  child identity. Exit0/PASS, no warnings,159 points/10ns, Vout0.9998787915V;
  native peak75.59MiB, streaming summary5.93MiB. +mt4 requested but Spectre
  disables threading for the tiny circuit. This validates workflow, not ADC.
- Two collections matched15561bytes with SHA256; impossible1TiB gate-only request
  refused. Historical rg4 cold small evidence copied read-only60862bytes to a new
  ignored local directory, no raw download.15 focused fixtures, compile,
  registry/link/input-hash and scoped diff checks pass. Later worker PID-group
  and exception-cleanup hardening covered by fixtures/Python2 loading; native
  smoke agent revision separately recorded, not silently relabeled.
- Fixed csh multiline RPC encoding, Python2 UTF8 probe decoding, and bounded
  Windows atomic-snapshot rename contention found in tests. Updated usage,
  source/server/run inventory and status. User Obsidian,10-bit and independent
  current-probe changes remain outside this commit. No deletion or push;
  scoped local commit under plan/2026-10-25-managed-execution.

## 2026-10-25 — Measure baseline reference currents without changing the circuit

- Scope: original Rgate/Mmain2um/refL90 FF cold/hot baselines only; no OA, PDK,
  DUT, timing, supply or monitor changes. Source hashes and reversible save-only
  deck transform checked. Existing raw and user Obsidian/10-bit work preserved.
- Diagnosed invalid lowercase save names and native automatic allpub fallback.
  One0.2ns smoke validates228 terminal saves; full200ns cases save232 currents
  plus130 voltages, subcktiprobes/useprobes=no. Extended task-owned PSF parser
  for current TRACE PROP units; sparse fixture and sign/KCL checks pass.
- Both native runs exit0/PASS,319432/282775 points; same1609 nodes/1833 MOS.
  Sequential4-thread native peaks321/318MiB; bounded streaming parser~6.5MiB.
  New raw9.67GB retained, hashes/stat identities checked, no cleanup or rerun.
- GNN4 peaks1.050940/1.055035V: MOS gate returns9.717/9.850uA through Rgate to
  driver while its command remains unchanged. CDAC/source network coupling,
  not a logic command to drive above VDD, is supported by terminal currents.
- BP7 minimum-56.939/-45.028mV forms in two stages. High-PMOS GP fall removes
  additional5.142/3.556fC while low NMOS replenishes0.500/0.159fC in that interval.
  Corrects the earlier low-side-only hypothesis. Idle BP3-27.090/-35.803mV is
  instead CDAC coupling during bit7 reset, with low-side replenishment.
- KCL residual including reference rails<90pA; common-voltage interpolation
  differences79.13uV cold/0.000832uV hot, critical peaks within1uV and sampling
  edges within0.001ps of original. Codes243/12, event counts8/8/8/16,14/14
  settling windows pass; max settling2.217/2.379ns. No overvoltage repair,
  internal channel/overlap-charge decomposition or reliability signoff claimed.
- Report, six visually reviewed layered plots, manifests, receipts, metrics
  and additive run registry added. Shared commits657f5b6/b6da655 preserved.
  On review of new managed policy, jobs/reductions were already complete;
  disabled task-specific launch/reduce for future jobs, kept bounded read-only
  recovery. New jobs must use managed SSD execution.
- Compile, frozen-input checks, parser fixture, complete-case validation and
  scoped diff checks passed. Task-only local commit; no push.

### 2026-10-25 Physical gate charge buffer candidate

- User requested complete repair. Opened bounded physical-stress repair plan;
  first candidate only, overall repair remains incomplete pending supply-contract
  choice. No OA or adopted baseline changes, no PDK changes or limit relaxation.
- Managed SSD run sar8fix-c1r4-ffcold: original1833 MOS unchanged, gate resistor
  parallel count x4 plus32 PDK MOM instances/1020 units (~4.084pF). Same FF0.99V,
  -40C, 200ns, finite reference network and external sample window.
- Native exit0/PASS and managed analysis complete;318574 native samples,
  all10998 MOS pairs screened. Codes243/12, counts8/8/8/16. GNN4 peak0.999016V,
  BP7 min-40.632mV, reference worst1.030632V: improvement, NOT closure.
  Driver/comparator/digital stress remains; candidate not promoted.
- Compact10ps-minimum export used only for plots and timing estimates, not exact
  timing signoff. All native points used for stress; narrow-spike parser fixture
  proves unexported peaks retained. Frozen inputs,14 collected files and native
  step count checked. Native DC tolerance-relaxation warning retained.
- Simulation/analysis733/147s; process-group peak323/110MiB, parser7.2MiB.
  New raw retained remotely;20.11MB collected, no skipped files. Early live
  collection checksum conflict resolved by collection-only retry after completion;
  receipt hashes select versioned logs instead of the earlier START snapshot.
- Report and three-panel comparison reviewed, broader supply decision requested;
  no further simulation queued. User Obsidian/independent10-bit work preserved.
  Targeted validation and scoped diff check; task-only checkpoint commit, no push.

## 2026-10-25 — Historical data cleanup proposal for human review

- Created management/cleanup/2026-10-25/review.md and exact JSON evidence, with
  separate local/server tables, experiment labels, observed sizes, retained
  copies and approval-pending file targets. Added a management navigation link.
- Read-only bounded census: local128 generated roots/files99.715GiB; server102
  present non-overlapping roots205.948GiB and72 missing registered roots. Added
  exact project-cell matches in known ADE simulation parents; unknown projects,
  OA/PDK, environments, Git and user source/Obsidian data excluded. No raw reads.
- Proposed local transmission parts2.639GiB and optional staged/idle native
  mirrors32.435GiB; server transmission gzip/parts10.913GiB.36 literal targets,
  five proposals, all pending. Matching size/case and historical receipts are
  not fresh SHA verification; full hashes and usage checks required after approval.
- Keep the90.075GiB stress comparison,11.926GiB current-probe evidence and new
  physical-repair/corner probes, including observed live natscreen-sscold job.
  Server natives backing optional local removal are required retained paths;
  preserved reduced.json.gz is not treated as a disposable generic gzip cache.
- Five focused tests, arithmetic/containment/no-last-copy-conflict checks,
  JSON/links, compile and scoped diff passed. No deletion/move/compression,
  simulation, remote writes, process kills or OA mutations. Independent active
  physical-repair and user10-bit/Obsidian edits remain outside this commit.
  Scoped local review commit, no push; user remains responsible for next approval.

## 2026-10-25 Fixed-supply native device feasibility checkpoint

- User confirmed 0.81–0.99V must remain; physical circuits/tolerant devices are
  authorized. Recorded in active physical-stress-repair plan; no voltage or
  external sample contract changes. Native Spectre used, not EVAS transistor
  substitution. Read-only CDF audit; no OA/PDK mutation.
- Completed13 managed small block simulations/analyses: core vs IO/UD12 five
  PVT points, SS cold hybrid short/long windows, native-NMOS short screen and
  five long-window PVT points. All original ADC candidates/raw remain intact.
- Reference IO scale2 passes standalone settling, not full-CDAC closure. Direct
  IO and first hybrid comparators fail SS timing; native-NMOS N4 resolves both
  signs at VCM.45V in all five extended-window tests, worst2.820ns and maximum
  pair1.152V. No claim of ADC repair, integrated timing, power, noise or mismatch.
- Local window-shadowing measurement bug fixed, all analyses regenerated and
  checked for identical windows/persistent decisions/Ron multiplicity. Native
  full-point streams/steps and169 collected hashes checked;322993 samples,
  97.71MB collected. Peak simulation293.3MiB/analysis115.5MiB; actual native
  single-thread. A premature analysis request was refused, then same ID retried
  after simulation completion; no duplicate simulation or analysis.
- Existing report updated under write-page clarity guidance with three reviewed
  comparison figures and explicit fixture limits.13 per-run receipts and batch
  verification retained. No background work remains; repair plan stays active.
- Concurrent cleanup-review commit c802f73, user Obsidian and independent10-bit
  changes preserved. Task-only local checkpoint commit; no push, no cleanup.

## 2026-10-25 Approved duplicate cleanup and home metadata inspection

- Human approved five proposals L-A1/L-B1/L-B2/S-A1/S-A2 from immutable review
  c802f73. Deleted21 exact local files35.074GiB and15 exact remote transfer
  files10.913GiB, no directories. Native PowerShell LiteralPath locally,
  exact unlink remotely; intent/outcome journals and final absence readback.
- Full SHA256 of21 local and25 server files; ten native pairs identical,
  eleven chunks/historical aggregate verified, four gzip payloads verified
  against native lengths/SHA/END. Managed heavy-work lock/admission, nice/idle
  IO, single streaming worker peak17,904KiB; no new Spectre simulation.
- All ten server-native PSFs retained unchanged. Local free delta35.074GiB;
  same server filesystem free delta10.914GiB, not summed per path. Permanent
  duplicate removal; local recovery via retained natives. Old/tmp storage
  still a retention risk, not silently migrated or claimed as durable backup.
- Read-only own-home434-entry metadata audit:317 *.ahdlSimDB directories
  120.48MiB,62 top-level files8.99MiB, multiple live Cadence logs/.nfs files,
  literal $D/$DST engineering-like folders. No home deletion/moving, startup
  changes, credential contents, other users' data, process kills or OA edits.
- Original approved-source CRLF hash guard initially refused before mutation;
  compared canonical Git LF bytes. Home cache sizing128MiB AS helper failed,
  read-only256MiB/core0 retry succeeded; final home snapshot contains no core.
- Added execution/home report, receipts, guarded one-time helper and9 focused
  tests. Updated inventories/run retention and persistent cleanup navigation;
  independently committed053ec7f physical repair and user Obsidian/10-bit
  changes preserved. No baseline adoption or last-copy deletion.
- JSON/links, compile, PowerShell parse, registry validation and scoped diff;
  local task-only commit, no push. Original review JSON remains unchanged.

## 2026-10-25 Old home compilation cache cleanup queued

- User authorized old unused compilation artifacts, not raw/source/log/OA/PDK
  removal. Frozen317 exact top-level own-home *.ahdlSimDB names;316 match
  project deck basenames.308 directories/3340 generated files116.883MiB are
  eligible; six generic names and three recent caches retained. No other home
  data or current per-run SSD cache is targeted. Full metadata kept on SSD and
  ignored transport; concise origin/eligibility evidence tracked.
- Inspected cwd/open descriptors/mappings/commands of own-user processes.
  Initial conservative audit stopped on zombies and ptrace-protected SSH;
  diagnosed exact process roles and recorded narrow non-simulation exclusions.
  Other unknown live processes remain fail-closed. No live cache refs observed.
- Existing loaded-reference Spectre retains managed workload lock; initial
  delete request correctly deferred. One idempotent nice/256MiB maintenance
  worker queued (submission PID25034), waits up to2h and rechecks before exact
  unlink/empty-rmdir. No process kills, resource bypass or duplicate simulation.
  Actual deletion NOT YET VERIFIED at checkpoint; no freed-space claim.
- New guarded helper/client and9 focused tests: path, owner/symlink, age,
  generic/unknown provenance, changed metadata, process refs, duplicate queue
  and exact-tree deletion preserving sibling source. Python compile/JSON and
  scoped diff checks; local task-only checkpoint, no push. User Obsidian,
  independent10-bit and concurrent loaded-block repair files preserved.
- Recovery uses scripts/management/home_cache_cleanup.py collect; remote
  journal/status is authoritative. Permanent cache removal is regenerable
  from retained sources, not restoration from a recycle bin. No cache-policy
  or global startup/environment changes in this task.

## 2026-10-25 Home cache cleanup completion readback

- Recovered the existing worker, no relaunch or new deletion:308 exact cache
  directories/3340 files deleted_verified, nine deliberately retained, no
  partial failure or additional skipped candidate. Worker completed in23.168s
  after normal workload-lock admission. Final helper readback verifies all308
  absent and all nine retained paths present.
- Fresh own-home read-only census:434 to126 top-level entries (64 directories,
  62 ordinary files). Exactly nine .ahdlSimDB remain,3,770,798 bytes3.596MiB:
  six generic-name caches and passive_ac01/pilot_aps/sar_aps_probe kept because
  recent at the frozen audit. No second-round deletion inferred from this
  status request. Original sources, waveforms, logs, OA/PDK and current caches
  outside the removal scope.
- Deleted logical bytes122,560,920 (116.883MiB), allocated blocks129,019,904
  (123.043MiB). Whole-home-filesystem free change during deletion was
  -100,663,296 bytes (-96MiB), NOT a positive net gain. Concurrent filesystem
  activity/accounting prevents equating that net delta with file removal;
  both measures preserved in receipts and home_remaining.json.
- Collected complete status/receipt/fresh verification; updated summary and
  completed the cleanup plan. JSON/arithmetic/retained names/per-file status
  and scoped diff checks passed. No circuit/simulation/process changes.
  Concurrent loaded-block reports, experiments and user notes/10-bit work
  preserved. Task-only local completion commit, no push.

## 2026-10-25 Home top-level inactive-file archive

- User authorized archival, not deletion, of inactive top-level home logs and
  historical simulation artifacts. Two-observation metadata and own-process
  FD/maps/cwd/command audit,1h inactivity, sidecar/type/owner/link guards and
  streaming SHA256 selected12 files: seven stopped logs and five *.scs.*.srf,
  total2,506,077 bytes. Six active logs and all locks/configs/engineering dirs,
  hidden data and nine preserved caches left in place.
- Archived to /home/chenzc_intern25/archive/home-top-2026-10-25/{logs,simulation}
  on the same filesystem; archive manifest records exact original/recovery
  paths, hashes and identities. Exclusive own maintenance lock, no-overwrite
  link then verified source-name removal; at least one verified copy always
  present. No overwrite, compression, file-data deletion or space-release claim.
- All12 archived hashes/identities/nlink1 and source absence verified. Protected
  metadata changes empty; final visible-name set exactly original minus12 plus
  archive. Ordinary ls51 to40 entries, hidden75 unchanged, total126 to115.
  Added complete remaining.txt plus JSON/audit/operation/readback evidence and
  management navigation/retention registration. Logs with unknown experiment
  provenance remain tool-level archives, not relabelled as qualified SAR results.
- Seven focused guard/collision/new-use/idempotence/exact-move tests, Python
  compile, JSON/arithmetic/name-set/metadata/hash and scoped diff checks passed.
  No new simulation/heavy analysis, queue bypass, process kills or OA mutation.
  User Obsidian/independent10-bit and concurrent loaded-block repair changes
  preserved. Task-only local completion commit; no push.

## 2026-10-25 Tolerant reference and comparator real-load checkpoint

- Preserved external0.81–0.99V contract, original input/reference50ohm networks,
  actual CDAC/MOM/controller load and sample sources. No OA changes or baseline
  adoption. Cleanup commits14b9446/98bc95c/19ae72f and unrelated user notes/10-bit
  files untouched. Own code/report updates use the active physical-repair plan.
- Completed managed strict reference-only FF cold, unchanged SS cold baseline,
  comparator-only SS cold, and identical reference numerical-control runs.
  Native exit0/PASS,200ns/END,1015 saved traces/10998 MOS pairs, all frozen and
  collected SHA256 checked. Native events and V*I integration; compact20ps
  display and gate-charge estimates explicitly separated. Synthetic sparse
  GROUP/PROP parser, hidden-spike and frame-split integration tests pass.
- ReferenceIO scale2 gives243/12, passes its1.98V class screen, but BP7 down to
  -82.31mV. All14 settling deadlines pass; second-frame power173.597uW.
  Unchanged core driver/comparator/control still exceed.99V. Not repaired.
- N4 real load gives243/12, second-frame44.102ns, held+.338mV, final reference
  reset197.366ns, power102.527uW. SS-cold all-pair screen passes. Larger input
  charge/kickback and reduced raw output high(.403V at last write) retained as
  risks; no rail-to-rail diagnostic threshold substituted for actual receiver.
  Startup DC frame is not a real power-ramp reset test. Original first241 remains.
- Numerical screen(actual1e-5 versus1e-7 strict) fails predeclared peak delta
  gate:1.004mV versus0.1mV. Same codes do not justify relaxed PVT settings.
- Registered/submitted strict combined five-corner batch and separate N4
  PMOS-latch2->4 SS-cold single-variable control, all unique frozen IDs.
  Managed single-worker queue; no duplicate simulations or raw downloads.
  One-shot local continuations request managed analysis then verified collection
  and local metrics; this is not a new recurring automation. Runs are ongoing,
  results not yet reviewed, overall repair remains INCOMPLETE.
- Controlled small circuit seed and observer archived, three original loaded
  inputs reproducible; no PDK content or raw waveforms staged. Reference,
  comparator and reset figures visually inspected. Python compile and scoped
  diff checks performed; unrelated pre-existing Obsidian trailing whitespace
  left untouched. Task-only local checkpoint commit, no push.

## 2026-10-25 Loaded PVT and tolerant receiver continuation

- Reviewed all five combined IO-reference/N4 PVT cases and the PMOS-latch x2
  control. Native/analysis exit0, frozen inputs and collected SHA256 verified;
  all cases1833 MOS/10998 pairs and native event/energy reduction. No OA edits,
  baseline promotion, raw deletion or push; unrelated Obsidian/10-bit and cleanup
  commit85378b3 preserved.
- Combined reference/comparator classes pass their screens at all five corners;
  original core receivers fail TT8 pairs, broad core driver/control fail FF.
  SS-hot first242 versus243 remains. PMOS doubling improves late output but not
  output at actual write; do not adopt. Summary/interface/startup plots reviewed.
- Four-MOS ordinaryIO receiving-inverter control completes TT and SS cold:
  both243/12,8/8/8/16 events per frame,14 settling windows,0 failed pairs.
  TT second conversion34.09475ns,power144.880uW (previous8 failing pairs).
  SS cold47.38843ns,power103.960uW. Sample close deltas<.001ps, window<.005ps;
  no meaningful sample-window change. These are bounded tests, not whole closure.
- Corrected reset measurement to follow fixed preset targets across nominal
  frame boundaries, using native0.5VDD control crossings and compact20ps settling
  estimates. SS-cold rx2 first reset100.75664ns, settled101.82129ns, actual sample
 103.32164ns,margin1.50035ns. Missing second reset after200ns remains unknown,
  not a pass/failure inferred from a truncated record. Existing SS-cold control
  reanalysis verifies observed first margin4.719ns and unknown unobserved tail.
- Input-order-only SS-hot control has identical DUT SHA:13/243 rather than
  expected12/243; first held+9.96584mV, second-.282829mV. High-side gate.763109V
  initially and1.656871V after precharge. Supports DC-start/no-precharge issue
  rather than one physical side. Native initial DC relaxation warning retained;
  no POR repair or discarded first-code claim. Polarity comparison plot checked.
- Tiny managed four-device intentional-overbias probe verifies native UD12
  CMI thresholds1.32V for both polarities/all6pairs,24,716bytes collected with
  hashes. No PDK mutation or model copying; metadata probe is not ADC operation
  or foundry lifetime signoff. Existing SS FO4 speed cost remains a design risk.
- Submitted immutable rx2-end210 and rx1-end210 SS-cold cases. The first changes
  observation duration only; second halves ONLY4 receiving-device multiplicities.
  Verified identical sources, corresponding DUT hashes/delta counts,200ns input
  reproduction, Python compile and scoped diff checks. Single-worker gate;
  one-shot continuation analyzes/collects named cases, never resubmits them.
  Receiver half-size case running, unchanged-size tail case queued at checkpoint.
- Report retains chronological evidence and leads with current incomplete state.
  Only task-owned checkpoint sources/results staged; follow-up tail results and
  remaining FF/control/startup/performance work stay active. Local commit only.


### 2026-10-27 — Local SAR ADC document and artifact hygiene

User requested cleanup of obsolete SAR_ADC products and documentation. Archived
only the former root README and docs/project_status navigation, preserving their
historical text and rebasing Markdown links. New root and docs index distinguish
manual ADC, ongoing module audits, preserved R3/R4 references, early 10-bit 5+5
and independent cdac10 work; catalog covers all 84 engineering reports. Fixed
navigation to the user's existing Obsidian Rvision/Head.md without moving notes.

Removed 369 individually verified ignored Python/pytest cache files, 4,499,577 B;
exact inventory and receipt: management/cleanup/2026-10-27/. Local output census
was 73,293,228,421 B (68.260 GiB), not removable space. Preserved all raw waveform,
reduced/pickle/log/failure evidence, unresolved plans, dirty work and protected
active caches. No remote access, OA/PDK/circuit change, run launch or adoption.

Validation: exact archived text with recorded link transformations, all new
local links and catalog coverage, JSON, cache absence, protected source hashes,
retained generated-file metadata and original log prefix; git diff --check.
Machine results are in the cleanup validation.json. Scoped local commit only,
excluding other owners' changes; no push.

Concurrent observation: the manual ADC owner updated its implementation plan
with new behavioral-authoring scope during this cleanup. Recorded its exact
before/after hashes; excluded it from unchanged-file counts and from staging.
All other protected source records and retained generated-file metadata are
checked independently. No cleanup operation wrote that plan.
