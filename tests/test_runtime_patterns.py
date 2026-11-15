import unittest
from research.mesence.runtime_patterns import decode_pattern_records, inspect_rom


class PatternTests(unittest.TestCase):
    def test_slot_order_suppression_and_offsets(self):
        result = decode_pattern_records(bytes([99, 1, 3, 241, 5, 7, 9]), 1, 1)
        self.assertEqual(result[0]["file_offset"], 1)
        self.assertEqual([s["tile_id"] for s in result[0]["slots"]], [1, 3, 241, 5, 7, 9])
        self.assertEqual([s["slot"] for s in result[0]["slots"] if s["suppressed"]], [2])

    def test_multiple_records_and_exact_end(self):
        records = decode_pattern_records(bytes(range(12)), 0, 2)
        self.assertEqual(records[1]["file_offset"], 6)
        self.assertEqual(records[1]["slots"][-1]["tile_id"], 11)

    def test_invalid_bounds_and_types(self):
        for offset, count in [(-1, 1), (0, 0), (0, -1), (1, 1), (7, 1), (0, 2), (True, 1), (0, 1.0)]:
            with self.subTest(offset=offset, count=count), self.assertRaises(ValueError):
                decode_pattern_records(bytes(6), offset, count)

    def test_unknown_rom_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            inspect_rom(bytes(400000))


if __name__ == "__main__":
    unittest.main()

