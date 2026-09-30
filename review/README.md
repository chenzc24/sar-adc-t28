# ADC design review workbench

Local, read-only branch maps: one global map leads to five circuit-module
branches. Each branch combines benchmark constraints, design progress, results
and next actions. Bootstrap has two parallel acquisition/turn-off chains.
Explanations expand within nodes; Canvas is a placeholder inside each module.
No separate theory/progress tabs, detail panel, document links or report viewer.
The app composes existing curated flow nodes into these consolidated maps;
numerical facts still come from the common calculation/evidence registry.

Each module node has 2–3 visible analysis points in `node-notes.yaml`, keyed by
module/node ID. Optional figure IDs refer to `figures.json`: explicit artifact
path, reviewed SHA-256, plot type and scope caption. The builder embeds only
available reviewed PNG/restricted SVG bytes as image data URLs, so no artifact
directory is served. Changed images fail validation; missing images omit the
entry instead of breaking navigation. Re-review before updating a figure hash.
Analytical envelopes are explicitly not transistor simulation results. The
figure dialog supports keyboard opening, Escape/close, and return to the node.

## Static topology linkage sample

Sampling nodes open the user-supplied Bootstrap sample from `topology/`.
The original .cir and PNG remain separate from the T28 design DUT. YAML stores
manual image anchors, functional groups, phases and typed analysis. `net0` has
display alias GBOOT only; original names and body terminals are retained.
The builder parses this bounded example (not a general SPICE importer), checks
anchor/reference coverage and embeds the diagram plus normalized pin mapping.
D/G/S/B remains an explicit model-interface assumption. Blue device outlines are
attention markers, not simulated switch states; orange net segments are existing
connections, not current paths. Device selection lists its related topics.
Phase selection clears topic highlights; topic selection selects its stated phase.
Netlist/image fingerprints identify the snapshot, not an LVS certificate.
No real Canvas IDs or live connection are claimed. A future adapter must bind
the same instance/net IDs to actual Canvas objects and verify the imported graph
before applying annotations; it must not identify a diagram by title alone.

## Build and open

From the ADC repository in PowerShell:

```powershell
.venv/Scripts/python.exe scripts/review/build.py
Start-Process output/review/index.html
```

The output embeds CSS, JavaScript and extracted structured facts, with no server
or CDN dependency. Direct file preview is not permitted by the in-app browser;
use a normal browser or the tested loopback preview. To preview in a
browser which only accepts HTTP, serve **only the generated review directory**:

```powershell
.venv/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1 --directory output/review
```

Open `http://127.0.0.1:8765`. This serves extracted design facts, not raw reports,
model/OA files or document paths. Do not bind to a public interface. Stop the
preview server when unused. Extracted facts still contain private project
information: review before sharing outside the project.

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
- `review/flows.yaml`: concise graph nodes, typed arrows, grid placement and
  explicit circuit block ownership. Numerical tokens use the calculation
  registry or curated observations; prose must be self-contained.
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

Do not run that command merely to clear warnings. Changed source hashes produce
a short stale warning, but paths, hashes and source documents stay behind the
build boundary. `public_snapshot` strips them before HTML and data.json are
written. Curated observations remain unchanged. This is build-time detection,
not file watching or live OA synchronization.

The simplified UI intentionally removes scenario controls, provenance panels,
raw source dialogs and the sidebar. The calculation registry still supports
scenario unit tests. URL hashes identify block/view; legacy dashboard links
open the global flow orientation.

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

Flow nodes must name known blocks; edge endpoints must exist and flow diagrams
must be acyclic. Allocation and pending-work arrows are dashed. Solid arrows
represent the stated derivation or workflow relationship, not pass assertions.

Browser acceptance: open all five module branches and return to the overview,
check arrow endpoints and fork/merge relationships, expand node explanations
and the module Canvas placeholder, and verify no document links/viewers.
Narrow screens scroll diagrams locally rather than shrinking text illegibly.
Changing formulas or evidence requires re-running the relevant numerical tests.
