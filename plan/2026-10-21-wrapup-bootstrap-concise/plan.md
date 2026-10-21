# Shorten the user's Bootstrap report section

Goal: two short old/new statements and one final data table, following the
user's manual reduction. Preserve all other sections, images and sources.
Starting HEAD653e509; branch exp/cdac-flat8-device. The report
contains user edits in sections1–3 and elsewhere. Only section2 is owned; other
edits remain unstaged. Concurrent HF-width analysis/docs and other vault moves
or drafts are read-only. Remote OA owned: none.

Owned local paths: section2 of Obsidian_docs/Report/Wrap-up & Experience.md,
this plan, one append to plan/log.md, ignored output/bootstrap_note_concise/
for a staging patch. No GUI, simulation or image changes. Read-only evidence:
bootstrap_driver_error_reduction, eight_bit_flat_migration, b_sine_main_w and
canvas_bootstrap_full_cdac reports. Correct the user's merged load attribution:
0.126mV belongs to8-bit flat/1um, not historical split-CDAC/0.5um.

Verify exact byte preservation outside section2, both image embeds, selected
source values and diff-check. Review/stage only section2 against HEAD, leaving
other user report edits unstaged; scope plan/log as usual. Local commit:
docs: shorten Bootstrap wrap-up to core results. No push requested.

Outcome: retained the paired image table; two compact old/new statements,
500kHz1/2/3um result table and one adoption/tradeoff sentence. Corrected the
0.126mV fixture attribution. Outside-section text matches the user's starting
version exactly after newline normalization. Both image embeds unchanged and
values checked against the four reports. A zero-context patch stages only
section2 against HEAD; user edits elsewhere remain unstaged. Scoped checks
pass; global diff-check retains the user's pre-existing section1 trailing
space rather than editing outside ownership. Local commit only.
