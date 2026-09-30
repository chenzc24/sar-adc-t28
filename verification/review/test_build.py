"""Focused checks for the review data contract, not a simulator regression."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review_build", ROOT / "scripts/review/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.model = build.read_yaml(ROOT / "review/model.yaml")
        self.evidence = build.read_yaml(ROOT / "review/evidence.yaml")

    def test_valid_model(self):
        build.validate(self.model, self.evidence)

    def test_compiled_graph_references(self):
        flows = build.read_yaml(ROOT / 'review/flows.json')
        figures = build.load_figures(json.loads((ROOT / 'review/figures.json').read_text(encoding='utf-8')))
        notes = build.load_node_notes(figures)
        topology = build.load_topology()
        compiled = build.resolve_graphs(flows, notes, figures, self.evidence['records'], topology)
        self.assertEqual({k:len(g['nodes']) for k,g in compiled['graphs'].items()},
                         {'all':7, 'sampling':8, 'cdac':4, 'reference':4, 'comparator':4, 'clock':4})
        for field, value, message in [('evidence',['missing'],'unknown graph evidence'),
                                      ('analysis','missing','missing graph analysis'),
                                      ('topology_topic','missing','unknown topology topic')]:
            bad = deepcopy(flows)
            bad['graphs']['sampling']['nodes'][0][field] = value
            with self.assertRaisesRegex(ValueError, message):
                build.resolve_graphs(bad, notes, figures, self.evidence['records'], topology)
        orphan = deepcopy(notes)
        orphan['sampling/unused'] = {'reasons':['one','two']}
        with self.assertRaisesRegex(ValueError, 'orphan'):
            build.resolve_graphs(flows, orphan, figures, self.evidence['records'], topology)

    def test_terminal_change_impact_without_mutating_fixture(self):
        topology = build.load_topology()
        before = topology['devices']
        after = deepcopy(before)
        after['XMN11']['G'] = 'independent_gate'
        impact = build.topology_impact(before, after, topology, netlist_changed=True)
        self.assertEqual(impact['changed_devices'], ['XMN11'])
        self.assertEqual(set(impact['affected_topics']), {'bootstrap','shared','reset'})
        self.assertTrue(impact['image_mapping_needs_review'])
        self.assertEqual(before['XMN11']['G'], 'net0')

    def test_evidence_change_reaches_related_nodes(self):
        records = deepcopy(self.evidence['records'])
        next(r for r in records if r['id']=='fast_ab')['observations'][0]['value'] = -0.005
        report = build.impact_report(self.model, records, build.read_yaml(ROOT/'review/flows.json'),
                                    json.loads((ROOT/'review/source-lock.json').read_text(encoding='utf-8')))
        self.assertIn('fast_ab', report['changed_records'])
        self.assertIn('sampling/input_path', report['affected_nodes'])
        self.assertIn('all/sampling', report['affected_nodes'])
        self.assertNotIn('clock/result', report['affected_nodes'])

    def test_image_and_parameter_change_have_distinct_impact(self):
        topology = build.load_topology()
        devices = topology['devices']
        image = build.topology_impact(devices, devices, topology, image_changed=True)
        self.assertTrue(image['image_mapping_needs_review'])
        self.assertEqual(image['affected_topics'], [])
        parameter = build.topology_impact(devices, devices, topology, netlist_changed=True)
        self.assertTrue(parameter['non_connectivity_change'])
        self.assertEqual(len(parameter['affected_topics']), 3)

    def test_topology_sample_binding_and_body_terminals(self):
        topology = build.load_topology()
        self.assertEqual(len(topology['devices']), 15)
        self.assertEqual(len(topology['phases']), 4)
        self.assertEqual(len(topology['topics']), 3)
        self.assertEqual(topology['devices']['XMN11'], {'D':'VOUT', 'G':'net0', 'S':'VIN', 'B':'VIN'})
        self.assertEqual(topology['devices']['XMN9']['B'], 'VIN')
        self.assertEqual(topology['devices']['XMP8']['B'], 'net0')
        members = [d for g in topology['groups'] for d in g['devices']]
        self.assertEqual(len(members), len(set(members)))
        self.assertEqual(set(members), set(topology['devices']))
        for topic in topology['topics']:
            for key in ('fact', 'inference', 'verify'):
                self.assertTrue(topic[key])

    def test_reviewed_figures_and_notes(self):
        records = json.loads((ROOT / 'review/figures.json').read_text(encoding='utf-8'))
        figures = build.load_figures(records)
        notes = build.load_node_notes(figures)
        self.assertEqual(len(notes), 24)
        self.assertEqual(len(figures), 7)
        for figure in figures.values():
            self.assertNotIn('path', figure)
            self.assertNotIn('sha256', figure)
            if figure['available']:
                self.assertTrue(figure['src'].startswith('data:image/'))

    def test_missing_figure_has_no_image_source(self):
        record = json.loads((ROOT / 'review/figures.json').read_text(encoding='utf-8'))[0]
        record['path'] = 'output/review-test-intentionally-missing.png'
        figure = build.load_figures([record])[record['id']]
        self.assertFalse(figure['available'])
        self.assertNotIn('src', figure)

    def test_unsafe_figure_path_rejected(self):
        record = json.loads((ROOT / 'review/figures.json').read_text(encoding='utf-8'))[0]
        record['path'] = '../outside.png'
        with self.assertRaisesRegex(ValueError, 'unsafe figure path'):
            build.load_figures([record])

    def test_changed_figure_rejected(self):
        record = json.loads((ROOT / 'review/figures.json').read_text(encoding='utf-8'))[0]
        if not (ROOT / record['path']).is_file():
            self.skipTest('optional local plot absent')
        record['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'changed since review'):
            build.load_figures([record])

    def test_duplicate_id_rejected(self):
        self.model["metrics"].append(deepcopy(self.model["metrics"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build.validate(self.model, self.evidence)

    def test_cycle_rejected(self):
        self.model["metrics"][0]["parents"] = ["analog"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            build.validate(self.model, self.evidence)

    def test_unknown_reference_rejected(self):
        self.model["steps"][0]["evidence"] = ["not-a-real-run"]
        with self.assertRaisesRegex(ValueError, "unknown step evidence"):
            build.validate(self.model, self.evidence)

    def test_no_evidence_no_claim(self):
        self.model["steps"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "claim requires evidence"):
            build.validate(self.model, self.evidence)

    def test_unit_mismatch_rejected(self):
        next(r for r in self.evidence['records'] if r['id'] == 'protected_screen')['observations'][0]['unit'] = 'A'
        with self.assertRaisesRegex(ValueError, "unit/reference mismatch"):
            build.validate(self.model, self.evidence)

    def test_false_pass_rejected(self):
        next(r for r in self.evidence['records'] if r['id'] == 'protected_screen')['observations'][0]['gate'] = 'pass'
        with self.assertRaisesRegex(ValueError, "contradicts"):
            build.validate(self.model, self.evidence)

    def test_stale_propagates_without_rewriting_observations(self):
        original = deepcopy(next(r for r in self.evidence['records'] if r['id'] == 'current_audit')['observations'])
        lock = {"sources": {k: {"path": p, "sha256": hashlib.sha256(build.source_path(p).read_bytes()).hexdigest()} for k, p in self.model["sources"].items()}}
        clean = build.snapshot(self.model, deepcopy(self.evidence), lock)
        self.assertFalse(clean["meta"]["stale_sources"])
        lock["sources"]["audit"]["sha256"] = "0" * 64
        stale = build.snapshot(self.model, deepcopy(self.evidence), lock)
        self.assertEqual(stale["meta"]["stale_sources"], ["audit"])
        record = next(r for r in stale["evidence"] if r["id"] == "current_audit")
        self.assertTrue(record["stale"])
        self.assertEqual(record["observations"], original)

    def test_source_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            build.source_path("../unrelated.md")

    def test_circuit_hash_mismatch_rejected(self):
        self.model["circuits"][0]["netlist_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            build.validate(self.model, self.evidence)

    def test_flow_graphs_are_connected_to_known_blocks(self):
        flows = build.read_yaml(ROOT / "review/flows.json")
        build.validate_flows(flows)
        flows["graphs"]["all"]["nodes"][0]["blocks"] = ["missing-block"]
        with self.assertRaisesRegex(ValueError, "unknown flow block"):
            build.validate_flows(flows)

    def test_flow_edge_endpoint_rejected(self):
        flows = build.read_yaml(ROOT / "review/flows.json")
        flows["graphs"]["all"]["edges"][0]["to"] = "missing-node"
        with self.assertRaisesRegex(ValueError, "endpoint"):
            build.validate_flows(flows)

    def test_public_payload_contains_no_repository_documents(self):
        flows = build.read_yaml(ROOT / "review/flows.json")
        private = build.snapshot(self.model, self.evidence, {})
        public = build.public_snapshot(private, flows)
        encoded = json.dumps(public, ensure_ascii=False)
        for forbidden in ("docs/", "config/", "netlist_sha256", "reviewed_sha256", "# System Error Budget"):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn("sources", public)
        self.assertNotIn("sources", public["model"])
        current = next(r for r in public["evidence"] if r["id"] == "current_audit")
        self.assertAlmostEqual(next(o["value"] for o in current["observations"] if o["unit"] == "A"), 25.858e-6)
        self.assertTrue(public["meta"]["needs_review"])


class IsolatedDiagramTests(unittest.TestCase):
    def test_isolated_fixture_is_distinct_and_uncompleted(self):
        original = build.load_topology()
        isolated = original['variants']['isolated']
        self.assertEqual(original['devices']['XMN11']['G'], 'net0')
        self.assertEqual(isolated['devices']['XMN11']['G'], 'net1')
        self.assertEqual(isolated['devices']['Cu'], {'A': 'VOUT', 'B': 'VCM'})
        self.assertEqual(sum('net1' in p.values() for p in isolated['devices'].values()), 1)
        self.assertEqual(len(isolated['anchors']), 16)
        self.assertNotEqual(original['image_revision'], isolated['image_revision'])
        self.assertIn('未定义', isolated['notice'])


if __name__ == "__main__":
    unittest.main()
