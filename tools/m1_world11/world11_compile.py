"""Read-only, incomplete source-driven World 1-1 Plains logical-map compiler.

This implements *only* the operations listed in SUPPORTED. Unknown operations
are preserved and cause `complete=False`. It never substitutes artwork or
claims that a static map is an observed PPU framebuffer.

Source interpretation: SMB3 US PRG1 layout and the Southbird disassembly
(https://github.com/captainsouthbird/smb3, 09b1bd81a788de8ceec664a34094e84ddb463117).
Only original Python logic and small numeric definitions are used here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

HEADER_OFFSET = 0x1FB92
STREAM_OFFSET = 0x1FB9B
STREAM_LEN = 264
STREAM_SHA = 'ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a'
ROM_SHA = '4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579'
COLS, ROWS, SCREENS = 176, 27, 11
SKY = 0x80
# Source-derived Plains ground tile IDs (top and interior rows).  In the
# generated *visible* static scene these remain visible when a vertical pipe
# body overlaps the already-placed floor.  This is independently observed in
# the provided native gameplay screenshot at World 1-1 columns 139-146, row 26.
# Source-level instruction replay/order is still provisional, so retain a
# ledger of suppressed pipe writes rather than claiming exact Tile_Mem replay.
GROUND_TILES = frozenset((0x53, 0x54, 0x55, 0x56, 0x57, 0x58))

# These values describe logical tile IDs, not CHR pattern indices.
BLOCK_RUN = {15: 0x67, 16: 0x63, 17: 0x6B, 18: 0x79,
             19: 0xBC, 20: 0x2E, 21: 0x72, 22: 0x40}
POWER_FIXED = {16 + i: n for i, n in enumerate((
    0x60, 0x61, 0x62, 0x64, 0x65, 0x66, 0x68, 0x69,
    0x6A, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x44, 0x45,
    0x03, 0x2F, 0x30, 0x31, 0x73, 0x74, 0x75, 0x46, 0xF2))}
SUPPORTED_GENERATORS = set(BLOCK_RUN) | {0, 1, 2, 3, 5, 8, 9, 10, 11, 12, 13, 23, 24, 25}
SUPPORTED_FIXED = set(POWER_FIXED) | {0, 1, 2, 7, 41}


@dataclass(frozen=True)
class Command:
    offset: int          # Absolute ROM file offset
    relative: int        # Offset within layout stream
    kind: str            # generator, fixed, junction
    index: int
    x: int               # World column, not screen pixels
    y: int               # World row
    shape: int
    extra: int | None = None


def parse_stream(stream: bytes) -> list[Command]:
    """Parse variable-length instructions without silently losing alignment."""
    commands: list[Command] = []
    cursor = 0
    while cursor < len(stream):
        if stream[cursor] == 0xFF:
            if cursor != len(stream) - 1:
                raise ValueError('Premature World 1-1 stream terminator')
            return commands
        if cursor + 3 > len(stream):
            raise ValueError('Truncated three-byte instruction')
        first, second, shape = stream[cursor:cursor + 3]
        if first & 0xE0 == 0xE0:
            kind, idx = 'junction', first & 0x1F
        elif shape & 0xF0:
            kind, idx = 'generator', (first >> 5) * 15 + (shape >> 4) - 1
        else:
            kind, idx = 'fixed', (first >> 5) * 16 + shape
        extra = None
        if kind == 'generator' and idx in (11, 12, 35, 36, 37, 38, 39, 40, 41, 42):
            if cursor + 4 > len(stream):
                raise ValueError('Truncated extended instruction')
            extra = stream[cursor + 3]
        # Main horizontal-level command: screen from high nibble of second,
        # column within screen from low nibble; row from first byte low 5 bits.
        x = ((second >> 4) * 16 + (second & 0x0F))
        y = first & 0x1F
        commands.append(Command(STREAM_OFFSET + cursor, cursor, kind,
                                idx, x, y, shape, extra))
        cursor += 4 if extra is not None else 3
    raise ValueError('Missing 0xFF layout terminator')


class Layout:
    """Explicit writer and source ledger, with unknown construction commands."""

    def __init__(self, image: bytes | None = None):
        self.image = image
        self.provisional: list[dict] = []
        self.tiles = [[SKY] * COLS for _ in range(ROWS)]
        self.writers = [[None] * COLS for _ in range(ROWS)]
        self.overwrites: list[dict] = []
        self.unsupported: list[dict] = []
        self.executed: list[int] = []
        self.junctions: list[dict] = []
        self.random_clouds_unknown = False
        self.pipe_ground_overlaps: list[dict] = []

    def put(self, x: int, y: int, tile: int, command: Command):
        if not (0 <= x < COLS and 0 <= y < ROWS):
            raise ValueError(f'Generator {command.index} at {command.relative:#x} writes outside map: {x},{y}')
        old = self.tiles[y][x]
        if self.writers[y][x] is not None and old != tile:
            self.overwrites.append({'x': x, 'y': y, 'from': old, 'to': tile,
                                    'previous': self.writers[y][x], 'writer': command.offset})
        self.tiles[y][x] = tile
        self.writers[y][x] = command.offset

    def run(self, commands: list[Command]):
        for c in commands:
            if c.kind == 'junction':
                self.junctions.append(asdict(c))
                continue
            if c.kind == 'generator':
                if c.index not in SUPPORTED_GENERATORS:
                    self.unsupported.append({**asdict(c), 'reason': 'generator not implemented'})
                    continue
                self._generator(c)
            elif c.index == 3:
                self.random_clouds_unknown = True
                self.unsupported.append({**asdict(c), 'reason': 'randomized clouds require original RNG state'})
                continue
            elif c.kind == 'fixed' and c.index in SUPPORTED_FIXED:
                self._fixed(c)
            else:
                self.unsupported.append({**asdict(c), 'reason': 'fixed-size generator not implemented'})
                continue
            self.executed.append(c.offset)
        return self

    def _fixed(self, c: Command):
        if c.index in (0, 1, 2):
            if self.image is None:
                raise ValueError('Bush construction needs the verified local ROM image')
            # The original bush shape templates are read from the user's ROM;
            # no game level tables are bundled with the source code.
            offset = 0x1CB61
            lengths = (21, 13, 49)  # including FF terminators
            start = offset + sum(lengths[:c.index])
            data = self.image[start:start + lengths[c.index]]
            width = (5, 4, 6)[c.index]
            if len(data) != lengths[c.index] or data[-1] != 0xFF:
                raise ValueError('Unexpected original bush template data')
            cells = data[:-1]
            if len(cells) % width:
                raise ValueError('Malformed bush shape')
            for dy in range(len(cells) // width):
                for dx in range(width):
                    n = cells[dy * width + dx]
                    if n == SKY:
                        continue
                    x, y = c.x + dx, c.y + dy
                    old = self.tiles[y][x]
                    if n not in (0x92, 0x93) and 0x90 <= old < 0x9F and old != n:
                        n = n + 2 if n < 0x94 else 0x98
                    if old != n:
                        self.put(x, y, n, c)
        elif c.index == 7:
            self.put(c.x, c.y, 0x06, c)
        elif c.index == 41:
            if self.image is None:
                raise ValueError('Goal construction needs the verified ROM')
            # Fills the last part of the preceding screen and the final one.
            for row in range(26):
                self.put(c.x, row, 0x01, c)
                for col in range(c.x + 1, COLS):
                    self.put(col, row, 0x00, c)
            # The goal command ends screen 9; native loader advances to the
            # following 16-column screen before writing the 16x6 decoration
            # at logical rows 20..25. Do not hardcode World 1-1's x=160.
            deco_x = (c.x//16 + 1)*16
            if deco_x + 16 > COLS or c.y != 0:
                raise ValueError('Unsupported goal decoration location')
            deco = self.image[0x1C8F7:0x1C8F7 + 96]
            if len(deco) != 96 or deco[:4] != b'\x00\x00\x13\x14':
                raise ValueError('Unexpected original goal decoration table')
            for dy in range(6):
                for dx in range(16):
                    self.put(deco_x + dx, 20 + dy, deco[dy*16 + dx], c)
            self.provisional.append({'source_offset': c.offset,
                  'reason': 'Goal placement logic derived from static code; runtime map equality pending'})
        else:
            self.put(c.x, c.y, POWER_FIXED[c.index], c)
            if c.index == 29:
                # The game also blanks the cell above a P-Switch brick.
                self.put(c.x, c.y-1, 0xC1, c)

    def _generator(self, c: Command):
        x, y = c.x, c.y
        width = (c.shape & 0x0F) + 1
        idx = c.index
        if idx in (0, 1, 2, 3):
            tops = ((0x26, 0x25, 0x27), (0x51, 0x50, 0x52),
                    (0xA1, 0xA0, 0xA2), (0xE3, 0xE2, 0xE4))
            mids = ((0x07, 0x09, 0x08), (0x47, 0x49, 0x48),
                    (0x87, 0x89, 0x88), (0xC7, 0xC9, 0xC8))
            bottoms = ((0x0D, 0x0A, 0x0E), (0x4D, 0x4A, 0x4E),
                       (0x8D, 0x8A, 0x8E), (0xCD, 0xCA, 0xCE))
            for dx in range(width):
                edge = 0 if dx == 0 else 2 if dx == width-1 else 1
                col = x + dx
                # The native generator searches for a ground-top tile, then
                # ends the block in the row immediately above that floor.
                ground = next((row for row in range(y+1, ROWS)
                               if self.tiles[row][col] in (0x53, 0x55)), None)
                if ground is None or ground < y + 2:
                    raise ValueError(f'No usable ground beneath big block at {col},{y}')
                self.put(col, y, tops[idx][edge], c)
                for row in range(y+1,ground-1):
                    self.put(col, row, mids[idx][edge], c)
                self.put(col, ground-1, bottoms[idx][edge], c)
            # The adjacent right-side shadow is generated after the body.
            # It alters existing blocks/bush tiles or paints sky, and stops
            # at ground-top tiles. Preserve write order as an overlay.
            shadow_x = x + width
            if shadow_x < COLS:
                old = self.tiles[y][shadow_x]
                if old == SKY:
                    top_shadow = 0xC0
                elif 0x90 <= old < 0x9F:
                    top_shadow = 0x9D
                else:
                    top_shadow = (old & 0xC0) | 0x0B
                self.put(shadow_x, y, top_shadow, c)
                shadows = {}
                for color_shift in (0x00, 0x40, 0x80, 0xC0):
                    shadows.update({color_shift + key: color_shift + value for key, value in
                                   ((0x07,0x0C),(0x09,0x0C),(0x0A,0x0F),(0x0D,0x0F))})
                shadows.update({0x90:0x99,0x94:0x9E,0x91:0x9A,0x95:0x9F,
                                0x92:0x9B,0x96:0x9E,0x93:0x9C,0x97:0x9E,0x98:0x9E})
                for row in range(y+1, ROWS):
                    old = self.tiles[row][shadow_x]
                    if old in (0x53,0x57):
                        break
                    self.put(shadow_x,row,shadows.get(old,0xC4),c)
            self.provisional.append({'source_offset': c.offset,
                  'reason': 'Source-modeled big-block shadow requires independent native tile-map validation'})
        elif idx == 5:
            # Four-wide, three-high floating block with a right-hand shadow.
            # The code selects color by generator index, and the low shape
            # nibble holds the body width (not its shadow).
            color = idx - 4
            rows = ((0x51, 0x50, 0x52), (0x4D, 0x4A, 0x4E),
                    (0xC2, 0xC5, 0xC5))
            for dy in range(3):
                for dx in range(width-1):
                    edge = 0 if dx == 0 else 2 if dx == width-2 else 1
                    self.put(x + dx, y+dy, rows[dy][edge], c)
                self.put(x + width-1, y+dy, (0xC0, 0xC4, 0xC3)[dy], c)
            self.provisional.append({'source_offset': c.offset,
                  'reason': 'Floating-block shadow colors need independent map validation'})
        elif idx in BLOCK_RUN:
            for dx in range(width):
                self.put(x + dx, y, BLOCK_RUN[idx], c)
        elif idx == 8:
            for dx in range(width):
                self.put(x + dx, y, 0x86, c)
        elif idx == 10:
            for dx in range(width):
                self.put(x + dx, y, 0x2C, c)
        elif idx == 13:
            # Two-high clouds: left / repeating middle / right.
            for dy, row in enumerate(((0x1F, 0x20, 0x21), (0x22, 0x23, 0x24))):
                for dx in range(width):
                    tile = row[0] if dx == 0 else row[2] if dx == width-1 else row[1]
                    self.put(x + dx, y + dy, tile, c)
        elif idx in (11, 12):
            if c.extra is None or c.extra < 1:
                raise ValueError('Ground run missing positive extended width')
            # Ground routines create width+1 columns, with edge caps.
            span = c.extra + 1
            height = width
            table = ((0x55, 0x53, 0x57), (0x56, 0x54, 0x58)) if idx == 11 else (
                    (0xF6, 0xF4, 0xF8), (0xF7, 0xF5, 0xF9))
            for dy in range(height):
                left, middle, right = table[0 if dy == 0 else 1]
                for dx in range(span):
                    self.put(x + dx, y + dy,
                             left if dx == 0 else right if dx == span - 1 else middle, c)
        elif idx in (23, 24, 25):
            caps = {23: (0xAD, 0xAE), 24: (0xB1, 0xB2), 25: (0xAF, 0xB0)}
            left, right = caps[idx]
            self.put(x, y, left, c)
            self.put(x + 1, y, right, c)
            # The source routine emits (low nibble + 1) body rows.  A literal
            # single-pass replay overwrites the ground under pipes because our
            # current compiler does not model the game's screen-loading order.
            # The native gameplay screenshot independently shows floor at row
            # 26 under the lower pipe and nearby shorter pipe, with the narrow
            # pit immediately to the left.  Retain existing ground there and
            # record each suppressed pipe write as provisional, rather than
            # shortening the pipe's source-defined body count or filling pits.
            for dy in range(1, width + 1):
                row = y + dy
                for col, pipe_tile in ((x, 0xBA), (x + 1, 0xBB)):
                    previous = self.tiles[row][col]
                    if previous in GROUND_TILES:
                        self.pipe_ground_overlaps.append({
                            'x': col, 'y': row,
                            'retained_ground_tile': previous,
                            'suppressed_pipe_tile': pipe_tile,
                            'pipe_command_offset': c.offset,
                            'previous_ground_writer_offset': self.writers[row][col],
                        })
                    else:
                        self.put(col, row, pipe_tile, c)
        elif idx == 9:
            # Right ground edge, empty gap, then left edge. The original pit
            # routine runs downward to the end of the logical screen.
            for dy in range(ROWS - y):
                first, last = (0x57, 0x55) if dy == 0 else (0x58, 0x56)
                self.put(x, y + dy, first, c)
                for dx in range(1, width - 1):
                    self.put(x + dx, y + dy, SKY, c)
                self.put(x + width - 1, y + dy, last, c)
        else:
            raise AssertionError(f'unsupported generator reached: {idx}')

    def summary(self, commands: list[Command], rom_sha: str) -> dict:
        return {
            'format': 'spritemine.world11.partial_logical/1',
            'source_class': 'partial_decoded', 'native_render_verified': False,
            'rom_sha256': rom_sha, 'stream_sha256': STREAM_SHA,
            'canvas_tiles': [COLS, ROWS], 'nominal_pixels': [COLS * 16, ROWS * 16],
            'command_count': len(commands),
            'executed_commands': len(self.executed), 'unsupported_commands': self.unsupported,
            'junctions': self.junctions,
            'random_clouds_unknown': self.random_clouds_unknown,
            'provisional_commands': self.provisional,
            'goal_edge_tile': 0x01,
            'goal_filler_tile': 0x00,
            'goal_edge_shape': 'authentic zigzag, not an image corruption',
            'written_cell_count': sum(t is not None for row in self.writers for t in row),
            'overwrites': self.overwrites,
            'pipe_ground_overlaps': self.pipe_ground_overlaps,
            'pipe_ground_overlap_status': 'visually_confirmed_for_row_26_cols_139_to_146_only; source write ordering unresolved',
            'tile_id_counts': dict(sorted(Counter(
                t for row in self.tiles for t in row).items())),
            'caveat': 'Unwritten sky is an initialization value, not a validated final tile. Unsupported generators and RNG may overwrite it.',
        }


def compile_image(image: bytes) -> tuple[list[Command], Layout, dict]:
    digest = sha256(image).hexdigest()
    if digest != ROM_SHA:
        raise ValueError('SMB3 US PRG1 image fingerprint mismatch')
    header = image[HEADER_OFFSET:STREAM_OFFSET]
    if len(header) != 9 or ((header[4] & 0x0F) + 1) != SCREENS:
        raise ValueError('Unexpected main level header')
    stream = image[STREAM_OFFSET:STREAM_OFFSET + STREAM_LEN]
    if sha256(stream).hexdigest() != STREAM_SHA:
        raise ValueError('World 1-1 stream fingerprint mismatch')
    commands = parse_stream(stream)
    if len(commands) != 86 or Counter(c.kind for c in commands) != {
        'generator': 71, 'fixed': 14, 'junction': 1,
    }:
        raise ValueError('Unexpected World 1-1 construction command counts')
    model = Layout(image).run(commands)
    return commands, model, model.summary(commands, digest)


def diagnostic_image(model: Layout):
    """Category heatmap only. NOT SMB3 original game graphics."""
    from PIL import Image, ImageDraw
    colors = {'sky': (205, 226, 238), 'ground': (114, 83, 52),
              'pipe': (63, 138, 94), 'cloud': (241, 241, 230),
              'bush': (77, 147, 84), 'block': (201, 137, 62),
              'coin': (238, 194, 63), 'other': (159, 148, 180)}
    out = Image.new('RGB', (COLS*16, ROWS*16), colors['sky'])
    draw = ImageDraw.Draw(out)
    for y, row in enumerate(model.tiles):
        for x, n in enumerate(row):
            if n == SKY: continue
            kind = ('ground' if n in (0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9)
                    else 'pipe' if 0xAD <= n <= 0xBB
                    else 'cloud' if 0x1F <= n <= 0x24 or n == 0x2C
                    else 'bush' if 0x86 <= n <= 0x9F
                    else 'coin' if n == 0x40
                    else 'block' if n in set(BLOCK_RUN.values()) | set(POWER_FIXED.values())
                    else 'other')
            draw.rectangle((x*16, y*16, x*16+15, y*16+15),fill=colors[kind])
    for x in range(0, COLS+1,16):
        xx=x*16
        draw.line([(xx,0),(xx,432)],fill=(74,96,112),width=1)
    return out


def main():
    import zipfile
    parser=argparse.ArgumentParser(description='Create a partial read-only World 1-1 source layout diagnostic')
    parser.add_argument('rom_zip',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with zipfile.ZipFile(args.rom_zip) as z:
        members=[i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith('.nes')]
        if len(members) != 1:
            raise ValueError('ZIP must contain exactly one NES image')
        image=z.read(members[0])
    commands,layout,report=compile_image(image)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'partial_layout_report.json').write_text(json.dumps(report,indent=2)+'\n')
    diagnostic_image(layout).save(args.output/'partial_layout_diagnostic.png')
    print(f"commands {len(commands)}, executed {len(layout.executed)}, unresolved {len(layout.unsupported)}")
    print(f"source-written cells {report['written_cell_count']}/{COLS*ROWS}")
    print('WARNING: diagnostic only, no native RGB or full-layout acceptance')

if __name__=='__main__':
    main()
