# Independent reference-current package review

Snapshot: 2026-10-26 09:21:25 Asia/Shanghai. Reviewer owns only the comparator
subtree. Reference/control files and existing comparator results were not edited;
no remote command, simulation, registration, commit or push was performed.

## Finding requiring correction before dispatch

**P1: generated source-peak times do not match the analyzer interface.**
`reference/prepare_current_analysis.py:62` copies the recovered peak dictionaries
with `time_ns`. All four entries in the generated managed `measurement.json`
therefore lack `time_s`; the analyzer's source-peak result construction reads
`item['time_s']`. A four-point synthetic PSF containing all 1,375 actual selected
signals reproduces `KeyError('time_s')` after successful streaming. Production
analysis cannot finish or write its final `result.json` with this combination.
This is a measurement-package defect, not evidence of a circuit fault.

Normalize the producer's peak times explicitly to seconds, validate required
peak fields before processing the raw file, and include a smoke check using the
actual generated configuration. Do not merely rename the numeric nanosecond value
to `time_s`. The 24 synthetic tests currently supply their own valid `time_s` and
therefore do not catch the generated-package mismatch.

## Independent checks

- All 275 requested current paths exist in the physical fixture or explicit
  external deck, with matching node, port, model, parameter hash and native save
  statement: 152 MOS ports, 80 poly-resistor ports, 36 MOM ports and seven external
  source/resistor/capacitor ports. This is a selected diagnostic set, not all
  currents in the 1,551-MOS fixture.
- All five KCL incidence sets independently match the flattened physical graph:
  GNNDRV 3, GNNB 4, GNNA 4, GNNRG 2 and GNN0 2 incident ports. The native port-current
  convention is positive from node into component; all terms enter the node sum
  with coefficient +1. Multiplicity must not be applied again.
- Replay-to-save mapping resolves: the replaced CAP_REQ source maps to
  `replay_xdut_xref_cap_req`; retained analog diagnostic nodes keep their native
  names. Required initial witnesses and diagnostic targets are in the saved set.
- The 24 local tests passed on the pinned analyzer/test snapshot. They cover
  signed current/KCL, sparse updates, GROUP/property aliases, missing TRACE or
  initialization, duplicate updates, END/stop checks, output budgets, native
  brackets, preserved CMI logs and final-result-last behavior. Tests used only
  synthetic files under the comparator subtree and cleaned them afterward.
- After converting `time_ns * 1e-9` **only in an in-memory probe configuration**,
  the real 275-current configuration streamed all four synthetic points, retained
  the last point at 65.99650423427016 ns, and integrated every constant 1-uA branch
  correctly over both the full interval and the actual in-window knot interval.
  No reference package was repaired by this review.
- Full-history export has 27 columns; fault export has 324. Gzip is lossless;
  compressed writes and final JSON consume the shared 30-MiB output budget.
  The frozen baseline table is bounded to 4 MiB, native lines to 64 KiB and edge
  records to 10,000. Linux CLI applies a 240-MiB address-space limit and checks
  256-MiB peak RSS. Real-run time, RSS and compressed output size remain unmeasured.

Signed charge uses native-knot trapezoids. `abs_C` is a trapezoid estimate of
sampled absolute current, not an exact decomposition into injection, conduction
and displacement charge. Fault charge uses only knots inside the reported actual
interval; it does not invent values at the requested window boundaries.

## Pending

Correct the time-field mismatch, regenerate/freeze the package and rerun its
actual-config smoke check before dispatch. Native Spectre TRACE realization,
current sign/KCL residuals, source-wave electrical reproduction, real resource
usage and Python-2 runtime execution are still pending. `acceptance_pass` remains
null; this review makes no repair, lifetime, ADC or comparator qualification claim.

The author changed analyzer/preparer/generated configuration during review.
The hashes below identify the exact final local test snapshot, not a commitment
that later shared files are unchanged or ready for registration.

## SHA256 of tested snapshot

| File under reference/ | SHA256 |
| --- | --- |
| reference_current_analyze.py | `81934249e6c21cecdf800413ad4afa41c60b457a59213a58ae0eb23242504c9f` |
| prepare_current_analysis.py | `e94a7f8ff45f0aedcaa89b75928fbca45f203237121e05e640949de25a6a1374` |
| build_first_fixture.py | `b2ccb8f138325ad808894e495bce58fa53b3302cb4d82af4693e0c6fe1b32729` |
| generated/first_reproduction/measurement_map.json | `c8b6236d8a6e104d3ce7eb1667e53caa2cb7c328fa68a2ce297634ded975bf4f` |
| generated/managed_reproduction/measurement.json | `78683a2a796b5781ccbb2677a7c809b66bef46f7ec1fd584a023f479d8c9d536` |
| test_reference_current_analyze.py | `f087a4acfb625d3da2f6af8b1d678b1fedc2f9995233d4f14b00205c444c9d5a` |
