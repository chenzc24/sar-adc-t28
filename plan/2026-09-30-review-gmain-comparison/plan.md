# GMAIN comparison figure

Add user-supplied top-plate sampling comparison to the GMAIN design node.
Own review/figures.json, review/node-notes.yaml, review/assets/gmain-comparison.png,
scripts/review/build.py (allow curated review/assets figures),
verification/review/test_build.py (figure count), this plan and plan/log.md.
Preserve unrelated circuit work. No OA objects or simulation; reports read-only.
Retain exact image; caption its top-plate, 0.8 V differential input, 270 ns
measurement and partial-transistor scope, without importing signoff claims.
Validate build/tests/hash/path boundary and browser figure dialog; local commit,
no push. Generated preview remains in output/review.

Outcome: added original PNG with hash-pinned registration at GMAIN safety node;
23 tests/build/diff checks pass and browser confirms dialog/caption. Screenshot
output/review/gmain-comparison-preview.png. Existing full_cdac source fingerprint
changed outside this task; retained need-review markers, did not accept baseline
or update experimental conclusions. Unrelated pgate-driver plan/script preserved.
