# GNN loaded IO path attribution and one-stage contrast — 2026-10-27

Owner reference/CDAC session; write only this standard_cell_gnn_path_v1/ subtree.
Parent owns shared plans/logs and managed execution. Branch ahead30 and dirty
shared management/Obsidian/log changes remain protected and nonoverlapping.
No remote work, native-library/OA/PDK edit, commit/push or baseline adoption.

Source completed original native-standard SS cold case
sar8audit-ref-bbm-stdcell-sscold-v1,10956points/resultSHA
c61c9a71f01e9485c455ec26e0424cfbd2847fae9e10d2d1618cdebb9be8615e.
Prior standard_cell_ss_nonoverlap_v1 establishes high-select N source-exchange
risk; no need to wait for intrinsic channel-overlap duration before proceeding.
All PRE/GNNA/GNNB/GNNDRV/GNN0 nodes and their native halfVDD events are present.

Attribute both directions of L0->X025->three identical IO inverters->Rgate->GNN0.
Check native edge brackets, source hashes and actual identical A/B/C gate pairs.
Only if stage count dominates, prepare one SS contrast: delete GNNAN/AP and
GNNBN/BP, connect unchanged final GNNCN/CP gate to real PRE instead of GNNB.
Keep odd inversion parity, final model/parameters/multi, real output load,
every Rgate leaf, other paths/standard cells, supplies and external PWL exact.
This is one analog-interface stage-count factor, not a new architecture or
individual-transistor attribution. No divider/drive/slew sweep.

Candidate measurements must cover actual final IO and upstream native X025
all terminal pairs and kickback; PRE/final actual load currents/work; both
directions of four switches' Vgs/Vsg/DGSB currents and reference source exchange;
original command-phase reference establishment, reset/pre-CODE startup history
and all actual MOS pairs including duration. Do not alias deleted stage names,
assign their measurements zero, assume Vth or equate halfVDD with channel state.
Existing DC-initialized bench cannot qualify physical supply-ramp startup.

Validation: one focused package check combining exact graph/exterior/input
equality and required runtime measurement exercise; AST/scoped whitespace/link
checks. View one small baseline attribution figure. Stage one frozen SS recipe
with budgets only for parent review/admission; no registration/submission by
owner. If SS improves, parent may later admit same circuit at FF to inspect
kickback; no second case or broader matrix prepared now.

## Completed checkpoint

Verified source identity/frozen inputs/receipts/full native hash through the
existing SS evidence loader and checked all6saved path-node crossings against
their actual native brackets. Both directions present; no missing/extra event
substitution. Source SS IO A/B/C off delays86.010/140.595/133.279ps,
Rgate51.646ps,X0257.837ps,total419.367ps. On direction73.888/150.904/122.459ps,
Rgate32.331ps,X0257.773ps,total387.354ps. IO stages85.8/89.6% of total.
Naively removing old A/B gives only16.806ps high-side halfrail ordering margin;
explicitly not a predicted channel-conduction pass because slew/kickback change.
One parallel-node timing figure inspected with negative extrema visible.

Prepared only SS case sar8audit-ref-gnn-io1-sscold-v1. Four A/B IO devices
deleted; final GNNCN/CP inputGNNB->realPRE, exact existing model/params/multi,
D/S/B/load unchanged; all188 other leaves and10Rgate records exact, native42
MOS mappings unchanged. All3original IO gate-pair params identical, so there
is no nominal input-area increase; actual gate charge is not assumed identical.

Final proposalSHA
7f75ed0953931628d7fdb2c0d72d34c5f510c8c551114e8abae0c583eef4fa88,
13inputs482073B;114V636I34KCL/119actualMOS714pairs/421nativecolumns.
New runtime replaces only legacy metrics requiring deleted A/B nodes; no zero
energy/trace aliases. Uses original native parser and actual library metadata,
all-pair duration measurement, independent command-phase reference settling,
PRE/source load work and KCL, all4switch DGSB/source exchange both directions,
finalIO/X025 same-time worst-terminal currents and PRE kickback, complete0–52ns
and pre-CODE startup history. Physical supply-ramp startup remains unqualified.

One focused package contract check passed0.802s: exact graph/parameter/load/
PWL/input-hash delta plus synthetic native-parser/analyzer execution,714pair
coverage, source-vs-drain diagnostics and PREwork closure, absent removed-node
columns, simultaneous targeted peaks and explicit unknown channel timing.
Synthetic fixture is not a circuit simulation. AST/UTF8/whitespace/link checks
and final13input hashes verified. No native Spectre elaboration yet; no register,
remote query/run, FF case, shared-plan/log update, commit/push or adoption.
Parent owns review/admission and later FF decision only after SS result.
