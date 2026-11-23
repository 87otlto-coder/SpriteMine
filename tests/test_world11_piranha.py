"""Synthetic public checks; authentic private-ROM build is opt-in."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'m1_world11'))
from piranha_plants import (
    SOURCE_PIRANHAS, WORLD11_OBJECT_OFFSET, PLANT_LOOPS,
    PHASE_SHIFTS, SCENE_TICKS, SCENE_TICK_MS,
    decode_oam_8x16, plant_sprite, rise_sequence, world11_objects,
    build, verify_gif_timeline,
)


def test_source_record_constants_and_rise_sequences():
    assert [(r[0],r[1],r[2]) for r in SOURCE_PIRANHAS] == [
        (0xA6,0x16,0x17),(0xA0,0x70,0x18),(0xA4,0x74,0x17)]
    assert [ (x*16+8,y*16) for _,x,y,_,_,_ in SOURCE_PIRANHAS] == [
        (360,368),(1800,384),(1864,368)]
    assert SCENE_TICKS==144 and SCENE_TICK_MS==40
    assert SCENE_TICKS%12==0 and SCENE_TICKS%9==0
    assert SCENE_TICKS%72==0
    for _,_,_,kind,max_rise,_ in SOURCE_PIRANHAS:
        seq=rise_sequence(kind)
        assert len(seq)==72
        assert min(seq)==0 and max(seq)==max_rise
        assert seq[0]==seq[-1]==0
        assert all(abs(b-a)<=4 for a,b in zip(seq,seq[1:]))
        assert sum(PLANT_LOOPS[kind])==72
        assert PHASE_SHIFTS[kind]%72 in (0,24,48)
        # Last GIF tick advances naturally to the first; no visible teleport.
        previous=seq[(SCENE_TICKS-1+PHASE_SHIFTS[kind])%72]
        next_rise=seq[PHASE_SHIFTS[kind]%72]
        assert abs(previous-next_rise)<=4


def test_private_object_parser_rejects_changed_ids():
    stream = bytearray(WORLD11_OBJECT_OFFSET+1+15*3+1)
    start = WORLD11_OBJECT_OFFSET
    stream[start] = 1
    rows = [(0x72, 0x11, 0x19)] * 11 + [
        (0xA6,0x16,0x17), (0xA0,0x70,0x18),
        (0xA4,0x74,0x17), (0x41,0xA8,0x15)]
    for idx,(ident,x,y) in enumerate(rows):
        stream[start+1+idx*3:start+4+idx*3] = bytes((ident,x,y))
    stream[start+1+len(rows)*3] = 0xFF
    assert len(world11_objects(bytes(stream)))==15
    stream[start+1+11*3] = 0xA5
    with pytest.raises(ValueError,match='Piranha'):
        world11_objects(bytes(stream))


def test_oam_tile_uses_odd_8x16_bank_transparent_zero_and_flip():
    ppu=bytearray(12288)
    # Odd $E1 chooses PPU $1000 + $E0*16 = $1E00; this is CHR bank $4F.
    base=0x1E00
    ppu[base]=0x80
    ppu[base+16]=0x40
    pal=bytearray(32)
    pal[16+2*4+1]=2
    rgb=bytearray(192)
    rgb[2*3:2*3+3]=bytes((10,30,50))
    left=decode_oam_8x16(bytes(ppu),bytes(pal),bytes(rgb),0xE1,2)
    right=decode_oam_8x16(bytes(ppu),bytes(pal),bytes(rgb),0xE1,2,hflip=True)
    assert left.size==(8,16)
    assert left.getpixel((0,0))==(10,30,50,255)
    assert right.getpixel((7,0))==(10,30,50,255)
    assert left.getpixel((1,8))==(10,30,50,255)
    assert left.getpixel((3,0))[3]==0
    with pytest.raises(ValueError,match='Unexpected'):
        decode_oam_8x16(b'',bytes(pal),bytes(rgb),0xE1,2)


def test_hidden_pipe_occlusion_clips_pixels_below_mouth():
    ppu=bytearray(12288)
    for tile in (0xE1,0xE3,0xE5,0xF1,0xF3,0xF5,0xF7):
        addr=0x1000+(tile&0xFE)*16
        for sub in (0,16):
            for row in range(8):
                ppu[addr+sub+row] = 0xFF
    pal=bytearray(32)
    for i in (1,2):
        pal[16+i*4+1]=2
    rgb=bytearray(192)
    rgb[6:9] = bytes((24,48,72))
    for kind in ('green_piranha','green_fire','venus_firetrap'):
        hidden=plant_sprite(bytes(ppu),bytes(pal),bytes(rgb),kind,0,0)
        part=plant_sprite(bytes(ppu),bytes(pal),bytes(rgb),kind,1,7)
        high=plant_sprite(bytes(ppu),bytes(pal),bytes(rgb),kind,0,25)
        assert hidden.getbbox() is None
        assert part.getbbox() is not None
        assert all(part.getpixel((x,y))[3]==0 for x in range(16) for y in range(7,32))
        assert all(high.getpixel((x,y))[3]==0 for x in range(16) for y in range(25,32))


def test_gif_timeline_verifier_accepts_coalesced_frames_and_detects_error(tmp_path):
    # Four expected time slots: A, A, B, B. GIF may encode only two frames.
    pngs=tmp_path/'png';pngs.mkdir()
    a=Image.new('RGB',(4,4),(10,20,30))
    b=Image.new('RGB',(4,4),(40,50,60))
    for tick,img in enumerate((a,a,b,b)):
        img.save(pngs/f'world11_{tick:03d}.png')
    gif=tmp_path/'scene.gif'
    a.save(gif,format='GIF',save_all=True,append_images=[a,b,b],duration=40,loop=0,optimize=False)
    result=verify_gif_timeline(gif,pngs,ticks=4,tick_ms=40)
    assert result['full_timeline_rgb_exact']
    assert result['declared_png_ticks']==4
    assert result['encoded_gif_frames']<=4
    b.putpixel((1,1),(100,100,100))
    b.save(pngs/'world11_003.png')
    with pytest.raises(ValueError,match='pixel mismatch'):
        verify_gif_timeline(gif,pngs,ticks=4,tick_ms=40)


def test_real_private_world11_piranha_recipe_opt_in(tmp_path):
    rom=os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    graphics=os.environ.get('SPRITEMINE_PRIVATE_GRAPHICS_ZIP')
    rgb=os.environ.get('SPRITEMINE_PRIVATE_RGB_PROFILE')
    recipe=os.environ.get('SPRITEMINE_PRIVATE_GOAL_RECIPE')
    if not all((rom,graphics,rgb,recipe)):
        pytest.skip('Private ROM, graphics frame and prior goal scene are not public GitHub inputs')
    target=tmp_path/'piranha'
    produced=build(Path(rom),Path(recipe),Path(graphics),Path(rgb),target)
    obj=json.loads(produced.read_text())
    assert obj['size']==[2816,432] and obj['ticks']==144
    assert obj['tick_ms']==40 and len(obj['layers'])==4
    assert len(obj['layers'][-1]['tracks'])==3
    assert len(obj['layers'][1]['tracks'])==51
    assert obj['layers'][3]['tracks'][0]['at']==[360,368]
    assert obj['layers'][3]['tracks'][1]['at']==[1800,384]
    assert obj['layers'][3]['tracks'][2]['at']==[1864,368]
    assert obj['staging_provenance']['piranha_plants']['matched_sprite_chr_page']==79
    assert obj['staging_provenance']['piranha_plants']['full_gameplay_or_native_pixel_acceptance'] is False
    with pytest.raises(FileExistsError):
        build(Path(rom),Path(recipe),Path(graphics),Path(rgb),target)
