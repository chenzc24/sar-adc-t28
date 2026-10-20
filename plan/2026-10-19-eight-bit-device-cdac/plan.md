# Eight-bit flat PDK CDAC and reference-switch implementation

## Goal, scope and assumptions

User authorizes the complete proposed device-level flow, not only an initial
plan or capacitor checkpoint. Select a legal T28 MOM unit from measured
capacitance/matching/load tradeoffs; build literal independent unit arrays;
replace reference relays with native MOS; size them; integrate the existing
native bootstrap and comparator and verify static/dynamic/timing/PVT/mismatch
in proportion to evidence. Keep eight-bit/10-MS/s, 0.9-V/VCM=0.45-V, +/-0.9-V
differential range, 200-MHz bit clock. Existing electrical macro and all older
OA/source/evidence remain read-only baselines. Reference buffer and SAR
digital logic are not reimplemented: use finite-R reference sources and
explicitly labeled ideal/VA controls, with native gate-drive checks.

Inspect layout/signoff prerequisites after electrical selection. If legal
technology/rule-deck/runset or licensed extraction tools are unavailable, do
not guess a signoff setup or call schematic results layout-qualified. Record
the exact missing surface and preserve electrical results. A placement-only
layout is not a substitute for DRC/LVS/PEX.

## Initial state / ownership

Clean `exp/top-plate-gmain-t28`, HEAD 4ced90a, six commits ahead of remote.
Use a new local feature branch for this multi-stage circuit target. No push.

Owned local: this plan, plan/log.md; new config/cdac_flat_8b_device.yaml,
scripts/cdac8_device/, verification/cdac8_device/, netlist/cdac8_device/,
models/veriloga/cdac8_device_sequence.va and optionally a dedicated phase-
safe eight-bit controller; docs/cdac_flat_8b_device.md, README.md,
docs/architecture.md, docs/design_log.md, docs/sampling_architecture_status.md,
virtuoso/cell_manifest.yaml; curated generated figures in
docs/figures/cdac8_device/. Ignored generated evidence output/cdac8_device/.
Own .gitattributes only for these two new VA files: pin LF so Windows Git
checkout does not alter tested source hashes; preserve the controller's exact
tested terminal blank line with a file-scoped blank-at-EOF exception. No
global Git setting or historical-file whitespace policy is changed.
Active spec resolution/noise/targets are unchanged. Existing scripts/models,
config/eight_bit_flat.yaml and historical docs/cells are read-only.

Owned new remote objects, only SAR_ADC_T28:
- `cdac8_unit_candidate_{a,b,c}` schematic/symbol; PDK-unit candidates.
- `tb_cdac8_unit_char` schematic; nominal AC/bias/mismatch characterization.
- `cdac8_unit` schematic/symbol (layout only after explicit prerequisite audit).
- `cdac8_bank_{1,2,4,8,16,32,64,128}` schematic/symbol; independent unit instances.
- `cdac8_caps_ideal_switch` schematic/symbol; PDK caps, ideal relays control.
- `cdac8_ref_switch` schematic/symbol; native rail switches/VCM TG and drive.
- `cdac8_ref_switch_b{0,1,2,3,4,5,6,7}` schematic/symbol: same native topology,
  bit-load-specific legal geometries, including two actual gate inverters.
- `cdac8_device` schematic/symbol; PDK arrays/reference switches.
- `cdac8_device_sequence` symbol/veriloga; test-only sequence stimulus.
- `cdac8_controller` symbol/veriloga if needed for phase-safe closed-loop control.
- `tb_cdac8_switch_char`, `tb_cdac8_caps`, `tb_cdac8_device`,
  `tb_cdac8_sampling`, `tb_cdac8_sar` schematics.
- `cdac8_device_nominal` schematic/symbol and
  `tb_cdac8_nominal`, `tb_cdac8_nominal_sar` schematics: same PDK geometry/MOS
  switches with parallel MOM `m` aggregation for deterministic large sweeps.
  Require correlation to the literal 512-unit hierarchy before relying on
  performance. Never use this nominal aggregation for mismatch/physical unit
  counting. Each run remains an exact export of its corresponding OA fixture.
- `tb_cdac8_safephase` schematic: same native nominal CDAC/bootstrap and
  comparator macro; post-conversion bootstrap re-acquisition precedes
  reference release/VCM restoration, with an independent cycle marker.
  Tests reference reset while TOP is driven instead of left floating.
- `cdac8_ref18_b{0..7}`, `tb_cdac8_ref18_char`,
  `cdac8_device_ref18`, `cdac8_nominal_ref18`, `tb_cdac8_ref18`,
  `tb_cdac8_ref18_literal`: same three-path reference topology with 1.8-V-rated
  native pass devices and existing 0.9-V native gate inverter topology.
  Characterize VCM headroom at SS/low supply/cold before array promotion.
- `tb_cdac8_ideal_input` schematic: same literal native CDAC/reference
  switches, replacing only input Bootstrap with the stated 150-ohm ideal
  relay, to isolate the observed SS/low-V/cold large-step acquisition failure.
- layout views of the selected unit/array only when verified tool/rule context
  allows safe implementation; add exact layout ownership before editing.

Read-only remote dependencies: tsmcN28 and all other shared libraries;
SAR_ADC_T28/tb_cap_char, sar_cdac_flat_8b, sar_comparator_macro_8b,
sar_macro_controller_8b, sar_bootstrap_canvas_flat_8b, sar_strongarm_t28,
all existing testbenches. Preserve unsaved/user-owned windows and locks.

## Steps and gates

Controller source is concretely `models/veriloga/cdac8_controller.va`; its
open_loop parameter also supplies the dedicated all-code DAC sequence, so no
second unused sequence model is created. No baseline VA file is modified.

1. Read relevant bridge/VA/simulator skills and API contracts. Preflight
   status/windows/library/PDK CDF and snapshot dependency readbacks. No guessed
   model sections, PCell geometry, mismatch activation or signoff decks.
2. Scan three legal MOM geometries near the prior load comparison; evaluate
   C-vs-bias/frequency and actual model statistics. Verify independent local
   variation with a smoke run before any 100-200-sample engineering screen.
   Select matching/linearity vs total load, not nominal kT/C alone.
3. Build 256 identical units per side (255 active+dummy), no single giant
   geometry or ambiguous multiplier pretending independent mismatch. Preserve
   ideal-switch electrical A/B version; verify weighted transfer all 256 codes.
4. Reference switch candidates: PMOS high rail, NMOS low rail, TG at VCM;
   explicit body ties and terminal stress, realistic state transitions. Size
   MSB then taper lower groups using actual per-bit transient error, not a
   universal hard Ron=150-ohm rule. Assess finite reference R/C, gate drive,
   nonoverlap, leakage, charge injection/feedthrough and supply current.
5. Exact-OA simulations: capacitor-only A/B, full device CDAC, native bootstrap
   sampling, real StrongARM interface/closed loop where feasible. Sample/hold
   reference handoff is phase-separated to prevent contention. Require
   decision-time settling <=0.25 LSB=1.7578125mV, conversion<60ns,
   static no missing codes |DNL/INL|<=1LSB; use 0.5LSB CDAC-static as an internal
   engineering margin, not an undisclosed system target change.
6. Verify nominal full-code static and coherent sine; target >=7 ENOB at
   system test level. Sensitivity/SS/TT/FF/supply-temperature endpoints and
   mismatch screens have actual model/log provenance; finite MC is not yield
   signoff. Reference R/C and VA logic remain labeled abstractions.
7. Read back final OA, zero markers, native device/count/connectivity audit,
   fresh-export equality to simulated hierarchy, unchanged dependencies.
   Inspect figures, focused tests/compile/YAML/diff checks. Record measured
   limitations, open failing conditions and exact layout/noise/PVT coverage.

All transient primary DUTs must come from saved OA. Experimental quick decks
may reuse literal exported device statements for isolated sizing/character-
ization only, explicitly labeled diagnostics and followed by OA back-annotation
and final exact-export verification. Never patch the final DUT netlist to hide
schematic errors. No proprietary models/raw OA/secrets committed.

## Artifacts / commit policy

Per-run hashes, result.ok/logs/PSF, model sections/version/PVT, CDF/geometry
readbacks and MC statistical activation evidence under output/cdac8_device/.
Durable report config/circuit source/tests and concise metrics tracked. Scoped
local commit(s) per evidence-backed stage; no push. Experience docs only on
human request.

Status: first candidate and isolation experiments implemented; nominal static,
local-capacitor MC, DC/PVT/phase verification and final OA audit completed.
The coherent APS dynamic run completed (48.7595 dB SNDR, 7.8072-bit ENOB,
64.9367 dB SFDR), with recorded stress warnings. Acceptance remains open:
reference-reset stress, SS/low-V/cold first full-swing acquisition and the
explicitly unimplemented/noise/layout gates are not waived. The reserved
ref18 family stopped at b7/characterization; no ref18 array was created or
promoted after its cold headroom failure.

Handoff connection boundary: a later library-read recheck found the CIW
endpoint refused connection. No further OA mutations were attempted. Earlier
successful audit is retained; a new live readback requires restoring bridge.
