import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_install_recovery import IMAGE_BYTES, inactive_slot, range_check


class InstallBoundaryTests(unittest.TestCase):
    def test_candidate_preserves_both_slot_boundaries(self):
        self.assertEqual(range_check('A', IMAGE_BYTES)['erase_end'], 0x790000)
        self.assertEqual(range_check('B', IMAGE_BYTES)['erase_end'], 0xf00000)

    def test_old_aggregate_b_size_overlaps_shared_overlay(self):
        with self.assertRaises(ValueError):
            range_check('B', 0x760000)

    def test_partial_erase_block_crossing_rejected(self):
        with self.assertRaises(ValueError):
            range_check('B', IMAGE_BYTES + 1)

    def test_never_overwrite_fallback_during_trial_or_unknown_state(self):
        self.assertEqual(inactive_slot(0), 'B')
        self.assertEqual(inactive_slot(2), 'A')
        for state in (1, 3, 4, -1, None, '0', False):
            with self.subTest(state=state), self.assertRaises(ValueError):
                inactive_slot(state)
