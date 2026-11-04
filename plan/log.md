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

## 2026-10-25 — Coordinated block-level audit

- User requested four forked module sessions and parent coordination. Read their
  two audit rounds; parent rechecked conversion settling target generation,
  historical comparator statistics report and observer timing definitions.
- Confirmed a measurement coverage gap, not an observed wrong-code mapping:
  conversion settling uses measured gate levels as target; fixed reset-target
  checks are separate. Historical comparator dynamic mismatch statistics do not
  qualify the new N4 and must not be treated as per-cycle noise.
- Created plan/2026-10-25-sar8-module-audit/plan.md with four disjoint local
  verification subtrees, parent-owned shared log, and no remote execution,
  circuit edits, commits or baseline adoption in this preparation phase.
- Assigned independent reference-state checks, event-table checks and two
  fixture specifications. Existing user dirty files and 210ns artifacts retained.
  No new simulation, OA change, push or deletion performed.

### 23:21 — Parent review during two-hour coordination

- Read all four third-round deliveries. Independently reran 26 oracle and 22
  event-tool tests (all pass); read-only replay reproduced the two-run/four-frame
  event JSON exactly with consumed input hashes verified. Parent separately
  verified all17 source-file hashes in each comparator/sampling fixture spec.
- Requested a correction before using the oracle on analog results: early D
  capture is an intermediate state, so mandatory full-rail analog settling at
  every early capture would invent a new design constraint. Require independent
  logical capture checks separately from declared late/reset settling windows.
- Assigned local-only comparator and sampling deck construction with unchanged
  DUT instances, exact cut/fanout audits and no remote submission. Control adds
  sampled-output-valid diagnostics where compact evidence supports it; unknown
  margins and native-vs-sampled limitations must remain explicit.
- User's autonomous window ends2026-10-26 01:09 Asia/Shanghai. Automation sar8
  active; no new simulations submitted, no commit/push or baseline/OA change.

### 23:32 — Corrected gates and rejected oversized extraction

- Parent reran34 revised reference tests and37 control tests; all pass. Logic
  capture correctness no longer implies intermediate analog full settling.
- Reviewed sampled DOUT results: TT frame2 matches final word at165.379ns before
  final write174.699ns; SS cold frame2 at175.687ns before187.873ns. Later unchanged
  bits explain why word matching is not conversion completion. Four legacy read
  windows have in-band samples, not proof against intersample glitches.
- Rejected sampling2506-device/1831MOS control-shell draft for remote execution;
  requested smaller extraction boundaries. No source circuit or old data changed.
  Requested bounded reference/control local reproduction specs; comparator deck
  preparation remains underway. No new native simulation or commit/push.

### 23:44 — Reduced fixture boundaries reviewed

- Comparator783-MOS proposal was paused; authorized local reduced receiver/write
  fixture with explicit diagnostic clock and real necessary register fanout.
- Reviewed sampling517-instance/169-MOS proposal and inspected frozen clock path.
  XIDLE sample-match branch is independent of ACTIVE; retaining that small branch
  can avoid inventing an unavailable QUAL replay. Exact output-edge/load agreement
  is still unmeasured and cannot be assumed from connectivity.
- Reviewed reference two-case spec and control34-MOS QUIET spec. Prioritized
  XDRV0 and requested bounded replay-data availability checks; rejected treating
  unavailable downstream gate-current replay as a prerequisite when real local
  load can be retained. No new native results, remote jobs, OA changes or commits.
- Scoped diff check passed; existing whitespace in user Obsidian file was left
  untouched. Four module sessions continue local preparation only.

### 23:56 — Diagnostic decks reviewed; native preflight healthy

- Parent reran comparator12 and sampling13 structural tests, all pass. Reviewed
  comparator v2 ideal-input TT/SS-cold decks and sampling compact_v2 SS-hot
  short/long-history decks. No Spectre compilation or electrical pass yet.
- Assigned only missing bounded native measurement packages to those two teams:
  all-MOS stress, actual events and power/charge observables; no new framework or
  remote submission by children. Exact managed run ownership will be added after
  measurement review, before register/submit.
- Bridge0.8.0 t28_io reports tunnel/CIW/Spectre21.1 healthy, expected thu-wei user
  and llm_IO workdir. Managed status confirms old rx2-end210-sscold simulation and
  analysis complete. Its historical resource snapshot is not current admission.
- Reference found required voltage traces saved in old raw but absent from compact
  export; missing original device-current saves cannot be reconstructed. Control
  prefers real buffer/load over unavailable gate-current replay. Neither fault
  has a new isolated reproduction result. No OA mutation, new run or commit.

### 00:02 — First isolated sampling pair dispatched

- Parent reran9 stream-package tests and byte-for-byte rebuild check. Reviewed
  237MOS/1422 six-pair records, actual clock event coverage and held/preclose
  measurement definitions; frozen original compact deck devices unchanged.
- Registered and submitted sar8audit-sample-v2-short and -long through managed
  entry. Short admitted/running, observedRSS313434112bytes; long queued behind it
  with existing_simulation_or_analysis reason. No bypass or parallel heavy job.
- Initial short gate observed21.96GB host MemAvailable, no swap traffic and no
  conflicting workload. Runtime limits remain1024MiB simulation/256MiB analysis,
  4threads,32MiB collection. This snapshot is not a future resource guarantee.
- No electrical conclusion until native completion and independent review.
  Original zero-precharge failure is not replaced by the short-low diagnostic.
  Comparator package still being prepared; reference/control await exact replay
  data and have no new run authorization. No OA change, baseline adoption or push.

### 00:04 — Sampling native completion; comparator pair dispatched

- Sampling short/long native runs completed with exit0 and zero-error footer,
  elapsed39.26/37.36s, peakRSS315035648/314994688bytes. Native warnings SFE-1131,
  SFE-2453 and VACOMP-2435 remain for log review. Effective reltol is1e-7 despite
  deck request1e-6; maxstep10ps, gear2only. No speed/equal-accuracy claim made.
- Both sampling analyses submitted to the same managed serial queue; no result
  collected or electrical verdict inferred yet.
- Parent reviewed comparator reducer additions (native write/clock snapshots,
  reset-level crossings, full260ns energy integration) and reran5 package tests.
  Registered/submitted sar8audit-comp-d2-tt and -sscold. TT admitted, SS queued.
  Exact inputs frozen; child told not to edit them or submit new jobs.
- These four module diagnostics do not modify the ADC baseline or demonstrate
  integrated PVT qualification. Reference/control historical replay gap remains.

### 00:14 — Four cases collected; sampling history anomaly isolated for review

- All four native simulations and analyses completed exit0. Collected sequentially:
  sample-short13854191bytes, sample-long13831448bytes, comp-TT2007296bytes,
  comp-SS-cold2004299bytes; each below32MiB, no skipped files. Native raw remains
  remote. Maximum observed analysisRSS150241280bytes stays below256MiB.
- Sampling native stress0/1422 in both cases, but accuracy differs drastically.
  Short opens103.110617ns/closes141.154911ns; held141.8ns error+797.453534mV.
  Long opens103.117169ns/closes141.155154ns; preclose error+.000895mV and held
  error+.279027mV. Analog values are compact interpolation, not native peak data.
  Both opening events exist; no missing-edge assumption explains the difference.
  Assigned source/initial-state/charge-path diagnosis before any modification.
- Comparator TT shows6 writes with expected polarity/D0 and precompare90% reset
  observations; stress0/2802, VDD energy2.189795pJ over260ns. TT/SS full review and
  plots assigned to comparator session, not an integrated timing/PVT pass claim.
- Native logs retain repeated PDK scale-option and obsolete environment warnings;
  sampling also reports explicit global/formal-node shadowing. No warning is
  silently removed. Comparator actually disables multithreading due to small
  size, despite requested4threads. No new job or circuit revision in this turn.

### 00:25 — Parent causal review; finite-history follow-up preparation

- Read both module result reports and inspected both final timing figures.
  Sampling short history has actualSEQ low2.155711ns, CbootP about0.179V before
  opening and mainG-input about-0.013V at110ns. Long equilibrium history has
  CbootP about0.810V before opening and mainG-input about+0.803V at110ns.
  Huge short error is already+796.709mV before closing; net turnoff change only
  about+0.745mV. Same-connection long result and normal short N-side support a
  P-side recovery-history explanation, not common supply/port wiring failure.
  This is not original integrated first-frame reproduction or a finite POR spec.
- Comparator native six-write checks match signs in TT and SS cold; first
  clock-to-write1.613/2.357ns, observed reset90 delay0.605/1.501ns. DATA lead
  about0.207/0.295ns on positive decisions is measured, not setup/hold approval.
  Asked comparator to finish checking TT simultaneous receiver-low excursion
  against already saved DONE/write events; no new simulation authorized.
- Approved only local preparation of sampling2/10/40ns finite external-low
  histories, same high-DC initial state and frozen formal101/141ns edges. Parent
  will review exact source deltas before assigning managed run IDs. No new
  remote job, OA mutation, circuit sizing, baseline adoption, commit or push.

### 00:33 — Finite-history sweep admitted; comparator review closed

- Parent reran6 finite-history checks, verified frozen measurement hashes and
  sole VSAMPLE-line differences, and confirmed healthy bridge0.8.0 t28_io to
  thu-wei/llm_IO/Spectre21.1. Registered/submitted low2,low10,low40 through the
  managed serial gate; exact paths approved in shared plan before registration.
  Initial gate had21.37GB MemAvailable, no swap traffic; queued cases remained
  behind the shared simulation/analysis lock. Queue timeout1800s, no gate bypass.
- low2 native simulation completed exit0/zero errors in40.53s, peak315179008B.
  Its analysis queued; low40 running and low10 queued at this observation. Queue
  does not promise FIFO; resource exclusivity, not case order, is required.
- Comparator final review reports TT PR/NR both low0.570–1.383ns after first
  clock edge. XOR-valid remains low in00 as in11; saved RAW,RAW_D,DEC,PHI_W each
  have exactly6 rising crossings, one per cycle, no duplicate/reset write at
  the observed half-VDD thresholds. Smaller analog pulses remain unqualified.
  TT207ps/SS295ps DATA lead is forward path difference, not measured DFF setup
  allowance. No further comparator design or native run assigned.
- Reference/control isolated overvoltage reproduction remains pending bounded
  native replay exports and load closure. Their specifications and independent
  checks are not circuit fixes. No whole-ADC/PVT qualification, OA change or push.

### 00:36 — Finite-history cases collected; recovery trend measured

- All3 finite-history simulations/analyses completed exit0. Simulation peakRSS
  low2/low10/low40=315179008/315310080/315330560B; analysis peak at most125575168B.
  Native effective reltol1e-7/maxstep10ps/gear2only; original SFE-1131,SFE-2453,
  VACOMP-2435 warnings retained. All3 native stress screens0/1422.
- Collected16 files each, respectively13868976/13871669/13869307B, noskipped.
  Parent independently rehashed all48 receipt-listed files successfully. Low2
  and low40 small transfers overlapped after tool yielded session IDs; their
  combined payload27.74MB stayed below32MiB, no raw downloaded. Both completed
  before low10 collection. Heavy simulation/analysis remained serialized.
- Parent reused frozen review_stream independently: low2 preclose+799.573216mV,
  held+800.336675mV; low10 preclose+701.789548mV,held+701.130927mV; low40
  preclose+.001543mV,held+.302817mV. Actual opening103.115071/103.115979/
  103.116897ns; closing141.154908/141.155132/141.155152ns. These are compact
  analog estimates with separate native edge evidence, not final ADC codes.
- Assigned sampling session independent initial-state/charge-path comparison
  and finite-history plot/report within existing ownership. 40ns is a working
  diagnostic point, not measured minimum POR time; no new circuit adjustment
  or native run authorized. All current managed jobs are complete.

### 00:43 — Four-module acceptance map and next cold control

- Parent viewed finite_history_rows.png and reviewed its sequential memory-map
  analysis. The source-reference error now follows the actual input reversal;
  no pre-reversal fixed-target error is used. Low10 shows delayed/weak gate drive
  and nonzero but insufficient acquisition current; it is not the same as
  low2's nearly absent main-switch conduction. All3 selected initial DC node
  values match the short control. EffectiveSEQ low durations are approximately
  4.060/12.061/42.062ns, not the external2/10/40ns plateaus.
- Added parent acceptance map to shared plan. Reference/control native replay
  and local current-measurement gaps remain explicit; comparator noise,
  kickback, common-mode/sensitivity and true setup/hold remain unqualified.
- Approved only local preparation of low40cold and longcold: change125C to
  -40C with SS/0.81V, all devices/loads/sources and formal edges otherwise
  unchanged. This tests finite recovery versus cold acquisition after equilibrium
  precharge. Parent still must approve exact run paths after source review.
- Rechecked bridge0.8.0 t28_io/thu-wei/llm_IO/Spectre21.1 healthy. No new native
  run this turn yet, no circuit/OA modification, no baseline promotion or push.

### 00:51 — Final isolated cold-control pair dispatched

- Parent inspected both temperature-only diffs and reran5 cold-control tests;
  source/measurement hashes remain fixed. Bridge preflight again confirmed
  expected0.8.0 t28_io/thu-wei/llm_IO/Spectre21.1. Approved exact low40cold and
  longcold recipe/run paths before registration. No OA or circuit sizing change.
- Both registered/submitted via managed serial gate. low40cold admitted,
  longcold queued behind its Spectre process. Gate observed20.53GB MemAvailable,
  swap_free0 but no swap traffic and sufficient cgroup headroom; policy allowed
  admission without overriding its checks. All prior seven cases complete.
- Queue timeout600s; simulation/analysis/collection remain1024/256/32MiB with
  max4threads. These two cases are the final native experiments in this window;
  only bounded result review/checkpoint follows. No whole-ADC regression/push.

### 00:55 — Both cold controls collected; equilibrium separates recovery failure

- low40cold/longcold simulation and analysis all complete exit0. Simulation
  peakRSS315072512/315150336B; analysis125554688/124964864B. Native temp=-40C,
  reltol1e-7/maxstep10ps/gear2only,4threads enabled in sampling log. Same7 warnings
  (SFE-2453,SFE-1131,VACOMP-2435) retained; stress0/1422 in both. Not PVT signoff.
- Sequentially collected16 files each,13885450/13854808B, no skipped/raw files.
  Parent independently rehashed all32 receipt-listed files successfully.
- Independent frozen review_stream yields low40cold preclose+13.693390mV,
  held+12.210887mV; longcold preclose+.054976mV,held+.306053mV. Actual close
  141.164708/141.164710ns, open103.323687/103.327132ns. The low-DC equilibrium
  control establishes this cold acquisition can work with adequate initial
  charge;40ns finite recovery remains inadequate in this specific history.
  Do not infer a universal minimum time or increase Mmain based only on this.
- Sampling session is reviewing charge/control/current waveforms and writing
  the final cold comparison/checkpoint. Nine native cases now complete with no
  in-flight managed work in this audit. No further experiments authorized.

### 2026-10-26 08:08 — User-return closeout

- User requested four-module progress/causes/open issues/next plan. Rechecked
  nine local collection receipts: all simulation/analysis complete with exit0,
  no skipped files. No new remote simulation or analysis started after window.
- Four module chats are inactive/notLoaded. Sampling's last cold-report turn is
  interrupted; final cold figure/report is not delivered. Parent numerical cold
  review and verified receipts remain available; prior plots remain intact.
- Paused only automation sar8 through app tool, preserving prompt/schedule/target.
  Pause was confirmed now, not at the original01:09 cutoff. No active module task
  needs interruption and no known in-flight audit job remains to kill.
- Shared plan records partial completion and remaining qualification gates.
  No circuit/PDK/OA/Obsidian/10bit change, new baseline, commit, push or deletion.

### 2026-10-26 — Coordination resumed without the former deadline

- User explicitly removed the two-hour limit. Updated the active audit plan and
  reactivated only heartbeat sar8 with the deadline removed and quiet unchanged
  polls. Electrical contracts and serial resource limits remain unchanged.
- Sampling resumes the interrupted cold report, then may locally prepare a
  finite60ns cold-history diagnostic matching the normal low-phase duration;
  this is not approval to change external sampling edges. Reference/control
  prepare native boundary exporters in their exclusive subtrees. Comparator
  performs a read-only cross-review of the parent's managed-runner extension.
- Bridge tunnel was initially down; normal start restored bridge0.8.0 t28_io,
  matching thu-wei/chenzc_intern25/llm_IO CIW and Spectre21.1. Both source runs
  sar8fix-loaded-ref-ffcold and sar8fix-loaded-both-ffcold remain complete.
- Added local analysis-only source-run support to the managed runner so saved
  native traces can be recovered without dummy simulations or overwriting old
  outputs. Fixed a local variable collision found by its registration test;
  all18 focused tests now pass. Cross-review and exact exporter review remain
  required before registration/execution. No new remote heavy job launched yet.
- Parent visually inspected the new sampling cold/hot comparison and read its
  measurement script; the report is still being finished. No circuit, PDK, OA,
  user Obsidian or independent10bit edits; no commit/push/deletion.

### 2026-10-26 — Finite60ns SS-cold diagnostic collected

- Approved and ran only sar8audit-sample-v2-low60cold through managed serial
  registration/submission/analysis/collection. One source-history falling edge
  changed; formal sample101–141ns, closing edge, geometry and load remain fixed.
- Native simulation40.65s, peakRSS315,015,168B; analysis13.22s,
  peakRSS124,936,192B. Collected16 files/13,883,806B with no skipped files.
  Simulation/analysis exit0 and native PASS; existing SFE1131/SFE2453/VACOMP2435
  warnings remain. No CMI stress failure:0/1422 MOS terminal-pair checks across
  22,802 native timepoints. This is a stress screen, not lifetime qualification.
- Parent bounded read: SEQ open103.323692816ns/close141.164709913ns;
  preclose140.964709913ns error+.119668106mV, held141.8ns error+.361995159mV,
  net turnoff interval change+.242327053mV. Cold40 corresponding errors were
  +13.693390mV/+12.210887mV. Normal60ns low interval restores acquisition in
  this fixed-reference/reset fixture; real conversion history and startup/POR
  remain unqualified. Sampling child independently reviews/plots the new case.
- Comparator child completed read-only runner cross-review:18 focused tests
  pass, real legacy comparator recipe is hash-identical to HEAD behavior, no
  blocking issue. Production worker exception handling verified locally. Parent
  caught Python2 unicode path rejection in reference exporter and sparse-PSF /
  final result filename issues in control exporter; requested corrections before
  freezing or remote use. No export run yet, no new circuit revision adopted.

### 2026-10-26 — Native FF boundary exports recovered; local fixtures next

- Completed managed analysis-only sar8audit-ref-native-v1 and then
  sar8audit-ctrl-native-v1 serially. These reuse existing completed simulations,
  start no new Spectre process and leave their source runs unchanged. Actual
  Python2 execution succeeded. New runner source binding/provenance, resource
  gates, terminal states and bounded collection worked on both real exports.
- Reference:108.86s, peakRSS120,844,288B;14 files/26,671,191B collected, no skips.
  Retained129,379 native points,32 columns through66ns; gzip24,229,723B,
  uncompressed33,121,024B, plus11,424-point64–66ns diagnostics. Parent memmap
  confirms GNNA1.034989914V@65.240591661ns, GNNB−.042540406V@65.243244885ns,
  GNNDRV1.057987231V@65.246122174ns, actualGNN0 .991208148V@65.246858873ns.
  This is stage-local voltage evidence; missing terminal currents still prevent
  a completed current-path attribution. Full source raw SHA remains uncomputed,
  explicitly recorded; source input hashes/state plus raw size/mtime checked.
- Control:10.18s, peakRSS121,257,984B;13 files/2,863,230B collected, no skips.
  8,746 native history points and4,665 diagnostic points,25 voltages plus time.
  X020.N peak1.078642014935018V@41.0895154336558ns matches the old native witness
  with zero value/time difference; no required signals missing. Source metadata,
  frozen inputs, raw stat identity and consumed-prefix SHA retained.
- Parent approved the sampling60ns report and inspected its new comparison
  figure. Sampling now holds; do not reuse FF boundary replay as an SS history.
  Reference/control are authorized only to review exports, plot and locally
  prepare first-event physical isolation fixtures/current probes. Device values
  stay fixed; no remote fixture run until parent reviews exact netlist, loading,
  initial conditions, measurements and run ownership. Control retains97MOS with
  true comparator outputs; absent fanout remains a reproduction limitation.
- Currently no in-flight managed job. The two module preparation chats continue
  under renewed authorization and active sar8 follow-up. No OA/PDK/Obsidian/10bit
  change, baseline adoption, commit, push or deletion.

### 2026-10-26 08:37 — Local isolation preparation checkpoint

- Both reference and control chats are actively reviewing recovered native data
  and preparing the already assigned local fixtures. No duplicate assignment or
  new remote run was issued. Comparator remains intentionally idle; sampling's
  accepted finite60ns result is unchanged.
- Refreshed the shared plan's current-status header to ten collected native
  diagnostics plus two analysis-only exports, removing stale next-step wording.
  Historical deadline remains explicitly superseded. No new electrical result
  or qualification change to notify; preserve all original data and ownership.

### 2026-10-26 08:50 — First-event fixture pre-review

- Control's local97-MOS fixture preserves real comparator outputs and seven
  native input histories. Parent found a PWL path mismatch against the managed
  Spectre cwd (inputs/); requested correction and a packaging-path check before
  freezing. No new run has been registered or launched.
- Reference's29 all-native PWL files exceed the32MiB package gate. Plan now
  permits a separately labelled local <=1uV-error piecewise-linear replay
  candidate, with all critical64–66ns points and threshold-crossing brackets
  retained and independently checked against every original native point.
  Original lossless data remain unchanged; package gate is not relaxed.
- Both existing preparation chats remain active. These are fixture review
  decisions, not new electrical results or qualification. No baseline change,
  circuit optimization, push or historical-data deletion.

### 2026-10-26 09:01 — Independent replay check and measurement review

- Parent independently parsed the actual serialized reference approximate PWL
  (SHA60e98573553b9c87df48d961daee643701fb685cba217383e9fa38a5274015f4).
  All29 channels preserve exact retained source timestamps/amplitudes, required
  fault-window/extremum/crossing knots, and an all-native maximum deviation of
  0.999987432uV. The22,534,325-byte source fits; the complete fixture package
  and electrical reproduction remain unapproved. Both native reference figures
  were visually inspected; values agree with recovered peak evidence.
- Requested the reference fixture stop at the last native replay point
  65.99650423427015ns instead of extrapolating to66ns. Existing source data stay
  unchanged. No circuit sizing change or remote simulation was authorized.
- Assigned the idle comparator chat a bounded independent review of the control
  fixture's retained receiver load, single-driver boundary, terminal-current
  KCL and native parser. It may read control files but writes only its existing
  comparator audit subtree. The control author continues implementation.

### 2026-10-26 09:10 — Control first-event native diagnostic admitted

- Comparator independent review found no blocking local defect: retained
 115 devices match source, immediate COMP_P/N/CMP_CLK fanouts preserved,
 416 terminal-current probes and56 KCL incidence sets match the fixture.
 Parent reran15 focused tests successfully and approved explicit reproduction
 screens in the shared plan. Cut downstream fanouts still need electrical
 validation; the first-event fixture does not qualify a conversion cycle.
- Registered sar8audit-ctrl-first-event-v1, recipe SHA
 587e794d928d6f25fa64ce7749d1d613fd0dd6fe3e1e46b7554b1dd1efb74ae7.
 Healthy bridge0.8.0 t28_io, thu-wei/chenzc_intern25 CIW and Spectre21.1 checked.
 Managed simulation admitted with no conflicting processes, one thread,
 1024MiB RSS cap. First status running, RSS127,000,576B at5.15s. No duplicate
 submission; original source/export/OA/PDK unchanged. Input package is frozen.
- Reference's local physical fixture/replay candidate is ready for review but
 lacks its dedicated current-analysis package. Assigned that missing preparation
 to its existing owner; no second remote job approved or launched.

### 2026-10-26 09:11 — Control current data recovered; fidelity screen not met

- sar8audit-ctrl-first-event-v1 completed simulation17.56s, peakRSS305,225,728B;
  analysis16.90s, peakRSS10,338,304B. Collected9 files/1,236,711B with no skips;
  parent verified every receipt SHA/size.5917 native points,1836 diagnostic rows,
  required terminal currents present and native END reached. No job in flight.
- Peak1.079890184V@41.085740590ns versus source1.078642015V@41.089515434ns:
  +1.248169mV and-3.774844ps. The preapproved1mV peak screen FAILS; time and
  edge-count/order checks pass5ps, initial maximum difference9.37nV passes1mV.
  Seven critical KCL residual maxima are below3.65pA, passing1nA. Current data
  are usable for fixture diagnosis, but source-circuit current attribution and
  a repair decision remain premature. No tolerance relaxation or baseline change.
- Native log has0 errors/31 warnings. Retained CMI2751–2755, SFE1131,
  VACOMP2435 and SPECTRE16780. The latter explicitly reports temporary LTE
  relaxation at41.0608ns on SAMPLE_INT; replay numerics and cut-fanout effects
  must be distinguished before assigning the amplitude discrepancy. Effective
  reltol1e-7, vabstol10nV, iabstol100fA, maxstep10ps, gear2only.
- Control owner is reviewing exact source-axis overlays and terminal-current
  integrals, with a proposed single-variable next diagnostic only. Frozen v1
  files remain unchanged; no new circuit modification or run approved.

### 2026-10-26 09:18 — Measurement review continues

- Control review identified four omitted MOS gate terminals on SN (X010/X014),
  a concrete candidate for the earlier LIVE transition. Causality is unproven:
  SAMPLE_INT replay's LTE warning remains a separate numerical hypothesis.
  Owner continues original-axis comparison and current integration; no new
  circuit variant or remote job has been authorized.
- Reference's current reducer and measurement-package builder now exist locally.
  Assigned an independent read-only review to the comparator owner, focusing on
  all275 terminal-current bindings, five KCL incidence sets, sparse/native-END
  handling, integration and bounded output. Its authored files remain confined
  to the comparator subtree. Reference author continues focused validation.
- No managed job is in flight and no new electrical result changes the preceding
  checkpoint. Existing frozen inputs and unrelated dirty files remain untouched.

### 2026-10-26 09:29 — Control plots reviewed; reference interface correction

- Parent inspected all three control v1 review figures on their original time
  axes. In this fixture only, NAND MP1 (gate LIVE) supplies the main positive
  pre-peak terminal-charge integral into X020.N:0.16636fC. The five terminal
  integrals balance; this does not separate channel/displacement currents or
  establish original whole-ADC current attribution while fidelity fails.
- PWL verification shows voltage continuity and <=0.4pV discrepancy from its
  declared piecewise-linear curve. Slope changes at knots remain; the logged LTE
  warning is preserved without asserting it explains the timing difference.
  Approved only local preparation of two source-bound analysis-only supplements
  for SN/X001 and missing X010/X014 load-bias evidence; no new run registered.
- Independent reference analyzer review caught a real configuration interface
  error: generated peak times used time_ns while the reducer expected time_s.
  Sent exact finding to reference owner for explicit unit conversion and an
  actual-generated-config end-to-end regression before freezing. Current probe
  and KCL mappings otherwise passed independent review. No faulty job launched.

### 2026-10-26 10:02 — Flat coordination; ready work and transport failure

- Applied user's explicit instruction to remove repetitive approval/review stops.
  Parent directly manages four module owners; diagnostic discrepancy is retained
  as evidence, not an automatic prohibition on targeted experiments. Actual
  resource/ownership/data protection and ADC specifications remain unchanged.
  Updated only sar8 automation accordingly; comparator resumes real input-load
  fixture preparation rather than serving as a recurring reviewer.
- Reference time-unit fix passed27 focused parent tests including actual config.
  Ready local run sar8audit-ref-current-v1 is frozen. First bulk registration
  timed out45s; exact managed status confirmed remote ENOENT. Extended register
  upload allowance to180s only;3 focused registration/hash tests passed. One
  unchanged retry ended with SSH server-not-responding; another exact status
  check again confirmed remote ENOENT. No Spectre submit occurred. Preserve both
  transport failures; no further blind retry. Small SSH/status calls still work.
- Control's two small SN supplemental export packages passed11 focused parent
  tests. These can advance the missing-load diagnosis while parent addresses
  reference bulk transport. No circuit variant adopted, push or deletion.

### 2026-10-26 10:11 — SN evidence delivered; reference current run launched

- Standard SSH compression recovered the unchanged25.34MB registration after
  the two recorded failures. sar8audit-ref-current-v1 hash
  bc5f54a1c7b5477c2be61e30833e6689b821191b089440a890e40055278b9d9e
  registered and submitted once. At126s it remains running, peak RSS391MB,
  output2.76GB within declared limits; analysis has not started. Sole heavy job.
- SN source/fixture analysis-only exports both completed and were collected:
  sar8audit-ctrl-source-sn-v1:8746 native points/9 signals,14 files/1,144,518B;
  sar8audit-ctrl-fixture-sn-v1:5917 points/3 signals,14 files/317,387B.
  All result-file hashes verified, no skipped files; peak analysis RSS122MB.
  Source/fixture recipes respectively3d1cc7bc...202d0 and512786dc...32680.
- Sent both exports directly to control owner. X001.N source/fixture peaks are
  1.00629127/1.01398521V; SN minima are-8.97765/-10.78040mV. These are measured
  fidelity differences, not proof of missing-load causality. Owner proceeds
  with original-device load restoration using recovered non-SN native biases.
  Comparator continues its real input-load fixture; no extra review layer.
- No original circuit, OA, PDK, historical result or user document changed;
  no baseline adoption, commit, push or deletion.

### 2026-10-26 10:20 — SN load reproduction resolves fidelity gap

- sar8audit-ctrl-snload-both-v1 (66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c)
  passed native simulation in30.35s, peak RSS306MB; streaming analysis18.51s,
  peak RSS10.4MB. Collected9 files/1,725,886B, no skips, all receipt SHA verified.
  Four original SN-connected MOS gate loads were restored with measured native
  diffusion biases; existing circuit devices and external timing unchanged.
- X020.N peak1.078641566V at41.089498025ns differs from original source by
  -0.448795uV and-0.017409ps, versus old fixture+1.248mV/-3.775ps. Initial
  witness maximum9.37nV,12 critical KCL maxima<=3.654pA. This supports the
  missing-load explanation for the reproduction discrepancy. The actual88.64mV
  overshoot and CMI warnings remain; no electrical repair/pass claimed.
  Sent full evidence to control owner for one targeted suppression candidate;
  do not spend more runs separating X010/X014 without a diagnostic need.
- Reference current v1 hit output_size_limit at364.85s/8,615,637,167B,
  peak RSS390.72MB. Original Spectre log reports SPECTRE-27 at61.9763ns,
  before64ns diagnostic window, followed by managed termination/SPECTRE-25.
  Four log/state files28,623B collected; no analysis or valid-result claim.
  Preserve raw and warnings, including replay LTE relaxation. Reference owner
  prepares save-only reduction with the same circuit/time span and budget.
- No heavy run remains active. Comparator real-load package is being finalized.
  No OA/PDK/history/Obsidian/10bit change, baseline adoption, commit or push.

### 2026-10-26 10:26 — Reference reduced-save rerun; comparator queued

- Reviewed reference v2 changed surface once; six focused tests passed. Saves
  reduce1375->413 while preserving275 currents,138 required/context voltages,
  KCL/stress/initial/edge evidence and all non-save circuit/solver bytes.
  Registered/submitted sar8audit-ref-current-v2 once, recipe
  4fd9a1d867afc325c1071a698186e16ef8845691fc1cccf6e394d28cfadb88cc.
  At95s it is running, peak RSS390MB/output621MB, original budgets unchanged.
- Comparator paired physical-CDAC diagnostic reviewed; nine focused tests pass.
  sar8audit-comp-kickback-tt-v1 registered with recipe
  5c3eee55600347ee6100a5dd2115f747cc4aa43a5ec490f51032f03bce65b769;
  managed queue accepted it but did not admit a simultaneous simulation. It
  waits behind reference with600s queue budget. Inputs frozen; no electrical
  result yet. Reference recovery and comparator analysis remain serial.
- Control owner prepares a single internal MP1 gate-resistor experiment on the
  verified both-load fixture; no additional fidelity sweeps requested. Parent
  viewed the existing source/v1 SN comparison figure; no new result claimed.
  Shared history and unrelated dirty files remain preserved; no commit/push.

### 2026-10-26 10:39 — Reference completes; control experiment queued

- Reference v2 native PASS/zero-error completed in411.44s,2,911,251,176B,
  peak RSS390,995,968B. Its stream analyzer is running at about14.25MB RSS;
  no result claimed before completion. One analysis-start SSH banner timeout
  was resolved by exact not_started readback before a single retry.
- Comparator kickback v1 reached221.657ns then output_size_limit at2,148,028,470B.
  Four logs/state files22,831B collected. Save names used lowercase while actual
  deck symbols are uppercase: native8281/8282/8286/8287 show ignored saves;
  output summary463 voltages/9 currents, not the declared36/45. Native27/7082
  and subsequent USIMUWI-20006 output exception retained. Initial-DC16881 is
  separately preserved; do not infer it caused output growth. Owner directly
  fixes save-symbol mapping in a fresh package, no budget or circuit change.
- Parent verified MP1 experiment actual package: exactly one gate reconnection,
  one existing-parameter rupolym, all MOS/boundary PWL/stop unchanged, correct
  new-gate KCL. Registered sar8audit-ctrl-mp1shape-v1 with hash
  8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a.
  One submit SSH banner failure had exact not_started readback before retry;
  managed accepted worker320897, queued behind reference analysis. No concurrent
  heavy job. No duplicate run, baseline adoption, commit, push or deletion.

### 2026-10-26 10:48 — First suppression result; bounded analysis recovery

- MP1 gate-resistor experiment completed native19.26s/RSS306.53MB and analysis
  18.26s/RSS10.49MB. Collected9 files/1,927,723B with no skips; all SHA verified.
  X020.N peak1.005487759V versus both-load1.078641566V: overshoot88.642->15.488mV
  (about82.5% reduction), still not compliant. New B_PM min-7.021713mV and
  max0.989999765V; native CMI persists. Critical KCL maximum3.452pA.
  LIVE/QUIET halfrail41.085210193/41.102521878ns. Sent evidence for explicit
  gate-terminal stress, charge/current and timing tradeoff review; no adoption.
- Reference v2 reducer failed after459.73s at its unchanged30MiB derived cap,
  peakRSS14.68MB. Bounded read-only console tail confirms fault.row -> reserve
  ValueError. Simulation remains valid. Partial-result collection timed out
  during transfer; retained local state files and remote partial data, no blind
  retry. Owner prepares analysis-only compact native exports retaining all275
  current statistics, with only15 critical-current waveforms. No Spectre rerun.
- Comparator exact-case save correction passes four focused tests. Registered
  and submitted sar8audit-comp-kickback-tt-v2 once, hash
  033415e34b80fa7ed2bb8d4f2baf1a0582ca7e6772f5a1a118d3dabc79302db2.
  It is the sole heavy run, at75s/RSS309MB/output194MB; native completion and
  signal acceptance still need verification. No old result, OA, PDK, user file,
  baseline or historical data was changed; no commit/push/delete.

### 2026-10-26 11:04 — Physical input-load comparator evidence recovered

- Comparator sar8audit-comp-kickback-tt-v2 completed native119.56s and analysis
  95.31s. All10 artifacts/11,855,029B collected and SHA/size verified. Original
  log confirms36 voltage/45 current saves, zero errors and seven warnings
  (SFE-1131/3031, SPECTRE-16881, VACOMP-2435 retained). No CMI in this run.
- Six TT0.9V27C comparisons at +/-1.7578125mV all wrote the expected sign;
  clock-half-to-write1.60816–1.61638ns. Active-minus-reset peak differential
  disturbance0.28484mV during decision; common-mode minimum-8.78074mV occurs
  at clock fall/reset after write. These are distinct phase effects, not a
  whole-ADC accuracy verdict. Selected N4/rx2 pair screen0/228 exceeded;
  attached storage/forward logic not requalified. Top-node KCL max51.73pA.
  Owner received verified data for phase-separated figures/report. Fixed
  bottom references and temporary initialization remain ideal boundaries.
- Reference compact recovery sar8audit-ref-current-v2-reduce1 registered with
  hash27d9447e0d10bf809d565e1c111bbef9fd3f206e0750d9e5f14f1226b12095d3;
  analysis-only worker84288 reads completed v2 raw. At298s RSS14.80MB and
  output15.82MB, still running. Seven focused wrapper tests passed; no new
  Spectre run or overwrite. Source inputs frozen.
- Collection45s timeout was a transport limitation, not a simulation failure.
  Read-only artifact fetch now allows180s, retaining32MiB/hash/resource gates;
  one focused transfer test passed and actual collection succeeded. No analysis
  or simulation was retried for that timeout. Control owner continues passive
  gate-bias candidate; sampling awaits same-corner history. No baseline,
  OA/PDK/history/user-file edits, commit, push or deletion.

### 2026-10-26 11:06 — Independent startup preparation

- Reference compact analysis remains active under15.2MB RSS; control prepares
  its single passive gate-bias change and comparator prepares verified-data
  phase plots. No additional remote heavy task was submitted.
- Sampling owner resumes local startup fixture preparation using existing SS
  cold fixed-reference real Bootstrap/CDAC. Supply ramp versus high-phase DC
  initialization must be explicit; normal sampling edges/MOS stay unchanged.
  External POR/precharge assumptions are not implemented circuitry. This
  independent preparation need not wait for FF reference evidence and does not
  repeat low60cold. No remote sampling run or baseline adoption authorized.

### 2026-10-26 11:10 — Reference current evidence recovered without rerun

- sar8audit-ref-current-v2-reduce1 completed522.63s, peakRSS17,551,360B.
  Eight artifacts29,400,176B collected with no skips; streamed SHA/size
  verification passed all. Source native data preserved, no Spectre rerun.
- Parsed147,657 native points with all275 selected currents initialized.
  GNNA1.034989438V, GNNB-0.042542380V, GNNDRV1.057986484V,
  GNN0.991208123V. Four target peak errors versus original source are at most
  1.974uV and0.0251ps; largest fault-window waveform discrepancy0.77486mV
  is explicitly an interpolated-source comparison, not a native measurement.
  Five-node fault KCL residual at most1.305pA. Actual CMI retained.
- Verified result and both native waveform exports forwarded to reference
  owner for branch-charge/current diagnosis and one minimal circuit experiment.
  Remote heavy queue now free; control candidate still under local preparation.
  No whole-ADC claim, new baseline, commit, push or data deletion.

### 2026-10-26 11:18 — Comparator phase correction; next control experiment

- Comparator owner's full native phase review corrects an overly narrow earlier
  interpretation: common-mode loss already reaches about-8.244mV at the first
  write, before reset. The-8.781mV global minimum is near reset, not evidence
  that common-mode disturbance starts there. Post-reset differential disturbance
  reaches0.348mV; the previously reported0.285mV is the decision-period peak.
  Six writes remain correct. Parent viewed timing_phases.png and requested
  unclipped current/output axes. One follow-up is locally authorized: omit only
  the second44–58.1ns initialization to test retained charge across two decisions;
  no remote comparator run yet. Original run/raw and prior record preserved.
- Reviewed actual control mp1_floor_v1 package once: only three equal original
  rupolym pullup resistors added; all previous leaves/PWL/non-save deck unchanged.
  All package SHA checks pass. A focused synthetic native case verifies joint
  stress extrema outside the plotted window and signed source-energy integration.
  Parent froze inputs and is registering sar8audit-ctrl-mp1floor-v1 for serial
  execution, preserving supply/window and resource limits. No baseline adoption.
- Registered control run hash3813f5e217e5d2b360b75fa11d46603b3ca0bbeb8e6e56380f56caa2b0fb529f;
  managed submit accepted/admitted worker182170, no conflicting processes.
  Inputs frozen. No second simulation submitted.

### 2026-10-26 11:23 — Gate-floor experiment is a tradeoff, not closure

- sar8audit-ctrl-mp1floor-v1 native19.72s/RSS306.60MB and analysis19.62s/
  RSS10.58MB complete. Nine files2,094,661B collected and all SHA/size verified.
  Actual CMI-2751..2755 remain.6055 native points, diagnostic KCLmax3.954pA.
- B_PM minimum becomes+0.251503V; full-history MP1 VSGmax0.738497V and
  |VGD|max0.98999355V show no selected-pair exceedance. However X020.N peaks
  1.025472329V: overshoot worsens15.488->35.472mV versus gate-series-R alone.
  LIVE min-11.6162mV remains; QUIET one rising edge41.10205889ns. Therefore
  candidate is not accepted. Local VDD energy1.08493pJ over41.5908ns is not
  whole-ADC power; new static current must be included in the tradeoff.
- Sent verified evidence to control owner for branch-level shape/floor comparison
  and one justified next change. No blind resistor sweep, architecture change,
  baseline adoption, commit/push, OA/PDK/history/user-file modification.

### 2026-10-26 11:29 — Serial recovery and held-charge follow-up

- Registered/dispatched two control source-bound analyses without simulation:
  mp1shape-stress-v1 cba77733017f88e06d61f9d27249c8d1eefa2cea1b40d041fdccfabea02bdbba,
  both-stress-v1 21e0940f7afc08f8d054056ca7f3f5eb70e4fdeb054909716780e11e131c82d0.
  First completed20.18s/RSS13.43MB; parsed result and waveform fetched with
  per-file SHA checks, final receipt interrupted by SSH banner timeout. Source
  full-history VSG0.997021713V and |VGD|0.996791886V confirm prior screen;
  local VDD energy0.0707719pJ versus floor1.08493pJ, same41.5908ns interval.
  No remote execution was retried because of transport failures.
- Comparator hold2 package reviewed; three focused tests pass, only one
  initialization pulse removed. Registered0ed949bb4dbf5cf206e928d2d27642530e91806146ef6647882d727e992d9737,
  managed admitted worker245218 after previous analysis released the lock.
  Exact run sar8audit-comp-hold2-tt-v1. Native outcome still being checked.
- Sampling startup diagnostic assumptions accepted for local package preparation,
  including260ns/two frames. Collection remains32MiB; owner adapts lossless
  compact export instead of the proposed40MiB. No POR implementation or startup
  spec is inferred. Comparator figure axes now show full62.9uA/1.017V peaks;
  parent visually checked updated plot. No baseline/commit/push/OA changes.
- Both source analyses now fully collected and receipt hashes verified: shape
  7 files1,909,884B; both7 files1,707,968B. Both baseline VDD energy0.0707303pJ
  versus shape0.0707719pJ and floor1.08493pJ. Forwarded for consistent local
  energy/stress comparison; transient SSH recovery did not rerun calculations.
- hold2 native completed128.81s/RSS310.40MB, PASS/zero-error with original
  warning classes retained; analysis admitted worker266855. Codes/residuals
  are not yet evaluated.
- Parent read reference branch metrics and viewed both native figures. At
  GNNDRV positive peak, Rgate current+0.686uA leaves the driver toward load;
  leading-window net charge has the same direction. This rules out net CDAC
  backflow as the source of this particular positive peak, not all coupling.
  Approved local preparation of one ideal1kOhm common C-stage gate-series
  resistor as a mechanism test; no new remote reference run yet or claim that
  it is a final PDK implementation. All external waveforms/MOS dimensions stay.

### 2026-10-26 11:38 — Retained-charge comparison recovered

- sar8audit-comp-hold2-tt-v1 analysis97.68s/RSS10.15MB completed;10 artifacts
  11,907,280B fully collected and SHA/size verified.100,644 native points.
  All six writes remain correct; selected N4/rx2 stress records0 exceeded.
  Second comparison before clock: differential1.757606762mV, original-target
  error-0.205738uV, CM0.449700415V; write delay1.60846273ns versus reinitialized
  1.60837533ns. Thus at this40ns comparison spacing the residual differential
  is small, although CM is about0.300mV below target. This does not verify the
  actual shorter SAR bit-reset interval. Owner prepares bounded result review.
- Control branch review motivates a single next parameter: X020 private NAND
  CMID PDK MOM multi2->1 on the floor candidate. Accepted local package
  preparation, keeping original MOM geometry/all MOS/gate pullup/PWL intact;
  parent checked the actual existing CMID definition. No new remote control
  run yet, and no conclusion that capacitance reduction will meet timing/stress.
- Reference1kOhm mechanism package and sampling startup pair remain in local
  preparation. No remote heavy task currently active; no baseline/commit/push.

### 2026-10-26 11:50 — Single-variable block experiments dispatched

- Control CMID half independently checked: sole private CMID multi2->1 change,
  all15 input hashes and unchanged test/PWL/analyzer. Managed run
  sar8audit-ctrl-cmidhalf-v1 hash4a7e6299c079bec1b798b68ea076c72482005a04c273b39a7824fd039c972069
  completed native26.18s/RSS306.58MB; original CMI2751..2755 and other warnings
  retained. Analysis dispatched worker42769, collection in progress. SSH status
  banner timeout recovered read-only; no simulation repeated.
- Reference sar8audit-ref-cinput-r1k-v1 hash
  c0a08c8b95cc536402aff144e3d71a4dd8d67e6943be902cc7c52b8a50da7732
  admitted worker45806 after control analysis released heavy lock. Three focused
  tests passed, including actual topology and six-node analyzer CLI. Candidate
  only changes final common-gate series resistance; no efficacy result yet.
- Sampling startup wrapper reviewed,10 focused checks and deterministic package
  check passed. Both recipes registered, not submitted: DC
  ecf53f6676e81c0e36fb90c1d1706ddbc6d45ab8a48c2cf4f714bf5852134c5e;
  ramp8fd56698aaf618d20faf997b0b8e87a82b4470b9669a3dd58aa6fdbc3b278ec2.
  Queue behind reference/control; no second remote heavy process. Comparator
  prepares only real-short-bit-interval TT retained-input fixture from frozen
  timing evidence. No baseline adoption/OA/commit/push/deletion.
- CMID half fully collected and verified9files2,081,537B; analysis19.52s,
  peakRSS10.57MB,6041nativepoints. N1.013105156V@41.088098367ns: overshoot
 35.472->23.105mV versus floor, still above0.99V. MP1 VSG0.738498091V,
  |VGD|0.989994816V remain within selected screen. QUIETsingleedge41.098726967ns;
  VDDenergy1.085184387pJ and minimum24.449uW indicate floor static cost remains.
  Forwarded verified result for branch/charge comparison and one justified next
  proposal. Reference1k experiment runningRSS389.27MB; startup pair registered
  only. No need for user action; candidate not adopted.

### 2026-10-26 11:56 — Serial startup control queued

- Reference C-input experiment remains running at389.27MB RSS. Admitted only
  the queued worker71551 for sar8audit-sample-start-dc-sscold-v1; it waits for
  existing Spectre45841 to release the heavy slot. Ramp remains registered,
  not submitted. Do not duplicate either run. Next collect/analysis follows
  precise completed state; reference result analysis remains priority.
- Parent viewed hold2 comparison figure: separate clock/initializer/differential/
  CM/write rows, correct units and40ns spacing caveat; readable without changes.
  Control charge analysis and comparator short-interval preparation are active.
  No new electrical outcome or user intervention required.

### 2026-10-26 12:07 — Native completion and bounded analysis queue

- Reference cinput-r1k native complete460.38s/peakRSS390.77MB, PASS/zero error;
  original CMI2751..2756 and numerical/environment warnings retained. Analysis
  admitted worker121676. No electrical efficacy conclusion before measurements.
- Sampling start-dc native complete59.28s/peakRSS315.13MB; PASS/zero error,
  SFE1131/2453 and VACOMP2435 retained, no CMI in this native summary. Startup
  accuracy still unmeasured. Analysis worker123065 queued behind reference;
  ramp remains registered only. One heavy task, unchanged resource limits.
- Read control four-version report/next-step and viewed waveform. Half peak
  MP1 injects22.010uA while upper NMOS draws20.781uA; MID remains0.5623V.
  Approved local single-variable NMOS gate-order swap to pre-discharge MID,
  with added joint terminal stress and revised gate KCL. Static floor loss is
  still unresolved. Do not infer channel/Cgd decomposition from total currents.
- Comparator prepares intact actual shortest TT pair3.955843ns spacing with
  its corresponding1.179357/1.212701ns high widths, not mixed minima. Parent
  emphasized small-input forced-reset test is conditional: history residues
  were much larger, so missing write cannot by itself indict asynchronous SAR.
  No baseline/OA/commit/push changes or user intervention required.

### 2026-10-26 13:11 — Reference recovered; next block cases serial

- Reference1k run analysis511.29s/18.99MB;11files27,863,346B allSHA/size verified.
  GNNDRV positive peak1.047580099V vs original1.057986484V, still exceeds0.99V.
  GNNB negative peak-44.2998mV vs-42.5424mV; new common gate-30.5825mV.
  Full-history GNN0 maximum is a different45.37973ns event, not65ns fault peak.
  Owner received complete evidence for same-window branch/stress/settling/energy
  review. No circuit repair claim; original warnings remain.
- StartupDC18files16,540,954B fully verified. Owner handles bounded unpack and
  two-frame measurement. Ramp simulation completed58.90s/315.18MB PASS, noCMI
  in native summary; original warning classes retained. Analysis123243 queued.
- Comparator actual-interval reviewed real deck/analyzer changes;3 focused tests
  passed. Register d7f6fe712c86d0788035bdca33f7d9913fb0bdc2b9978d82136710494d051352;
  worker121401 admitted. Conditional forced-clock interpretation remains.
- Control stackorder reviewed config/synthetic joint-stress test, unchanged
  analyzer, actual two private gate-line diffs and all original deck/PWL bytes.
  A scratch first-occurrence replacement check hit generic NAND and failed;
  corrected exact line comparison confirmed only private lines179/186 change.
  Register f7fdea18a1eb32890b5dd3688952ac6e14e91d8d05106bc8dfcd3d85305a82e3;
  queued worker127006. All queues share one heavy lock. No OA/commit/push.

### 2026-10-26 13:14 — Startup pair fully recovered

- Ramp startup analysis complete22.82s/peakRSS141.95MB,18files17,932,208B
  SHA/size verified with no skips. Owner received both startup cases for bounded
  unpack and comparison, preserving first-frame-0.81V vs second-frame0V distinction.
- Comparator actual-interval native complete107.03s/310.40MB, PASS/zero errors,
  original SFE1131/3031,SPECTRE16881,VACOMP2435 retained. Analysis134009 queued
  behind stackorder simulation. Control stackorder native complete18.81s/
  306.62MB PASS/zero errors, CMI2751..2755 and original warnings retained;
  analysis138078 queued behind comparator. No reruns or efficacy claims yet.
- Reference same-window branch/stress review continues in existing owner chat;
  no new candidate dispatched. Protected dirty state untouched; no OA/commit/push.

### 2026-10-26 13:25 — Stack order and short-clock results recovered

- Stackorder9files2,109,393B SHA/size verified;5939nativepoints. MID starts
  0.325uV and N peaks1.005230071V@41.084645444ns, reducing overshoot from
  half23.105 to15.230mV but not solving terminal stress. Added observations:
  MN0|VGD|max1.000868868V,VDS0.997816271V; MN1VGS/VGB0.991334270V,
  VGD0.990283806V. These are newly measured, not proven newly introduced.
  MP1selectedpairs remain within screen. QUIET41.094599063ns singleedge;
  VDDenergy1.085590476pJ retains floor static cost. Owner analyzes currents
  and proposes one local change addressing coupling, static loss and headroom.
- Comparator actual10files10,970,767B verified;93208nativepoints,228selected
  screens0exceeded. First two forced-short pulses yield no resolution or write
  before reset; later four controls write correctly, no unassigned write.
  Second precompare diff1.756938433mV andCM449.582184mV. This is recovery
  after interrupted decision, not two valid SAR conversions or proof of actual
  asynchronous failure. Owner received result and will propose minimum real
  completion-feedback fixture. Analysis86.34s/10.13MB completed.
- Viewed startup power-up detail: moving half-VDD crossings while external
  SAMPLE stays0 are explicitly distinguished from accepted sampling events.
  Pair report still in progress; do not infer POR compliance. Reference review
  confirms R1k partial peak benefit does not reduce228screen violation count.
  All dispatched jobs complete; no heavy task active. No original changes/push.

### 2026-10-26 13:35 — Bounded startup evidence and next reference direction

- Read final reference R1k report and viewed same-window figure.111/228 terminal
  records exceed limits in both versions; peak shaping did not cure stress.
  Authorized existing owner to prepare minimal1.8V driver-cell real-load
  feasibility using legal prior primitives, FFhigh/cold and SSlow/cold controls.
  Original source IO reference switches are not mistaken for IO driver stages.
- Read complete startup pair report and inspected full-wave/detail figures.
  Ramp first preclose/held0.287818/0.523542mV versusDC0.048685/0.303479mV;
  second held-0.166134 versus-0.163703mV. Both0/1422 terminal screens. Formal
  sample edges unchanged; first/second inputs differ, cross-frame drift not a
  startup causal comparison.0.409..0.456V SEQ crossings are intermediate supply
  state, not normal-operation error. Fixed-reference diagnostic checkpoint done;
  POR/full reference switching integration still unqualified. Owner saves and
  waits on reference/control dependency, no redundant startup sweep.
- Control reports peak injection moved toMN0 after stack swap; Q1 overrail was
  already present in half (about0.624mV), now1.334mV and applied to lower gate.
  Awaiting completed branch-derived next proposal; comparator feedback proposal
  also active. No heavy task active, no baseline/OA/commit/push/deletion.

### 2026-10-26 13:45 — Next local packages assigned without extra review layers

- Read control stack-order findings and next-step proposal. Assigned one bounded
  FF-cold legal IO logic candidate retaining stack order and removing the three
  gate-floor bias resistors. Device-class plus bias removal is a cell-scheme
  change, not a single-parameter experiment. Preserve actual interface loads,
  all affected terminal-pair measurements, delay and source energy. SS speed
  requires its own later stimulus; no FF analog replay labeled SS evidence.
- Read comparator completion-feedback proposal and inspected actual_vs_hold2
  figure: clocks, held input, common mode, output difference, write and D0 are
  separated with baseline/threshold and reset markers. Approved direct local
  construction of one TT held +0.25LSB eight-token fixture with original
  completion/reset chain and a finite explicit real receiver-load island.
  PHI_U is update, not reference-settling acknowledgement. Conditional cuts
  remain disclosed; no full-ADC or startup-handshake qualification inferred.
- Reference IO package remains in preparation; sampling checkpoint is complete.
  All existing runs recovered; no new remote dispatch or heavy task this turn.
  Protected dirty files unchanged; no baseline adoption, OA edit, commit or push.

### 2026-10-26 14:07 — Local IO result recovered; native feedback dispatched

- Registered sar8audit-ctrl-iolocal-v1, managed hash
  aa418b9919dce4576fe5013f09e6d1721c63df76b856e20e205a682d570682a7.
  Native20.242s/306.57MB, analysis23.871s/11.33MB completed.9files4,436,865B
  SHA/size verified with1MiB chunks; no skipped files;6065native points.
  Changed IO0/90 provisional terminal screens exceeded; retained core46/102
  exceeded, including MN_CLEAR VGS1.031652416V. N1.034017195V now lies within
  IO boundary but overshoot is not eliminated. QUIET41.192313209ns; five-source
  energy retained, VDD0.061016793pJ over same41.590786ns versus1.085590476pJ
  stackorder. No whole-ADC power claim. CMI2751..2755 retained. Owner now
  compares current paths, delay and exposed core interfaces before next change.
- Read comparator feedback analyzer/cut and ran four focused tests successfully.
  Owner corrected proposed simulation RSS1536 to1024MiB; seven payloads remained
  unchanged and parent verified hashes. Registered sar8audit-comp-feedback-tt-v1,
  hash f8fc3ef1e8edbfb22c81215cc4ee066884ca6af8d934bad9f918bab5ee3062ea;
  accepted worker100817 after control analysis completed, sole heavy task.
- Reference owner showed apparent history/context drift toward creating chats;
  sent precise correction to resume existing IO cell package only, no new chats
  or remote operations. Sampling checkpoint unchanged. Protected dirty state
  preserved; no baseline adoption, OA edit, commit, push or deletion.

### 2026-10-26 14:14 — Feedback output failure preserved; reference pair dispatched

- Comparator feedback-v1 stopped at38.0381ns with SPECTRE-27 single-file size
  limit, followed by7082/USIMUWI20006. Managed output2,149,646,420B exceeded
  declared2GiB; native PASS=false.264.55s/319.08MB peakRSS. Exit0 alone is not
  success and trailing not-enough-virtual-memory text is not proof of RAM OOM.
  Collected4files20,761B, SHA/size verified, no skips. Failed raw remains.
  Owner prepares v2 with same1457MOS/100ns/stimuli/solver and smaller explicit
  functional/critical-stress save set. Full8742-pair coverage remains uncompleted;
  native CMI stays enabled. No resource cap bypass or old-case overwrite.
- Read reference IO-cell note, paired topology, streaming analyzer and ran3
  focused tests successfully. Four package hashes verified and managed registered:
  core-ffcold7d6784ce..., io-ffcold76a2de63..., core-sscold73578e24...,
  io-sscoldabe5b326... (full hashes in management/runs records).
  FF core accepted worker146378; FF IO worker146794 queued behind it under
  existing_simulation_or_analysis gate. SS pair registered only; do not duplicate
  submissions.4threads/512MiB simulation,256MiB analysis,32MiB collection.
- Reference owner confirmed no new chats or remote work; resumed correct scope.
  Control interface analysis continues independently. Original/PDK/OA/Obsidian/
  10bit and historical results unchanged; no commit, push or deletion.

### 2026-10-26 14:26 — Reference FF pair recovered and feedback v2 running

- Reference core/io FF native completed20.01/20.59s (~303MB); streaming analysis
 51.83/49.96s (~15.2MB). Collected11files each:3,862,432B and3,895,665B,
 SHA/size verified, no skips;8534/8439native points. CMI2751..2756 preserved.
 FF core versus IO B-to-C falling1.987/8.441ps, rising1.487/10.431ps;
 B-to-load-gate falling67.371/75.996ps, rising32.309/44.025ps. Same independent
 logic fixture only. High-reference BN0 final errors1.13764/1.13989mV remain
 outside1mV diagnostic in both. Owner analyzing full pair stress/KCL/energy.
- Reference SS core native complete19.66s; analysis queued. SS IO already
 queued, not resubmitted. Shared gate admits exactly one heavy task; comparator
 feedback-v2 currently running, original failed v1 retained.
- Feedback-v2 registered hash d56adca4380107296e7bd8aebe5fadd39f419aa579e8a0235bc53284b2b5cb90.
 Parent verified unchanged electrical deck/four payloads, seven frozen hashes
 and focused test; only save scope/stress reporting changed.124V/23I,
165MOS/990 pairs, remaining7752 unmeasured. No resource/solver relaxation.
- Viewed control retained-interface figure: old AB/X001 peaks are explicit
 scalar witnesses, not invented old waveforms. Core interface follow-up is
 still being prepared. No baseline/OA/commit/push/deletion; protected files intact.

### 2026-10-26 — User-directed T28 standard-cell feasibility inspection

- Live t28_io bridge confirms seven tcb libraries; main library1386 OA entries.
  Representative gates/DFF/latch/delay have symbol/spectre/layout views; separate
  SPICE contains1186 subcircuits. Selected cells use nch_mac/pch_mac core models.
- Recorded concise metadata and assessment under verification/sar8_module_audit/standard_cells/.
  Found five matching voltage/corner manual filenames, SPICE/LPE and CCS archive.
  170a versus180a/190a compatibility, exact characterization limits and simulator
  binding remain unverified. PDF extraction unavailable remotely; bounded local
  read declined size above16MB. Initial archive listing timed out45s; subsequent
  bounded member inspection stopped before large payload. No archive unpacking.
- Recommend smallest control-cone standard-cell comparison before more custom
  IO patches; no standard-cell simulation or replacement performed. Control owner
  asked to preserve IO checkpoint. Protected OA/PDK/history unchanged; no commit/push.
- Background comparator feedback-v2 native complete100ns,561.37s,316985344B peakRSS,
  zero-error/PASS footer, SFE1131/VACOMP2435 retained. Managed analysis accepted
  worker295967; circuit verdict pending. SS IO prior queue_timeout was pre-start;
  no uncertain retry performed.
- Clarification to14:26 entry: reference FF BN0~1.14mV final-window sample overlaps
  companion turn-off beginning46.995ns; it is not evidence that the preceding
  plateau never settled. Owner separating plateau/turn-off measurements.

### 2026-10-26 14:50 — Recover results; standard-cell route preparation

- Reference FF report confirms both variants settled before companion turnoff.
  The previously quoted~1.14mV endpoint overlaps46.995ns turnoff. Subsequent
  floating gap BN0~+44.37mV/BP0~-35.37mV is distinct switching disturbance.
  IO C worst1.371385V is below provisional1.98V, while core A/B still exceed
 0.99V by20.753/36.131mV. Viewed handoff figure; no whole-ADC pass claim.
- Comparator feedback-v2 analysis failed after100.12s at derived output cap,
  not native simulation. Retrieved exact traceback from analysis.console.log.
 8files30,426,213B SHA/size verified; partial gzip must not be used as complete
  waveform. Owner preparing bounded-export analysis-only recovery without
  changing native-point metrics or original simulation.
- SS core11files4,150,189B SHA/size verified and handed to reference owner.
  SS IO prior pre-start queue rejection2files1,367B verified, no child/start.
  Explicit same-input q2 registered70189d38065071c2a25266856ec1eb94274817c9263b44138707956787c84e3b;
  native52ns complete/PASS, zero errors, SFE1131/VACOMP2435. Analysis dispatched.
- Control owner prepares local minimal logic-equivalent tcb mapping; old IO
  candidate frozen, no standard-cell simulation/adoption. No OA, commit, push
  or deletion. Original inputs/PDK/history and unrelated dirty files preserved.

### 2026-10-26 15:00 — SS IO recovery delivered for paired interpretation

- sar8audit-refcell-io-sscold-q2 completed52ns native22.70s/302747648B;
  analysis48.32s/15163392B. Native PASS/zero errors with SFE1131/VACOMP2435.
  Collected11files3,710,891B; all SHA/size verified, no skips. Reference owner
  now compares SS pair and summarizes FF/SS tradeoff with turnoff distinct
  from on-state settling. Original rejected queue admission remains untouched.
- Comparator owner preparing two-pass analysis-only export repair: native-point
  metrics retained, bounded display export and source-hash comparison. Not yet
  frozen or submitted; no repeat simulation. Control minimum standard-cell
  mapping still in progress; no duplicate assignment. Sampling remains at its
  documented conditional checkpoint. No new baseline/OA/push/deletion.

### 2026-10-26 15:10 — SS pair interpreted; native-only metric recovery launched

- Reviewed SS core/IO report:450 screens pass in each measured fixture, noCMI;
  C worst0.935208/1.113774V (core0.99/IO1.98 provisional screens). IO B-to-GNN0
  off/on104.093/80.201ps versus40.939/27.972ps; BN0 low-reference1mV settling
  delayed73.85ps. Both establish; off-gap~+33.775/-32.387mV persists. FF A/B
  violations remain. Candidate direction is feasible locally, not an adopted
  sizing, full asynchronous timing closure or whole ADC qualification.
- Reviewed comparator completed-source reducer; one focused test passed and
  five frozen hashes verified. analysis-only sar8audit-comp-feedback-v2-reduce1
  registered fba4c814e8d1b7e4721d4ca9d69ad6777090d1c9305233fc26f95d4a68942cda,
  worker94472 accepted. All native metrics retained; sampled display export
  includes explicit event/extrema/recovery witnesses. No new simulation.
- Reviewed minimal control X020 NAND+INV mapping. Read-only installed170a
  switch-graph verification confirms Boolean functions and NAND A1 adjacent
  to output. Saved metadata only; no foundry internal copy. Control prepares
  local FF-only bounded package with true RC/SR load and original inputs;
  simulator/model compatibility remains to be checked. No remote standard-cell
  experiment or new baseline yet. No OA edits, commit, push or deletion.

### 2026-10-26 15:20 — Comparator native-feedback sequence recovered

- Completed-source analysis sar8audit-comp-feedback-v2-reduce1 succeeded in
 299.32s/13,987,840B peakRSS. Collected7files7,290,320B, all SHA/size verified
  with1MiB chunks, no skips. Original native data unchanged.156161 metric rows,
 19924 display rows/57columns, stride8 plus475 witness times; source passes match.
- Eight native clock/write/update/reset events, tokens7..0 terminate, no
  unassigned events, protocol_eight_pass=true. Clock half-high2.1555..2.1656ns,
  write latency1.5863..1.5979ns, reset-ready delay0.5903..0.5908ns. Selected
 990 terminal screens have0 exceedances; full8742 coverage incomplete.
- Conditional TT0.9V/27C, fixed+0.25LSB and fixed-bottom CDAC,32 downstream
  reference outputs unloaded, ideal startup boundary. acceptance_pass=null,
  circuit_repair_claim=false.10.912755pJ is local0..100ns VDD energy, not ADC
  power qualification. Owner now preparing figures and interpretation; no new
  simulation. Standard-cell FF package still being prepared; no duplicate task.
- No baseline adoption, protected changes, OA edits, commit, push or deletion.

### 2026-10-26 15:30 — Standard-cell native integration metadata supplied

- Control requested actual six-MOS probe identities and master types before
  preparing FF package. Parent read only installed170a SPICE:2,452,584B,
  SHA b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e.
  Recorded instance/terminal names and explicit n suffix on L/W; no transistor
  geometry values or foundry netlist copied.
- Actual ffmacro include follows cln28ull_1d8_elk_v1d8_3.scs. nch_mac/pch_mac
  are inline subckt, ports n1..n4=D/G/S/B (declarations14236/24533, primitives
 14237/24534). Initial plain-subckt search missed inline syntax; corrected
  metadata does not claim absent/encrypted definitions. No source mutation.
- Control owner received both metadata files and continues same FF package.
  Unchanged foundry SPICE M-call/Spectre compatibility still needs native
  validation; no guessed prefix rewriting or missing-current zero-fill.
  Comparator figures remain in progress. No new remote job or baseline.

### 2026-10-26 15:40 — First native standard-cell comparison dispatched

- Reviewed X020-only standard-cell package, analyzer and one focused test;
  test passed. Nineteen frozen input hashes and recipe match. Read-only
  foundry2,452,584B SHA b7b366bf... unchanged before dispatch.
- sar8audit-ctrl-stdcell-ff-v1 registered593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20,
  worker260281 accepted and native simulation running.1thread/1GiB/41.5908ns.
  Physical101MOS606screens plus3 node diagnostics,61V435I60KCL; actual native
  SPICE M/inline current bindings remain first-run checks. No baseline adoption.
- Read comparator conditional-feedback report and viewed all three figures.
  Internal reset90 at~0.591ns after clock fall still leaves~79uV differential
  recovery error; next precompare error~-0.807uV. No claim this observation
  threshold proves charge recovery, setup/hold or ADC precision.
- Comparator now prepares paired opposite-history-to-small-residual fixture
  locally, preserving original feedback/RC and floating MOM input after bounded
  charge stimulus. Standard-cell run retains queue priority. No OA changes,
  push, commit, history deletion or shared-source modification.

- Follow-up: stdcell-ff-v1 native completed20.36s with PASS/zero-error footer.
  Unmodified foundry SPICE was accepted in this fixture. CMI2751..2755 and
  SFE1131/SPECTRE16780/VACOMP2435 remain; cannot infer which groups pass.
  Analysis worker266432 accepted; native terminal bindings/metrics pending.

### 2026-10-26 15:50 — Standard-cell first-event native results recovered

- sar8audit-ctrl-stdcell-ff-v1 native20.36s/335,761,408B and analysis39.09s/
 12,533,760B complete.9files8,997,843B collected, SHA/size verified, no skips.
  All six library MOS numeric terminal probes resolve natively;5974points.
- X020.N max1.032371960V@41.085325ns versus original snload-both1.078641566V.
  Overshoot above0.99V falls88.64->42.37mV, but does not meet0.99V screen.
  Standard-cell36 physical pairs include23 exceeding; retained570 pairs230,
  some tiny values require magnitude/tolerance-aware interpretation, not
  changing pass threshold or counting all as equally severe. CMI2751..2755
  retained. VDD energy0.068339946pJ for this local0..41.5908ns fixture only.
- Control owner preparing paired waveforms/KCL/causal interpretation and next
  single-variable recommendation; no broader replacement or baseline adoption.
  Comparator history fixture remains in preparation. No new remote work,
  OA edits, commit, push or deletion.

### 2026-10-26 16:14 — Standard-cell cause review and paired-history preparation

- Reviewed control first-run report and native current figure: LIVE minimum
 -28.512mV originates with net extraction by original upstream PM drain;
  library input gates supply current at that trough. N upper-rail injection
  and later QUIET undershoot are separate events; total terminal currents
  are not labeled pure Cgd/channel components. Standard cells remain unsafe
  in this conditional first event despite reduced N overshoot.
- Authorized one local R0 between real LIVE driver and entire NAND A1 input,
  preserving library internals, Q1, loads and replay. Owner prepares package;
  no remote dispatch or broader migration. Updated standard-cell assessment
  with actual native SPICE/probe validation and remaining limits.
- Used Verilog-A language skill to review paired-history TB stimulus: only
  bottom rails and isolated marker driven; original feedback remains native.
  Reviewed phase/actual-input analysis and wrapper. One focused synthetic
  paired-history and invalid-phase test passed. Requested correction of
  stale recipe input/summary metadata before managed admission.
- No OA edits, baseline adoption, commit, push or deletion. Unrelated dirty
  Obsidian/10bit/tooling files preserved.

- History metadata corrected and final11 frozen input hashes per case verified.
  Negative-to-positive registered8e52c191b9fd0dad38d84e35d6cc930bdec2255f1ac3400eafa5337ce28c31b4;
  accepted worker112759, child112780, observed running196,820,992B RSS.
  Positive-to-negative registeredab5e7087826c40a466269f03113654c06f3f4155fb8a4d3a4ff77b76028284b0
  only, not submitted. Keep serial dispatch; no completed native result yet.

### 2026-10-26 16:29 — First history native complete; R0 queued

- sar8audit-comp-history-neg-pos-tt-v1 native completed558.015s, peakRSS
 332,746,752B,997,624,086B output. PASS and zero-error footer confirmed;
  SFE1131/VACOMP2435 retained. Functional/phase/precision verdict pending.
  Analysis accepted worker200756 under256MiB limit.
- Reviewed whole-A1 R0 package/analyzer and ran one focused test, passed;
 20 frozen hashes verified. Exact source R0 is rupolym17.13um/1um, with
  source-bias V/I~9.792kohm; new transient effective behavior not inferred.
- sar8audit-ctrl-stdcell-r0-ff-v1 registered
  f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a.
  Queue accepted worker204896, not admitted while history analysis active.
  Source/foundry inputs unchanged. Positive-to-negative history stays
  registered only until queue is free. No duplicate dispatch or parallel work.
- No OA, baseline, protected history, user notes or10bit changes; no push.

### 2026-10-26 16:40 — History first-polarity evidence and R0 comparison recovered

- Comparator neg-pos analysis completed308.375s/13,844,480B peakRSS.
 10files7,365,284B collected and SHA/size verified in1MiB chunks.154820
  native points; phase_valid/history_assessment_valid/protocol_eight_pass
  true. First actual input-56.250246mV, second+1.558021mV versus nominal
 +1.757813mV; actual CM449.591069mV. All8 writes correct in this conditional
  fixture, but-199.792uV charge-target deviation is not comparator offset.
  Owner preparing analysis; full stress/ADC qualification remains incomplete.
- R0 native20.194s/335,622,144B, analysis40.639s/12,558,336B completed.
 9files9,440,208B receipt verified, no skips. N overshoot42.372->18.683mV;
  LIVE undershoot-28.512->-30.133mV, filteredA1 minimum-9.857mV; QUIET
 -13.267->-9.211mV. Incoming/filtered10-90 slew2.539/20.086ps; filter
  halfrail delay4.351ps. KCL3.954pA, CMI retained; not a complete repair.
  Owner now prepares paired plots/current/time/energy interpretation.
- Positive-to-negative history submitted once worker276945 after R0 analysis,
  observed running315,633,664B RSS. No concurrent heavy analysis or new
  design adoption. No OA edits, push, deletion or protected-file changes.

### 2026-10-26 16:48 — Opposite history native complete; analysis waits for memory

- sar8audit-comp-history-pos-neg-tt-v1 completed524.647s, peakRSS
 317,272,064B, native PASS/zero-error footer; SFE1131/VACOMP2435 retained.
- Analysis submission accepted worker2598 but not admitted: host_memory_headroom,
  available6,618,181,632B and swap_free0 in the actual gate snapshot. Keep
  queued under existing limits; do not bypass or create another run.
- Comparator result-review chat hit model-capacity service failure; resumed
  same chat/checkpoint once without changing model or repeating simulations.
  Control R0 plot/cause analysis continues locally; reference/sampling
  checkpoints unchanged. No new circuit variants or protected-file changes.

### 2026-10-26 17:00 — Paired history recovered; next LIVE recovery diagnostic

- Queued pos-neg analysis admitted when memory recovered and completed
 290.933s/14,106,624B peakRSS.10files7,359,206B collected, allSHA/size
  verified, no skips.150636nativepoints;8 correct token writes and valid
  stimulus phase. Actual second input-1.558020336mV,CM449.590950mV;
  nominal target error+199.792164uV. Selected990 pairs0 exceed, full8742
  still incomplete. Both polarities now conditional-pass; owner combining
  report and partitioning pre-step history/coupling/post-step recovery.
- Read R0 completed cause report, viewed timing plot and comparator first/
  second-decision figure. R0 lowers N peak but widens main exceedance
 3.760->5.584ps and delays QUIET6.565ps. LIVE stress persists; total gate
  charge~0.755fC unchanged, slower exchange rather than stronger discharge.
- Authorized local-only LIVE NM multi1->2 diagnostic package, exact owner
  path added to plan. Preserve all other circuit/PWL/sample timing and
  measure upstream load, all previous stress/KCL/energy. No remote job yet.
- All managed jobs currently complete. No OA edits, baseline adoption,
  push, deletion or protected-file changes.

### 2026-10-26 17:20 — LIVE NM2 admitted to queue; comparator paired review closed

- Reviewed private-clone one-instance multi1->2 package and input-loading
  analyzer. One focused test passed,21 frozen payload hashes verified.
  sar8audit-ctrl-stdcell-r0-mn2-ff-v1 registered
  a262cf7214baa45720243b0252a0988d6c2ddcfcd391b9f1aebf571853927629.
  Submission accepted worker167139, not admitted due host_memory_headroom
  (available8,163,663,872B,swap_free0). Preserve queue/limits, no bypass.
- Reviewed comparator paired report and charge-stage plot. Negative-to-
  positive target gap decomposes+81.11/-276.58/-4.32uV at declared A/B/C
  endpoints; reverse case near mirror. This is voltage bookkeeping, not
  independent capacitance/memory/offset extraction. A is last exported
  native baseline-bottom sample, not claimed last solver point.
- Comparator keeps conditional paired-history checkpoint awaiting repaired
  switching interfaces. No additional simulations assigned. No OA change,
  adoption, push or deletion; unrelated dirty files remain untouched.

### 2026-10-26 17:38 — NM2 queue expired before simulation

- Exact original run rejected queue_timeout after host_memory_headroom stayed
  insufficient. No started_epoch or child_identity; this is not Spectre or
  circuit failure. Preserved2files1940B and verified receipt SHA/size.
- Read-only gate still fails: host available8,006,529,024B, account used
 1,338,138,624B, no conflicting simulation/analysis. No repeated submission,
  replacement ID, resource-policy changes or process termination.
- Plan now directs future resource checks through read-only gate; explicit
  re-admission only after actual recovery, preserving original failure.
  No OA/circuit/PDK/history/Obsidian edits, no adoption or push.

### 2026-10-26 17:48 — Read-only resource probe timed out

- Exact NM2 gate query returned transport exit124, no fresh resource
  snapshot. Transport receipt1793008059834457800.output.json retained.
  The timed-out action was read-only gate, not submit; original queue-timeout
  rejection remains the last confirmed execution state. No automatic retry
  or new remote job. Four owner checkpoints unchanged.

### 2026-10-26 18:14 — NM2 recovered after resource recovery

- Read-only gate passed with host available14,597,865,472B and no conflicts.
  Original v1 rechecked rejected queue_timeout, no child/start; preserved.
  Declared q2 ownership, verified21 identical payload hashes, registered
  sar8audit-ctrl-stdcell-r0-mn2-ff-q2 hash
 3b0e98474b6d0dc6e6a11484382c79e06d762e3a4d070c8134536097cedff31c.
  Submitted once, admitted worker23906; no policy relaxation.
- Simulation49.391s/337,760,256B peakRSS; analysis37.730s/13,385,728B.
  Native PASS, original CMI2751..2755/SFE1131/SPECTRE16780/VACOMP2435
  retained.9files9,399,303B recovered and SHA/size verified, no skips.
 6048nativepoints, missing_required_signals empty.
- R0->NM2 LIVE minimum-30.133->-24.549mV; X020.N peak1.008683->
 1.008098V. X001.N peak1.006273->1.005875V but falling slew7.681->
 8.484ps; sample-close-to-QUIET halfrail31.665->32.513ps. These are
  first-event diagnostics, not complete circuit repair. Selected failures:
  changedNM3/6, standard cells15/36, other core219/564 physical pairs.
- Control owner preparing paired figures/current/energy interpretation and
  targeted next suggestion; no additional remote experiment. Four chats
  checked, other checkpoints unchanged. No OA/adoption/push/deletion.
  Unrelated dirty Obsidian/10bit/management files preserved.

### 2026-10-26 18:21 — Reference upstream-stage preparation

- Four module checkpoints checked: control is analyzing recovered NM2;
  comparator/sampling retain conditional checkpoints, no new native results.
- Reviewed reference FF IO-C findings and exact GNNBN/GNNBP connectivity.
  C tolerance did not remove B36.131mV/A20.753mV excess. Authorized local
  preparation of B-only IO pair using validated C parameter sets, with A/C,
  load, reference/sample commands unchanged. Plan records exact owner paths.
- FF/SS packages will retain450-pair/KCL/energy screening and expose A
  loading plus speed tradeoff; provisional IO screen is not lifetime approval.
  Reference owner prepares locally while control finishes result interpretation.
  No remote job submitted; no baseline, OA, PDK, history or Obsidian edits.

### 2026-10-26 18:34 — B IO two-corner results recovered

- Reviewed exact two-instance B substitution and streaming analyzer; owner
  focused staged-analyzer test passed. Verified six frozen inputs per corner.
  Recorded managed ownership and registered/submitted sequentially:
  FF hash a89eda94b9e3b68db0598a21cbde394af33dd297f9c18f82d0ea9366df36aae6;
  SS hash ad9bc0c2c590427fac6d81ca47b273f278f6a3aec353b01309f11de733fab36e.
- FF simulation20.132s/304,549,888B peakRSS, analysis48.902s/16,539,648B;
  SS19.624s/304,467,968B and44.996s/16,494,592B. No concurrent heavy jobs.
  Collected11files each:3,988,387B and3,948,132B; allSHA/size verified,
  no skips.8496/8087nativepoints,447 required currents all initialized.
- FF B/C each worst1.199118V with no1.98V-screen exceedance; core A
  still1.009099V and6 strictly exceeding pairs. FF CMI retained, not repaired.
  SS450pairs zero exceed; A/B/C worst0.863165/0.959065/0.971107V.
  SS B-to-load off/on172.192/145.693ps; low-reference BN0 settles within
 1mV from48.975269ns. Keep high-reference ON window separate from46.995ns
  turnoff; native zero-error footer is not circuit acceptance.
- Sent both results to reference owner for concise paired plots/causes.
  Viewed control NM2 timing plot; owner finishing report without extra tests.
  No new baseline, OA edits, push, deletion or protected-file changes.

### 2026-10-26 18:41 — Control route after NM2 review

- Read completed NM2 report, retained paired waveform and source identities.
  Unified comparison remains237/606 failed physical terminal pairs; LIVE
  dip improves18.53% but below-1mV duration5.194->5.599ps and N main
  exceedance5.584->5.901ps. No pass or sole-conductance attribution.
- Prioritized repair over further fixed-input attribution: authorized local
  X001 LIVE-stage replacement by the same verified native standard NAND/INV
  pair used for X020, sourced from completed R0 MN1. Explicit owner paths
  added to plan. Keep external logic/PWL, load, sampling edges, other gates
  and solver fixed. Report internal node/parasitic changes and native current
  mappings; one focused test. No remote submission yet or new baseline.
- Reference owner continues combined FF/SS B IO interpretation; comparator
  and sampling retain conditional checkpoints. No OA, foundry, history,
  Obsidian edits, push or deletion. All managed runs currently complete.

### 2026-10-26 18:50 — Reference remaining A interface

- Reviewed combined B-stage report and PRE-to-GNN0 timing figure. Actual
  SS off/on propagation115.94/91.53->252.67/234.00ps includes both B and C;
  GNN0 negative excursion-77.163->-121.881mV remains explicit. FF A still
  exceeds19.099mV. ON settling and off-gap correctly kept separate.
- Authorized local A-only IO pair preparation from completed IO-BC fixture,
  FF/SS cold, exact paths in plan. Preserve B/C/real loads/all commands and
  sample edges; measure PRE input loading/source work, all terminal pairs,
  body currents and complete delay. Provisional IO screen is not SOA approval.
- Reference owner also identifies real PRE source/fanout from immutable
  netlist before future real-source testing. Ideal PRE candidate cannot qualify
  that interface. Control standard LIVE-stage package remains in preparation.
  No remote task, OA change, new baseline, push or deletion.


### 2026-10-26 19:07 — Standard LIVE and reference ABC IO recovery

- Completed standard LIVE replacement run sar8audit-ctrl-stdcell-live-ff-v1,
  hash a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226.
  Nine files9,416,094B verified;6053 native points,48 foundry MOS ports bound.
  LIVE dip improves-30.133 to-21.370mV, X020.N remains1.007966V;
 237/606 physical pairs still exceed. Native CMI retained. Control owner
  preparing concise current/timing comparison; standard-cell substitution
  alone has not fixed the interface.
- Reference A-only IO FF run sar8audit-refcell-ioa-ffcold completed:
  hash f1e6dd17f97789e692fb6f9a988804048275ba32cefcbe414c9265952544f4f1.
  Eleven files4,121,724B verified with1MiB streaming SHA checks;
 8410 native points,447 currents initialized. A/B/C worst terminal
  differences1.162828/1.162828/1.140901V, below provisional1.98V screens.
  Remaining12 strictly exceeding pairs belong to reset comparator, maximum
 2.933uV beyond0.99V; original CMI2754/2755/2756 retained.
  PRE-to-GNN0 off/on119.562/88.048ps, GNN0 minimum-30.565mV.
  PRE is ideal: real X025 and shared L0 fanout remain untested.
- Serial SS run sar8audit-refcell-ioa-sscold registered once, hash
 327a9455d983dfa17c1d72eb7ba456af43b7539f007e80ee7633c4133413e283.
  Native completed20.075s,306,479,104B peakRSS; analysis worker302941
  active at checkpoint. No parallel heavy jobs or repeated submissions.
  Parent owns recovery; reference owner preparing paired interpretation.
  No OA edits, adoption, push, deletion or protected-history changes.

- SS follow-through: analysis completed50.012s/18,599,936B peakRSS;
  eleven files4,037,948B allSHA/size verified, no skips.7915 native points,
 447 currents initialized,450screens no exceed. A/B/C maxima
 0.960077/0.960077/0.960807V. PRE-to-GNN0 off/on402.956/375.908ps,
  GNN0 minimum-120.084mV; low BN0 reaches/stays within1mV at49.117648ns.
  Sent both results to reference owner for short paired report/plot and
  real-driver fixture proposal. All heavy jobs now complete; no new run queued.


### 2026-10-26 19:10 — Continue standard-cell reset interface

- Reviewed control standard LIVE table and parallel waveforms; dip magnitude
  improves29.08% but width5.194->5.555ps,237/606 screens still exceed.
  At LIVE minimum, native PM drain extracts3.645uA, NM/R0 restore2.090/1.555uA;
  KCL supports net exchange but not intrinsic Cgd/channel decomposition.
- Authorized local XCLOCK.X000 RB inverter replacement only, keeping real
  CLOCK_RESET driver and SR fanout. RB-25.523mV and incoming CLOCK_RESET
  about+24mV remain independent measured issues; no claim either is repaired.
  Exact owner paths added to plan; no new managed remote job yet.
  Reference paired ABC report in progress; comparator/sampling checkpoints
  unchanged, await actual repaired interfaces. Unrelated dirty files retained.


### 2026-10-26 19:20 — Restore actual reference PRE interface

- Read io_astage_findings.md and inspected BC_to_ABC_cold_timing.png.
  ABC screen clearing reflects IO voltage capability, not removal of overshoot;
  retained negative excursions, body-port current, ideal PRE burden and SS delay.
- Authorized local reference fixture restoring original core X025 plus shared
  L0-driven GPP branch and physical load. Boundary moves to logical L0;
  remove ideal PRE/GPP output force, retain original sample edges and allow
  actual delay to emerge. Original BBM source remains unqualified explicitly.
  One mapping/load/measurement test; parent controls later managed runs.
- Control RB standard-cell preparation remains active; no duplicate dispatch,
  no heavy remote task queued, no OA/protected-history changes or push.

- RB package owner confirmed focused test passed and final freeze
  d4f3a5fea3e3d2043e58643da2a923bd74d172b092bd10116ff10c30be2b6e42.
  Parent reviewed builder/analyzer/test, verified all23input hashes once,
  registered and submitted sar8audit-ctrl-stdcell-rb-ff-v1 once, managed hash
 745d10a01ded0cc487e7d2e5ff4ba57d130f7de2ec4e2959979f937375524bc4.
  Worker63905 admitted;1thread1GiB simulation,256MiB analysis,32MiB collection.
  No other heavy job; target is local reset inverter only, not whole ADC.

- RB run follow-through: native18.982s/335,695,872B peakRSS;
  analysis38.865s/13,365,248B. Nine files9,487,824B verified by1MiB SHA
  streaming;6065native points. CMI2751..2755 retained, native zero errors
  does not qualify circuit. RB dip-20.571mV, max0.994650V; incoming
  CLOCK_RESET1.014622V, SR_QB max1.002319/min0.877998V and SR_SN
  max1.001749V.237/606 physical pairs still exceed. Release4.712ps;
  reset assertion absent, not treated as zero delay or reset pass.
  Sent result to control owner for concise waveform/current comparison and
  ranked remaining causes. All remote jobs complete; reference real-PRE
  fixture in local preparation. No baseline/OA/protected file changes.


### 2026-10-26 19:40 — Real PRE pair submitted; reset NAND preparation

- Reviewed real PRE builder/analyzer and focused test handoff. Verified7input
  hashes per FF/SS case (312,423B), restored8 original X025/GPP MOS with
  actual shared L0 gates and removed ideal output forcing.498pairs478currents,
 14KCL152native columns. Parent exact managed paths declared before registration.
- FF run sar8audit-refcell-realpre-ffcold hash
  c9909243ed203316d852a034eb18d5552a4a631aa925158124f1377f5e4c969f:
  native20.715s/302,931,968B completed, CMI2751..2756 retained;
  analysis worker157981 active. SS registered only, hash
 0809de01ca6223f739f43ecc47f84111b0eb74ad6777968445763ffe109f7a42,
  to execute serially after FF analysis. Native success is not electrical pass.
- Reviewed RB report and plot; lower RB dip accompanies larger rebound and
  persistent CLOCK_RESET+24.622mV. Authorized local-only X023.X002 ND2D1
  replacement, preserving AB/A1,BB/A2 and real upstream INV/downstream SR.
  No further RB sizing or full-chain substitution. Control owner preparing.
  No OA/adoption/push/deletion or protected-history edits.

- Real PRE pair recovery complete: FF analysis59.467s/18,497,536B peakRSS,
  SS native20.608s/302,858,240B, analysis56.253s/18,477,056B.11files each
 7,253,880/7,162,427B verified SHA/size with1MiB streams, no skips.
 9237/8848native points,478 required currents initialized both cases.
  FF42/498exceed: X0256/12(max1.009124V),GPP24/36(max1.056699V),
  reset-comparator load12; IO GNN0/36. FF CMI retained, SS noCMI and
 498screens clear. Actual-model screens unchanged; not full-chain acceptance.
  SS GNN trails GPP353.556/348.255ps, GNN0-120.037mV, lowBN0 within1mV
  from49.125324ns. Sent both cases for concise cause comparison; no additional
  remote run submitted. Original BBM source still ideal/unverified.


### 2026-10-26 19:50 — CLOCK_RESET source-stage test

- Reviewed frozen reset-NAND builder/analyzer, owner focused-test handoff;
  verified24inputs once and kept same source recipe358c53c6...0736a.
  Registered/submitted sar8audit-ctrl-stdcell-resetnand-ff-v1 once, managed
  hash7f60d766e2c8f6f4b964d5744cdd1442292e7f86485596b8374694a5ec616c9d.
  Native completed18.820s/335,745,024B peakRSS, CMI2751..2755 retained;
  managed analysis started after simulation, no simultaneous heavy job.
- Added user-provided overdrive-recovery analogy to interpretation scope:
  separate edge-localized exchange from post-edge current deficit/recovery
  using existing native V/I first. No triode/channel/diode attribution without
  operating-point or component-current evidence, no extra simulation yet.
  Reference owner continues current paired report with this distinction.
  No OA, baseline adoption, push, deletion or protected-file edits.

- RESET NAND run recovered: analysis41.378s/13,406,208B peakRSS,
 9files9,448,118B allSHA/size verified,6058native points,missing[].
  CLOCK_RESET1.010340V,RB-18.144mV/0.994724V,SR_QB0.877733..1.001974V,
  release5.008ps.245/606 physical pairs exceed vs237previous; sent exact
  result to owner to distinguish additional tiny violations from major peaks,
  verify72native library ports and assess current/bias-based recovery.
  No next gate replacement prepared or authorized. Reference actual-PRE
  interpretation continues; all heavy jobs complete. No OA/adoption/push.


### 2026-10-26 20:10 — Charge storage versus edge coupling

- Reviewed real PRE feedback and control QB/MID waveforms. Reference has
  leading driver-port charge redistribution plus60-150ps downstream return
  current; total terminal currents do not establish triode/channel/diode split.
- Control QB continues falling after RB90%; MID absorbs4.365fC after that
  edge, with20.415uA capacitor current30ps after QB minimum and~132ps QB
  stable recovery. This supports internal-node charging/charge sharing,
  distinct from the few-ps rail spikes. No wrong CLOCK_Q transition observed.
  Additional8failed pairs are13.8-83.3uV tail events, not8new20mV spikes.
- Authorized one local CMID multi2->1 experiment for control and one local
  GPP driver-block3core stages->1IO inverter experiment for reference.
  Logic polarity and ADC architecture remain; actual delay/load must be measured,
  no internal edge compensation. Exact paths/measurement boundaries in plan.
  No remote jobs, no baseline/OA/foundry/history changes or push.

### 2026-10-26 20:24 — QB storage single-variable dispatch

- Reviewed private target cloning and native streaming storage observer. Owner
  focused test passed; all25 input hashes and final recipe identity verified.
  Only XCLOCK.X003.CMID multi2->1; all127 other instances and11PWL unchanged.
- Registered/submitted sar8audit-ctrl-stdcell-qbcap-ff-v1 once, managed hash
  e51627eebe5435844411e185bfd80f38eb3a2ded3796abf95bdfd4c955c5a7ee.
  Managed gate admitted1thread/1GiB; simulation running. Keep original606
  physical screens and CMI; no inferred transistor region or ADC acceptance.
- Reference GPP handoff had stale unrelated final text; requested completion
  of existing focused test/freeze/note only. No duplicate task or experiment.
  Protected edits preserved; no OA, adoption, push or deletion.

- QBcap native run ended before circuit parsing: exit2 after31.302s,
  peakRSS42,795,008B. spectre.out explicitly reports SPECTRE-209 license
  checkout failure (5280@thu-han), despite +lqtimeout60. No circuit/waveform
  result and no analysis launched.3files6023B recovered without skips.
  This is license availability, not a circuit regression; retain exact failed
  identity and do not blindly resubmit under another ID. Other local work continues.
- Failed-run receipt3files6023B independently SHA/size verified. Reference
  GPP singleIO package now ready; read final note and verified both seven-input
  sets (FF426b80e4...fdc8,SS9d65f0c0...9674). Owner focused test passed;
  parent prior builder/analyzer review remains valid. Hold remote launch while
  license checkout is unavailable; package remains unchanged and locally ready.

### 2026-10-26 20:30 — License checkout recovered, GPP comparison running

- Bounded read-only license status showed server/vendor UP and available
  Spectre X feature capacity. This did not itself prove checkout capability.
  Existing reviewed GPP FF package registered and submitted once; hash
  f75375b04ba9631de7d93636fb5323717ec57046cc6da0068688e56b22bfb3b0.
- FF native completed21.517s/302,968,832B peakRSS, exit0/zero-error/PASS.
  CMI2751/2754/2755/2756 retained; native disabled multithreading for small
  circuit. Analysis started serially. This successful run proves checkout
  worked now, not that previous failure was electrical or that ADC passes.
- SS package registered only while FF analysis runs. QBcap failed identity
  remains intact; no duplicate or automatic retry of that run.
- GPP FF/SS pair collected11files each6,013,768/5,992,515B, allSHA/size
  verified by1MiB streams, no skips. Native8844/8346points and462currents
  initialized. Analysis56.942s/18,165,760B and51.773s/18,182,144B.
  Owner now preparing paired comparison with restored-PRE source.
- Following two successful native checkouts, known failed QBcap-v1 remains
  read-only. Registered/submitted exactly one q2 recovery with identical25
  inputs/solver/resource settings and explicit provenance; managed hash
  ae800c95066a921a5df6e9101c29adecdf7a6e761cac71b1490ed0f1b30920b0.
  SS analysis finished before q2 simulation launch. No uncertain duplicate.
- QBcap q2 native completed50.668s/335,884,288B with CMI2751..2755,
  managed analysis45.166s/13,545,472B.9files9,473,260B independently
  SHA/size verified,6059native points. QB minimum0.917302V/recovery70.734ps
  and postRB90 cap1.906870fC versus source0.877733V/131.898ps/4.365fC.
  RB dip-18.149mV and CLOCK_RESET1.010339V essentially unchanged;
 245/606 physical pairs still exceed. This supports separate storage-recovery
  and edge-overshoot mechanisms, not full repair. Owner preparing comparison.
  No heavy job active; all protected areas unchanged, no adoption or push.

### 2026-10-26 20:42 — GPP tradeoff review and real boundary restoration

- Reviewed paired GPP report and both edge/settling figures. Provisional IO
  screens clear for GPP, but FF output -0.240667..1.270576V and SS
  -0.290528..1.115649V are larger rail excursions. X025 FF still1.009120V.
  Latest low-reference1mV settling changes only~4ps; L0 absolute edge charge
  grows FF2.465->3.661fC and SS1.740->2.235fC. No full-chain acceptance.
- Reference report preparation hit model capacity, resumed same chat once;
  existing artifacts retained. Parent authorized original L0 source/fanout
  restoration as next local fixture, avoiding optimization against ideal source.
  Only boundary restoration, no simultaneous X025/sizing changes; exact local
  paths in plan, remote ownership follows package. Control comparison ongoing.
  No remote heavy job active, no OA/adoption/push or historical edits.

### 2026-10-26 20:50 — Restore real L0 source

- Reviewed new builder/native measurement once and owner focused-test handoff;
  both seven-input frozen sets verified. Original L0 fanout has four gates,
  all retained; only original two core source MOS added,142 records alias-only.
  N preceding NAND output remains ideal, actual internal delay uncorrected.
- Registered FF05a160866e5f9d0a2c8a870c1fdda9150735713fab975613e192848cb8cd4ac1
  and SS5a871ba335820094f7e7d7aa87e61b15aeae21dccdd1a057fdb333b0ba6f95a2.
  FF native complete22.220s/302,989,312B with CMI2751..2756; analysis active.
  SS registered only. Control report hit model capacity, resumed same chat once.
  No new baseline/OA/protected edits, push or deletion.
- FF collection11files6,600,138B independently verified,8966points and470
  initialized currents. Real source L0-15.858mV..1.007959V, PRE-20.116mV..
 1.016824V,GPPDRV-247.953mV..1.327264V. Source-stage stress remains visible.
  SS initially queued behind another detected Spectre process, then admitted
  normally: native20.648s/303,030,272B, analysis62.826s/18,468,864B.
  Collection in progress; no concurrent heavy job or queue bypass.
- Reviewed QBcap table and same-axis figure. Authorized only XB CLOCK X003
  NM input-order local comparison Q-upper/RB-lower on multi1; preserve PM,
  sizes/stimuli, exact gate-current/KCL remapping and full-SR coverage gap.
  Exact local paths in plan. No fresh control remote job yet.
- SS collected11files6,490,553B SHA/size verified with1MiB streams,no skips;
 8527points470currents initialized,noCMI,SFE1131/VACOMP2435 retained.
  Both real-L0 results sent for source/load comparison. No active heavy job;
  next control package remains local preparation. Scoped diff check clean.

### 2026-10-26 21:04 — Consolidate reference boundary restoration

- Reviewed real-L0 final paired report, voltage and current figures. FF L0SRC
 6/12 screens fail; X0256->10/12. Leading-edge charge flows from source
  drains into X025/GPP gates; no unsupported intrinsic-capacitance attribution.
  Full BBM input remains unverified; SS486screens clear is only scoped evidence.
- To avoid repeated gate-by-gate boundary restoration, authorize one local
  complete original bit0 CODE-to-H/L BBM fixture, actual two legs/fanout/high
  drivers as needed, current low driver variants unchanged. No internal ideal
  gate forces, no delay compensation, external sampling contract unchanged.
  Exact paths/limits in plan; parent reviews once before managed submission.
- Control QB NAND gate-order preparation continues; no duplicate request/run.
  No remote heavy jobs, adoption, OA, protected edits, push or deletion.

### 2026-10-26 21:12 — QB NAND gate-order native test

- Parent reviewed exact two-gate cloning, actual RB/Q loading/KCL/stress maps
  and native observer; owner focused test passed,26 input hashes verified.
  Registered/submitted sar8audit-ctrl-stdcell-qborder-ff-v1 once, hash
  c933758028b599adad5e3ab700a3e610424c2ab10133ccbaa33ead845fd87ce4.
- Native complete20.879s/335,855,616B with zero-error/PASS. CMI2751..2755,
  SFE1131,SPECTRE16780,VACOMP2435 retained; analysis now running serially.
  Reference complete-BBM local preparation continues. No adoption or OA edits.

### 2026-10-26 21:16 — QB gate-order result recovered

- Analysis complete52.221s/13,512,704B. Collected9files9,440,613B;
  SHA/size verified with1MiB streams, no skipped files. 6051 native points,
  all required signals present. Managed run identity unchanged.
- Compared to QBcap-q2, QB minimum0.917302->0.989612V, recovery from minimum
  to stable1mV70.734->16.442ps. QB positive excursion remains10.185mV;
  RB minimum-18.074mV and RESET peak1.010340V persist. 237/606 physical
  terminal screens fail versus245; all native CMI warnings retained.
- Sent verified results to control owner for paired report/current evidence
  and full-SR coverage recommendation; this window has no Q state transition.
  Reference complete-BBM package preparation continues. No active heavy job,
  no baseline adoption, OA edits, push, deletion or unrelated changes.

### 2026-10-26 21:23 — Complete bit0 BBM isolation running

- Reviewed boundary inventory/builder/analyzer and focused-test coverage once.
  Seven inputs/corner434,235B hash/size verified; original40 BBM primitives,
  14 H-driver MOS,142 unchanged mapped leaves. CODE is only ideal reference
  logic boundary. Exact managed paths added before registering FF/SS.
- FF sar8audit-real-bbm-ffcold native complete26.068s/304,549,888B,
  zero-error/PASS; CMI2751..2756,SFE1131,VACOMP2435 retained. Analysis active
  at72s/16,977,920B; SS registered only, awaiting serial FF analysis/collection.
  Managed hashes recorded in plan. No duplicate or simultaneous heavy run.
- Control paired report still in progress, no repeated dispatch. No adopted
  baseline, OA edits, commit, push, deletion or protected-file changes.

### 2026-10-26 21:33 — Full BBM FF recovered; settle-window distinction

- FF11files22,435,355B verified by1MiB SHA streams, no skips;11326points,
  analysis91.405s/22,376,448B. H/L half-rail nonoverlap130.413/148.175ps,
  but these are logic diagnostics, not transistor conduction proof. FF CMI
  persists; SS native32.819s/309,391,360B complete without CMI, analysis active.
- Identified high-state settling metric ending after next CODE transition:
  its +28.19/-10.39mV at48.06785ns must not be labelled failure to establish.
  Independent native stream shows BN/BP -0.027861/+0.005474mV at44.003432ns,
  -0.000009402/+0.000001969mV at47.993432ns, then +24.519/-8.894mV at
  48.059915ns. Owner to distinguish pre-command settling and switching kick
  in new report, retaining original raw/derived results unchanged.
- Reviewed control gate-order report and figure.16.442ps includes positive
  peak decay; screen245->237 is12 removed/4 new. Authorized precise local
  full-SR two-direction fixture with actual drives/fanout and truth-table
  check before assuming priority. No new control remote run, no adoption/OA.

### 2026-10-26 21:41 — Complete BBM paired results recovered

- SS analysis86.144s/22,380,544B;11files22,627,864B verified by1MiB SHA
  streams,no skips;10975points. All738 actual-model terminal pairs below
  provisional screens,noCMI (SFE1131/VACOMP2435 retained). H/L half-rail
  gaps185.134/221.390ps; GPPDRV-0.248573..1.090772V still has rail excursions.
- Independent native samples confirm SS high established before next CODE:
  47.989410ns BN/BP errors-0.000015967/+0.000012166mV;52ns low errors
  +0.000012226/-0.000016032mV. Paired interpretation/source-current figures
  delegated to reference owner, including prior high-window endpoint artifact.
- FF213/738 fail:BBM121,Hdriver70,other22; largest BBM |Vgd|1.062566V
  at XD_HD.X005, H-driver GPNCN |Vds|1.058000V. Additional physical coverage
  forbids raw fail-count comparison against old486-pair fixture. No adoption.
- Control full-SR local preparation hit model-capacity failure; resumed same
  chat/checkpoint once, no new chat/model/remote experiment. No active heavy
  job, no OA changes, protected edits, commit, push or deletion.

### 2026-10-26 21:51 — Reference timing and stress separated

- Read full-BBM paired report and viewed all three native-time figures.
  Pre-next-CODE high settling FF BN/BP43.583991/43.391137ns,
  SS43.938057/43.990761ns. Prior halfVDD-end errors are transition residues.
- SS BBM positive185.134ps becomes N gate -191.747ps after unequal real
  drivers; simultaneous opposed total D currents ~10uA observed, without
  claiming channel-only shoot-through. FF RC1 kick is simultaneous with
  MP_CLEAR release: HD leading D output~0.436fC into C1/R1/X005 gate loads,
  consistent with terminal charge exchange; no intrinsic-capacitance split.
- Authorized one local HD C0 MOMmulti1->4 paired test to probe actual high
  selection delay, all other primitive/stimulus/sample-contract values fixed.
  Preserve RC1 stress and two-direction reset checks; no predicted pass claim.
  New precise child paths recorded in plan. Control full-SR preparation active.
  No active heavy job or new remote submission; no adoption/OA/push/deletion.

### 2026-10-26 22:01 — RC1 receiver/source stress cross-check

- Existing frozen FF scalar evidence shows HD X005 NM |Vgs|1.059705V,
  both X005 |Vgd|1.062566V; its PM |Vgs|1.008802V reflects RC1 negative
  excursion too. MP_CLEAR |Vds|/|Vbd|1.008802V also fails, although its
  |Vgs|/|Vgb| remain0.99V. Replacing only the RC1 receiver cannot by itself
  close all source/receiver stress. No new component change authorized here.
- Reference C0 single-variable and control full-SR local packages continue;
  no repeat dispatch, no active heavy job, no duplicate simulation or adoption.

### 2026-10-26 22:12 — HD C0 comparison submitted

- Reviewed one-cap builder, additive physical-window/reset analyzer and owner
  focused-test evidence.8 frozen inputs/corner442,695B SHA/size verified;
  exact managed paths recorded before registering both cases. FF submitted
  once, native27.839s/316,284,928B zero-error/PASS with CMI2751..2756,
  SFE1131/VACOMP2435; analysis active. SS registered, not submitted yet.
- Control SR truth-table/drive/fanout and functional analyzer reviewed; its
  declared80MiB collection exceeds user32MiB. Asked owner to adjust only
  exports/budget while preserving raw439 currents and606 full-history screens.
  Reference execution continues independently. No duplicate run/adoption/OA.
- FF analysis complete89.594s/22,286,336B,11files22,574,580B SHA/size
  verified,11421points. High BBMgap244.612ps,N/Pgate153.710/218.538ps;
  low direction unchanged. High BN/P established43.698327/43.505600ns,
  low48.451840/48.585732ns. Sent results for paired interpretation; SS
  submitted once and native running serially. No qualification/adoption claim.

### 2026-10-26 22:20 — SS analysis and standard-cell scope clarification

- HD C0x4 SS native28.399s/309,510,144B complete without CMI;
  SFE1131/VACOMP2435 retained. Submitted managed analysis once,worker87954.
- User asked whether all digital gates are standard cells. Verified current
  control candidate: X020 and LIVE each NAND+INV, RB INV, RESET final NAND;
  six native cells/18MOS total in this fixture. SR feedback/set qualification,
  other gates and reference BBM remain custom. Experimental netlists are not
  adopted whole-ADC or OA replacements. Control export-budget update active.

### 2026-10-26 — Standard-cell implementation becomes digital mainline

- User recommends full standard-cell digital replacement. Updated module plan
  and sent control/reference owners complete mapping/boundary assignments.
  Custom gates were retained for causal diagnosis, not a final implementation
  advantage. Hold unsubmitted custom SR-cycle pair at its checkpoint.
- Finish in-flight C0 recovery only; prioritize equivalent standard-cell logic,
  reset priority, async handshake and real-load timing. Analog circuits and
  timing/voltage-domain interfaces require their own implementation contracts.
- Updated only sar8 heartbeat to preserve this steering. No OA, adopted
  baseline, original foundry content, commit or push changes.

### 2026-10-26 22:30 — Mapping active; SS status transport unavailable

- Control/reference owners are actively preparing standard-cell migration and
  interface inventory; no duplicate assignment or custom-gate run submitted.
- Read-only status for sar8audit-bbm-hdc0x4-sscold failed first with SSH banner
  timeout, then one bounded retry returned forwarding No route to host.
  Transport records 1793024988475916100 and 1793025014748824400 retained.
  Analysis worker87954 completion remains unknown, not marked failed or rerun.
  Local mapping work continues; reference owner informed. No OA/baseline change.

### 2026-10-26 — User-requested SSH path diagnosis

- Effective OpenSSH configuration: PC -> thu-han (101.6.68.50:22) ->
  thu-wei:22 via ProxyJump. Earlier channel-open No route to host was on
  forwarded target connection; it is not a Virtuoso/PDK/license failure.
- Bounded fresh direct jump and target probes now return Connection refused
  from 101.6.68.50:22. Jump-side hostname/getent/ping commands did not execute.
  Current first-hop refusal prevents any conclusion about thu-wei OS health,
  resource consumption or completion of pending analysis worker87954.
- No new simulation/analysis submitted, process killed or service restarted.
  Preserve in-flight identity and continue local standard-cell mapping work.

### 2026-10-26 — User confirms server outage

- All four owners notified: local work only, stop at server-dependent steps.
  No further SSH/Bridge/status/collection attempts until user confirms recovery.
- sar8 automation updated to finish local mapping/checkpoints then pause;
  existing SS analysis identity retained as unknown, no kill or resubmission.
  No remote action, circuit change, commit or push performed.

### 2026-10-26 — Stage report and scheduled follow-up paused

- User requested stage report and stopping timer. Tool confirmed sar8 PAUSED;
  other automations unchanged. Four module chats all idle at local checkpoints.
- Reviewed completed control migration inventory (174 maximal replacement
  blocks:118 combinational,24 registers,2 SR,30 timing) and reference boundary.
  DFF semantics/library version and timing interfaces still require validation;
  no full standard-cell candidate or adopted baseline exists.
- Reviewed C0x4 FF report: high-direction gate gap increased, peak stress not
  repaired; X005 Vgd1.062579V and >0.991V duration141.989ps (old70.601ps).
  SS native previously complete, analysis/recovery unknown due outage.
- Stage report separates sampling/comparator conditional evidence from whole
  ADC qualification and old027b951 FFT. No remote operations/commit/push.

### 2026-10-26 — User session evidence points to home mount/login services

- User reached thu-jin (101.6.70.7), then authenticated to thu-wei
  (192.168.184.60). Both sessions report missing /home/chenzc_intern25;
  missing .ssh/known_hosts follows from that missing home. thu-wei additionally
  reports user-596.slice not loaded and sudo_resource_limit.sh exit1 during PAM.
- Read-only historical inventory observed2026-10-25T07:47:04Z records home
  mounted by NFS4 from thu-qin:/net/thu-qin/disk13/home/chenzc_intern25,
  server192.168.184.50. Missing mount/export/autofs or storage reachability is
  a leading hypothesis, not verified current cause or evidence of data loss.
  /server_local_ssd was a separate local XFS filesystem in that snapshot.
- User-supplied alternate-path login proves that path reached authentication;
  original thu-han route health and pending worker completion remain unknown.
  No remount/mkdir/service restart/job submission performed. Resource-limit
  initialization failure requires admin review before further compute work.

### 2026-10-27 — User-authorized restored-server check

- SSH managed run-status succeeded for sar8audit-bbm-hdc0x4-sscold with matching
  recipe0637635277e9c930917f811951e9de090ab01cdeee85810a60b573c4cf638973.
  Native and analysis both complete/exit0; analysis84.847s,peak22,298,624B.
  Status is not electrical qualification; collection/review still pending.
- No Virtuoso/CIW required for this path. No new sim/analysis, OA mutation,
  owner dispatch or automation resume; sar8 remains paused.

### 2026-10-27 — SS recovery and standard-cell implementation resumed

- User authorized continued SSH/Spectre netlist work; Virtuoso/OA excluded and
  timer remains paused. Control preparing full candidate and SR/DFF evidence;
  reference completing paired C0 diagnostic, each within existing owned subtree.
- Collected SS C0x4:11files22,387,216B,no skipped; streamed SHA/size verified,
  10861 native points, analysis complete. High N gate gap -35.697ps vs original
  -191.747ps; physical high BN/P 1mV settling44.048998/44.140323ns, low
  49.364107/48.974242ns; both delay legs reset under existing diagnostic.
  Remaining negative half-rail gap is not equivalent to a channel overlap claim.
- Main review notes ordinary paired core inverter drivers cannot be exempted
  from digital migration merely because their load is analog; owner to map
  those or state a specific voltage/interface reason. Source full baseline
  remains b9bf9f... and must not silently inherit later IO diagnostic variants.

### 2026-10-27 — VNC/login support, separate from SAR8 execution

- Read-only SSH through thu-jin confirms home accessible and thu-wei
  user-596.slice active,48GiB limit. Both hosts uptime indicates prior-night
  restart. Shared shell warning reproduces on thu-jin; no profile edits.
- Old thu-jin:24 log copied to .log.pre-20261027-recovery, SHA matched.
  A single display24 start was refused by existing single-session policy;
  no bypass/retry/kill. Fresh observation finds existing display3,PID23203,
  started08:16:37,GNOME processes running,TCP5903 listening. This successful
  session is not attributed to our refused attempt. User given new endpoint.
- Details in plan/2026-10-27-vnc-recovery/plan.md. No OA/circuit change or
  compute submission. Viewer access and residual login warnings remain distinct.


### 2026-10-27 native standard-cell dispatch

Original reference bit0/C0multi1 native INV/NAND candidate registered and run as sar8audit-ref-bbm-stdcell-ffcold-v1 (managed hash a7b09f5868cf81605a7ad3ff8b2fb7696b36dca88b19ec7cd20f13a61e3e1e8b). Native complete26.704s/peak345026560B; analysis complete82.220s/peak22736896B. Collected11files21843637B; parent streamed all hashes/sizes. FF213/738 strict pair failures remain; NAND MM4|Vds|1.108483V at43.026695ns; HD X005 library receiver|Vgs|1.061799V at43.005ns. Physical high/low reference1mV settling alltrue, not qualification. SS paired native complete21.671s/338812928B with noCMI; analysis in progress.

Control full native standard-cell candidate and26context storage fixture frozen/reviewed; FF/SS inputs verified and registered under sar8audit-ctrl-stdfull-storage-{ff,ss}-v1, not yet submitted at this checkpoint. Source original-core reference ADC; explicit first-level fanout/RC load scope and downstream cutoff. All remote execution serial; timer remains paused; noVirtuoso/OA/PDK/oldsource edits or commit/push.

Reference stdcell SS collection complete11files22126021B, parent SHA/size verification; analysis79.314s/peak22675456B,0/738 terminal failures, high N halfrail off-to-on gap -209.799ps. No claim of nonoverlap/wholeADC qualification. Control storage FF now admitted/running, SS registered waiting; no second heavy job.

Storage FFv1 hit output_size_limit at2151981342B/79.347s; raw retained, four failure evidence files27169B collected. No complete native transient or electrical verdict despite child exit0. SSv1 not submitted. Authorized measurement-only v2 preparation: fullvoltage/stress/function retained, targeted currents, original budgets. No circuit/timing change.

Storage measurement-v2 registered: FF managed351d0c4ca4e27bd33dccbe0057e92e1f2146e5f4ba2ca5619983749217407596, SSface837cd8445d0c1aa1a9071be97485af9774861a188fdd4a492971ea8020e4.16 frozen inputs per corner verified;89I retained/all980V unchanged. FF native complete239.494s/356433920B peak/1379493156B output, zero-error footer, CMI retained; managed analysis running. SS submitted once with --queue, correctly waiting for existing analysis. Reference L-swap frozen recipe6ea8073b... registered managed2b62fa1e5f736c747ecc25f8573280df23276f5d6e69705b873865874b7bf99b, not yet submitted. Parent inspected all4 native reference comparison figures and detailed mechanism report.

FFv2 source simulation retained complete. Exact old analysis child was gracefully terminated after identity verification; analysis failed exit-15 after883.005s,peak42663936B; cancellation receipt preserved. Fast equivalent reducer registered analysis-only3a52e63451d7563e5938829b9df8efd6a6b27b4d66ca8064333ea72e2f536f40 and dispatched. SSv2 queue-only rejection preserved; identical q1 native complete225.959s,peak354189312B,1424264047B output, zero-error footer and noCMI. SS electrical analysis pending. No OA or timer changes.

FFv2 fast analysis-only complete423.540s/peak83197952B,8files23313357B collected with managed SHA/size validation. All30060 native points preserved;26context stable hold and expected Q edge patterns pass. Strict terminal screen fails7596/11220pairs; worst DFF MM64|Vds|1.105788V at5.031257ns. Native CMI retained; not wholeADC qualification. SSq1 source-bound fast analysis registered5457100df99d4f68409118c9d7e4dab6972f6788d7719b419cf095124763e353 and queued behind Lswap. Lswap native complete22.726s/338567168B,397710817B output; analysis in progress. No new circuit baseline or OA adoption.

Lswap FF complete/collected11files21911695B,analysis81.489s/22556672B. Parent reviewed report and both figures: L MM4 CODE-rise maximum1.108483->0.731909V, old negative stack mechanism suppressed; full-window maximum now0.992307V at48.123404ns (D0.993660,S0.001353), so residual2.307mV remains. H unchanged1.105306V; HD RC1max1.061799V unchanged. Strict213/738 and >1mV197/738 counts unchanged, not full repair. Both reference states remain inside1mV before command deadlines. Report reference/standard_cell_bbm_lswap_v1/comparison/report.md. Next minimal reference candidate would swap H only on this Lswap source, then reassess separate RC and transient residue; not adopted or automatically dispatched.

SSq1 fast analysis-only complete423.222s/peak81379328B;8files23867269B collected, managed size/SHA validation and no skips.31020 native points,26contexts stable hold and expected Q patterns alltrue,0/11220 terminal failures,noCMI,source raw unchanged. This completes paired storage smoke, not full controller/ADC/Miller-load signoff. All dispatched heavy jobs ended; only targeted FF DFF joint-node evidence preparation remains. Timer remains paused.

Parent reviewed storage FF timing/event zoom/class plots and SS timing/event zoom. Both26contexts/502stable phases and all expected Q patterns pass; FF7596strict/7348>1mV diagnostic pairs,SS0 with maximum0.959787487V. First logged MM45 microvolt alarm is about0.990003ns, not DC; preserved separately from MM64maximum5.031257ns. Accurate attribution is native DFF internal device in reference-store context, not reference analog switch. Generated results README is report entry; instantaneous/average source-power numbers are fixture-only, no ADC1mW comparison. Full control/ADC remains unqualified.

Targeted MM64 native export completed129.902s/peak10752000B,5files10789529B collected with managed hashes. Full30060points/rawSHA and all6terminal statistics exactly match FF source. At5.031257327ns:D0.988246124V,S-0.117541916V,G0.000332838V,B0,Q0.989995087V; VDS1.105788040V. VDS>.99 interval estimate5.021254939..6.011584995ns (0.990330056ns),970 native points. This is persistent negative internal node with normal-high drain, not a1.106V drain spike; causal current decomposition remains unknown because MM64 intrinsic currents unsaved. Source/OA/PDK unchanged; no new simulation. Parent requests one short joint-node figure/report addition, no additional experiments this batch.

Parent inspected final MM64 joint figure (original4.98..6.05ns clock/internal nodes,D/S,VDS threshold,Q) and same-time summary. Supports bounded-recovery internal negative-node interpretation; intrinsic current/region missing prevents unique Cgd/channel attribution. Ready to deliver paired storage report plus reference Lswap evidence. All remote phases complete, original failures retained, no pending simulation. Next electrical modifications require a fresh single-variable fixture, not automatic adoption. No timer resume,OA edit,commit or push.

2026-10-27: User explicitly resumed scheduled SAR8 work and chose netlist-only design. Existing sar8 heartbeat updated successfully to ACTIVE at ten-minute cadence with fresh completed-batch checkpoint; outage/paused instructions superseded. Virtuoso/OA not required for managed Spectre work, OA remains untouched and not synchronized. Next priorities: library slew/load evidence, DFF recovery, symmetric NAND/RC stress, then controller interfaces. Existing resource and protected-data constraints preserved. Only plan/log coordination updated; no simulations launched, baseline adoption, commit/push or unrelated automation changes in this scheduling turn.

2026-10-27 resumed heartbeat: all four existing owners inspected; no new uncollected result or running remote batch reported. Parent assigned two nonduplicate local next steps after updating exact ownership: control standard_cell_usage_v1 for native DFF slew/load evidence and targeted fixture; reference standard_cell_bbm_hlswap_v1 for H-only pin-order delta on frozen L-swap. Managed submission remains parent-owned; comparator/sampling remain at checkpoints while interface work proceeds. No new remote run, baseline, OA change or push.

2026-10-27 batch2: Parent reviewed and passed H-swap structural/native-duration focused test; managed d0020c7f2887144d28c373ad052a6f24e81d0d4af120993e2c1066b7c8f186f7 registered as sar8audit-ref-bbm-stdcell-hlswap-ff-v1. Native complete22.980s,peak344551424B,398419847B output, zero-error footer/PASS; CMI2751-2756 retained, small-design multithreading disabled. Analysis running. Control usage baseline and2k packages reviewed;2 focused checks passed, all native library and original PWL/first-hop loads retained. Baseline managed a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1 queued behind reference analysis; contrast registered only pending baseline evidence. Library characterization bounds still unknown; no ADC qualification.

2026-10-27 batch2 recovery checkpoint: H/Lswap analysis complete117.956s,peak30273536B;11files26389195B collected no skips,11298native points. H full VDS0.992331628V (48ns phase max0.684430965V), L0.992307091V, full214/738 strict failures; reference owner now preparing paired report. Usage baseline native PASS19.513s/peak332996608B/108066435B, but analysis failed18.519s/peak10883072B at configured20MiB uncompressed native export cap (fixed error message says30MiB). Exact console tail inspected via bounded read-only SSH;7files21000756B failure/partial evidence collected. Owner preparing lossless streaming-compressed source-bound analysis-only recovery without changing original input/circuit or32MiB collection budget. Contrast registered997693935954ebbce4f0d4191e0a55ac1e1f391d7502bd5f5005c92c39876b3a but NOT submitted. No remote heavy task active after baseline analysis failure; no duplicate run or baseline adoption.

2026-10-27 reviewed HL report and both figures: H negative stack min-0.116073 to-0.015037V;48ns MM4VDS1.105306 to0.684431V, but43ns0.992332V residue remains. Full213->214 means6 added/5 removed H gate-related terminal pairs; >1mV count197 unchanged, reference settling/reset preserved. RC1HDmax1.061723V and gate/clear stress remain. Assigned reference local RC1 signed-current/charge diagnosis and one candidate preparation using collected native data, no new remote task. Read control characterization evidence:170a document/SPICE labels match but full PDK pairing and DFF slew/load axes unknown; recommended supply range is not an absolute transient lifetime limit. Continue strict project screen without equating it to foundry lifetime signoff.

2026-10-27 usage recovery: reviewed streaming gzip/source binding and2focused equivalence/strict compressed guard checks passed. Baseline recovery recipe5b3272e0847ceb467cba551cd29cf6e84cf8768058a893fe159b9c29266b0533 registered managed8ca29469d5f223a490bf62c1e7f13f649c54830e37cf3fe9caefc95fb2505663, completed21.035s/peak17739776B;8files19152735B collected. All22772native points,348pairs/73currents retained;decoded21132416B and SHA verified,compressed18854904B. MM64VDS1.105789020V@5.031317284ns reproduces full-storage1.105788040V within0.98uV/0.060ps;functional hold/expectedQ patterns pass. Six-node KCLmax2.971pA. Original failed20MiB export remains. Approved and submitted frozen2kohm CK diagnostic sar8audit-ctrl-usage-rck2k-ff-v1 once; native running, old analyzer will not be started. Owner prepares baseline current/charge report, contrast will use separately bound gzip analysis.

2026-10-27 usage pair completed: rck2k native19.978s/peak333979648B/112100419B PASS; original analysis not_started explicitly preserved. Independent gzip recipe319011cd8485f2921910663a9f7befada6c57bb63567640292453718780e1211 registered902767f0e40794753b6c98c0dd01898e42850c377809e61187f12e784510fe71;analysis21.538s/peak17784832B;8files19810268B collected with no skips.23083points,hold/Q pass,256/348terminal failures unchanged. MM64VDS1.105795516V@5.032212225ns versus baseline1.105789020V@5.031317284ns;2k does not materially reduce worst stress. ActualCP10/90%slew2.773–2.801ps to3.487–3.647ps only, so cannot rule out stronger slew sensitivity or internal rebuffering. Owner preparing native internal-clock/current/phase-charge paired interpretation, no additional sweep. All managed remote phases complete; referenceRC1 local diagnosis and control paired report active. No OA, baseline adoption, commit/push or old-data edit.

2026-10-27 RC1 single-variable run: parent reviewed native charge figure/port mapping, exact HD-only gate-resistor delta and analyzer; focused package check passed. Recipe3805b0f88e1face70a166ecc407746bb6ce41d86c6359eacc5634de5dfc3f32b registered sar8audit-ref-rc1-hd-cleargater-ff-v1 managed f99c95e1c92a40c8abbe26f5456f77c03793e496538994c5ef75a17660a21e2b. Native22.348s/peak344887296B/404596111B output/PASS;analysis118.203s/peak53137408B.11files27685183B collected, no skips,11420nativepoints; CMI2751-2756 preserved. HD RC1 positive peak1.061723->1.026241V and minimum-19.953->-16.508mV, but receiver worst|Vgd|1.035538V remains. Clear|Vds|1.009953->1.006508V while >.99V duration4.497->11.274ps; RC1 reset8.748->31.734ps. Four reference1mV settling and both resets remain true, actual N gaps high23.524->23.498ps/low171.487->171.555ps. Strict214->215/738 includes new clear|Vgd|0.990000431V (0.431uV excess,25fs estimated), not physical repair success. Reference owner preparing paired report/figures and residual receiver-phase interpretation. All remote phases complete; no duplicate run or adoption.

2026-10-27 DFF current report review: parent read results/README.md and viewed paired_timing.png/paired_currents.png. CP2.793->3.581ps but clkbb4.386->4.453ps, mq4.172ps unchanged; MM64max remains1.1058V, about0.99033ns above project screen. Native total terminal currents and signed phase integrals close, intrinsic mechanism remains unseparated. Assigned control bounded read-only170a library/PDK pairing and same-version Liberty conditions under existing characterization ownership; no additional slew sweep. Shared plan/log only plus new managed recipe/run touched by parent; unrelated dirty work protected, no OA/PDK/library edit, commit/push or deletion.

2026-10-27 04:36UTC coordination: reference RC1 paired report/current attribution remains active in its comparison/ subtree; no duplicate simulation or collection. Control bounded metadata read confirms native SPI170a header CLN28HT and no embedded include dependency; current DFCNQD1 model names resolve, but exact recommended PDK pairing remains unverified. Known unfolded library path has no Front_End Liberty; bounded20,480B compressed-prefix read of180a CCS archive found an initial267,632,640B binary .db member only, without reading/extracting that member or scanning the13.66GB archive. Same-version slew/load limits therefore remain unknown. Owners continue already assigned tasks; comparator/sampling remain checkpoints awaiting actual interface evidence. No new remote heavy job, protected-data change, adoption or commit/push.

2026-10-27 04:46UTC paired RC1 report reviewed and both figures viewed. HD X005 negative Vgd worsens-1.009186->-1.035538V despite smaller individual RC1/HD excursions: at new worst48.004116ns RC1=-16.367mV,HD=1.019171V; slower reset overlaps NAND gate return. Complete HD incidence is two receiver D ports plus two NAND G ports; at worst their summed currents are+/-59.977uA, signed leading charge0.174058fC versus0.123016fC baseline. Total-port evidence does not resolve intrinsic current components. Distinguish RC1 reset8.748->31.734ps from whole-HD-leg reset11.507->31.734ps. Assigned one verified stronger native X005 master candidate in reference/standard_cell_rc1_drive_v1/, no new remote submission yet. Control dependency audit remains incomplete: assigned source-bound managed archive metadata index preparation in characterization/index_v1/ with streaming256MiB/1thread/1800s ceilings, no library body extraction or fabricated simulation. Protected versions/ADC/OA unchanged; no commit/push.

2026-10-27 05:07UTC D1P25 completed: parent reviewed final fractional native-master mapping/measurement after D2 preparation was corrected before any submission. Owner focused test0.899s passed; recipe5f416251a1f26ec288b2c980dbdd05c965fc56e6a6ca3659a1fdb788d29f5b3a registered managed24306072b56f9a60a0d2e73fa0619d797094ce81a7829cbb6c61b3d4c0e1a81d. Native23.452s/peak340766720B PASS with CMI2751-2756 retained; analysis125.074s/peak52326400B;11files27718889B collected no skips,11422points. ResultSHAa273e6730a84cd84aebe79a099b99605bdd8549c154d497bce0e44fa2faa1dbd. HD receiver worst|Vgd|1.035538->1.027665V but overlimit duration68.257->68.752ps, clear|Vds|1.006508->1.006237V, RC1reset31.734->31.879ps. Actual225/750 pairs equals215/738 equivalent groups, unchanged equivalent failure count. Both resets/four1mV settling diagnostics pass; electrical repair not complete. Reference assigned bounded comparison/ figure/report only, no additional candidate. Parent also reviewed final source-bound library index and3focused tests; recipe82298c98ce101b966f2c0068fc6ed5d61ee3667a4f210d0c14f078f8c0922231 registered61b56ce7a68b2915029f9071b2157734ff1ba7d30575c8987cf5b15963d6f9b2 and started only after reference analysis finished. Sole heavy job sar8audit-ctrl-dependency-ccs-index-v1 currently running41s/peak10047488B, no duplicate scan. OA/source/library/PDK unchanged; no adoption, commit/push or deletion.

2026-10-27 05:18UTC library dependency index complete: managed61b56ce7a68b2915029f9071b2157734ff1ba7d30575c8987cf5b15963d6f9b2,187.122s/peak10133504B;7files79939B collected no skips.195members,13,657,415,950compressed/45,137,694,720decoded bytes,complete gzip/CRC and fullSHA03982f44e41e3af56b2ef38eda1fdd9de641c43f765a9a443fc56801dd4ded22. Exact FF0.99V/-40C text .lib1556315212B exists alongside .db249438208B; no release-note member, no Liberty values yet. Assigned control characterization/liberty_v1 bounded source-bound semantic extraction preparation; no new remote run or repeated index. Parent reviewed reference D1P25 report and D1_D1P25_phase_comparison.png: simultaneous worstHD1.019171->1.011603V while NAND gate backflow59.977->59.830uA persists; confirms limited driver benefit without clearing RC1/HD overlap. Assigned reference interface_options/ to compare at most2 physical interface options and prepare one justified single-variable candidate only; frozen sources protected. All remote heavy phases now complete, no pending sim. Existing comparator/sampling remain interface-dependent checkpoints. No adoption,OA/PDK/library changes,commit/push/deletion or automation modification.

2026-10-27 05:28UTC preparation checkpoint: reference analog IO/guard interface and control exact-member Liberty reader remain active locally; neither package frozen or remotely admitted, no active server task. Parent inspected interface draft and clarified essential correctness: unloaded quarter/threequarter-VDD estimates do not establish actual logic margins; retain original rail-reset outcome alongside guard-level settling, measure loaded plateaus/downstream output/false transitions/static power, and preserve unknown VIH/VIL. Composite interface change cannot attribute separate component benefits. Existing scopes retained, no duplicated work or new simulation/adoption/commit/push.


2026-10-27 05:44UTC guard/Liberty checkpoint: reviewed final IO-clear/receiver/passive-guard composite interface and analyzer, owner2focused checks passed. Proposal563a395e239d663a2299ba5a31189cf3039ebf2a548bdfed21d28f2a80926685 registered managedf4e063a683dcc65de7630b8f139f1a1c9d61a1c32e0fc10543924de7f1ce52d0, sar8audit-ref-hd-io-guard-ff-v1. Native22.276s/peak342290432B PASS, CMI2751-2756 retained;analysis124.446s/peak29118464B;11files28479798B collected no skips,11373nativepoints. HD0.260053..0.730529V,static0.261235/0.718386V;IO receiver/clear within1.98V screen, H NAND MM4maxVDS0.988770V but other NAND pairs1.001841V and unchanged HD X0021.020313V remain;overall194/738strict. Four independent command-phase1mV reference windows pass/noHLoverlap;original zero-rail HD reset fails with0.261235V residual. Guard static36.32..36.84uW plus high-state NAND2.985uW, not free protection. Assigned bounded paired report/figure to existing reference comparison ownership; gate-defined high ON window extends into next CODE and cannot replace independent command-phase settling. No new candidate authorized. Parent reviewed control source-bound indexed Liberty semantic package once, cell-level threshold inheritance gap fixed with focused synthetic check before registration;frozenproposal8900e32d69ffcbbaa7d353ece7d3fe743c581d20c22d7b40bcf40293552ee7f8 registeredmanageda4a97646beb0fbd2033ff805ac83ac9c7ee787337b8d2443c3e38fa817dc17f9 and started analysis-only sar8audit-ctrl-ff-liberty-semantics-v1 after guardcomplete. This is sole heavy job;1thread256MiB900s/4MiBoutput, no new simulation or library body extraction. Originalsource/index/PDK/library/OA protected, unrelateddirtyObsidian/10bit/management untouched. No baseline adoption,commit/push,deletion or automationchange.

2026-10-27 05:45UTC update: Liberty semantic v1 failed46.249s/peak11096064B with Indexed tar header/body identity mismatch, member_bytes_read0 at targetbody13230658048.6files11101B failure/checkpoint collected; no semantic values or full second-pass integrity obtained. Original completed archive index remains valid; direct raw-header vs effective GNU/PAX-name comparison suspected, not yet proven. Assigned control liberty_v2/ narrow source-reader/header-evidence correction and focused extension test, preserve allv1 inputs/results. No server heavy job active; reference paired guard interpretation proceeds independently. No circuit/PDK/library change or duplicate submission.

2026-10-27 05:58UTC: reviewed reference interface_options/comparison/report.md, comparison data interpretation and both rendered figures.720identical actual terminal pairs show202->194strict,8relatedH NANDpairs removed/0added. Remaining upstreamB-30.313mV@48.005686ns tied toRC0-driven inverter switching (R1returns atpeak), downstreamNAND_N-11.841mV@47.998033ns tied toCODE whileHDinrails; no intrinsic-current decomposition claimed. Guard not selected for full implementation given36..37uW/leg+highNAND2.985uW, high-phase~130psdelay and remainingcorestress. Keep diagnostic evidence; no divider/drive sweep. Existing controlv2 header reader/diff reviewed once, awaiting focused-test freeze; originalv1failedresults protected, no remoteactivejob. No commit/push/OA/PDK/library change.

2026-10-27 05:59UTC semantic reader recovery: final v2proposal7a7309c887069dcc0b18257667616aeaea35dfe95fa85c10af2176c33180475a and12inputs1282646B reviewed;onefocusedGNU/PAX/wrong-field/checksum check passed. Registeredmanagedcc657c424bacb365f6c71c3dbc920297ff29e59c2d9c6053b260beeaae3f5be9, sar8audit-ctrl-ff-liberty-semantics-v2 analysis-only admitted with no conflicts. Exact predecessor gap1024B parsed, raw/effective fields saved beforebody; all name/size/type/offset/link checks retained. Source/failedv1/index and semanticlogic frozen, no new simulation. Comparison and sampling checkpoints inspected, still interface-dependent; no duplicate dispatch.

2026-10-27 06:04UTC v2 source read completed231.748s/peak11874304B;7files151973B collected no skips; fullarchiveSHA/CRC verified, memberSHA b3e3dd53d17059ba9eb9b9ba30dab9b88437454a78151170366f211d2c7c4019, DFCNQD1found15arcs/no unresolvedtemplates. Header mismatch confirmed missing GNU.longname in v1; v2 fields/checksallmatch. Textdeclaresrevision170 despite180aarchive; notfullPDKpairproof. Actualaxes1.5..262.9ps, Qload.41..102.31fF. Parent found partialsemanticerror: numeric/default/threshold attrs concatenated into default_max_transition string; native-slew fieldsnull. Tool exit0 does not complete usage qualification. Assigned strict local small-evidence attribute recovery and native-edge recomputation in control liberty_v2/attribute_recovery/, preservingoriginal result; no new remote scan/simulation. No serverheavyjobactive.

2026-10-27 06:08UTC local recovery continues in existingcontrolowner, no duplicate dispatch or remotejob. Parent researched slew definition from primary characterization vendor Paripath (https://www.paripath.com/blog/characterization-blog/demystifying-slew-derate): threshold_interval=d*library_slew. Requested separate sourced normalized interval/d column after strict attribute recovery, retaining raw native30/70 measurement and originaltable axes; not equating nonlinear measured10/90 to normalizedvalue and not using range agreement as reliabilitypass. Frozen v1/v2 unchanged.


### 2026-10-27 — SAR_ADC_T28_manual read-only initial review

User requested independent review of hand-built 8bit/10MS/s ADC; preserve topology, ideal external sources, future netlist TB allowed. Read six cells via healthy T28_IO bridge; raw snapshots output/manual_adc_review, curated connections/report verification/manual_adc_review. Found shift-register CDN=CLKS conflicts with high sampling/low conversion; native library clear is !CDN. First-up/later-down 128C-per-side algorithm is viable with first-step cross-mapping and separate output MSB polarity. Current 5ns two-edge feedback delay implies earliest eighth evaluate ~75ns before device delays. L1 has no nets in readback, unsaved edits preserved; screenshot tool produced empty file, no visual confirmation. Existing ideal demo is 5V/100MHz and not a device TB. All analog sizing/settling/stress still unverified. Arithmetic code-centre check is not circuit simulation. No OA changes, new simulations, commit or push; old SAR8 evidence not attributed to manual design.

2026-10-27 06:20UTC recovery reviewed: local450-character strict token recovery/identity evidence and normalization code confirm CP/D/CDN coordinates in1.5..262.9ps across32mapped axes. Raw30/70interval is divided by explicit0.50derate; measured10/90unchanged. Thus input-coordinate out-of-range is not established, while MM64~1.105789V,unknown effectiveQload/conditional timing/model pairing remain. Assigned control rck20k_v1 one resistor-only sensitivity package with losslessgzip analysis, no automaticsweep or remoteexecution. Assigned reference standard_cell_ss_nonoverlap_v1 bounded source-bound actual-gate/branch-current SS analysis from completeddata; no newcandidate/sim unless data gap identified and separatelyadmitted. ExistingmanualADC/VNCreview and userdirtyfiles protected. No active newserverjob, adoption,OA/PDK/library edit,commit/push,deletion or automationchange.

2026-10-27 06:32UTC RCK20k: reviewed exact one-resistor delta/wrapper/observer and owner2focused tests; proposal e4efbd1d98afbe366ee0f87517a63b0ca84718e1224dae069fb2357cd27bee00 registered c5e24bb1779f7a04a405799aa719a4f4b67047f7d4ac5cf7bd6cb9d563e2fea9. Native21.849527s/333090816B/PASS retainsCMI2751–2756, actualCXgear2/reltol1e-7/10nV/100fA/maxstep10ps verified. Analysis queued behind unrelatedSpectre, completed24.733671s/23408640B;9files20965819B no skips,24253nativepoints. CP10/90 2.79265->20.71845ps,30/70=7.42115ps; clkbb4.38632->5.38521ps,mq4.17234->4.16820ps. MM64VDS1.105789020->1.105857818V,256/348strict unchanged,hold/Qtrue. Stops resistor-repair direction per predeclared decision; control comparison/ owns three-case native-current/recovery figure/report only. Reference SS figure/code inspected, signed source-port currents distinguish charge exchange from opposed-drain proxy; final report pending. No remaining new remotejob, no adoption/OA/library/PDKchange/commit/push/deletion.

2026-10-27 SS native-switch report reviewed: original standard SS cold10956points, select-highN sourceexchange10.764uA and fullD/G/S/B/KCL support slowGNN-off risk; select-lowP1.203uA opposedD peak has only9.18nA to lowreferenceS, so Dcurrent alone is not channel-overlap. Four reference1mVsettling pass, exact channel overlap/deadtime unknown. Viewed actual-switch figure and reviewed signed-port code; no new simulation. Assigned reference standard_cell_gnn_path_v1 per-stage existing-data diagnosis plus at most one parity-preserving3IO->1IO interface preparation, contingent on delay/load evidence; allotherpaths/Rgate/sourceconditions preserved, owner no remoteexecution. Parent also viewed control20k timing_comparison/recovery_currents: externalCPslows, mq/net176 recovery remain unchanged in magnitude; three-case finalreport inprogress, no repeated simulation. No newremotejob/adoption/OA/PDK/librarychange/commit/push/deletion.

### 2026-10-27 — Manual ADC independent netlist implementation, module checkpoint

Implemented reset inversion, first-bit-only P/N cross and raw-decision output mapping in verification/manual_adc, preserving source OA. Read-only native export snapshots retained; two testbench failures and native-delay minstep failure preserved under unique run IDs. Bootstrap original core devices show native CMI; connection-preserving IO1.8V candidate and main1/2/4um sweep complete,4um selected for joined diagnostic. CDAC seven ideal-driven steps match within2.51uV; comparator actual capacitive input gives<=0.189ns VALID and<=3.70uV evaluate differential kickback; receiving standard-cell CMI unresolved. RC timing replacement retains gate graph; four sequential and eight selected digital patterns decode correctly. All managed runs one thread with declared resource caps. Joined four-frame candidate submitted, not yet qualified. Scripts/report/results/three reviewed figures under owned manual_adc paths. No OA/PDK/library/old experiments edits, no commit/push.

2026-10-27 06:48UTC reviewed final control rck20k_v1/comparison/README.md and results: unchanged failure set, net176 about-48mV near5.95ns, nextclock recovery distinguished from natural settling; sourceenergy scope correctly limited. Both figures already viewed. Assigned control intrinsic_probe_v1 exact-model supportedconduction-field lookup/measurement-only preparation (boundedread/help outsideCIW withtimeouts, no guessedids or libraryedit), nativebaseline unchanged; parent retains all newmanaged execution. Reference baseline_GNN_stage_timing.png reviewed: SS slowoff419ps includesIOchain360ps/Rgate52ps/X0258ps, firsttwoIO227ps.3->1candidate remains a diagnostic, not17ps-margin passprediction; preparation already active, no duplicate task. SharedmanualADC results are independent and not attributed toSAR8audit. No newserverjob/adoption/OA/PDK/librarychange/commit/push/deletion.

Manual ADC joined follow-up: native420ns completed0errors/29displayedwarnings, repeatedCMI suppressed;165s/326MiB. Initial analyzer exceeded derived28MiB guard, retained; managed analysis-only manual8-joined-dc-reduce-v2 reused completed source with20ps display export and all-native metrics,9MiBpeak/17s,3.76MB collected. Fourcodes142/28/227/130 match,8compares/frame,8.596..8.681ns close-to-last-bit, all-source netenergy mean68.966uW. Updated README, exact JSON, four-frame and conversionzoom plots. Comparator timing clarified as50%-clock to50%-VALID112.6..163.4ps. ElectricalCMI and fullcode/FFT qualification unresolved; no OA or baseline adoption, no commit/push.

2026-10-27 07:04UTC GNN singleIO SS completed and collected once: proposal7f75ed0953931628d7fdb2c0d72d34c5f510c8c551114e8abae0c583eef4fa88, managede42eefcc60054ad08228cd02fc809d40fff746d2e2f52fc22540c74a5e4d4b0c. Native21.309s/340758528B/PASS,SFE1131/VACOMP2435 preserved;analysis105.351s/27774976B;11files24264511B/no skips,10464nativepoints. L->GNN lowoff113.643ps versus419.367ps, N highphase source-exchange28.986nA versus10.764uA, integral2.820aC;four1mVsettlingpass,0/714strict. PRE-29.492..845.061mV, X025max845.061mV,finalIOmax1.100865V within1.98V. Sourceexchange remains total-port diagnostic, no exact channel deadtime/fullADC claim. Assigned reference comparison/ paired report/plots and samefrozencircuit candidate/ffcold/ preparation. Control intrinsic lookup reviewed: TMI fielddefinition/negativeVDSsign unavailable, ordinarybsimbulk ids not adopted. Allowed one unchanged-baseline op_mapping_v1/ capability-check preparation under existingcontrolowner, no newdesign/remoteexecution. Originalsources/failedqueries/protectedmanualADC/Obsidian/10bit untouched; no active heavyjob, adoption,OA/library/PDKedit,commit/push/deletion or timerchange.

2026-10-27 07:10UTC preparation continuation: reference comparison and identical-DUT FF package active, original SS receipt/result unchanged; no duplicate task or recovery. Control OP mapping lacked info/save syntax and initially saved exact missing items; parent clarified existing bounded read-only authority includes exactly installed Spectre -h info/-h save,8s/512KiB each without CIW/files/simulation. Owner continues directly to one mapping-only candidate if supported; no guessed intrinsic-current acceptance, additional approval layer or library modification. Comparator/sampling checkpoints unchanged. No heavy remote submission this checkpoint; protected dirty work preserved, no adoption/commit/push/deletion/timerchange.

### 2026-10-27 — Manual ADC standard-cell internal stress diagnosis and delay review

User requested analysis/waveforms/proposal only, OAignored. Unchanged joinedcandidate save-only run manual8-stress-baseline-v1 completed120ns0errors,333MiBpeak; internal voltage/current analysis820MOS34instances identified59MOS>0.99V. Repeatedreset qfpositive spike~1.058V, floatingNMOSnet176negative-203.874mV with simultaneousMM64VDS1.034207V/213.910ps, transparent-master data-edgePMOSstackMM79VDS1.012065V/211.160ps. Full-native windowplot export manual8-stress-zoom-v1 collected0.76MB; three figures reviewed. First-reset initialstate differs from old optimizedrun so no bitwise-source-replayclaim; laterreset confirms recurring mechanism. Ideal-delay matched120ns200ps/5psmaxstep both0errors/code0correct yet16780remain; old25.62usfail preserved. Corrected RC equivalence mistake, retain RCresultsasdiagnostic-only and recommend restoredideal-delay mainline. Report verification/manual_adc/stress_diagnosis/README.md, exactjson/script evidence. ProposedCDNslew, stagedclear and alternativeFFtests; no repairadoption/OA/library/PDKchanges/commit/push.

2026-10-27 07:36UTC GNN same-DUT FF reviewed condition-only delta and existing focused check; proposalf67e60b0ceab7a9205249aa46820d4abde98beba7bf6bebb95711886b2ba0bd7 registeredmanagede32ae97bcfe3022f58de068333ddeae1886752ba043e9f6df14cab3533f03e78. Native22.360s/341803008B,CMI2751..2756 retained;analysis110.658s/27746304B;11files24662257B collected once/no skips,10889points. Four1mVreferencewindows pass but213/714strict; X0251.007405V exceeds0.99,finalIO1.315104V within1.98; not electrical pass. SS paired report reviewed and bothfigures viewed,708identicalmodel/node/limitpairs distinguished from6rewired/24deleted; energy scope local. Assigned originalFF/IO1FF samepair attribution and waveform/recommendation under reference comparison_ff/, no newcandidate yet.
Control static-info package95fddc61431ffd0980449765901a4ad6c52e64c6cfdefeeea6f833d9d26047fb reviewed once,17inputs179875B;registeredmanagedd6ea28629d09a0b808c2392767688153b3b8c72ac68e2ab3847a3826ab3006a8. Queued behindFFanalysis then completednative20.149s/333070336B,analysis21.976s/17592320B;9files19156467B collected. MM65/MM65.nch exactaliases and tmibsimbulk found;targetOPtextpresent but parserzero fields not absence. Assigned small exactcompletedfile format diagnosis then parser-only/source-bound recovery preparation within op_mapping_v1/recovery/, no native repeat or guessed current semantics. All heavyjobs now complete, failed/unknown outcomes retained; no baseline/OA/library/PDK change,commit/push/deletion/timerchange. IndependentmanualADC and other dirtywork protected.

2026-10-27 08:00UTC MM65 parser-only recovery reviewed/admitted: proposal81beb7387451c2aa3d63c31390059e8213b129711d9c30f33190e648570114f7, managed6dad2f98b9fa87ab178f879416527217301cb1907feb417c96e8b142f1208920,3inputs13986B. Completed0.574s/9867264B;4files23076B/no skips. Actual Instance scope yields98fields and matching four ports. Corrects prior alias claim: MM65.nch.35 is Model identifier, not confirmed .nch instance. Staticids850.088aA/id323.622fA are un-timed OP values, not5.5ns recovery. Original22772points,256/348stressfails,MM64VDS1.105789V unchanged. Assigned one unchanged-baseline actualMM65 named-field transientmeasurement preparation under intrinsic_probe_v1/transient_fields_v1/, retaining totalport/node consistency and uncertaincurrent semantics; no physical/library change or automatic retry. Reference FFsamepair attribution still active, no duplicated assignment. No pendingheavyjob, adoption,OA/PDK/libraryedit,commit/push/deletion or timerchange.

2026-10-27 08:27UTC reviewed reference FF paired accounting, actual-port attribution and both readable figures:708same pairs retain213failures, X0251.007408->1.007405V, upstream event precedes largefinalIO excursion. Reference context drift to historical session creation corrected; owner confirms no chats created/dispatched. Authorized one Boolean-equivalent NAND-output tap interface preparation under standard_cell_nand_tap_v1/ after finishing report, preserving L0/GPP load and all external timing; no remote run or library edit. Control MM65 transient-fields package remains active. Existing results frozen, no repeated recovery/submission, baseline/OA/PDK/library change,commit/push/deletion or automationchange.


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


## 2026-10-27 — 手搭SAR8行为模型就绪

按用户要求新增 verification/manual_adc/behavioral_v1/：采样开关、守恒电荷的单侧CDAC、可取消待决结果的比较器、首位向上/后续向下SAR四个VA模型；附wrappers、日常实验TB、自检TB、参数和替换接口说明。外部100ns/约40ns采样窗口及关闭沿保留，下一次采样锁存上一帧输出；延时采用显式事件，不使用RC。默认不含已校准的噪声、失配、端压或功耗行为。

独立算法检查通过256码中心。managed manual8-beh-smoke-v1首次编译与13项自检通过，保留其edge未来保留字告警；改名trf后manual8-beh-smoke-v2复核820ns，原生0错误、仅1条旧环境变量告警VACOMP-2435。8组码0/255/85/170/127/128/1/254全部正确，每帧8次比较；共模/残差、比较器取消与恢复、双高拒绝、缺响应超时、采样中断后无旧事件全部通过。最终代码SHA及结果见behavioral_v1/validation.json。此次仅为代码交付和短自检，不开展晶体管尺寸/PVT/混合验证；OA/PDK/历史候选、用户Obsidian及其他任务文件未改，不commit/push。


## 2026-10-27 — SAR隔离实验定义

用户要求本聊天聚焦SAR，先给测试指标、TB边界、理想模块输入与DFF监控。新增plan/2026-10-27-manual-sar-isolation/plan.md及verification/manual_adc/sar_isolation_v1/test_contract.md。核对原生连接，明确CLK7到CLK0是依次置高并保持的热码，非独热；I5固定D与I12后级复位作为对照，全部32DFF按移位/正负判决/最终输出监控。定义已知判决序列响应器TB-A与理想采样/CDAC/比较器闭环TB-B；17理想delay保留，真实参考MOS静态栅负载另挂，声明不包含Miller。首轮TT0.9V27°C，八模式重复两轮；40ns转换、1ns复位/输出建立与100µW数字电源预算为拟定子模块目标，非已有结果；库setup/hold等暂无约束时保留unknown。后续五点PVT仅列范围，未派发或仿真。scoped diff --check通过（仅既有日志CRLF提示）；OA/原电路/行为模型/PDK/其他任务未改，不commit/push。

## 2026-10-27 — 比较器独立尺寸工作区与首轮筛查

按用户授权新增 comparator_design/，作为后续比较器唯一设计入口；冻结手搭15MOS原拓扑和模型引用，未改OA/PDK/标准库或其他设计。接收端8个DFQD1 D端加OR2D4输入的TT动态等效负载为6.012–6.049fF/侧，筛选取6.1fF；真实接收FF的CMI保留，未宣称修复。

完成managed cmpdesign-load-tt-v1、cmpdesign-sizing-tt-v1（B0/I4/T4/R2/O4/P4，直接/1.28pF保持输入）、cmpdesign-b0-i4-ss-cold-v1、ss-hot-v1、ff-cold-v1、ff-hot-v1。TT测量通过cmpdesign-sizing-tt-measure-v2绑定原始波形修正评价结束窗口及稳定判决时间上界，不重复仿真；cmpdesign-worst-terminal-zoom-v1绑定FF热角保留673个原生点，峰值匹配完整扫描。

896次确定性极性/输出复位检查通过。TT及SS两点通过所列筛查；FF两点端压未通过。B0/I4的SS冷角最慢判决0.6418/0.3856ns；FF热角最坏端压1.024053/1.021465V，位于复位时LP/LN上冲并反映到输出N管栅体/栅源及再生支路。噪声、失配、细门限历史、最短复位及真实CDAC/标准单元接口尚未验收；未冻结新尺寸或整机基线。

报告 comparator_design/RESULTS.md、数值 results/summary.json、四图 figures/已人工图像检查，完整性及只读源SHA核对见validation.json。单重任务、1线程；仿真峰值RSS314.15MiB、分析10.09MiB；无在途本目录任务。保留原始告警/测量旧版，未commit/push。下一轮继续在该目录做复位过冲单变量定位。

## 2026-10-27 — 比较器过冲节点与时间定位

用户要求核实过冲节点、时刻及原始数据。复用既有673点FF热角原生窗口；新增managed analysis-only cmpdesign-start-overshoot-zoom-v1，绑定已完成FF冷角源，未重跑仿真或改电路。B0/FF热角LN在155.531683ns达到1.024053V，位于155.500–155.550ns复位下降沿；单次高于0.99V约30.08ps。I4/FF冷角net2在354.033170ns达到1.003607V，位于354.000–354.050ns启动上升沿；单次越限约40.27ps。LP/net1有对称事件，不能把全程累计越限时间当作一次尖峰宽度。

新增comparator_design/OVERSHOOT.md、results/overshoot_location/原生CSV及测量JSON、figures/overshoot_location.png和定位脚本。图像检查通过，峰值与全程原生扫描一致，交点使用相邻原生点插值。确认复位节点同步上升与高节点过冲；寄生耦合路径按实际网表解释，尚未取得支路电流贡献证据，保持推断边界。不改OA/PDK/标准库，不commit/push。

## 2026-10-27 — SAR隔离测试启动与资源预算纠正

按用户“开始测试”实现sar_isolation_v1的TB-A/B、响应器、32DFF端口和10代表DFF/248MOS六端差流式测量、绘图与时序脚本。OA/原生标准库/原候选只读，全部17个原模拟delay先按原文运行。v1因VA的.5语法失败；v2修复后67.1684ns SPECTRE-16928失败，保留16780/16191与CMI。v3改为明确标注的VA逻辑传输延时，实际2ns/100ps与50ps边沿待事件核对，未用RC；在2GiB输出预算终止。v4 tran reltol参数未改变实际设置，原生帮助确认conservative乘0.1；核对PID/boot/start/cmdline后SIGINT停止冗余对照，回执已保存。v5正确设置实际reltol1e-6，但在约1.374us仍触及旧2GiB预算，非16帧完成。

用户明确要求放宽资源预算；纠正为后续案例8GiB输出、仿真3600s/分析1800s，仿真1GiB/分析256MiB、单并发和32MiB回收不变，未修改共享管理脚本或全局策略。当前managed manual8-sar-a-tt-v6按相同电路/实际容差/监控范围运行；串行sar_isolation_flow.py待A完整回收并检查功能后才注册/运行manual8-sar-b-tt-v5。原失败日志/波形保留，不宣称功能、电气或PVT通过。脚本语法检查通过；最终图像审核和结果交付待完成。无commit/push/OA修改，其他任务/用户笔记未改。

2026-10-27 SAR隔离范围纠正：用户指出仅端压定位无需重复两轮。已停止本地sar_isolation_flow.py控制器（仅本任务匹配进程17048/42724），TB-B未注册/启动。查询v6仍运行，约869.58ns，首轮已经过去；保留在途原生文件收尾，不重跑或增加案例。后续仅分析启动/正常复位和代表数据翻转，新的端压实验约120–220ns；旧16帧功能矩阵不再作为当前目标。未改电路、OA或资源策略。

## 2026-10-27 10:35 UTC — Comparator currents and user-authorized concurrency=2

Completed cmpdesign-current-reset-v1 and cmpdesign-current-start-v1 through managed simulation/analysis/collection; native success, immutable DUT/models confirmed, unchanged-event peaks within 0.413nV, complete-node KCL residual below 3e-21A. Both runs finished sequentially before policy deployment; no duplicate submission. LN reset injection is dominated by M6/M0 gate terminal charge, while M4 extracts charge. net2 startup injection comes from M5 dynamic drain charge offset by its conductive recovery; low-input M9 has negligible conductive charge. Saved current_attribution.json, validation, reviewed plot and CURRENT_ATTRIBUTION.md under comparator_design. Proposed separate M2/M4 and M3/M5 multi=2/4 experiments; no size modification/adoption or OA write.

User explicitly requested repository rule change and one additional parallel job. Updated AGENTS.md, project/policy/docs and managed admission to two slots shared by simulation/analysis; legacy workload.lock retained as slot0. Preserved existing uncommitted analysis-only/transport changes. Twenty management tests pass; deployed version2 policy and exact hashed agent. Real Linux flock test verified concurrent legacy slot0+slot1, third denied, release/reuse; receipt in comparator_design/results/concurrency. Single-job budgets and unknown-process/resource checks remain enforced. No commit/push/deletion. No comparator jobs remain in flight.


## 2026-10-27 — SAR已有结果关键端压窗口回收

按用户要求仅回收manual8-sar-a-tt-v6已有结果，源运行已正常完成1.62us、原生零错误结束，CMI保留。analysis-only manual8-sar-a-v6-stress-windows-v1处理前220ns的42951个原生时刻，覆盖10代表DFF/248MOS；37.034s、峰值RSS约10.6MiB，回收7739896字节，未新跑仿真，TB-B未运行。

定位三类事件：复位qf上冲使I5.MM76 VGB=1.061118V；后级移位复位叠加D下降使I12.MM64内部源极下冲，VDS=1.084476V、连续230.65ps；普通判决与输出DFF内部PMOS源节点上冲，代表MM79/MM1约1.006–1.012V。输出I46_3在CP仍低且Q保持时，D变化已引发内部超限。电流未保存，耦合/弱恢复解释以连接和电压时序支持，未做定量电流归因，未宣称电气合格。

交付verification/manual_adc/sar_isolation_v1/stress_windows/report.md、key_events.json、三图；原生峰值与同刻两节点差核对，单次宽度不混用累计/其他脉冲最长，三图已查看，脚本语法及scoped diff检查通过。未改OA/PDK/标准库/其他任务，不commit/push。


## 2026-10-27 — SAR DFF内部节点局部拓扑图

用户要求将端压定位映射到晶体管拓扑。新增sar_isolation_topology.py，从已有原生连接清单核对16只绘制器件D/G/S/B，生成stress_windows/内4张PNG/SVG及总览、连接检查JSON，并在report.md解释主/从锁存节点、串联内部源节点与外部Q的区别。每图明确省略支路，未把局部图当完整DFF，未构造寄生电容或改动库。图像查看后修正标签压线，脚本执行/语法及scoped diff检查通过；不启动仿真、不改OA、不commit/push。

## 2026-10-27 — Comparator first precharge sizing point A2

User authorized independent M2/M4 and M3/M5 multi2/4 sweeps and requested observing one point first. Created only cmpdesign-precharge-a2-ff-hot-v1 (I4 input multi4, M2/M4 multi2, rest1; FF0.99V125C) in comparator_design. Exact netlist comparison confirmed only specified multis changed, original MOS geometry/models and sources/clock/solver preserved. New sim and read-only baseline review cmpdesign-i4-ffhot-reset-review-v1 used managed slots0/1, overlapping21.69s. Both native complete and collected; original baseline context metrics unchanged. New held worst terminal1.006436V vs1.021465V, decision106.7ps vs103.0ps, reset54.6ps vs59.0ps;64 total polarity/reset checks passed, CMI retained and terminal screening FAILED. New worst event moved to371.532989ns; plot includes original271.5ns and new371.5ns reset windows, full-native samples, visually checked. Internal reset residual remains~0.643mV. Report PRECHARGE_A2.md and machine results saved; new sim RSS286.6MiB,23.5s. Other sweep points not submitted to allow requested first-point observation. Scope remains netlist only, no OA/baseline adoption/commit/push. Unrelated dirty sources preserved.

## 2026-10-27 — Comparator M2/M4 multi4 and 1/2/4 comparison

Completed cmpdesign-precharge-a4-ff-hot-v1 under existing comparator_design ownership. Only M2/M4 multi4 changed from I4/A2; baseline1 and A2 reused without simulation/analysis resubmission. Full TB equality after candidate rename, exact MOS geometry/models/clock/solver confirmed. Native Spectre400ns success, all64 driven/held polarity/reset checks pass, 294.1MiB simulation peak and8.8MiB analysis peak. Worst terminal0.99890755V remains FAILED vs0.99V; compared with1.02146508V/1.00643613V for1/2. Decision113.0ps, reset50.9ps vs103.0/59.0 and106.7/54.6. Reset overvoltage amplitude reduction71.7% vs1, but net1/net2 startup peaks rise7.305→7.727→8.753mV aboveVDD; not fixed overall. Retained CMI/SFE warnings and internal~0.643mV residual. PRECHARGE_A124.md, new three-way native reset plot (visually checked), comparison/validation JSON saved; old artifacts preserved. No OA modifications, adoption, commit/push, other corner/group submissions. No comparator job in flight.

## 2026-10-27 — M3/M5 sweep with M2/M4 fixed at4

Within comparator_design, created/validated only M3/M5 multi2/4 points relative to A4. Full TB unchanged apart from names and current saves; native geometry/models/clock/solver unchanged. cmpdesign-precharge-a4b2-ff-hot-v1 and a4b4 both native complete400ns, actual concurrent overlap23.66s; peak RSS284.1/285.7MiB. Analysis-only cmpdesign-a4-start-reset-review-v1 bound to completed A4, added native startup/reset windows and phase maxima; old metrics identical. At FF0.99V125C, startup net1/net2 peaks for1/2/4 are0.998753/1.006351/1.027941V, resetLP/LN0.998908/1.000852/1.006696V; electrical fail retained. Decision113.0/115.5/120.2ps; reset50.9/49.5/48.6ps; all64 checks per candidate correct. Residualat0.5ns0.643/0.321/0.161mV improves but not a proven settling-time reduction. Saved PRECHARGE_A4B124.md, native comparison plot visually checked after startup vertical zoom, metrics/validation; KCL passes, warnings retained. No new baseline, OA, commit/push, othercorner simulations or in-flight jobs.


## 2026-10-27 — tcb DFF只读选型与CDN最小方案

按用户要求扫描STD_CELL已展开原生SPICE（11路径/9套唯一库），主12T30库336个DFF型号；原文仅暂存ignored output。新增sar_isolation_dff_inventory.py及sar_isolation_v1/dff_inventory/报告、端口/结构目录和来源验证。固定端口、N/P与D/G/S/B、合并并联后比较，哈希分组再精确映射；DFQD2仅输出变化，DFQD4内部尺寸变化，DFCNQD2/4有独立复位支路复制。OPTB与普通扫描对应D1图同构，OPTMA/OPTSAD非扫描D8同构，未把驱动档位都当独立拓扑。

选出GDFCNQMCOD1/GDFQMCOD1及SDFSYNCNQD1/SDFSYNQD1两组结构差异候选；原厂170a TT25C PDF确认功能并视觉核对真值表。GDF时钟输入电容约7倍；SDFSYNCNQ为异步清零，DFKCNQ同步清零不直接替换。候选尚未电气/时序验证或采用。CDN仅形成三种边沿（原波形1/2/4倍）、两DFF、单次目标复位、约9ns的诊断方案，保持原单元与其他条件；5fF为诊断负载，不称真实扇出。

图比较执行与重命名不变性/已知输出级差异验证、JSON/AST、手册页复核、scoped diff通过。未构建或注册/提交仿真，未改PDK/标准库/OA/其他任务，无commit/push。

## 2026-10-27 — Comparator M3/M5 minimum-width audit

Read-only audit of the exact A4 model chain, installed pch_mac bin limits and native Spectre scalefactor. With L30nm/nf1 and scale0.9, minimum model width90nm maps to netlist W100nm, exactly the current M3/M5 width. Proposed50/60/75/80/90nm widths fall outside supported bins. Conditional smaller-W sweep therefore not submitted; no simulations duplicated, no fractional multi substitute, no geometry/clock/OA/PDK changes. Added comparator_design/scripts/audit_precharge_width.py, derived JSON with source SHA, PRECHARGE_WIDTH_LIMIT.md and plan/README entry. Explicitly model applicability only, not PCell/physical DRC signoff; encrypted callback not decoded. Existing A4 electrical failure remains. Script execution and targeted whitespace checks completed; unrelated dirty work preserved, no commit/push.

## 2026-10-27 — SAR CDN三边沿最小实验

按用户授权完成三个9ns TT0.9V27C managed仿真manual8-cdn-s0/s1/s2-tt-v1，两个原生DFCNQD1不改，Q各5fF；仅CDN目标下降90–10时间16.83/33.65/67.30ps，50%时刻5ns不变，后级D固定延后11.33ps。未新增整机/PVT或候选单元测试。实际Spectre21.1 CX、reltol1e-6、maxstep1ps、gear2only，三例各约13s、313–315MiB，均原生零错误完成，CMI/SFE保留。

初版分析在Py2写结果前发生推导变量a泄漏覆盖argparse对象；原始波形完整。以args命名修正，通过三个analysis-only reduce-v2绑定完成源重新测量，未重跑仿真、未改历史结果；全部10426/10450/10428原生点回收。原生同时刻六端差及插值持续时间与独立数组复核一致，所选MOS四端总流KCL残差<4.6e-16A，稳定功能区间通过。

A.MM76 VGB峰1.057358/1.032722/1.000578V，超限6.116/5.700/3.596ps；B.MM64 VDS峰1.084223/1.080499/1.072681V，超限230.474/227.200/204.267ps。A的qf_x上升随CDN变缓，B的mq下降仍约5.53ps，后级下冲只小幅改善。清零27.25/30.28/34.80ps，三例功能通过、电气全部未过。建议下一步小台比较真正不同结构的SDFSYNCNQ/GDFCNQ，不继续只扫CDN；尚未执行或采用候选。三张波形与报告/机器数据保存verification/manual_adc/sar_isolation_v1/cdn_slew_v1，已视觉检查、原生库SHA/单变量输入/本地语法和scoped diff核对。OA、PDK、标准库、其他模块、Obsidian和10bit保持，未commit/push。

## 2026-10-27 — Comparator M3/M5 L60/90nm sweep

Completed authorized length-only comparison with A4 L30nm reused. PDK explicit length list and scaled W/L bins support both lengths at W100nm/nf1; junction/LDE geometry frozen, no PCell/DRC claim. Managed cmpdesign-precharge-a4l60-ff-hot-v1 and a4l90 complete400ns,24.385s actual overlap, ~288/295MiB RSS, analysis~8.8MiB, collection~9MiB each. All64 comparisons per candidate pass decision/reset, but CMI electrical failures remain. Held startup overshoot30/60/90nm=8.753/23.418/43.062mV; LP/LN reset=8.908/.068/.180mV. Separately identified net2 excursions3.623/6.329/9.421mV during next input update80.1–80.15ns while clock low, not clock-edge ringing. Decision113.0/111.6/111.4ps and outputreset50.9/51.8/51.9ps effectively similar; internal0.5ns residual grows. Saved PRECHARGE_LENGTH.md, native comparison/validation/model-domain JSON and two plots visually reviewed. Fixed builder unused candidate metadata inheritance; frozen inputs retained with explicit standalone correction proving actual multi1 and no measurement effect. Scoped checks passed; no new baseline, OA, other PVT runs, commit/push or in-flight tasks. Unrelated user/parallel work preserved.

## 2026-10-27 — Manual Bootstrap-only TT short tests

按用户要求完成三个独立managed短测manual8-bootshort-dc/startup/sine-v1，仅原12管IO Bootstrap晶体管级，主开关4x1um/L150nm、Cboot1p不改，其他模块VA、外源理想；并设全VA对照和静止负载保持夹具。8/4/16帧均完成、每帧8比较无FAULT，原生总点数58651/30826/115450。静态保持误差最大0.4343mV通过暂定0.25LSB；真实上电首帧Cboot仅0.5701V、建立误差4.1955mV、保持误差4.5729mV，启动筛查失败。正弦最大原始误差10.659mV、码差2失败；拟合滞后472.4ps、增益-0.0607%、残差峰19.08uV，明确不是原始精度通过、纯延迟或ENOB。外层六端差峰1.80740V，无原生CMI，不等于可靠性签核。保留DC初值容差放宽、PDK重复scale及VA环境警告，重复scale只读确认为0.9。

全部原始结果保留，流式回收各1.18–4.77MB，单仿真RSS约287–291MiB。三张图视觉检查完成，独立CSV插值与原生保持样点差<0.1uV。新增verification/manual_adc/bootstrap_short_v1、scripts/manual_adc/bootstrap_short_*及专属recipes/runs；报告、机器数据、TB与预先门槛齐备。仅完成短测及修改建议，无尺寸/时序/OA/PDK/其他实验变更，无commit/push。


## 2026-10-27 — Manual CDAC isolated short test

按用户要求完成晶体管参考开关CDAC、其余模块行为/理想的820ns TT0.9V27C短测。28只原生MOS尺寸与16只理想电容行均保留，Bootstrap替换为1ohm/10ps无注入采样器，比较器/SAR行为模型、理想源、100ns外时钟。managed源manual8-cdac-isolation-tt-v1原生零错误完成；Spectre X CX1线程，实际tran reltol1e-7/gear2only/maxstep20ps。8帧0/255/85/170/127/128/1/254码字全对，64次比较/56次更新，最大DM4.979436uV、CM1.252527uV、转换21.235ns。

初版建立窗口止于下一栅极50%导致误报；analysis-only review-v2按1%仍混入下一边沿早期耦合，40/56段通过；review-v3改用原生valid50%加既定50ps捕获+100ps更新命令，保持原2ns/.1LSB门槛，最终56/56段通过，最慢建立上界28.069ps。只重分析、不重跑/改电路，原版和v2结果完整保留；summary/比较/端压指标完全相同。先前口头56段通过早于完整v2结果，已向用户更正并等v3实测确认。

电气仍不通过：110.029226ns重新采样，N1C底板-97.691mV，M12 |VDS|/|VBD|0.997691V，超过0.99V约5.036ps；N侧1C..32C共六支高参考PMOS同类超限，原生CMI2751/2755保留。原生zoom示采样接通顶板快速下降时复位门仍0.824V，边界为采样/参考恢复重叠；建议只提前参考复位做单变量，未执行。报告、三图、测试台、机器数据和validation见verification/manual_adc/cdac_isolation_v1；图像已查看。仅TT理想电容无噪声失配PEX，非整机合格。OA/PDK/历史/其他工作未改，未commit/push。


## 2026-10-27 — SAR 原生 SDF/GDF 结构候选短测


完成：仅新增manual8-dff-syn/gdf-tt-v1两个9ns TT0.9V27C案例，原D1复用CDN1x结果；SDF SI/SE接0，GDF同端口，库SHA核对一致。两例原生零错误，功能稳定窗口通过，但电气未过。原D1/SDF/GDF的A全部端差最大1.057563/1.005447/0.970827V；B.MM64 VDS为1.084223/1.089457/1.096250V，连续超限230.474/283.173/321.195ps。GDF首级通过本小台筛查，但后级更差；SDF缓冲后MM65局部边沿3.601ps更陡，关键主锁存串联链仍在。GDF时钟绝对电荷积分为原版7.62倍，不能在理想CP条件下忽略真实驱动代价。暂不采用替代单元，建议下一步单变量D/CDN相对时序，本轮未执行。
实际Spectre21.1 CX、reltol1e-6/maxstep1ps/gear2only；两仿真14.079/13.442s、RSS322.24/315.12MiB，分析约9.27/9.10MiB；CMI/SFE原告警保留。全部MOS六端差流式测量与独立数组复核一致，时长差<1e-12ps，所选MOS KCL残差<1.4e-16A。三张图已视觉检查；AST/JSON/定向空白检查完成。报告/机器数据/图在dff_candidates_v1，两个新运行全部回收，无在途任务。仅TT理想回放5fF诊断负载，不是实际级联/PVT/整机签核；未改OA/库/其他实验，无commit/push。

## 2026-10-27 — Comparator input M8/M9 multi4 to8

完成用户指定A4I8单变量：M8/M9 multi4→8，M2/M4固定4，M3/M5固定W100nm/L30nm/multi1，其余电路/时钟/激励不变；FF0.99V125C，managed cmpdesign-input-a4i8-ff-hot-v1完整400ns回收，A4已有结果只读复用。driven/held各32次功能/输出复位通过，但端压失败。保持输入net1/net2启动上冲8.753→10.095mV，LP/LN启动8.817→13.021mV，LP/LN复位8.908→5.615mV；全程最坏转至382.036312ns LP1.003021V。判决112.98→114.02ps、复位50.87→52.18ps；DM/CM反冲0.1440/0.1684→0.2861/0.3399mV，复位前DM残差0.0974→0.1916mV。未采用8倍，4倍仅保留对照而非合格基线。

保存INPUT8.md、comparison/validation JSON及两张波形图并目视检查。原生CMI/SFE保留，364.15/372.15ns输入更新处SPECTRE-16780局部LTE放宽如实记录，未宣称全程无数值告警。仿真25.29s/RSS287.82MiB，分析RSS8.84MiB，回收9.58MiB，KCL残差约1.1e-16A。网表唯一变量、输入SHA与64次结果核对完成；脚本语法、JSON及定向diff检查。仅本目录/managed登记/共享日志；未改OA/PDK/其他实验，未commit/push，无本轮在途任务。

## 2026-10-27 — Comparator A4 clock-rise50/100/200ps

按用户要求完成cmpdesign-rise100-a4-ff-hot-v1、cmpdesign-rise200-a4-ff-hot-v1，仅VCK上升段围绕原50%对称展开，DUT/模型、全部下降沿、输入/采样控制不变。50ps绑定已完成A4作analysis-only cmpdesign-rise50-a4-review-v1，旧判决/复位/全端差/功耗字段严格相同，无重跑基线。两新仿真FF0.99V125C400ns原生零错误，全部回收；各条件driven/held64次判决与输出复位通过，端压仍失败。

net1/net2启动上冲8.753/3.235/1.389mV，最大峰对应单次超限44.70/70.28/127.57ps；LP/LN启动8.817/3.113/1.301mV，脉宽36.73/62.44/113.57ps（最长脉宽另存）。最慢判决112.98/123.60/147.98ps；输入DM反冲0.14404/0.14410/0.14281mV、CM均约0.16840mV，几乎未变。最坏端差仍371.528ns附近LN复位0.998908V。削峰有效但展宽，不宣称可靠性通过或全部修复。

rise_reduce.py按实际rise_start测完整边沿反冲并保留clock50后口径，原生流式统计连续脉冲；独立CSV原生窗口复核峰值/脉宽、全部32次实际上下沿50%、源唯一变量和AST/JSON检查完成。显示CSV末点可比400ns早20ps以内；验证按显示抽样粒度检查，原生精确终点由reducer核对，不把末点差误报为仿真未完成。CLOCK_RISE.md、两图已目视、comparison/validation与原日志齐备。CMI/SFE保留，100/200ps无SPECTRE-16780。仿真24.91/24.36s、回收8.60/8.70MB，资源在预算内。仅本目录/managed登记/共享日志，无下降沿/其他PVT追加，无本轮在途任务，OA/PDK/其他任务未改，无基线采用/commit/push。


## 2026-10-27 — CDAC采样接通与提前复位单变量对照

按用户授权完成manual8-cdac-edge-b10/s50/s100/r500-tt-v1四组820ns TT0.9V27C，沿用原28参考MOS及理想电容，尺寸不变。为只改变接通沿，复制行为采样器拆分rise/fall，按已知周期安排rise事件，电导50%固定10.030ns+n100ns、fall50%49.980ns+n100ns，fall10ps；外部CLKS不动。仅复位组独立REFRST提前500ps清gate_p/gate_n，raw码/输出捕获不动。b10用于验证新监测接口/事件调度等价：与原基线端压仅差0.687uV、比较时刻一致。原生采样边沿实测和单变量网表diff通过。

b10/50/100ps/提前500ps最低底板-97.692/-46.651/-34.341/-180.145mV，全程最大端压0.997692/0.946651/0.939802/1.080145V，最大单端对累计超限5.036/0/0/13.903ps。全部8码正确，56段建立均通过，最大DM约4.979uV、CM1.253uV，转换21.235ns。50/100ps无CMI；基线和提前复位仍CMI失败。提前复位使N顶板从0.4553恢复到上帧0.89824V，随后10ps采样接向0.001758V，跃变近翻倍，最坏移至N64C net7/M0，110.0292ns发生。原1C改善不能代表整体修复；本例否定仅提前复位建议，优先研究采样受控接通，未采用新基线。

所有managed源/分析已完成回收，真实SpectreCX1thread、tranreltol1e-7、gear2only、maxstep20ps；原生零错误，PDK重复scalefactor SFE1131及旧环境VACOMP2435告警保留。simRSS最高370.9MiB、分析10.4MiB、每组回收<7MB。verification/manual_adc/cdac_edge_v1保存README、两图、comparison/validation/manifest及四组输入；原生zoom独立核对全时域底板极值，图像已查看。原生MOS/cap行及电源/时钟一致，未改OA/PDK/其他任务/历史结果，未commit/push/PVT。

## 2026-10-27 — Comparator rise200 fixed, fall50/100/200ps

按用户要求完成cmpdesign-rise200-fall100-a4-ff-hot-v1、cmpdesign-rise200-fall200-a4-ff-hot-v1，两新仿真400ns原生零错误并回收；cmpdesign-fall50-a4-review-v1绑定完成rise200源只读重分析，旧判决/复位/全端压/供电能量逐字段一致，未重跑基线。仅VCK下降段围绕原fall50对称展开，上升200ps及全部50%交叉、DUT/模型/输入/保持/负载保持不变。

FF0.99V125C保持输入：复位LP/LN上冲8.908/7.800/5.990mV，最大峰值所在连续超限18.07/34.84/65.83ps。最长独立微小尾波142.25/131.82/120.06ps，对应仅11.736/4.808/1.801uV超出0.99V，另列不混作主脉宽。输出复位从fall50起算50.72/45.45/34.76ps，从下降开始75.72/95.45/134.76ps，明确前者缩短不表示完整复位更快；最慢判决均147.98ps。每点driven/held各32次功能通过，端压全部失败，200ps全程最大0.995990V。下一输入更新约80.1ns造成net2约3.623mV上冲未变，保留全程检查并与复位边沿统计分开。

fall_reduce按实际fall_start结束判决窗口，并原生统计至fall50后0.5ns的复位脉冲。独立验证初次整窗argmax会选主峰而非最长尾波，已按报告峰时刻定位对应连续区间再独立查找阈值交点；原始测量与结果未修改。全部实际上下沿50%、冻结源唯一变量、原生峰值/脉宽、AST/JSON与两图目视核对完成。CLOCK_FALL.md、comparison/validation、原生CMI/SFE告警齐备，新运行无SPECTRE-16780。新仿真23.67/24.35s、RSS284.11/286.09MiB，分析约9.1MiB、回收各约9.3MB，符合资源预算。未改OA/PDK/其他任务，无本轮在途任务、无基线采用/其他角/尺寸扩展/commit/push。

## 2026-10-27 — CDAC100ps接通四个极端工艺/温度短测

完成manual8-cdac-s100-ffcold/ffhot/sscold/sshot-v1四例，固定0.9V、FF/SS×-40/125C、820ns8帧，TT复用上一轮s100。100ps仍指理想采样电导接通过渡，外部CLKS50ps与参考栅控50ps、采样中点/关闭沿/参考复位/全部尺寸不变；只有MOS section和温度变化，输入SHA与差异检查保存。全部托管仿真/流式分析/回收完成，原生零错误。

FF冷/热、SS冷/热最低底板-27.508/-32.377/-37.872/-44.468mV，最大端压0.935510/0.939934/0.941065/0.945005V，168端对全部低于0.99V且无CMI；每角8/8码、64比较、56更新正确。FF热角最大DM残差710.855uV，超703.125uV预算7.73uV，末两步在0/255/1/254码各失败，总计48/56建立通过；其他三角56/56。端压改善不能等同精度全通过。75–100ns保持阶段TT/FF热角参考电流6.213/796.428uA，高底板压降4.963/710.484uV且栅控到轨、参考理想不跌落，支持漏电/静态压降假设，尚未分解漏极/体电流；FF热高参考单独持续供能约0.717mW。本轮未改尺寸，下一步建议测支路电流。

报告、两图、comparison/validation/manifest、steady_diagnostic与各角results在verification/manual_adc/cdac_100ps_corners_v1；计划plan/2026-10-27-manual-cdac-100ps-corners。图像已查看、原生时序/温度/精度设置及供电核对，脚本AST/JSON/输入hash和定向diff检查。实际Spectre21.1X CX单线程、tranreltol1e-7、gear2only、maxstep20ps；SFE1131/VACOMP2435原警告保留。仿真24.15–26.82s/RSS最高294.24MiB、分析10.38MiB以内、单例回收6.55MiB以内；本轮无在途任务。仅固定电压工艺温度短测，不是全供电PVT/真实Bootstrap/整机签核；OA/PDK/历史/其他任务只读，未commit/push/采用基线。

## 2026-10-27 — Bootstrap延后启动与M0 4/6/8um单变量

按用户授权完成7例managed短测：首次采样延后100ns至110ns，保持100ns周期、39.9ns脉宽和50ps边沿；先验证原M0x4启动，再固定上电/时钟条件各跑8帧DC、16帧4.501953MHz正弦，其他模块行为级、外源理想。M0只改multi4/6/8，全部其他器件/VA/模型一致。启动Cboot0.57015→0.89999996V，首帧误差4.57295→0.41274mV，预算通过。

三档滞后472.50/275.00/172.85ps，拟合残差峰23.28/14.18/12.31uV，静态差分关断台阶0.434/0.663/0.905mV，最大端压1.80740/1.81635/1.81873V，均无CMI；4um正弦码差仍达2，6/8um不超过1，静态24码全匹配。原始高频误差10.659/6.260/4.009mV仍保留，拟合不是原始误差通过或ENOB。SFE1131/VACOMP2435保留，显式启动无17191。

所有运行原生完成并流式回收；simRSS≤344MiB、analysis≤10MiB、单例回收≤5.12MB。输入散列及电路单变量验证、逐帧关闭沿、独立显示波形与原生保持样点、AST/JSON和三图目视检查完成。新增bootstrap_width_v1及bootstrap_width_*脚本、专属recipes/runs；报告含启动图、宽度收益代价图、关断台阶与残差分布。6um作为均衡候选建议、8um更低滞后，未采用基线，未改OA/PDK/其他任务，无PVT/全码FFT/commit/push。

## 2026-10-27 — Comparator clock edges extended to500ps

完成cmpdesign-r500-f200-a4-ff-hot-v1、cmpdesign-r200-f500-a4-ff-hot-v1、cmpdesign-r500-f500-a4-ff-hot-v1，200/200只读复用；FF0.99V125C400ns，A4尺寸、DUT/模型/输入/保持/负载及全部50%时刻不变，仅VCK边沿变化。全部managed仿真/分析/回收结束，每组64次判决和输出复位通过，端压均失败。

保持输入：上升500ps使启动1.389→0.511mV、峰值连续越限127.57→301.51ps，最慢判决147.98→223.99ps；下降500ps使LP/LN复位5.990→3.548mV、主脉冲65.83→155.30ps，从实际下降开始输出复位134.76→250.69ps。下降50%后约0.69ps的报告值仅表示复位在交叉附近完成，原生采样括区约0.96ps，不能说复位只需亚ps。下降500ps另引出net1/net2复位1.865mV/29.53ps；全程最坏为80.142077ns下一输入更新处net2/M5DG/M7SB/M9DB的0.9936225V，既有扰动未修复。500/500没有优于200/500的全程最坏端压，却增加判决时间/功耗，不采用基线。

edge500_reduce扩展至完整边沿，稳定复位从实际fall_start测量；原生四类脉冲峰值/持续时间、全部实际50%时刻、模型/DUT身份及单变量网表、64次功能独立验证通过。CLOCK_500.md、comparison/validation JSON及两图保存并目视检查。实际Spectre21.1X CX、reltol1e-7、gear2only、maxstep20ps；零原生错误，CMI2752–2756/SFE1131保留，三组无SPECTRE16780。仿真约23.7s/组，RSS最高290.4MiB，分析<9.2MiB，单组回收<9.4MB；脚本AST/JSON/文档链接与定向diff检查完成。无本轮在途任务，无OA/PDK/其他任务改动，无commit/push。

## 2026-10-27 — Comparator fixed200/500ps input/reset branch attribution

按用户要求固定A4/200ps rise/500ps fall，完成cmpdesign-edge-current-a4-ff-hot-v1。原400ns源只读；新观测从0保留历史至85ns，唯增save和改stop；全held15MOS四端流与id/电荷等OP齐备，三窗口618/253/618个原生点未抽点。节点峰值复现最大差5.54pV，KCL残差<1.12e-21A，DUT/模型/所有源一致、连接表和原生脉宽独立核验通过。

输入更新80.142077ns net2 0.9936225V、连续53.32ps，CLK=0；输入起点至峰值M9.D注入+0.049185fC，M5.D/M7.S抽取-0.048946/-0.000240fC。M9动态-DeltaQd+0.049232fC与导电项-0.0000446fC重建总流，支持输入栅漏动态耦合；M5 id/qd重建约4.7%残差保留，不宣称其精确分解。复位79.491171ns net2与83.491171ns net1均0.9918650V/29.53ps；越过VDD后到峰值M7/M6.S注入+0.003204fC，M5/M3.D与M9/M8.D分别抽取-0.002773/-0.000431fC。源端-DeltaQs重建误差0.018%，对侧LP/LN上升约176mV、漏端只变19uV，支持交叉耦合栅源路径。正常预充与超轨后阶段分开，未把初期M3/M5充电判为越限驱动。

EDGE_CURRENT.md、三张电压/支路电流/电荷图及attribution/validation JSON保存，图像已检查。提出当前边沿下M3/M5 1→2与独立M8/M9 4→2单变量候选，保留旧50ps加宽失败、启动馈通/SS速度/精度风险，不实际调尺寸或继续放缓边沿。85ns原生零错误，CMI2752–2756/SFE1131保留，无SPECTRE16780。sim19.27s/RSS286.79MiB、analysis9.13MiB、回收3.44MB，托管预算内。脚本AST、JSON、链接及定向diff检查，无在途任务，无OA/PDK/其他任务改动，无基线采用、commit/push。

## 2026-10-27 — FF热角CDAC参考开关支路漏电定位

完成manual8-cdac-leak-ffhot-v1，原FF0.9V125C/s100/820ns8帧只追加100条保存电流，28MOS四端与电容电流齐备。尺寸/模型/拓扑/外部理想激励/100ps采样接通过渡及关闭沿不动。原生/managed分析/回收完成，等价重放码字与时序一致，端压峰差2.11e-14V、比较DM差1.94e-13V。旧FF热精度失败保留，没有调整规格。

码0的75–95ns最大漏电在P64C XADC.XP.XD.M1：ID398.808831uA、IS-398.784598uA、IG-0.294122nA、IB-23.939077nA，VGS12nV已关断。REFP经导通M0、底板、关断M1流向REFN；M0压降710.484uV、有效Ron1.7815ohm。全高参考状态NMOS每C漏电6.231uA，按multi比例，P64占总参考796.428uA的50.08%；低参考关断PMOS每C约0.04062uA，明显更小。确认主要是关断漏源电流，非栅未拉低/体电流主导；未分解内部亚阈值/DIBL/GIDL比例。

按采样关闭前后底板误差变化核算：P64贡献-358.221uV，N1..32合计-352.624uV（N32-179.111、N16-89.555）；P1..32及N64参考状态没变，初始和最终压降抵消，不随耗流量直接计入残差。重建-710.845uV与实测-710.865uV，8帧最大差19.744nV。有效底板高低跨度约0.899283558V，较理想缩小0.0796%，持续等待不能恢复；不是已经测得缺码或ENOB下降。建议后续仅改NMOS L评估漏电/Ron，未执行。

全部原生点28管、14底板和2参考轨KCL最大残差1.472e-13A；导出CSV独立核对1.022e-13A，8个20ns时间加权窗口/112支路记录完成。verification/manual_adc/cdac_leak_ffhot_v1保存README、两图、results/branch_table/validation/independent_current_check/manifest，图像已查看。原生零错误、无CMI，SFE1131/VACOMP2435保留；SpectreCX1线程/实际reltol1e-7/gear2only/maxstep20ps。仿真33.77s/RSS294.92MiB，分析103.91s/RSS11.43MiB，回收14.83MiB。脚本AST/JSON/输入hash/定向格式检查；仅本任务与共享追加日志，无在途任务、OA/PDK/历史/其他任务改动、commit/push或基线采用。


## 2026-10-27 — 6 µm Bootstrap四个极限角短测完成


6um extreme-corner short tests completed: eight manual8-bootpvt-{ss/ff}-{cold/hot}-{dc/sine}-v1 runs finished, analyzed and collected serially; TT6um reused. Fixed reference0.9V/inputCM0.45V/fullscale1.8V,1ns supplyramp,110ns clockstart and149.975ns close retained. Native PDK SS/FF macros confirmed SS_18/FF_18. All32new static codes exact;96new frames have8comparisons/noFAULT. Minimum precharge99.9014%VDD; startup/static/quiet-hold/terminal screens pass. SS cold/hot sine rawerror25.7978/17.9183mV, lag1152.698/799.694ps, residualpeak1038.119/156.429uV, code delta4/3 fails unchanged1code screen. FF cold/hot rawerror2.5472/4.3772mV, lag108.113/189.701ps, residual20.381/25.688uV, codedelta1. Static held peaks SS cold/hot0.55998/0.58249mV, FF cold/hot0.75775/0.76521mV. Maximum terminal1.906979V, zero nativeCMI; not lifetime/wholeADC qualification.6um remains selected netlist candidate, SS high-frequency tracking unresolved.

Validation: source hashes/material single-variable generation, native temperature/log settings, actual halfVDD clock edges and retained native snapshot consistency checked;3PNG/SVGfigures reviewed. SS cold display-decimation interpolation differs from native held sample by<=6.361uV, failing original0.1uV displayagreement diagnostic; recorded explicitly, not used for metrics or waived. Allothercorners pass displaycheck. Next-capture tail has oneextra risingedge as intended, noextra close. Native reltol1e-7/gear2only/maxstep50ps;SFE1131/VACOMP2435 preserved. SimRSS<=291.01MiB,analysis<=9.82MiB. Reports/plots/results/validation in bootstrap_pvt_v1; no work in flight for this batch, no OA/PDK/oldresults changes, no commit/push. Bounded requested test complete; next engineering issue is SS dynamic tracking, not another startup fix.

## 2026-10-27 — Comparator200/500ps independent precharge/input sizing

用户确认两个独立对照后，完成cmpdesign-edge-b2-ff-hot-v1（仅M3/M5 multi1→2）与cmpdesign-edge-i2-ff-hot-v1（仅M8/M9 multi4→2），基线cmpdesign-r200-f500-a4-ff-hot-v1只读复用。FF0.99V125C400ns，全部W/L/nf/其他multi及test.scs/models.scs与时钟/输入/负载不变，原生零错误，managed双槽运行并全部回收。每组driven/held共64次判决/复位通过，端压失败。

保持输入：基线/A/B输入更新3.623/1.814/1.800mV，主宽53.32/52.72/51.70ps；启动net1/2为1.389/2.034/1.361mV；复位net1/2为1.865/0.742/2.000mV、主宽29.53/26.20/38.82ps；LP/LN复位3.548/4.457/3.575mV、主宽155.30/164.87/161.46ps。判决147.99/152.52/156.94ps，边沿起算复位250.69/241.72/246.47ps。差模反冲0.14281/0.14442/0.07186mV，功耗2.210/2.310/2.147uW。A全局最坏转355.477889ns LN0.9944568V，整体恶化；B转371.480192ns LN0.9935745V，全程仅改善约0.048mV，不能以馈通减半声称电气修复。不组合、不采用基线、不自动追加SS或失配。

EDGE_SIZES.md、两图及edge_sizes_comparison/validation JSON齐备，图像已目视。源模型字节一致和唯一multi改变、实际上下沿50%、主峰/最长脉冲、全程最大端差、稳定复位与64次功能独立核验通过；下一输入64节点窗口均在原生不抽点导出区，脉冲无截断。实际SpectreCX单线程、reltol1e-7、gear2only/maxstep20ps，CMI2752–2756/SFE1131保留，无SPECTRE16780。sim24.24/24.79s、RSS290.31/286.13MiB，analysis9.13/9.17MiB，回收9.31/9.39MB；AST/JSON/链接及定向diff检查。原OA/PDK/历史/其他任务未改，无在途任务、commit/push。

## 2026-10-27 — Manual CDAC FF-hot NMOS L30/60/90 sweep

Completed managed manual8-cdac-nl60-ffhot-v1 and manual8-cdac-nl90-ffhot-v1; reused manual8-cdac-leak-ffhot-v1 for L30. Only seven shared-subckt NMOS L tokens changed (14 branches), W/nf/multi/PMOS/geometry extras/models/stimuli/100ps sample turn-on/close/reset fixed; no OA. Read-only PDK supported-length and actual W/nf bin check passed; frozen LDE retained, no layout legality claim.

L30/60/90: P64C OFF NMOS 398.809/32.848/9.880uA, high-rail drop710.484/58.504/17.604uV, low-rail offset5.959/8.065/10.305uV, max comparison DM710.855/66.058/27.700uV. Settling48/56,56/56,56/56;8/8 correct codes each. Total REFPhold796.428/70.224/24.648uA; N64 effectiveRon2.292/3.102/3.964ohm. Bottom minimum-32.377/-42.071/-51.536mV, max terminal0.939934/0.942071/0.951536V; noCMI. L60/L90 pass this short test, L30 failed precision preserved. L60 is sufficient at FF0.9V125C; L90 lower leakage but greater undershoot. Next SS settling and high-VDD stress before selection; no baseline adoption.

New native sim34.28/34.30s, RSS288.70/286.75MiB; analysis106.30/105.43s, RSS11.38/11.41MiB; collection15.26/15.20MiB. Native0errors; sameSFE1131/VACOMP2435 and Spectre21.1X CX1thread/effective reltol1e-7/gear2only/maxstep20ps.64apertures/56segments/8steadywindows/168terminalpairs, nativeKCL<1.83e-13A, charge closure<19.76nV, independent exported KCL/timing/input hashes verified. README,3figures visuallychecked, comparison/validation/branch_table/legality/manifest in verification/manual_adc/cdac_nlength_v1. AST/JSON/scoped checks complete. No pending jobs, no other-task changes, no commit/push.

## 2026-10-27 — Comparator combined precharge2/input2 at200/500ps

用户授权组合后，完成cmpdesign-edge-b2i2-ff-hot-v1，FF0.99V125C400ns。相对基线仅M3/M5 multi1→2、M8/M9 multi4→2；相对任一独立候选仅另两条multi不同，其他尺寸/模型/源/时刻/负载不变。三旧例只读复用，四组比较原三组数值逐字段相同，未覆盖旧结果。新run全部托管完成回收，64次判决/输出复位通过，端压失败。

组合输入更新0.901mV/51.44ps，启动net1/2 2.024mV/138.95ps，LP/LN启动1.931mV；net1/2复位0.731mV/29.94ps，LP/LN复位4.494mV/168.86ps。判决161.23ps，下降开始到输出复位237.07ps，DM/CM反冲0.07282/0.08319mV，比较器供电2.238uW。整体最坏355.472714ns LN0.9944943V，相关M14GB/GS、M6GB、M7DB；比原整体最坏高0.872mV。输入更新两项收益叠加约降75%，但未抵消LP/LN复位恶化，不采用基线、不追加其他尺寸/PVT。

EDGE_COMBO.md、两张四组叠图、edge_combo_comparison/validation保存，图像已检查。源模型字节一致、四条multi唯一改变、实际上下沿50%、原生主峰/最长脉冲、全程端差、稳定复位及功能核验通过。脚本语法/JSON/链接与定向diff检查。实际Spectre21.1X CX单线程、reltol1e-7、gear2only/maxstep20ps，原生零错误、CMI2752–2756/SFE1131保留，无SPECTRE16780。sim23.63s/RSS288.61MiB、analysis9.19MiB、回收9.22MB，预算内。无在途任务，OA/PDK/旧实验/其他任务未改，未commit/push。


## 2026-10-27 — SS冷角Bootstrap导通/栅压/关断分解


SS冷角跟踪定位完成（manual8-bootss-probe-tt/ss-v1及manual8-bootss-m0-tt/ss-v1全部managed完成/回收）。两组16帧等价0V漏端探针与历史保持样点最大差0.000126/0.000898uV；原生温度/模型、唯一电气探针差分、输入散列和独立M0常偏置已核对。三图在bootstrap_ss_diagnosis_v1；没有改MOS尺寸/拓扑时序/OA/PDK或采用修复。

稳定跟踪M0有效电阻中位TT306ohm、SS1132ohm；VGS约0.889/0.801V稳定，Cboot没有塌陷。独立M0固定VDS1mV、VIN0.45V：TT/VGS.889为303.516ohm；SS/VGS.889为509.084ohm；SS/VGS.800为1104.356ohm；SS恢复VGS.810也仅988.252ohm。R*C预测0.388/1.414ns，对应实测关断前实际时刻滞后0.390/1.435ns。源体偏置扫描SS/VGS.8的R从751到1626ohm，支持输入相关导通非线性；未将全部拟合残差强行归因于体效应。

关闭沿处滞后TT390.036ps/SS1436.745ps；保持+1ns相对关闭沿滞后275.001/1152.698ps，关断过程净相位追近115/284ps，不是主滞后源。关断VGS0.3V标记TT156–210ps、SS394–596ps，非精确通断/孔径定义。原生关断全点导出消除旧显示稀疏问题；SS保持1→3.5ns最多31.742uV，不能解释约26mV原始误差。

评价澄清：SS25.798mV原始误差主要为相位，仅对齐常相位后峰差1.583mV，全增益/偏置/相位拟合残差1.038mV（RMS.751mV）；相位对齐解析量化器最大码差1。原同关闭沿4码筛查失败记录保留，但不是4LSB非线性或ENOB失败证据。固定延迟不直接降低单音SNDR；16样点不能证明全频段纯延迟/ENOB。建议暂留6um，先核对SS完整频谱/频率响应，再决定是否需要8/10/12um单变量增宽；不优先增加Cboot或加快放电，不改低角供电/输入来通过。提出方案未执行修复/FFT。

新运行无CMI；原生SFE1131/VACOMP2435保留。simRSS<=287.32MiB、analysis<=10.77MiB、单组回收<=15.98MB；M0 SS曾正常排队，未绕过管理；初始本地配方summary_signals缺失在注册前拦截并修正。源/脚本/JSON/文档链接/图像和定向diff核对，四组无在途任务，无commit/push。


## 2026-10-27 — Comparator combined LP/LN reset branch diagnosis (checkpoint)

固定组合M2/M4 multi4、M3/M5和M8/M9 multi2及200/500ps边沿。完成源cmpdesign-edge-b2i2-ff-hot-v1原生波形的两节点电压/LN七条完整端流分析：LN355.472714ns、LP379.472714ns各0.994494V/168.86ps。LN越轨→峰值M6.G+0.047345fC、M0.G+0.013976、M7.D+0.012338；M4.D−0.069578主要回拉。M1.D总积分负但峰值附近正，报告明确时间依赖。M6.G支持内部恢复动态耦合路径，未把Cgd/Cgs比例或LP对称电流推断当作实测。建议M2/M4单独4→8，未扫尺寸。

补齐OP观测v1 cmpdesign-combo-latch-current-ff-hot-v1因output_size_limit明确失败（536958941B，RSS305299456B），失败状态本地保存，未重启/覆盖。v2减少为68个必要信号，DUT/模型相同，网表仅save/stop变化，保留0起381.025ns；最新managed queued/user_cgroup_headroom，辅助进程继续等待，资源策略未放宽，无重复提交。v2 LP支路/OP、两张详细图及validator待仿真数据，不宣称完成。run.py在本目录新增limit_exceeded/expired终止态，避免失败后无限轮询。

COMBO_LATCH_CURRENT.md、figures/combo_latch_source.png、results/combo_latch_source_attribution.json已写，图已目视；7端连接按冻结DUT核对、KCL<5.71e-18A、积分/源峰值、AST、链接和scoped diff检查通过。README/PLAN更新。未改OA/PDK/旧实验/其他任务，无commit/push。回续先查v2精确状态再收取，不重复启动；若队列因资源超时拒绝须保留结果。


### 同轮完成更新 — LP/LN两侧端电荷观测已回收

上述v2随后获资源准入，381.025ns仿真/分析/回收全部完成，无在途任务。两窗口各645原生点，LP7端流和OP补齐；峰值相对完整源汇总差<1.2e-14V。LN主M6.G+0.047345fC（−ΔQg0.047379，差0.072%，栅漏电峰值0.83pA）、M0.G+0.013976（误差0.0043%）、M7.D+0.012338（−ΔQd0.012373、−∫id−0.0000346，重建差5.48e-7fC）。LP逐条对称实测；M4/M2主要抽取−0.069578fC，有导电和动态分量。M1/M0.D全段净抽取但峰前转注入，其重建差0.0010fC保留，不给精确比例。两节点KCL<7.5e-22A。

COMBO_LATCH_CURRENT.md/PLAN/README已替换待运行状态，三图已目视；combo_latch_attribution/validation与原生证据保存，身份/连接/原峰值与脉宽/主要电荷重建/双侧对称性/AST/链接验证通过。sim29.14s RSS284.31MiB、analysis6.21s RSS8.77MiB、输出约169.4MB、回收839695B。Spectre21.1X CX实际单线程/reltol1e-7/gear2only/maxstep20ps，0错误，CMI2752–2756/SFE1131保留，无SPECTRE16780。只给M2/M4独立4→8建议，未扫尺寸/扩展PVT，不采用基线。OA/PDK/历史/其他任务只读，无commit/push；此前v1输出限制失败完整保留。

## 2026-10-27 — Manual CDAC L60 cold settling and high-VDD stress

User-selected NMOSL60, W/nf/multi/PMOS and100ps sample-on/window/close/reset unchanged; native CDAC ref switches, ideal other blocks/caps, fixed0..0.9V input/reference, logic/PMOSbody follows VDD. Completed four820ns tests: SS0.90/-40,SS0.81/-40,FF0.99/-40,FF0.99/125. Each56/56 settling,64apertures,8/8codes; all224updates/32codes pass. SS maxsettling32.934/39.353ps vs2ns budget; DM0.0200/0.0183uV at numerical floor; maxterminal0.946468/0.948646V,noCMI. FFcold/hot maxDM0.0670/59.9780uV, maxterminal1.021792/1.029437V,CMI2752–2755. XADC.XN.XD.M5 drain-body peaks at109.991811/109.991982ns, bottom-31.792/-39.437mV whilebody0.99V; sampler just connecting and gate still~0.99V, before110.025ns reference reset. Sampling top-plate transition capacitively drags bottom low; do not attribute mainpeak to later gate reset. Electrical issue remains despite correct codes.

Original ss081cold-v1 failedSPECTRE16927 at1.14929ns beforefirstsample; retained. Recovery ss081cold-i1p-v1 changed only iabstol10fA→default1pA, actualreltol1e-7/vabstol10nV/gear2only/maxstep20ps retained, successful; not same-tolerance evidence or picoamp precision claim. FFhot-v1 definitively queue_timeout rejected before simulation; after user-authorized memory release, identicalcircuit/solver retryFFhot-v2 completed. Usercgroup had~45.3GiB filecache,~1.0GiB RSS; POSIX_FADV_DONTNEED on five named completed rawfiles released2.02GiB charged memory, filesizes/mtimes unchanged, no deletion/kill/globaldrop/gatechanges. Exactidentities andmemoryrecords retained.

verification/manual_adc/cdac_l60pvt_v1 containsREADME,2reviewedPNGs,comparison/validation/manifest/results andfailure/cache evidence. Full-native scalar measurement and timing/source identity checks pass; FFcold KCL10.098nA fails original1nA diagnostic (preserved); others<0.21pA. Python2 mixedlist/tuple sorting omitted early extendedcurrent windows; original full-native scalar metrics unaffected, independent fixed reset_native voltage export verifies worstpeaks and plots, currentwindow decimation explicitly disclosed. Allfourmanagedruns collected within32MiB;no workinflight. NoOA/PDK/userObsidian/otherexperiments changes, baseline adoption,commit orpush. Next unresolved target is high-VDD sample-reconnection undershoot/terminal margin; no new sizing/timing repair performed.


## 2026-10-27 — Comparator combined M2/M4 multi4→8

用户授权后完成新run cmpdesign-combo-a8-ff-hot-v1，FF0.99V125C400ns；只读复用cmpdesign-edge-b2i2-ff-hot-v1。唯一M2/M4 multi4→8；M3/M5和M8/M9 multi2及所有几何/模型/输入/200-500ps时钟/50%时刻/负载不变。managed仿真、分析和回收结束，各driven/held32次判决/输出复位正确，端压失败。

4→8：启动net1/2上冲2.024→2.865mV（主脉宽138.95→150.33ps）、启动LP/LN1.931→2.324mV（128.42→131.83ps）；复位net1/2 0.731→0.749mV（29.94→19.85ps）、复位LP/LN4.494→2.192mV（168.86→115.79ps）。最慢判决161.23→179.56ps、从下降开始输出复位237.07→215.58ps、平均比较器供电2.238→2.414uW。输入更新仍0.901mV，反冲基本不变。全程最坏移到354.058845ns net2启动0.9928645V，相关M7SB/M9DB；对称net1同类。复位改善51.2%，但启动/速度/功耗代价明显，不采用基线，不再追加扫描。共同理想CLK源两上下文合计净功率2.85→4.25nW另注明，不能当作单比较器真实驱动功率。

COMBO_A8.md、两图与combo_a8_comparison/validation已保存，图像已目视；唯一两multi、test/models字节相同、事件与实际50%、原生主峰/最长脉冲、稳定复位、全程端压、64功能、旧组合汇总逐字段不变独立核验通过。AST/JSON/链接/定向diff检查完成。Spectre21.1X CX实际单线程、reltol1e-7、gear2only/maxstep20ps，原生零错误，CMI2752–2756/SFE1131保留无SPECTRE16780。sim24.24s RSS286.80MiB、analysis31.49s RSS9.24MiB、collect9248998B，预算内。无在途任务；OA/PDK/旧数据/Obsidian/其他任务未改，无commit/push。


## 2026-10-27 — PDK与数字库端压规则核查


完成：只读核对DRM T-N28-CL-DR-002 v2.3(2025-08-27)第643–649页、170a TT标准单元手册第12–13页及当前V1.8_3模型。核心nch/pch六端差默认max0.99V，1.8V管对应1.98V；原生CMI阈值一致。DRM给寿命机制/条件但Vmax相关条目仍待qualification且指定N28HP；数字库绝对电压指向TSMC Online e-Reliability按寿命条件评估。未找到可用于当前HPC+ULL尖峰的峰值/脉宽豁免表，未取得正式模型/库配套证明。明确严格端压筛查未过不等于已证明寿命失败，也不能因脉冲短或属于标准单元而批准。ov_ratio未改；MSOA文档实为Mixed Signal Open Access，排除为SOA证据。
资料缓存仅ignored output/manual_adc_voltage_rule_audit，三份新PDF远端SHA匹配，既有标准库PDF SHA与清点匹配；关键表/寿命段已视觉核对。摘要与来源JSON在verification/manual_adc/voltage_rule_audit，JSON/定向空白检查完成。无新仿真、无远端写入/OA/PDK/标准库修改，无commit/push；其他实验dirty保留。后续所缺为对应工艺qualification/产品寿命条件/厂商认可可靠性评估，本轮资料核查已完成，不把缺失数据猜成许可值。

## 2026-10-27 - Bootstrap6um TT/SS coherent FFT batch launched

User requested unchanged6um SS cold1024point spectrum and low/mid/high TT comparison. Built immutable copied nativeBootstrap/ideal-other-block fixtures at k17/257/461 over1024,10MS/s,-1dBFS,32warmup. Same supply/reference/input/start/window/closing-edge and MOS dimensions as selected candidate. Dedicated read-only VA event observer plus1ns strobe saving reduces raw output without relaxing conservative/maxstep50ps. Pilot observer syntax failure and console-parser failure preserved; corrected analysis-only on completedpilot verifies exact16codes versus oldSS, held difference9.8212nV,8cmp/1EOC/noFAULT,zeroCMI. Native effective reltol1e-7/gear2only; pilot sim48.90s/peak326.07MiB, analysis8.37MiB, collection42286B. DirectFFT/Parseval/directfundamental and ADCtoolbox0.9.1 SNDR/SFDR numerical cross-check prepared. ENOB>=7/SNDR>=43.9dB target; SFDR has no separate specified limit.

Serial managed background flow PID31676 now running manual8-bootfft-ss-k461-v1; six full cases prepared, not completed. Exactflowstate output/manual_adc/bootstrap_fft_v1/flow_status.json; source/partialreport verification/manual_adc/bootstrap_fft_v1/. Fullplots/review awaitingactual1024codes; no16frameENOBclaim. Resume by inspecting existing flow and each run, never resubmit uncertain cases; frozen failures preserved. No circuit/OA/PDK/oldresults/sharedmanagement changes, no commit/push. Existing sar8 automation remainsPAUSED, not modified.


## 2026-10-27 — Historical Mmain2/L90 functional freeze and TT static batch

User freezes pre-stress-repair e94e802 historical DUT for functional characterization, retaining idle reset, two explicit1um Mmain units/side and reference L90nm; no subsequent keeper/IO/standard-cell edits. Curated byte-exact DUT SHA41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4 matches allfive historical PVT DUTs; inverse16L changes matchesMmain2/L30 predecessor. New independent design entry does not adopt baseline or updateOA.

TT0.9V27C10MS/s lowcodes0..3/three boundaries35frames started managed sar8frozen-tt-001-003-v1, hash36689b1340b15945152fcc051cf1c2a5cefee5e7e8fccd9df541cc60f5adb1f3. Original external load/clock and VA source/observer preserved; requestedCX4threads/preset_override/reltol1e-6/maxstep10ps; observedgear2only/10nV/100fA. Firstnative frame0 input-0.896484375V outputs2 with8/8/8/16counts and held-0.878146048634V: startup remains incorrect, no steady-state verdict yet. Rawwarnings retained; stress deferred peruser, notqualified.

Finite serial flowPID33560 analyzes/collects lowcase then, only on native decode/timing/center/bracket pass, runs8remaining segments4..255. No scheduler resumed; sar8 remains paused. Status output/sar8_frozen_static/flow_status.json and lock must be checked before continuing, no duplicate or uncertain resubmission. Sim1GiB/4threads,analysis256MiB,collection32MiB; resource policy honored. Full-case metrics pending. Version/PVT/MC staged milestone report docs/sar8_frozen_functional.md; original027b951FFT not attributed tofreeze. MC requires per-unit mismatch semantics/nominal equivalence and identical random realization across code segments; not launched.

Python compile, decoder/timestamp/truncation focused check, allrecipeinput hashes, byte-exactVA, unique255boundary partition and YAML parse pass. Shared management tools/policy and other manualADC/comparator/Obsidian/10bit dirty changes preserved; no historical data deletion, OA/PDK edits,commit orpush.


## 2026-10-27 — Isolated standard-cell rebase onto historical functional freeze

User asks independent digital merge. Generated sar8_l90_mmain2_stdcell_v1 from exact historical parent41d5444c; candidatef31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea. Reused reviewed digital transformation, not later wholeDUT;12masters/96referenceinverterpairs replaced. All other subcircuits and port contracts, driver non-MOS/RC/clear/analog/Mmain2/L90 preserved, exactinverse restoresparent. Native library referencedonly; no proprietary contentscopied. Manifest records transformer/library identities. Structural/AST/JSON/YAML checks pass; timing/load/function stillunverified, no simsubmission or baselineadoption. OriginalTT batch continues unchanged; timerremains paused. README explains actualaperture/handshake/BBM/power paired shorttest next; stress remainsdeferred. NoOA/PDK/library/history or otherexperiment edits, noGitmerge/commit/push.


## 2026-10-27 — Frozen A/B TT short test registered and queued

User authorizes paired native wholeADC TT short test, stress deferred. A=41d5444c Mmain2/L90;B=f31b66c8 isolated digital migration. Identicalbench/stimulus TT0.9V27C10MS/s,10centerframes0/0/12/127/128/243/255/255/0/128;originalloads/clocks preserved. Save fullnative interfaces; unchanged VA observer crosschecks codes/counts. Measure external/internal/sequenced sample close, diagnosticBootstrapVGS0.45fall,8cmp/write/update/16capture/order/stability, preclose/hold error and measured-precompare-referenced DACtail. No idealDAC accuracy or physicalthreshold claims. Native library/PDK freshlysha256matchhistorical;inputhash/AST/identicalA-B and correct/misorderedhandshake targetedtests pass.

ManagedA sar8ab-a-tt-short-v1 hash496fc6b5f6be1a4ff4be87c6776b243158a336f27a0a399adba5cdde808cfcf5 submittedqueued user_cgroup_headroom. B sar8ab-b-tt-short-v1 hash1a06cfca0f92ff2fd3a0fcb050b4ba64480fb9638d1d11f897f58edb35c4b947 registeredonly;finiteflowPID49752 waitsA thenserialB/analysis/collection/report. Read output/sar8_ab_short/flow_status.json beforecontinuing;no duplicatesorautomaticretries. Priorlowcodeflowunchanged. Sim1GiB4threads/output2GiB,analysis256MiB,collect32MiB;noresourcebypass/cachedeletion/processkill. NoactualA-BresultorfigureQAyet. verification/sar8_ab_short/README.md statespending. Sharedotherdirtywork/PDK/library/OA/history preserved;timerstillpaused,nocommit/push/adoption.


## 2026-10-27 — User-authorized completed-run cache release; A/B admitted

Accountmemory primarilyfilecache(~45GiB) versusRSS~1.3GiB. Scopedinventory404terminalfiles plus7 limit_exceededfiles, exactmanagedterminalenum. POSIX_FADV_DONTNEED411regularUID596files afterrunstate/openfd/mapping/inode/size/mtime checks; allreturns0. Released29.546GiBcache; accountused46.270->17.075GiB/headroom1.730->30.925GiB. ConcurrentAstartup explainscache/netdifference. Deleted0files/reclaimed0diskbytes/killed0processes; raw/finalresults/PDK/OA/libraryretained,noglobaldrop orpolicychanges. Active/unknownsourcesuntouched. Fullinventory/receipts/summary verification/sar8_ab_short/memory_cleanup.

WindowscommandlengthfailureoccurredbeforeSSHcreation; switchedinventorypayloadtostdinthenbothpassescompleted. Existing sar8ab-a-tt-short-v1 worker automaticallyadmittedslot1/PID180871,running~353MiBRSS; Bregisteredserialfollow-on. Priorlowcodejobpreserved,noduplicate/timerchange. Statusdocsupdated,syntax/JSON/scopeddiffchecks; nocommit/push.


## 2026-10-27 — A/B short-test partial native recovery

Read-only managed status and bounded native log tail recovered: A running, B not_started. A frames0-6 expected/actual 0/2,0/0,12/12,127/127,128/128,243/243,255/255; startup fails, following six observer codes correct. Counts8/8/8/16 each; SAMPLE_INT close41.079504ns, close-to-last-update29.704-29.965ns. Not sequenced close, full order or settling qualification. Effective transient reltol1e-7 versus global1e-6 retained. Receipt verification/sar8_ab_short/partial_20261027.json; README and plan updated. Existing finite serial flow continues; no duplicate submit, incomplete-PSF analysis, timer change, circuit change or commit/push.

## 2026-10-27 - Bootstrap FFT recovery and first1024point result

User requested six-case completion/recovery. Actualbatch1/6complete: SSH failed during polling firstSS; remote simulation finishednormally, subsequentfive hadnotstarted. Reusedcompletedmanual8-bootfft-ss-k461-v1 via managedanalyze/collect (noresimulation);1056framesperchain/1024FFTcodes,8cmp/1EOC/noFAULT,independentstrobeagreementallpass,zeroCMI. SS0.81V-40C4.501953MHz SNDR48.400786dB/SFDR58.546867dBc/ENOB7.747639 vs samecaseideal48.756061/64.818326/7.806655. Margin4.500786dB over43.9 target. Lag1.157ns with0.763mVrms fittedresidual;4code rawgap retained,not4LSBdistortion. Largestspur3.505859MHz foldedthird. Preliminary6um adequate for this isolated SS point; TT/otherfrequenciesnotyetmeasured, noallADCclaim.

Twofiguresviewed; report/results updatedonlyactualcompletedrow. Circuitinvariance,105721native1nsstrobes,fullframeevents,Parseval/directfundamental/ADCtoolbox0.9.1crosscheckpassed. Failurelogpreserved; localflowstatus transportonly retriesbounded5times, mutationsneverreplayed. ResumedserialcontrollerPID45088; TThighrunning,remainingfourfollowwithoutcircuitchanges. NoOA/PDK/otherexperiments/automation/commit/pushchanges. Check output/manual_adc/bootstrap_fft_v1/flow_status.json before recovery; results verification/manual_adc/bootstrap_fft_v1/README.md. Fullsix-casecompletionstillpending.

## User stop: unstarted Bootstrap FFT cases

Stopped local bootstrap_fft_flow parent45088 and child46288 after exact commandline/identity verification. TT k461 native simulation stillrunning, SS k461 completed data intact. Low/mid k17/k257 TT/SS notregistered; no submissions remain fromthiscontroller. Preserve allinputs/results; no other tasks/processes/automations modified. Further low/midlaunch requiresuserresume.


## 2026-10-28 — User-selected low60/high40 A/B phase verification

Supersedes unsubmitted101ns candidates; originals retained. New external clock low from0, rise60ns/fall100ns,100psedges,39.9ns high plateau gives40ns threshold high width and60ns normal low. Same frozen A/B DUTs/conditions; stimulus and measurement origin shifted59ns. First valid code157ns must pass; ten original center codes retained. Observer time-origin-only edit roundtrips to original, no electrical contributions; native reducer origin/count/order positive/negative tests and input hashes passed. Managed phase60 A registered a44f1dc5da9173361ac1b43cbf8499c776bf4ff50f4864d79196bd9d7227339c; B e008f2bc1d5ef60d19df25fa760d03293b7016e838e0030bf3d65f2ba0e96bb4. Finite serial flow launched, inspect output/sar8_ab_phase60/flow_status.json for actual PID/state. No waveform/result verdict yet; preserves resource queue and existing flows, no timer/OA/PDK/library/DUT changes or commit/push.


## 2026-10-28 — Deadline-priority SAR8 server campaign and six-slot admission

User moved deadline priority to1024FFT+five-point key-code PVT before fullstatic,
and explicitly allowed more slots. Fresh48CPU quota/~29GiB accountheadroom,
~106GiB hostavailable/zero swap supported6managedheavy slots,4threads/job. Updated
only concurrency fields in policy/docs/AGENTS/default; retained legacy2slot tests
with explicit2 policy; focused6-slot CPU/memory/unknown-process checks passed.
Published through managed storage API; remote policyhashbd74a262b4346e9a530120fa14b8b414596bc5f7f865fa868d3ddb9f8e6ecc08.
Existing phase60A,originalB andphase60B admitted; unrelatedmanualADC retained.
Old frozen-static local submit loop checkpointed and stopped(PID33560; child5908
already disappeared); active remote low-code simulation163198 preserved.

Prepared/registered100strict future cases and24solver benchmark/priority variants;
none of the long cases submitted before prerequisite checks. Solver variants CX
moderate andMX moderate, unchanged10ps maxstep/DUT/stimulus, compare to strict
phase60 native10frames. Exactcodes/order,5psaperture,50psconversion/tail and
0.02LSBacquisition diagnostic tolerances; differing settings not equalaccuracy.
Coordinator selects passingB elsepassingA; selects faster passing solver else
strict; then one continuous1024FFT plus4additionalPVTscreen cases in parallel.
Fullstatic follows priority artifacts, lowboundaries thenpairs. Runtime limits
and resource gates remain. FFT decoder streams10psstrobe; power estimate pending
native/gridconvergence, excludesinputsourcepower andlistsclockseparately.
MC not submitted: statisticalsections found but independentunit/multi mapping
still needs verification. No assumed distribution/seed claims.

Finite coordinator deployed to campaigns/sar8-functional-20261028 using exact
managedagent API c63a3f6c; first launch128MiB AS limit caused libcrypto import
failure before any API call. Preserved console/launch; verified dead PID234764,
removed self-imposed inherited AS cap (managedworkers set their own budgets),
restarted identical coordinator/manifest PID236574. Readback shows both phase60
runs running. Metadata-only coordinator does not depend on laptop. Receipts in
verification/sar8_campaign; no heartbeat resumed, noOA/PDK/library/DUT edits,
no committed/pushed changes or baselineadoption.

## 2026-10-28 — Use spare slots for solver comparisons

User authorizes autonomous resource management within own account/project.
Admission observations show about27.4GiB account memory headroom and zero swap;
no additional cache eviction or file deletion was needed. Submitted existing
immutable sar8camp-b-cm-bench-v1 (recipe350b734c) and
sar8camp-b-mm-bench-v1 (recipe599a1a82) into the two available slots. Readback
confirms both running, Spectre PIDs238305/238512, RSS about356/373MiB. Six managed
simulations now admitted including the untouched manualADC run,21 declaredthreads.
Finite server coordinator reuses these IDs; FFT/PVT remain conditional on actual
phase60 and solver comparison results. No circuit/library/OA changes, no paid
services, no commit/push, and no automation changes.

## 2026-10-28 — Recover A/B phase60 and CX/MX, resume priority batch

All four phase60/solver simulations completed, native exit0. Original phase60A
analysis failed on missing optional lowercase Bootstrap BTOP/BBOT save names;
server coordinator stopped before FFT/PVT. Preserved failure/raw; four new
sar8camp-recover-{a,b,cm,mm}-v1 analysis-only runs bind completed sources. Missing
charge probes explicitly null, all functional/timing signals mandatory. Parser
and per-frame measurement AST identical to original; analysis completed119/121/
123/37s within256MiB budget, small outputs collected and verified. No resimulation.

A/B all10codes includingfirst0 correct;8compare/8write/8update/16cap perframe,
observer/native checks pass. B SAMPLE_INT close +4.927ps,SEQclose+4.547..5.202ps;
conversion28.874..29.118ns vs A29.660..29.898ns (~0.78ns faster). Min measured-DAC
quietmargin A513.190ps/B464.325ps, not blanket improved settling. Maxpreclose
sourceerrors0.057842/0.040645mV; firsthold200ps0.445530/0.437160mV.
CXstrict B2079.555s; CXnominalmoderate2064.809s actuallysameconservative1e-7/
gear2only and identical recovered metrics. MX308.169s,6.748x,actual1e-6/trap.
MX diagnostic pass: maxclosure0.02056ps,conversion5.499ps,pinerror3.132uV,
tailquiet9.284ps, exactcodes. Not equal-accuracy/fullFFT proof; stress deferred.
Report/JSON/visually-reviewed figure:verification/sar8_campaign/recovery/.

Corrected only four optional save-node cases in new B PVT mm-v2 recipes; source
DUT/electrical setup unchanged. Verified actual uppercase instance/node names.
New continuation_v2 maps completed source IDs to immutable recovery IDs; focused
fake API check validates both identities and no duplicate submit/analyze. Old
PID dead and failurecheckpoint retained. New coordinatorPID59989/hash13354111,
manifesthasha86a5707 deployed separate continuation-v2 subtree. Readback confirms
selectedB/MX and allfive prioritysimulations running:TT fft1024-mm-v1 and
ssc/ssh/ffc/ffh-screen-mm-v2. TTshort supplies fifthPVTpoint, notfullfivecorner
static qualification. Original waveform/library/OA/DUT and unrelateddirtyfiles
preserved; no commit/push/baselineadoption/automationchanges.

## 2026-10-28 — Add A FFT parallel companion

User requests runtime estimate and parallel A FFT. B observed~312s wall and8
completed warmup frames at~0.9us of103.259us; estimated9-12h simulation plus~30min
analysis allowance, provisional early-rate estimate, not guaranteed completion.
Actual memoryheadroom~20GiB,48CPUquota,zero swap, free managedslots available.
New A MX bench-v2 corrects four optional save names only, same DUT/stimulus and
solver. Registered53548f19. Companion checks A's own strictCX recovered reference,
then MX short diagnostic before A FFT. Pass launches existingA-mmFFT; fail uses
existingstrictAFFT and preserves mismatch, notblindB-speedtransfer. Focused
selection/order tests passed bothbranches. Remote a-companion PID63401,codehash
e4ac4dd5,manifest60231cb3; readback nextstep saved. B/PVT continuation untouched.
No circuit/OA/library edits, no commit/push/automation changes.

## 2026-10-28 — A MX benchmark recovered, both FFTs confirmed running

Managed sar8camp-a-mm-bench-v2 simulation302.431s/analysis34.980s complete;
collected bounded outputs with no skippedfiles. Local recomputation using same
reviewed diagnostic agrees pass:10/10codes includingfirst0, all8/8/8/16cycles.
Max SAMPLE_INT delta0.026332ps,SEQdelta0.020335ps,conversion5.279ps,pinerror7.833uV,
DACquietmargin9.137ps;7.026x observed speed versus ownstrictCX reference.
Fixed optional savecases yielded both Cboot charge~0.900V before59ns.
ActualA MX CMI2751/2754/2755 on XCDAC.XSN4.MN_LOW at~62.229ns; preserve relative
to strictA noCMI, no claim either solver qualifies stress. Numeric16780/16881also
retained. No endpoint peak/convergence inference from truncated warningprints.
A/B FFT-mm-v1 both running, no uncertainworker observation; A strictFFT remains
notstarted. Local report/receipts:verification/sar8_campaign/recovery/a_mx/.
No sourcecircuit/PDK/OA/policy/automationchanges; no commit/push.

## 2026-10-28 — Recover B five-point PVT screens and A/B FFT progress

All four B non-TT mm-v2 screen simulations+analyses complete; collected all
small results with no skipped files, preserve raw/native warnings. Same-MX TT
reference from recovery/mm supplies fifth point. Each of5corners passes all10
codes [0,0,12,127,128,243,255,255,0,128], includingfirstframe; all8/8/8/16counts,
order, native/observer crosscheck andvalid flags pass. Conversion maxima TT29.124,
SScold39.797,SShot34.293,FFcold25.873,FFhot27.741ns. Maxsourcepreclose errors
0.04067/0.26829/0.02386/0.06669/0.05001mV. Allhold200ps windows have noDACupdate.
CMI presentTT/SScold/FFcold/FFhot, absentinSShotlog; not electrical qualification.
Only B has this fivecornerbatch; A has TT tests plus in-flight FFT, no inferred
A PVT result. No fullstatic/noise/mismatch/PEX claims; passives fixednominaltt.

Bounded64KiB native-logtail+managedstates observed epoch1793148185: A FFT12/1032
frames (8warmup+4/1024measured),elapsed388s; B37/1032 (8+29),elapsed1147s,both
running. No completed FFT metrics. Comparison/status/provenance/report saved
verification/sar8_campaign/pvt_recovery/. No circuit/OA/PDK/library/policy/process
mutations, no new simulations, no commit/push/automationchanges.

### 2026-10-28 — 分段复位性能笔记单版本整理

按用户要求整理 Obsidian_docs/Rvision/8bit性能与ADCToolbox.md：删除 R4 对照文字、表格和图片引用，保留 027b951 空闲段分步复位版，注明结果于 2026-10-23 回收分析。十二图读法压缩为表格，保留相位参照、残差定义与验证范围。新增 note_figures.py 从历史 candidate 数值重绘 static_idle.png 与 spectrum_idle.png，未改变指标或原始记录。

验证：绘图脚本执行成功，两图目视检查通过；全部 5 个嵌入及本地链接存在，正文无 R4，静态指标与 JSON 一致，完整目标 diff 已审阅。本次范围 diff --check 通过；全仓检查另报原有 Wrap-up & Experience.md:13 尾随空格，保持不动。无仿真/OA/PDK/标准库/后台任务变更，无 commit/push。计划：plan/2026-10-28-sar8-idle-note/plan.md。

## 2026-10-28 — Parallel A five-point PVT requested

User explicitly requests A same-fivepoint screens versus B, stress recorded but
functional/startup/settling priority. Reuse A TT MX bench-v2; prepared/registered
A ssc/ssh/ffc/ffh screen-mm-v2 correcting four save-node cases only. Verified
A/B corresponding test.scs,tb.scs,observer,analyzer text and preset/resources,
corner/supply/temp/reference/frame/expectedcode contexts identical, DUT difference
intentional. All historicalregisteredinputs retained. Finite a_pvt coordinator
runs4managedjobs+analysis and assembles5point A/B comparison, actual failureflags
preserved. Focused assembly/no-duplicate/order/fail-preservation checks passed.
Remote a-pvt PID73242,code31a30c8a,manifest24af2da5; launch readback saved under
verification/sar8_campaign/ab_pvt/. Uses6slot sharedqueue with twoFFT jobs, no
resource changes. No circuit/OA/PDK/library edits, commit/push/automationchanges.

## 2026-10-28 — A/B five-point PVT comparison recovered

A ssc/ssh/ffc/ffh screen-mm-v2 simulation andanalysis complete; all bounded
collections have no skippedfiles, raw preserved. A/B each5corners x10frames pass
firstframe0/allcodes and8/8/8/16 protocol/order/nativeobserver crosschecks. TT
reuses completed ownMX benchmarks, same-case electrical fixture verified before
submission. Maxconversion A/B(ns):TT29.904/29.124,SS-cold40.531/39.797,SS-hot
34.899/34.293,FF-cold26.630/25.873,FF-hot28.515/27.741. B longestconversion is
0.606..0.780ns shorter; actualSAMPLE_INT closure B-A4.884..7.837ps acrosscorners.
Minrelative-DACquiet A/B(ps):513.27/464.70,751.39/636.41,685.23/603.79,
416.58/388.52,517.53/480.97. Not blanket improvedsettling; noidealDACaccuracy
claim. Maxpreclose sourceerrors A/B(mV):.05783/.04067,.26336/.26829,
.03972/.02386,.07888/.06669,.07035/.05001. NoDACupdates in200psholdwindows.
CMI A:TT/FFcold/FFhot present,SSlogs absent; B:TT/SScold/FFcold/FFhot present,
SShot absent. Numericwarnings preserved. Functionalonly, no stresssignoff.

FFT snapshot Beijing2026-10-28 09:01:32: A50/1032total,42/1024measured,24.94min;
B74/1032total,66/1024measured,37.59min,bothrunning,~0.37GiBRSS each. NoFFTfinal
metrics. Reports/JSON/collectionreceipts verification/sar8_campaign/ab_pvt/.
No simulations restarted, no circuit/OA/library edits, no commit/push/automation
changes. User Obsidian updates are unrelated and retained.

## 2026-10-28 — User-requested compute scaling diagnostic

Observed48CPU quota,~17GiB headroom,no swap,2running4threadFFTs. Raised only
per-job allowable thread ceiling4to16 and +mt allowlist1..16; default4,6heavy
slots,aggregateCPU/memory/disk gates retained. Initial registration rejected by
oldallowlist before remote submission; corrected scoped allowlist, boundary
checks0/17reject and1..16accept, exact sourceinput identity passed. Published
policy d6040cb0. New unique A MX short runs mt8/mt16 admitted with nativePID
83064/83270; originalFFTPIDs59993/65587 unchanged. Native16request islimited
to8threads forsmallcircuit; both actually8, recommends2or4. No performance
conclusion yet; runningcheckpoint saved verification/sar8_campaign/thread_scaling.
At epoch1793149846 FFT A/B lastobserver68/92 respectively, both running.
Scoped diff-check passed. No circuit/model/OA/library changes, deletion, commit,
push or automationchange. Recover/analyze compute benchmarks on continuation.

## 2026-10-28 — Thread scaling recovered, FFTs retained

mt8/mt16-request A short simulations completed271.876/272.140s; both actual8
threads vs4reference302.431s,10.10/10.02percent wall-time reduction. Same
immutable inputs and actualMX settings; managedanalyses complete, each8files
~2.44MB hash-collected withoutskip. All10codes/startup/nativeprotocol pass;
reported close/conversion/acquisition/tail metrics identical to4threadreference
at analyzer precision. Native CMI/numericwarnings retained. Historicalload differs,
B8thread scaling unmeasured, no2x speed claim. BothFFTs continue original4threads;
restarting would erase most/all estimated~52min gain. No simulation restart,
circuit/model/OA change, policyedit, heartbeatresume, commit/push or deletion.
Comparison and timestampedFFT snapshot:verification/sar8_campaign/thread_scaling/.

## 2026-10-28 — A/B TT fullstatic started alongside unchanged FFT

User requests spare-resource parallelA/B TT static, preserving4threadFFT and
no mistakenkills. Fresh48CPU quota,15.9GiB accountheadroom,96.9GiBhostavailable,
zero swap;30.4GiB accountfilecache versus1.7GiBanonymousRSS. No cleanupneeded.
Finite ab-static coordinator reuses18registeredstrictCX4threadcases, low1..3
perlabel first then2independent segments/label;6sharedheavy slots includingFFT.
Checked low-first,2cap,idempotent-running recognition, failedA permitsBadvance
and completion using syntheticmetadata. Remote registeredhashes/coordinatorhash
and PIDstartticks verified. Coordinator89555; A/B lowstatic89559/89589 running;
FFTPIDs65587/59993 unchangedrunning. Native4threads verified, conservativeCX
staticdistinctfromMX FFT. OriginalBcontinuation later reusesidenticalmanagedIDs.
No serverprocesskilled, cacheflushed, historicaldeleted, policychanged, heartbeat
resumed, circuit/OA/PDK changed, commit/push. Evidence verification/sar8_campaign/
ab_static/. Fullstaticresults pending; sharedresourcecontention not assumedzero.

## 2026-10-28 — In-flight A/B FFT code audit

Readonly boundednative-log snapshots Beijing09:29:56: A108/B131totalframes,
100/123after8warmup. Allrecords8/8/8/16counts,early=late,valid1,conversion<60ns,
no protocolfailure. Source-aperture idealcodes differ88/100and110/123,max3LSB;
do not call allcodesideal. Held-top ideal differs11/100and18/123,max1LSB,all
within.143LSBofnominalboundary. Partialfit held/source equivalentlag.845/.838ns;
physicalcause not established. Codefit residualmax.499/.529LSB withgain/DC/phase
removed,notfinalFFT. Common100measuredframes differonlyframe13(151/152)and
37(30/31). Firstframeboth231 vsheldideal231/sourceideal232. Artifacts/script
verification/sar8_campaign/fft_live_audit and live_fft_audit.py. No fullnative
waveformcrosscheck yet, no performance/electricalqualification. Allsimulations
unmodifiedrunning; no cleanup, newheavyanalysis, policychange,commit/push.

### 2026-10-28 — ADCToolbox ±1 LSB 静态总览

按用户要求扩展分段复位性能笔记：实际调用本地 ADCToolbox plot_dnl_inl，生成 static_idle_overview.png；保留现有 static_idle.png 放大图。使用同一 027b951 边界搜索数组，明确 1/128 LSB（54.93 µV）区间中点法、标称 DNL 与端点 INL 归一化差别，未进行直方图重分析。保留用户对笔记的其他精简。

验证：项目虚拟环境运行 note_figures.py --overview-only 成功；两轴 ±1 LSB 和绘制数组完全一致的断言通过；新图目视审阅通过，全部 6 个嵌入存在，目标 diff --check 通过。原始数据、放大图、频谱与后台仿真不变，无远端/OA操作，无 commit/push。

### 2026-10-28 — ADCToolbox 正弦直方图真实重算

从 027b951 历史 dynamic_frames 的 1024 个整数输出码调用 analyze_inl_from_sine(num_bits=8, clip_percent=0.01)，不使用边界数组。结果：DNL −0.3132305～+0.2749805 LSB，INL 最大绝对值 0.170241 LSB；观察码 13–242，工具返回轴 15–238。同相干长度、拟合幅相的理想量化器合成对照 DNL −0.313638～+0.279583、INL 最大绝对值 0.176641 LSB，明确其为算法对照而非电路仿真，提示短记录有限采样/估计误差。不能据此确认全码静态线性度。

新增 reanalyze_static.py、verification/sar8_idle_performance/reanalysis_20261028.json、static_sine_reanalysis.png；笔记替换仅绘图的总览，保留边界搜索放大图和原指标，说明数据/口径区别与后续均匀慢斜坡要求。实际运行、源哈希与样本数核对、链接检查和图像目视通过；scoped diff --check 通过。没有新电路仿真，没有伪造均匀斜坡数据，无远端/OA/后台任务变更，无 commit/push。

## 2026-10-28 — Partial low-code recovery and FFT checkpoint

Beijing10:38:16: A/B lowstatic stillrunning21/35and22/35frames. Boundednative
logs recovered; both0->1boundary samebracket[-.892144775391,-.892089843750]V,
status0,midpointoffset+.12109375LSB vsnominal. Width1/128LSB; notfinalDNL/INL.
Centers0/1correct; secondboundarysearching,thirdpending. Finalnativewavecrosscheck
notrunonunfinishedraw. FFT A252total/244measured,B271total/263measured,alllogged
observerprotocolflagsvalid. All4processesrunning unchanged, no resourcewait.
Partialreport verification/sar8_campaign/ab_static/low_partial_1793155095.md.
No newsubmissions, circuit changes, cleanup, commit/push.

## 2026-10-28 — Manual ADC overvoltage atlas
- Preserved user-adjusted CDAC and comparator geometry in private Analog Canvas; reconciled comparator numbering, added internal-node labels, compacted complete 28/24-MOS DFF diagrams with stage headings. Native D/G/S/B connectivity readback passes; DFF diagnostics clean. Comparator's existing decorative stubs/port-label observations retained.
- Added Obsidian_docs/Report/手搭ADC-过压图解.md and assets/manual_overvoltage with four SVG/PNG circuits plus copied existing waveforms. Note distinguishes event time, terminal pair, state transition, inferred causes, measured current evidence, and unsuccessful optimization outcomes. Bootstrap omitted.
- Local image review and all note links checked; scoped diff whitespace check passes. Editable project and validation saved in output/manual_overvoltage_atlas. No new simulation, OA/PDK/library mutation, baseline adoption, commit or push.

## 2026-10-28 — Low-end nearing completion, second boundary recovered

11:11:03Beijing A32/35,B33/35stillrunning. First2boundaries identicalA/B,
midpoints−892.117309571/−885.086059571mV,both+.12109375LSBnominalshift,
1/128LSBbrackets/status0; centers0..2correct. Thirdboundaryrefining, nofinal
acceptance yet. All16remainingstaticcases notstarted, coordinator correctly
awaitingcompletedlowpass. FFT314/330effectivepoints,allloggedprotocolvalid.
Boundedmetadata/log snapshots saved ab_static/progress_1793157063.json and
low_partial_1793157063.md. No simulation/process/model changes or commit/push.

2026-10-28 — Manual overvoltage atlas: redrew both DFFs around left-to-right signal flow and local latch feedback, separated clock buffer below. Retained complete 28/24 MOS and verified all 112/96 D/G/S/B terminal partitions. Preserved user CDAC/comparator content; CDAC revision metadata advanced only. Updated Obsidian SVG/PNG and explanation; visual review complete. Native project backed up; no simulation, commit or push.

2026-10-28 — Overvoltage atlas highlight revision: added colored node/branch overlays and event badges to four native SVG derivatives, compacted the Obsidian report with evidence tables and expandable waveform/full-circuit details. Visible prose ~26% shorter; 99/99 extracted constraints retained; local links valid; images reviewed. Original Canvas circuit geometry/connectivity unchanged; no OA, simulation, commit or push.

## 2026-10-28 — A/B low-end passed; fullstatic auto-expansion verified

Bothlowruns35frames simulation+analysiscomplete,exit0; each7smallartifacts
hashcollected/no skip. Native35framecodecrosscheck,centers0..3,bracketstatus,
monotonicity andfunctionalpass true; startup4frames0/valid. All3A/B brackets
identical at1/128LSBresolution; midpoints−892.117309571,−885.086059571,
−878.054809571mV,each+.12109375LSB vsnominal. Notfullstaticmetrics; B CMI
2751..2755retained, noelectricalqualification. At12:29:55Beijing automatic
coordinator89555 has startedA/B s004-035,s036-067,all4running; othersegments
waitingturn. OriginalFFT A481/B490effectivepoints,47.0/47.9percent,running.
Evidence ab_static/low_complete.md,low_comparison.json,post_low_progress.json,
a_low/b_low collections. No newsubmission, processkill/restart, model/OA change,
policychange,cleanup,commit/push or automationchange.

## 2026-10-28 — FFT ~67percent; partialstatic A/B boundary comparison

14:05:31Beijing FFT A684/B685effectivepoints, running unchanged. Static only
previouslowsegmentcomplete; no newcomplete segment tocollect. Active A4..35
49/325,A36..6747/325,B4..3551/325,B36..6750/325. Read boundednative logtails;
11boundaries/version(1..7,36..39),13unique testedcentercodes(0..7,35..39),
alltestedcenterscorrect/bracketstatuses0/knownadjacentboundariesordered. Only
boundary36 differsA/B by+54.9316405uV(1/128LSB) inB,adjacentbrackets touch;
other10same. Provisionalrunningdata, onlyfirst3boundaries finalnativecrosschecked;
nofullcode/no-missing-codequalification. Coordinator6running/nofailure/wait.
Evidence ab_static/progress_review_1793167531.md,partial_comparison_1793167531.json.
Initial read-only probe failed due Python2comprehensionvariableleak; corrected
query only, no remote artifacts/processes modified. No newsubmission orcleanup.

2026-10-28 — Comparator note clarified: exact combination4/8 sizes, measured balancing steps, three event mechanisms and TT evidence boundaries. User then authorized0.9V PT tests and one extra managed slot: 6->7 deployed with other limits unchanged. Ten frozen cases prepared, TT4/TT8 collected with all diagnostic screens passing; remaining FF/SS cases running serially. No OA/PDK/library changes, commit or push. See plan/2026-10-28-comparator-pt09/plan.md and comparator_design/PT_09V.md.

2026-10-28 PT09 checkpoint:8/10 collected, all diagnostic screens pass (TT27,FF-40/125,SS-40, two sizes). SS cold worst4x/8x .957117981/.978890863V; decision540.115/670.800ps. NoCMI warnings in8logs; SFE1131 retained. SS hot4 queued: user_cgroup_headroom ~7.94GiB below8GiB aggregate admission threshold; slot6 is available, do not change gates. SShot8 not submitted; serial runner retained (local exec session8025), queue timeout600s. Summary chart visually reviewed, inputs/metrics/counts/resources and links checked; partial results written to PT_09V.md and Obsidian note. No adoption/OA/commit/push.

2026-10-28 — Per user request, removed expanded PT/history material from Obsidian comparator section; retain A8 results and three sizing/edge tradeoffs. Comparator prose reduced from 3231 to 961 characters. A8 source values and links checked; CDAC/SAR byte-identical, full experiment evidence remains outside vault. No simulation/OA/assets/commit/push.

2026-10-28 — Moved six source links in the manual overvoltage note to a collapsed end-of-note reference block, per user request. Other user-edited prose/images preserved verbatim; links checked. No circuit/assets/simulation/commit/push.

2026-10-28 — Added requested short opening summary to manual overvoltage Obsidian note; summarizes three module stress classes and outstanding electrical qualification. Remaining note byte-identical; no commit/push.

2026-10-28 — Added concise CDAC L60 and comparator A8 W/L,nf,m annotations in Obsidian, verified from corresponding frozen netlists. Explicit literal netlist W avoids conflating fingers/multiplicity. All other user content unchanged. No simulation/OA/commit/push.

2026-10-28 — 按用户要求填充 Obsidian_docs/Report/PVT验收-频谱.md，采用 ADC-过压图解 的概况、短说明、指标表与折叠来源风格。核对 ab_pvt/comparison.json，A/B 各五角10帧码字与握手均通过；记录转换时间、采样误差、内部关闭沿差异、逐位安静裕量及CMI告警。15:30北京时间只读managed状态确认两版TT FFT仍simulation running、analysis not_started，不填历史版本频谱冒充新结果；TT低端0..3通过，全码其余仍待完成。10组数值及通过字段、所有来源链接和scoped diff --check通过。参考笔记保持原样，无仿真提交/进程修改/OA/PDK变更，无commit/push。首次run-status使用错误CLI参数只返回usage，修正为位置参数后读回成功。

## 2026-10-28 — 16:20 campaign status

Read-only bounded native logs/state: FFT A970/1024 effective (94.7%), B959/1024 (93.7%), both simulation running, analysis not started, original PIDs unchanged. A static4..35 89/325 and36..67 87/325; B93/325 and90/325. No new completed segment; coordinator no failures/wait. Each variant19 recorded boundaries (1..11,36..43),21 tested center codes (0..11,35..43) correct, ordered known adjacent brackets and no observer-invalid flags. Only boundary36 differs by54.9316405uV (one search step); other18 brackets identical. Running-segment evidence provisional, original CMI warnings remain; no final FFT/fullstatic/electrical verdict. Snapshot verification/sar8_campaign/ab_static/status_1793175649.json. No launch/restart/resource-policy/other-task changes, cleanup, commit or push. Shared seven-slot policy added by comparator task is preserved.

## 2026-10-28 — A/B 1024-point FFT completed, collected and plotted

Both original MX4thread runs completed exit0 (A29354.308s/B30522.210s); managed streaming analyses completed exit0 in293.86/293.18s at~7MiB RSS. Seven hash-checked small files collected perversion (A466569/B473324bytes), no skippedfiles/no raw-wave download. All1032 frames native decoded vs observer identical; startup and1024 steady records all protocol-valid. Current frozenA SNDR48.789405821dB/SFDR64.003984294dBc/ENOB7.812193658; frozenB48.788077375/64.767791653/7.811972986. Twenty codes differ by1LSB, no assertion of equality to ideal code. Core+reference power estimate A138.620922uW/B86.530560uW from10psgrid, no integration convergence signoff. A noCMI inthisbatch; BCMI2751..2755 retained. Both retain numerical warnings and actualreltol1e-6/trap; no equal-accuracy whole-recordCX claim. NumPy/ADCtoolbox0.9.1/native FFT agree within1e-8dB, Parseval and fitted residual consistency pass. Source phase explicitly removed for relativephase fit. SpectrumPNG/SVG plusA/B12-panelPNG visually inspected; local wrapper separates harmonic labels without altering old renderer. Evidence verification/sar8_campaign/fft_final/README.md/results.json/collection receipts. All static runs/coordinators untouched, no circuit/OA/Obsidian/baseline/commit/push changes.

2026-10-28 — 按用户要求简洁更新Obsidian_docs/Report/PVT验收-频谱.md：加入冻结A/B当前TT1024点SNDR/SFDR/ENOB及功耗估计、对比结论和频谱图，折叠链接两版ADCtoolbox12图与完整依据。更新概况，区分PVT短测与长FFT的CMI记录，保留原PVT/时序内容。三张已验图复制至vault assets/sar8_campaign_fft，逐文件hash一致；表格与结果JSON及所有链接核对通过。无仿真/OA/其他笔记/commit/push改动。

2026-10-28 — Updated user-created Obsidian_docs/手册.md for Canvas ECS procurement: added RAM account creation and explicit ECS/VPC/order permissions, concrete encrypted PEM transfer and login acceptance, and removed console-readable handoff fields. Preserved purchase configuration and Owner-selected 3-month/1-year choice. Full readback, required-content and whitespace checks passed; official Alibaba Cloud RAM references checked. No actual credentials, cloud/OA changes, staging, commit or push. See plan/2026-10-28-canvas-purchase-manual/plan.md.

2026-10-28 — Simplified Canvas procurement manual private-key handoff at user request: direct one-to-one PEM attachment, no archive encryption or password call; recipient saves the file and validates SSH. Updated receiving step and handoff summary; preserved intervening user edits elsewhere. Targeted obsolete-text/content checks and scoped diff --check passed. No actual credentials transferred, cloud/OA changes, commit or push.

2026-10-28 — Fixed RAM permissions table in Obsidian_docs/手册.md: moved the table out of numbered-list nesting, made it standalone with blank lines, and referenced it from step 4. Verified five rows/two columns, unindented table syntax and byte-identical text outside the replacement span. User deletions and other sections preserved. No cloud operations, commit or push.

2026-10-29 — Read-only SSH overvoltage document review completed. Found model usage guide PDF38–41/printed37–40 and actual core model default 0.99V six-terminal-pair thresholds; adjustable ov_ratio is a check setting, not reliability permission. Standard-cell170a manual p12 refers voltage ratings to TSMC Online lifetime assessment. DRM v2.3 reliability and design-information sections inspected with technology-scope limits; no applicable HPC+ULL transient envelope established. Four PDF copies SHA256 matched, source model remotely hashed, critical pages rendered/inspected. Corrected MSOA to Mixed Signal Open Access. Original findings and sources under verification/sar8_overvoltage_doc_review; raw documents remain ignored output. No simulation, circuit/PDK/OA/adoption/automation/commit/push changes; unrelated dirty files preserved.

2026-10-29 — Continued SSH search for independent reliability/voltage-duration documentation at user request. Listed PDK_DOCS/PDK_DOC/Packages, inspected55 ZIP indexes and nested core/RF model packages, six numbered small reports, RF DRM1.8_R and STA signoff guide. Final filtered metadata traversal6145dirs/216entries completed without errors; excluded implementation trees and unexpanded large archives explicitly recorded. No current-core ps/ns envelope located; DRM647 points to Qualification Report, standard-cell manual to e-Reliability. Newly found public TSMCHOME RN190A p1–2 establishes model SP0791.0_2p8 and valid CCS180a/doc170a/spi170a combination. Its native model also defaults core Vgs/Vds warnings to0.99V; no change or false-warning inference. New source hashes/visual checks and search manifest saved under verification/sar8_overvoltage_doc_review. No simulation/PDK/OA/model/automation/commit/push changes.

## 2026-10-29 — Unified nch/pch overvoltage evidence

User requested analog NMOS/PMOS coverage as well as standard cells. Read-only model and library inspection independently confirms six default core terminal checks at 0.99 V and 1.8 V device checks at 1.98 V. Parsed 11 existing frozen A/B native logs (165 printed terminal-warning entries); all instance paths resolve to actual model families. Retained A TT CDAC MN_LOW Vgd -0.997397 V, B TT DFF PMOS Vgs -1.012960 V / NMOS Vgb 1.000700 V and B SS-cold DFF NMOS Vds 0.994701 V as printed events, not waveform maxima or durations. B TT-short native log excluded as not locally collected. Unified device-specific reliability references; no applicable voltage-duration/lifetime permission found. Artifacts: verification/sar8_overvoltage_doc_review/device_matrix.md, device_warning_inventory.json and bounded extraction script. Source/log/netlist identities preserved. Validation: parsing and hierarchy assertions, numeric readback, JSON and scoped diff checks. No simulation, circuit/model/OA mutation, automation change, commit or push; unrelated dirty state preserved.

2026-10-29 — Continued reliability-document search. DRM v2.3 PDF p11 reference table (rendered/verified) identifies T-N28-CL-QR-095, HPC+ 0.9/1.8 V Fab15; report body not found and ULL applicability not established. Fully streamed current standard-library doc archive (98 files) and nested ULL PDK DOC archive (263 entries / 122 selected document-text entries), no standalone target. Seven additional guides and representative IO databook inspected; eight downloaded sources hash-matched remotely. IO p9 operating table visually verified, not a core transient permission. Supplementary filtered live filename scan timed out at25s/19505dirs and is explicitly incomplete. Original summary and source/index manifest saved in verification/sar8_overvoltage_doc_review/qualification_followup.md and followon_search_manifest.json. JSON/count/hash/whitespace validation passed; transient envelope still unresolved. No simulations, models/circuits/OA/automation changes, commit or push; unrelated dirty state preserved.


### 2026-10-29 — Continued reliability-document search

Completed resumed filtered T28 filename inventory (126924 directories, 281080 files, queue empty; no target matches/errors), full current ULL implementation index (94066 entries), model-text scan and local OCR of all 363 corner-note pages. DR-070 AVT/SRM_ULL supplement p4 cites QR-095; scope and citation visually checked, downloaded ZIP remote hash verified. Other public-process shallow metadata search completed with 8 access errors retained. Saved persistent_search.md and persistent_search_manifest.json. Numerical device voltage-duration/lifetime envelope remains unavailable; no warning waiver or reliability pass. No simulation, model/circuit/OA/automation changes, deletion, commit or push.

2026-10-29 — User authorized transient-noise progression. Created scoped noise plan, three immutable B40frame recipes and streaming short analyzer; sources/hash/compile checks passed. Installed Spectre tran help confirms noise controls. Managed preflight passed under unchanged7slots; registered/submitted off,1GHz,2GHz seed101 cases. Off submission response timed out; original state readback confirmed running, no resubmit. All3 running at 2026-10-29T16:50:28.551424+08:00, noisy logs confirm requested fmax/fmin/seed; no completed noise result yet. Shared static runs untouched. resistor help timeouts retained; resistor setting parsed successfully in off transient. No OA/DUT/PDK/baseline/automation/commit/push changes. See verification/sar8_noise/README.md and output/sar8_noise/latest_status.json.

2026-10-29 19:55 — Noise status/recovery: three B40frame simulations completed exit0 (off1512.12s,1GHz4683.56s,2GHz5819.36s). Managed stream analyses exit0 in~13.7s/~6.2MiB;7 hash-checked files each collected (~64kB), no raw. All40 codes match observer, protocol/settling screens pass, all original warnings retained.32steady paired held difference RMS86.37/77.98uV,2/1 one-LSB code differences, no fullFFT/no noise convergence claim. Native options verified. Results verification/sar8_noise/comparison.json and README.md. No new simulations, static/resource-policy/OA/circuit/automation changes, cleanup, commit/push.

2026-10-29T20:04:08.769043+08:00 — User authorized first B1024 noisy FFT2GHz/10kHz/seed101. Frozen new run sar8noise-b-tt-fft1024-g2-s101-v1, recipe801428c34c56668eb389ab37962e9df6069a265c3ee1151ebda5883afbe6f474; managed register/submit succeeded, simulation running PID203935. Native requested noise values and unchanged effective MX/reltol1e-6/trap/maxstep10ps confirmed. Scoped finite metadata watcher PID204499 healthy; automatically managed-analyzes this run after completion, compares frozen baseline JSON, outputs spectrumSVG; no recurring automation. New wrapper preserves original reducer, source hashes/compile/minimal paired-deck diff and synthetic zero-comparison test pass. Other4static runs, circuit/PDK/OA/resource policy untouched; no cleanup/commit/push. Artifacts verification/sar8_noise and output/sar8_noise/fft_*.

2026-10-30T15:59:17.943047+08:00 — Read-only noise/static status: B noisyFFT474 total/466effective, running~19.97h, observer invalid0; watcher healthy. A/B static1..131 complete/analyzed, collected4 newly completed68..99/100..131 segments (7 hashchecked files each,<258kB, no raw). All131boundaries/native code checks pass each,132center codes correct, cross-segment monotonic. A/B 13 bracket differences; max midpoint difference 0.007812500053350706 LSB. Current132..163/164..195 running;196..255 pending; originalwarnings preserved. No simulation launches/restarts/cleanup/policy/OA/automation/commit/push changes. Evidence output/sar8_noise/current_all_status.json and static_collected_comparison.json.


2026-10-31 — B1024 noisyFFT collected: simulation exit0 in148183.08s (41.16h), managed analysis exit0 in301s.9 hashchecked small files495975bytes, no raw.1032 native/observer codes match, all-frame protocol valid. SNDR48.57407865dB/SFDR63.62885045dBc/ENOB7.77642503; versus no-noise delta -0.21399872dB/-1.13894120dB/-0.03554796bit.53/1024 codes change by1LSB, not wrongcode verdict. Maxconversion29.477963ns vs29.435806; close edge maxdelta0.164516ps. Core+ref86.521735uW gridestimate. NumPy independent FFT agrees within1e-8dB. Retain CMI2751..2755, numerical warnings and SPECTRE555 (1.87MB swap observed, performance warning). Single-seed/bandwidth and low-frequency limits remain. Spectrum plotted at verification/sar8_noise/fft_final/spectrum_comparison.png. No simulations/circuit/OA/automation/policy changes, cleanup, commit/push.
`n2026-10-31 — Generated requested noisy B ADCtoolbox12panel from native-crosschecked1024 codes. Used project .venv ADCtoolbox0.9.1 after workspace venv import failed (no installation/change). Isolated renderer adapter corrects noise footer/limits, preserves original report. Toolbox SNDR/SFDR agree with managed within1e-8dB; Parseval/decomposition checks pass. PNG visually inspected; artifacts verification/sar8_noise/fft_final/b_noise_toolbox_panel.png/json. No simulation/circuit/OA/Obsidian/commit/push changes.

2026-11-01 — Fullstatic recovery: all18 A/B simulations complete. Original coordinator failed on string equality of maxstep logs (actual10ps identical; displayed defaults35.59/325.59/285.59ns vary with duration). Preserved failure JSON; ran only existing A196..227/228..255 managed analyses, both complete exit0, collected8 remaining small segment sets with hash checks/no skips. Local semantic aggregate preserves raw settings, validates all other settings identical, all255 ordered brackets and256 center codes/native checks perversion. A DNL +/-0.03125LSB, endpoint INL0.03666759LSB; B +/-0.0390625LSB, INL0.04448755LSB. Offset both0.85144043mV; endpoint gain -0.0953494%; bracket resolution1/128LSB.22/255 A/B boundaries differ by atmost1/128LSB. TT deterministic only, electrical deferred. Evidence verification/sar8_campaign/ab_static/fullstatic_recovered.json and recover_summary.py. No new simulation/coordinator restart/circuit/OA/automation/commit/push.

2026-11-01 — Plotted frozen A/B TT transition-based DNL/endpoint INL with installed ADCtoolbox native plot_dnl_inl (not histogram estimation). Independently recalculated arrays match recovered summary within1e-12;255 boundaries/254 interior widths. Full +/-1LSB and zoom +/-0.06LSB PNG/SVG saved under verification/sar8_campaign/ab_static/static_dnl_inl_*. Zoom visually inspected, labels and limits clear. Nominal DNL vs endpoint INL normalization and1/128LSB search brackets explicitly labeled. No simulation/circuit/OA/Obsidian/commit/push changes.

2026-11-01 — 按用户要求更新PVT验收-频谱笔记：加入A/B转换边界扫描法DNL/端点INL图、指标和结论，以及B含噪声FFT对比图/表与12图链接。注明非ramp直方图、1/128LSB搜索分辨率、TT无失配/PEX、单seed与端压限制；保留原PVT内容。4图复制hash一致，全部笔记链接存在，scoped diff检查通过。无仿真/OA/commit/push。

2026-11-02 — Simulation diagnostics proposal: read-only server tool probes confirm Spectre21.1.0.509 and xrun21.09-s008; OCEAN/PSF paths found, Synopsys setup stale VCS path retained as finding. Reviewed4 complete+4 failed native logs,3 bounded remote raw/header/tail/logStatus sets; all3 remote/native local hashes match. Independent existing-checker and false-positive reviews consolidated into verification/simulation_diagnostics_review/proposal.md. Covers SOA, compile/license/numerical/runtime/data/protocol/code/settings categories, excludes spurs. Evidence distinguishes print suppression, exit0+fatal, effective/default settings, no-oracle unknown. No heavy analysis, simulations, source checker/PDK/OA changes or commit/push. Proposal only, implementation/tests pending.
2026-11-03 — User-authorized live Spectre inspector campaign. Scoped plan plan/2026-11-03-simcheck-live/plan.md;16 immutable managed IDs simcheck-live-*-20261103-v1,14 executed/collected, syntax and wall-nooutput CPU-queued.14 original small receipts217472bytes plus RC raw54470bytes hashchecked; no ADC raw download. A/B TT3frames MX4thread use original frozen DUT/TB/library/observer hashes, only stop359ns; codes231/44/183 valid1, B CMI retained. Synthetic native faults cover model/include/parameter/VA/topology/DC/minstep/output; initial wall probe hit output cap first, retained honestly. Only rc-normal used user-approved1thread CPU exception; original remote policy bytes/hash restored before resuming the other queued worker. No other process/OA/PDK/history/source-policy edits, no commit/push. E:/spectre-log-inspector fixes5 observed extraction/completeness defects,85 tests pass; new report docs/live-spectre-validation.md there. Pending queues/checkpoints retained; no automatic resubmit or recurring automation.


2026-11-03 — B local-mismatch pilot: froze original B DUT and32 initial managed recipes, submitted nominal+3101/3102/3103 only. Actual Spectre MC reports0process/19mismatch parameter types/12315RVs; raw parameter scalars generated, full activation validation pending. Native MOM model has multi-aware sigma normalization; no capacitor expansion/circuit change. User narrowed scope to CDAC/comparator, then explicitly requested stopping two: verified current identities and SIGTERM3102/3103 only, both children exited; raw/worker failure retained plus user_stop receipts. Nominal completed363.49s,3101 continues; remaining27 andrepeat unsubmitted, no simulation coordinator deployed. Pinned inspector164dbe6 sample scan verified and isolated serverPython3.11 collector live; status/wait cursor/show/evidence saved. Corrected analysis adapter prepared as bound analysis-onlyv2 after observing actual MC scalar/family locations; nominal analysis submitted. Module plan verification/sar8_mc/block_plan.md targets current B core, notN4/rx2. No OA/PDK/baseline/otherprocess/commit/push changes.

MC nominal analysis submitted as analysis-onlyv2 but queued by actual active_swapping/cpu_load admission; no gate bypass. Retained whole-chip nominal+3101 only. Remaining module work is planning, not new simulation submission. Syntax, stop-receipt identities, unchanged B source hash and scoped whitespace checks passed.

2026-11-04T00:01:35.616181+08:00 — Two retained B simulations native-complete: nominal363.49s/seed3101 692.80s,10frames each. Nominal analysisv2 missing optional4Bootstrap charge nodes failure retained; bound v3 uses existing optional-signal recovery and MC scalar paths, both analysis exit0/~40s, small outputs hash-collected. Native/observer codes and protocol pass;3101 differs from nominal in7frames by−1LSB, source/offset attribution unresolved;18CDAC/2input-pair random records saved. Inspector manifest had omitted actual analysis name; added tran_ab+exactraw+stop, reloaded only identified collector, same pinned164dbe6 and DB; both now complete. No simulation rerun/newseed or circuit/PDK/OA/automation/commit/push changes. Module work remains planned.

2026-11-04 — B module local-mismatch30each completed and delivered in verification/sar8_mc/blocks. Finalv2 all64managed simulations/analyses complete,64hashchecked small collections, no raw. CDACv1 ideal-driven instance merging invalidated/archived; corrected preserve_inst=all gives18independent nativeMOM rows and distinctP/N caps, originalB hash unchanged. Independent NumPyweight/DACmetric and comparatorsearch recomputation pass; same-seed controls reproduce. CDAC worstlinearizedDAC DNL0.11426215/endpointINL0.06131120LSB,30monotonic; not fullADCstatic. Comparator offsetmean-3.8875mV/SD12.6206078mV/range-23.9375..25.3125mV,30valid;300tested speedprobes resolve correctly,receiverdelay0.218029..0.376334ns underdiagnosticclock/stiffinput. Seed4101 DCtolerance and4124 LTEwarning retained/flagged; setupwarnings retained, no electrical/yield/kickback/fullasync claim. Pinned164dbe6status/wait/show/evidence+cursor saved,64complete/livecollector. Two finalPNG/SVGplots visually inspected, report/CSV/JSON/validation/QA saved; scopedsyntax/whitespace checks. No newdesign/wholechip30/OA/PDK/otherprocess/baseline/commit/push/deletion. Only scopedcdac-30followup will pause afterdelivery; oldsar8/r4 unchanged.

2026-11-04 — Delivery follow-up cdac-30 paused through automation_update and source configuration read back PAUSED; local receipt updated. Other automations unchanged.

2026-11-04 — Completed B comparator physical-input retained-sample validation and first legal width candidate. Original91native mismatch rows preserved across nominal/4121/4124 physical Bootstrap+MOM/CDAC/receiver fixture with original50ohm/4pF interface and recorded100ns clock/eightpulse burst. Physical thresholds-23.926955/+25.301739mV overlap stiff controls; nominal guarded +/-62.5uV after exact-zero noiseless unresolved search retained. Input-pair-only nominalization keeps89other rows fixed ->-7.683987/+4.685660mV, identifies major input contribution. W4refused CMI2440modelWmax2.7001um (3failures retained); W2changes only two input geometry rows with derived diffusion, all91latent values fixed ->-20.178584/+20.178959mV,15.67/20.25% selected amplitude improvement. Tested speedmax0.366833->0.280478ns; three selected native windows including resetkick0.143624->0.243339mV. Nominalreltol1e-7 same bracket/delaydelta<0.102ps, LTE/16881retained; CMI2732here is1e18->1e12Ohm diagnostic clampcut,40nVconservative driftbound. SSHinterruption recovered exact registrations; inherited coordinator hardlimit caused3analysis-start failures, preserved and source-bound reanalyzed without simulation rerun.19native simulations16complete/3modelrefused,16small resultsets hash-collected. Independent search/geometry/sourcehash checks and plotreview pass. Pinned164dbe6 status/wait/show/evidence final16complete/3failed/livecollector; MC childname metadata correction retained. Report verification/sar8_mc/physical_input/README.md, summary/CSV/figures/QA. W2not adopted; no new30seed/PVT/fullSAR/power/yield/reliability claim. FrozenB unchanged, no OA/PDK/Obsidian/otherprocess/automation/cleanup/commit/push changes.

2026-11-04 — Four paired native runs completed, with valid held thresholds and exact 87-row mapping. NMOS/PMOS signed influences (baseline minus disabled) in mV: seed4121 -4.873/-2.624, seed4124 +2.124/+2.499. No common dominant branch across these samples. See verification/sar8_mc/physical_input/regen.md.

2026-11-04 — Completed 30 paired seeds (4101–4130), 84 new managed runs plus 6 reused. All threshold brackets valid and row checks matched. Sample SD in mV: input nominal 5.027, additionally N nominal 1.714, additionally P nominal 4.005. Paired SD gap 2.291 mV, bootstrap95 [1.144,3.378], leave-one-out [1.733,2.413]. Prioritize MNLATN/P for remaining mismatch under this TT fixture. A read-only fetch interruption was recovered; original simulations retained. Report verification/sar8_mc/regen30/README.md. No design adoption, OA edits, commit or push.

2026-11-04 — B timing MC plan revised in plan/2026-11-04-sar8-timing-mc/plan.md. Reuse prior five-point evidence; retain stages 2/3/4. Planning only; no simulation submitted.

2026-11-04 — B timing MC is running. 340 TT module extensions and 100 cold identities registered. Live collectors pinned at 164dbe6. Increased managed concurrency target from four to seven, at four Spectre threads per case. All four normal pilots reached native completion and ten frames of 8/8/8/16, with minimum receiver-to-write margin 273.08 ps (SS cold) / 183.64 ps (FF cold). Original scope classifier flagged the selected subcircuit roots as outsiders. Exact root/descendant review retains the initial failed measurement receipt and consumes the completed sources. Same-seed longer quiet-dwell references for 5101 pass 80/80 bits at both corners, worst top-node changes 0.0355/0.0746 LSB; 5102 references in progress. Retain CMI warnings and code deviations. Dispatch subsequently requires valid pilot references. Summary receipts in verification/sar8_mc/timing_mc/checkpoint.json and module_results.json. No design adoption, OA edits, commit/push or other automation change.

2026-11-04 — All four SS/FF pilot same-word reviews passed (largest SS 0.03549, FF 0.07463 LSB). Independent controller wrote pilot_pass and entered cold_samples. Inspector saw four new running cold cases; TT small-result recovery at 186/200 valid comparator thresholds and 186/200 CDAC samples. Scoped cdac-30 thread follow-up now tracks this campaign every 15 min.

2026-11-04 — Replaced stale project entry with current frozen B design/TB/results navigation. scripts/sar8_entry.py projects 49 verbatim subcircuits into design/sar8_b (46 reachable, 3 retained helpers, 3 external standard-cell masters), locks seven real managed test cases, and exports exact reproduction bundles under output/sar8_b. All source and recipe-input SHA checks, five navigation-page link checks, syntax and scoped whitespace checks passed. No new Spectre run for the split view; native qualification remains bound to original frozen B. Historical experiment physical consolidation remains outside this entry cleanup. No commit/push.

2026-11-04 — User authorized commit, push and main merge using exp/cdac-flat8-device. origin/main is an ancestor, enabling fast-forward. Snapshot includes current project sources, input packages, results and navigation dependencies, with three native binary caches excluded. New-text scan found no PDK/standard-cell model definitions or private keys. Publication validation and remote-ref readback follow in plan/2026-11-04-sar8-publish/plan.md.

2026-11-04 — Publication preflight passed from independent staged checkout. Frozen B SHA256 f31b66c8… survives Git extraction; all 49 subcircuits, seven complete input exports and current entry links validated. 20 managed unit tests pass. Added byte-preserving Git attributes for hash-bound scientific input/receipt directories. Current branch is ready for one snapshot commit and atomic fast-forward push to branch/main under user authorization.
