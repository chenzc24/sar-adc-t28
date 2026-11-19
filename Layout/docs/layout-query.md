# Virtuoso OA Query Guide

Use the existing Bridge to execute a focused, read-only SKILL query in the session that owns the edit. Confirm the library, cell and view against the requested target, including named review and filled views. If the session or target cannot be identified, report that gap. For an explicitly saved view, read it in an isolated background session and identify its source. [Layout manifest](../design/manifest.json)

| Question | OA objects and measurement |
| --- | --- |
| Where is an instance pin? | Find the instance by hierarchy path, read all pin figures from its master terminal, and transform them into the requested coordinate frame. Return layer/purpose and bounds for each landing. |
| How is a net routed on M2? | Read the figures bound to the named net, filter by layer/purpose, and state the hierarchy covered. For path lengths, sum the requested centerlines. Report polygon-only geometry or missing bindings separately when the length cannot be determined. |
| Which differential segment differs? | Use the same scope, units and length convention on both nets. Identify corresponding endpoints and give coordinates for the differing segments. Report ambiguous pairing explicitly. |

After a move or reroute, repeat the query against the active edit. Report its cellview and the coordinates needed to locate the result on the canvas. Use the matching native run reports for an exported revision. [Verification workflow](workflow.md#layout-queries)

## OA Query Interfaces

| Interface | Inputs | Output |
| --- | --- | --- |
| `VirtuosoClient.from_env()` | Optional `profile` and `timeout` | Client using the existing configuration |
| `client.fetch(expr, fields, timeout=30)` | SKILL expression returning a list of objects and a list of property names | `list[dict]`, one row per object |
| `client.fetch_one(expr, fields, timeout=30)` | SKILL expression returning one object and a list of property names | `dict` |
| `layout_read_geometry(lib, cell, view="layout")` | Library, cell, and view | SKILL source to execute |
| `client.execute_skill(code, timeout=30)` | SKILL source | `VirtuosoResult` with `status`, `output`, `errors`, `warnings`, and `metadata` |
| `parse_layout_geometry_output(raw)` | Geometry query `output` | `list[dict]` of shapes and instances |

`fetch` batches and parses property reads. It unquotes strings, converts `nil` to `None` and `t` to `True`, and returns lists as Python lists. Convert numeric strings explicitly before calculating with them. The current implementation returns limited execution status. If a result is unexpectedly empty, use `execute_skill()` to check status and errors for the same query before concluding that an object is absent.

Geometry reads return current-level shapes and instances. Use master queries for nested geometry and targeted queries for pins, vias, mosaics, and nets where the current interface has gaps. Shape fields are `objType/layer/purpose/bbox/points/xy/orient/text`. Instance fields are `name/lib/cell/view/xy/orient/bbox/transform`. The parser converts applicable `bbox/points/xy` values to numbers and returns `transform` as raw text. Scientific notation requires a parser fix. Preserve raw values when encountered.

## Connect and Query Objects

Use the configured bridge Python environment and profile. These examples read the layout currently open for editing and can see unsaved changes. Open the target view first and keep the edit context fixed during the query.

```python
from virtuoso_bridge import ExecutionStatus, VirtuosoClient
from virtuoso_bridge.virtuoso.layout import (
    layout_read_geometry,
    parse_layout_geometry_output,
)

client = VirtuosoClient.from_env()
target = client.fetch_one("geGetEditCellView()", ["libName", "cellName", "viewName"])
if not target or not all(target.get(k) for k in ("libName", "cellName", "viewName")):
    raise RuntimeError("Identify the active layout edit window first")
lib, cell, view = (target[k] for k in ("libName", "cellName", "viewName"))
print({"library": lib, "cell": cell, "view": view, "source": "session"})
```

Use a short batch query for instances, terminal names, and shapes.

```python
instances = client.fetch(
    "geGetEditCellView()~>instances",
    ["name", "libName", "cellName", "viewName", "xy", "orient", "bBox"],
)
terminals = client.fetch(
    "geGetEditCellView()~>terminals", ["name", "direction"],
)
metal = client.fetch(
    'setof(s geGetEditCellView()~>shapes '
    'equal(s~>lpp list("M4" "drawing")))',
    ["objType", "lpp", "bBox", "points"],
)
```

`instances` lists the instances at the current level. `terminals` lists the current cell's terminals. `metal` lists that cell's M4 drawing shapes. Query the master for child-instance geometry and the pin figures for terminal geometry.

Use the geometry helper when you need parsed shape and instance records.

```python
result = client.execute_skill(layout_read_geometry(lib, cell, view=view), timeout=30)
if result.status != ExecutionStatus.SUCCESS:
    raise RuntimeError(result.errors)
geometry = parse_layout_geometry_output(result.output or "")
if any(obj["kind"].startswith("ERROR") for obj in geometry):
    raise RuntimeError(result.output)
```

This helper opens the database by name. In the same Virtuoso session, it can return a view already in memory. For a saved OA snapshot, use the existing isolated background reader and record its input identity. The local helper currently has a cellview reference-release gap. Reuse the upstream fix before running it in long batches.

## Instance Pins and Coordinate Transforms

Select one ordinary instance in the current layout. Read its pin figures from the actual master and transform each bounding box into the parent cell's coordinates. The project's `design/mom.il` uses the same traversal.

```python
result = client.execute_skill('''
let((inst rows)
  inst = car(geGetSelSet())
  unless(inst && inst~>objType == "inst"
    error("Select one ordinary instance first"))
  foreach(term inst~>master~>terminals
    foreach(pin term~>pins
      foreach(fig pin~>figs
        rows = cons(list(inst~>name term~>name fig~>lpp
          dbTransformBBox(fig~>bBox inst~>transform)) rows))))
  reverse(rows)
)
''', timeout=30)
if result.status != ExecutionStatus.SUCCESS:
    raise RuntimeError(result.errors)
print(result.output)
```

`output` is SKILL list text. Each row contains `(instance_name terminal_name layer/purpose parent_bbox)`. Read the output directly for this inspection. `dbTransformBBox()` handles instance translation, rotation, and mirroring. Use `dbTransformPoint()` for points. Compose transforms through each hierarchy level. The result is in top-level coordinates when the parent is the top cell. Read pin geometry from the master for actual pin locations.

## Reporting Query Results

- Record the library, cell, view, source (current session or saved OA), hierarchy path, and coordinate units. Use the current technology library's user units for OA values.
- Use bounding boxes to locate and filter shapes. Report polygon contact, OA net properties, and LVS connectivity with their respective evidence. Use actual geometry and interlayer connectivity rules to check for shorts. Use PEX from the matching revision for parasitic values.
- Reuse the bridge or the project's existing executor for transport, database access, and parsing. Put temporary queries and results under the ignored `work/layout/` directory. Maintain reusable instructions here.

The interface details were checked against the local `virtuoso-bridge-lite` source. The Python snippets can be syntax-checked locally. OA verification requires execution against the target Virtuoso session.
