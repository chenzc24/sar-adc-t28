# Feedback TT v2: measurement-only save reduction

Local only, not Spectre compiled/submitted. recipe_proposal.json is ready for
parent managed serial registration. The failed v1 is immutable and not retried.
Same1457MOS, full feedback, physical cut,100ns, sources/initialization, model
includes, solver tolerances,1GiB RSS/one thread and2048MiB output budget.
cells.scs/cdac_load.scs/initializer.va/native_support.py are byte-identical.

Save124V/23I. Keep exactly the same57 returned native timing/current/KCL columns.
Additional required voltages cover all N4 comparator and the complete native
154MOS sar8p_timing cone, including rx2, RAW/DEC, write/update, SR/QUIET and
clock output driver:165MOS/990 terminal-pair screens. Every requested save uses
its actual case from the native v1 accepted list. No wildcard/allpub saves.

1292 retainedMOS/7752 pairs are explicitly unmeasured by local waveform stress
analysis. Output full_mos_screen_complete=false and full_mos_screen_exceeded_records
=null; selected_mos_screen_exceeded_records is only the165MOS screen. Native CMI
remains enabled across the unchanged circuit and its complete log is preserved.
No all1457/8742 waveform-stress pass or lifetime qualification can be claimed.

V1 accepted711V/23I; its2GiB psfascii failure at38.0381ns starts with SPECTRE-27,
followed by7082/USIMUWI-20006. Native PASS=false; peakRSS319,078,400B does not
demonstrate memory exhaustion. Log/receipt hashes are in manifest.json.
ASCII name/field-cost extrapolation estimates1007.6MiB to100ns or1511.4MiB at
1.5x native point density. No accepted-step footer exists after abort, so this
is a capacity estimate, not a guaranteed bound;2048MiB hard gate stays active.

Only save statements/configuration and stress-report scope labels change.
Native protocol, token/write/update/reset and recovery algorithms are unchanged.
All original warnings/native errors must remain visible. Streaming derived cap
29MiB and total32MiB collection allowance remain; do not collect raw PSF.
