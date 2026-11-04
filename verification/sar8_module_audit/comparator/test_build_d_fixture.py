"""Local structural tests only; no Spectre or electrical pass assertions."""
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
import unittest

import build_d_fixture as build


class FixtureStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts, cls.audit = build.prepare()
        cls.spec = json.loads(build.SPEC.read_text(encoding="utf-8"))
        cls.source = build.check_source(cls.spec)
        cls.original = build.blocks((build.ROOT / cls.source["rx2_dut"]["path"]).read_text())
        cls.cells = build.blocks(cls.artifacts["cells.scs"])
        cls.manifest = json.loads(cls.artifacts["manifest.json"])

    def test_all_generated_hashes_and_uncompiled_state(self):
        for name, value in self.manifest["files"].items():
            self.assertEqual(build.sha(self.artifacts[name].encode()), value)
        self.assertEqual(self.manifest["status"], "not_Spectre_compiled")
        self.assertIsNone(self.manifest["simulation_pass"])
        self.assertFalse(self.manifest["remote_submission"])
        self.assertFalse(self.manifest["managed_recipe_created"])

    def test_source_tamper_is_rejected(self):
        spec = deepcopy(self.spec)
        spec["sources"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Frozen source hash mismatch"):
            build.check_source(spec)

    def test_native_cells_are_verbatim(self):
        native = set(self.cells) - {"audit_cmp_timing", "audit_cmp_ctrl", "audit_comparator_d"}
        self.assertGreater(len(native), 10)
        for name in native:
            self.assertEqual(self.cells[name], self.original[name], name)

    def test_only_forward_timing_cone_and_instances_are_unchanged(self):
        old = {n: (args, master, params)
               for n, args, master, params in build.instances(self.original["sar8p_timing"])}
        new = {n: (args, master, params)
               for n, args, master, params in build.instances(self.cells["audit_cmp_timing"])}
        self.assertEqual(set(new), build.TIMING_KEEP)
        for name in new:
            self.assertEqual(old[name], new[name], name)
        self.assertNotIn("XCLOCK", new)
        self.assertNotIn("X025", new)
        self.assertNotIn("XD_QUIET_D", new)

    def test_register_load_with_independent_token_and_reset(self):
        old = {n: (args, master, params)
               for n, args, master, params in build.instances(self.original["sar8i_ctrl"])}
        new = {n: (args, master, params)
               for n, args, master, params in build.instances(self.cells["audit_cmp_ctrl"])}
        self.assertEqual(set(new), {"XTIM"} | {"XBIT" + str(i) for i in range(8)})
        self.assertNotIn("XSEQ", new)
        self.assertNotIn("X018", new)
        self.assertEqual(new["XTIM"][1], "audit_cmp_timing")
        for bit in range(8):
            name = "XBIT" + str(bit)
            args = old[name][0]
            expected = ["REG_RESET" if n == "SAMPLE" else "TOKEN" + str(bit)
                        if n == "T" + str(bit) else n for n in args]
            self.assertEqual(new[name][0], expected)
            self.assertEqual(new[name][1:], old[name][1:])

    def test_preserved_native_fanout_and_omissions_are_explicit(self):
        self.assertEqual(len(self.audit["preserved_terminal_fanout"]), 6)
        for node, records in self.audit["preserved_terminal_fanout"].items():
            self.assertGreater(len(records), 0, node)
        self.assertIn("XDUT.PHI_U", self.audit["removed_boundary_terminal_fanout"])
        self.assertIn("XDUT.XREF.XMUX0", " ".join(
            r["instance"] for values in self.audit["removed_boundary_terminal_fanout"].values()
            for r in values))
        self.assertLess(self.audit["retained_native_MOS"], self.audit["original_ADC_MOS"] * .3)
        self.assertFalse(any("refword" in n or "cdac" in n or "bootstrap" in n
                             or "bitseq" in n or n == "sar8p_sr" for n in self.cells))
        clock = self.audit["clock_cut"]
        self.assertEqual(len(clock["removed_clock_node_terminals"]), 2)
        self.assertTrue(all(".X025.X001." in r["instance"] and r["terminal"] == "d"
                            for r in clock["removed_clock_node_terminals"]))

    def test_exact_three_MOM_geometries(self):
        old = {n: (args, master, params) for n, args, master, params in
               build.instances(self.original["sar_adc8_join_r4"]) if n.startswith("CL_COMP") or n == "CL_CMP_CLK"}
        new = {n: (args, master, params) for n, args, master, params in
               build.instances(self.cells["audit_comparator_d"]) if n in old}
        self.assertEqual(len(new), 3)
        for name in old:
            self.assertEqual(old[name][1:], new[name][1:])
            self.assertEqual(new[name][0], ["VSS" if x == "0" else x for x in old[name][0]])

    def test_no_internal_ideal_driver_contention(self):
        for label in build.CORNERS:
            source_nodes = []
            for line in self.artifacts[label + ".scs"].splitlines():
                m = re.match(r"V\w+ \((\S+) 0\) vsource", line)
                if m:
                    source_nodes.append(m[1])
            expected = {"VDD!", "CMP_CLK", "TOPP", "TOPN", "REG_RESET", "SAMPLE_GUARD"}
            expected.update("TOKEN" + str(i) for i in range(8))
            self.assertEqual(set(source_nodes), expected)
            self.assertEqual(len(source_nodes), 14)
            self.assertNotIn("START", source_nodes)
            self.assertNotIn("COMP_P", source_nodes)
            self.assertNotIn("X025", self.cells["audit_cmp_timing"])

    def test_same_DUT_and_stimulus_only_environment_changes(self):
        def normalize(deck):
            deck = re.sub(r"parameters SUP=[^\n]+", "parameters SUP=ENV", deck)
            deck = deck.replace("ttmacro_mos_moscap", "ENVmacro_mos_moscap")
            deck = deck.replace("ssmacro_mos_moscap", "ENVmacro_mos_moscap")
            return re.sub(r"options temp=\S+ tnom=", "options temp=ENV tnom=", deck)
        self.assertEqual(normalize(self.artifacts["tt.scs"]), normalize(self.artifacts["sscold.scs"]))
        self.assertIn("section=tt_mom", self.artifacts["sscold.scs"])
        self.assertEqual(self.artifacts["sscold.scs"].count("section="), 7)

    def test_sign_history_and_pwl_order(self):
        points = build.stimulus_points()
        self.assertEqual(build.SIGNS, (1, 1, -1, 1, -1, -1))
        for key, values in points.items():
            self.assertTrue(all(a[0] < b[0] for a, b in zip(values, values[1:])), key)
        for i, (at, sign) in enumerate(zip(build.START_NS, build.SIGNS)):
            update = at - 8 + .1
            vp = next(v for t, v in points["TOPP"] if abs(t - update) < 1e-9)
            vn = next(v for t, v in points["TOPN"] if abs(t - update) < 1e-9)
            self.assertAlmostEqual(vp - vn, sign * build.VDIFF, places=12)
            self.assertAlmostEqual((vp + vn) / 2, .45, places=12)
        self.assertFalse(self.manifest["stimulus"]["timing_budget_allocated"])

    def test_saved_nodes_exist_after_hierarchical_alias_resolution(self):
        p = build.ports(self.cells["audit_comparator_d"])
        binding = {n: n for n in p}
        binding.update(VDD="VDD!", VSS="0")
        flat = build.flatten(self.cells, "audit_comparator_d", binding)
        nodes = {n for r in flat.values() for n in r["nodes"]}
        for line in self.artifacts["tt.scs"].splitlines():
            if not line.startswith("save "):
                continue
            name = line.split()[1]
            if ":" not in name:
                self.assertIn(name, nodes)
            elif name not in ["VVDD:1", "VCMP_CLK:1"]:
                instance, terminal = name.rsplit(":", 1)
                self.assertIn(instance, flat)
                self.assertIn(int(terminal), range(1, 5))

    def test_immutable_writer_refuses_old_different_output(self):
        # A temporary directory strictly inside this owned subtree; no old evidence.
        with tempfile.TemporaryDirectory(prefix="local_test_", dir=build.HERE) as temp:
            destination = Path(temp).resolve()
            self.assertTrue(destination.is_relative_to(build.HERE))
            (destination / "keep.txt").write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                build.emit({"keep.txt": "replacement", "other.txt": "new"}, destination)
            self.assertEqual((destination / "keep.txt").read_bytes(), b"original")
            self.assertFalse((destination / "other.txt").exists())


if __name__ == "__main__":
    unittest.main()
