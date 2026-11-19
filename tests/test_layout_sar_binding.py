import re
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import json

from Layout.project import ROOT
from Layout.design.sar_array import generate
from Layout.design.sar_reference import ARRAY_DECAPS
from Layout.tools.simulation.prepare_sar_timing import bind_extracted_macro, quiet_eco


class SarExtractionTest(unittest.TestCase):
    def test_static_latch_source_and_row_placement_agree(self):
        from Layout.design.sar_standard import DECAPS, generate as generate_standard
        with TemporaryDirectory() as temp:
            out = Path(temp)
            generate_standard(out, quiet_stages=9)
            intent = json.loads((out / "intent.json").read_text())
            cdl = (out / "standard-leaves.cdl").read_text()
        cells = intent["instances"]
        self.assertEqual(sum(q["master"].startswith("DEL") for q in cells.values()), 52)
        self.assertTrue(all(q["master"].endswith("BWP12T30P140") for q in cells.values()))
        self.assertEqual({name for name in cells if name.startswith("XCTRL__XTIM__XCLOCK__")},
                         {f"XCTRL__XTIM__XCLOCK__X00{i}__XLIB" for i in range(4)})
        self.assertNotIn("cfmom_2t", cdl)
        self.assertEqual(len(intent["ports"]), 26)
        for row, master in DECAPS.items():
            name = "DECAP_" + row
            self.assertEqual(cells[name]["pins"], {"VDD":"VDD", "VSS":"VSS"})
            self.assertIn(f"X{name} VDD VSS {master}BWP12T30P140\n", cdl)

    def test_shortened_chains_keep_the_final_qualifier_and_fold_the_sample_path(self):
        from Layout.design.sar_standard import generate as generate_standard
        from Layout.design.sar_timing import electrical
        for stages in (5, 6):
            with self.subTest(stages=stages), TemporaryDirectory() as temp:
                out = Path(temp)
                generate_standard(out, quiet_stages=stages)
                intent = json.loads((out / "intent.json").read_text())
                cells, ports, hashes = electrical(standard_delays=True, static_latch=True, quiet_stages=stages)
                branch = "XCTRL/XTIM/XD_QUIET_D/"
                final = cells[branch + f"XQUAL{stages}/X001/XLIB"]
                self.assertEqual(final.pins["ZN"], "XCTRL__XTIM__QUIET_D")
                self.assertEqual(sum(q.master.startswith("DEL") for q in cells.values()), 43 + stages)
                self.assertEqual(len(intent["rows"]), 13)
                self.assertEqual(set(intent["ports"]), set(ports))
                self.assertIn("design/xtor/clock/delays_std_q%d.scs" % stages, hashes)

    def test_trimmed_final_cell_matches_electrical_source_and_native_reference(self):
        from Layout.design.sar_standard import generate as generate_standard
        from tools.saradc.quiet_delay import REFERENCE, source_for_stages
        baseline = (ROOT / 'design' / REFERENCE).read_bytes()
        _, uniform = source_for_stages(baseline, 6)
        name, trimmed = source_for_stages(baseline, 6, 200)
        changes = [(a,b) for a,b in zip(uniform.splitlines(), trimmed.splitlines(), strict=True) if a!=b]
        self.assertEqual(len(changes), 1)
        old, new = changes[0]
        self.assertTrue(old.startswith(b'XD6 '))
        self.assertEqual(new, old.replace(b'DEL250D1', b'DEL200D1'))
        with TemporaryDirectory() as temp:
            out = Path(temp)
            generate_standard(out, quiet_stages=6, quiet_final_ps=200)
            intent = json.loads((out / 'intent.json').read_text())
            cdl = (out / 'standard-leaves.cdl').read_text()
        cell = 'XCTRL__XTIM__XD_QUIET_D__XD6'
        self.assertEqual(intent['instances'][cell]['master'], 'DEL200D1BWP12T30P140')
        self.assertRegex(cdl, r'(?m)^X' + cell + r' .* DEL200D1BWP12T30P140$')
        self.assertIn('design/' + name + ' SHA256', cdl)

    def test_single_sample_tap_keeps_both_request_qualifiers_and_matches_placement(self):
        from Layout.design.sar_standard import generate as generate_standard
        from tools.saradc.quiet_delay import REFERENCE, source_for_stages

        reference = (ROOT / "design" / REFERENCE).read_bytes()
        _, control = source_for_stages(reference, 6, 200)
        sample = re.compile(rb"(?ms)^subckt sar8r_delay A VDD VSS Y\r?\n(.*?)^ends sar8r_delay\b")
        for delay in (75, 200):
            with self.subTest(delay=delay), TemporaryDirectory() as temp:
                name, candidate = source_for_stages(reference, 6, 200, sample_delay_ps=delay)
                self.assertEqual(sample.sub(b"", candidate), sample.sub(b"", control))
                self.assertEqual(sample.search(candidate)[1].splitlines(), [
                    b"XD1 (A D1 VDD VSS) DEL%03dD1BWP12T30P140" % delay,
                    b"XQUAL1 (A D1 VDD VSS Y) sar8p_and2",
                ])
                out = Path(temp)
                generate_standard(out, quiet_stages=6, quiet_final_ps=200, sample_delay_ps=delay)
                cells = json.loads((out / "intent.json").read_bytes())["instances"]
                self.assertEqual(cells["XSEQ__XD__XD1"]["master"], "DEL%03dD1BWP12T30P140" % delay)
                self.assertNotIn("XSEQ__XD__XD2", cells)
                for gate in ("XSEQ__XA", "XSEQ__XD__XQUAL1"):
                    self.assertEqual(cells[gate+"__X000__XLIB"]["pins"]["A1"], "SAMPLE_MATCH")
                self.assertEqual(cells["XSEQ__XB__XFINAL__XLIB"]["pins"]["ZN"], "SEQ_SAMPLE")
                self.assertIn("design/" + name + " SHA256", (out / "standard-leaves.cdl").read_text())

    def test_array_placement_and_lvs_reference_include_the_same_supply_devices(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            generate(folder)
            intent = json.loads((folder / "intent.json").read_text())
            source = (folder / "array-leaves.cdl").read_text()
        self.assertEqual(len(ARRAY_DECAPS), 7)
        for row, master in ARRAY_DECAPS.items():
            name = "DECAP_" + row
            cell = intent["instances"][name]
            self.assertEqual(cell["pins"], {"VDD": "VDD", "VSS": "VSS"})
            self.assertEqual(cell["master"], master + "BWP12T30P140")
            self.assertIn(f"X{name} VDD VSS {cell['master']}\n", source)
        self.assertEqual(len(intent["nets"]), 208)
        self.assertEqual(len(intent["ports"]), 26)
        for n in (0, 1):
            cell = intent["instances"][f"XCTRL__XTIM__XD_QUIET_D__R{n}"]
            self.assertEqual(cell["options"]["l"], "8.5u")

    def test_integrated_core_and_wrapper_call_keep_the_verified_master(self):
        source = (ROOT / "design/top/adc_top.scs").read_text()
        ports = ["VDD!", "0", "SAMPLE", "SAR_PHI_W", "WRITE_AT_D7"]
        for master in ("sar8_sar_timing_core", "sar8_sar_timing"):
            with self.subTest(master=master):
                deck = bind_extracted_macro(source, ports, master)
                self.assertEqual(
                    re.findall(r"(?m)^\s*XSAR_PHY\s*\(([^)]*)\)\s*(\w+)\s*$", deck),
                    [(" ".join(ports), master)],
                )
                self.assertNotRegex(deck, r"(?m)^\s*(XCTRL|XSEQ|XIDLE|XSAMPLE)\s+\(")
                self.assertRegex(deck, r"(?m)^\s*XCDAC\s+\(")

    def test_quiet_length_only_changes_the_two_electrical_statements(self):
        source = (ROOT / "design/xtor/clock/delays.scs").read_bytes()
        trial = quiet_eco(source, "9.85u")
        changed = [
            (old, new)
            for old, new in zip(source.splitlines(), trial.splitlines(), strict=True)
            if old != new
        ]
        self.assertEqual({new.split()[0] for _, new in changed}, {b"R0", b"R1"})
        self.assertTrue(
            all(re.sub(rb"l=\S+", b"l=9.85u", old) == new for old, new in changed)
        )
