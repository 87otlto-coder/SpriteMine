"""ROM-derived, independently timed SMB3 end-level card roulette for M1.

This module uses a user's *private* SMB3 USA PRG1 ROM and matching MesenCE
PPU/palette capture to decode actual 8x16 NES OAM artwork. No sprites,
recordings, ROM contents, or artwork belong in the public GitHub repository.

Pinned source: captainsouthbird/smb3 commit 09b1bd81a788de8ceec664a34094e84ddb463117
  PRG/prg002.asm: ObjP41, EndLevelCard_Untouched, EndLevelCard_AttributeByFrame
  PRG/prg000.asm: Object_Draw16x16Sprite, Object_ShakeAndCalcSprite
  PRG/objects/1-1.asm: OBJ_ENDLEVELCARD, $A8, $15
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image

# OAM tile values for untouched card frames 0,1,2. Each hardware 8x16
# sprite uses the same tile; right half is horizontally flipped.
CARD_FRAMES = (("mushroom", 0x51, 1), ("flower", 0x53, 2), ("star", 0x55, 1))
CARD_GAME_TICKS_PER_SYMBOL = 8
CARD_POSITION_WORLD11 = (0xA8 * 16, 0x15 * 16)  # (2688, 336)
PRIVATE_ROM_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
PPU_SIZE = 12288
PALETTE_RAM_SIZE = 32
RGB_PROFILE_SIZE = 192
SPRITE_ROM_PAGE = 4  # captured PPU bank 5 == 1 KiB CHR-ROM page 4
DISASSEMBLY_COMMIT = "09b1bd81a788de8ceec664a34094e84ddb463117"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def decode_mirrored_oam_8x16(
    pattern_table_8k: bytes, palette_ram: bytes, rgb_profile: bytes,
    tile: int, palette_index: int,
) -> Image.Image:
    """Decode two identical 8x16 hardware sprites, second horizontally flipped.

    OAM 8x16 mode chooses the pattern table through tile bit 0, and the
    even-numbered tile and its following tile are stacked vertically.
    Color index zero is transparent, *not* the NES universal background color.
    """
    if len(pattern_table_8k) < 8192 or len(palette_ram) != PALETTE_RAM_SIZE:
        raise ValueError("Expected 8 KiB PPU pattern data and 32-byte palette RAM")
    if len(rgb_profile) != RGB_PROFILE_SIZE:
        raise ValueError("Expected 64 NES RGB24 colors")
    if not 0 <= tile <= 255 or not 0 <= palette_index <= 3:
        raise ValueError("Invalid OAM tile index or sprite palette")

    top = ((tile & 1) << 12) + ((tile & 0xFE) << 4)
    pal = palette_ram[16 + palette_index * 4:20 + palette_index * 4]
    colors = [(0, 0, 0, 0)] + [
        (*rgb_profile[(pal[i] & 0x3F) * 3:(pal[i] & 0x3F) * 3 + 3], 255)
        for i in (1, 2, 3)
    ]
    image = Image.new("RGBA", (16, 16))
    pixels = image.load()
    for y in range(16):
        row = top + (y // 8) * 16 + (y % 8)
        lo, hi = pattern_table_8k[row], pattern_table_8k[row + 8]
        for x in range(16):
            source_x = x if x < 8 else 15 - x
            bit = 7 - source_x
            value = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
            pixels[x, y] = colors[value]
    return image


def private_inputs(rom_zip: Path, graphics_zip: Path, rgb_profile_file: Path):
    from make_m1_bundle import load_single_rom_zip
    from preview_tiles import ROM_SHA

    rom = load_single_rom_zip(rom_zip)
    if digest(rom) != ROM_SHA or digest(rom) != PRIVATE_ROM_SHA256:
        raise ValueError("Unverified ROM: expected SMB3 US PRG1 / Revision A")
    if len(rom) != 16 + 256 * 1024 + 128 * 1024:
        raise ValueError("Unexpected SMB3 ROM length")
    chr_rom = rom[16 + 256 * 1024:]
    with zipfile.ZipFile(graphics_zip) as capture:
        names = [n for n in capture.namelist() if not n.endswith("/")]
        ppu_files = [n for n in names if n.endswith("-start-ppu.bin")]
        pal_files = [n for n in names if n.endswith("-start-palette.bin")]
        if len(ppu_files) != 1 or len(pal_files) != 1:
            raise ValueError("Expected one paired PPU/palette capture")
        if ppu_files[0].rsplit("-start-", 1)[0] != pal_files[0].rsplit("-start-", 1)[0]:
            raise ValueError("PPU and palette captures must come from the same frame")
        ppu = capture.read(ppu_files[0])
        pal = capture.read(pal_files[0])
        frame = ppu_files[0].rsplit("/", 1)[-1].split("-")[0]
    rgb = rgb_profile_file.read_bytes()
    if len(ppu) != PPU_SIZE or len(pal) != PALETTE_RAM_SIZE or len(rgb) != RGB_PROFILE_SIZE:
        raise ValueError("Invalid private graphics capture sizes")
    # At this specific observed frame, PPU $1400..$17FF corresponds to ROM
    # CHR page 4. Requiring the byte-for-byte mapping prevents guessed art.
    expected = chr_rom[SPRITE_ROM_PAGE * 1024:(SPRITE_ROM_PAGE + 1) * 1024]
    if ppu[0x1400:0x1800] != expected:
        raise ValueError("MesenCE sprite CHR page differs from ROM page 4")
    return rom, ppu, pal, rgb, {
        "rom_sha256": digest(rom),
        "graphics_zip_sha256": digest(graphics_zip.read_bytes()),
        "ppu_sha256": digest(ppu),
        "palette_sha256": digest(pal),
        "rgb_profile_sha256": digest(rgb),
        "capture_frame": frame,
        "sprite_chr_page": SPRITE_ROM_PAGE,
        "source_asm_commit": DISASSEMBLY_COMMIT,
    }


def build(
    rom_zip: Path, animated_recipe: Path, graphics_zip: Path,
    rgb_profile: Path, output_scene: Path,
) -> Path:
    """Extend a 4-phase World 1-1 animated scene with authentic card artwork.

    The 3-phase card and 4-phase background share an 8-game-frame update
    interval. Their composition repeats after LCM(3,4)=12 source steps.
    """
    if output_scene.exists():
        raise FileExistsError(f"Refusing to overwrite existing scene: {output_scene}")
    _, ppu, pal, rgb, provenance = private_inputs(rom_zip, graphics_zip, rgb_profile)
    recipe = json.loads(animated_recipe.read_text(encoding="utf-8"))
    if recipe["size"] != [2816, 432] or recipe["ticks"] != 4 or recipe["tick_ms"] != 130:
        raise ValueError("Expected source-backed 4-phase World 1-1 scene")
    bg_animation = recipe.get("staging_provenance", {}).get("animation", {})
    if bg_animation.get("game_frames_per_phase") != CARD_GAME_TICKS_PER_SYMBOL:
        raise ValueError("Background phase must last eight game frames")
    snapshot = recipe.get("staging_provenance", {}).get("graphics_snapshot_provenance", {})
    if (snapshot.get("ppu_sha256") != provenance["ppu_sha256"] or
        snapshot.get("palette_sha256") != provenance["palette_sha256"] or
        snapshot.get("rgb_profile_sha256") != provenance["rgb_profile_sha256"]):
        raise ValueError("Roulette sprite snapshot differs from background snapshot")
    if len(recipe["layers"]) != 2 or not recipe["layers"][1].get("tracks"):
        raise ValueError("Expected static tiles plus source-backed CHR animation")
    if any(sum(c["ticks"] for c in track["cels"]) != 4 for track in recipe["layers"][1]["tracks"]):
        raise ValueError("Expected four-frame background phase tracks")

    # Ensure the full recipe and all game images are contained beneath the
    # source recipe directory. Do not implicitly copy from arbitrary paths.
    base = animated_recipe.parent.resolve()
    output_scene.mkdir(parents=True)
    try:
        for name, spec in recipe["assets"].items():
            source = (base / spec["file"]).resolve()
            if not source.is_relative_to(base):
                raise ValueError(f"Asset escapes source recipe directory: {name}")
            data = source.read_bytes()
            if spec.get("sha256") and digest(data) != spec["sha256"]:
                raise ValueError(f"Source asset SHA-256 mismatch: {name}")
            dst = output_scene / spec["file"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)

        card_dir = output_scene / "goal_roulette"
        card_dir.mkdir()
        tracks = []
        for frame_number, (label, tile, sprite_palette) in enumerate(CARD_FRAMES):
            picture = decode_mirrored_oam_8x16(ppu[:8192], pal, rgb, tile, sprite_palette)
            file = card_dir / f"goal_{frame_number}_{label}.png"
            picture.save(file)
            name = f"end_level_card_{label}"
            recipe["assets"][name] = {
                "file": file.relative_to(output_scene).as_posix(),
                "sha256": digest(file.read_bytes()),
                "provenance": {
                    **provenance,
                    "kind": "ROM_derived_OAM_8x16_sprite_pair",
                    "object_id": 0x41,
                    "object_pattern_set": "ObjP41",
                    "oam_tile": tile,
                    "oam_palette": sprite_palette,
                    "right_half_hflip": True,
                    "frame": frame_number,
                    "source_class": "decoded",
                    "pixel_reference": "original_CHR_ROM_1k_page_4_matches_450840_PPU",
                },
            }
            tracks.append({"asset": name, "ticks": 1})
        recipe["ticks"] = 12  # LCM: 4 background phases × 3 card states
        recipe["layers"].append({
            "tracks": [{"at": list(CARD_POSITION_WORLD11), "phase": 0, "cels": tracks}]
        })
        recipe["staging_provenance"]["goal_roulette"] = {
            **provenance,
            "source": "PRG/prg002.asm EndLevelCard_Untouched and ObjP41; PRG/objects/1-1.asm",
            "world_position": list(CARD_POSITION_WORLD11),
            "source_object_record": [0x41, 0xA8, 0x15],
            "sprite_tiles": [item[1] for item in CARD_FRAMES],
            "sprite_palettes": [item[2] for item in CARD_FRAMES],
            "symbols": [item[0] for item in CARD_FRAMES],
            "game_frames_per_symbol": CARD_GAME_TICKS_PER_SYMBOL,
            "approx_ntsc_ms_per_symbol": 8 * 1000 / 60.0988,
            "gif_ms_per_symbol": recipe["tick_ms"],
            "combined_phase_ticks": recipe["ticks"],
            "state": "untouched_loop_only; card collection/end sequence not reproduced",
            "full_level_native_rgb_verified": False,
        }
        destination = output_scene / "recipe.json"
        destination.write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return destination
    except BaseException:
        shutil.rmtree(output_scene, ignore_errors=True)
        raise



def export_goal_scene(recipe: Path, destination: Path) -> dict:
    """Export a 12-step native-art goal roulette and lossless numbered PNGs."""
    from spritemine.scene import Scene
    from spritemine.scene_export import export

    scene = Scene.load(recipe)
    if scene.ticks != 12 or scene.tick_ms != 130:
        raise ValueError("Expected 12 source-derived combined phases at 130ms each")
    export(recipe, destination)
    frame_dir = destination / "frames"
    frame_dir.mkdir()
    frames = []
    digests = {}
    for tick in range(scene.ticks):
        frame = scene.render(tick)
        filename = f"world11_{tick:02d}.png"
        target = frame_dir / filename
        frame.save(target)
        digests[filename] = digest(target.read_bytes())
        frames.append(frame)
    with Image.open(destination / "scene.gif") as gif:
        if gif.n_frames != scene.ticks or gif.info.get("loop") != 0:
            raise ValueError("GIF collapsed frames or does not loop")
        for tick, image in enumerate(frames):
            gif.seek(tick)
            if gif.info.get("duration") != scene.tick_ms:
                raise ValueError("GIF frame timing differs from recipe")
            if gif.convert("RGB").tobytes() != image.tobytes():
                raise ValueError(f"GIF pixel mismatch at tick {tick}")
    if len({image.tobytes() for image in frames}) != 12:
        raise ValueError("All twelve combined ticks must be visually distinct")
    report = {
        "source_class": "ROM_CHR_decoded_card_and_background_tracks",
        "frame_count": scene.ticks,
        "tick_ms": scene.tick_ms,
        "loop_ms": scene.ticks * scene.tick_ms,
        "card_game_ticks_per_state": CARD_GAME_TICKS_PER_SYMBOL,
        "card_approx_ntsc_ms_per_state": 8000 / 60.0988,
        "card_gif_ms_per_state": scene.tick_ms,
        "goal_position": list(CARD_POSITION_WORLD11),
        "gif_rgb_matches_every_png_frame": True,
        "gif_loops": True,
        "frame_png_sha256": digests,
        "gif_sha256": digest((destination / "scene.gif").read_bytes()),
        "native_full_stage_rgb_accepted": False,
        "note": "Untouched roulette only; card collection and finish choreography are not included",
    }
    (destination / "goal_roulette_verification.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom_zip", type=Path)
    parser.add_argument("source_animated_recipe", type=Path)
    parser.add_argument("graphics_zip", type=Path)
    parser.add_argument("rgb_profile", type=Path)
    parser.add_argument("private_scene_destination", type=Path)
    parser.add_argument("--gif-output", type=Path, help="New directory for GIF, frames and QA")
    args = parser.parse_args()
    recipe = build(args.rom_zip, args.source_animated_recipe,
                   args.graphics_zip, args.rgb_profile, args.private_scene_destination)
    print(recipe)
    if args.gif_output:
        print(json.dumps(export_goal_scene(recipe, args.gif_output), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
