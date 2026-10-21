# Present final result figures with explicit bench status

## Goal and ownership

User requests top-plate common/differential mode instead of reference error,
separate parallel timing rows with minimum working-principle signals, final
results rather than iteration plots, and conditions/module status on every
figure. Replot saved numerical data using Matplotlib; no image editing,
simulation, GUI or OA operations. An electrical macro, rather than the pure
code-output VA model, supplies physical top-plate nodes; label that accurately.

Starting HEAD53722d8, branch exp/cdac-flat8-device. Result has user table
formatting edits; preserve that table while revising relevant narrative/figures.
Wrap-up and b_hf_main_w_analyze.py have independent dirty edits. All other
untracked/moved notes and cdac10_dualrail work remain outside scope. The new
4.5MHz work is launched, not an available completed result for this report.

Owned: Obsidian_docs/Rvision/Result.md; new assets/result8_final/ figures and
data provenance; scripts/reporting/result8_final_figures.py; this plan and one
append to plan/log.md. Ignored output/result_final_figures/ may hold the
pre-edit snapshot and analysis intermediates. Existing figures, data, source
reports, other notes and circuit sources are read-only. Remote OA owned:none.

## Work and validation

Inspect exact saved waveforms/receipts and existing analyzers. Create compact
final-design plots: electrical macro CM/DM with separated clocks; selected
Bootstrap; PDK capacitor final result if useful; unchanged StrongARM; final
native async timing; R3+B representative closed-loop conversion and baseline
continuous-sine result. Omit earlier designs, ablations, event-fix comparisons
and width candidates from displayed final plots. Preserve open failures in
brief prose/data and point history to Revision/Wrap-up.

Every figure carries simulator, process/environment/input/load and module
status (native/ideal/macro/not connected), plus noise/mismatch status as
applicable. Read real saved data, never synthesize logic waveforms or claim
nominal curves prove full qualification. Log inputs, hashes, transformations,
windows and displayed statistics. Compile/run focused plotting script, verify
CM/DM algebra, raw edges/decision counts, references and source metrics, inspect
each complete image, revise clipping/legibility. Validate Markdown/YAML/embed
targets, diff-check and full scoped review. Keep final report concise and
preserve existing heading anchors when practical. Local commit only:
docs: present final ADC waveforms with bench context. No push requested.

## Outcome

Generated seven PNG/SVG pairs: macro CM/DM and independent timing rows,
selected1um-only sampling fixture, selected MOM local-MC distribution, adopted
initial StrongARM nominal waveform, final simple_v2 SAR, current R3+B native
conversion and current1um continuous-input result. Every image includes its
actual bench, voltage/temperature/input/load and module realization. Only
separate DC/AC/local-MC behavior is claimed for the capacitor plot.

Removed all nine previous figure embeds, including historic ablations, width
comparisons and event-fix comparisons. Old images remain available, unchanged.
Retained six heading anchors and the user's comparator-table formatting.
The note is reduced from5458 to approximately3900 characters. Failures remain
explicit;3um is not silently adopted. Pending HF work and dirty analyzer/
Wrap-up/other note changes were not touched.

Compile and full plotting execution pass. Assertions verify CM/DM inverse
algebra, actual8/8/8 edge counts and final codes192/145/142, capacitor statistics,
191.3676ps displayed comparator cycle, and raw4.464649mV/14-of-20 failure.
All input/image/generator hashes, seven embeds, YAML, exact heading anchors and
preserved user table pass. All seven final images visually inspected after
label/axis/context refinements. Normal CM scale avoids magnifying numerical
noise; held-error detail is limited explicitly to post-handoff data, not
clipped. No simulation rerun, circuit change, GUI or OA mutation. Scoped review
and local commit only; shared log appended after reading its current end.

Matplotlib SVG trailing-space serialization initially failed diff-check;
normalized whitespace in the generator and validated all SVG XML. PNG hashes
are identical before/after that formatting change. Staged diff-check passes.
Global unstaged diff-check reports only the existing user Wrap-up line13
trailing space; left it unchanged and outside the staged set.
