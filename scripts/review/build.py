"""Build a self-contained review snapshot; never touch OA or design sources."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "review"
KINDS = {"derived", "allocation", "model"}
WORK = {"complete", "planned", "blocked", "active"}
VERDICTS = {"scoped", "fail", "diagnostic", "unverified"}
UNITS = {"V", "F", "A", "s", "count"}


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def by_id(items, name):
    require(isinstance(items, list) and bool(items), f"{name}: expected nonempty list")
    result = {}
    for item in items:
        ident = item.get("id")
        require(isinstance(ident, str) and ident and ident not in result, f"{name}: missing/duplicate id {ident}")
        result[ident] = item
    return result


def acyclic(items, key):
    visiting, visited = set(), set()

    def visit(ident):
        require(ident not in visiting, f"cycle: {ident}")
        if ident in visited:
            return
        visiting.add(ident)
        for parent in items[ident][key]:
            require(parent in items, f"unknown dependency: {parent}")
            visit(parent)
        visiting.remove(ident)
        visited.add(ident)
    for ident in items:
        visit(ident)


def source_path(relative):
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT), f"source escapes repository: {relative}")
    require(path.suffix in {".md", ".yaml"} and path.is_file(), f"missing/unsupported source: {relative}")
    require(path.relative_to(ROOT).parts[0] in {"docs", "config"}, f"unsupported source area: {relative}")
    return path


def validate(model, evidence):
    require(model["schema_version"] == evidence["schema_version"] == 1, "unsupported schema")
    modules = by_id(model["modules"], "modules")
    metrics = by_id(model["metrics"], "metrics")
    steps = by_id(model["steps"], "steps")
    records = by_id(evidence["records"], "evidence")
    require(model["focus"] in steps, "unknown focus")
    for key, path in model["sources"].items():
        require(isinstance(key, str), "bad source id")
        source_path(path)
    for metric in metrics.values():
        require(metric["module"] in modules and metric["kind"] in KINDS, f"metric: {metric['id']}")
        require(metric["unit"] in UNITS, "unsupported metric unit")
        require(isinstance(metric["scale"], (int, float)) and metric["scale"] > 0, "invalid display scale")
        require(all(s in model["sources"] for s in metric["sources"]), "unknown metric source")
        require(metric["sources"] and metric["premise"], "metric requires premises and sources")
    acyclic(metrics, "parents")
    for step in steps.values():
        require(step["module"] in modules and step["work"] in WORK and step["verdict"] in VERDICTS, "invalid step state")
        require(all(m in metrics for m in step["metrics"]), "unknown step metric")
        require(all(e in records for e in step["evidence"]), "unknown step evidence")
        require(step["verdict"] == "unverified" or bool(step["evidence"]), "claim requires evidence")
        require(step["coverage"] and step["method"] and step["next"], "step requires scope/method/next")
    acyclic(steps, "depends_on")
    for record in records.values():
        require(record["sources"] and all(s in model["sources"] for s in record["sources"]), "unknown evidence source")
        require(record["scope"] and record["limitations"], "evidence requires scope/limits")
        for obs in record["observations"]:
            require(obs["unit"] in UNITS and isinstance(obs["value"], (int, float)) and math.isfinite(obs["value"]), "bad observation")
            if "metric" in obs:
                require(obs["metric"] in metrics and obs["unit"] == metrics[obs["metric"]]["unit"], "observation unit/reference mismatch")
                require(obs.get("gate") in {"pass", "fail"}, "observation requires gate verdict")
                require(obs.get("comparison") == "abs_lt" and isinstance(obs.get("limit"), (int, float)) and math.isfinite(obs["limit"]) and obs["limit"] > 0, "observation requires a historical threshold")
                require(obs["gate"] == ("pass" if abs(obs["value"]) < obs["limit"] else "fail"), "gate contradicts historical observation/threshold")
        if "artifact_path" in record:
            p = (ROOT / record["artifact_path"]).resolve()
            require(p.is_relative_to(ROOT / "output"), "raw artifact outside output")
        if "netlist_sha256" in record:
            require(len(record["netlist_sha256"]) == 64 and all(c in "0123456789abcdef" for c in record["netlist_sha256"]), "bad netlist hash")
    for binding in model["circuits"]:
        require(all(m in modules for m in binding["modules"]), "unknown circuit module")
        require(binding["evidence"] and all(e in records for e in binding["evidence"]), "unknown circuit evidence")
        require(any(records[e].get("netlist_sha256") == binding["netlist_sha256"] for e in binding["evidence"]), "circuit/evidence hash mismatch")


def validate_flows(flows):
    require(flows["schema_version"] == 1, "unsupported flow schema")
    blocks = by_id(flows["blocks"], "blocks")
    for graph in flows["graphs"].values():
        nodes = by_id(graph["nodes"], "flow nodes")
        grid = set()
        for node in nodes.values():
            require(all(b in blocks for b in node["blocks"]), "unknown flow block")
            require(node["row"] > 0 and node["col"] > 0 and node["col"] + node.get("span", 1) - 1 <= graph["columns"], "invalid flow position")
            for col in range(node["col"], node["col"] + node.get("span", 1)):
                require((node["row"], col) not in grid, "overlapping flow nodes")
                grid.add((node["row"], col))
        dependencies = {ident: {"parents": []} for ident in nodes}
        for edge in graph["edges"]:
            require(edge["from"] in nodes and edge["to"] in nodes, "unknown flow edge endpoint")
            require(edge["kind"] in {"derive", "allocate", "next", "pending"}, "unknown flow edge kind")
            dependencies[edge["to"]]["parents"].append(edge["from"])
        acyclic(dependencies, "parents")


def public_snapshot(data, flows):
    """Extract panel facts, not repository documents, source paths or hashes."""
    public = deepcopy(data)
    public.pop("sources")
    public["model"].pop("sources")
    public["model"].pop("circuits")
    for metric in public["model"]["metrics"]:
        metric.pop("sources")
    for record in public["evidence"]:
        for key in ("sources", "artifact_path", "artifact_available", "netlist_sha256"):
            record.pop(key, None)
    public["meta"] = {"reviewed_at": data["model"]["reviewed_at"], "needs_review": bool(data["meta"]["stale_sources"])}
    public["flows"] = flows
    return public


def snapshot(model, evidence, lock):
    sources = {}
    for ident, relative in model["sources"].items():
        path = source_path(relative)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        old = lock.get("sources", {}).get(ident, {})
        sources[ident] = {"path": relative, "sha256": digest, "reviewed_sha256": old.get("sha256"),
                          "stale": old.get("sha256") != digest or old.get("path") != relative,
                          "text": path.read_text(encoding="utf-8")}
    for record in evidence["records"]:
        record["stale"] = any(sources[s]["stale"] for s in record["sources"]) or sources["spec"]["stale"]
        record["artifact_available"] = bool(record.get("artifact_path") and (ROOT / record["artifact_path"]).is_dir())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    spec = read_yaml(source_path(model["sources"]["spec"]))
    full18 = read_yaml(source_path(model["sources"]["full18_config"]))
    return {"model": model, "evidence": evidence["records"], "sources": sources, "spec": spec,
            "context": {"temperature_k": model["assumptions"]["temperature_k"],
                        "hold_limit_v": full18["conditions"]["raw_error_limit_v"]},
            "meta": {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "source_commit": commit, "stale_sources": [s for s in sources if sources[s]["stale"]],
                     "model_sha256": hashlib.sha256((REVIEW / "model.yaml").read_bytes()).hexdigest(),
                     "evidence_sha256": hashlib.sha256((REVIEW / "evidence.yaml").read_bytes()).hexdigest()}}


def load_figures(records):
    """Embed only reviewed image bytes; never expose artifact filesystem paths."""
    figures = {}
    for record in records:
        ident = record['id']
        require(ident not in figures, 'duplicate figure')
        path = (ROOT / record['path']).resolve()
        require(path.is_relative_to(ROOT / 'output') and not path.is_relative_to(ROOT / 'output/review'), 'unsafe figure path')
        require(path.suffix in {'.png', '.svg'}, 'unsupported figure format')
        public = {k: record[k] for k in ('title', 'kind', 'caption')}
        public['available'] = path.is_file()
        if path.is_file():
            raw = path.read_bytes()
            require(len(raw) <= 5_000_000, 'figure too large')
            require(hashlib.sha256(raw).hexdigest() == record['sha256'], 'figure changed since review')
            if path.suffix == '.png':
                require(raw.startswith(b'\x89PNG\r\n\x1a\n'), 'invalid PNG')
                mime = 'image/png'
            else:
                require(b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw, 'unsafe SVG')
                root = ET.fromstring(raw)
                allowed = {'svg', 'rect', 'style', 'text', 'line', 'polyline', 'path', 'g', 'circle', 'title', 'desc'}
                for element in root.iter():
                    require(element.tag.split('}')[-1] in allowed, 'unsafe SVG element')
                    require(all(not k.lower().startswith('on') and 'href' not in k.lower() for k in element.attrib), 'unsafe SVG attribute')
                lower = raw.lower()
                require(b'url(' not in lower and b'@import' not in lower, 'unsafe SVG resource')
                mime = 'image/svg+xml'
            public['src'] = 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii')
        figures[ident] = public
    return figures


def load_node_notes(figures):
    notes = read_yaml(REVIEW / 'node-notes.yaml')['nodes']
    for key, note in notes.items():
        require('/' in key and 2 <= len(note['reasons']) <= 3, 'node requires 2–3 reasons')
        require(all(isinstance(s, str) and s for s in note['reasons']), 'empty node reason')
        require(all(f in figures for f in note.get('figures', [])), 'unknown node figure')
    return notes


def load_topology():
    folder = REVIEW / 'topology'
    netlist = (folder / 'bootstrap.cir').read_text(encoding='utf-8')
    topology = read_yaml(folder / 'bootstrap.yaml')
    require(hashlib.sha256(netlist.encode('utf-8')).hexdigest() == topology.pop('netlist_sha256'), 'topology netlist changed: re-review mapping')
    devices = {}
    for line in netlist.splitlines():
        fields = line.split()
        if not fields or not fields[0].startswith('X'):
            continue
        capacitor = fields[0].startswith('XC')
        terminals = ['A', 'B'] if capacitor else ['D', 'G', 'S', 'B']
        require(fields[0] not in devices, 'duplicate topology instance')
        devices[fields[0]] = dict(zip(terminals, fields[1:1 + len(terminals)]))
    require(set(devices) == set(topology['anchors']), 'topology anchor mismatch')
    nets = {net for pins in devices.values() for net in pins.values()}
    for item in topology['groups'] + topology['phases'] + topology['topics']:
        require(set(item['devices']) <= set(devices), 'unknown topology device')
        require(set(item.get('nets', [])) <= nets, 'unknown topology net')
    require(set(topology['net_marks']) <= nets, 'unknown overlay net')
    require(all(t['phase'] in {p['id'] for p in topology['phases']} for t in topology['topics']), 'unknown topology phase')
    for x, y, w, h in topology['anchors'].values():
        require(0 <= x < x+w <= 1034 and 0 <= y < y+h <= 675, 'invalid image anchor')
    raw = (folder / 'bootstrap.png').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == topology.pop('image_sha256'), 'topology image changed: re-review anchors')
    topology.update(devices=devices, image='data:image/png;base64,' + base64.b64encode(raw).decode('ascii'),
                    revision=hashlib.sha256(netlist.encode('utf-8')).hexdigest()[:12],
                    image_revision=hashlib.sha256(raw).hexdigest()[:12])
    return topology


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-source-lock", action="store_true", help="Only after reviewing source changes: acknowledge current source fingerprints")
    parser.add_argument("--check", action="store_true", help="Validate without writing a snapshot")
    args = parser.parse_args()
    model, evidence = read_yaml(REVIEW / "model.yaml"), read_yaml(REVIEW / "evidence.yaml")
    validate(model, evidence)
    flows = read_yaml(REVIEW / "flows.yaml")
    validate_flows(flows)
    lock_path = REVIEW / "source-lock.json"
    if args.record_source_lock:
        require(not args.check, "--check cannot record source lock")
        lock = {"schema_version": 1, "sources": {k: {"path": v, "sha256": hashlib.sha256(source_path(v).read_bytes()).hexdigest()} for k, v in model["sources"].items()}}
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    data = snapshot(model, evidence, lock)
    public = public_snapshot(data, flows)
    public['figures'] = load_figures(json.loads((REVIEW / 'figures.json').read_text(encoding='utf-8')))
    public['node_notes'] = load_node_notes(public['figures'])
    public['topology'] = load_topology()
    if not args.check:
        out = ROOT / "output" / "review"
        out.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(public, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        template = (REVIEW / "app" / "index.html").read_text(encoding="utf-8")
        assets = {"__STYLE__": "style.css", "__FORMULAS__": "formulas.js", "__APP__": "app.js", "__TOPOLOGY__": "topology.js"}
        for placeholder, filename in assets.items():
            template = template.replace(placeholder, (REVIEW / "app" / filename).read_text(encoding="utf-8"))
        template = template.replace("__DATA__", serialized)
        (out / "index.html").write_text(template, encoding="utf-8")
        (out / "data.json").write_text(json.dumps(public, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"Built {out / 'index.html'}")
    print(f"Validated {len(model['metrics'])} metrics, {len(model['steps'])} steps, {len(evidence['records'])} evidence records")
    print(f"Stale source references: {data['meta']['stale_sources'] or 'none'}; OA/Canvas not connected")


if __name__ == "__main__":
    main()
