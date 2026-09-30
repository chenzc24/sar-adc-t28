# Local design review workbench v1

## Goal and boundary

Deliver a local, offline-capable review frontend with linked benchmark,
workflow and circuit-slot views. Sampling/bootstrap is the complete vertical
slice; other ADC modules expose honest evidence and coverage gaps. This is
presentation and data curation, not a circuit repair or new simulation.

Initial branch: `exp/bootstrap-protected-eval`, clean at start. The current-path
audit is already committed and is a read-only evidence dependency.

## Ownership

- Local owned: `review/`, `scripts/review/`, `verification/review/`, this plan,
  bounded README and `plan/log.md` entries.
- Generated: ignored `output/review/` and a loopback-only preview process.
- Remote OA owned: none. All OA, PDK, existing design specs, reports, scripts,
  experiment outputs and other plans are read-only.
- Dependencies: `config/design_spec.yaml`, existing reports and cell manifest,
  project Python/PyYAML, Node for focused JS checks; no cloud deployment.

## Implementation

1. Define stable IDs, typed metric/workflow/evidence relationships, source
   fingerprints, units and explicit assumptions. Reference existing spec values.
2. Curate the bootstrap screen and September 30 current-path audit without
   turning their scope-limited results into full sampler acceptance.
3. Build an offline HTML from maintainable CSS/JS and YAML. Include expandable
   derivations, linked workflow/gates, evidence inspector and Canvas slot.
   Scenario changes are local previews only and never mutate measured results.
4. Add deterministic validation and document the build/update process.
5. Check the rendered desktop/mobile UI and core interactions in a browser.

## Pass criteria

- Parse and validate all model records, IDs, typed edges, source paths,
  fingerprints, formula bindings and acyclic derivation dependencies.
- Focused calculation tests agree with the existing budget; reject invalid
  references and unsupported pass claims. Changing a budget never alters
  recorded observations; hash mismatch produces a visible stale status.
- Browser checks: all three tabs, module selection, node/evidence expansion,
  budget preview/reset, no broken rendering or horizontal overflow at mobile.
- Python compile, JS syntax/tests, `git diff --check`, owned diff inspection.
- Report OA/Canvas connection as not performed. Source excerpt availability is
  separate from raw artifact availability and simulator/rule qualification.

## Outputs and commit policy

Generated entry: `output/review/index.html` (embedded data, no CDN dependency).
Local maintenance docs live in `review/README.md`. Update the maintenance log,
then commit only owned paths as `feat: add local ADC design review workbench`.
No push is authorized by this target.

## Validation and outcome

- Implemented 13 typed metric nodes, 12 workflow steps, eight curated evidence
  records, source fingerprints, embedded source-text snapshots and two historical
  circuit bindings. Bootstrap current-path audit is included; no new circuit
  test or repair is implied.
- Ten Python contract tests pass, including cycle/reference/unit checks, stale
  propagation, historical observation immutability and rejection of a false
  pass. Node verifies budget values, formula units, scenario isolation and
  infeasible input handling. JS syntax, Python compilation and diff checks pass.
- Browser verified all three views, module selection, evidence/source dialog,
  candidate budget calculation and reset. The candidate changes theory while
  preserving the -8.755-mV observation. 390- and 320-pixel layouts have no
  document overflow; browser error/warning log is empty in inspected checks.
- The generated HTML has embedded assets/data and is usable without external
  resources. Direct file-protocol preview is blocked by the in-app browser's
  policy and was not bypassed; the verified preview uses the loopback server.
- Preview server: port 8765, bound only to 127.0.0.1, serving output/review.
  The browser tab is left open for user review.
- Concurrent unrelated files appeared during this target:
  `plan/2026-09-30-bootstrap-netlist-fast-ab/` and
  `scripts/characterization/screen_bootstrap_netlist_ab.py`. They do not overlap
  owned implementation/source inputs and were not read, changed or staged.
  This snapshot does not claim to reflect that in-progress circuit experiment.
- Commit only this target locally; no push and no remote OA mutation.
