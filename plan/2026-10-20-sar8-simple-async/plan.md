# Sample-initialized, minimal asynchronous SAR controller

## Goal

Implement the user-approved 8-bit asynchronous timing: one SAMPLE input,
local comparator/write/update phases, a one-hot bit chain, eight SAR slices,
and separate P/N bottom-plate driver banks. No independent reset/start/hold,
permission, reset-acknowledgement, deadline/fault/status, or EOC interface.
Preserve the earlier controller as a comparison, not the active implementation.

## Dirty-State Note

Initial branch: `exp/cdac-flat8-device`. Untracked `config/cdac10_dualrail.yaml`,
`models/veriloga/cdac10_dualrail_{comparator,controller,input}.va`,
`plan/2026-10-20-cdac10-dualrail/`, `scripts/cdac10_dualrail/`, and
`verification/cdac10_dualrail/` are unrelated concurrent work and remain untouched.
Existing Virtuoso windows include old sar8a cells and CDAC testbenches: do not
close, save, rebuild, or alter those objects.

## Local Owned Files

- This plan; one factual appended entry in `plan/log.md` and `docs/design_log.md`.
- `scripts/sar8_simple/`, `models/behavioral/sar_async_simple.py`.
- `config/sar8_simple.yaml`, `verification/sar8_simple/`.
- Update only the active controller-contract pointer in `config/design_spec.yaml`,
  add a short README link and a supersession note in `docs/sar8_async_implementation.md`.
- Update the controller row/new-fixture links in `docs/project_status.md`;
  retain its earlier library inventory as a time-pinned snapshot.
- `docs/sar8_simple_async.md`, `docs/figures/sar8_simple/`.
- Ignored generated results in `output/sar8_simple/`.

## Remote OA Owned Objects

Only library `SAR_ADC_T28`, new schematic/symbol cells:
`sar8s_inv`, `sar8s_nand2`, `sar8s_and2`, `sar8s_buf`, `sar8s_or2`,
`sar8s_xor2`, `sar8s_mux2`, `sar8s_sr`, `sar8s_dffr`, `sar8s_clkbuf`,
`sar8s_delay_quiet`, `sar8s_delay_valid`, `sar8s_delay_write`,
`sar8s_delay_bbm`, `sar8s_timing`, `sar8s_bitseq8`, `sar8s_bit`,
`sar8s_bp_slice`, `sar8s_bp_p8`, `sar8s_bp_n8`,
`sar_logic_8b_async_simple`, `tb_sar8s_logic`, `tb_sar8s_strongarm`.
Check absent/unowned conflicts before creation. Later repairs require this
target's ownership receipt, saved readback, and no GUI-open target.

## Read-Only State

All old `sar8a_*`, `sar_logic_8b_async`, `sar_strongarm_t28`, existing
`sar8a_plant/veriloga`, all unrelated CDAC/OA work, PDK/library contents,
and old generated exports/results. No hand edits to OA databases.

## Shared Dependencies And Assumptions

- Bridge 0.8.0 workspace venv, profile `t28_io`, CIW in
  `/home/chenzc_intern25/TSMC28/llm_IO`; library path
  `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`, technology `tsmcN28`.
- Active 8-bit/10 MS/s/0.9 V flat binary SAR spec, differential span 1.8 V.
- One complete initial SAMPLE-high phase is mandatory. DOUT is the working
  register, changes during conversion, and is cleared by next acquisition.
  Read at a fixed late-frame window; no retained previous-frame output bank.
- Native MOS leaves initially inherit the previous measured static CMOS/TG-DFF
  topology, but are independent newly named cells. R/C delay seeds are explicit
  schematic ideal passives, not PDK/layout/tolerance-qualified delay circuits.
- Completion detection remains local to timing; one clock latch, no serial
  stage-handshake FSM. Write precedes delayed update/reset. Quiet interval covers
  propagation/BBM/DAC settling plus comparator reset, without reset acknowledgement.
- Conventional trial-one binary control: CODE = stored bit OR current token.
  P/N reference choices are complementary only in steady conversion; both off
  during acquisition/BBM. This is a controller interface, not integration with
  the separately evolving physical dual-rail CDAC or sampling network.
- Reuse the read-only behavioral plant for ideal sampled DAC/comparator closure;
  native StrongARM is a separate bounded interface check, not full-ADC validation.

## Expected Work

1. Write timing contract, native hierarchy and deterministic event model.
2. Verify all 256 words locally, variable comparator delay, stop-after-eight,
   and sample interruption/restart; distinguish abstraction from transistor proof.
3. Preflight status/windows/library/targets; create and read back new OA cells.
4. Export unchanged OA hierarchy, run bounded Spectre APS representative codes,
   two alternating input frames, fast/slow supply-temperature screens, and a
   representative unchanged StrongARM case if interface permits.
5. Audit clock/write/update counts, one-hot progression, code, nonoverlap,
   data-before-reset, settle/reset intervals, extra edges, frame recovery,
   waveform excursions, device stress warnings, and result.ok.
6. Produce concise two-cycle/main-bit plots and factual report; commit owned
   changes only. Do not run hours-long full-256 native regression or push.

## Validation And Pass Criteria

- Local compile/targeted deterministic model: exact 8 comparisons/writes/updates
  for complete frames; all 256 decisions reproduced; tail token zero; no ninth
  launch. Interrupted/stuck frames need not publish an error flag, but must
  terminate at new SAMPLE and restart correctly without stale writes.
- OA readback matches source instance/master/pin/parameter connectivity and
  symbol terminals, zero schematic markers. Library technology/path verified.
- Native nominal two-frame case: 145 then 85 for held differential inputs
  +0.123 V then -0.300 V; stable final word through fixed read window 95..99 ns
  relative to each frame. Exactly 8 local events and no extra conversion edges.
- Native P/N references are mutually exclusive per bottom plate; stable at
  comparison/write. Measured write-to-reset/update margins positive. Quiet
  interval, pulse widths and PVT behavior are reported, not assumed from seeds.
- PVT screens: tt/0.9 V/27 C, ss/0.81 V/125 C, ff/0.99 V/-40 C. Nominal timing
  failures must be fixed; stress or nonnominal failures remain explicit open gates
  if not repairable within this bounded architecture target.
- Execution success requires result.ok AND finite requested vectors. Device
  SOA warnings separately preclude physical qualification even when code passes.
- `git diff --check`, final owned diff review/status; no claim of noise,
  ENOB, power, layout, mismatch, or full physical ADC qualification.

## Expected Artifacts

Owned source manifest, immutable export/deck/result identities and hashes,
curated numerical summary, waveform figures, OA readbacks and report under
the local owned paths; raw PSF remains ignored under output.

## Commit And Push Intent

Commit: `feat: simplify SAR8 asynchronous timing and verify native hierarchy`.
Push: not requested.

## Progress

- Preflight CLI: t28_io CIW/tunnel/Spectre healthy, bridge 0.8.0. Existing old
  SAR and CDAC windows deliberately preserved. Implementation not yet built.
- First exported native implementation: two-frame word145/85, eight events
  each, no bottom overlap; representative unchanged StrongARM word145 passes.
  The 202-ns observation retains PHI_W=-0.105802 V at201.08764 ns and CMI
  stress warnings. Before final regression, add a local stronger final-stage clock
  buffer only to PHI_W, preserving the write-before-update topology; compare
  immutable v1/v2 exports/runs. This is a drive repair, not a new control state.
- Clock-buffer CDF readback rejected requested PMOS Wfg=4um: the PDK callback
  clamps it to3um. Adopt explicit accepted sizing NMOS2um/PMOS3um (4x/3x the
  baseline inverter), and require fresh complete readback before simulation.
- Concurrent untracked `docs/cdac8_pn_ratio.md`, `docs/figures/cdac8_pn_ratio/`,
  `plan/2026-10-20-cdac8-pn-ratio/`, and the two pn_ratio scripts appeared
  during work; unrelated and preserved.
- Functional exported-netlist checker initially omitted a line-wrapped XTIM
  instance (single-space regex) and lacked a clock-buffer primitive. Fixed the
  parser, added exact per-block instance-set checks and explicit buffer
  abstraction. Fresh v2 check passes256 words/eight stuck recovery positions;
  do not reinterpret this as native256-code Spectre coverage.
- Final v2:21 native cell types,16 DFF and1 clock SR,1476 MOS. All23 owned
  schematic cells (21 hierarchy plus2 benches), plus21 symbols, fully read back without check markers.
  Controller bodies identical across benches; StrongARM body identical to the
  legacy export. Post-run remote plant hash equals local source hash.
- Final13 bounded APS runs complete with result.ok and finite70 requested
  signals. Every complete frame has8 compares/writes/updates, correct code,
  unique write token, no bottom reference overlap at0.5VDD, and no bottom change
  during comparison through100ps after write. Acquisitions initialize work/
  pointer and inhibit new clock edges; interruption and stuck recovery pass.
- TT word145 last write71.2503ns, second word85 at171.2695ns. Write/update
  separation~460ps; write/reset~544ps; comparator-low interval~2.755ns. Quiet
  interval is a measured control margin, not a physical CDAC settling proof.
  Position transitions briefly overlap (~7ps nominal), retained in figures;
  all write-time positions are unique and ordered, not claimed globally
  glitch-free one-hot outputs.
- V2 nominal PHI_W minimum-41.105694mV vs v1-105.801697mV;10ps maxstep
  control gives-41.105690mV. No nominal printed/suppressed CMI. SS representative
  last write74.0778ns; unchanged StrongARM case70.3087ns. FF.99V function passes
  but30 printed CMI and13,031,246 suppressed remain a failed device safety gate.
- Completion status: bounded implementation/verification delivered, NOT full
  physical ADC qualification. Old evidence preserved; no256-code native sweep,
  no transient noise/MC/power/layout claim and no push. Final source/doc checks,
  visual review and local scoped commit are recorded in maintenance log.
- Four generated figures visually inspected. Opened only the new bit/timing/
  top windows, preserving all pre-existing user windows; zoom uses IC618
  SKILL-Finder-verified hiZoomIn, not the unavailable troubleshooting hiZoom
  alias. No connectivity or netlist change from presentation actions.
