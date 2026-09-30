# ADC design review workbench

Local, read-only v1: benchmark derivations, module workflow and an unconnected
Analog Canvas slot. Sampling/bootstrap is the complete vertical slice; other
modules deliberately show partial coverage. No remote OA or PDK mutation,
network dependency, or simulator run is part of this application.

## Build and open

From the ADC repository in PowerShell:

```powershell
.venv/Scripts/python.exe scripts/review/build.py
Start-Process output/review/index.html
```

The output embeds all CSS, JavaScript, structured records and plain-text source
snapshots, so it also works via `file://` with no server or CDN. To preview in a
browser which only accepts HTTP, serve **only the generated review directory**:

```powershell
.venv/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1 --directory output/review
```

Open `http://127.0.0.1:8765`. This exposes curated reports, not raw model/OA
files. Do not bind to a public interface. Stop the preview server when unused.
Source snapshots may still contain project-private design information: review
them before sharing the generated HTML outside the project.

## Source of truth and maintenance

- `config/design_spec.yaml` remains the authoritative system specification.
  The separate experiment hold guard is read from
  `config/bootstrap_protected_full18_eval.yaml` (0.439 mV), not silently
  equated to the exact 0.25-LSB value (0.439453125 mV).
- `review/model.yaml`: stable IDs, module membership, premises, formula IDs,
  constraint relationships, steps, coverage and historical circuit bindings.
- `review/evidence.yaml`: small, curated observations and explicit limits from
  reports. These records are NOT automatically guessed from prose. A simulator
  adapter can later emit the same records after its numerical checks.
- `review/source-lock.json`: fingerprints of sources at last deliberate review.
- `review/app/formulas.js`: the single calculation registry shared by the
  browser and Node tests. Display expressions/premises are kept in model.yaml.
- `review/app/`: browser source, intentionally plain JS/CSS/HTML for zero-build
  runtime dependencies. A TypeScript migration is not required to extend data.
- `output/review/`: ignored generated artifacts. Never hand-edit the output.

For each bounded design target, update only the affected step/metric/evidence
records, then rebuild. Keep failed experiments and their scope limits. Read the
changed reports and reconcile the structured record before acknowledging new
fingerprints:

```powershell
.venv/Scripts/python.exe scripts/review/build.py --record-source-lock
```

Do not run that command merely to clear warnings. Without it, changed source
hashes produce visible stale warnings. Each build captures current local source
text and reports whether its reviewed fingerprint matches. If it does not,
historic curated observations are preserved but marked for review. This is
build-time detection, not file watching or live OA synchronization. A stale
system spec also marks all experiment interpretations for review.

Temporary ENOB/sampling-budget scenarios live only in browser memory. They do
not write files, change experimental thresholds, rescore historical runs, or
produce fake new measurements. Refresh resets the scenario. URL hashes preserve
the selected module/view/object, not edited scenario parameters.

## Data contract v1

IDs must be unique within each record type. References must resolve. `parents`
is the acyclic constraint/derivation dependency; it is distinct from module
ownership. `depends_on` is an acyclic workflow dependency, not a pass assertion.

Metric fields: `id`, `module`, `kind`, `formula`, SI `unit`, `display_unit`,
`scale`, `expression`, `premise`, `sources`, `parents`. Kinds are `derived`
(conditional), `allocation` (tentative), and `model` (prediction). System input
specifications are read directly, not duplicated as hardcoded records.

Step fields include purpose, abstraction method, work state, verdict, coverage,
result, next action, metrics, evidence and dependencies. Work state and verdict
are independent: completed work can fail. Allowed verdicts are scoped,
diagnostic, fail and unverified. No unqualified module pass is inferred.

Evidence records require sources, scope and limitations. Observations use
finite SI values with supported units V/F/A/s/count. A scored observation must
bind to a metric with matching units, a historical threshold/comparison, and a
numerically consistent pass/fail gate. Thresholds are not retroactively replaced
when the current budget changes. A record with an
unavailable raw directory remains readable but cannot claim reproducibility.
Current artifact existence is not a waveforms-integrity verification.

Circuit bindings record historical library/cell/view and exported netlist hash,
plus evidence references with the same hash. They are not live OA readbacks.
Canvas is a slot only: no credentials, claim codes, simulated connection or
invented embedding capability are included.

## Focused validation

```powershell
.venv/Scripts/python.exe scripts/review/build.py --check
.venv/Scripts/python.exe verification/review/test_build.py -v
node verification/review/test_formulas.cjs
node --check review/app/app.js
git diff --check
```

Browser acceptance: switch all three views, inspect derivation parents and step
dependencies, open embedded sources, preview/reset budget changes, check the
current audit observations, and verify desktop and narrow-width rendering.
Changing formulas or evidence requires re-running the relevant numerical tests.
