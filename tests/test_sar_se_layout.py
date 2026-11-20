import unittest

from Layout.design.sar_single_edge import CORE, PORT_ORDER, SITES, check_drivers, electrical, flat_net, verilog


class SarMacroNetlistTest(unittest.TestCase):
    def setUp(self):
        self.cells, self.ports, self.hashes = electrical()

    def test_group_flattens_to_native_cells(self):
        self.assertEqual(len(self.cells), 174)
        self.assertTrue(all(c['master'] in SITES for c in self.cells.values()))
        self.assertEqual(self.ports, list(PORT_ORDER))
        self.assertIn('design/xtor/sar/single_edge.scs', self.hashes)

    def test_every_net_is_driven_once(self):
        check_drivers(self.cells, self.ports)

    def test_verilog_declares_the_macro_ports(self):
        text = verilog(self.cells, self.ports)
        self.assertTrue(text.startswith('module %s (%s);' % (CORE, ', '.join(PORT_ORDER))))
        self.assertEqual(text.count('BWP12T30P140 '), 174)

    def test_probe_paths_resolve_to_macro_nets(self):
        self.assertEqual(flat_net('xdut.xctrl.xtim.sn_d'), 'XCTRL__XTIM__SN_D')
        self.assertEqual(flat_net('xdut.xctrl.xbit3.din'), 'XCTRL__XBIT3__DIN')
        self.assertIsNone(flat_net('xdut.cmp_clk'))
        with self.assertRaises(ValueError):
            flat_net('xdut.xbootp.g')


if __name__ == '__main__':
    unittest.main()
