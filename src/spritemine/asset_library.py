"""Index existing private SMB3 exports; never mutate source assets."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import subprocess
import wave
from pathlib import Path
from urllib.parse import quote
from PIL import Image


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def inside(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute(): raise ValueError(f'Unsafe absolute path: {relative}')
    p = (root / relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError(f'Missing or unsafe asset: {relative}')
    return p


def load(root: Path, relative: str) -> dict:
    return json.loads(inside(root, relative).read_text(encoding='utf-8'))


def build(root: Path) -> dict:
    root = root.resolve()
    entries = []
    ids = set()
    def add(id, name, kind, file, expected, provenance, tags):
        if id in ids:
            raise ValueError(f'Duplicate ID: {id}')
        p = inside(root, file)
        actual = digest(p)
        if actual != expected:
            raise ValueError(f'Hash mismatch: {file}')
        item = dict(id=id, name=name, kind=kind, file=file, sha256=actual,
                    provenance=provenance, tags=tags)
        if kind in ('graphic', 'animation'):
            with Image.open(p) as im:
                item.update(dimensions=list(im.size), frames=getattr(im,'n_frames',1))
        else:
            with wave.open(str(p),'rb') as wav:
                item.update(sample_rate=wav.getframerate(), channels=wav.getnchannels(),
                            sample_width=wav.getsampwidth(), samples=wav.getnframes(),
                            seconds=wav.getnframes()/wav.getframerate())
        entries.append(item); ids.add(id)
    scene = load(root, 'stage/recipe.json')
    for key, info in sorted(scene['assets'].items()):
        group = info['file'].split('/')[0]
        add('stage:'+key, key.replace('_',' '), 'graphic', 'stage/'+info['file'],
            info['sha256'], info['provenance'], ['world 1-1',group])
    proof = load(root, 'stage_export/ground_export_verification.json')
    add('stage:panorama','World 1-1 — animated panorama','animation','stage_export/scene.gif',
        proof['gif_sha256'],proof,['world 1-1','composition','owner accepted'])
    world = load(root, 'map/manifest.json')
    for file, sha in sorted(world['files'].items()):
        kind = 'animation' if file.endswith(('.gif','.apng')) else 'graphic'
        name = {'world1_4x.gif':'World 1 — animated map (4×)',
                'world1_native.apng':'World 1 — animated map (native)'}.get(file,file.replace('_',' '))
        add('map:'+file,name,kind,'map/'+file,sha,
            {'manifest':'map/manifest.json','rom_sha256':world['rom_sha256'],
             'source_prg_offsets_excluding_header':world['source_prg_offsets_excluding_header'],
             'limitations':world['limitations']},['world 1','map','background only'])
    audio = load(root,'audio/manifest.json')
    unavailable=[]
    for req in audio['requests']:
        if not req['exports']:
            unavailable.append({'id':'audio:'+req['name'], 'status':req['status']})
        for info in req['exports']+req.get('stems',[]):
            kind = 'channel' if 'voice' in info else req['category']
            name = req.get('display_name', req['name'].replace('_',' ').title())
            suffix = info['file'].removeprefix(req['name']+'_').removesuffix('.wav')
            add('audio:'+info['file'],name+' — '+suffix.replace('_',' '),kind,
                'audio/'+info['file'],info['sha256'],
                {'rom_sha256':audio['rom_sha256'],'manifest':'audio/manifest.json',
                 'queue':req['queue'],'value':req['value'],'source_symbol':req.get('source_symbol'),
                 'status':req['status'],'context':req.get('context',''),'export':info,
                 'loop':req.get('loop')},[req['name'],kind,suffix])
    roms={e['provenance'].get('rom_sha256') for e in entries} - {None}
    if roms != {world['rom_sha256']} or audio['rom_sha256'] != world['rom_sha256']:
        raise ValueError('Mixed ROM provenance')
    return {'schema':1,'rom_sha256':world['rom_sha256'],'assets':entries,'unavailable':unavailable}


def resolve_composition(catalog: dict, recipe: dict) -> tuple[dict,dict]:
    by_id={e['id']:e for e in catalog['assets']}
    if recipe.get('schema')!=1: raise ValueError('Unsupported composition schema')
    visual=by_id[recipe['visual']]; sound=by_id[recipe['audio']]
    if visual['kind']!='animation' or sound['kind']!='music':
        raise ValueError('Composition requires animation and music')
    return visual,sound


def index_html(catalog:dict, recipe:dict) -> str:
    esc=lambda x:html.escape(str(x),quote=True)
    url=lambda x:esc(quote(x,safe='/'))
    visual,sound=resolve_composition(catalog,recipe)
    cards=[]
    for e in catalog['assets']:
        search=esc(' '.join([e['name'],e['id'],e['kind'],*e['tags'],str(e['provenance'].get('source_symbol',''))]).lower())
        media=(f'<img loading="lazy" src="{url(e["file"])}" alt="{esc(e["name"])}">' if e['kind'] in ('graphic','animation') else f'<audio controls preload="none" src="{url(e["file"])}" {"loop" if e["file"].endswith("_loop.wav") else ""}></audio>')
        cards.append(f'<article data-search="{search}" data-kind="{esc(e["kind"])}"><h3>{esc(e["name"])}</h3><small>{esc(e["kind"])}</small>{media}<a href="{url(e["file"])}" download>Export original</a><details><summary>Provenance</summary><pre>{esc(json.dumps(e,indent=2))}</pre></details></article>')
    options=''.join(f'<option>{esc(k)}</option>' for k in sorted({e['kind'] for e in catalog['assets']}))
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SpriteMine M3</title><style>body{background:#15181e;color:#e8ebf0;font:15px system-ui;max-width:1240px;margin:24px auto;padding:0 20px}h1{letter-spacing:-1px}a{color:#95cfef}input,select{padding:10px;border:1px solid #59616f;background:#252a33;color:white;border-radius:6px}section{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}article{min-width:0;background:#20252c;border:1px solid #363d48;border-radius:8px;padding:12px}article[hidden]{display:none}article h3{font-size:15px;overflow-wrap:anywhere}article img{width:100%;height:110px;object-fit:contain;image-rendering:pixelated;background:#101216}article audio{width:100%}small{display:block;color:#a9b4c2;margin-bottom:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}details{margin-top:8px}#hero{max-width:768px;width:100%;image-rendering:pixelated}#count{color:#abb6c3}</style><h1>SpriteMine · Unified asset library</h1><p>Private SMB3 PRG1 assets. Existing ROM-derived and composed outputs, not exhaustive game coverage.</p>'''+f'<h2>{esc(recipe["name"])}</h2><img id="hero" src="{url(visual["file"])}" alt="World 1 animated map"><p><audio controls loop preload="none" src="{url(sound["file"])}"></audio></p><p>Independent visual and music loops. <a href="composition.json" download>Editable recipe</a> · <a href="catalog.json" download>Catalog JSON</a></p><h2>Browse assets</h2><input id="q" placeholder="Search names, IDs, tags" aria-label="Search"> <select id="k" aria-label="Asset type"><option value="">All types</option>{options}</select> <span id="count"></span><section>'+''.join(cards)+'''</section><script>const q=document.getElementById('q'),k=document.getElementById('k'),cards=[...document.querySelectorAll('article')];function filter(){let n=0;for(const c of cards){c.hidden=!(c.dataset.search.includes(q.value.trim().toLowerCase())&&(!k.value||c.dataset.kind===k.value));if(!c.hidden)n++}document.getElementById('count').textContent=n+' assets'}q.addEventListener('input',filter);k.addEventListener('change',filter);filter()</script></html>'''


def write_library(root:Path) -> dict:
    catalog=build(root)
    recipe={'schema':1,'name':'World 1 — animated map with original map music',
            'visual':'map:world1_4x.gif','audio':'audio:world_1_loop.wav',
            'playback':'independent loops; no shared seamless period claimed'}
    if (root/'composition.json').is_file(): recipe=load(root,'composition.json')
    page=index_html(catalog,recipe)
    for name,data in [('catalog.json',json.dumps(catalog,indent=2,sort_keys=True)+'\n'),
                      ('composition.json',json.dumps(recipe,indent=2)+'\n'),('index.html',page)]:
        target=root/name
        if target.is_symlink() or (target.exists() and target.stat().st_nlink>1):
            raise ValueError(f'Unsafe metadata output: {target}')
        target.write_text(data,encoding='utf-8')
    return catalog


def export_video(root:Path, output:Path, seconds:float, ffmpeg:str='ffmpeg') -> None:
    if not 0 < seconds <= 600: raise ValueError('Duration must be within 0–600 seconds')
    c=build(root); v,a=resolve_composition(c,load(root,'composition.json'))
    if output.exists(): raise FileExistsError(output)
    # Convenience preview: lossy H.264/AAC. Source GIF/WAV remain unchanged.
    subprocess.run([ffmpeg,'-nostdin','-n','-stream_loop','-1','-i',str(inside(root,v['file'])),
                    '-stream_loop','-1','-i',str(inside(root,a['file'])),'-t',str(seconds),
                    '-vf','fps=30,format=yuv420p','-c:v','libx264','-crf','18','-c:a','aac','-b:a','192k',
                    '-movflags','+faststart',str(output)],check=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    p.add_argument('--video',type=Path);p.add_argument('--seconds',type=float,default=14.4);p.add_argument('--ffmpeg',default='ffmpeg')
    args=p.parse_args();print(f"Indexed {len(write_library(args.root)['assets'])} verified assets")
    if args.video: export_video(args.root,args.video,args.seconds,args.ffmpeg)

if __name__=='__main__':main()
