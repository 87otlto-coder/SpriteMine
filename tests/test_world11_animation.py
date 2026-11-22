"""Public synthetic and private opt-in tests for bank-switched M1 scene export."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'m1_world11'))
from animate_world11 import bank_cycle,decode_metatile,build,export_animated_scene


def test_regular_level_phase_cycle_start_matches_capture():
    assert bank_cycle((100,101))==((100,101),(102,103),(96,97),(98,99))
    assert bank_cycle((96,97))==((96,97),(98,99),(100,101),(102,103))
    with pytest.raises(ValueError,match='not one of'):
        bank_cycle((104,105))


def test_2bpp_metatile_uses_selected_1k_pages():
    # Pattern 0 maps to PPU CHR slot 2 ($0800). Fill one pixel with color 3,
    # keeping another bank's pattern different. No game ROM is used.
    rom=bytearray(0x20000)
    for page,color in ((96,1),(98,2),(100,3),(102,0)):
        rom[page*1024]=0x80 if color & 1 else 0
        rom[page*1024+8]=0x80 if color & 2 else 0
    quad=bytes([128]*1024)  # pattern 128 => PPU $0800 (start of bank slot 2)
    groups=tuple(tuple((n,n,n) for n in range(4)) for _ in range(4))
    values=[]
    for base in (96,98,100,102):
        im=decode_metatile(bytes(rom),quad,0,(8,9,base,base+1),groups)
        assert im.size==(16,16)
        values.append(im.getpixel((0,0))[0])
        assert im.getpixel((1,0))==(0,0,0)
    assert values==[1,2,3,0]


def test_scene_export_animated_layers_synthetic(tmp_path):
    """Actual PR #29 compositor can overlay two independent four-phase tracks."""
    from spritemine.scene import Scene
    from spritemine.scene_export import export
    root=tmp_path/'scene';root.mkdir()
    base=Image.new('RGB',(16,16),(20,20,20));base.save(root/'static.png')
    assets={'s':{'file':'static.png'}}
    for t in range(4):
        for kind in (0,1):
            name=f'{kind}_{t}'
            im=Image.new('RGB',(16,16),(t*50,kind*80,30))
            im.save(root/f'{name}.png')
            assets[name]={'file':f'{name}.png'}
    spec={'version':1,'size':[32,16],'tile_size':[16,16],'ticks':4,
          'tick_ms':130,'background':[0,0,0],'assets':assets,
          'layers':[{'tiles':[['s','s']]},{'tracks':[
              {'at':[kind*16,0], 'cels':[{'asset':f'{kind}_{t}','ticks':1} for t in range(4)]}
              for kind in (0,1)]}]}
    recipe=root/'recipe.json';recipe.write_text(json.dumps(spec))
    scene=Scene.load(recipe)
    assert scene.render(1).getpixel((0,0))==(50,0,30)
    assert scene.render(1).getpixel((16,0))==(50,80,30)
    out=tmp_path/'export'
    export(recipe,out)
    with Image.open(out/'scene.gif') as gif:
        assert gif.n_frames==4 and gif.info['loop']==0
        for tick in range(4):
            gif.seek(tick)
            assert gif.info['duration']==130
            assert gif.convert('RGB').tobytes()==scene.render(tick).tobytes()


def test_private_full_width_animation_and_determinism_opt_in(tmp_path):
    rom=os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    graphics=os.environ.get('SPRITEMINE_PRIVATE_GRAPHICS_ZIP')
    rgb=os.environ.get('SPRITEMINE_PRIVATE_RGB_PROFILE')
    if not all((rom,graphics,rgb)):
        pytest.skip('Owner-controlled private SMB3 source inputs not supplied')
    from make_m1_bundle import build as build_static
    static=build_static(Path(rom),tmp_path/'static',graphics_zip=Path(graphics),rgb=Path(rgb))
    animated=build(Path(rom),static,Path(graphics),Path(rgb),tmp_path/'animated')
    spec=json.loads(animated.read_text('utf8'))
    assert spec['size']==[2816,432]
    assert spec['tick_ms']==130 and spec['ticks']==4
    assert spec['staging_provenance']['animation']['source_timing_class'].startswith('decoded_game')
    report=json.loads((animated.parent/'animation_report.json').read_text('utf8'))
    assert report['phase_banks']==[[100,101],[102,103],[96,97],[98,99]]
    assert report['source_dynamic_tiles']['tile_40']==23
    assert report['track_count']==51
    from spritemine.scene import Scene
    scene=Scene.load(animated)
    with Image.open(static.parent.parent/'partial_chr_preview.png') as p:
        assert p.convert('RGB').tobytes()==scene.render(0).tobytes()
    first=export_animated_scene(animated,tmp_path/'gif1')
    second=export_animated_scene(animated,tmp_path/'gif2')
    assert first['gif_rgb_matches_all_png_frames']
    assert first['gif_sha256']==second['gif_sha256']
    for n,digest in first['png_frame_sha256'].items():
        assert second['png_frame_sha256'][n]==digest
    with pytest.raises(FileExistsError):
        build(Path(rom),static,Path(graphics),Path(rgb),tmp_path/'animated')
