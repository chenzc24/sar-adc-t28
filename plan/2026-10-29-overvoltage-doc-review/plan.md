# PDK overvoltage design-document review

Goal: inspect server PDK design/reliability and standard-cell documentation and
explain which voltage conditions actually apply to the frozen SAR8 warnings.
Read-only SSH to thu-wei, account UID596. No simulation or OA operation.

2026-10-29 persistent follow-up (search completed; envelope unresolved): user explicitly requests deeper continued
search. Expand read-only discovery to public process/document roots visible to this
account, exact QR identifiers, complete resumed filename inventory, current PDK
implementation archive and reliability/aging model configuration, and reference
content of remaining relevant documentation. Do not enter other users' private
homes. Use streamed bounded operations with checkpoints instead of abandoning an
inventory at its first time limit. Same local ownership; no simulation or mutation.

Persistent follow-up result: resumable filtered T28 filename queue completed,
126924 directories / 281080 files / zero matches or errors. Full ULL implementation
archive index 94066 entries; 363-page corner note OCR completed locally. DR-070
v1.7 AVT/SRM_ULL supplement p4 independently cites QR-095; p3/4 visually checked,
archive remote SHA256 matched. Other-process shallow search completed with 8
access errors retained. Report and manifest: persistent_search.md and
persistent_search_manifest.json. Still no applicable voltage-duration permission;
no limits, circuit, model, run, automation or adoption changes; no commit/push.

2026-10-29 follow-on (bounded search complete; envelope unresolved): continue user-requested document search. Prioritize
previously unsearched documentation/archive locations and explicit references to
qualification/e-Reliability/aging and overshoot. Include bounded metadata inspection
of the user's own TSMC28 documentation locations; do not inspect other users' homes.
Use the existing owned paths for original findings and ignored document extracts.
No changes to simulations, models, circuits or automations; no commit/push.
New result: DRM v2.3 reference table p11 identifies T-N28-CL-QR-095 (HPC+,
0.9/1.8 V, Fab15); visually checked, ULL coverage not established. Full streamed
indexes of current standard-cell doc archive (98 files) and nested ULL PDK DOC
archive (263 entries / 122 document-text entries) found no independent target.
Seven new guides plus representative IO manual text inspected; eight transferred
files hash-verified. Additional live name walk timed out at25s/19505dirs and is
explicitly incomplete. Saved qualification_followup.md and followon manifest.

2026-10-29 extension (bounded inventory complete): user requests unified nch/pch coverage. Inspect
actual frozen model families, both NMOS/PMOS and 1.8V variants, all terminal-check
definitions and existing bounded warning logs. Search device-specific reliability
sections rather than assuming standard-cell rules cover analog MOS. Save a unified
matrix under the same verification ownership. No waveform processing or reruns.

Result: all four model families checked independently; core nch/pch default six
checks 0.99 V, _18 nch/pch 1.98 V. Frozen A/B hierarchy and native standard-library
MOS types resolve all 165 printed terminal warnings in 11 collected small logs.
Analog A CDAC MN_LOW and digital A/B NMOS/PMOS warnings retained separately;
B SS cold DFF MM64 warning retained. Counts are suppressed/rounded log evidence,
not waveform maxima or durations. B TT short log not locally collected and is
explicitly excluded. NMOS/PMOS TDDB/HCI/NBTI/PBTI documentation references unified;
applicable numerical transient lifetime envelope remains unavailable. Sources,
hashes, events and original summary saved in device_warning_inventory.json and
device_matrix.md. Minimal validation: complete log parsing/hierarchy assertions,
numeric/count readback, JSON parse and scoped diff check. No simulation/circuit/OA,
automation, commit/push changes.

Ownership: this plan, verification/sar8_overvoltage_doc_review/ (original summary
and file identities only), output/sar8_overvoltage_doc_review/ (ignored document
working copies and page renders), append-only plan/log.md. PDK, standard libraries,
all circuit inputs/results and unrelated dirty Obsidian/manual/comparator and
management changes remain read-only. Existing dirty files do not overlap this
review. No commit/push, no changes to limits or adoption.

Steps: locate relevant documents; read applicable versions/pages; visually verify
critical tables; distinguish DC/rated voltage, model warnings, junction limits,
transient duty-cycle/lifetime rules; summarize applicability and missing evidence.
Use bounded document transfers and local PDF extraction, no raw waveform reads.
Validation: exact remote paths and hashes, page numbers and table context; no
unsubstantiated equivalence across processes/device families. Preserve unknowns.

Status: deeper bounded search finished; requested quantitative envelope remains
unresolved (not a successful reliability qualification). User-requested directory inventory and independent
reliability-file search. Same ownership and read-only boundaries. Capture directory
inventory, inspect matching reliability deliverables and their dependencies,
verify any quantitative stress envelope and its device/process applicability.
Final filtered traversal: 6145 directories, 216 document/keyword entries, no errors
or time bound; 55 ZIP indexes and nested model archives inspected. Qualification
Report referral found but report/envelope not located. New RN190A found and visual
review confirms SP079 1.0_2p8 pairing and valid CCS180a/doc170a/spi170a combination.
Paired model default core warning threshold is also0.99V; no false-warning claim.
Evidence saved in deeper_search.md and search_manifest.json. No circuit/model/run
or automation changes; no commit/push. Existing user dirty state preserved.

Previous pass: complete. Read-only SSH inspection found model warning guidance and actual
0.99 V terminal-check definitions, standard-cell lifetime-assessment referral,
and technology-scoped DRM reliability/design information. Four relevant PDFs
were SHA256 matched to server originals; the actual model identity was hashed
remotely. Critical model-guide, standard-cell, DRM and model-POR pages rendered
and visually inspected. Original findings and identities saved in
verification/sar8_overvoltage_doc_review/. No applicable transient lifetime
permission established; warnings and qualification status unchanged. MSOA acronym
misinterpretation explicitly corrected. No simulation, OA, adoption, commit/push.
