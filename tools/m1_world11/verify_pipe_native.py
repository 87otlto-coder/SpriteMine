"""Bounded screenshot-to-ROM-preview visual comparison for World 1-1's lower pipe.

This script intentionally uses the user's independent MesenCE screenshot only
as a *reference*. It never copies pixels from it into the scene recipe.

The reference screenshot is a 2x nearest-neighbor display crop, not a raw RGB24
emulator frame. Camera alignment was independently established by matching the
source-built tile boundaries and visible pit/pipe cap against the screenshot.
This verifies only the selected visible region, not the whole World 1-1 stage.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageChops

# For the uploaded screenshot image(20261122-202320).png:
#   world col 139 starts at (2224-2176)*2+1 = screen x97
#   logical row 26 starts at (416-239)*2 = screen y354
# The HUD begins at screen y384; exclude the final native row (2 display px).
WORLD_RECT = (139*16, 26*16, 8*16, 15)
WORLD_ORIGIN = (2176, 239)
SCALE = 2
SCREEN_OFFSET = (1, 0)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def compare(preview_path: Path, reference_path: Path) -> dict:
    with Image.open(preview_path) as source:
        preview = source.convert('RGB')
    with Image.open(reference_path) as screenshot:
        reference = screenshot.convert('RGB')

    if preview.size != (2816, 432):
        raise ValueError(f'Expected full-stage 2816 x 432 preview, got {preview.size}')
    if reference.width < 506 or reference.height < 384:
        raise ValueError('The MesenCE screenshot must include the 506x384 playfield crop')

    wx, wy, ww, wh = WORLD_RECT
    sx = (wx-WORLD_ORIGIN[0])*SCALE+SCREEN_OFFSET[0]
    sy = (wy-WORLD_ORIGIN[1])*SCALE+SCREEN_OFFSET[1]
    target = preview.crop((wx, wy, wx+ww, wy+wh)).resize(
        (ww*SCALE, wh*SCALE), Image.Resampling.NEAREST)
    native = reference.crop((sx, sy, sx+ww*SCALE, sy+wh*SCALE))
    # Pillow-only comparison keeps Windows CI on the project's declared
    # dependencies (Pillow + pytest); NumPy is not required.
    delta = ImageChops.difference(target, native)
    diff_bytes = delta.tobytes()
    flags = [any(diff_bytes[i:i+3]) for i in range(0,len(diff_bytes),3)]
    per_col = {}
    for col in range(139,147):
        lo=(col-139)*16*SCALE
        hi=lo+16*SCALE
        per_col[str(col)]=sum(
            flags[yy*target.width+xx]
            for yy in range(target.height) for xx in range(lo,hi))
    mismatch_count = sum(flags)
    sample_count = len(flags)
    return {
        'status': 'matched' if mismatch_count == 0 else 'mismatched',
        'reference_type': 'user_supplied_scaled_MesenCE_screenshot',
        'candidate_preview_sha256': _digest(preview_path),
        'reference_sha256': _digest(reference_path),
        'world_rect_xywh': list(WORLD_RECT),
        'screenshot_rect_xywh': [sx,sy,ww*SCALE,wh*SCALE],
        'world_origin_xy': list(WORLD_ORIGIN),
        'screenshot_offset_xy': list(SCREEN_OFFSET),
        'display_scale': SCALE,
        'unique_world_pixel_positions': ww*wh,
        'display_rgb_pixel_samples': sample_count,
        'matching_samples': sample_count-mismatch_count,
        'mismatching_samples': mismatch_count,
        'per_column_mismatches': per_col,
        'scope_limit': 'Only logical row 26 columns 139-146; excludes two bottom display rows obscured by HUD and all sprite/animation validation',
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preview_png',type=Path)
    parser.add_argument('mesence_screenshot_png',type=Path)
    parser.add_argument('report_json',type=Path)
    args=parser.parse_args()
    result=compare(args.preview_png,args.mesence_screenshot_png)
    if args.report_json.exists():
        parser.error(f'Refusing to overwrite existing report {args.report_json}')
    args.report_json.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f"{result['matching_samples']}/{result['display_rgb_pixel_samples']} "
          f"pixels match, {result['mismatching_samples']} mismatch")
    print(f'Report: {args.report_json}')
    return 0 if result['mismatching_samples']==0 else 1


if __name__=='__main__':
    raise SystemExit(main())
