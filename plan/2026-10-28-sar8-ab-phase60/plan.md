# A/B normal low60/high40 startup phase

User explicitly requests initial low60ns then high40ns, repeat100ns, unchanged
DUTs and operating conditions. Supersedes unsubmitted101ns startup candidates.
Owned: scripts/sar8_ab_phase60/, verification/sar8_ab_phase60/,
output/sar8_ab_phase60/, management/recipes/sar8ab-phase60-*.yaml,
management/runs/sar8ab-phase60-*.yaml and corresponding managed output dirs,
this plan and append-only plan/log.md. OA:none. Frozen A/B DUTs, old recipes,
PDK/library/history/Obsidian/manualADC/comparator/10bit/sharedmanagement read-only.
Dirty existing files reviewed; no overlapping edits. No commit/push/adoption.

Pulse val0=0,val1=SUP,delay60ns,rise/fall100ps,width39.9ns,period100ns.
First rising edge starts60ns, falling edge100ns; 50% high width40ns and normal
low width60ns. Source and measurement frame origin shift59ns (old fall41ns
becomes100ns). First input held since0; first valid output read157ns, then100ns
apart. Observer copied with time-origin parameter59ns, no DUT contributions;
first valid conversion is frame0 and must pass. Initial0..59ns unscored only.
Bootstrap plates additionally saved for precharge diagnostic; no .ic forcing.
Same10center codes,TT0.9V27C,loads,source/reference,solver settings and DUT hashes.
Do not claim low-clock DC initialization proves physical power-ramp/POR behavior.

Verify edge arithmetic, stimulus shifts, observer default-time roundtrip,
native analyzer shifted-frame/count/order tests and allinputhashes. Register new
managed IDs; serial finite flow submits A then analysis/collect thenB. Existing
flows remain untouched; managed queue enforces2heavy/4threads/1GiB sim/256MiB
analysis/32MiB collect/2GiB output. No duplicate submission or bypass.
Deliver first+all codes, original-vs-phase results, close/handshake/tail measures,
plots and status README. Native completion and observer agreement required.
Electrical stress deferred but warnings retained. If pending, report exact state.
