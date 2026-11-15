"""Synthetic tests: no game ROM or extracted tables."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research.mesence.player_recipe import _decode_tables, read_recipe, PATTERNS


class PlayerRecipeTests(unittest.TestCase):
    def setUp(self):
        self.offsets = bytes(2 + 3*i for i in range(81))
        self.patterns = bytes(i % 256 for i in range(486))
        self.pages = bytes(i // 24 for i in range(81))

    def decode(self, frame, **changes):
        args = dict(offsets=self.offsets, patterns=self.patterns, pages=self.pages, frame=frame)
        args.update(changes)
        return _decode_tables(**args)

    def test_biased_pointer_and_page_carry(self):
        for frame in (0, 1, 42, 43, 80):
            r = self.decode(frame)
            self.assertEqual(r['pattern_table_index'], frame*6)
            self.assertEqual(r['components'][0]['source_rom_offset'], PATTERNS+frame*6)
            self.assertEqual(r['components'][-1]['tile_id'], (frame*6+5) % 256)

    def test_oam_order_is_not_table_order(self):
        self.assertEqual([c['relative_oam_slot'] for c in self.decode(0)['components']], [3,4,5,0,1,2])

    def test_game_suppression_marker(self):
        r = self.decode(0, patterns=bytes([0xF1])+self.patterns[1:])
        self.assertTrue(r['components'][0]['suppressed_by_game_marker'])
        self.assertFalse(r['components'][1]['suppressed_by_game_marker'])

    def test_invalid_frames_and_truncation(self):
        for frame in (-1,81,True,1.5,'1'):
            with self.assertRaises(ValueError): self.decode(frame)
        for key in ('offsets','patterns','pages'):
            with self.assertRaises(ValueError): self.decode(0, **{key:b''})

    def test_pointer_bounds(self):
        for offset in (0,255):
            with self.assertRaises(ValueError): self.decode(0, offsets=bytes([offset])+self.offsets[1:])

    def test_rejects_other_rom_without_mutation(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.nes'; path.write_bytes(b'synthetic only')
            with self.assertRaises(ValueError): read_recipe(path,0)
            self.assertEqual(path.read_bytes(),b'synthetic only')


if __name__ == '__main__': unittest.main()
