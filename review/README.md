# ADC design review — maintenance guide

As of 2026-10-19 this viewer is explicitly the **historical 10-bit 5+5**
review. Its formulas bind to `config/design_spec_10b.yaml`, so old evidence is
not silently compared against the new eight-bit gates. The active eight-bit
results are reviewed in [the migration report](../docs/eight_bit_flat_migration.md).
Migrating the interactive graph content is a separate presentation task;
changed source-report fingerprints are still reported as needing review.

The HTML in output/review is a generated offline bundle, never an editing target.
There is no framework or backend service to maintain. The compiler resolves and
validates references; the browser renders the compiled snapshot.

## Ownership map

| Concern | Maintained source | Responsibility |
| --- | --- | --- |
| Historical specification / formulas | config/design_spec_10b.yaml, model.yaml, app/formulas.js | Inputs, units, benchmark calculation |
| Experimental records | evidence.yaml | Observations, scope, gate and report references |
| Flow presentation | flows.json | Six actual graphs, nodes, edges, layout and evidence references |
| Node analysis | node-notes.yaml | 2–3 curated reasons and optional figure references |
| Result plots | figures.json | Artifact path, caption/type and reviewed image fingerprint |
| Topology input | topology/bootstrap.cir | Original supplied example, separate from T28 DUT |
| Topology analysis | topology/analysis.json | Functional groups, phases, facts, inference and verification |
| Diagram binding | topology/diagram.json | Static-image coordinates, net strokes and snapshot fingerprints |
| Reviewed baselines | source-lock.json, evidence-baseline.json, topology/connectivity-baseline.json | Explicit last-reviewed state |
| Display conversion | app/presentation.js | Format calculated/evidence values into tokens |
| Rendering | app/app.js, app/topology.js | Graph/dialog interaction; no graph composition |
| Image adapter | app/diagram-static.js | Render semantic device/net selections on a static image |
| Compilation | scripts/review/build.py | Validate references, resolve analysis, embed assets and report impact |

A graph node references analysis by module/node ID, experiments by evidence ID,
figures by figure ID, and the optional circuit entry by topology_topic. The builder
rejects missing references and orphan analysis notes. Browser code does not carry
Bootstrap-specific lists of entry nodes or assemble alternate graphs.

The older flows.yaml and combined topology/bootstrap.yaml were replaced, not kept
as competing sources. Quantitative formula outputs remain in the shared registry.
Historical explanatory prose is still curated, not mechanically proven consistent
with every number. Do not treat impact detection as an automatic reasoning engine.

## Daily workflow

From the ADC repository:

```powershell
.venv/Scripts/python.exe scripts/review/build.py --impact
.venv/Scripts/python.exe scripts/review/build.py --check
.venv/Scripts/python.exe scripts/review/build.py
```

- Edit a phase or circuit explanation in topology/analysis.json.
- Edit graph order or layout in flows.json; keep stable IDs when meaning is unchanged.
- Add a result in evidence.yaml, then bind its ID to the relevant graph nodes.
- Add a plot in figures.json and reference it from node-notes.yaml.
- Change the original circuit only within an authorized circuit task. Run --impact
  before updating its diagram mapping or accepting a new reviewed baseline.
- Review affected conclusions first. Only then update the relevant baseline.
  source-lock.json acknowledges report/spec bytes; evidence-baseline.json stores
  SHA-256 of each record serialized with Python json.dumps(record, sort_keys=True).
  connectivity-baseline.json stores reviewed instance-terminal mappings.
  There is deliberately no command that silently accepts all changed inputs.

--impact is read-only and works even when a topology hash mismatch blocks normal
builds. It reports changed source reports, changed evidence records, affected graph
nodes, changed/neighboring circuit devices, affected topics and diagram-review
requirements. Connectivity impact conservatively includes devices sharing touched
nets. A non-connectivity netlist change requires all topics to be reviewed; an
image-only change requires anchor review, not new electrical conclusions.
The normal UI marks affected nodes as “需复核”. No report documents or filesystem
paths are embedded in the public panel.

## Circuit / Canvas boundary

The sample parser handles this bounded X-device fixture; it is not a general SPICE
parser. D/G/S/B is an explicit interface assumption. Body terminals are retained.
The adapter receives a snapshot plus selected device IDs, net IDs and attention
IDs. It emits device selection via data-device. Coordinates exist only in the
static adapter data, not in the phase/topic analysis.

A future real Canvas adapter must obtain actual Canvas object IDs and verify
connectivity against the netlist before enabling annotations. It must support
selection/highlighting, or report unsupported operations. Do not substitute image
coordinates or fabricated Canvas IDs. No live Canvas connection is implemented.

## Preview and verification

```powershell
.venv/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1 --directory output/review
.venv/Scripts/python.exe verification/review/test_build.py -v
node verification/review/test_formulas.cjs
node --check review/app/app.js
node --check review/app/presentation.js
node --check review/app/topology.js
node --check review/app/diagram-static.js
git diff --check
```

Open http://127.0.0.1:8765. Serve only the generated review directory, not the
repository or PDK. The bundle includes reviewed local images; missing optional
figures omit controls, changed image hashes block the build. Generated files
remain ignored. Private design facts remain private even though the bundle is
self-contained.

Tests include broken references, orphan notes, gate consistency, graph structure,
MN11 gate-change impact and A/B record-change propagation without editing real
inputs. Browser smoke checks cover all module entries, node details, figures and
topology phase/device selection. Conclusions and figure provenance still require
human/agent review; new files are not automatically discovered or approved.
