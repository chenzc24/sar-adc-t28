# GNN IO1 collected SS pairing and unchanged-circuit FF preparation

Owner reference/CDAC session. Write only comparison/ and candidate/ffcold/.
Root preparation/analyzer/helper, candidate DUT/delta/migration/metadata and SS
recipe/test/measurement are now frozen (proposal7f75ed...); do not modify them.
Shared plans/logs/management, other modules, user Obsidian, OA/PDK/libraries and
all original results read-only. Existing dirty state does not overlap these
new subtrees. No register/remote query/collect/run, commit/push or adoption.

Pair original standard SS (10956points,22126021B) with completed IO1 SS
(10464points,11files24264511B, managed
e42eefcc60054ad08228cd02fc809d40fff746d2e2f52fc22540c74a5e4d4b0c).
Verify all identities/input/receipt/native hashes and actual timing/port data;
compare both handoffs, real Vgs/Vsg/source exchange, reference establishment,
PRE/finalIO kickback, same actual terminal tuples and energy. Do not equate
source exchange to channel conduction or zero strict counts to full qualification.
Preserve startup/DC-initialization boundary, original warning codes and failures.
Deliver paired waveform figure and concise report with exact structured data.

Then prepare only sar8audit-ref-gnn-io1-ffcold-v1: identical frozen candidate
DUT/analyzers; test body comes from completed original FF fixture with its
actual model section/0.99V/-40C/reference/source/solver conditions. Verify the
only SS->FF differences are original PVT changes and legitimate supply-dependent
measurement metadata; same actual nodes/currents/screens and runtime method.
Keep all native sample/closing edges/load and original source logs. Do not alter
topology or prepare a new variant/sweep. Parent reviews/adopts managed operation.

Validation: projected native streams with128row blocks and independent source
peak/timing/energy/KCL readback; 702 pairs on fully unchanged MOS plus12 pairs
on the same rewired final devices (6of these retain identical endpoints),
24deleted-stage pairs. Thus708 exact matching model/node/limit tuples. View final image,
AST/UTF8/links/whitespace and scoped diff. For FF do one bounded preparation
check of identical DUT/inputs/graph/condition-only delta, using existing passed
runtime contract rather than adding an unnecessary new parser test matrix.

## Completed checkpoint

Paired original10956points/22126021B and IO1 SS10464points/24264511B using
their exact managed/proposal/input/receipt/full-native hashes, PASS/END and
652/636 initialized currents. Same external body/effective solver confirmed.
Local128row projection; final pairing3.180s. Independently recomputed physical
source-port peaks/integrals and PRE gate work; matched frozen runtime values.
708same model/node/screen tuples,6gate-remapped pairs,24deleted A/B pairs;
both0strict. Old47native diagnostic voltages supplemented only by original raw
measurement extrema, not invented traces; new114V covers714actual pair waveforms.

SS findings: L->GNN off419.367->113.643ps,on387.354->87.626ps. High N reference
source-exchange peak10.763921uA->28.985699nA; metric integral0.998385fC->2.820259aC.
Other3source peaks remain25..44nA; no pure-channel/zero-overlap claim. Four
command-phase1mV settling and HD/LD reset complete; no pre-CODE H/L halfrail
event. PRE min/max-28.434/844.183->-29.492/845.061mV, X025max0.845061V;
retained finalIO extrema grow to-0.268270/1.100865V, within actual1.98V screen
at this SS point. Local52ns VDD303.972->299.740fJ, GNNstage net5.691->1.464fJ,
not fullADC power/startup/PVT qualification. Both SS figures parent-viewed and
accepted; no further layout rework or duplicated runtime tests.

Prepared only same frozen circuit FF case sar8audit-ref-gnn-io1-ffcold-v1.
Proposal f67e60b0ceab7a9205249aa46820d4abde98beba7bf6bebb95711886b2ba0bd7,
13inputs483925B. DUT a0f3665f1d43cba886bff9dfa8098dd1948bea998c920c06f30a8e12c809dcf0
and all analyzers/714screens/actualnodes/measurement method exact. One bounded
preparation check proves originalFFbody and only4SS->FF PVT lines differ:
SUP,MOSsection,VVDD,CODEamplitude. Temp-40C/reference0.9/0V/otherPWL/input/
clock edges/passive models/Rgate/real load/solver unchanged. Existing0.802s
runtime test reused; no new matrix or native simulation by owner.

Parent accepted FF PVT_delta/package and confirmed registration/submission as
managed e32ae97bcfe3022f58de068333ddeae1886752ba043e9f6df14cab3533f03e78.
All SS/FF inputs frozen; do not rerun preparation. Parent owns status/collection
and later FF-pair assignment. Child only finalized SS prose and provenance;
no server query/run, shared-plan/log/OA/PDK edit, new candidate, commit/push.

Report validation:708unique rows, exact model/node membership, all four
establishment flags and reset/startup boundary retained, timing sum/source
metric/targeted terminal KCL, AST/UTF8/report links and scoped whitespace check.
