# Two complete sampling periods: measured asynchronous SAR timing

## Request and boundaries

User asks for a timing diagram of two full sampling periods and all key nodes,
following discussion of the cross-frame CAPTURE undershoot. Starting commit
efea0db on exp/cdac-flat8-device. Untracked cdac10_dualrail files/plan/scripts
are unrelated, preserved and excluded. No agents, push, circuit repair or OA
mutation. Remote OA ownership: none. All PDK, existing OA, exported DUTs,
behavioral plant and earlier simulation evidence are read-only.

Existing current-revision multi-frame APS runs inject a frame-1 fault/reset;
they are useful abnormal comparisons but cannot be presented as two normal
conversions. Run one bounded nominal APS observation transient for 202 ns,
using the unchanged saved recovery controller hierarchy and ideal ADC plant.
Only testbench VIN stimulus, save list and transient stop differ: input .123 V
first acquisition, -.3 V during second acquisition, expected output145 then85.
Save all controller handshake/state guards, token/work/trial/output banks,
reference selections, actual frame sources and comparator/DAC plant rails.
No complete physical ADC, new PVT or native 256-code sweep is implied.

The measured sampling edges near1.01/101.01/201.01 ns bound exactly two100-ns
periods. Show0..202 ns for initial system reset and right boundary context;
initial system reset overlaps only the beginning of the first acquisition.

## Ownership and workflow

Owned local paths: this plan; scripts/sar8_async/two_cycles.py;
docs/sar8_async_two_cycles.md; docs/figures/sar8_async_two_cycles/;
verification/sar8_async/two_cycle_summary.json; bounded link addition to
docs/sar8_async_implementation.md and a maintenance entry in plan/log.md.
Generated raw/decks/logs/waves stay in ignored output/sar8_async_impl/ under a
unique two-cycle case identity. No existing execution is overwritten.

Use the spectre skill's native runner, explicit save list, APS/conservative
transient (200-ps maxstep with adaptive device resolution), exact result.ok
and finite-vector validation. EVAS is not used because it has no MOS solver.
Use standard scientific plotting for measured waveforms per visualization
guidance: aligned time axes, labelled units, grouped/readable figures, no
ideal rectangular redraw passed off as measured electrical waveforms.

Deliver a concise two-period overview, full grouped node traces, per-bit
register/reference lanes, one-bit handshake detail, cross-frame undershoot
detail, and an honest original fault-case comparison. Keep raw voltages,
edge-derived buses and any annotations distinguishable. Do not suppress or
repair undershoot/SOA in the plots. All requested controller-level key nodes
are listed in a manifest; not every transistor terminal is a key timing node.

## Validation and completion

Bridge0.8.0 t28_io tunnel/daemon/Spectre healthy before simulation; confirmed
existing project/profile and remote IC618 session. Supported native runner
pattern checked in examples/02_spectre/01_inverter_tran.py.

Require exact unchanged native subcircuit definitions, complete finite saved
traces, two success observers with correct codes/eight decisions, preserved
last result through new acquisition, and measured cross-frame extrema.
Record and retain any functional/SOA failure rather than beautifying it.
Validate generated files, timing edges and signal coverage; visually inspect
all diagram groups. Run focused Python compile and git diff checks; stage only
owned paths, local commit `docs: visualize two complete asynchronous SAR cycles`.
No push; leave all Virtuoso/user windows unchanged.

## Result

Delivered one unchanged-hierarchy APS 202-ns run, two correct conversions
145/85, eight EVAL/CAPTURE/ADVANCE per frame, all 88 selected voltage traces
complete and finite. SAMPLE edges 1.01/101.01/201.01 ns delimit two exact
100-ns periods; VALID 87.349605/187.373284 ns. DOUT145 remains during second
acquisition until the next COMMIT.

First boundary CAPTURE=-86.541 mV at101.125 ns; closing boundary after the
second full period=-111.316 mV at201.126 ns. CMI begins201.114 ns, 25 printed /
15565 suppressed warnings: functional pass, SOA fail. Keep amplitudes distinct
from the older 165-code fault-case result. No root-cause isolation or repair.

Generated 18 PNG diagrams and seven scalable SVG overviews/bit-bank diagrams:
27-row control/bus overview, seven raw-node groups, six eight-bit banks,
single-bit detail, two boundary zooms and labelled old fault comparison.
All88 saved nodes covered; no unmeasured state synthesized. Targeted narrow
pulse / negative-peak preservation test passes. All figure text passes canvas
bounds checks; visual review of full main/detail/bit panels and three complete
QA contact sheets finds no remaining clipping/title/footer collisions.

During this target, concurrent reset-timing and inventory documentation commits
advanced shared HEAD to5ab88f7. Read and preserve those committed changes and
the new inventory maintenance entry; no branch switch or unrelated integration.
Our only shared report change is a bounded link, and log change is a new entry.

Source compile, JSON/links/SVG parse, signal coverage and scoped diff checks.
Local bounded documentation commit, no push. No remote OA or window changes;
unrelated ten-bit dirty files remain excluded.
