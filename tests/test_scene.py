import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageSequence

from spritemine.scene import Scene, viewport_to_world
from spritemine.scene_export import export
from spritemine.terrain_motion import Terrain, motion_cels

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from make_scene_fixture import create_fixture


class SceneTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.path = create_fixture(self.root / "inputs")
        self.recipe = json.loads(self.path.read_text(encoding="utf-8"))
        self.scene = Scene.load(self.path)

    def test_all_rows_and_columns_stay_in_world_coordinates(self):
        static = self.scene.render(animated=False)
        self.assertEqual(static.size, (180, 108))
        for point in [(116, 12), (52, 44), (12, 88), (179, 106)]:
            self.assertEqual(static.getpixel(point), (136, 166, 153) if point[1] != 106 else (55, 76, 105))
        self.assertEqual(static.getpixel((112, 12)), (23, 33, 59))
        self.assertEqual(viewport_to_world((24, 62), (100, 32), (8, 12)), (116, 82))

    def test_indexed_alpha_layer_order_and_animation_phase(self):
        frame = self.scene.render(0)
        self.assertEqual(frame.getpixel((70, 40)), (232, 242, 176))  # transparent atlas index
        self.assertEqual(frame.getpixel((71, 40)), (151, 96, 155))  # foreground occludes actor
        self.assertEqual(frame.getpixel((140, 16)), (232, 242, 176))
        self.assertEqual(self.scene.render(5).getpixel((140, 17)), (231, 180, 94))
        self.assertIsNone(ImageChops.difference(frame, self.scene.render(84)).getbbox())

    def test_capture_crop_clips_at_the_canvas_edge(self):
        self.recipe["layers"].append({"stamps": [{
            "asset": "lit", "at": [5, 8],
            "viewport": {"scroll": [2, 3], "origin": [9, 13]},
        }]})
        frame = Scene(self.recipe, self.path.parent).render(animated=False)
        self.assertEqual(frame.getpixel((0, 0)), (232, 242, 176))
        self.assertEqual(frame.getpixel((2, 0)), (23, 33, 59))

    def test_terrain_walk_turn_fall_hide_and_hop(self):
        patrol, fall, hop = self.scene.layers[1].tracks[:3]
        self.assertEqual(max(cel.offset[0] for cel in patrol.cels), 20)
        self.assertTrue(all(cel.asset is not None and cel.offset[1] == 0 for cel in patrol.cels))
        self.assertEqual({cel.asset for cel in patrol.cels}, {"left", "right"})
        self.assertTrue(any(cel.offset[1] > 0 and cel.asset for cel in fall.cels))
        self.assertIsNone(fall.cels[-1].asset)
        self.assertEqual(fall.cel_at(42), fall.cel_at(0))
        self.assertLess(min(cel.offset[1] for cel in hop.cels), 0)

    def test_wall_stops_and_reverses_actor(self):
        terrain = Terrain.from_recipe({"tile_size": [1, 1], "rows": [
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1],
        ]})
        spec = {
            "bounds": [1, 1], "period": 6, "hide_y": 2, "direction": -1,
            "left": ["left"], "right": ["right"],
        }
        cels = motion_cels((1, 0), spec, terrain)
        self.assertEqual([cel["offset"][0] for cel in cels], [0, 0, 1, 2, 2, 1])

    def test_gif_roundtrip_timing_palette_and_second_build(self):
        first = self.root / "first"
        second = self.root / "second"
        manifest = export(self.path, first)
        self.assertEqual(manifest, export(self.path, second))
        for name in ("static.png", "scene.gif", "manifest.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        with Image.open(first / "scene.gif") as gif:
            self.assertEqual(gif.info["loop"], 0)
            tick = 0
            for frame in ImageSequence.Iterator(gif):
                hold = frame.info["duration"]
                self.assertEqual(hold % 40, 0)
                for _ in range(hold // 40):
                    self.assertIsNone(
                        ImageChops.difference(frame.convert("RGB"), self.scene.render(tick)).getbbox()
                    )
                    tick += 1
            self.assertEqual(tick, 84)
        with Image.open(first / "static.png") as static:
            self.assertEqual(static.tobytes(), self.scene.render(animated=False).tobytes())

    def test_nominal_full_size_export_reaches_all_canvas_edges(self):
        self.recipe.update(size=[2816, 432], ticks=2)
        self.recipe["layers"] = [{
            "stamps": [{"asset": "floor", "at": [2812, 428]}],
            "tracks": [{"at": [2812, 0], "cels": [
                {"asset": "lit", "ticks": 1}, {"asset": "dim", "ticks": 1},
            ]}],
        }]
        self.path.write_text(json.dumps(self.recipe), encoding="utf-8")
        export(self.path, self.root / "full-size")
        with Image.open(self.root / "full-size" / "scene.gif") as gif:
            self.assertEqual(gif.size, (2816, 432))
            self.assertEqual(gif.convert("RGB").getpixel((2815, 431)), (55, 76, 105))
            self.assertEqual(gif.convert("RGB").getpixel((2815, 0)), (232, 242, 176))
            gif.seek(1)
            self.assertEqual(gif.convert("RGB").getpixel((2815, 0)), (23, 33, 59))

    def test_gif_rejects_palette_overflow_without_partial_output(self):
        image = Image.new("RGB", (257, 1))
        image.putdata([(i % 256, i // 256, 0) for i in range(257)])
        image.save(self.path.parent / "overflow.png")
        self.recipe["size"] = [257, 1]
        self.recipe["assets"]["overflow"] = {"file": "overflow.png"}
        self.recipe["layers"] = [{"stamps": [{"at": [0, 0], "asset": "overflow"}]}]
        self.path.write_text(json.dumps(self.recipe), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "256-color"):
            export(self.path, self.root / "overflow")
        self.assertFalse((self.root / "overflow").exists())

    def test_rejects_bad_period_paths_hashes_and_crops(self):
        self.recipe["ticks"] = 83
        with self.assertRaisesRegex(ValueError, "period"):
            Scene(self.recipe, self.path.parent)
        self.recipe["ticks"] = 84
        asset = self.recipe["assets"]["floor"]
        for bad, error in [
            ({"file": "../outside.png"}, "escapes"),
            ({"sha256": hashlib.sha256(b"wrong").hexdigest()}, "SHA-256"),
            ({"crop": [0, 0, 20, 20]}, "crop"),
        ]:
            original = asset.copy()
            asset.update(bad)
            with self.assertRaisesRegex(ValueError, error):
                Scene(self.recipe, self.path.parent)
            asset.clear()
            asset.update(original)


if __name__ == "__main__":
    unittest.main()
