"""SpriteMine creative prototype: World 1-1-inspired stage GIF from private PRG1 ROM + MesenCE capture.

Only source code is suitable for public GitHub. Original ROM, native capture and rendered
artwork remain private; creative layout/motion must never be labelled native level decoding.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, zipfile
from pathlib import Path
from PIL import Image, ImageDraw

ROM_SHA = '4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579'
QUAD_SHA = 'c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362'
SAMPLE_FRAME = 450840
BG_SKY = (181, 235, 242)


def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def image_from_rgb(data: bytes) -> Image.Image:
    if len(data) != 256*240*3: raise ValueError('Expected 256x240 native RGB frame')
    return Image.frombytes('RGB',(256,240),data)


def input_rom(path: Path) -> bytes:
    with zipfile.ZipFile(path) as z:
        names=[i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith('.nes')]
        if len(names)!=1: raise ValueError('One NES file expected in ZIP')
        data=z.read(names[0])
    if sha(data)!=ROM_SHA: raise ValueError('Verified SMB3 US PRG1 ROM mismatch')
    return data


def resolve_chr_pages(chr_rom: bytes, snapshot: bytes) -> list[int]:
    if len(snapshot)!=12288: raise ValueError('Native PPU snapshot length mismatch')
    pages=[]
    for i in range(4):
        block=snapshot[i*1024:(i+1)*1024]
        matches=[j for j in range(len(chr_rom)//1024) if chr_rom[j*1024:(j+1)*1024]==block]
        if len(matches)!=1: raise ValueError(f'PPU background page {i} not uniquely mapped to ROM')
        pages.append(matches[0])
    return pages


def load_rgb_profile(path: Path) -> list[tuple[int,int,int]]:
    """Read local MesenCE 2C02 source or a private 64-color JSON cache.

    No GPL C++ source/table is included in the public SpriteMine repository.
    """
    source=path.read_text(encoding='utf-8-sig')
    if path.suffix.lower()=='.json':
        data=json.loads(source)
        if data.get('profile')!='MesenCE_2C02_default_reference':
            raise ValueError('Unknown local RGB profile')
        codes=data['rgb_hex']
    else:
        match=re.search(r'/\*\s*2C02\s*\*/\s*\{([^}]*)\}',source)
        if not match: raise ValueError('Pinned MesenCE source missing 2C02 default palette')
        codes=re.findall(r'\b0xFF([0-9a-fA-F]{6})\b',match.group(1))
    if len(codes)!=64: raise ValueError('Expected 64 RGB entries')
    return [tuple(bytes.fromhex(code)) for code in codes]


class CaptureSource:
    """Read private MesenCE data from B.zip or the owner's existing replay folder."""
    def __init__(self,path:Path):
        self.path=path
        self.zip=None
        if path.is_file(): self.zip=zipfile.ZipFile(path)
        elif not (path.is_dir() and (path/'B').is_dir()):
            raise FileNotFoundError('Expected existing capture directory with B/ or B.zip')

    def read(self,relative:str)->bytes:
        if not relative.startswith('B/') or '..' in relative.split('/'):
            raise ValueError('Unexpected capture member path')
        return self.zip.read(relative) if self.zip else (self.path/relative).read_bytes()

    def fingerprint(self)->dict:
        if self.zip:
            return {'source_format':'zip','sha256':sha(self.path.read_bytes())}
        report=self.path/'report.json'
        if report.is_file():return {'source_format':'directory','report_json_sha256':sha(report.read_bytes())}
        return {'source_format':'directory','ppu_snapshot_sha256':sha(self.read(f'B/{SAMPLE_FRAME}-start-ppu.bin'))}

    def __enter__(self):return self
    def __exit__(self,*args):
        if self.zip:self.zip.close()


def validate_animation_periods(recipe:dict)->None:
    """Require every independent animation to complete whole cycles per GIF loop."""
    frames=recipe['frames']
    for block in recipe['blocks']:
        if 'frames' in block:
            period=len(block['frames'])*block['ticks_per_frame']
            if period<=0 or frames%period:raise ValueError('Question block does not wrap at GIF seam')
    for c in recipe['coins']:
        if c['period_frames']!=8 or frames%8 or frames%c['bob_period']:
            raise ValueError('Coin period does not wrap at GIF seam')
    mario=recipe['mario']
    if frames%mario['bob_period'] or frames%(2*mario['pose_period']):
        raise ValueError('Mario animation does not wrap at GIF seam')


class Art:
    def __init__(self, rom: bytes, archive: CaptureSource, rgb: list[tuple[int,int,int]]):
        self.chr=rom[16+256*1024:]
        self.table=rom[0x1e010:0x1e410]
        if sha(self.table)!=QUAD_SHA: raise ValueError('Expected original Plains quadrant table')
        self.palette=archive.read(f'B/{SAMPLE_FRAME}-start-palette.bin')
        self.pages=resolve_chr_pages(self.chr,archive.read(f'B/{SAMPLE_FRAME}-start-ppu.bin'))
        self.rgb=rgb
        self.tiles={}
        self.archive=archive
        self.sky=self.rgb[self.palette[0]&63]
        if self.sky!=BG_SKY: raise ValueError('Unexpected captured World 1-1 sky color')
        self.pipe=self._pipe()
        self.mario_fly=self._mario(450778)
        self.mario_idle=self._mario(450786)
        self.coin=self._coin()

    def metatile(self, number: int, sky_alpha: bool=False) -> Image.Image:
        key=(number,sky_alpha)
        if key in self.tiles: return self.tiles[key]
        if not 0<=number<=255: raise ValueError('Logical metatile outside 0..255')
        palgroup=number>>6
        colors=[self.rgb[self.palette[0]&63]]+[self.rgb[self.palette[4*palgroup+i]&63] for i in (1,2,3)]
        image=Image.new('RGBA',(16,16))
        # Source table: UL, LL, UR, LR; physical 1KiB page selection is snapshot-verified.
        for quadrant,xo,yo in ((0,0,0),(1,0,8),(2,8,0),(3,8,8)):
            tile=self.table[quadrant*256+number]
            address=tile*16
            base=self.pages[address//1024]*1024+(address%1024)
            tilebytes=self.chr[base:base+16]
            for y in range(8):
                for x in range(8):
                    bit=7-x
                    value=((tilebytes[y]>>bit)&1)+2*((tilebytes[y+8]>>bit)&1)
                    color=colors[value]
                    image.putpixel((xo+x,yo+y),color+(0 if sky_alpha and value==0 else 255,))
        self.tiles[key]=image
        return image

    def _frame(self,num:int)->Image.Image:
        return image_from_rgb(self.archive.read(f'B/{num}-end-rgb.bin'))

    def _pipe(self)->Image.Image:
        image=self._frame(SAMPLE_FRAME).crop((106,132,140,192)).convert('RGBA')
        image.putalpha(Image.new('L',image.size))
        # Extract authentic captured pipe, key only exact sky pixels.
        for y in range(image.height):
            for x in range(image.width):
                r,g,b,_=image.getpixel((x,y));image.putpixel((x,y),(r,g,b,0 if (r,g,b)==self.sky else 255))
        return image

    def _mario(self,num:int)->Image.Image:
        frame=self._frame(num).crop((99,63,140,112)).convert('RGBA')
        frame.putalpha(Image.new('L',frame.size))
        for y in range(frame.height):
            for x in range(frame.width):
                r,g,b,_=frame.getpixel((x,y));frame.putpixel((x,y),(r,g,b,0 if (r,g,b)==self.sky else 255))
        bbox=frame.getbbox()
        if not bbox: raise ValueError(f'Missing Mario sprite at {num}')
        trimmed=frame.crop(bbox)
        if trimmed.width>40 or trimmed.height>45: raise ValueError('Mario crop might contain background')
        return trimmed

    def _coin(self)->Image.Image:
        frame=self._frame(450881).crop((215,32,233,50)).convert('RGBA')
        # Bonus room background is black; preserve interior dark pixels by flood-filling
        # only exterior black, leaving enclosed outline pixels opaque.
        w,h=frame.size;pix=frame.load()
        seen=set(); stack=[]
        for x in range(w): stack.extend(((x,0),(x,h-1)))
        for y in range(h): stack.extend(((0,y),(w-1,y)))
        while stack:
            x,y=stack.pop()
            if (x,y) in seen or not 0<=x<w or not 0<=y<h:continue
            if pix[x,y][:3]!=(0,0,0):continue
            seen.add((x,y));stack.extend(((x+1,y),(x-1,y),(x,y+1),(x,y-1)))
        for y in range(h):
            for x in range(w):
                r,g,b,_=pix[x,y];pix[x,y]=(r,g,b,0 if (x,y) in seen else 255)
        bbox=frame.getbbox()
        if not bbox:raise ValueError('Missing captured coin')
        return frame.crop(bbox)


def default_recipe()->dict:
    return {
      'recipe_version':1,'project':'SpriteMine M1 — World 1-1 Creative Stage Loop',
      'source_class':'composed/edited','not_native_level_layout':True,
      'width':512,'height':288,'scale':2,'frames':48,'frame_duration_ms':80,
      'stage':{'ground_y':208,'dirt_tile_ids':[0x7A,0x7B],
               'captured_pipe':{'x':328,'bottom_y':208},
               'small_pipe':{'x':432,'bottom_y':208,'height':36},
               'hill_clusters':[[54,176],[220,176],[385,176]],
               'bushes':[[86,192],[260,192],[486,192]],
               'clouds':[[54,49],[252,41],[424,61]]},
      'blocks':[{'x':122,'y':114,'static_id':0x7A},
                {'x':138,'y':114,'frames':[0x60,0x61,0x62,0x63,0x64,0x65],'ticks_per_frame':4},
                {'x':154,'y':114,'static_id':0x7A},
                {'x':390,'y':96,'frames':[0x60,0x61,0x62,0x63,0x64,0x65],'ticks_per_frame':8}],
      'coins':[{'x':192,'y':93,'period_frames':8,'bob_period':24,'bob_amp':3},
               {'x':404,'y':61,'period_frames':8,'phase':4,'bob_period':16,'bob_amp':2},
               {'x':234,'y':137,'period_frames':8,'phase':2,'bob_period':24,'bob_amp':2}],
      'mario':{'anchor_x':345,'feet_y':145,'bob_period':24,'bob_amp':7,'pose_period':12},
      'transparency_policy':'sprites keyed by captured background; composited fixed-camera',
      'origin':'ROM Plains metatiles + MesenCE owner-captured pipe, Mario and coin art',
    }


def draw_cloud(canvas:Image.Image,x:int,y:int,white:tuple[int,int,int],shadow:tuple[int,int,int]):
    # Artist-composed cloud from NES palette colors, deliberately not a claimed ROM tile.
    d=ImageDraw.Draw(canvas)
    # 2px-step block outline; no antialiasing and no scrolling camera.
    outer=[(x+8,y+2,x+21,y+5),(x+3,y+6,x+30,y+12),
           (x+0,y+10,x+35,y+19),(x+4,y+20,x+31,y+22)]
    for box in outer:d.rectangle(box,fill=shadow)
    inner=[(x+8,y+4,x+21,y+8),(x+5,y+8,x+28,y+13),
           (x+2,y+12,x+33,y+18),(x+5,y+17,x+30,y+19)]
    for box in inner:d.rectangle(box,fill=white)


def bg_scene(art:Art,recipe:dict)->Image.Image:
    W,H=recipe['width'],recipe['height']
    image=Image.new('RGBA',(W,H),art.sky+(255,))
    colors=art.rgb
    cloud_white=colors[0x30];cloud_shade=colors[0x10]
    for x,y in recipe['stage']['clouds']:
        draw_cloud(image,x,y,cloud_white,cloud_shade)
    # Real 16x16 ROM-derived, artist-arranged green hills and plants.
    for x,y in recipe['stage']['hill_clusters']:
        for i,tid in enumerate((0x90,0x91,0x92,0x93)):
            image.alpha_composite(art.metatile(tid,sky_alpha=True),(x+16*i,y))
        # Second tier creates a richer multi-row crest with same source graphic.
        for i,tid in enumerate((0x90,0x91,0x92,0x93)):
            image.alpha_composite(art.metatile(tid,sky_alpha=True),(x+16*i,y+16))
    for x,y in recipe['stage']['bushes']:
        image.alpha_composite(art.metatile(0x85,sky_alpha=True),(x,y))
    ground=recipe['stage']['ground_y']
    ids=recipe['stage']['dirt_tile_ids']
    for y in range(ground,H,16):
        for x in range(0,W,16):
            tid=ids[((x//16)*7+(y-ground)//16)%len(ids)]
            image.alpha_composite(art.metatile(tid),(x,y))
    # Artist-added 2px grassy trim: green from genuine NES palette, not photo color.
    green=colors[0x2A]; darkgreen=colors[0x1A];d=ImageDraw.Draw(image)
    d.rectangle((0,ground-4,W-1,ground-3),fill=darkgreen)
    d.rectangle((0,ground-2,W-1,ground-1),fill=green)
    # The tall pipe is an actual sprite-free captured pipe from the MesenCE stage.
    pipe=recipe['stage']['captured_pipe']
    image.alpha_composite(art.pipe,(pipe['x'],pipe['bottom_y']-art.pipe.height))
    # A shorter pipe, constructed by reusing original pipe rim + cropped column body.
    short=recipe['stage']['small_pipe']
    height=short['height'];stub=Image.new('RGBA',(art.pipe.width,height))
    stub.alpha_composite(art.pipe.crop((0,0,art.pipe.width,15)),(0,0))
    # Stretch by repeating the actual captured pipe body rows, never blur.
    body=art.pipe.crop((0,16,art.pipe.width,32))
    for y in range(15,height,16):
        chunk=body.crop((0,0,art.pipe.width,min(16,height-y)))
        stub.alpha_composite(chunk,(0,y))
    image.alpha_composite(stub,(short['x'],short['bottom_y']-height))
    # Static blocks separated from independently animated blocks.
    for block in recipe['blocks']:
        if 'static_id' in block:
            image.alpha_composite(art.metatile(block['static_id']),(block['x'],block['y']))
    return image


def draw_frame(art:Art,recipe:dict,scene:Image.Image,index:int)->Image.Image:
    image=scene.copy()
    for block in recipe['blocks']:
        if 'frames' in block:
            tid=block['frames'][(index//block['ticks_per_frame'])%len(block['frames'])]
            image.alpha_composite(art.metatile(tid),(block['x'],block['y']))
    # Coin animation is deliberately artist-created from an authentic captured coin sprite.
    widths=(art.coin.width,12,8,4,2,4,8,12)
    for c in recipe['coins']:
        phase=(index+int(c.get('phase',0)))%c['period_frames']
        width=widths[phase%len(widths)]
        coin=art.coin.resize((width,art.coin.height),Image.Resampling.NEAREST)
        bob=round(math.sin(2*math.pi*index/c['bob_period'])*c['bob_amp'])
        image.alpha_composite(coin,(c['x']-width//2,c['y']-coin.height//2+bob))
    m=recipe['mario'];bob=round(math.sin(2*math.pi*index/m['bob_period'])*m['bob_amp'])
    pose=art.mario_fly if (index//m['pose_period'])%2==0 else art.mario_idle
    image.alpha_composite(pose,(m['anchor_x']-pose.width//2,m['feet_y']-pose.height+bob))
    return image.convert('RGB')


def encode_gif(frames:list[Image.Image],rgb_colors:list[tuple[int,int,int]],ms:int,scale:int,out:Path):
    # Fixed palette prevents per-frame color drift; no resampling or dither.
    pal=Image.new('P',(1,1))
    flat=[component for color in rgb_colors for component in color]
    pal.putpalette(flat+[0]*(768-len(flat)))
    indexed=[]
    for image in frames:
        frame=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
        indexed.append(frame.quantize(palette=pal,dither=Image.Dither.NONE))
    indexed[0].save(out,save_all=True,append_images=indexed[1:],duration=ms,loop=0,optimize=False,disposal=2)


def write_metatile_atlas(art:Art, path:Path)->None:
    """Browsable original Plains 16x16 graphics, with source tile IDs for recipes."""
    cell_w,cell_h=46,52
    sheet=Image.new('RGB',(16*cell_w,16*cell_h),(34,39,45))
    draw=ImageDraw.Draw(sheet)
    for index in range(256):
        x=(index%16)*cell_w
        y=(index//16)*cell_h
        tile=art.metatile(index).resize((40,40),Image.Resampling.NEAREST)
        sheet.paste(tile.convert('RGB'),(x+3,y+2))
        draw.text((x+13,y+43),f'{index:02X}',fill=(255,255,255))
    sheet.save(path)


def build(rom_path:Path,capture_path:Path,palette_path:Path,outdir:Path,recipe_path:Path|None=None)->dict:
    outdir.mkdir(parents=True,exist_ok=True)
    recipe=(json.loads(recipe_path.read_text(encoding='utf-8')) if recipe_path else default_recipe())
    if recipe.get('recipe_version')!=1:raise ValueError('Unsupported composition schema version')
    for k in ('frames','frame_duration_ms','scale','width','height'):
        if not isinstance(recipe[k],int) or recipe[k]<=0:raise ValueError(f'Invalid {k}')
    if recipe['frames']>120 or recipe['width']>1024 or recipe['height']>576:raise ValueError('Bounded prototype output exceeded')
    validate_animation_periods(recipe)
    rom=input_rom(rom_path)
    colors=load_rgb_profile(palette_path)
    with CaptureSource(capture_path) as archive:
        capture_fingerprint=archive.fingerprint()
        art=Art(rom,archive,colors)
        write_metatile_atlas(art,outdir/'World11_Source_Metatiles.png')
        scene=bg_scene(art,recipe)
        frames=[draw_frame(art,recipe,scene,i) for i in range(recipe['frames'])]
    gifpath=outdir/'World11_Stage_Loop.gif'
    encode_gif(frames,colors,recipe['frame_duration_ms'],recipe['scale'],gifpath)
    poster=frames[0].resize((recipe['width']*recipe['scale'],recipe['height']*recipe['scale']),Image.Resampling.NEAREST)
    poster.save(outdir/'World11_Stage_Preview.png')
    contact=Image.new('RGB',(4*recipe['width'],3*recipe['height']))
    for index,fi in enumerate([round(i*len(frames)/12)%len(frames) for i in range(12)]):
        contact.paste(frames[fi],((index%4)*recipe['width'],(index//4)*recipe['height']))
    contact.save(outdir/'World11_Stage_Frames.png')
    (outdir/'World11_Stage_Recipe.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8')
    # Inspect actual exported GIF, not just Pillow frames.
    from PIL import ImageSequence
    with Image.open(gifpath) as image:
        count=getattr(image,'n_frames',1)
        loop=image.info.get('loop');durations=[];pxtypes=[]
        for i in range(count):
            image.seek(i);durations.append(image.info.get('duration',0))
            pxtypes.append(image.mode)
    if count!=len(frames) or loop!=0:raise ValueError(f'GIF encoding incomplete: {count} frames / loop {loop}')
    if len(set(durations))!=1:raise ValueError('Unexpected GIF frame duration mismatch')
    # Position is a periodic function for each animated element. Looped phase and
    # frame edge are visually inspectable in full frame previews, not mathematically identical.
    report={
      'acceptance':'prototype_gif_exported_needs_visual_review',
      'source_class':'composed/edited','native_exact_level_reproduction':False,
      'rom_sha256':sha(rom),'capture_fingerprint':capture_fingerprint,
      'capture_frames_used':[SAMPLE_FRAME,450778,450786,450881],
      'plains_quadrants_sha256':QUAD_SHA,'chr_pages_1k_used':art.pages,
      'rgb_profile_sha256':sha(palette_path.read_bytes()),
      'browse_contact_sheet':'World11_Source_Metatiles.png',
      'gif':gifpath.name,'gif_sha256':sha(gifpath.read_bytes()),
      'gif_frames':count,'loop_count':loop,'frame_duration_ms':durations[0],
      'frame_dimensions':[recipe['width']*recipe['scale'],recipe['height']*recipe['scale']],
      'scene_layers':['captured sky color','ROM Plains tile hills','ROM terrain','artist-composed grass/clouds','native captured pipe','ROM blocks','native captured coin','native captured raccoon Mario'],
      'independently_animated':['question blocks','coin spins+bobbing','Raccoon Mario bob/pose'],
      'known_limitations':['Creative World 1-1 stage composition, not native exact level','Hand-arranged terrain and cloud shapes','Coin spin and Mario bounce are artist-created, not inferred timing','GIF palette constrained to native MesenCE 2C02 colors'],
      'visual_review':'pending'
    }
    (outdir/'World11_Stage_QA.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,required=True,help='Private SMB3 US PRG1 ROM ZIP')
    parser.add_argument('--capture',type=Path,required=True,help='Private MesenCE B.zip or replay directory')
    parser.add_argument('--rgb-profile',type=Path,required=True,help='Local pinned MesenCE NesDefaultVideoFilter.cpp or 64-color JSON')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--recipe',type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.rom,args.capture,args.rgb_profile,args.output,args.recipe),indent=2))

if __name__=='__main__':main()