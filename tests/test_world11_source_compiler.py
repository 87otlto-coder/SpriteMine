"""Synthetic tests and opt-in private-ROM checks for World 1-1 source compiler."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'/'m1_world11'))
from world11_compile import (parse_stream, Layout, compile_image, diagnostic_image,
                             COLS, ROWS, SKY, ROM_SHA)


def test_parse_extended_and_fixed():
    # Artificial stream: one ground run followed by randomized-cloud marker.
    stream = bytes.fromhex('1A 00 C0 02 00 00 03 FF')
    cmds = parse_stream(stream)
    assert len(cmds) == 2
    assert (cmds[0].kind, cmds[0].index, cmds[0].x, cmds[0].y, cmds[0].extra) == ('generator', 11, 0, 26, 2)
    assert (cmds[1].kind, cmds[1].index, cmds[1].relative) == ('fixed',3,4)
    layout=Layout().run(cmds)
    assert layout.tiles[26][:4] == [0x55,0x53,0x57,SKY]
    assert layout.random_clouds_unknown
    assert len(layout.unsupported) == 1


def test_malformed_stream_fails_closed():
    for stream in (b'',b'\x1a\x00',b'\x1a\x00\xc0',b'\xff\xff',b'\x1a\x00\xc0\xff'):
        with pytest.raises(ValueError):parse_stream(stream)


def test_ground_and_pipe_generator_synthetic():
    cmds = parse_stream(bytes.fromhex('1A 00 C0 02 37 16 A2 FF'))
    layout = Layout().run(cmds)
    assert layout.tiles[26][0:3] == [0x55,0x53,0x57]
    # The synthetic floor only spans columns 0-2, so this pipe in open sky
    # still has its complete programmed body.
    assert layout.tiles[26][22:24] == [0xBA,0xBB]
    assert layout.pipe_ground_overlaps == []
    assert layout.tiles[23][22:24] == [0xB1,0xB2]
    assert layout.tiles[24][22:24] == [0xBA,0xBB]


def test_full_private_rom_opt_in():
    zip_path = os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    if not zip_path:
        pytest.skip('private ROM not provided; no copyrighted fixture in repo')
    with zipfile.ZipFile(zip_path) as z:
        members=[x for x in z.namelist() if x.lower().endswith('.nes')]
        assert len(members)==1
        image=z.read(members[0])
    assert hashlib.sha256(image).hexdigest()==ROM_SHA
    commands,layout,report=compile_image(image)
    assert len(commands)==86
    assert report['canvas_tiles']==[COLS,ROWS]
    assert report['nominal_pixels']==[2816,432]
    assert len(layout.executed)==84
    assert len(layout.unsupported)==1
    assert layout.random_clouds_unknown
    assert [layout.tiles[26][x] for x in (0,1,38,39,67,68,72,93,94,96,104)] == [
        0x55,0x53,0x57,0x56,0x58,SKY,0x55,0x57,SKY,0x55,0x55]
    assert layout.tiles[25][39]==0x55
    assert layout.tiles[7][141:143]==[0xAD,0xAE]
    # The one-tile pit LEFT of the tall pipe is genuine. The right side of
    # the pipe must not overwrite ground at its foot.
    assert layout.tiles[26][139:147]==[0x57,SKY,0x55,0x53,0x53,0x53,0x53,0x53]
    assert {(e['x'],e['y']) for e in report['pipe_ground_overlaps']} >= {
        (141,26),(142,26),(145,26),(146,26)}
    assert layout.tiles[0][155:157]==[0x01,0x00]
    # Framebuffer equivalence is deliberately not asserted here.
    assert report['native_render_verified'] is False
    assert diagnostic_image(layout).size==(2816,432)
    _, second, report2=compile_image(image)
    assert second.tiles==layout.tiles
    assert json.dumps(report,sort_keys=True)==json.dumps(report2,sort_keys=True)


def test_pipe_body_without_ground_preserves_full_height():
    # The source routine really does draw low-nibble+1 body rows. The ground
    # suppression must only apply to existing ground, not shorten every pipe.
    cmds = parse_stream(bytes.fromhex('25 11 A2 FF'))
    layout=Layout().run(cmds)
    assert layout.tiles[5][17:19]==[0xB1,0xB2]
    for row in (6,7,8):
        assert layout.tiles[row][17:19]==[0xBA,0xBB]
    assert layout.pipe_ground_overlaps==[]


def test_pit_adjacent_to_pipe_does_not_become_solid_ground():
    # The pit instruction must preserve the sky column while restoring the
    # edge of the ground beside the pipe.
    # Synthetic order mirrors source: floor, pipe, then a single-row pit.
    from world11_compile import Command
    floor=Command(100,0,'generator',11,10,26,0xC0,14)
    pipe=Command(104,4,'generator',24,18,23,0xA2)
    pit=Command(108,8,'generator',9,16,26,0xA2)
    layout=Layout().run([floor,pipe,pit])
    assert layout.tiles[26][16:20]==[0x57,SKY,0x55,0x53]
    assert layout.tiles[25][18:20]==[0xBA,0xBB]


def test_invalid_rom_rejected():
    with pytest.raises(ValueError,match='fingerprint'):
        compile_image(b'NES\x1a' + bytes(128))


def test_private_scene_recipe_reproduces_source_preview(tmp_path):
    zip_path = os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    if not zip_path:
        pytest.skip('private ROM not provided')
    from PIL import Image
    from preview_tiles import export_private_scene_bundle, render
    with zipfile.ZipFile(zip_path) as z:
        raw=z.read([x for x in z.namelist() if x.lower().endswith('.nes')][0])
    _, model, report=compile_image(raw)
    recipe_path=export_private_scene_bundle(raw,model,report,tmp_path/'scene')
    spec=json.loads(recipe_path.read_text())
    assert spec['size']==[2816,432]
    assert spec['layers'][0]['tiles'][7][141]=='tile_ad'
    assert spec['staging_provenance']['native_verified'] is False
    assert spec['staging_provenance']['pipe_floor_visual_overlap_corrections']
    composed=Image.new('RGB',(2816,432))
    for row, names in enumerate(spec['layers'][0]['tiles']):
        for column, name in enumerate(names):
            with Image.open(recipe_path.parent/spec['assets'][name]['file']) as tile:
                composed.paste(tile,(column*16,row*16))
    assert composed.tobytes()==render(raw,model).tobytes()
    with pytest.raises(FileExistsError):
        export_private_scene_bundle(raw,model,report,recipe_path.parent)


def test_native_graphics_profile_snapshot_validation(tmp_path):
    zip_path = os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    if not zip_path:
        pytest.skip('private ROM not provided')
    from preview_tiles import load_native_graphics_profile
    with zipfile.ZipFile(zip_path) as z:
        raw=z.read([x for x in z.namelist() if x.lower().endswith('.nes')][0])
    chr_rom=raw[16+0x40000:16+0x40000+0x20000]
    # Artificial PPU snapshot built from known ROM pages. This is not a
    # claim that the game's actual mapper selected these pages on any frame.
    ppu=bytearray(0x3000)
    indices=(8,9,100,101)
    for i,k in enumerate(indices):
        ppu[i*1024:(i+1)*1024]=chr_rom[k*1024:(k+1)*1024]
    ppuf=tmp_path/'ppu.bin';ppuf.write_bytes(ppu)
    palf=tmp_path/'palette.bin';palf.write_bytes(bytes(range(32)))
    rgbf=tmp_path/'rgb.bin';rgbf.write_bytes(bytes(j for i in range(64) for j in (i,0,0)))
    pages, groups, source=load_native_graphics_profile(raw,ppuf,palf,rgbf)
    assert pages==indices
    assert groups[0][0]==(0,0,0)
    assert groups[1][1]==(5,0,0)
    assert source['world_wide_mapping_verified'] is False
    palf.write_bytes(bytes([64]*32))
    with pytest.raises(ValueError,match='palette codes'):
        load_native_graphics_profile(raw,ppuf,palf,rgbf)


def test_cli_private_bundle_contains_source_writers(tmp_path):
    zip_path=os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    if not zip_path:
        pytest.skip('private ROM not provided')
    from make_m1_bundle import build
    build(Path(zip_path),tmp_path/'output')
    ledger=json.loads((tmp_path/'output'/'source_tile_ledger.json').read_text())
    cmds=json.loads((tmp_path/'output'/'source_command_ledger.json').read_text())
    assert len(cmds['commands'])==86
    assert ledger['last_writer_ROM_offset_or_null'][7][141] is not None
    assert ledger['last_writer_ROM_offset_or_null'][0][0] is None
    assert ledger['native_verified_cells']==0
    assert len(ledger['logical_tile_ids'])==27
    assert all(len(row)==176 for row in ledger['logical_tile_ids'])


def test_native_pipe_screenshot_comparator_detects_one_pixel(tmp_path):
    from PIL import Image
    from verify_pipe_native import compare
    candidate=Image.new('RGB',(2816,432),(10,20,30))
    target=tmp_path/'candidate.png'; candidate.save(target)
    screenshot=Image.new('RGB',(506,483),(10,20,30))
    reference=tmp_path/'reference.png'; screenshot.save(reference)
    result=compare(target,reference)
    assert result['mismatching_samples']==0
    assert result['unique_world_pixel_positions']==1920
    assert result['display_rgb_pixel_samples']==7680
    screenshot.putpixel((97,354),(255,0,0))
    screenshot.save(reference)
    broken=compare(target,reference)
    assert broken['mismatching_samples']==1
    assert broken['per_column_mismatches']['139']==1


def test_native_pipe_screenshot_reference_opt_in():
    import os
    path=os.environ.get('SPRITEMINE_PRIVATE_NATIVE_PIPE_SCREENSHOT')
    romzip=os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    rgb=os.environ.get('SPRITEMINE_PRIVATE_RGB_PROFILE')
    ppu=os.environ.get('SPRITEMINE_PRIVATE_PPU_450840')
    palette=os.environ.get('SPRITEMINE_PRIVATE_PALETTE_450840')
    if not all((path,romzip,rgb,ppu,palette)):
        pytest.skip('private native screenshot and graphics profile not provided')
    from verify_pipe_native import compare
    from preview_tiles import load_native_graphics_profile,render
    from PIL import Image
    with zipfile.ZipFile(romzip) as z:
        raw=z.read([n for n in z.namelist() if n.lower().endswith('.nes')][0])
    pages, groups, provenance=load_native_graphics_profile(raw,Path(ppu),Path(palette),Path(rgb))
    _, model, _=compile_image(raw)
    img=render(raw,model,page_mapping=pages,palette_groups=groups)
    # Write to the test's temporary directory without bundling private art.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        png=Path(tmp)/'preview.png';img.save(png)
        result=compare(png,Path(path))
    assert result['mismatching_samples']==0, result['per_column_mismatches']


def test_video_reference_synthetic_tolerance_and_exclusion(tmp_path):
    from PIL import Image
    from verify_video_reference import compare
    scene=Image.new('RGB',(32,32),(24,60,92))
    frame=Image.new('RGB',(64,64),(24,60,92))
    scene_path=tmp_path/'scene.png';frame_path=tmp_path/'frame.png'
    scene.save(scene_path);frame.save(frame_path)
    report=compare(scene_path,frame_path,frame_rect=(0,0,64,64),world_origin=(0,0),scale=2,
                   excluded_rects=((0,0,2,3),),tolerance=0)
    assert report['compared_positions']==1024-6
    assert report['outside_tolerance']==0
    frame.putpixel((12,14),(255,255,255));frame.save(frame_path)
    broken=compare(scene_path,frame_path,frame_rect=(0,0,64,64),world_origin=(0,0),scale=2,tolerance=0)
    assert broken['outside_tolerance'] > 0
    assert broken['source_class'].startswith('compressed_video')


def test_private_graphics_zip_and_goal_source(tmp_path):
    zip_path=os.environ.get('SPRITEMINE_PRIVATE_ROM_ZIP')
    graphics=os.environ.get('SPRITEMINE_PRIVATE_GRAPHICS_ZIP')
    rgb=os.environ.get('SPRITEMINE_PRIVATE_RGB_PROFILE')
    if not (zip_path and graphics and rgb):
        pytest.skip('private ROM, frame capture ZIP and RGB profile not supplied')
    from make_m1_bundle import build
    recipe=build(Path(zip_path),tmp_path/'native',graphics_zip=Path(graphics),rgb=Path(rgb))
    data=json.loads(recipe.read_text())
    provenance=data['staging_provenance']['graphics_snapshot_provenance']
    assert provenance['capture_frame']=='450840'
    assert provenance['mapped_chr_pages']==[8,9,100,101]
    ledger=json.loads((tmp_path/'native'/'source_tile_ledger.json').read_text())
    # At the goal edge, the authentic zigzag is metatile 0x01 for all rows
    # above ground, and ground tile 0x53 below it. Adjacent black filler is 0.
    assert all(ledger['logical_tile_ids'][y][155]==0x01 for y in range(26))
    assert all(ledger['logical_tile_ids'][y][156]==0x00 for y in range(20))
    assert ledger['logical_tile_ids'][26][155]==0x53
    assert ledger['logical_tile_ids'][20][163]==0x14


def test_reference_goal_silhouette_opt_in():
    preview=os.environ.get('SPRITEMINE_PRIVATE_PREVIEW_450840')
    frame=os.environ.get('SPRITEMINE_PRIVATE_GOAL_VIDEO_FRAME')
    if not (preview and frame):
        pytest.skip('private gameplay recording reference not supplied')
    from verify_video_reference import compare_goal_silhouette
    result=compare_goal_silhouette(Path(preview),Path(frame))
    assert result['classified_pixels']==4960
    assert result['mismatching_classes']==0
    assert result['native_rgb_accepted'] is False
