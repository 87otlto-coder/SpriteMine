"""Verified-ROM player recipes and canonical small-Mario indexed silhouettes."""

import hashlib

from .rom import Rom, RomFormatError
from .sprite import sprite_pixels, sprite_tiles

ROM_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
FRAME_COUNT = 81
OFFSETS, PATTERNS, PAGES = 0x3AC10, 0x3AC61, 0x3AE47
FINGERPRINTS = {
    0x3E: (138, "59a99166faf0abdb429c7cb265dfc8333dce2cc2c8852e0ba1ac57fd87d359ac",
           "cca62efc7fa9a1d1809afed6987e8fe48348ae74a9a0f3d058a07bfe19a162d8"),
    0x3F: (174, "a04ee7c9349a05404140af3e5cc1a84eb91678b54a8be81f1e339e2454c5efe1",
           "eec9c262edcdc3d8d71036ffcbf52c74fd3e2517efdd305c75afef8693ff25ce"),
    0x40: (194, "9d97e76ab09aaf2c205fc8f25c5a4f40d66d5130a4b42b89dce03e341f03862c",
           "9d7b1ac228ca04e421b18190a0ed159688516fb73ef142601e6f9064505996bb"),
}


def _decode_recipe(image: bytes, frame: int) -> dict:
    if not 0 <= frame < FRAME_COUNT:
        raise ValueError("Recipe ID must be in 0..80")
    start = PATTERNS + 2 * image[OFFSETS + frame] - 4
    if not PATTERNS <= start <= PAGES - 6:
        raise ValueError("Recipe pointer falls outside the pattern table")
    return {
        "recipe_id": frame,
        "lookup_rom_offset": OFFSETS + frame,
        "chr_page_rom_offset": PAGES + frame,
        "chr_page_offset": image[PAGES + frame],
        "components": [
            {"pattern": pattern, "relative_oam_slot": (i + 3) % 6,
             "recipe_rom_offset": start + i, "software_hidden": pattern == 0xF1}
            for i, pattern in enumerate(image[start:start + 6])
        ],
    }


def _provenance(rom: Rom) -> dict:
    if rom.metadata.rom_sha256 != ROM_SHA256:
        raise RomFormatError("Expected exact SMB3 USA PRG1 ROM SHA-256")
    return {"provenance_type": "decoded", "decoder": "spritemine.player/1",
            "rom_sha256": rom.metadata.rom_sha256}


def inspect_recipes(rom: Rom) -> dict:
    return {**_provenance(rom), "recipes": [_decode_recipe(rom.image, i) for i in range(FRAME_COUNT)]}


def reconstruct_player(rom: Rom, frame: int) -> tuple[dict, bytes]:
    provenance = _provenance(rom)
    if frame not in FINGERPRINTS:
        raise ValueError("Canonical rendering supports recipes 0x3E, 0x3F and 0x40")
    recipe = _decode_recipe(rom.image, frame)
    page = 0x50 + recipe["chr_page_offset"]
    pages = (0, 0, 0, 0, page, 0, 0, 0)
    components = [entry for entry in recipe["components"] if not entry["software_hidden"]]
    if len(components) != 2 or any(entry["pattern"] & 193 != 1 for entry in components):
        raise ValueError("Canonical recipe must contain two sprites within PPU CHR window 4")
    sprites = []
    for entry in components:
        pattern = entry["pattern"]
        tiles = sprite_tiles(pattern, pages)
        entry["chr_page_1k"] = page
        entry["chr_tile_rom_offsets"] = [rom.metadata.chr_rom_offset + 16 * tile for tile in tiles]
        sprites.append(sprite_pixels(rom, pattern, pages))
    pixels = b"".join(sprite[row:row + 8] for row in range(0, 128, 8) for sprite in sprites)
    alpha = bytes(bool(pixel) for pixel in pixels)
    return ({
        **provenance, **recipe, "width": 16, "height": 16,
        "orientation": "canonical_unflipped", "capture_state": None,
        "opaque_pixels": sum(alpha), "transparent_pixels": len(alpha) - sum(alpha),
        "indexed_sha256": hashlib.sha256(pixels).hexdigest(),
        "alpha_sha256": hashlib.sha256(alpha).hexdigest(),
    }, pixels)


def validate_player(rom: Rom) -> dict:
    results = []
    for frame, expected in FINGERPRINTS.items():
        report, _ = reconstruct_player(rom, frame)
        actual = tuple(report[key] for key in ("opaque_pixels", "indexed_sha256", "alpha_sha256"))
        results.append({**report, "matches_reference": actual == expected})
    return {"passed": all(item["matches_reference"] for item in results), "frames": results}
