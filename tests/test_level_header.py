import unittest
from research.mesence.level_header import decode_header


class LevelHeaderTests(unittest.TestCase):
    def test_pointers_are_little_endian_and_alternate_tileset_is_explicit(self):
        r=decode_header(bytes([0x34,0x12,0x78,0x56,0,0,9,0,0]))
        self.assertEqual(r['alternate_layout_cpu_pointer'],0x1234)
        self.assertEqual(r['alternate_object_cpu_pointer'],0x5678)
        self.assertEqual(r['alternate_tileset'],9)
        self.assertNotIn('current_tileset',r)

    def test_fields_do_not_overlap(self):
        r=decode_header(bytes([0]*4+[0xff,0xff,0xff,0xff,0xff]))
        self.assertEqual(r['length_in_screens'],16)
        self.assertEqual(r['player_start_y'],0x180)
        self.assertEqual(r['player_start_x'],0x80)
        self.assertEqual(r['object_palette_set'],11)
        self.assertTrue(r['vertical_level'])
        self.assertEqual(r['background_bank_index'],31)
        self.assertEqual(r['initial_action'],7)
        self.assertEqual(r['music_selector'],15)
        self.assertEqual(r['uninterpreted_music_byte_bits'],3)
        self.assertEqual(r['timer_start'],0)

    def test_timer_and_y_selectors(self):
        for i,value in enumerate([300,400,200,0]):
            self.assertEqual(decode_header(bytes(8)+bytes([i<<6]))['timer_start'],value)
        for i,value in enumerate([0x170,0x40,0,0x140,0x70,0xb0,0xf0,0x180]):
            self.assertEqual(decode_header(bytes(4)+bytes([i<<5])+bytes(4))['player_start_y'],value)

    def test_truncation_and_trailing_data_rejected(self):
        for n in (0,8,10):
            with self.assertRaises(ValueError): decode_header(bytes(n))


if __name__=='__main__': unittest.main()
