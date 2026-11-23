"""The ADC core fill-owner table (Layout/specs/fill-policy.md) names every floorplan region once; the chip fill-owner
table gives every chip region an owner."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def owner_rows(text, heading='### ADC Core Fill Owners'):
    section = text.split(heading, 1)[1].split('\n### ', 1)[0]
    rows = [line for line in section.splitlines() if line.startswith('| ')]
    cells = [[c.strip() for c in row.strip('|').split('|')] for row in rows[2:]]
    return {cell[0]: cell[1:] for cell in cells}


class FillOwnership(unittest.TestCase):
    def setUp(self):
        text = (ROOT / 'Layout/specs/fill-policy.md').read_text(encoding='utf-8')
        self.rows = owner_rows(text)
        self.chip_rows = owner_rows(text, '### Chip Fill Owners')
        plan = json.loads((ROOT / 'Layout/design/floorplan.json').read_text(encoding='utf-8'))
        self.regions = [b['id'] for b in plan['blocks']] + [r['id'] for r in plan['reserved_regions']]

    def test_every_region_has_exactly_one_owner_row(self):
        named = [name for region in self.rows for name in re.findall(r'`([^`]+)`', region)]
        self.assertEqual(sorted(named), sorted(set(named)), 'region named in more than one row')
        self.assertEqual(sorted(named), sorted(self.regions))

    def test_every_row_has_an_owner_and_the_remainder_is_covered(self):
        for region, (owner, fill, status) in self.rows.items():
            self.assertTrue(owner and fill, region)
        self.assertTrue(any(r.startswith('Rest of the core') for r in self.rows))
        ring = [cells for r, cells in self.rows.items() if 'io_ring.json' in r]
        self.assertEqual(len(ring), 1)
        self.assertEqual(ring[0][0], 'Chip level')
        self.assertIn('#chip-fill-owners', ring[0][1])

    def test_every_chip_row_has_an_owner(self):
        self.assertTrue(self.chip_rows)
        for region, (owner, fill, status) in self.chip_rows.items():
            self.assertTrue(owner and fill and status, region)
        self.assertTrue(any(r.startswith('IO ring cells') for r in self.chip_rows))
        self.assertTrue(any(r.startswith('The rest of the ring opening') for r in self.chip_rows))


if __name__ == '__main__':
    unittest.main()
