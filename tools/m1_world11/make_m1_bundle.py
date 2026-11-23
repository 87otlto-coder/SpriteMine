"""Private local ROM-to-partial-World-1-1 scene recipe, preview and report.

No extracted Nintendo assets should be committed to the public repository.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict
from pathlib import Path
from world11_compile import compile_image, diagnostic_image
from preview_tiles import (render, export_private_scene_bundle,
                           load_native_graphics_profile, decode_native_graphics_profile, PAGES, PALETTES)


def load_single_rom_zip(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        matches=[item for item in archive.infolist()
                 if not item.is_dir() and item.filename.lower().endswith('.nes')]
        if len(matches)!=1:
            raise ValueError('ZIP must contain exactly one .nes image')
        if matches[0].file_size>1024*1024:
            raise ValueError('Unexpected oversized ROM')
        return archive.read(matches[0])


def build(rom_zip: Path, output: Path, *, ppu: Path|None=None,
          palette: Path|None=None, rgb: Path|None=None,
          graphics_zip: Path|None=None):
    if output.exists():
        raise FileExistsError(f'Output exists; refusing to overwrite: {output}')
    if graphics_zip is not None:
        if ppu is not None or palette is not None or rgb is None:
            raise ValueError('With graphics_zip supply only --rgb-profile, not individual dumps')
    elif any(p is not None for p in (ppu,palette,rgb)) and not all(
            p is not None for p in (ppu,palette,rgb)):
        raise ValueError('Provide all three native graphics files, or none')
    raw=load_single_rom_zip(rom_zip)
    commands, layout, report=compile_image(raw)
    if graphics_zip is not None:
        with zipfile.ZipFile(graphics_zip) as archive:
            files=[name for name in archive.namelist() if not name.endswith('/')]
            ppu_files=[name for name in files if name.endswith('-start-ppu.bin')]
            pal_files=[name for name in files if name.endswith('-start-palette.bin')]
            if len(ppu_files)!=1 or len(pal_files)!=1 or (
                    ppu_files[0].split('-start-')[0] != pal_files[0].split('-start-')[0]):
                raise ValueError('Capture ZIP must contain exactly one same-frame PPU/palette pair')
            pages, groups, provenance=decode_native_graphics_profile(
                raw,archive.read(ppu_files[0]),archive.read(pal_files[0]),rgb.read_bytes())
            provenance.update({'capture_zip_sha256':__import__('hashlib').sha256(
                graphics_zip.read_bytes()).hexdigest(),'capture_frame':ppu_files[0].split('/')[-1].split('-')[0]})
    elif ppu is not None:
        pages, groups, provenance=load_native_graphics_profile(raw,ppu,palette,rgb)
    else:
        pages, groups, provenance=PAGES, PALETTES, None
    recipe_path=export_private_scene_bundle(
        raw,layout,report,output/'scene',page_mapping=pages,
        palette_groups=groups,graphics_provenance=provenance)
    (output/'partial_layout_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (output/'source_command_ledger.json').write_text(json.dumps({
        'source_class':'ROM_parsed_commands_source_model',
        'commands':[asdict(c) for c in commands],
        'source_offset_note':'offsets point into immutable iNES image',
        'native_verified':False,
    },indent=2)+'\n',encoding='utf-8')
    (output/'source_tile_ledger.json').write_text(json.dumps({
        'source_class':'provisional_decoded',
        'canvas':[176,27],
        'logical_tile_ids':layout.tiles,
        'last_writer_ROM_offset_or_null':layout.writers,
        'source_model_written_cells':report['written_cell_count'],
        'unknown_cloud_placement':report['random_clouds_unknown'],
        'pipe_floor_visual_overlap_corrections': report['pipe_ground_overlaps'],
        'pipe_floor_correction_status': report['pipe_ground_overlap_status'],
        'native_verified_cells':0,
        'provisional_source_offsets':[x['source_offset'] for x in report['provisional_commands']],
        'warning':'Null last-writer means initialized SKY, NOT proven final gameplay sky.',
    },indent=2)+'\n',encoding='utf-8')
    diagnostic_image(layout).save(output/'partial_layout_diagnostic.png')
    preview=render(raw,layout,page_mapping=pages,palette_groups=groups)
    preview.save(output/'partial_chr_preview.png')
    print(f'Parsed {report["command_count"]} World 1-1 layout commands; '
          f'modeled {report["executed_commands"]}; '
          f'{len(report["unsupported_commands"])} unresolved')
    print(f'Wrote {report["written_cell_count"]}/4752 cells with command provenance; '
          'the rest are source-initialized sky, not validated gameplay')
    print('Scene recipe:',recipe_path)
    print('Warning: partial model and globally sampled graphics, not native RGB acceptance')
    return recipe_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom_zip',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--ppu-snapshot',type=Path)
    parser.add_argument('--palette-ram',type=Path)
    parser.add_argument('--rgb-profile',type=Path)
    parser.add_argument('--frame-graphics-zip',type=Path)
    args=parser.parse_args()
    build(args.rom_zip,args.output,ppu=args.ppu_snapshot,palette=args.palette_ram,
          rgb=args.rgb_profile, graphics_zip=args.frame_graphics_zip)


if __name__=='__main__':
    main()
