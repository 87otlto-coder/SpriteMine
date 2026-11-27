import json
import wave
from pathlib import Path
import pytest
from PIL import Image
from spritemine import asset_library as a


def fixture(root):
    for folder in ('stage','stage_export','map','audio'):
        (root/folder).mkdir()
    def save(path, data):
        (root/path).write_text(json.dumps(data), encoding='utf-8')
    for path in ('stage/tile.png','stage_export/scene.gif','map/world1_4x.gif'):
        Image.new('RGB',(8,8),'red').save(root/path)
    with wave.open(str(root/'audio/world_1_loop.wav'),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\0'*160)
    save('stage/recipe.json',{'assets':{'tile':{'file':'tile.png','sha256':a.digest(root/'stage/tile.png'),'provenance':{'rom_sha256':'test'}}}})
    save('stage_export/ground_export_verification.json',{'gif_sha256':a.digest(root/'stage_export/scene.gif')})
    save('map/manifest.json',{'files':{'world1_4x.gif':a.digest(root/'map/world1_4x.gif')},'rom_sha256':'test','source_prg_offsets_excluding_header':{},'limitations':[]})
    save('audio/manifest.json',{'rom_sha256':'test','requests':[{'name':'world_1','display_name':'World 1 — Map Theme','category':'music','queue':1269,'value':1,'status':'test','exports':[{'file':'world_1_loop.wav','sha256':a.digest(root/'audio/world_1_loop.wav')}]},{'name':'resume','category':'effect','status':'silent','exports':[]}]})


def test_catalog(tmp_path):
    fixture(tmp_path)
    c=a.write_library(tmp_path)
    assert len(c['assets'])==4 and c['unavailable'][0]['id']=='audio:resume'
    assert c==a.write_library(tmp_path)
    assert 'World 1 — Map Theme' in (tmp_path/'index.html').read_text(encoding='utf-8')
    assert a.resolve_composition(c,a.load(tmp_path,'composition.json'))[0]['kind']=='animation'


def test_tampered_file(tmp_path):
    fixture(tmp_path);(tmp_path/'audio/world_1_loop.wav').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Hash mismatch'): a.build(tmp_path)


def test_path_escape(tmp_path):
    p=tmp_path/'root';p.mkdir();(tmp_path/'outside').touch()
    with pytest.raises(ValueError,match='unsafe'): a.inside(p,'../outside')


def test_wrong_composition_kind(tmp_path):
    fixture(tmp_path);c=a.build(tmp_path)
    with pytest.raises(ValueError,match='requires animation'): a.resolve_composition(c,{'schema':1,'visual':'stage:tile','audio':'audio:world_1_loop.wav'})


def test_mixed_rom(tmp_path):
    fixture(tmp_path);p=tmp_path/'audio/manifest.json';d=json.loads(p.read_text());d['rom_sha256']='wrong';p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='Mixed ROM'): a.build(tmp_path)
