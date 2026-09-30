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
        require((path.is_relative_to(ROOT / 'output') and not path.is_relative_to(ROOT / 'output/review'))
                or path.is_relative_to(REVIEW / 'assets'), 'unsafe figure path')
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


def resolve_graphs(flows, notes, figures, evidence, topology):
    """Compile maintained references into a render-only graph payload."""
    result = deepcopy(flows)
    validate_flows(result)
    topics = {t['id'] for t in topology['topics']}
    records = {e['id']: e for e in evidence}
    used = set()
    for name, graph in result['graphs'].items():
        require(graph.get('layout') in {'overview', 'branch', 'chain'}, 'unknown graph layout')
        for node in graph['nodes']:
            require(all(e in records for e in node['evidence']), 'unknown graph evidence')
            require(not node.get('focus') or node['focus'] in result['graphs'], 'unknown graph destination')
            variant = node.get('topology_variant')
            require(not variant or variant in topology.get('variants', {}), 'unknown topology variant')
            node_topics = {t['id'] for t in topology['variants'][variant]['topics']} if variant else topics
            require(not node.get('topology_topic') or node['topology_topic'] in node_topics, 'unknown topology topic')
            if name != 'all':
                ref = node.get('analysis')
                require(ref in notes, 'missing graph analysis')
                used.add(ref)
                node.update(deepcopy(notes[ref]))
            require(all(f in figures for f in node.get('figures', [])), 'unknown graph figure')
            node['needs_review'] = any(records[e].get('stale', False) for e in node['evidence'])
    require(used == set(notes), 'orphan node analysis')
    return result


def parse_topology_netlist(netlist):
    """Bounded X-device / primitive-C fixture parser, not a general SPICE parser."""
    devices = {}
    for line in netlist.splitlines():
        fields = line.split()
        if not fields or not fields[0].upper().startswith(('X', 'C')):
            continue
        capacitor = fields[0].upper().startswith(('XC', 'C'))
        terminals = ['A', 'B'] if capacitor else ['D', 'G', 'S', 'B']
        require(len(fields) > len(terminals) + 1, 'incomplete topology instance')
        require(fields[0] not in devices, 'duplicate topology instance')
        devices[fields[0]] = dict(zip(terminals, fields[1:1 + len(terminals)]))
    return devices


def load_topology(variant=None):
    require(variant in {None, 'isolated'}, 'unknown topology variant')
    folder = REVIEW / 'topology'
    if variant:
        folder = folder / variant
    netlist = (folder / 'bootstrap.cir').read_text(encoding='utf-8')
    topology = {**read_yaml(folder / 'analysis.json'), **read_yaml(folder / 'diagram.json')}
    require(hashlib.sha256(netlist.encode('utf-8')).hexdigest() == topology.pop('netlist_sha256'), 'topology netlist changed: re-review mapping')
    devices = parse_topology_netlist(netlist)
    require(set(devices) == set(topology['anchors']), 'topology anchor mismatch')
    nets = {net for pins in devices.values() for net in pins.values()}
    for item in topology['groups'] + topology['phases'] + topology['topics']:
        require(set(item['devices']) <= set(devices), 'unknown topology device')
        require(set(item.get('nets', [])) <= nets, 'unknown topology net')
    require(set(topology['net_marks']) <= nets, 'unknown overlay net')
    require(all(t['phase'] in {p['id'] for p in topology['phases']} for t in topology['topics']), 'unknown topology phase')
    for x, y, w, h in topology['anchors'].values():
        require(0 <= x < x+w <= topology['width'] and 0 <= y < y+h <= topology['height'], 'invalid image anchor')
    raw = (folder / 'bootstrap.png').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == topology.pop('image_sha256'), 'topology image changed: re-review anchors')
    topology.update(devices=devices, image='data:image/png;base64,' + base64.b64encode(raw).decode('ascii'),
                    revision=hashlib.sha256(netlist.encode('utf-8')).hexdigest()[:12],
                    image_revision=hashlib.sha256(raw).hexdigest()[:12])
    if variant is None:
        topology['variants'] = {'isolated': load_topology('isolated')}
    return topology


def topology_impact(before, after, topology, netlist_changed=False, image_changed=False):
    changed = sorted(d for d in set(before) | set(after) if before.get(d) != after.get(d))
    changed_nets = {n for d in changed for pins in [before.get(d, {}), after.get(d, {})] for n in pins.values()}
    # Conservatively include consumers on touched nets, not only the edited device.
    touched = set(changed) | {d for d, pins in {**before, **after}.items() if set(pins.values()) & changed_nets}
    non_connectivity = netlist_changed and not changed
    topics = [t['id'] for t in topology['topics'] if non_connectivity or set(t['devices']) & touched or set(t['nets']) & changed_nets]
    return {'changed_devices': changed, 'related_devices': sorted(touched),
            'affected_topics': topics, 'image_mapping_needs_review': image_changed or bool(changed),
            'non_connectivity_change': non_connectivity}


def impact_report(model, records, flows, lock):
    changed_sources = [s for s, path in model['sources'].items()
                       if hashlib.sha256(source_path(path).read_bytes()).hexdigest() != lock.get('sources', {}).get(s, {}).get('sha256')]
    reviewed = json.loads((REVIEW / 'evidence-baseline.json').read_text(encoding='utf-8'))
    changed_records = [e['id'] for e in records if hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest() != reviewed.get(e['id'])]
    changed_records += sorted(set(reviewed) - {e['id'] for e in records})
    evidence = [e['id'] for e in records if set(e['sources']) & set(changed_sources) or 'spec' in changed_sources or e['id'] in changed_records]
    evidence = sorted(set(evidence) | set(changed_records))
    folder = REVIEW / 'topology'
    topology = {**read_yaml(folder / 'analysis.json'), **read_yaml(folder / 'diagram.json')}
    baseline = json.loads((folder / 'connectivity-baseline.json').read_text(encoding='utf-8'))
    text = (folder / 'bootstrap.cir').read_text(encoding='utf-8')
    impact = topology_impact(baseline, parse_topology_netlist(text), topology,
                            hashlib.sha256(text.encode('utf-8')).hexdigest() != topology['netlist_sha256'],
                            hashlib.sha256((folder / 'bootstrap.png').read_bytes()).hexdigest() != topology['image_sha256'])
    variant_changes = {}
    for variant in {'isolated'}:
        variant_folder = folder / variant
        binding = read_yaml(variant_folder / 'diagram.json')
        variant_changes[variant] = (
            hashlib.sha256((variant_folder / 'bootstrap.cir').read_text(encoding='utf-8').encode()).hexdigest() != binding['netlist_sha256']
            or hashlib.sha256((variant_folder / 'bootstrap.png').read_bytes()).hexdigest() != binding['image_sha256'])
    affected = [f'{g}/{n["id"]}' for g, graph in flows['graphs'].items() for n in graph['nodes']
                if set(n['evidence']) & set(evidence) or n.get('topology_topic') in impact['affected_topics']
                or impact['image_mapping_needs_review'] and n.get('topology_topic')
                or variant_changes.get(n.get('topology_variant'), False)]
    return {'changed_sources': changed_sources, 'changed_records': changed_records, 'affected_evidence': evidence,
            'affected_nodes': affected, 'topology': impact, 'topology_variants_changed': variant_changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-source-lock", action="store_true", help="Only after reviewing source changes: acknowledge current source fingerprints")
    parser.add_argument("--check", action="store_true", help="Validate without writing a snapshot")
    parser.add_argument('--impact', action='store_true', help='Read-only change impact report; does not accept new baselines')
    args = parser.parse_args()
    model, evidence = read_yaml(REVIEW / "model.yaml"), read_yaml(REVIEW / "evidence.yaml")
    validate(model, evidence)
    flows = read_yaml(REVIEW / "flows.json")
    validate_flows(flows)
    lock_path = REVIEW / "source-lock.json"
    if args.impact:
        require(not args.record_source_lock, '--impact cannot acknowledge source changes')
        print(json.dumps(impact_report(model, evidence['records'], flows, json.loads(lock_path.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))
        return
    if args.record_source_lock:
        require(not args.check, "--check cannot record source lock")
        lock = {"schema_version": 1, "sources": {k: {"path": v, "sha256": hashlib.sha256(source_path(v).read_bytes()).hexdigest()} for k, v in model["sources"].items()}}
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    impact = impact_report(model, evidence['records'], flows, lock)
    data = snapshot(model, evidence, lock)
    public = public_snapshot(data, flows)
    public['figures'] = load_figures(json.loads((REVIEW / 'figures.json').read_text(encoding='utf-8')))
    public['node_notes'] = load_node_notes(public['figures'])
    public['topology'] = load_topology()
    public['flows'] = resolve_graphs(flows, public['node_notes'], public['figures'], public['evidence'], public['topology'])
    for graph_id, graph in public['flows']['graphs'].items():
        for node in graph['nodes']:
            node['needs_review'] |= f'{graph_id}/{node["id"]}' in impact['affected_nodes']
    public['meta']['needs_review'] |= bool(impact['affected_nodes'])
    public.pop('node_notes')
    if not args.check:
        out = ROOT / "output" / "review"
        out.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(public, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        template = (REVIEW / "app" / "index.html").read_text(encoding="utf-8")
        assets = {"__STYLE__": "style.css", "__FORMULAS__": "formulas.js", "__APP__": "app.js", "__TOPOLOGY__": "topology.js", "__PRESENTATION__": "presentation.js", "__DIAGRAM__": "diagram-static.js"}
        for placeholder, filename in assets.items():
            template = template.replace(placeholder, (REVIEW / "app" / filename).read_text(encoding="utf-8"))
        template = template.replace("__DATA__", serialized)
        (out / "index.html").write_text(template, encoding="utf-8")
        (out / "data.json").write_text(json.dumps(public, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"Built {out / 'index.html'}")
    print(f"Validated {len(model['metrics'])} metrics, {len(model['steps'])} steps, {len(evidence['records'])} evidence records")
    print(f"Stale source references: {data['meta']['stale_sources'] or 'none'}; OA/Canvas not connected")
    print(f"Nodes requiring review: {impact['affected_nodes'] or 'none'}")


if __name__ == "__main__":
    main()
