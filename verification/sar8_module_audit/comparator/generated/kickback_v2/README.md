# Kickback v2: exact-case save names

Local proposal ready for parent managed dispatch. This package changes only the
Spectre `save` spellings and their corresponding input hashes. All circuit,
initialization, clock, endpoint, model, tolerance and analyzer bytes/settings
are unchanged from v1. The2-GiB output budget remains unchanged; queue timeout
is600s, matching the registered v1 run.

## What failed in v1

The original19810-byte `spectre.out` is preserved in
`output/managed_execution/runs/sar8audit-comp-kickback-tt-v1/collected/`.

| Log lines | Evidence |
| --- | --- |
| 149--171 | Lowercase saves do not resolve uppercase netlist symbols; SPECTRE-8281/8286 and8282/8287 ignore them |
| 248 | No outputs found; the simulator falls back to `allpub` |
| 281--282 | Actual output is463 voltages and9 currents, versus the requested36 voltages and45 currents |
| 294--300 | File-size limit at221.657ns; SPECTRE-27,7082 and following writer/fatal errors |

This is a measurement-name generation error. The81 save statements shown in
the inventory are not evidence that81 requested signals were accepted. The
fallback increases the total saved trace count to472. The aborted log has no
accepted-step summary; it does not prove the absence of timestep refinement.
The native transient is FAIL and has no zero-error footer, despite process exit0.
There is no completed v1 electrical result.

SPECTRE-16881 refers to initial-condition/Verilog-A convergence, separately from
the output fallback. The simulator subsequently tried Fast DC0 and entered the
transient. Keep this warning and the matrix/Gmin context visible in v2; do not
loosen tolerances to remove them. Also preserve the SFE-3031 internal capacitor
removal warning and all foundry/environment warnings.

## Correction and local validation

`prepare_kickback_savefix.py` resolves all36 nodes and45 terminal-current saves
against the actual flattened fixture and top-level deck, preserving declared
case. The PSF analyzer still normalizes names after reading. No ideal clamp,
device, parameter, edge, endpoint or output-format change was introduced.

Four focused tests passed: v1 invalid case is rejected, every generated v2 save
resolves, non-save circuit statements/other inputs are byte-identical, budgets
match, and synthetic uppercase native/GROUP/sparse data still produces all six
expected diagnostic writes. Original v1 artifacts and logs remain unchanged.

Submit `recipe_proposal.json` once through the parent managed queue. The first
native checks are absence of ignored-save/allpub fallback, all requested TRACE
initializations, complete260-ns PASS/zero-error footer and retained warnings.
Then analyze the original +/-0.25-LSB held inputs, differential/common-mode
kickback, writes and delay. Fixed CDAC bottom rails and temporary ideal
initialization remain diagnostic boundaries. No electrical pass is claimed here.
