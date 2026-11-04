# Collected HD clear-gate R comparison

Read-only frozen candidate/analyzers/HL inputs and original collected results.
Write only this comparison subtree and user-requested execution-status README
update. Parent owns managed operations/shared log. No re-simulation, new scan,
candidate preparation, other-module edits or changes to registered dependencies.

Pair HL baseline against completed managedf99c95e1c92a40c8abbe26f5456f77c03793e496538994c5ef75a17660a21e2b,
11files27685183B/no skips,11420points/654I/445derived columns. Verify exact
receipt/file/input/native hashes/PASS/END. Compare full738 actual pairs and
phase-specific amplitude/duration, clear and native X005 coincident endpoints,
MP_CLEAR/C1/R1/X005 gate charge, reset/assert delay and loaded-gate/reference
interfaces. Trace X005 negative-phase Vgd via RC1 and actual output-node
current incidence, not positive RC1 peak alone. Preserve all residuals and
strictly identify newly failing/cleared pairs. Inspect plots, give one necessary
future variable recommendation, never assume it works or launch it.

Completed local paired checkpoint: HL11298/652I/441columns versus candidate
11420/654I/445columns; candidate11files27685183B and exact managedf99c95...
hash verified, as are input/file/native stream size/SHA, PASS/END and settings.
All738 pair maps and full/rise/fall duration retained,1476unique CSV rows.
RCevent four-group re-integration agrees with remote values within explicit
floating accumulation roundoff only; input/native data/limits not changed.

HD RC1 positive1.061723->1.026241V, negative-19.953->-16.508mV. clearDS
max1.009953->1.006508V but timeabove.99 4.497->11.274ps. X005positivegd
1.061623->1.026231V, negativegd-1.009186->-1.035538V; totalabs timeabove.99
65.396->68.257ps. At48.004116292ns, simultaneous RC1=-.016367482V,
HD=1.019170740V; HD output peak now overlaps negative RC1 whereas baseline
RC1 already.471209V at its HDpeak (candidate-.016214V at its HDpeak).
Complete HD incidence=2native X005D+2H NANDG: at worst NANDG=-59.977uA,
X005D=+59.977uA. Leading Qsource+.123016/+.174058fC versus NANDG equal
negative, KCLmax1.104/.956pA. Identifies downstream gate-port backflow and
timing overlap, not a fabricated intrinsic current decomposition.

HD leadingMPQpos-.427214->-.267691fC with greaterR1diversion; negative
.113984->+.104552fC. First-return signed budgets also tabled, not confused
with completeCODEphase injection. LD almost unchanged. HD whole1%reset
11.507->31.734ps; LD18.985->19.022ps; physical4 reference windows and both
resets true. ActualN high23.524->23.498ps/low171.487->171.555ps. strict
214->215 solelyHDclearGD -.990000431V at42.995021286ns (+.431uVexcess,
duration.025057ps), >1mVcounts197unchanged; all residuals/CMI preserved.

Two plots inspected, worstnegative same-time markers added; Markdown tables,
links/AST/whitespace and numerical count/delta/KCL/Vgd tradeoff checks pass.
README now states managed execution/recovery complete and failure persists;
old preparation note explicitly replaced. One next variable recommended:
verified stronger nativeHD.X005 drive cell, other settings fixed, with input
capacitance/RCtiming/all stress checked; existence/model not assumed, no new
candidate or simulation. Registered inputs/analyzers, original raw/derived and
shared files unchanged. Checkpoint complete; no commit/push/adoption.
