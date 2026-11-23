"""Populate the private full-stage World 1-1 panorama with 11 source actors.

Only SMB3 US PRG1; original ROM and extracts stay in private fixture/output.
All graphics and source placements are decoded from the original ROM and the
frame-450840 MesenCE PPU/palette snapshot, which identifies sprite CHR page 79.
Motion is an *authored ambient wallpaper loop*, not an authentic simultaneous
emulator replay. Actor reconstruction follows the original source OAM piece
pattern/palette references and labels uncertain offsets explicitly.

Source: captainsouthbird/smb3 commit 09b1bd81a788de8ceec664a34094e84ddb463117
PRG/prg004.asm ObjP6C, ObjP72, GroundTroop_Draw, Troopa_Draw,
ParaGoomba_Draw, ObjNorm_RedTroopa, ObjNorm_ParaGoomba; objects/1-1.asm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from goal_card import private_inputs
from piranha_plants import decode_oam_8x16, world11_objects, verify_gif_timeline
from world11_compile import GROUND_TILES

SCENE_TICKS = 144
TICK_MS = 40
DISASSEMBLY_COMMIT = '09b1bd81a788de8ceec664a34094e84ddb463117'
SPRITE_PAGE = 79
# Original W101O source records, excluding three Piranhas and one card.
# Format: (object ID, source column, source row, kind); never infer simultaneous
# active objects from the object list.
SOURCE_ACTORS = (
    (0x72,0x0E,0x19,'goomba'),
    (0x72,0x21,0x19,'goomba'),
    (0x6D,0x24,0x16,'red_koopa'),
    (0x72,0x34,0x18,'goomba'),
    (0x72,0x37,0x18,'goomba'),
    (0x73,0x3B,0x18,'paragoomba'),
    (0x6E,0x53,0x13,'green_hopper'),
    (0x6E,0x56,0x13,'green_hopper'),
    (0x6E,0x59,0x13,'green_hopper'),
    (0x6C,0x5C,0x19,'green_koopa'),
    (0x6D,0x83,0x17,'red_koopa'),
)
ACTOR_IDS = frozenset((0x72,0x73,0x6E,0x6C,0x6D))
# Floor surface IDs verified within the source-generated positions used for
# this World 1-1 preview. This is NOT a general NES collision table.
WORLD11_SURFACES = frozenset(GROUND_TILES | {0xA0,0x67,0xE2,0xE3,0xE4})


@dataclass(frozen=True)
class Pose:
    frame: int
    facing_right: bool
    wing_up: bool


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_source_actors(rom: bytes) -> tuple[tuple[int,int,int,str],...]:
    """Validate every World 1-1 record before treating any as an actor."""
    matched = tuple((obj,x,y) for obj,x,y in world11_objects(rom)
                    if obj in ACTOR_IDS)
    if matched != tuple((obj,x,y) for obj,x,y,_ in SOURCE_ACTORS):
        raise ValueError('World 1-1 actor records differ from disassembly')
    return SOURCE_ACTORS


def sprite_piece(ppu: bytes, pal: bytes, rgb: bytes, tile: int,
                 palette: int, *, hflip: bool = False) -> Image.Image:
    return decode_oam_8x16(ppu,pal,rgb,tile,palette,hflip=hflip)


def assemble_actor(ppu: bytes, pal: bytes, rgb: bytes, kind: str,
                   pose: Pose) -> Image.Image:
    """Compose source OAM sprite pieces into a complete, transparent actor.

    Goomba/paragoomba source ObjP72 has D9,DB or DB,D9 pairs. Koopas use
    separate C1 head tip palette 3, CB/C3 body, C7/C9 or F9/FB feet, and CD/CF
    paratroopa wing palette 1. Source routine uses mirroring/extra pieces;
    display alignment is an authored fixed scene approximation, not raw OAM.
    """
    if pose.frame not in (0,1):
        raise ValueError('Only source actor frame 0 or 1 supported')
    if kind not in {row[3] for row in SOURCE_ACTORS}:
        raise ValueError(f'Unsupported World 1-1 enemy: {kind}')
    if kind in ('goomba','paragoomba'):
        palette = 3 if kind=='goomba' else 1
        # Disassembly ObjP72 shows two genuinely different frame pairs.
        pair = ((0xD9,0xDB),(0xDB,0xD9))[pose.frame]
        if kind=='goomba':
            image=Image.new('RGBA',(16,16))
            for side,tile in enumerate(pair):
                image.alpha_composite(sprite_piece(ppu,pal,rgb,tile,palette,
                                                   hflip=side==1),(side*8,0))
        else:
            image=Image.new('RGBA',(20,26))
            for side,tile in enumerate(pair):
                image.alpha_composite(sprite_piece(ppu,pal,rgb,tile,palette,
                                                   hflip=side==1),(2+side*8,10))
            wing_tile=0xCD if pose.wing_up else 0xCF
            # Source ParaGoomba_Draw: two PAL2 wings Y-10, x offsets -2/+2.
            image.alpha_composite(sprite_piece(ppu,pal,rgb,wing_tile,2,hflip=True),(0,0))
            image.alpha_composite(sprite_piece(ppu,pal,rgb,wing_tile,2),(12,0))
    else:
        # Source Troopa_Draw 16x32 body+feet and separate PAL3 head tip.
        body_palette = 1 if kind=='red_koopa' else 2
        image=Image.new('RGBA',(16,48))
        for side,tile in enumerate((0xCB,0xC5) if pose.frame==0 else (0xC3,0xC5)):
            part=sprite_piece(ppu,pal,rgb,tile,3 if side==0 else body_palette,
                              hflip=False)
            image.alpha_composite(part,(side*8,16))
        image.alpha_composite(sprite_piece(ppu,pal,rgb,0xC1,3),(0,0))
        feet=(0xC7,0xC9) if pose.frame==0 else (0xF9,0xFB)
        for side,tile in enumerate(feet):
            image.alpha_composite(sprite_piece(ppu,pal,rgb,tile,body_palette,
                                               hflip=False),(side*8,32))
        if kind=='green_hopper':
            wing_tile=0xCD if pose.wing_up else 0xCF
            image.alpha_composite(sprite_piece(ppu,pal,rgb,wing_tile,1),(8,8))
    if pose.facing_right:
        image=image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if image.getbbox() is None:
        raise ValueError('Decoded actor is empty')
    return image


def surface_row(tiles: list[list[str]], source_col: int, source_row: int) -> int:
    """Find the first supported local World 1-1 footing tile below a record."""
    if len(tiles)!=27 or any(len(row)!=176 for row in tiles):
        raise ValueError('Expected original full World 1-1 176x27 logical layout')
    for row in range(source_row+1,min(source_row+5,27)):
        key=tiles[row][source_col]
        if key.startswith('tile_') and int(key[5:],16) in WORLD11_SURFACES:
            return row
    raise ValueError(f'Unresolved actor footing at {source_col},{source_row}')


def actor_motion(kind: str, tick: int, ordinal: int) -> tuple[int,int,Pose]:
    """Wallpaper motion, designed to be seamlessly periodic at tick 144.

    No NPC physics, slope avoidance, AI, spawn/despawn, or actual event replay.
    The source only grounds graphic forms and placement. Gentle bounded travel
    avoids invisible hard resets while making a stationary stage feel alive.
    """
    if not 0<=tick<SCENE_TICKS:
        raise ValueError('Timeline tick outside full scene')
    if kind not in {row[3] for row in SOURCE_ACTORS}:
        raise ValueError('Unexpected actor kind')
    period=72 if kind in ('goomba','paragoomba') else 144
    phase=(tick+(ordinal%2)*(period//2))%period
    angle=2*math.pi*phase/period
    amplitude=9 if kind in ('goomba','paragoomba') else 7
    dx=round(amplitude*math.sin(angle))
    facing_right=math.cos(angle)>=0
    if kind=='paragoomba':
        # Three short hops then a larger hop are gameplay-specific; this
        # wallpaper approximation uses source-inspired repeated flutter hops.
        rise=round(17*max(0,math.sin(2*angle))**2)
    elif kind=='green_hopper':
        # 3 repeated jumps with 0, 16 and 32 tick offsets for its three actors.
        wing_phase=(tick+ordinal*16)%48
        rise=round(25*max(0,math.sin(2*math.pi*wing_phase/48))**2)
    else:
        rise=0
    # 40ms ticks approximate 4/8 NES frames; source code toggles feet/wing
    # pairs on counters, though their exact phase is not captured here.
    frame=(tick//2)%2 if kind!='red_koopa' else (tick//3)%2
    wing_up=((tick//2 + ordinal)%2)==0
    return dx,-rise,Pose(frame,facing_right,wing_up)


def _asset_png(image: Image.Image, folder: Path, name: str) -> tuple[str,str]:
    dest=folder/(name+'.png')
    image.save(dest)
    return dest.name,digest(dest.read_bytes())


def build(rom_zip: Path, piranha_recipe: Path, graphics_zip: Path,
          rgb_profile: Path, destination: Path) -> Path:
    """Extend previous private M1 stage scene without mutating any inputs."""
    if destination.exists():
        raise FileExistsError(f'Will not overwrite prior scene: {destination}')
    rom,ppu,pal,rgb,provenance=private_inputs(rom_zip,graphics_zip,rgb_profile)
    actors=read_source_actors(rom)
    chrrom=rom[16+0x40000:]
    if ppu[0x1C00:0x2000]!=chrrom[SPRITE_PAGE*1024:(SPRITE_PAGE+1)*1024]:
        raise ValueError('Sprite CHR page 79 mismatch with original ROM')
    recipe=json.loads(piranha_recipe.read_text(encoding='utf8'))
    if recipe.get('version')!=1 or recipe.get('size')!=[2816,432] or recipe.get('ticks')!=144 or recipe.get('tick_ms')!=40:
        raise ValueError('Expected canonical World 1-1 plant wallpaper recipe')
    if len(recipe.get('layers',[]))!=4 or len(recipe['layers'][3].get('tracks',[]))!=3:
        raise ValueError('Expected compositor background, CHR, card and three pipe plants')
    captured=recipe.get('staging_provenance',{}).get('graphics_snapshot_provenance',{})
    if any(captured.get(k)!=provenance[k] for k in ('ppu_sha256','palette_sha256','rgb_profile_sha256')):
        raise ValueError('Actor/scene PPU+palette snapshots do not agree')
    static=recipe['layers'][0]['tiles']
    base=piranha_recipe.parent.resolve()
    destination.mkdir(parents=True)
    try:
        for asset,spec in recipe['assets'].items():
            path=(base/spec['file']).resolve()
            if not path.is_relative_to(base):
                raise ValueError('Unsafe asset path outside private input scene')
            data=path.read_bytes()
            if digest(data)!=spec.get('sha256'):
                raise ValueError(f'Source scene asset was modified: {asset}')
            target=(destination/spec['file']).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('Unsafe output asset path')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        targetdir=destination/'actors';targetdir.mkdir()
        # Decode every distinct source piece once. Repeated actor positions
        # reference the same PNG and differ only in timeline transforms.
        artwork={}
        tracks=[]
        positions=[]
        for ordinal,(obj,x,y,kind) in enumerate(actors):
            floor_y=surface_row(static,x,y)*16
            cels=[]
            for tick in range(SCENE_TICKS):
                dx,dy,pose=actor_motion(kind,tick,ordinal)
                key=(kind,pose.frame,pose.facing_right,pose.wing_up if kind in ('green_hopper','paragoomba') else False)
                asset=f'actor_{key[0]}_f{key[1]}_r{int(key[2])}_w{int(key[3])}'
                if asset not in artwork:
                    im=assemble_actor(ppu,pal,rgb,kind,pose)
                    filename,file_sha=_asset_png(im,targetdir,asset)
                    artwork[asset]={
                        'file':f'actors/{filename}', 'sha256':file_sha,
                        'provenance':{
                            **provenance,'source_class':'decoded',
                            'object_id':obj,'source_pattern_group':'ObjP6C or ObjP72',
                            'sprite_chr_page':SPRITE_PAGE,
                            'composition':'source OAM pieces, authored alignment and mirroring',
                            'source_asm_commit':DISASSEMBLY_COMMIT,
                            'artwork_kind':kind,'animation_frame':pose.frame,
                            'facing_right':pose.facing_right,
                            'wing_up':pose.wing_up,
                        },
                    }
                # Align the lowermost visible pixels to nearby source-derived
                # terrain, not the bottom of the padded OAM assembly canvas.
                with Image.open(destination/artwork[asset]['file']) as im:
                    bottom=im.getbbox()[3]
                # Move the transparent sprite panel's top so its last
                # visible pixel is just above the world terrain pixel row.
                image_y=floor_y-bottom
                cels.append({'asset':asset,'ticks':1,
                             'offset':[dx-(2 if kind=='paragoomba' else 0),
                                       image_y-y*16+dy]})
            tracks.append({'at':[x*16,y*16], 'phase':0,'cels':cels})
            positions.append({'source':[obj,x,y],'kind':kind,
                              'source_world':[x*16,y*16],
                              'floor_pixel_y':floor_y,
                              'motion':'bounded authored oscillation/hop; phase loop 144x40ms'})
        recipe['assets'].update(artwork)
        recipe['layers'].append({'tracks':tracks})
        recipe['staging_provenance']['world11_ground_actors']={
            **provenance,'disassembly_commit':DISASSEMBLY_COMMIT,
            'source_object_offset':0xC537,
            'object_records':positions,'record_count':len(positions),
            'source_chr_page':SPRITE_PAGE,'graphic_source':'original CHR 8x16 + frame-local palette',
            'motion':'authored wallpaper trajectories; NOT emulator runtime AI',
            'source_motion_summary':'Troopa walk + red turn, Goomba walk, winged hop; simplified periodic motion',
            'simultaneous_visibility_is_artistic':True,
            'background_scene_unchanged':True,
            'native_oam_exact':False,
            'full_world_native_verified':False,
        }
        output=destination/'recipe.json'
        output.write_text(json.dumps(recipe,indent=2,sort_keys=True)+'\n',encoding='utf8')
        (destination/'ground_actor_report.json').write_text(json.dumps({
            'recipe_sha256':digest(output.read_bytes()),
            'source_actor_count':len(positions),
            'distinct_actor_art_pngs':len(artwork),
            'scene_size':recipe['size'],
            'ticks':SCENE_TICKS,'tick_ms':TICK_MS,
            'actor_placements':positions,
            'native_gameplay_motion_verified':False,
            'note':'Source graphics/positions, independently composed actor silhouettes; authored ambient motion and terrain alignment.'
        },indent=2,sort_keys=True)+'\n',encoding='utf8')
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True)
        raise
    return output


def export_scene(recipe: Path, out: Path) -> dict:
    from spritemine.scene import Scene
    from spritemine.scene_export import export
    instance=Scene.load(recipe)
    if instance.size!=(2816,432) or instance.ticks!=SCENE_TICKS:
        raise ValueError('Unexpected final World 1-1 dimensions')
    manifest=export(recipe,out)
    frames=out/'frames';frames.mkdir(exist_ok=True)
    for t in range(SCENE_TICKS):
        instance.render(t).save(frames/f'world11_{t:03d}.png')
    evidence=verify_gif_timeline(out/'scene.gif',frames,ticks=SCENE_TICKS,tick_ms=TICK_MS)
    (out/'ground_actor_timeline_verification.json').write_text(
        json.dumps(evidence,indent=2,sort_keys=True)+'\n',encoding='utf8')
    return {**manifest,'gif_timeline':evidence}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rom_zip','piranha_recipe','graphics_zip','rgb_profile','private_scene'):
        parser.add_argument(name,type=Path)
    parser.add_argument('--export',type=Path)
    args=parser.parse_args()
    path=build(args.rom_zip,args.piranha_recipe,args.graphics_zip,
               args.rgb_profile,args.private_scene)
    print('Private full-stage scene with all source actors:',path)
    if args.export:
        print('Export:',export_scene(path,args.export))

if __name__=='__main__':
    main()
