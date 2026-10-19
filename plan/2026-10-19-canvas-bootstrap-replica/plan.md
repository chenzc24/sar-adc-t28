# Native T28 bootstrap from the user's Canvas topology

## User correction superseding the visual-replica approach

The user clarified that the goal is a T28 design using native devices from
the existing PDK, the Canvas topology, and a bounded sizing iteration. Custom
graphic/device wrappers are not requested. Stop work on the seven `*_1019`
cells: they were connection checked but never simulated or accepted.

Active remote ownership: new native-device cells
`SAR_ADC_T28/sar_bootstrap_canvas_t28/{schematic,symbol}` and
`SAR_ADC_T28/tb_bootstrap_canvas_t28/{schematic,maestro}` if needed.
Use ten original native T28 1.8-V MOS plus two T28 MOS for the inverter,
analogLib capacitors and the original body connections. Native PDK symbols
and electrical topology take precedence over pixel equivalence. Preserve
relative placement and route paths where symbol contacts permit.

Active local owned sources additionally:
`scripts/characterization/canvas_bootstrap_t28.py` and
`docs/canvas_bootstrap_t28.md`, plus the compact user-topology source
`config/canvas_bootstrap_topology.json` and the two new entries in
`virtuoso/cell_manifest.yaml`; generated evidence in
`output/canvas_bootstrap_t28/`. Compare the all-1-um baseline with bounded
W/Cboot candidates, keeping the 1.8-V device L at 150 nm unless the PDK
requires otherwise. At each chosen geometry export the actual saved OA
circuit unchanged, run nominal static and changing-input checks, then
install/read back the selected geometry. Record raw errors even if the
allocation is not met; no topology fix or calibration is implied by sizing.
Active intended commit: `feat: characterize Canvas bootstrap with native T28 devices`.
Analysis/report ownership additionally includes
`scripts/analysis/analyze_canvas_bootstrap_t28.py` and generated comparison
figures and warning/terminal-voltage summaries. The abandoned visual-replica
generator is archived in ignored output, not retained as a design dependency.

## Initial visual-replica attempt (superseded)

Reproduce the user's current Analog Canvas `Bootstrap switch/dut` (revision
357, structure revision 32) in native Virtuoso schematic, preserving device
positions, orientations and all route polylines under one uniform coordinate
transform. User selected T28 1.8-V MOS, original W=1 um, L=150 nm, m=nf=1,
Cboot=Cs=1 pF. Keep the existing project bootstrap cells unchanged.

Start state: `exp/top-plate-gmain-t28` clean, three local commits ahead of
origin. No unrelated dirty files. No changes to Canvas are authorized or needed.

Owned local tracked: this plan; `scripts/characterization/canvas_bootstrap_replica.py`;
`docs/canvas_bootstrap_replica.md`; factual entry in `plan/log.md`.
Generated: `output/canvas_bootstrap_replica/` (snapshot, render, scripts,
readback, exact OA netlist, Spectre logs/PSF, metrics and figures).
Owned remote library: SAR_ADC_T28 only, new cells
`sar_bootstrap_canvas_1019`, `tb_bootstrap_canvas_1019`, and helper cells
`canvas_bs_1019_n`, `canvas_bs_1019_ps`, `canvas_bs_1019_pd`,
`canvas_bs_1019_cap`, `canvas_bs_1019_inv` (schematic/symbol, with a behavioral
inverter view if needed). Existing cells and all PDK libraries are read-only.
Refuse pre-existing targets rather than overwrite them.

## Method and assumptions

- Inspect current MCP exports and published export UI before claiming native
  direct export support. Current adapter exposes project/image/netlist exports.
- Save the exact Canvas snapshot and SVG/PNG; never store connector claims.
- Read back library technology and PDK pins first. Use local custom symbols
  with Canvas terminal geometry, each backed by an actual schematic containing
  T28 `nch_18_mac`/`pch_18_mac`. NMOS bulk remains grounded; PMOS bulk follows
  the original source or drain. This preserves top drawing while retaining PDK
  subcircuits. Record the helper hierarchy explicitly.
- Retain the Canvas ideal inverter, including its 10-ps/10-mV settings; do not
  silently replace it with a differently timed transistor inverter.
- Translate every route point with one scale and y-axis reversal. Do not
  autoroute or replace visible wires by net labels. Hidden body connectivity
  is implemented inside the appropriate helper schematic.
- T28 first nominal run: VDD=0.9 V, 27 C, TT, 10-MHz sample clock, 100-ps
  edges, static inputs 0.05/0.45/0.85 V and one changing-input diagnostic.
  These are fixture assumptions, not Canvas-provided conditions. Acquisition,
  edge injection, holding error, gate/BOOT waveforms and warning inventory
  are measured; numerical failure is a valid result, not grounds to resize.

## Steps and validation

1. Capture source data, check bridge/session/library/target absence, and read
   actual APIs and PDK pin geometry. No unsaved user-owned target exists.
2. Create isolated helper cells, replica and testbench using supported bridge
   APIs. Read back schematic connections and native wire geometry.
3. Compare every Canvas device connection through the documented wrapper
   mapping; compare all transformed route polylines exactly (within OA grid).
   Check & Save, inspect markers, capture the Virtuoso drawing for review.
4. Export a fresh unmodified OA circuit netlist; add only model/environment,
   stimuli/analysis/save instructions outside the exported circuit. Require
   Spectre result.ok, inspect warnings and save exact run provenance.
5. Report the measured results, geometry differences if any, and the model/
   symbol/ideal-inverter boundaries. Run Python compile, diff check, update
   plan/log.md and commit only owned tracked sources. Do not push.

## Output and commit

Exact source and generated evidence: `output/canvas_bootstrap_replica/`.
Intended commit: `feat: reproduce Canvas bootstrap in Virtuoso with T28 MOS`.
No claim of layout parasitic equivalence or completed ADC acceptance.

## Cleanup and final evidence

After native-device verification, retire only the six mistaken wrapper/drawing
cells created during this target (the old `tb_*_1019` was never created).
Archive their source/readback under ignored output first, reject any unsaved
or unexpectedly modified cell, close only their exact windows, and remove
them with supported `ddDeleteObj`. No existing project design is removed.
The native DUT and testbench are retained open. A fresh final OA export must
match the selected five-point simulated export except its generation timestamp.

## Completed result

Native topology/clock/capacitor readback passed; final schematic has zero
Check & Save markers. Seventeen useful nominal Spectre transients succeeded.
Selected Mmain W/L=0.5 um/150 nm; all other MOS 1 um/150 nm, Cboot=Cs=1 pF.
The five-point held-error maximum is 0.302735 mV; maximum acquisition error
is 0.056856 mV. The 0.32-um main and stronger-reset variant fail acquisition.
Final saved OA export is identical to the five-point simulated selected export
except generation timestamp. Six mistaken draft cells were removed and their
source/readback archived under ignored output. No existing design was removed.
The native source/config/report/manifest/log receive one scoped local commit;
no push. PVT/noise/mismatch/full-CDAC validation remains outside this target.
