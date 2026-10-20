# Native eight-bit SAR logic and Canvas review

## Goal and starting state

Implement the active eight-bit SAR register/sequencer in SAR_ADC_T28,
verify its expected phase contract, and reproduce the implemented hierarchy
and timing in the user's connected Analog Canvas for review.

Start: exp/cdac-flat8-device. Existing untracked config/strongarm8_baseline.yaml,
scripts/strongarm8/, verification/strongarm8/, docs/figures/strongarm8/ and
plan/2026-10-20-strongarm8-baseline/ belong to comparator characterization.
They are read-only and will not be staged by this target. The active design
is eight-bit flat CDAC; historical ten-bit split controllers are references.

## Ownership

Local: this plan; config/sar8_logic_timing.yaml; docs/sar8_logic.md;
netlist/dut/sar_logic_8b_canvas.cir (ideal Canvas gate export, no PDK);
scripts/sar8_logic/; verification/sar8_logic/; docs/figures/sar8_logic/;
bounded append to plan/log.md and docs/design_log.md and a bounded
sar8-specific addition to virtuoso/cell_manifest.yaml after OA validation.
Generated data: output/sar8_logic/ (ignored).

Remote OA intended new cells, schematic and symbol in SAR_ADC_T28:
sar8_inv, sar8_nand2, sar8_nor2, sar8_mux2, sar8_tglatch,
sar8_dffrn, sar8_sr, sar8_delay, sar8_bbm,
sar8_bit, sar_logic_8b and tb_sar_logic_8b.
All names must be checked absent before creation. Add any required helper
explicitly here before creation. No existing controller, CDAC, Bootstrap,
StrongARM, PDK, shared library or unsaved cellview may be changed.

Canvas: connected project project-d469b166-a782-4714-81de-7ae661fe2f45,
initial empty document-main. Keep the Editor open. Create review drawings
after the corresponding Virtuoso implementation exists and has readback.
Use only supported MCP operations. Manifest and loaded adapter both 0.17.75;
the advertised unsupported set_document_grid operation is not needed.
No claim or session credential is stored in project sources.

## Dependencies and implementation decision

Retain the native CDAC testbench's separate externally supplied phases:
CLK_SAMPLE/PHI, PREPARE, HOLD_START, CLK_TRIAL, CLK_COMPARE, CLK_LATCH.
The 200-MHz phase generator/clock tree is a separate block. The logic target
implements memory, sequencing, decode, non-overlap and comparator clock
gating using native T28 MOS; a VA behavioral controller is not the result.
Expose an explicit RST_N for deterministic startup and interrupted cycles.

Expected frame: sample 1--41 ns, VCM release 42 ns, HOLD_START 43 ns,
MSB compare 46 ns, latch 47.5 ns; subsequent trial/compare/latch shift by
5 ns; LSB latch 82.5 ns; PREPARE 90 ns, VCM reconnect about 90.22 ns;
next sample starts 101 ns. Pulses are source commands; physical threshold
crossings and gate delays must be measured rather than assumed identical.

## Steps and validation

1. Read active spec, latest native CDAC and comparator interfaces. Record
   expected timing and native logic architecture with stable output storage.
2. Require healthy t28_io bridge, CIW/window/library/technology/lock audit.
   Read existing dependencies through supported API; retain exact snapshots.
3. Create and characterize basic static CMOS gates, resettable master/slave
   registers and reference break-before-make path. Validate truth, reset and
   actual delay in exact OA-exported Spectre transients.
4. Build one-hot MSB-to-LSB sequencer, trial state, working bits, separate
   output bank, BUSY/VALID and safe comparator-clock gating. Simulate known
   comparator decision patterns, repeated conversions, output retention,
   acquisition abort and explicit reset. Verify eight decisions per frame,
   bit order, reference non-overlap and complete comparator evaluation pulse.
5. Read back every new cell and pin map; require zero check markers and
   result.ok from fresh native exports. Report native core/PVT/load scope
   honestly. Existing analog acquisition/stress issues are not repaired here.
6. Recreate implemented hierarchy/one-bit circuit and expected versus measured
   timing in Canvas, render and visually review, fit the final active drawing.
   Canvas's model/process defaults do not replace T28 Spectre evidence.
7. Record report, log and exact evidence; git diff --check and scoped commit
   `feat: implement native eight-bit SAR register logic`. No push requested.

## Current preflight

2026-10-20: Canvas MCP connected successfully to the exact user origin.
Virtuoso Bridge 0.8.0 t28_io: tunnel and Spectre available, daemon reports
NO RESPONSE and windows reports no windows. The user was asked to load the
profile's setup in the intended CIW. OA mutation and the subsequent Canvas
reproduction depend on a successful live-session preflight.

## User-directed scope change

2026-10-20: user reports a problem with Virtuoso and explicitly requests
designing the topology in Canvas now. Proceed with the conceptual eight-bit
logic hierarchy, one-bit memory circuit and expected timing in Canvas first.
Label these as a proposal, without native OA or measured timing claims.
Native Virtuoso implementation remains deferred until the live CIW works.
The approved Canvas-first review supersedes step 6's original ordering.

## Canvas milestone result

Completed the user-directed Canvas proposal in eight documents: SAR8_Review,
SAR8_TIMING, SAR8_TOP, SAR8_BIT, SAR8_TOKEN, SAR8_FLAGS, SAR8_CLK_GATE and
SAR8_BBM. The top instantiates eight bit slices, a token chain, reset-priority
HOLD/trial state, separate output registers, comparator-ready/fault handling,
low-level-latched clock gates and a BBM path for each bit plus dummy.

All six electrical documents have zero structural errors in fresh MCP verify.
Warnings include open formal-port display stubs and label/wire clearance;
these are not represented as a clean ERC or physical timing acceptance.
Exported actual Canvas SPICE topology has 27 ideal registers and 187 ideal
combinational gates when flattened. The independent Boolean interpreter
passes all 256 decision words, eight fault positions, reset dominance,
output retention and full final comparison pulse logic. It intentionally
does not prove analog td, pulse-width margin, metastability, BBM interval,
power or PVT. The abstract buffer td=100p is an RC parameter, not a verified
100-ps dead time. Main review and timing exports were visually inspected.

No remote OA cells were created or changed. CIW repair and native T28
implementation remain deferred by the user. This milestone is committed as
`feat: draft eight-bit SAR logic topology in Analog Canvas`; no push.
