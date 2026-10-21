# Adopt the verified reference-gate B fix in Virtuoso

## Goal and ownership

User authorizes synchronization of final B (local candidate b3, commit 39a2ee2)
to Virtuoso, preserving transistor topology, all device sizes and simulation
precision. Discuss shorter fault-finding tests; do not launch a full campaign.

Branch exp/cdac-flat8-device. Unrelated untracked cdac10_dualrail configuration,
models, scripts, verification and plan are user-owned and remain untouched.

Owned local paths: this plan; scripts/integration/r3_b_oa.py;
models/veriloga/sar8_join_b/; verification/integration/r3_b_oa_results.json;
docs/r3_b_oa_adoption.md; plan/log.md. Generated evidence: output/r3_b_oa/.
Also own the narrow current-status update in docs/project_status.md so its
entry does not continue claiming that the interrupted old campaign is running.
Remote OA intended ownership: SAR_ADC_T28/sar8j_aligned_refgate_b
(placeholder schematic, symbol, veriloga and CDF), and only the 16 ideal gate
master bindings in SAR_ADC_T28/sar_adc8_join_r3/schematic. All other R3 instance
properties/connectivity/geometry and tb_sar_adc8_join_r3 are read-only. Historical
R0/R1/R2 and original shared reference gate remain unchanged. Never edit raw OA.

Shared dependencies: verified B source and input-history results are immutable;
native T28 PDK, controller, CDAC, comparator, Bootstrap and reference pass MOS
are read-only. Bridge profile t28_io, user chenzc_intern25, thu-wei, llm_IO,
library SAR_ADC_T28, tech tsmcN28 must be verified before any OA mutation.

## Steps and validation

1. Restore only the local bridge tunnel using its documented SSHClient.warm;
   require healthy daemon/user/session and Spectre, inspect windows/locks.
   No Virtuoso restart, forced lock removal, process termination or dialog dismissal.
2. Capture current R3 topology/positions/all parameters, native dependency
   surfaces, CDF, and exported original netlist. Stop on unsaved/locked targets,
   unexpected changes or unowned existing B cell.
3. Import a versioned B VA cell with an otherwise exact copy of verified b3,
   changing only its module name to the new master name. Preserve all ports,
   default parameters, output equations and diagnostics. Preserve old gate.
4. Use a documented supported binding API, if available, to switch only 16
   ideal gate masters in current R3. Read back and require every other instance
   parameter, pin, net and geometry unchanged. Export a fresh OA-derived netlist;
   require every native subcircuit byte-identical and identical top statements
   after normalizing only the versioned gate name. Check explicit 100ps restore,
   100ps dead time and 50ps edges.
5. Verify remote VA readback hashes and port/CDF equivalence. No all-code/FFT
   simulation in this turn. A minimal native elaboration/short smoke is permitted
   if needed solely to validate import; do not relax existing precision.
6. Record factual receipts, limitations and a suggested staged front-end
   verification ladder. Syntax/diff-check and scoped local commit, no push:
   `fix: adopt verified reference gate B in Virtuoso`.

## State

Started. Previous status check showed local Windows reboot at 08:21 and stale
bridge tunnel state causing status WinError87. SSH remains reachable. Original
four full R3 Spectre processes and local campaign coordinator are absent;
partial remote results remain. No full campaign restarted or cancelled.

Connection recovered through normal warm; healthy matching CIW and Spectre.
Read-only original gate symbol/VA, R3 symbol and TB schematic have existing
CIW cache locks (33567); they will not be modified, unlocked or closed.
The only existing writable target, R3 top schematic, has no lock and no GUI
editor is open. Native and historical OA surfaces match frozen records.
The lock preflight is narrowed to the actual writable schematic; read-only
dependency locks are recorded, not treated as authorization to unlock.

## Completed result

Normal warm recovered the healthy tunnel without terminating anything or
requiring CIW reload. Original gate/commit models and 36 native/historical
surfaces verified. Imported new B symbol and VA through supported copy/import/
reparse APIs. Symbol terminals (including physical positions) and exposed CDF
equal the original; source differs from tested b3 only in module name.

Switched exactly 16 ideal reference-gate instances through documented
dbSetInstHeaderMasterName in the current top. Readback confirms all other OA
fields, parameters, geometry and connectivity identical, TB unchanged, zero
markers. Fresh before/after exports preserve every native subcircuit text and
all top electrical statements, testbench sources and simulator options.
Instance-header replacement changes only top statement serialization order;
compare top records by instance name, not byte order. This warrants a fresh
original-history replay next, not a claim of identical full ADC trajectories.

Downloaded imported VA ran original B gate unit on native Spectre21.1 APS4,
same precision. result.ok,0errors/1warning/6notices (old AHDL environment warning).
20saved signals,121443timepoints exactly equal verified B, preserving all96
midpoint and96conversion checks. Compute11.63s,total27.50s. No full ADC replay
or static/dynamic campaign launched. Earlier completed B12frame results remain
separate evidence; no new OA-top full performance claim.

Receipts verification/integration/r3_b_oa_results.json and output/r3_b_oa/.
Updated project status to remove stale running-campaign claim and link the
adoption/short-test proposal. Source/receipt check,syntax,diff-check and scoped
review pass. Scoped local commit only; no push. All unrelated user files kept.
