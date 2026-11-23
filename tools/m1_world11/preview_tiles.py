"""Illustrative-only CHR-backed preview of a partially decoded source map.

No capture palettes or complete physical CHR mapping were uploaded in this
session. This is NOT an SMB3-native RGB panorama and is excluded from acceptance.
"""
import hashlib
import sys
import zipfile
from pathlib import Path
from PIL import Image
from world11_compile import compile_image, COLS, ROWS, ROM_SHA

ROM_QUADS = 0x1E010
ROM_QUAD_SHA = 'c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362'
# Previously documented capture frame 450840 mapping; not verified against
# every part of the scene, so use only for a provisional art inspection.
PAGES = (8, 9, 100, 101)
# Illustrative palettes, NOT captured MesenCE palette RAM. Index zero is sky.
PALETTES = (
  ((181,235,242),(242,244,232),(167,182,194),(84,96,118)),
  ((181,235,242),(227,160,91),(178,100,51),(87,59,43)),
  ((181,235,242),(179,222,109),(82,162,80),(38,96,60)),
  ((181,235,242),(228,193,98),(167,120,63),(80,57,39)),
)


def render(image, model, *, page_mapping=PAGES, palette_groups=PALETTES):
    table=image[ROM_QUADS:ROM_QUADS+1024]
    if hashlib.sha256(table).hexdigest()!=ROM_QUAD_SHA:
        raise ValueError('Quadrant table SHA-256 mismatch')
    chr_rom=image[16+0x40000:16+0x40000+0x20000]
    if len(chr_rom)!=0x20000:
        raise ValueError('Expected 128 KiB CHR')
    tile_cache={}
    out=Image.new('RGB',(COLS*16,ROWS*16))
    pixels=out.load()
    for y in range(ROWS):
        for x in range(COLS):
            tileid=model.tiles[y][x]
            if tileid not in tile_cache:
                tc=Image.new('RGB',(16,16))
                pc=tc.load()
                colors=palette_groups[tileid>>6]
                for q,dx,dy in ((0,0,0),(1,0,8),(2,8,0),(3,8,8)):
                    pattern=table[q*256+tileid]
                    address=pattern*16
                    physical=page_mapping[address//1024]*1024+(address%1024)
                    b=chr_rom[physical:physical+16]
                    for yy in range(8):
                        for xx in range(8):
                            bit=7-xx
                            n=((b[yy]>>bit)&1)|(((b[yy+8]>>bit)&1)<<1)
                            pc[dx+xx,dy+yy]=colors[n]
                tile_cache[tileid]=tc
            out.paste(tile_cache[tileid],(x*16,y*16))
    return out

if __name__=='__main__':
    path=Path(sys.argv[1]); dest=Path(sys.argv[2])
    with zipfile.ZipFile(path) as z:raw=z.read([x for x in z.namelist() if x.lower().endswith('.nes')][0])
    _,model,_=compile_image(raw)
    result=render(raw,model)
    result.save(dest)
    print('Illustrative CHR-backed preview only:',dest,result.size)


def export_private_scene_bundle(rom_image: bytes, model, report: dict, output: Path, *,
                                page_mapping=PAGES, palette_groups=PALETTES,
                                graphics_provenance=None) -> Path:
    """Create a PR #29 recipe from the source-built map, not reference screenshots.

    Graphics use the *illustrative* physical CHR page choice and palette from
    this preview. Thus these are useful inputs for testing compositor I/O,
    NOT final game-frame RGB/CHR verification or Milestone 1 acceptance.
    Extracted tile art stays local/private and is never committed to GitHub.
    """
    import json
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite an existing bundle: {output}')
    output.mkdir(parents=True)
    sprites = output / 'tiles'
    sprites.mkdir()
    table=rom_image[ROM_QUADS:ROM_QUADS+1024]
    chr_rom=rom_image[16+0x40000:16+0x40000+0x20000]
    if hashlib.sha256(table).hexdigest()!=ROM_QUAD_SHA:
        raise ValueError('Unexpected Plains table SHA-256')
    if len(chr_rom)!=0x20000:
        raise ValueError('Unexpected CHR size')
    rows=[]
    assets={}
    for source_row in model.tiles:
        names=[]
        for tile_id in source_row:
            name=f'tile_{tile_id:02x}'
            names.append(name)
            if name in assets:
                continue
            # Generate actual 8x8 NES CHR pixels into each 16x16 metatile.
            rgba=Image.new('RGB',(16,16))
            pix=rgba.load()
            rgb=palette_groups[tile_id>>6]
            refs=[]
            for quad,xoff,yoff in ((0,0,0),(1,0,8),(2,8,0),(3,8,8)):
                pattern=table[quad*256+tile_id]
                address=pattern*16
                physical=page_mapping[address//1024]*1024+address%1024
                raw=chr_rom[physical:physical+16]
                refs.append({'pattern_id':pattern,'chr_offset':physical})
                for y in range(8):
                    for x in range(8):
                        bit=7-x
                        ink=((raw[y]>>bit)&1)|(((raw[y+8]>>bit)&1)<<1)
                        pix[x+xoff,y+yoff]=rgb[ink]
            file=sprites / f'{name}.png'
            rgba.save(file)
            assets[name]={
                'file': f'tiles/{name}.png',
                'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                'provenance': {
                    'kind':'source_derived_preview',
                    'logical_tile_id':tile_id,
                    'quadrants':refs,
                    'rom_sha256':ROM_SHA,
                    'quadrant_sha256':ROM_QUAD_SHA,
                    'physical_chr_page_selection':list(page_mapping),
                    'palette_mode':'captured_snapshot' if graphics_provenance else 'illustrative_not_native',
                },
            }
        rows.append(names)
    recipe={
        'version':1,
        'size':[COLS*16,ROWS*16],
        'tile_size':[16,16],
        'ticks':1,
        'tick_ms':20,
        'background':list(palette_groups[2][0]),
        'assets':assets,
        'layers':[{'tiles':rows}],
        'staging_provenance':{
            'source':'world11_compile.partial/1',
            'source_class':'partially_decoded',
            'native_verified':False,
            'background_source':'compiled_ROM_command_stream_not_screenshot',
            'unknown_random_clouds':report['random_clouds_unknown'],
            'unverified_command_sources':[c['offset'] for c in report['unsupported_commands']],
            'provisional_command_sources':[c['source_offset'] for c in report['provisional_commands']],
            'source_written_cells':report['written_cell_count'],
            'pipe_floor_visual_overlap_corrections':report['pipe_ground_overlaps'],
            'pipe_floor_correction_status':report['pipe_ground_overlap_status'],
            'total_cells':COLS*ROWS,
            'caveat':'Partial source layout. Global graphics snapshot does not verify dynamic CHR changes. This is not a full accepted native scene.',
            'graphics_snapshot_provenance':graphics_provenance or {'profile':'illustrative','chr_pages':list(page_mapping)},
        },
    }
    path=output/'recipe.json'
    path.write_text(json.dumps(recipe,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (output/'preview_validation.json').write_text(json.dumps({
        'generated_by':'spritemine_m1_work.preview_tiles.export_private_scene_bundle',
        'source_preview_sha256':hashlib.sha256(render(rom_image,model,page_mapping=page_mapping,palette_groups=palette_groups).tobytes()).hexdigest(),
        'recipe_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'native_rgb_verified':False,
        'environmental_animation_integrated':False,
        'enemies_integrated':False,
        'note':'Bundle for generic scene compositor interface; source graphics are private.',
    },indent=2)+'\n',encoding='utf-8')
    return path



def load_native_graphics_profile(rom_image: bytes, ppu_snapshot: Path,
                                 palette_ram: Path, rgb_profile: Path):
    """Decode a single real PPU graphics snapshot into ROM CHR references.

    This is FRAME-LOCAL information. Do not assume these pages or palette RAM
    are correct at other World 1-1 frames or at a different world position.
    """
    return decode_native_graphics_profile(rom_image, ppu_snapshot.read_bytes(),
                                          palette_ram.read_bytes(), rgb_profile.read_bytes())


def decode_native_graphics_profile(rom_image: bytes, ppu: bytes,
                                   palette: bytes, profile: bytes):
    """Allow frame-exact in-memory ZIP input without extracting private dumps."""
    if len(ppu)!=0x3000 or len(palette)!=32 or len(profile)!=192:
        raise ValueError('Expected 12 KiB PPU, 32-byte palette RAM, 192-byte RGB profile')
    if max(palette)>63:
        raise ValueError('Expected palette codes 0..63')
    chr_rom=rom_image[16+0x40000:16+0x40000+0x20000]
    pages=[]
    for i in range(4):
        sample=ppu[i*1024:(i+1)*1024]
        matches=[k for k in range(len(chr_rom)//1024)
                 if chr_rom[k*1024:(k+1)*1024]==sample]
        if len(matches)!=1:
            raise ValueError(f'Physical CHR page {i} is ambiguous or absent ({len(matches)} matches)')
        pages.append(matches[0])
    groups=[]
    for n in range(4):
        indices=[palette[0],palette[n*4+1],palette[n*4+2],palette[n*4+3]]
        groups.append(tuple(tuple(profile[j*3:j*3+3]) for j in indices))
    provenance={
        'source':'MesenCE_start_PPU_snapshot_frame_local',
        'ppu_sha256':hashlib.sha256(ppu).hexdigest(),
        'palette_sha256':hashlib.sha256(palette).hexdigest(),
        'rgb_profile_sha256':hashlib.sha256(profile).hexdigest(),
        'mapped_chr_pages':pages,
        'world_wide_mapping_verified':False,
    }
    return tuple(pages),tuple(groups),provenance
