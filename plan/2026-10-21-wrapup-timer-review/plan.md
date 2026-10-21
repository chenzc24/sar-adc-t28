# Review user-edited wrap-up and illustrate the reference timer failure

## Goal and ownership

Review the user's latest wrap-up against repository evidence; explain section 5
concisely and add one readable actual-waveform figure. Keep the user's wording
and edits outside section 5 unchanged; deliver other factual qualifications in
chat rather than silently rewriting their observations.

Starting branch exp/cdac-flat8-device, ahead 14. The report has user edits,
including live changes observed during reading. Re-read immediately before a
targeted section replacement. Unrelated note moves/deletions, pasted images,
Rvision files, cdac10 work and b_dynamic_512 work remain untouched and unstaged.

Owned local paths:
- Section 5 only of Obsidian_docs/Report/Wrap-up & Experience.md
- scripts/reporting/wrapup_timer_figure.py
- Obsidian_docs/assets/wrapup_timer/
- This plan and one appended entry in plan/log.md
- Ignored output/wrapup_timer_review/ for a scoped staging patch if needed

Remote OA owned: none. Circuit sources, original simulation results, PDK,
all other note sections and all other project files are read-only.

## Evidence and implementation

Read r3_refgate_events, r3_b_oa_adoption, sampling_acceptance, sar8_simple_async,
sar8_async_implementation, cdac8_dualrail and the current b_short_acceptance.
Verilog-A skill and events/state reference guide review of the old deadline
guard and new pending-event handlers. No circuit or simulator change.

Use hash-verified A and b3 saved native waveforms and the curated event result.
Show SAMPLE, representative N7 bottom reference and differential input error
through acquisition/hold. Mark the source-time convention, physical error
measurement at 841.65 ns, the expected baseline, and A/B results. Explain that
timer is a VA scheduled event, and that a 0.159 fs callback discrepancy caused
the model to skip restoration for an entire approximately 40 ns acquisition.
The reference restoration is to the initial bottom-plate word, not all plates
to VCM. Keep the 100 ps guard/dead time and actual native circuit unchanged.

## Validation and artifacts

Verify saved waveform SHA256 against receipt and curated record; reconstruct
the frame 9 held errors and final codes from saved pins. Plot actual samples,
not fabricated waveforms. Visually inspect PNG; parse SVG; validate figure
links and report UTF-8/YAML; inspect scoped diff and run git diff --check.
Preserve text outside section 5 exactly against a pre-edit snapshot.

Save PNG/SVG plus small manifest and source note under assets/wrapup_timer.
Stage only section 5 from the report, the new assets/script/plan and log append.
Intended local commit: docs: explain reference timer failure with waveforms.
No push, GUI operation, remote mutation or new simulation.

## Outcome

Section 5 now defines timer, explains the rejected callback / missed 40 ns
acquisition / late bottom-plate switch sequence, and embeds a Chinese A/B
waveform figure with full-window and handoff views. The early callback was
about 0.159 fs, versus a 0.001 fs secondary comparison margin. The figure uses
actual SAMPLE, N7 bottom, and differential error; 841.65 ns readings reproduce
-442.8504966 / +0.1013553 mV, with saved-pin final codes 1 / 65 at 898 ns.

Waveform hashes match receipts and curated evidence. Script execution, AST,
PNG visual inspection, SVG parse, output hashes, UTF-8/YAML and new links pass.
Report prefix and source footer outside section 5 match the immediate pre-edit
snapshot exactly, including intervening user edits. No source outside the
owned paths changed. Whole-report diff-check still flags the user's preexisting
trailing space in section 1; the staged section-5 patch is checked separately.

Other review findings are delivered in chat: early 12.03/9.10 mV switch results
and later old-topology 1.536 mV use different fixtures; new 0.126 mV is the
8-bit 1-um five-point fixture. Native control uses complementary binary trial,
not a verified named bidirectional algorithm. Module PVT/mismatch and bounded
44-frame integration work exist, while full ADC qualification is incomplete.
General claims about LLM research/design habits remain personal observations.

Commit policy: only section 5 staged from the report; all other user edits stay
in the working tree. New script/figure/provenance/plan and this target's log
entry included. No push.

## Follow-up: focus on early problem detection

User requests a concise section 5 about AI-assisted short tests and monitoring,
with timer only as an example. Explicitly identify the ideal reference-gate
model's code fault and the absence of transistor-level implementation for that
control logic. Preserve the user's newly shortened section and existing figure;
all other report sections and the figure sources stay read-only.

Current branch ahead16, with user edits in the report and unrelated note/cdac10
work. Same ownership: section5, this plan and one log append. Replace only the
section body/title; validate exact preservation outside it, the image link,
UTF-8/YAML and a section-scoped staged diff. Local commit only, no push.

Follow-up completed: two short paragraphs emphasize early detection and use
the VA timer fault only as an example. Explicitly distinguish the unimplemented
native reference-control logic from existing transistor circuits. Existing
figure retained with a concise code1-to65 caption. Outside-section text and
all other user edits preserved; only this section staged from the report.
