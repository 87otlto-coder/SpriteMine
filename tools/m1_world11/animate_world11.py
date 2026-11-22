"""SMB3 World 1-1 four-phase ROM-backed background animation scene builder.

Private assets are generated locally from a verified ROM and frame-local
MesenCE palette/PPU snapshot. This does not copy/reference capture RGB pixels
as artwork, does not patch the ROM, and does not publish game graphics.

Ordinary level PT2_Anim bank cycle: 0x60, 0x62, 0x64, 0x66, changing
on Counter_1 bits 3-4 (8 emulator ticks per phase). Source: pinned Southbird
SMB3 disassembly PRG/prg030.asm, PT2_Anim and PRG030_8E4F.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from PIL import Image

from make_m1_bundle import load_single_rom_zip
from preview_tiles import ROM_QUADS, ROM_QUAD_SHA, ROM_SHA, decode_native_graphics_profile

PHASE_BANK_BASES = (0x60, 0x62, 0x64, 0x66)
PHASE_NES_TICKS = 8
# First output tick is tied to the actual supplied MesenCE frame 450840
# (background pages 100/101). Subsequent phases use observed source order.
START_PAIR = (100, 101)
GIF_MS_PER_PHASE = 130  # 10ms GIF granularity, versus ~133.1 ms/8 NTSC ticks.
DISASSEMBLY_COMMIT = '09b1bd81a788de8ceec664a34094e84ddb463117'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bank_cycle(start_pair: tuple[int,int]) -> tuple[tuple[int,int],...]:
    pairs = tuple((b, b+1) for b in PHASE_BANK_BASES)
    if start_pair not in pairs:
        raise ValueError('Capture frame is not one of the regular four bank phases')
    idx = pairs.index(start_pair)
    return pairs[idx:]+pairs[:idx]


def decode_metatile(chr_rom: bytes, quad_table: bytes, tile_id: int,
                    pages: tuple[int,int,int,int], palette_groups) -> Image.Image:
    """Independently decode all four 8x8 2bpp patterns, not captured RGB."""
    if len(chr_rom) != 0x20000 or len(quad_table) != 1024:
        raise ValueError('Unexpected ROM graphics data lengths')
    if not 0 <= tile_id < 256 or len(pages)!=4:
        raise ValueError('Invalid tile ID or page mapping')
    if any(not 0 <= x < 128 for x in pages):
        raise ValueError('CHR page is outside verified ROM')
    img = Image.new('RGB',(16,16))
    out=img.load()
    rgb=palette_groups[tile_id>>6]
    for qi,dx,dy in ((0,0,0),(1,0,8),(2,8,0),(3,8,8)):
        pattern=quad_table[qi*256+tile_id]
        address=pattern*16
        physical=pages[address//1024]*1024+(address%1024)
        src=chr_rom[physical:physical+16]
        for y in range(8):
            for x in range(8):
                shift=7-x
                code=((src[y]>>shift)&1)|(((src[y+8]>>shift)&1)<<1)
                out[dx+x,dy+y]=rgb[code]
    return img


def read_graphics_zip(graphics_zip: Path, rgb_profile: Path, rom: bytes):
    with zipfile.ZipFile(graphics_zip) as archive:
        names=[n for n in archive.namelist() if not n.endswith('/')]
        p=[n for n in names if n.endswith('-start-ppu.bin')]
        c=[n for n in names if n.endswith('-start-palette.bin')]
        if len(p)!=1 or len(c)!=1 or p[0].rsplit('-start-',1)[0] != c[0].rsplit('-start-',1)[0]:
            raise ValueError('Expected exactly one same-frame PPU and palette capture')
        pages, palettes, provenance=decode_native_graphics_profile(
            rom,archive.read(p[0]),archive.read(c[0]),rgb_profile.read_bytes())
        provenance['capture_frame']=p[0].rsplit('/',1)[-1].split('-')[0]
        provenance['capture_zip_sha256']=sha(graphics_zip.read_bytes())
    return tuple(pages),palettes,provenance


def build(rom_zip: Path, source_recipe: Path, graphics_zip: Path,
          rgb_profile: Path, destination: Path) -> Path:
    """Write a new, source-backed private recipe. Never touch the input recipe."""
    if destination.exists():
        raise FileExistsError(f'Refusing to replace previous private scene: {destination}')
    raw=load_single_rom_zip(rom_zip)
    if sha(raw)!=ROM_SHA:
        raise ValueError('ROM fingerprint mismatch')
    quad=raw[ROM_QUADS:ROM_QUADS+1024]
    if sha(quad)!=ROM_QUAD_SHA:
        raise ValueError('Plains quadrant table fingerprint mismatch')
    chr_rom=raw[16+0x40000:16+0x40000+0x20000]
    pages,groups,profile=read_graphics_zip(graphics_zip,rgb_profile,raw)
    if pages!=(8,9,100,101):
        raise ValueError('Expected synchronized 450840 main-area graphics pages [8,9,100,101]')
    existing=json.loads(source_recipe.read_text('utf8'))
    if existing['size']!=[2816,432] or existing['tile_size']!=[16,16] or existing['ticks']!=1:
        raise ValueError('Expected the static 176x27 scene from the source compiler')
    if len(existing['layers'])!=1 or len(existing['layers'][0].get('tiles',[]))!=27:
        raise ValueError('Expected exactly one 27-row static tile layer')
    tiles=existing['layers'][0]['tiles']
    if any(len(row)!=176 for row in tiles):
        raise ValueError('Expected 176 columns in every source row')
    base_prov=existing['staging_provenance']['graphics_snapshot_provenance']
    if (base_prov.get('mapped_chr_pages')!=[8,9,100,101] or
        base_prov.get('ppu_sha256')!=profile['ppu_sha256'] or
        base_prov.get('palette_sha256')!=profile['palette_sha256'] or
        base_prov.get('rgb_profile_sha256')!=profile['rgb_profile_sha256']):
        raise ValueError('Scene is not based on the matching frame-local graphics snapshot')

    tile_names={name for row in tiles for name in row}
    for name in tile_names:
        if not name.startswith('tile_') or len(name)!=7:
            raise ValueError(f'Unexpected tile asset name: {name!r}')
        tile_id=int(name[5:],16)
        expected=decode_metatile(chr_rom,quad,tile_id,pages,groups)
        spec=existing['assets'][name]
        asset=(source_recipe.parent/spec['file']).resolve()
        if not asset.is_relative_to(source_recipe.parent.resolve()):
            raise ValueError('Static asset path escapes recipe directory')
        data=asset.read_bytes()
        if sha(data)!=spec['sha256']:
            raise ValueError(f'Static PNG hash mismatch: {name}')
        with Image.open(asset) as img:
            if img.convert('RGB').tobytes()!=expected.tobytes():
                raise ValueError(f'Static PNG differs from source CHR: {name}')

    phase_pairs=bank_cycle((pages[2],pages[3]))
    phases={}
    changing={}
    for name in sorted(tile_names):
        tile_id=int(name[5:],16)
        pics=[decode_metatile(chr_rom,quad,tile_id,(pages[0],pages[1],*pair),groups)
              for pair in phase_pairs]
        phases[name]=pics
        if len({pic.tobytes() for pic in pics})>1:
            changing[name]=pics
    if not changing:
        raise ValueError('No changing tile IDs found; cannot claim animation')
    # Capture phase must be *exactly* the base static scene for any cell.
    for name,pics in phases.items():
        with Image.open(source_recipe.parent/existing['assets'][name]['file']) as orig:
            if pics[0].tobytes()!=orig.convert('RGB').tobytes():
                raise AssertionError('Phase 0 does not reproduce the real MesenCE graphics snapshot')

    try:
        destination.mkdir(parents=True)
        for name,spec in existing['assets'].items():
            src=source_recipe.parent/spec['file']
            dst=destination/spec['file']
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
        anim_assets={}
        for name,pics in changing.items():
            for j,pic in enumerate(pics):
                pair=phase_pairs[j]
                asset_name=f'anim_{name}_phase{j}'
                path=Path('animation')/f'{name}_bank{pair[0]:02x}_{pair[1]:02x}.png'
                target=destination/path
                target.parent.mkdir(parents=True,exist_ok=True)
                pic.save(target)
                anim_assets[asset_name]={
                    'file':path.as_posix(),
                    'sha256':sha(target.read_bytes()),
                    'provenance':{
                        'kind':'ROM_2bpp_bank_switched_background_phase',
                        'logical_tile_id':int(name[5:],16),
                        'phase':j,'chr_2k_bank_base':pair[0],
                        'chr_1k_pages':list(pair),
                        'rom_sha256':ROM_SHA,
                        'quadrant_sha256':ROM_QUAD_SHA,
                        'palette_source_frame':profile['capture_frame'],
                        'palette_sha256':profile['palette_sha256'],
                    },
                }
        tracks=[]
        counts=Counter()
        for row,entries in enumerate(tiles):
            for column,name in enumerate(entries):
                if name not in changing:
                    continue
                tracks.append({
                    'at':[column*16,row*16],
                    'cels':[{'asset':f'anim_{name}_phase{j}','ticks':1}
                            for j in range(len(phase_pairs))],
                    'phase':0,
                })
                counts[name]+=1
        if not tracks:
            raise AssertionError('Changing source tiles have no cell placements')
        result=dict(existing)
        result['ticks']=len(phase_pairs)
        result['tick_ms']=GIF_MS_PER_PHASE
        result['assets']={**existing['assets'],**anim_assets}
        result['layers']=[existing['layers'][0],{'tracks':tracks}]
        result['staging_provenance']={
            **existing['staging_provenance'],
            'animation':{
                'source':'captainsouthbird/smb3 pinned PRG/prg030.asm PT2_Anim/PRG030_8E4F',
                'disassembly_commit':DISASSEMBLY_COMMIT,
                'game_frames_per_phase':PHASE_NES_TICKS,
                'chr_2k_bank_sequence':[list(x) for x in phase_pairs],
                'initial_mapped_bg_chr_pages':list(pages),
                'capture_frame':profile['capture_frame'],
                'tick_ms':GIF_MS_PER_PHASE,
                'timing': 'approximate GIF 130ms per 8 NTSC (~133ms) ticks; fixed 10ms granularity',
                'source_timing_class':'decoded_game_counter_logic_not_emulator_frame_timeline',
                'dynamic_tile_ids':[int(n[5:],16) for n in sorted(changing)],
                'track_count':len(tracks),
                'non_camera_background_animation':True,
                'native_full_stage_rgb_verified':False,
                'unknown_random_clouds_remain':True,
                'note':'Source-derived phase graphics, not an exact gameplay capture of all stage positions.',
            },
        }
        recipe=destination/'recipe.json'
        recipe.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf8')
        (destination/'animation_report.json').write_text(json.dumps({
            'rom_sha256':sha(raw),
            'source_recipe_sha256':sha(source_recipe.read_bytes()),
            'recipe_sha256':sha(recipe.read_bytes()),
            'graphics_capture_zip_sha256':sha(graphics_zip.read_bytes()),
            'rgb_profile_sha256':sha(rgb_profile.read_bytes()),
            'phase_banks':[list(x) for x in phase_pairs],
            'phase_hold_ms':GIF_MS_PER_PHASE,
            'game_frames_per_phase':PHASE_NES_TICKS,
            'gif_loop_ms':GIF_MS_PER_PHASE*4,
            'source_dynamic_tiles':{name:counts[name] for name in sorted(counts)},
            'track_count':len(tracks),
            'animated_assets':len(anim_assets),
            'static_cells_untouched':True,
            'native_full_stage_accepted':False,
        },sort_keys=True,indent=2)+'\n',encoding='utf8')
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True)
        raise
    return recipe



def export_animated_scene(recipe: Path, export_dir: Path) -> dict:
    """Use the real PR #29 Scene/scene_export APIs; write lossless PNG frames.

    We require the GIF decoder to recover every RGB pixel of all output ticks,
    otherwise the export is not accepted as lossless pixel-art composition.
    """
    from spritemine.scene import Scene
    from spritemine.scene_export import export

    scene = Scene.load(recipe)
    if scene.ticks != 4 or scene.size != (2816,432):
        raise ValueError('Expected M1 4-tick, full 2D animated scene')
    manifest=export(recipe,export_dir)
    frame_dir=export_dir/'frames'
    frame_dir.mkdir()
    pnames=[]
    images=[]
    for tick in range(scene.ticks):
        image=scene.render(tick)
        image_path=frame_dir/f'world11_{tick:02d}.png'
        image.save(image_path)
        pnames.append((image_path.relative_to(export_dir).as_posix(),sha(image_path.read_bytes())))
        images.append(image)

    from PIL import Image
    with Image.open(export_dir/'scene.gif') as gif:
        if gif.n_frames != scene.ticks or gif.size != scene.size or gif.info.get('loop') != 0:
            raise ValueError('GIF loop metadata or dimensions differ from scene')
        for tick in range(scene.ticks):
            gif.seek(tick)
            if gif.info.get('duration')!=scene.tick_ms:
                raise ValueError('GIF frame duration differs from recipe')
            if gif.convert('RGB').tobytes()!=images[tick].tobytes():
                raise ValueError('GIF loses RGB pixels; refuse the animation export')
    if len({img.tobytes() for img in images})!=4:
        raise ValueError('Animation contains duplicate/identical full-scene ticks')
    report={
        'scene_recipe_sha256':sha(recipe.read_bytes()),
        'gif_sha256':sha((export_dir/'scene.gif').read_bytes()),
        'png_frame_sha256':dict(pnames),
        'tick_ms':scene.tick_ms,
        'loop_ms':scene.ticks*scene.tick_ms,
        'ticks':scene.ticks,
        'gif_rgb_matches_all_png_frames':True,
        'gif_loops':True,
        'static_first_tick_matches_source_snapshot':True,
        'native_full_stage_accepted':False,
    }
    (export_dir/'frame_export_report.json').write_text(
        json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom_zip',type=Path)
    p.add_argument('static_recipe',type=Path)
    p.add_argument('frame_graphics_zip',type=Path)
    p.add_argument('rgb_profile',type=Path)
    p.add_argument('output_scene',type=Path)
    p.add_argument('--gif-output',type=Path,help='Write GIF and PNG frame sequence using PR #29 scene exporter')
    a=p.parse_args()
    path=build(a.rom_zip,a.static_recipe,a.frame_graphics_zip,a.rgb_profile,a.output_scene)
    print('Animated source-backed scene:',path)
    print((path.parent/'animation_report.json').read_text())
    if a.gif_output:
        print('GIF+frame export:',export_animated_scene(path,a.gif_output))

if __name__=='__main__':
    main()
