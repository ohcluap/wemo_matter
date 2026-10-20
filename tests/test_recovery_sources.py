from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_recovery_sources import layout, overlaps


class RecoveryLayoutTests(unittest.TestCase):
    def test_aliases_are_not_concatenated_into_a_backup(self):
        partitions = layout('''label = "whole"; reg = <0x0 0x100>;
            label = "subregion"; reg = <0x80 0x20>;''')
        self.assertEqual(max(p['end'] for p in partitions.values()), 0x100)
        self.assertEqual(overlaps(0x70, 0x30, partitions, ['subregion']), {'subregion': 0x20})

    def test_adjacent_ranges_do_not_overlap(self):
        partitions = layout('label = "protected"; reg = <0x100 0x100>;')
        self.assertEqual(overlaps(0, 0x100, partitions, ['protected']), {})
        self.assertEqual(overlaps(0, 0x101, partitions, ['protected']), {'protected': 1})

    def test_ambiguous_or_missing_partition_table_rejected(self):
        for text in ('', 'label = "x"; reg = <0x0 0x0>;',
                     'label = "x"; reg = <0x0 0x10>; label = "x"; reg = <0x10 0x10>;'):
            with self.assertRaises(ValueError):
                layout(text)
