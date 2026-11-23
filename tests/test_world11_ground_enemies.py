"""Public synthetic and opt-in private tests for original-source SMB3 actors."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'m1_world11'))
from ground_enemies import (
    SOURCE_ACTORS, SCENE_TICKS, TICK_MS, Pose,
    actor_motion, assemble_actor, read_source_actors, surface_row, build,
)
from piranha_plants import WORLD11_OBJECT_OFFSET


def test_source_records_stable_and_exactly_eleven():
    assert len(SOURCE_ACTORS)==11
    assert [(x,y) for _,x,y,_ in SOURCE_ACTORS]==[
        (14,25),(33,25),(36,22),(52,24),(55,24),(59,24),
        (83,19),(86,19),(89,19),(92,25),(131,23)]
    assert {kind for *_,kind in SOURCE_ACTORS}=={
        'goomba','red_koopa','green_koopa','paragoomba','green_hopper'}
    assert SCENE_TICKS==144 and TICK_MS==40
    # Build a synthetic read-only stream: original ordering includes three
    # Piranhas in between and ends with the goal card. No game bytes committed.
    rows=[
        (0x72,0x0E,0x19), (0xA6,0x16,0x17),
        (0x72,0x21,0x19), (0x6D,0x24,0x16),
        (0x72,0x34,0x18), (0x72,0x37,0x18),
        (0x73,0x3B,0x18), (0x6E,0x53,0x13),
        (0x6E,0x56,0x13), (0x6E,0x59,0x13),
        (0x6C,0x5C,0x19), (0xA0,0x70,0x18),
        (0xA4,0x74,0x17), (0x6D,0x83,0x17),
        (0x41,0xA8,0x15)]
    rom=bytearray(WORLD11_OBJECT_OFFSET+len(rows)*3+2)
    rom[WORLD11_OBJECT_OFFSET]=1
    for i,rec in enumerate(rows):
        rom[WORLD11_OBJECT_OFFSET+1+3*i:WORLD11_OBJECT_OFFSET+4+3*i]=bytes(rec)
    rom[WORLD11_OBJECT_OFFSET+len(rows)*3+1]=0xFF
    assert read_source_actors(bytes(rom))==SOURCE_ACTORS
    rom[WORLD11_OBJECT_OFFSET+1]=0x73
    with pytest.raises(ValueError,match='actor records'):
        read_source_actors(bytes(rom))


def test_actor_motion_bounded_and_seamless():
    for ordinal,(_,_,_,kind) in enumerate(SOURCE_ACTORS):
        values=[actor_motion(kind,t,ordinal) for t in range(144)]
        assert all(abs(dx)<=9 and -25<=dy<=0 for dx,dy,_ in values)
        assert all(p.frame in (0,1) for _,_,p in values)
        assert max(abs(x2-x1) for (x1,_,_),(x2,_,_) in zip(values,values[1:]+values[:1]))<=2
        assert max(abs(y2-y1) for (_,y1,_),(_,y2,_) in zip(values,values[1:]+values[:1]))<=5
        assert any(v[0]!=values[0][0] or v[1]!=values[0][1] for v in values)
    with pytest.raises(ValueError,match='outside'):
        actor_motion('goomba',144,0)


def test_source_mirror_and_transparency():
    ppu=bytearray(12288)
    # All relevant odd tiles use bank 1 in NES 8x16 sprite mode.
    for tile in (0xC1,0xC3,0xC5,0xC7,0xC9,0xCB,0xCD,0xCF,
                 0xD9,0xDB,0xF9,0xFB):
        addr=4096+(tile&0xFE)*16
        for row in range(8):
            ppu[addr+row]=0x80
            ppu[addr+16+row]=0x40
    pal=bytearray(32)
    for group in range(4):pal[16+4*group+1]=2
    rgb=bytearray(192);rgb[6:9]=bytes((12,34,56))
    for kind in ('goomba','paragoomba','green_koopa','red_koopa','green_hopper'):
        left=assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),kind,Pose(0,False,True))
        right=assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),kind,Pose(0,True,True))
        assert left.size==right.size
        assert left.getbbox() is not None
        assert left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()==right.tobytes()
        assert left.getchannel("A").getextrema()[0]==0
        assert left.getchannel("A").getextrema()[1]==255
    assert assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),'goomba',Pose(0,False,True)).size==(16,16)
    assert assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),'paragoomba',Pose(0,False,True)).size==(20,26)
    assert assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),'green_hopper',Pose(0,False,True)).size==(16,48)
    with pytest.raises(ValueError,match='Only source actor frame'):
        assemble_actor(bytes(ppu),bytes(pal),bytes(rgb),'goomba',Pose(5,False,True))


def test_local_footing_is_explicit_not_guessed():
    a=[['tile_80']*176 for _ in range(27)]
    a[24][36]='tile_a0'
    a[26][92]='tile_53'
    a[20][83]='tile_e3'
    assert surface_row(a,36,22)==24
    assert surface_row(a,92,25)==26
    assert surface_row(a,83,19)==20
    with pytest.raises(ValueError,match='footing'):
        surface_row(a,66,22)
    with pytest.raises(ValueError,match='176x27'):
        surface_row([['tile_80']*15],1,1)


def test_real_private_build_opt_in(tmp_path):
    vals=[os.getenv(k) for k in (
        'SPRITEMINE_PRIVATE_ROM_ZIP',
        'SPRITEMINE_PRIVATE_GRAPHICS_ZIP',
        'SPRITEMINE_PRIVATE_RGB_PROFILE',
        'SPRITEMINE_PRIVATE_PIRANHA_RECIPE')]
    if not all(vals):
        pytest.skip('Original ROM and source graphic artifacts are private')
    rom,graphics,rgb,prior=(Path(v) for v in vals)
    r=build(rom,prior,graphics,rgb,tmp_path/'enemies')
    scene=json.loads(r.read_text())
    assert scene['size']==[2816,432] and scene['ticks']==144 and scene['tick_ms']==40
    assert len(scene['layers'])==5
    assert [len(layer.get('tracks',[])) for layer in scene['layers']]==[0,51,1,3,11]
    assert len(scene['staging_provenance']['world11_ground_actors']['object_records'])==11
    assert scene['staging_provenance']['world11_ground_actors']['native_oam_exact'] is False
    assert all(sum(c['ticks'] for c in track['cels'])==144 for track in scene['layers'][-1]['tracks'])
    assert all(Path(r.parent,v['file']).is_file() for v in scene['assets'].values())
    with pytest.raises(FileExistsError):
        build(rom,prior,graphics,rgb,tmp_path/'enemies')
    second=build(rom,prior,graphics,rgb,tmp_path/'enemies_copy')
    assert second.read_bytes()==r.read_bytes()
    assert sorted((x.name,x.read_bytes()) for x in (tmp_path/'enemies'/'actors').glob('*.png')) == \
           sorted((x.name,x.read_bytes()) for x in (tmp_path/'enemies_copy'/'actors').glob('*.png'))
