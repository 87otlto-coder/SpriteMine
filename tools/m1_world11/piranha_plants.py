"""Add three original-ROM SMB3 World 1-1 pipe plants to the private panorama.

Graphics: original 8x16 OAM patterns at ROM CHR page $4F, as selected in
ObjectGroup04_PatTableSel. Placement: original W101O records at file $C537.
Original 1-pixel/game-tick emergence and 8-tick mouth animation are represented
in a creative, independently looping 40ms wallpaper timeline. The stage is
static; the deterministic replay is explicitly NOT an emulator gameplay trace.

Source: captainsouthbird/smb3, pinned commit
09b1bd81a788de8ceec664a34094e84ddb463117 (prg005.asm, objects/1-1.asm).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from goal_card import private_inputs

DISASSEMBLY_COMMIT = '09b1bd81a788de8ceec664a34094e84ddb463117'
WORLD11_OBJECT_OFFSET = 0xC537
SOURCE_PIRANHAS = (
    (0xA6, 0x16, 0x17, 'venus_firetrap', 33, 1),
    (0xA0, 0x70, 0x18, 'green_piranha', 25, 2),
    (0xA4, 0x74, 0x17, 'green_fire', 25, 2),
)
OBJECT_HEAD_TILES = {
    'green_piranha': ((0xE1, 0xE1), (0xE5, 0xE5)),
    'green_fire': ((0xF1, 0xF3), (0xF5, 0xF7)),
    'venus_firetrap': ((0xF1, 0xF3), (0xF5, 0xF7)),
}
OBJECT_STEM_TILES = (0xE3, 0xE3)
BLANK_STEM_TILES = (0x71, 0x71)
SCENE_TICKS = 144
SCENE_TICK_MS = 40
# Motion is an authored ambient replay, not a claim about player-dependent
# gameplay timers or simultaneous object spawning.
PLANT_LOOPS = {
    'venus_firetrap': (8, 14, 20, 14, 16),
    'green_piranha': (14, 11, 22, 11, 14),
    'green_fire': (10, 11, 30, 11, 10),
}
PHASE_SHIFTS = {'venus_firetrap': 0, 'green_piranha': 24, 'green_fire': 48}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def world11_objects(rom: bytes) -> list[tuple[int,int,int]]:
    """Read real PRG1 source records, including the end-card, without modification."""
    offset = WORLD11_OBJECT_OFFSET
    if rom[offset] != 1:
        raise ValueError('World 1-1 W101O header differs from pinned source')
    offset += 1
    records = []
    for _ in range(64):
        ident = rom[offset]
        if ident == 0xFF:
            break
        if offset + 2 >= len(rom):
            raise ValueError('Truncated object stream')
        records.append((ident, rom[offset+1], rom[offset+2]))
        offset += 3
    else:
        raise ValueError('Unterminated object stream')
    if len(records) != 15 or records[-1] != (0x41, 0xA8, 0x15):
        raise ValueError('Unexpected World 1-1 object stream')
    selected = [r for r in records if r[0] in (0xA6, 0xA0, 0xA4)]
    if selected != [(p[0],p[1],p[2]) for p in SOURCE_PIRANHAS]:
        raise ValueError('Piranha records do not match original World 1-1')
    return records


def decode_oam_8x16(ppu: bytes, palette_ram: bytes, rgb24: bytes,
                     tile: int, palette: int, *, hflip: bool = False) -> Image.Image:
    """NES 8x16 hardware sprite, transparent value zero, no RGB guessing."""
    if len(ppu) != 12288 or len(palette_ram) != 32 or len(rgb24) != 192:
        raise ValueError('Unexpected PPU / palette / RGB24 capture sizes')
    if not (0 <= tile <= 255 and 0 <= palette <= 3):
        raise ValueError('Invalid hardware tile or palette')
    base = (tile & 1) * 4096 + (tile & 0xFE) * 16
    image = Image.new('RGBA', (8,16))
    pixels=image.load()
    colors=[(0,0,0,0)]
    for idx in (1,2,3):
        code=palette_ram[16+4*palette+idx]&63
        colors.append((*rgb24[3*code:3*code+3],255))
    for y in range(16):
        a=ppu[base+(y//8)*16+y%8]
        b=ppu[base+(y//8)*16+y%8+8]
        for x in range(8):
            bpos=x if hflip else 7-x
            color=((a>>bpos)&1)|(((b>>bpos)&1)<<1)
            pixels[x,y]=colors[color]
    return image


def plant_sprite(ppu: bytes, pal: bytes, rgb: bytes, kind: str,
                 frame: int, rise: int) -> Image.Image:
    """Original pattern halves and source palettes; clip to pipe upper lip.

    We intentionally do NOT reproduce hardware OAM overflow, proximity gates,
    native sprite masking tile $77 or fetch-time priority. Clipping is an
    authored wallpaper approximation to that pipe occlusion effect.
    """
    if kind not in OBJECT_HEAD_TILES or frame not in (0,1):
        raise ValueError('Unknown piranha kind or animation frame')
    max_rise=33 if kind=='venus_firetrap' else 25
    if not 0 <= rise <= max_rise:
        raise ValueError('Rise height outside source-object range')
    head=OBJECT_HEAD_TILES[kind][frame]
    stem=OBJECT_STEM_TILES if rise>=17 else BLANK_STEM_TILES
    mirrored_head=(kind=='green_piranha')
    base_pal=1 if kind=='venus_firetrap' else 2
    img=Image.new('RGBA',(16,32),(0,0,0,0))
    for row,patterns,selection,mirror in [(0,head,base_pal,mirrored_head),
                                          (16,stem,2,True)]:
        for side,tile in enumerate(patterns):
            piece=decode_oam_8x16(ppu,pal,rgb,tile,selection,hflip=mirror and side==1)
            img.alpha_composite(piece,(side*8,row))
    if rise < 32:
        for y in range(rise,32):
            img.paste((0,0,0,0),(0,y,16,y+1))
    return img


def rise_sequence(kind: str) -> tuple[int,...]:
    """72 output ticks, repeating exactly with a hidden-to-hidden seam."""
    initial, up, hold, down, final=PLANT_LOOPS[kind]
    assert initial+up+hold+down+final==72
    target=33 if kind=='venus_firetrap' else 25
    ascending=[min(target,round((i+1)*target/up)) for i in range(up)]
    descending=[max(0,round(target*(down-1-i)/down)) for i in range(down)]
    result=(0,)*initial+tuple(ascending)+(target,)*hold+tuple(descending)+(0,)*final
    assert len(result)==72 and result[0]==result[-1]==0
    assert max(result)==target
    return result


def build(rom_zip: Path, goal_recipe: Path, graphics_zip: Path,
          rgb_profile: Path, destination: Path) -> Path:
    """Produce a new, private PR29 compositor-v1 recipe and decoded art."""
    if destination.exists():
        raise FileExistsError(f'Will not overwrite private scene {destination}')
    rom, ppu, pal, rgb, provenance = private_inputs(rom_zip,graphics_zip,rgb_profile)
    records=world11_objects(rom)
    if ppu[0x1c00:0x2000] != rom[16+0x40000+79*1024:16+0x40000+80*1024]:
        raise ValueError('Original piranha sprite CHR page $4F not mapped at PPU $1C00')
    recipe=json.loads(goal_recipe.read_text(encoding='utf-8'))
    if recipe.get('version') != 1 or recipe['size'] != [2816,432] or recipe['ticks'] != 12 or recipe['tick_ms'] != 130:
        raise ValueError('Expected canonical PR32 full-stage goal scene')
    snapshot=recipe.get('staging_provenance',{}).get('graphics_snapshot_provenance',{})
    if (snapshot.get('ppu_sha256')!=provenance['ppu_sha256'] or
        snapshot.get('palette_sha256')!=provenance['palette_sha256'] or
        snapshot.get('rgb_profile_sha256')!=provenance['rgb_profile_sha256']):
        raise ValueError('Piranha snapshot is not the same original graphics capture')
    if len(recipe['layers'])!=3 or len(recipe['layers'][0]['tiles'])!=27:
        raise ValueError('Unexpected source scene layers')
    for layer in recipe['layers'][1:]:
        for track in layer.get('tracks',[]):
            if sum(cel['ticks'] for cel in track['cels']) not in (3,4):
                raise ValueError('Unknown existing animation track')
    # Pipe caps from source tile models; objects are centered over their mouths.
    for obj_id,x,y,kind,rise,palidx in SOURCE_PIRANHAS:
        if (recipe['layers'][0]['tiles'][y][x],recipe['layers'][0]['tiles'][y][x+1])!=('tile_b1','tile_b2'):
            raise ValueError(f'No verified two-column pipe mouth at {x},{y}')
    base=goal_recipe.parent.resolve()
    destination.mkdir(parents=True)
    try:
        for name,spec in recipe['assets'].items():
            source=(base/spec['file']).resolve()
            if not source.is_relative_to(base):
                raise ValueError(f'Asset path escapes input folder: {name}')
            data=source.read_bytes()
            if sha(data)!=spec.get('sha256'):
                raise ValueError(f'Existing sprite or tile asset changed: {name}')
            path=(destination/spec['file']).resolve()
            if not path.is_relative_to(destination.resolve()):
                raise ValueError('Destination asset escapes scene')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        recipe['ticks']=SCENE_TICKS
        recipe['tick_ms']=SCENE_TICK_MS
        for layer in recipe['layers'][1:]:
            for track in layer.get('tracks',[]):
                for cel in track['cels']:
                    cel['ticks']*=3
        plants=[]
        sprite_assets={}
        for obj_id,x,y,kind,target,palidx in SOURCE_PIRANHAS:
            movements=rise_sequence(kind)
            cels=[]
            for frame_idx,rise in enumerate(movements):
                if rise==0:
                    cels.append({'asset':None,'ticks':1})
                    continue
                frame=(frame_idx//3)%2
                asset_name=f'plant_{kind}_r{rise:02d}_f{frame}'
                if asset_name not in sprite_assets:
                    image=plant_sprite(ppu,pal,rgb,kind,frame,rise)
                    rel=Path('piranha')/(asset_name+'.png')
                    path=destination/rel
                    path.parent.mkdir(exist_ok=True)
                    image.save(path)
                    sprite_assets[asset_name]={
                        'file':rel.as_posix(),'sha256':sha(path.read_bytes()),
                        'provenance':{**provenance,
                            'source_class':'decoded_CHR_art_with_authored_wallpaper_motion',
                            'object_id':obj_id,'pattern_set':'ObjPA0/ObjPA4',
                            'pattern_chr_page':79,'oam_palette_head':palidx,
                            'oam_palette_stem':2,'emergence_pixels':rise,
                            'source_frame':frame,
                            'pipe_mask':'authored clip above pipe lip; not native OAM mask'},
                    }
                cels.append({'asset':asset_name,'ticks':1,'offset':[0,-rise]})
            plants.append({
                'at':[x*16+8,y*16],
                'phase':PHASE_SHIFTS[kind],
                'cels':cels,
            })
        recipe['assets'].update(sprite_assets)
        recipe['layers'].append({'tracks':plants})
        recipe['staging_provenance']['piranha_plants']={
            **provenance,'disassembly_commit':DISASSEMBLY_COMMIT,
            'source_record_file_offset':WORLD11_OBJECT_OFFSET,
            'source_records_total':len(records),
            'source_plants':[{'object_id':obj,'x_byte':x,'y_byte':y,'kind':kind,
                              'world_sprite_at':[x*16+8,y*16],'max_rise':h}
                             for obj,x,y,kind,h,_ in SOURCE_PIRANHAS],
            'matched_sprite_chr_page':79,
            'scene_ticks':SCENE_TICKS,'scene_tick_ms':SCENE_TICK_MS,
            'wallpaper_motion':'authored fixed repeating 72-tick schedules; player-relative gating and fireballs omitted',
            'source_velocity':'PRG/prg005.asm Piranha_Emerge/Piranha_Retract +/-$10 = 1 px/game tick',
            'source_head_frame_rate':'8 game frames (~133ms); render approximates with 3*40ms=120ms',
            'goal_and_bg_frame_rate':'3*40ms=120ms vs original approx 133ms',
            'alpha_mask':'clip against pipe lip; original mask OAM $77 not emulated',
            'full_gameplay_or_native_pixel_acceptance':False,
        }
        output_recipe=destination/'recipe.json'
        output_recipe.write_text(json.dumps(recipe,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        (destination/'piranha_report.json').write_text(json.dumps({
            'recipe_sha256':sha(output_recipe.read_bytes()),
            'rom_sha256':sha(rom),
            'sprite_capture_sha256':provenance['ppu_sha256'],
            'plant_count':len(plants),'source_records':recipe['staging_provenance']['piranha_plants']['source_plants'],
            'decoded_assets':len(sprite_assets),'scene_size':recipe['size'],
            'ticks':SCENE_TICKS,'tick_ms':SCENE_TICK_MS,'loop_ms':SCENE_TICKS*SCENE_TICK_MS,
            'source_graphics_verified':True,
            'motion_is_authored_not_native_gameplay':True,
            'note':'This private build retains real sprites, pipes and roulette. Native priority/behavior is not accepted.',
        },indent=2,sort_keys=True)+'\n',encoding='utf-8')
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True)
        raise
    return output_recipe


def verify_gif_timeline(gif_path: Path, png_frames: Path, *, ticks: int, tick_ms: int) -> dict:
    """Verify decoded RGB and timing; GIF encoders may coalesce identical frames.

    Never treat coalescing as a missing animation frame. A GIF frame held for
    e.g. 80 ms correctly represents two identical 40 ms source ticks. Every
    source PNG time slot must be lossless and the sum of durations exact.
    """
    slot = 0
    with Image.open(gif_path) as gif:
        if gif.info.get('loop') != 0:
            raise ValueError('GIF is not configured to loop infinitely')
        encoded_frames = gif.n_frames
        for frame in range(gif.n_frames):
            gif.seek(frame)
            duration = gif.info.get('duration', 0)
            if duration < tick_ms or duration % tick_ms:
                raise ValueError(f'GIF frame {frame} has invalid {duration} ms hold')
            rgb = gif.convert('RGB').tobytes()
            for _ in range(duration // tick_ms):
                if slot >= ticks:
                    raise ValueError('GIF exceeds declared source timeline')
                with Image.open(png_frames/f'world11_{slot:03d}.png') as original:
                    if rgb != original.convert('RGB').tobytes():
                        raise ValueError(f'GIF/PNG pixel mismatch at timeline tick {slot}')
                slot += 1
    if slot != ticks:
        raise ValueError(f'GIF covers {slot}/{ticks} declared ticks')
    return {'declared_png_ticks':ticks, 'encoded_gif_frames':encoded_frames,
            'full_timeline_rgb_exact':True, 'gif_total_duration_ms':ticks*tick_ms}


def export_scene(recipe_path: Path, out_dir: Path):
    from spritemine.scene import Scene
    from spritemine.scene_export import export
    scene=Scene.load(recipe_path)
    if scene.size!=(2816,432) or scene.ticks!=SCENE_TICKS:
        raise ValueError('Piranha scene dimensions/ticks changed')
    manifest=export(recipe_path,out_dir)
    frames_dir=out_dir/'frames';frames_dir.mkdir()
    for tick in range(scene.ticks):
        scene.render(tick).save(frames_dir/f'world11_{tick:03d}.png')
    timing=verify_gif_timeline(out_dir/'scene.gif',frames_dir,ticks=scene.ticks,
                               tick_ms=scene.tick_ms)
    (out_dir/'piranha_timeline_verification.json').write_text(
        json.dumps(timing,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return {**manifest, 'gif_timeline':timing}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('rom_zip','goal_recipe','graphics_zip','rgb_profile','private_scene'):
        cli.add_argument(name,type=Path)
    cli.add_argument('--export',type=Path)
    a=cli.parse_args()
    result=build(a.rom_zip,a.goal_recipe,a.graphics_zip,a.rgb_profile,a.private_scene)
    print('Private piranha scene:',result)
    if a.export:
        print('Export manifest:',export_scene(result,a.export))

if __name__=='__main__':
    main()
