"""Fixture-free tests for the headless SpriteMine stage GIF composition pipeline."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import zipfile
from PIL import Image
import pytest
from spritemine.stage_gif import (
    CaptureSource, ROM_SHA, default_recipe, draw_frame, encode_gif,
    input_rom, load_rgb_profile, resolve_chr_pages, sha, validate_animation_periods,
)


def test_scene_recipe_all_elements_wrap_at_exact_48_frame_seam():
    recipe=default_recipe()
    assert recipe['frames']==48
    validate_animation_periods(recipe)
    assert recipe['source_class']=='composed/edited'
    wrong=copy.deepcopy(recipe)
    wrong['blocks'][-1]['ticks_per_frame']=6  # six tiles * 6 = 36 frames, not 48
    with pytest.raises(ValueError, match='Question block'):
        validate_animation_periods(wrong)
    wrong=copy.deepcopy(recipe)
    wrong['coins'][0]['bob_period']=25
    with pytest.raises(ValueError, match='Coin'):
        validate_animation_periods(wrong)
    wrong=copy.deepcopy(recipe)
    wrong['mario']['pose_period']=13
    with pytest.raises(ValueError, match='Mario'):
        validate_animation_periods(wrong)


def test_palette_can_be_read_from_local_reference_cpp_and_json(tmp_path):
    rgb=[f'{n:02X}{(63-n):02X}{(n*3)%256:02X}' for n in range(64)]
    cpp=tmp_path/'NesDefaultVideoFilter.cpp'
    cpp.write_text('/* 2C02 */ { '+', '.join('0xFF'+x for x in rgb)+' }',encoding='utf8')
    data=load_rgb_profile(cpp)
    assert data[0]==(0,63,0) and data[63]==(63,0,189)
    j=tmp_path/'colors.json'
    j.write_text(json.dumps({'profile':'MesenCE_2C02_default_reference','rgb_hex':rgb}))
    assert load_rgb_profile(j)==data
    cpp.write_text('/* 2C02 */ { 0xFF123456 }')
    with pytest.raises(ValueError,match='64 RGB'):
        load_rgb_profile(cpp)


def test_capture_reads_private_directory_or_zip_without_mutation(tmp_path):
    folder=tmp_path/'capture'
    (folder/'B').mkdir(parents=True)
    (folder/'B'/'sample.bin').write_bytes(b'NES source capture')
    (folder/'report.json').write_text('{"checked":true}')
    with CaptureSource(folder) as src:
        assert src.read('B/sample.bin')==b'NES source capture'
        assert src.fingerprint()['source_format']=='directory'
        with pytest.raises(ValueError,match='Unexpected'):
            src.read('../oops')
    archive=tmp_path/'capture.zip'
    with zipfile.ZipFile(archive,'w') as out:
        out.write(folder/'B'/'sample.bin',arcname='B/sample.bin')
    with CaptureSource(archive) as src:
        assert src.read('B/sample.bin')==b'NES source capture'
        assert src.fingerprint()['source_format']=='zip'
    assert (folder/'B'/'sample.bin').read_bytes()==b'NES source capture'


def test_chr_pages_must_map_uniquely_to_original_chr(tmp_path):
    chr_rom=b''.join(bytes([i])*1024 for i in range(8))
    snapshot=b''.join(chr_rom[i*1024:(i+1)*1024] for i in [4,5,6,7])+bytes(8192)
    assert resolve_chr_pages(chr_rom,snapshot)==[4,5,6,7]
    with pytest.raises(ValueError,match='length'):
        resolve_chr_pages(chr_rom,b'')
    dupe=bytes(1024)*2+chr_rom
    with pytest.raises(ValueError,match='uniquely'):
        resolve_chr_pages(dupe,bytes(1024)+snapshot[1024:])


def test_unsupported_rom_rejected_not_opened_as_native_asset(tmp_path):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('test.nes',b'NES\x1a'+bytes(12))
    with pytest.raises(ValueError,match='Verified SMB3'):
        input_rom(archive)


def test_gif_encoder_is_looping_and_deterministic_with_fixed_palette(tmp_path):
    colors=[(i*4,0,0) for i in range(64)]
    frames=[Image.new('RGB',(16,12),colors[i%2]) for i in range(8)]
    path=tmp_path/'loop.gif'
    encode_gif(frames,colors,80,2,path)
    first_hash=sha(path.read_bytes())
    with Image.open(path) as gif:
        assert gif.n_frames==8
        assert gif.size==(32,24)
        assert gif.info['loop']==0
        timings=[]
        for n in range(gif.n_frames):
            gif.seek(n);timings.append(gif.info['duration'])
        assert timings==[80]*8
    encode_gif(frames,colors,80,2,path)
    assert sha(path.read_bytes())==first_hash


class FakeAssets:
    def __init__(self):
        self.coin=Image.new('RGBA',(8,8),(255,0,0,255))
        self.mario_fly=Image.new('RGBA',(12,12),(0,255,0,255))
        self.mario_idle=Image.new('RGBA',(12,12),(0,0,255,255))
    def metatile(self,number):
        return Image.new('RGBA',(16,16),(number,0,0,255))


def test_independent_animation_changes_frames_without_mutating_scene():
    r=default_recipe()
    base=Image.new('RGBA',(r['width'],r['height']),(0,0,0,255))
    art=FakeAssets()
    before=base.tobytes()
    a=draw_frame(art,r,base,0)
    b=draw_frame(art,r,base,4)
    c=draw_frame(art,r,base,12)
    assert base.tobytes()==before  # composition does not overwrite reusable background
    x,y=r['blocks'][1]['x'],r['blocks'][1]['y']
    assert a.getpixel((x,y))!=b.getpixel((x,y))  # question block cycle
    mx=r['mario']['anchor_x']; my=r['mario']['feet_y']-8
    assert a.getpixel((mx,my))!=c.getpixel((mx,my))  # Mario pose changed
    assert a.tobytes()!=b.tobytes()