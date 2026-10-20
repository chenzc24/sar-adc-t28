# Eight-bit SAR logic: phase and register contract

The active converter is eight-bit, 10 MS/s, fully differential, flat CDAC.
This note records the expected logic design and the user-directed Canvas-first
proposal. Native SAR logic has not yet been created or measured: the t28_io
live CIW daemon was unavailable during the initial 2026-10-20 preflight,
and the user requested the Canvas topology while resolving that issue.

## Existing testbench timing

Source of the expected phases: models/veriloga/cdac8_controller.va and
scripts/cdac8_device/oa.py::bench. Time is relative to each 100-ns frame.

| Command time (ns) | Event | Required control behavior |
| ---: | --- | --- |
| 1 | Input Bootstrap sample turns on | Clear work/token/VALID; preserve last output word |
| 41 | Input sampling ends | Top node holds; references remain released |
| 42 | CDAC VCM switches release | Keep both reference enables off |
| 43 | HOLD_START | Assert BUSY; apply first MSB trial and dummy BASE after non-overlap |
| 46 | First comparator evaluation begins | CDAC has approximately 3 ns from hold command |
| 47.5 | Capture bit 7 | Keep or reject MSB; comparator result must already be valid |
| 48 | Trial bit 6 | Update trial only during comparator reset |
| 51 / 52.5 | Compare / capture bit 6 | Repeat at 5-ns spacing |
| 78 / 81 / 82.5 | Trial / compare / capture bit 0 | Atomically publish D7..D0; clear BUSY; assert VALID |
| 90 | PREPARE | Release reference enables; preserve D7..D0 and completed VALID |
| 90.22 | VCM switches reconnect | Existing analog-reset behavior remains separately unqualified |
| 101 | Next sample starts | Clear VALID and working state; retain last published output |

These are phase-source commands. Finite source rise/fall times and native
gate propagation shift actual threshold crossings. A successful logic result
must report measured times in addition to this expected schedule.

## Native implementation architecture

An eight-position one-hot token selects the bit to decide, MSB first. A
separate trial state raises only the current unresolved bit. Eight working
registers retain accepted comparator decisions; the instantaneous CDAC word
is WORK OR TRIAL. A second eight-register bank publishes a complete word
only on the final decision, including the just-decided LSB. Its outputs stay
stable during acquisition and the next conversion.

HOLD_START and PREPARE control reference ownership. For bit i:

```text
want1[i] = HOLD AND (WORK[i] OR TRIAL[i])
want0[i] = HOLD AND NOT (WORK[i] OR TRIAL[i])
```

Physical reference enables need immediate turn-off and delayed turn-on:
both must be low during a reference change. A native inverter-delay path and
logic combine each request with its delayed copy; actual dead time must be
measured under load and PVT. The existing VA's 100-ps timer is an expected
target, not a characterized gate-delay guarantee.

Comparator clock gating must preserve the whole evaluation pulse at the
last bit; clearing BUSY must not prematurely reset StrongARM while its
decision is being captured. Explicit active-low reset initializes the
storage and safely aborts a conversion. External phase generation is retained
for this block-level implementation; the complete phase generator and clock
distribution are separate circuit tasks.

## Canvas review and functional checks

Canvas project: `SAR8 Logic — Topology Review`, eight documents:

- `SAR8_Review`: explanatory architecture and review entry.
- `SAR8_TIMING`: expected phase commands, clearly labelled as not measured.
- `SAR8_TOP`: eight actual hierarchical bit-slice instances and common logic.
- `SAR8_BIT`: NAND data-selection muxes, working/output registers and trial decode.
- `SAR8_TOKEN`: eight resettable registers, with inverted first-token storage.
- `SAR8_FLAGS`: reset-priority HOLD/trial latches, DONE/VALID/FAULT registers.
- `SAR8_CLK_GATE`: NAND latch tracking enable only while raw clock is low.
- `SAR8_BBM`: immediate request AND its delayed copy, separately per reference.

The existing separated external phases remain inputs. `RST_N` is active-low
system reset; internal `SYS_RST` and `WORK_RST` are active-high. Acquisition
clears work, token, DONE/VALID/FAULT; only system reset clears the published
output. `PREPARE` releases references while retaining the previous result.

`READY = COMP_P XOR COMP_N` checks comparator output logic consistency.
`FAULT` captures an unresolved result at any decision. The final publication
enable is `T0 AND READY AND NOT FAULT`. Failed conversions stop after eight
decisions, keep the previous output word and do not assert VALID. This logic
check is not an analog metastability detector or a comparator noise guarantee.

All six electrical drawings reported zero structural errors on fresh MCP
verify. Open port-stub and label-clearance warnings remain; zero structural
errors is not a claim of clean ERC or simulation qualification.

The exported ideal library netlist is tracked at
`netlist/dut/sar_logic_8b_canvas.cir`. It contains no T28 models. Run:

```powershell
.venv/Scripts/python.exe scripts/sar8_logic/check_canvas.py
```

This interpreter reads the actual exported hierarchy, expands its 27 ideal
registers and 187 Boolean gates, and checks all 256 words, eight fault
positions, reset dominance, acquisition/output retention and final clock
gating. All pass. It ignores analog slew, propagation, setup/hold, pulse-width
and BBM duration. The displayed buffer `td=100p` is a library RC parameter;
its threshold delay is not automatically 100 ps.

Curated review figures: [architecture](figures/sar8_logic/review.svg) and
[expected timing](figures/sar8_logic/timing.svg). The complete Canvas export,
PNG inspection copies and Boolean summary are in ignored `output/sar8_logic/`.

## Review boundary

The current Canvas drawing is a topology proposal. Native implementation
evidence will follow Virtuoso readback and focused Spectre verification.
The existing PDK CDAC reset stress and cold-SS input acquisition failures
remain analog-block findings and are not evidence against logic correctness.
No full-transistor ADC SNDR, power, PVT or layout acceptance is implied by
this logic block's eventual timing tests.
