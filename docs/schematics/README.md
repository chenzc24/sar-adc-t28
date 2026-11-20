# RNL Schematics

The generated views follow the current Spectre design: the single-edge SAR, its native reference decoder and the top. The drawing manifest records the exact source files. [Current DUT](../../design/dut.scs) · [Drawing manifest](../../design/rnl/manifest.json)

The workspace contains 60 views: 19 native circuit definitions, 7 standalone fixtures and 34 external interfaces. Native files with authored drawing records are included directly. The viewer generates display drawings for native source files without drawing records and verifies that their electrical statements are preserved. Open sar8_se_window for the DEL250 chain and its registered tap multiplexers, sar8_se_timing for the phase counter and comparator clock, and sar8_se_ctrl for the sticky tap selects. [Netlist index](../../design/README.md) · [Shared symbols](../../design/rnl/sar8.rnl)

## View

Run this command from the repository root.

```powershell
.venv/Scripts/python.exe -m tools.saradc draw --serve
```

Open <http://127.0.0.1:8875/>. Select the top level or a module on the left. Double-click a subcircuit in the schematic or use the instance button below to descend. For overlapping objects, select the device and use the control labeled “进入子电路” to enter the subcircuit. The right pane provides zoom, fit, and access to the complete official viewer. You can view the source netlist or export a single SVG or a self-contained RNL netlist. The presentation netlist includes drawing symbols and opens independently. Use the original netlist for simulation.

The offline page embeds all SVGs for browsing the hierarchy. Start the local service for the official viewer's pan, zoom, and editing functions. Export browser edits and check them against the source files. Matching net names indicate connectivity. Crossing lines connect where a junction is shown. [Offline viewer](index.html)

## Edit and Update

```powershell
# Regenerate views and digests after changing source netlists or drawing annotations.
.venv/Scripts/python.exe -m tools.saradc draw
# Check the current views against the actual sources.
.venv/Scripts/python.exe -m tools.saradc draw --check
```

By default, `draw` preserves manually edited RNL in source files. Use `draw --annotate` to reapply the layout generator. It replaces only the annotations between the `BEGIN/END SARADC RNL` markers. `rnl.py` defines and generates the shared symbols. [Layout generator](../../tools/saradc/rnl_layouts.py) · [Symbol generator](../../tools/saradc/rnl.py)

`current.scs` includes the annotated module sources and the generated display drawings. `export.scs` is the standalone download. The manifest records SHA256 digests for the actual sources, generator, and drawing outputs, together with the RNL checks. Apply drawing edits to the current text design. [Current includes](../../design/rnl/current.scs) · [Standalone export](../../design/rnl/export.scs) · [Manifest](../../design/rnl/manifest.json)

## Candidates and Scope

The candidate registry provides module-page selectors. A candidate is drawn from its actual netlist. A topology without an authored arrangement is labeled as automatic layout. Display selection controls only what is shown. Use the candidate registration and adoption workflow to change simulation defaults. [Candidate registry](../../specs/candidates.json) · [Candidate conventions](../../design/xtor/README.md)

Local wrappers can be expanded by hierarchy. External standard-cell, PDK, and Verilog-A objects display their actual port interfaces. Use RNL for the text-design view and native evidence for OA synchronization, layout completion, and electrical qualification.

## Tools and Provenance

Generation uses the official RNL 0.5.5 CLI. Install it on PATH, use the local `work/tools/rnl-0.5.5/cli/rnl.exe`, or provide the same version through `--rnl PATH`. The official viewer 0.5.3 and core 0.5.5 are cached under ignored `work/tools/` according to the per-file lock. The first launch fetches the official assets and later launches verify the cache. If an upstream digest differs, retain the failure and update the version explicitly. The service binds to loopback and serves the drawing inputs listed in the manifest. [Viewer lock](../../tools/saradc/rnl_viewer.lock.json)

The drawing arrangement and hierarchy take reference from the ADC-12b-100M RNL sources. Devices, parameters, and connectivity come from this project's design. [Reference schematic sources](https://github.com/many-question/ADC-12b-100M/tree/10ef811bf94fbc928992aec2520382304390a960/design) · [RNL tooling, format, and license](https://github.com/rich-netlist/rnl)
